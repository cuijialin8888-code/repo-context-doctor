"""Detector orchestration for the public scan API."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from repo_context_doctor.detectors.ci import detect_ci
from repo_context_doctor.detectors.dependencies import detect_dependencies
from repo_context_doctor.detectors.ecosystems import detect_ecosystems
from repo_context_doctor.detectors.instructions import detect_instructions
from repo_context_doctor.detectors.repository import detect_repository
from repo_context_doctor.detectors.verification import detect_verification
from repo_context_doctor.models import (
    Category,
    Confidence,
    Finding,
    PrivacySummary,
    ScanReport,
    Status,
    VerificationPath,
)
from repo_context_doctor.scoring import calculate_scores
from repo_context_doctor.snapshot import ScanLimits, discover_repository


def _deduplicate_verification(paths: list[VerificationPath]) -> list[VerificationPath]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[VerificationPath] = []
    for path in paths:
        key = (path.kind, path.command.casefold(), path.provenance, path.source_path.casefold())
        if key not in seen:
            seen.add(key)
            result.append(path)
    return sorted(
        result, key=lambda item: (item.kind, item.provenance, item.command, item.source_path)
    )


def _recommendations(findings: list[Finding]) -> list[str]:
    priority = {Status.FAIL: 0, Status.WARN: 1, Status.UNKNOWN: 2}
    candidates = sorted(
        (finding for finding in findings if finding.status in priority and finding.recommendation),
        key=lambda finding: (priority[finding.status], finding.category, finding.id),
    )
    result: list[str] = []
    for finding in candidates:
        if finding.recommendation not in result:
            result.append(finding.recommendation)
        if len(result) == 5:
            break
    return result


def scan_repository(
    root: str | Path,
    *,
    include_score: bool = True,
    limits: ScanLimits | None = None,
) -> ScanReport:
    """Scan one local directory without writing to it or executing its code."""

    requested = Path(root)
    snapshot = discover_repository(requested, limits=limits)

    findings: list[Finding] = []
    facts: dict[str, bool] = {}

    surfaces, instruction_findings, instruction_facts = detect_instructions(snapshot)
    findings.extend(instruction_findings)
    facts.update(instruction_facts)

    repository_findings, repository_facts = detect_repository(snapshot)
    findings.extend(repository_findings)
    facts.update(repository_facts)

    ecosystem_state, ecosystem_findings, ecosystem_facts = detect_ecosystems(snapshot)
    findings.extend(ecosystem_findings)
    facts.update(ecosystem_facts)

    dependency_findings, dependency_facts = detect_dependencies(snapshot, ecosystem_state)
    findings.extend(dependency_findings)
    facts.update(dependency_facts)

    ci_verification, ci_findings, ci_facts = detect_ci(snapshot)
    findings.extend(ci_findings)
    facts.update(ci_facts)

    verification, verification_findings, verification_facts = detect_verification(
        snapshot, ecosystem_state, surfaces, ci_verification
    )
    findings.extend(verification_findings)
    facts.update(verification_facts)
    verification = _deduplicate_verification(verification)

    if snapshot.discovery_errors or snapshot.read_errors:
        findings.append(
            Finding(
                "scan.partial",
                Category.REPOSITORY,
                Status.UNKNOWN,
                "Some repository metadata could not be inspected",
                "Permission or file-read errors make this a partial scan.",
                (
                    f"discovery_errors={len(snapshot.discovery_errors)}; "
                    f"read_errors={len(snapshot.read_errors)}"
                ),
                "Rerun with access to the affected metadata if complete coverage is required.",
                Confidence.HIGH,
            )
        )
    if snapshot.oversized_files or snapshot.undecodable_files:
        findings.append(
            Finding(
                "scan.text-skipped",
                Category.REPOSITORY,
                Status.UNKNOWN,
                "Some metadata text was safely skipped",
                "Oversized or non-UTF-8 files are not fully interpreted.",
                (
                    f"oversized={len(snapshot.oversized_files)}; "
                    f"undecodable={len(snapshot.undecodable_files)}"
                ),
                "Keep critical repository instructions and metadata UTF-8 and within "
                "documented limits.",
                Confidence.HIGH,
            )
        )
    if snapshot.depth_limited or snapshot.entry_limited:
        findings.append(
            Finding(
                "scan.bounds",
                Category.REPOSITORY,
                Status.UNKNOWN,
                "Repository discovery reached a configured bound",
                "Results remain valid for inspected paths but may omit deeper or later entries.",
                f"depth_limited={snapshot.depth_limited}; entry_limited={snapshot.entry_limited}",
                "Use a narrower repository root or review the documented scan limits.",
                Confidence.HIGH,
            )
        )

    status_counts = Counter(finding.status.value for finding in findings)
    summary = {status.value: status_counts.get(status.value, 0) for status in Status}
    privacy = PrivacySummary(
        sensitive_files_skipped=len(snapshot.sensitive_files),
        oversized_files_skipped=len(snapshot.oversized_files),
        undecodable_files_skipped=len(snapshot.undecodable_files),
    )
    root_name = snapshot.root.name or "repository"
    repository = {
        "name": root_name,
        "path": ".",
        "is_git": snapshot.root.joinpath(".git").exists(),
        "monorepo": ecosystem_state.monorepo,
        "manifests": sorted(ecosystem_state.manifests),
    }
    scan = {
        "read_only": True,
        "project_commands_executed": False,
        "network_used": False,
        "symlinks_followed": False,
        "entries_seen": snapshot.entries_seen,
        "files_discovered": len(snapshot.files),
        "directories_discovered": len(snapshot.directories),
        "symlinks_skipped": len(snapshot.symlinks_skipped),
        "limits": {
            "max_depth": snapshot.limits.max_depth,
            "max_entries": snapshot.limits.max_entries,
            "max_file_bytes": snapshot.limits.max_file_bytes,
        },
    }
    return ScanReport(
        timestamp=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        repository=repository,
        ecosystems=sorted(ecosystem_state.ecosystems),
        instruction_surfaces=surfaces,
        verification_paths=verification,
        findings=sorted(findings, key=lambda finding: (finding.category, finding.id)),
        scores=calculate_scores(facts) if include_score else None,
        summary=summary,
        recommendations=_recommendations(findings),
        privacy=privacy,
        scan=scan,
    )
