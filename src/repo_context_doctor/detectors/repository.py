"""Repository orientation signals."""

from __future__ import annotations

from repo_context_doctor.models import Category, Confidence, Finding, Status
from repo_context_doctor.snapshot import RepositorySnapshot

_README_NAMES = {"readme", "readme.md", "readme.rst", "readme.txt"}
_SOURCE_DIRS = {"app", "cmd", "internal", "lib", "packages", "scripts", "src"}
_TEST_DIRS = {"__tests__", "integration", "spec", "test", "tests"}


def detect_repository(snapshot: RepositorySnapshot) -> tuple[list[Finding], dict[str, bool]]:
    files_lower = {path.lower(): path for path in snapshot.files}
    top_files = {path for path in files_lower if "/" not in path}
    top_dirs = {path.lower() for path in snapshot.directories if "/" not in path}

    readme = next((files_lower[name] for name in _README_NAMES if name in top_files), None)
    contributing = files_lower.get("contributing.md")
    docs = "docs" in top_dirs
    source_dirs = sorted(_SOURCE_DIRS & top_dirs)
    test_dirs = sorted(_TEST_DIRS & top_dirs)

    findings: list[Finding] = []
    if readme:
        findings.append(
            Finding(
                "orientation.readme",
                Category.ORIENTATION,
                Status.PASS,
                "Repository README detected",
                "A root README gives humans and coding agents a shared orientation entry point.",
                readme,
                "Keep setup and validation commands synchronized with manifests and CI.",
                Confidence.HIGH,
                (readme,),
            )
        )
    else:
        findings.append(
            Finding(
                "orientation.readme",
                Category.ORIENTATION,
                Status.WARN,
                "Root README was not detected",
                "The repository may still be valid, but its primary orientation path is unclear.",
                "No supported README filename was present at repository root.",
                "Add a concise README describing purpose, setup, and validation when appropriate.",
                Confidence.HIGH,
            )
        )

    secondary = [path for path in (contributing, "docs" if docs else None) if path]
    findings.append(
        Finding(
            "orientation.supporting-docs",
            Category.ORIENTATION,
            Status.PASS if secondary else Status.INFO,
            "Supporting contributor or docs entry point detected"
            if secondary
            else "No supporting contributor or docs entry point detected",
            "Supporting documentation can reduce repeated repository exploration.",
            ", ".join(secondary) if secondary else "No CONTRIBUTING.md or root docs/ directory.",
            "Document non-obvious contribution or architecture workflows when they exist.",
            Confidence.HIGH,
            tuple(secondary),
        )
    )

    if source_dirs or test_dirs:
        evidence_parts = []
        if source_dirs:
            evidence_parts.append("source: " + ", ".join(source_dirs))
        if test_dirs:
            evidence_parts.append("tests: " + ", ".join(test_dirs))
        findings.append(
            Finding(
                "orientation.structure",
                Category.ORIENTATION,
                Status.INFO,
                "Conventional source or test directories detected",
                "Directory names are orientation signals only; source contents were not analyzed.",
                "; ".join(evidence_parts),
                "No action is required when the current layout is already documented.",
                Confidence.MEDIUM,
                tuple(source_dirs + test_dirs),
            )
        )

    return findings, {
        "readme": bool(readme),
        "supporting_docs": bool(secondary),
        "source_dirs": bool(source_dirs),
        "test_dirs": bool(test_dirs),
    }
