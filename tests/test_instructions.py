from __future__ import annotations

from conftest import finding

from repo_context_doctor.models import Status
from repo_context_doctor.scanner import scan_repository


def surface(report, path: str):
    return next(item for item in report.instruction_surfaces if item.path == path)


def test_root_agents_md_is_inventoried(make_repo):
    root = make_repo({"AGENTS.md": "# Instructions\n"})
    report = scan_repository(root)

    item = surface(report, "AGENTS.md")
    assert item.scope == "repository"
    assert item.recognized_by == ("OpenAI Codex", "GitHub Copilot", "Cursor")
    assert finding(report, "instructions.inventory").status is Status.PASS


def test_nested_agents_md_builds_scope_map(make_repo):
    root = make_repo({"AGENTS.md": "root", "src/AGENTS.md": "src", "tests/AGENTS.md": "tests"})
    report = scan_repository(root)

    assert surface(report, "src/AGENTS.md").scope == "src/**"
    assert surface(report, "tests/AGENTS.md").scope == "tests/**"
    context = next(item for item in report.scores["categories"] if item["id"] == "agent_context")
    assert context["score"] == 100


def test_agents_override_shadows_codex_file_in_same_directory(make_repo):
    root = make_repo({"services/AGENTS.md": "base", "services/AGENTS.override.md": "override"})
    report = scan_repository(root)

    assert "Shadowed for Codex" in surface(report, "services/AGENTS.md").precedence_note
    assert surface(report, "services/AGENTS.override.md").recognized_by == ("OpenAI Codex",)


def test_multiple_surfaces_are_info_not_conflict(make_repo):
    root = make_repo({"AGENTS.md": "a", "CLAUDE.md": "c", "GEMINI.md": "g"})
    report = scan_repository(root)

    item = finding(report, "instructions.multiple-surfaces")
    assert item.status is Status.INFO
    assert not any(f.status is Status.FAIL for f in report.findings)


def test_copilot_path_scope_reads_apply_to(make_repo):
    root = make_repo(
        {
            ".github/instructions/python.instructions.md": (
                "---\napplyTo: '**/*.py'\n---\nUse Ruff.\n"
            )
        }
    )
    report = scan_repository(root)

    assert surface(report, ".github/instructions/python.instructions.md").scope == "**/*.py"
    assert not any(item.id == "instructions.copilot-apply-to" for item in report.findings)


def test_copilot_path_scope_missing_apply_to_is_fail(make_repo):
    root = make_repo({".github/instructions/python.instructions.md": "Use Ruff.\n"})
    report = scan_repository(root)

    assert finding(report, "instructions.copilot-apply-to").status is Status.FAIL


def test_cursor_rule_reports_globs(make_repo):
    root = make_repo(
        {
            ".cursor/rules/python.mdc": (
                "---\ndescription: Python rules\nglobs: '**/*.py'\n"
                "alwaysApply: false\n---\nUse Ruff.\n"
            )
        }
    )
    report = scan_repository(root)

    item = surface(report, ".cursor/rules/python.mdc")
    assert item.kind == "cursor_rule"
    assert item.scope == "**/*.py"


def test_cursor_always_apply_rule_is_repository_scoped(make_repo):
    root = make_repo({".cursor/rules/all.mdc": "---\nalwaysApply: true\n---\nRule.\n"})
    report = scan_repository(root)

    assert surface(report, ".cursor/rules/all.mdc").scope == "repository"


def test_claude_rule_reads_paths_list(make_repo):
    root = make_repo(
        {
            ".claude/rules/api.md": (
                "---\npaths:\n  - 'src/api/**/*.py'\n  - 'tests/api/**/*.py'\n"
                "---\nUse API conventions.\n"
            )
        }
    )
    report = scan_repository(root)

    assert surface(report, ".claude/rules/api.md").scope == "src/api/**/*.py, tests/api/**/*.py"


def test_nested_gemini_scope_is_reported(make_repo):
    root = make_repo({"GEMINI.md": "root", "packages/api/GEMINI.md": "api"})
    report = scan_repository(root)

    assert surface(report, "packages/api/GEMINI.md").scope == "packages/api/**"
