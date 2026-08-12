"""Ecosystem and manifest detection with bounded structured parsing."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from repo_context_doctor.models import Category, Confidence, Finding, Status
from repo_context_doctor.snapshot import RepositorySnapshot


@dataclass(slots=True)
class EcosystemState:
    ecosystems: set[str] = field(default_factory=set)
    manifests: list[str] = field(default_factory=list)
    package_json: dict[str, dict[str, Any]] = field(default_factory=dict)
    pyproject: dict[str, dict[str, Any]] = field(default_factory=dict)
    cargo_toml: dict[str, dict[str, Any]] = field(default_factory=dict)
    go_mod: list[str] = field(default_factory=list)
    powershell_tests: list[str] = field(default_factory=list)
    monorepo: bool = False


_OTHER_MANIFESTS = {
    "build.gradle": "Java",
    "build.gradle.kts": "Java/Kotlin",
    "composer.json": "PHP",
    "gemfile": "Ruby",
    "package.swift": "Swift",
    "pom.xml": "Java",
}

_FIXTURE_DIRECTORIES = {"fixtures", "testdata"}


def _is_fixture_manifest(path: PurePosixPath) -> bool:
    return bool(_FIXTURE_DIRECTORIES & {part.lower() for part in path.parts[:-1]})


def _parse_json(snapshot: RepositorySnapshot, path: str) -> dict[str, Any]:
    text = snapshot.read_text(path)
    if text is None:
        raise ValueError("unreadable UTF-8 JSON or file exceeded the read limit")
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value is not an object")
    return value


def _parse_toml(snapshot: RepositorySnapshot, path: str) -> dict[str, Any]:
    text = snapshot.read_text(path)
    if text is None:
        raise ValueError("unreadable UTF-8 TOML or file exceeded the read limit")
    return tomllib.loads(text)


def detect_ecosystems(
    snapshot: RepositorySnapshot,
) -> tuple[EcosystemState, list[Finding], dict[str, bool]]:
    state = EcosystemState()
    findings: list[Finding] = []
    primary_manifest_dirs: list[str] = []

    for path in sorted(snapshot.files):
        pure = PurePosixPath(path)
        name = pure.name
        lower = name.lower()
        depth = len(pure.parts) - 1
        if depth > 4 or _is_fixture_manifest(pure):
            continue

        try:
            if lower == "package.json":
                state.ecosystems.add("Node.js")
                state.manifests.append(path)
                primary_manifest_dirs.append(pure.parent.as_posix())
                data = _parse_json(snapshot, path)
                state.package_json[path] = data
                if data.get("workspaces"):
                    state.monorepo = True
            elif lower == "pyproject.toml":
                state.ecosystems.add("Python")
                state.manifests.append(path)
                primary_manifest_dirs.append(pure.parent.as_posix())
                state.pyproject[path] = _parse_toml(snapshot, path)
            elif lower == "cargo.toml":
                state.ecosystems.add("Rust")
                state.manifests.append(path)
                primary_manifest_dirs.append(pure.parent.as_posix())
                data = _parse_toml(snapshot, path)
                state.cargo_toml[path] = data
                if data.get("workspace"):
                    state.monorepo = True
            elif lower == "go.mod":
                state.ecosystems.add("Go")
                state.manifests.append(path)
                primary_manifest_dirs.append(pure.parent.as_posix())
                state.go_mod.append(path)
            elif lower in {"setup.cfg", "setup.py", "requirements.txt", "tox.ini"}:
                state.ecosystems.add("Python")
                state.manifests.append(path)
            elif lower == "pnpm-workspace.yaml":
                state.ecosystems.add("Node.js")
                state.manifests.append(path)
                state.monorepo = True
            elif lower in _OTHER_MANIFESTS:
                state.ecosystems.add(_OTHER_MANIFESTS[lower])
                state.manifests.append(path)
            elif lower.endswith((".sln", ".csproj", ".fsproj")):
                state.ecosystems.add(".NET")
                state.manifests.append(path)
        except (json.JSONDecodeError, tomllib.TOMLDecodeError, ValueError) as exc:
            findings.append(
                Finding(
                    f"manifest.malformed.{len(findings) + 1}",
                    Category.REPOSITORY,
                    Status.FAIL,
                    f"Manifest could not be parsed: {path}",
                    "A present but malformed manifest is a machine-verifiable repository error.",
                    type(exc).__name__,
                    "Repair the manifest syntax, then rerun the scan.",
                    Confidence.HIGH,
                    (path,),
                )
            )

    powershell = [
        path
        for path in snapshot.files
        if PurePosixPath(path).suffix.lower() in {".ps1", ".psd1", ".psm1"}
    ]
    if powershell:
        state.ecosystems.add("PowerShell")
        state.powershell_tests = [
            path for path in powershell if path.lower().endswith(".tests.ps1")
        ]

    distinct_dirs = {directory for directory in primary_manifest_dirs if directory != "."}
    if len(distinct_dirs) > 1:
        state.monorepo = True

    if not state.ecosystems:
        state.ecosystems.add("Generic")

    findings.append(
        Finding(
            "repository.ecosystems",
            Category.REPOSITORY,
            Status.INFO,
            "Detected repository ecosystem signals",
            "Deep interpretation is limited to Generic, Node.js, Python, Rust, Go, and PowerShell.",
            ", ".join(sorted(state.ecosystems)),
            "Treat presence-only ecosystems as candidates for future detector contributions.",
            Confidence.HIGH,
            tuple(state.manifests),
        )
    )
    if state.monorepo:
        findings.append(
            Finding(
                "repository.monorepo",
                Category.REPOSITORY,
                Status.INFO,
                "Monorepo or multi-package structure detected",
                "The signal came from workspaces or multiple primary manifest directories.",
                ", ".join(sorted(set(primary_manifest_dirs))),
                "Check that instruction scopes and package-specific verification paths "
                "remain clear.",
                Confidence.MEDIUM,
                tuple(state.manifests),
            )
        )

    if state.powershell_tests:
        findings.append(
            Finding(
                "powershell.pester-structure",
                Category.VERIFICATION,
                Status.INFO,
                "Pester-style test files detected",
                "File naming is evidence of test structure, not proof of a complete invocation.",
                ", ".join(state.powershell_tests[:8]),
                "Document the intended Invoke-Pester command in repository instructions or CI.",
                Confidence.MEDIUM,
                tuple(state.powershell_tests),
            )
        )

    return state, findings, {"manifest_present": bool(state.manifests)}
