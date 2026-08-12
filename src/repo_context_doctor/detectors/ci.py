"""Bounded CI presence and verification-command inspection."""

from __future__ import annotations

from pathlib import PurePosixPath

from repo_context_doctor.detectors.verification import _extract_documented_commands, _kind
from repo_context_doctor.models import (
    Category,
    Confidence,
    Finding,
    Provenance,
    Status,
    VerificationPath,
)
from repo_context_doctor.privacy import sanitize_excerpt
from repo_context_doctor.snapshot import RepositorySnapshot


def _github_workflows(snapshot: RepositorySnapshot) -> list[str]:
    return sorted(
        path
        for path in snapshot.files
        if path.lower().startswith(".github/workflows/")
        and PurePosixPath(path).suffix.lower() in {".yml", ".yaml"}
    )


def _run_blocks(text: str) -> list[str]:
    commands: list[str] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped.startswith("run:"):
            index += 1
            continue
        value = stripped[4:].strip()
        if value and value not in {"|", ">", "|-", ">-"}:
            commands.extend(_extract_documented_commands(f"```\n{value}\n```"))
            index += 1
            continue
        indent = len(line) - len(line.lstrip())
        block: list[str] = []
        index += 1
        while index < len(lines):
            candidate = lines[index]
            if candidate.strip() and len(candidate) - len(candidate.lstrip()) <= indent:
                break
            block.append(candidate.strip())
            index += 1
        commands.extend(_extract_documented_commands("```\n" + "\n".join(block) + "\n```"))
    return commands


def detect_ci(
    snapshot: RepositorySnapshot,
) -> tuple[list[VerificationPath], list[Finding], dict[str, bool]]:
    workflows = _github_workflows(snapshot)
    other = []
    for path in snapshot.files:
        lower = path.lower()
        if lower in {".gitlab-ci.yml", "azure-pipelines.yml"} or lower == ".circleci/config.yml":
            other.append(path)

    findings: list[Finding] = []
    ci_paths: list[VerificationPath] = []
    if workflows or other:
        findings.append(
            Finding(
                "automation.ci",
                Category.AUTOMATION,
                Status.PASS,
                "Continuous-integration configuration detected",
                "GitHub Actions receives bounded command inspection; other CI systems are presence-only.",
                ", ".join(workflows + sorted(other)),
                "Keep local verification guidance aligned with CI.",
                Confidence.HIGH,
                tuple(workflows + sorted(other)),
            )
        )
    else:
        findings.append(
            Finding(
                "automation.ci",
                Category.AUTOMATION,
                Status.INFO,
                "No supported CI configuration was detected",
                "Absence of CI is not necessarily an error for every repository.",
                "No GitHub Actions, GitLab CI, Azure Pipelines, or CircleCI config was found.",
                "Document local verification clearly when CI is intentionally absent.",
                Confidence.HIGH,
            )
        )

    for path in workflows:
        text = snapshot.read_text(path)
        if text is None:
            continue
        for command in _run_blocks(text):
            safe, _ = sanitize_excerpt(command)
            ci_paths.append(
                VerificationPath(
                    _kind(safe),
                    safe,
                    Provenance.CI,
                    Confidence.HIGH,
                    path,
                    "GitHub Actions run step contains a supported verification command",
                )
            )

    if workflows:
        kinds = sorted({path.kind for path in ci_paths if path.kind != "other"})
        findings.append(
            Finding(
                "automation.ci-verification",
                Category.AUTOMATION,
                Status.PASS if kinds else Status.INFO,
                "Verification signals detected in GitHub Actions"
                if kinds
                else "GitHub Actions detected without recognized verification commands",
                "Workflow parsing is intentionally shallow and does not evaluate YAML semantics.",
                ", ".join(kinds) if kinds else "No supported run command matched.",
                "Review the workflow manually if commands are composed through reusable actions or variables.",
                Confidence.MEDIUM,
                tuple(workflows),
            )
        )

    return ci_paths, findings, {"ci_detected": bool(workflows or other), "ci_verification": bool(ci_paths)}

