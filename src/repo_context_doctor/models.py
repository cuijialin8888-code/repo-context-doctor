"""Shared immutable report models.

Detectors produce these models. Renderers only serialize them and never make
diagnostic decisions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

TOOL_NAME = "Repo Context Doctor"
TOOL_VERSION = "0.1.0"
SCHEMA_VERSION = "1"


class Status(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    INFO = "INFO"
    UNKNOWN = "UNKNOWN"


class Confidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Provenance(StrEnum):
    MANIFEST = "MANIFEST"
    INSTRUCTION = "INSTRUCTION"
    DOCUMENTATION = "DOCUMENTATION"
    CI = "CI"
    MAKEFILE = "MAKEFILE"
    INFERRED = "INFERRED"


class Category(StrEnum):
    AGENT_CONTEXT = "agent_context"
    VERIFICATION = "verification"
    AUTOMATION = "automation"
    REPRODUCIBILITY = "reproducibility"
    ORIENTATION = "orientation"
    REPOSITORY = "repository"
    PRIVACY = "privacy"


@dataclass(frozen=True, slots=True)
class Finding:
    id: str
    category: Category
    status: Status
    summary: str
    details: str
    evidence: str
    recommendation: str
    confidence: Confidence
    source_paths: tuple[str, ...] = ()
    provenance: Provenance | None = None


@dataclass(frozen=True, slots=True)
class InstructionSurface:
    path: str
    kind: str
    scope: str
    recognized_by: tuple[str, ...]
    precedence_note: str


@dataclass(frozen=True, slots=True)
class VerificationPath:
    kind: str
    command: str
    provenance: Provenance
    confidence: Confidence
    source_path: str
    evidence: str


@dataclass(frozen=True, slots=True)
class CategoryScore:
    id: str
    label: str
    weight: int
    score: int
    rationale: str


@dataclass(slots=True)
class PrivacySummary:
    sensitive_files_skipped: int = 0
    oversized_files_skipped: int = 0
    undecodable_files_skipped: int = 0
    redactions_applied: int = 0
    relative_paths_only: bool = True


@dataclass(slots=True)
class ScanReport:
    timestamp: str
    repository: dict[str, Any]
    ecosystems: list[str]
    instruction_surfaces: list[InstructionSurface]
    verification_paths: list[VerificationPath]
    findings: list[Finding]
    scores: dict[str, Any] | None
    summary: dict[str, int]
    recommendations: list[str]
    privacy: PrivacySummary
    scan: dict[str, Any]
    tool: dict[str, str] = field(
        default_factory=lambda: {"name": TOOL_NAME, "version": TOOL_VERSION}
    )
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation with a stable field order."""

        raw = asdict(self)
        return {
            "tool": raw["tool"],
            "schema_version": raw["schema_version"],
            "timestamp": raw["timestamp"],
            "repository": raw["repository"],
            "ecosystems": raw["ecosystems"],
            "instruction_surfaces": raw["instruction_surfaces"],
            "verification_paths": raw["verification_paths"],
            "findings": raw["findings"],
            "scores": raw["scores"],
            "summary": raw["summary"],
            "recommendations": raw["recommendations"],
            "privacy": raw["privacy"],
            "scan": raw["scan"],
        }
