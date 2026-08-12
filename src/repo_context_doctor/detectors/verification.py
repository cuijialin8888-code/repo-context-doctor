"""Discover verification paths and retain their provenance without executing them."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from repo_context_doctor.detectors.ecosystems import EcosystemState
from repo_context_doctor.models import (
    Category,
    Confidence,
    Finding,
    InstructionSurface,
    Provenance,
    Status,
    VerificationPath,
)
from repo_context_doctor.privacy import sanitize_excerpt
from repo_context_doctor.snapshot import RepositorySnapshot

_SCRIPT_KINDS = {
    "test": "test",
    "lint": "lint",
    "format": "format",
    "fmt": "format",
    "build": "build",
    "typecheck": "typecheck",
    "type-check": "typecheck",
    "check-types": "typecheck",
    "integration": "integration",
    "e2e": "integration",
}

_COMMAND_RE = re.compile(
    r"(?i)^(?:python\s+-m\s+pytest|pytest(?:\s|$)|ruff\s+(?:check|format)(?:\s|$)|"
    r"mypy(?:\s|$)|pyright(?:\s|$)|tox(?:\s|$)|nox(?:\s|$)|"
    r"npm\s+(?:test|run\s+\S+)|pnpm\s+\S+|yarn\s+\S+|bun\s+(?:test|run\s+\S+)|"
    r"cargo\s+(?:test|build|fmt|clippy)(?:\s|$)|go\s+(?:test|build|vet)(?:\s|$)|"
    r"Invoke-Pester(?:\s|$)|Invoke-ScriptAnalyzer(?:\s|$)|make\s+\S+)"
)


def _kind(command: str) -> str:
    lower = command.lower()
    if any(
        token in lower
        for token in ("pytest", "npm test", "pnpm test", "cargo test", "go test", "invoke-pester")
    ):
        return "test"
    if any(token in lower for token in ("lint", "ruff check", "clippy", "scriptanalyzer")):
        return "lint"
    if any(token in lower for token in ("typecheck", "type-check", "mypy", "pyright")):
        return "typecheck"
    if any(token in lower for token in ("format", " fmt", "ruff format")):
        return "format"
    if "build" in lower:
        return "build"
    if "integration" in lower or "e2e" in lower:
        return "integration"
    return "other"


def _package_manager(snapshot: RepositorySnapshot, manifest: str, data: dict[str, object]) -> str:
    declared = data.get("packageManager")
    if isinstance(declared, str) and declared:
        manager = declared.split("@", 1)[0].lower()
        if manager in {"npm", "pnpm", "yarn", "bun"}:
            return manager
    parent = PurePosixPath(manifest).parent
    candidates = {
        "pnpm-lock.yaml": "pnpm",
        "yarn.lock": "yarn",
        "bun.lock": "bun",
        "bun.lockb": "bun",
        "package-lock.json": "npm",
    }
    for filename, manager in candidates.items():
        path = (parent / filename).as_posix()
        if snapshot.has_file(path):
            return manager
    return "npm"


def _script_invocation(manager: str, name: str) -> str:
    if manager == "npm":
        return "npm test" if name == "test" else f"npm run {name}"
    if manager == "bun":
        return "bun test" if name == "test" else f"bun run {name}"
    return f"{manager} {name}"


def _extract_documented_commands(text: str) -> list[str]:
    commands: list[str] = []
    fenced = False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            fenced = not fenced
            continue
        candidate = stripped
        if candidate.startswith(("$ ", "> ")):
            candidate = candidate[2:].strip()
        if not candidate or len(candidate) > 500:
            continue
        if (fenced or raw_line.startswith(("    ", "\t"))) and _COMMAND_RE.match(candidate):
            commands.append(candidate)
    return commands


def _make_targets(text: str) -> list[str]:
    targets: list[str] = []
    for line in text.splitlines():
        if line.startswith((" ", "\t", ".")):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+)\s*:(?![=])", line)
        if match and match.group(1).lower() in _SCRIPT_KINDS:
            targets.append(match.group(1))
    return targets


def _deduplicate(paths: list[VerificationPath]) -> list[VerificationPath]:
    seen: set[tuple[str, str, str]] = set()
    result: list[VerificationPath] = []
    for path in paths:
        key = (path.kind, path.command.casefold(), path.source_path.casefold())
        if key not in seen:
            seen.add(key)
            result.append(path)
    return sorted(
        result, key=lambda item: (item.kind, item.provenance, item.command, item.source_path)
    )


def detect_verification(
    snapshot: RepositorySnapshot,
    state: EcosystemState,
    surfaces: list[InstructionSurface],
    existing_paths: list[VerificationPath] | None = None,
) -> tuple[list[VerificationPath], list[Finding], dict[str, bool]]:
    paths: list[VerificationPath] = list(existing_paths or [])

    for manifest, data in sorted(state.package_json.items()):
        scripts = data.get("scripts")
        if not isinstance(scripts, dict):
            continue
        manager = _package_manager(snapshot, manifest, data)
        for name, raw in sorted(scripts.items()):
            if not isinstance(name, str) or not isinstance(raw, str):
                continue
            base = name.split(":", 1)[0].lower()
            kind = _SCRIPT_KINDS.get(base)
            if not kind:
                continue
            paths.append(
                VerificationPath(
                    kind,
                    _script_invocation(manager, name),
                    Provenance.MANIFEST,
                    Confidence.HIGH,
                    manifest,
                    f"package.json defines scripts.{name}",
                )
            )

    for path in sorted(snapshot.files):
        name = PurePosixPath(path).name.lower()
        if name not in {"makefile", "gnumakefile"}:
            continue
        text = snapshot.read_text(path)
        if text is None:
            continue
        for target in _make_targets(text):
            paths.append(
                VerificationPath(
                    _SCRIPT_KINDS[target.lower()],
                    f"make {target}",
                    Provenance.MAKEFILE,
                    Confidence.HIGH,
                    path,
                    f"Make target '{target}' is defined",
                )
            )

    instruction_paths = {surface.path for surface in surfaces}
    documentation_paths = {
        path
        for path in snapshot.files
        if PurePosixPath(path).name.lower()
        in {"readme.md", "readme.rst", "contributing.md", "development.md"}
        and len(PurePosixPath(path).parts) <= 3
    }
    for path in sorted(instruction_paths | documentation_paths):
        text = snapshot.read_text(path)
        if text is None:
            continue
        provenance = (
            Provenance.INSTRUCTION if path in instruction_paths else Provenance.DOCUMENTATION
        )
        for command in _extract_documented_commands(text):
            safe, _ = sanitize_excerpt(command)
            paths.append(
                VerificationPath(
                    _kind(safe),
                    safe,
                    provenance,
                    Confidence.MEDIUM,
                    path,
                    "Command appears in an indented or fenced documentation line",
                )
            )

    explicit_kinds = {path.kind for path in paths}
    for manifest, data in sorted(state.pyproject.items()):
        tool = data.get("tool")
        if not isinstance(tool, dict):
            continue
        inferred: list[tuple[str, str, str]] = []
        if "pytest" in tool and "test" not in explicit_kinds:
            inferred.append(("test", "pytest", "pyproject.toml configures pytest"))
        if "ruff" in tool and "lint" not in explicit_kinds:
            inferred.append(("lint", "ruff check .", "pyproject.toml configures Ruff"))
        if "mypy" in tool and "typecheck" not in explicit_kinds:
            inferred.append(("typecheck", "mypy .", "pyproject.toml configures mypy"))
        for kind, command, evidence in inferred:
            paths.append(
                VerificationPath(
                    kind,
                    command,
                    Provenance.INFERRED,
                    Confidence.MEDIUM,
                    manifest,
                    evidence,
                )
            )

    if "Rust" in state.ecosystems:
        for kind, command in (
            ("test", "cargo test"),
            ("build", "cargo build"),
            ("format", "cargo fmt --check"),
            ("lint", "cargo clippy"),
        ):
            if kind not in explicit_kinds:
                paths.append(
                    VerificationPath(
                        kind,
                        command,
                        Provenance.INFERRED,
                        Confidence.MEDIUM,
                        next(iter(state.cargo_toml), "Cargo.toml"),
                        "Stable Rust ecosystem convention; not repository-documented",
                    )
                )
    if "Go" in state.ecosystems:
        for kind, command in (("test", "go test ./..."), ("build", "go build ./...")):
            if kind not in explicit_kinds:
                paths.append(
                    VerificationPath(
                        kind,
                        command,
                        Provenance.INFERRED,
                        Confidence.MEDIUM,
                        state.go_mod[0] if state.go_mod else "go.mod",
                        "Stable Go ecosystem convention; not repository-documented",
                    )
                )

    paths = _deduplicate(paths)
    findings: list[Finding] = []
    by_kind = {
        kind: [path for path in paths if path.kind == kind] for kind in _SCRIPT_KINDS.values()
    }
    test_paths = by_kind.get("test", [])
    explicit_test = any(path.provenance != Provenance.INFERRED for path in test_paths)
    if explicit_test:
        findings.append(
            Finding(
                "verification.test",
                Category.VERIFICATION,
                Status.PASS,
                "Explicit test verification path discovered",
                "The command came from repository-owned metadata, instructions, "
                "documentation, or CI.",
                ", ".join(path.command for path in test_paths[:5]),
                "Keep the command aligned across instructions, manifests, and CI.",
                Confidence.HIGH,
                tuple(path.source_path for path in test_paths),
            )
        )
    elif test_paths:
        findings.append(
            Finding(
                "verification.test",
                Category.VERIFICATION,
                Status.INFO,
                "Only an inferred test path was discovered",
                "The command is an ecosystem convention, not explicit repository guidance.",
                ", ".join(path.command for path in test_paths),
                "Document the intended test command if contributors need a "
                "repository-specific path.",
                Confidence.MEDIUM,
                tuple(path.source_path for path in test_paths),
                Provenance.INFERRED,
            )
        )
    else:
        findings.append(
            Finding(
                "verification.test",
                Category.VERIFICATION,
                Status.WARN,
                "No test command was discovered",
                "Test files or frameworks are not treated as proof of a runnable command.",
                "No supported explicit or inferred test invocation was found.",
                "Document a verified test command in a manifest, instruction file, "
                "README, Makefile, or CI.",
                Confidence.HIGH,
            )
        )

    discovered_kinds = sorted({path.kind for path in paths})
    findings.append(
        Finding(
            "verification.inventory",
            Category.VERIFICATION,
            Status.PASS if paths else Status.UNKNOWN,
            f"Discovered {len(paths)} verification path(s)"
            if paths
            else "Verification path inventory is empty",
            "Commands are reported but never executed.",
            ", ".join(discovered_kinds) if discovered_kinds else "No supported command evidence.",
            "Prioritize explicit test, lint, build, and typecheck commands that match CI.",
            Confidence.HIGH,
            tuple(path.source_path for path in paths),
        )
    )

    explicit = {path.kind for path in paths if path.provenance != Provenance.INFERRED}
    inferred = {path.kind for path in paths if path.provenance == Provenance.INFERRED}
    facts = {
        "explicit_test": "test" in explicit,
        "inferred_test": "test" in inferred,
        "explicit_lint": "lint" in explicit,
        "inferred_lint": "lint" in inferred,
        "explicit_build": "build" in explicit,
        "inferred_build": "build" in inferred,
        "explicit_type_or_format": bool({"typecheck", "format"} & explicit),
        "inferred_type_or_format": bool({"typecheck", "format"} & inferred),
    }
    return paths, findings, facts
