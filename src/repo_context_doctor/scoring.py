"""Transparent, capped heuristic scoring."""

from __future__ import annotations

from repo_context_doctor.models import CategoryScore


def _category(id_: str, label: str, weight: int, score: int, rationale: str) -> CategoryScore:
    return CategoryScore(id_, label, weight, min(100, max(0, round(score))), rationale)


def calculate_scores(facts: dict[str, bool]) -> dict[str, object]:
    """Calculate fixed category scores without counting duplicate files."""

    context = (
        (60 if facts.get("instruction_any") else 0)
        + (25 if facts.get("instruction_root") else 0)
        + (15 if facts.get("scoped") else 0)
    )
    verification = (
        (40 if facts.get("explicit_test") else 20 if facts.get("inferred_test") else 0)
        + (20 if facts.get("explicit_lint") else 10 if facts.get("inferred_lint") else 0)
        + (20 if facts.get("explicit_build") else 10 if facts.get("inferred_build") else 0)
        + (
            20
            if facts.get("explicit_type_or_format")
            else 10
            if facts.get("inferred_type_or_format")
            else 0
        )
    )
    automation = (50 if facts.get("ci_detected") else 0) + (
        50 if facts.get("ci_verification") else 0
    )
    reproducibility = (
        (35 if facts.get("manifest_present") else 0)
        + (40 if facts.get("lock_present") else 0)
        + (25 if facts.get("manager_consistent") else 0)
    )
    orientation = (
        (45 if facts.get("readme") else 0)
        + (25 if facts.get("supporting_docs") else 0)
        + (15 if facts.get("source_dirs") else 0)
        + (15 if facts.get("test_dirs") else 0)
    )

    categories = [
        _category("agent_context", "Agent context", 30, context, "Capped presence, root, and scope signals."),
        _category(
            "verification",
            "Verification discoverability",
            30,
            verification,
            "Explicit commands receive more credit than ecosystem inference.",
        ),
        _category("automation", "Automation / CI", 15, automation, "CI presence and verification evidence."),
        _category(
            "reproducibility",
            "Dependency reproducibility",
            15,
            reproducibility,
            "Manifest, lockfile, and package-manager consistency signals.",
        ),
        _category(
            "orientation",
            "Repository orientation",
            10,
            orientation,
            "README, supporting docs, and conventional source/test entry points.",
        ),
    ]
    overall = round(sum(item.score * item.weight for item in categories) / 100)
    if overall >= 85:
        label = "STRONG EVIDENCE"
    elif overall >= 65:
        label = "PARTIAL EVIDENCE"
    else:
        label = "LIMITED EVIDENCE"
    return {
        "overall": overall,
        "label": label,
        "heuristic": True,
        "benchmark_of_repository_quality": False,
        "categories": [
            {
                "id": item.id,
                "label": item.label,
                "weight": item.weight,
                "score": item.score,
                "rationale": item.rationale,
            }
            for item in categories
        ],
    }

