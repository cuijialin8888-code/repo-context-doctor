"""Plain, stable console renderer."""

from __future__ import annotations

from collections import defaultdict

from repo_context_doctor.models import TOOL_NAME, TOOL_VERSION, ScanReport
from repo_context_doctor.privacy import redact_text


def render_console(report: ScanReport) -> str:
    lines = [f"# {TOOL_NAME} {TOOL_VERSION}", "", "Repository"]
    lines.extend(
        [
            f"Name:          {report.repository['name']}",
            f"Ecosystems:    {', '.join(report.ecosystems)}",
            f"Git:           {'Yes' if report.repository['is_git'] else 'No'}",
            f"Monorepo:      {'Yes' if report.repository['monorepo'] else 'No'}",
        ]
    )

    grouped: dict[str, list] = defaultdict(list)
    for finding in report.findings:
        grouped[finding.category.value].append(finding)

    labels = {
        "agent_context": "Agent Context",
        "verification": "Verification",
        "automation": "Automation",
        "reproducibility": "Reproducibility",
        "orientation": "Orientation",
        "repository": "Repository",
        "privacy": "Privacy",
    }
    for category in labels:
        if category not in grouped:
            continue
        lines.extend(["", labels[category]])
        for finding in grouped[category]:
            lines.append(f"[{finding.status.value}] {finding.summary}")

    if report.verification_paths:
        lines.extend(["", "Verification paths (not executed)"])
        for path in report.verification_paths:
            lines.append(
                f"- {path.kind}: {path.command} [{path.provenance.value}, {path.confidence.value}] "
                f"({path.source_path})"
            )

    lines.extend(["", "Summary"])
    lines.append("  ".join(f"{key}: {value}" for key, value in report.summary.items()))
    if report.scores:
        lines.extend(
            [
                "",
                "Heuristic evidence score",
                f"{report.scores['overall']} / 100 — {report.scores['label']}",
                "Not a benchmark of repository quality or agent success.",
            ]
        )

    lines.extend(["", "Recommended next steps"])
    if report.recommendations:
        lines.extend(f"{index}. {item}" for index, item in enumerate(report.recommendations, 1))
    else:
        lines.append("No high-priority gaps were identified by the supported checks.")

    value = "\n".join(lines) + "\n"
    redacted, count = redact_text(value)
    report.privacy.redactions_applied += count
    return redacted

