"""SARIF 2.1.0 report renderer."""

from __future__ import annotations

import json
from typing import Any

from repo_context_doctor.models import SCHEMA_VERSION, TOOL_NAME, TOOL_VERSION, ScanReport, Status
from repo_context_doctor.privacy import redact_text

SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"


def _level(status: Status) -> str:
    return {
        Status.FAIL: "error",
        Status.WARN: "warning",
        Status.UNKNOWN: "warning",
        Status.INFO: "note",
        Status.PASS: "note",
    }[status]


def _locations(source_paths: tuple[str, ...]) -> list[dict[str, Any]]:
    return [
        {"physicalLocation": {"artifactLocation": {"uri": path.replace("\\", "/")}}}
        for path in source_paths
    ]


def render_sarif(report: ScanReport) -> str:
    """Render findings for SARIF consumers without changing diagnostic decisions."""

    rules: list[dict[str, Any]] = []
    seen_rules: set[str] = set()
    results: list[dict[str, Any]] = []
    for finding in report.findings:
        if finding.id not in seen_rules:
            rules.append(
                {
                    "id": finding.id,
                    "name": finding.summary,
                    "shortDescription": {"text": finding.summary},
                    "fullDescription": {"text": finding.details},
                    "defaultConfiguration": {"level": _level(finding.status)},
                    "help": {"text": finding.recommendation or finding.details},
                }
            )
            seen_rules.add(finding.id)

        result: dict[str, Any] = {
            "ruleId": finding.id,
            "level": _level(finding.status),
            "message": {
                "text": finding.details or finding.summary,
            },
            "properties": {
                "status": finding.status.value,
                "category": finding.category.value,
                "confidence": finding.confidence.value,
                "provenance": finding.provenance.value if finding.provenance else None,
                "evidence": finding.evidence,
                "recommendation": finding.recommendation,
            },
        }
        locations = _locations(finding.source_paths)
        if locations:
            result["locations"] = locations
        results.append(result)

    payload = {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": TOOL_NAME,
                        "informationUri": "https://github.com/cuijialin8888-code/repo-context-doctor",
                        "semanticVersion": TOOL_VERSION,
                        "rules": rules,
                    }
                },
                "results": results,
                "properties": {
                    "schema_version": SCHEMA_VERSION,
                    "repository": report.repository.get("name"),
                    "read_only": True,
                },
            }
        ],
    }
    value = json.dumps(payload, ensure_ascii=False, indent=2)
    redacted, count = redact_text(value)
    report.privacy.redactions_applied += count
    return redacted + "\n"
