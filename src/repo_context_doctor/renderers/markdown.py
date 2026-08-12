"""Markdown report renderer."""

from __future__ import annotations

from collections import defaultdict

from repo_context_doctor.models import TOOL_NAME, TOOL_VERSION, ScanReport
from repo_context_doctor.privacy import redact_text


def render_markdown(report: ScanReport) -> str:
    lines = [f"# {TOOL_NAME} {TOOL_VERSION}", "", "## Repository", ""]
    lines.extend(
        [
            f"- Name: `{report.repository['name']}`",
            f"- Ecosystems: {', '.join(report.ecosystems)}",
            f"- Git repository: {'Yes' if report.repository['is_git'] else 'No'}",
            f"- Monorepo: {'Yes' if report.repository['monorepo'] else 'No'}",
        ]
    )

    grouped: dict[str, list] = defaultdict(list)
    for finding in report.findings:
        grouped[finding.category.value].append(finding)
    for category, findings in grouped.items():
        lines.extend(["", f"## {category.replace('_', ' ').title()}", ""])
        for finding in findings:
            lines.append(f"- **{finding.status.value}** — {finding.summary}")
            if finding.evidence:
                lines.append(f"  - Evidence: {finding.evidence}")
            if finding.recommendation:
                lines.append(f"  - Recommendation: {finding.recommendation}")

    if report.verification_paths:
        lines.extend(
            [
                "",
                "## Verification paths",
                "",
                "These commands were discovered but not executed.",
                "",
            ]
        )
        lines.append("| Kind | Command | Provenance | Confidence | Source |")
        lines.append("|---|---|---|---|---|")
        for path in report.verification_paths:
            command = path.command.replace("|", "\\|")
            lines.append(
                f"| {path.kind} | `{command}` | {path.provenance.value} | "
                f"{path.confidence.value} | `{path.source_path}` |"
            )

    if report.scores:
        lines.extend(
            [
                "",
                "## Heuristic evidence score",
                "",
                f"**{report.scores['overall']} / 100 — {report.scores['label']}**",
                "",
                "This is not a benchmark of repository quality or coding-agent success.",
            ]
        )

    lines.extend(["", "## Recommended next steps", ""])
    if report.recommendations:
        lines.extend(f"{index}. {item}" for index, item in enumerate(report.recommendations, 1))
    else:
        lines.append("No high-priority gaps were identified by the supported checks.")

    value = "\n".join(lines) + "\n"
    redacted, count = redact_text(value)
    report.privacy.redactions_applied += count
    return redacted
