"""JSON report renderer."""

from __future__ import annotations

import json

from repo_context_doctor.models import ScanReport
from repo_context_doctor.privacy import redact_text


def render_json(report: ScanReport) -> str:
    value = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    redacted, count = redact_text(value)
    report.privacy.redactions_applied += count
    if count:
        value = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
        redacted, _ = redact_text(value)
    return redacted + "\n"
