from __future__ import annotations

import json

from conftest import category_score

from repo_context_doctor.renderers.console import render_console
from repo_context_doctor.renderers.json_renderer import render_json
from repo_context_doctor.renderers.markdown import render_markdown
from repo_context_doctor.scanner import scan_repository


def test_empty_repository_does_not_crash(make_repo):
    root = make_repo({})
    report = scan_repository(root)

    assert report.ecosystems == ["Generic"]
    assert report.summary["FAIL"] == 0


def test_json_is_parseable_and_has_schema_fields(make_repo):
    root = make_repo({"README.md": "# Example\n"})
    payload = json.loads(render_json(scan_repository(root)))

    assert payload["tool"]["name"] == "Repo Context Doctor"
    assert payload["schema_version"] == "1"
    assert isinstance(payload["findings"], list)
    assert payload["scan"]["project_commands_executed"] is False


def test_markdown_is_readable(make_repo):
    root = make_repo({"README.md": "# Example\n", "AGENTS.md": "# Rules\n"})
    output = render_markdown(scan_repository(root))

    assert output.startswith("# Repo Context Doctor 0.1.0")
    assert "## Verification" in output
    assert "## Recommended next steps" in output


def test_console_has_stable_summary(make_repo):
    root = make_repo({"README.md": "# Example\n"})
    output = render_console(scan_repository(root))

    assert "PASS:" in output
    assert "WARN:" in output
    assert "UNKNOWN:" in output
    assert "Not a benchmark of repository quality or agent success." in output


def test_core_report_is_deterministic_except_timestamp(make_repo):
    root = make_repo({"package.json": '{"scripts":{"test":"vitest"}}', "AGENTS.md": "rules"})
    first = scan_repository(root).to_dict()
    second = scan_repository(root).to_dict()
    first.pop("timestamp")
    second.pop("timestamp")

    assert first == second


def test_multiple_root_instruction_files_do_not_game_context_score(make_repo):
    one = make_repo({"AGENTS.md": "a"}, name="one")
    many = make_repo({"AGENTS.md": "a", "CLAUDE.md": "c", "GEMINI.md": "g"}, name="many")

    assert category_score(scan_repository(one), "agent_context") == category_score(
        scan_repository(many), "agent_context"
    )


def test_no_score_omits_score_object(make_repo):
    root = make_repo({"README.md": "# Example"})
    report = scan_repository(root, include_score=False)

    assert report.scores is None
