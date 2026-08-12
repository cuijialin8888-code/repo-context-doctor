from __future__ import annotations

import json

import pytest

from repo_context_doctor.cli import main


def test_cli_json_output(make_repo, capsys):
    root = make_repo({"README.md": "# Example"})
    code = main([str(root), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    assert json.loads(captured.out)["repository"]["name"] == "repository"
    assert captured.err == ""


def test_cli_markdown_output(make_repo, capsys):
    root = make_repo({"README.md": "# Example"})
    code = main([str(root), "--markdown"])

    assert code == 0
    assert capsys.readouterr().out.startswith("# Repo Context Doctor")


def test_cli_writes_only_explicit_output(make_repo, tmp_path, capsys):
    root = make_repo({"README.md": "# Example"})
    output = tmp_path / "report.json"
    before = {path.relative_to(root) for path in root.rglob("*")}

    code = main([str(root), "--json", "--output", str(output)])
    after = {path.relative_to(root) for path in root.rglob("*")}

    assert code == 0
    assert before == after
    assert json.loads(output.read_text(encoding="utf-8"))["schema_version"] == "1"
    assert "Report written to report.json" in capsys.readouterr().out


def test_cli_no_score(make_repo, capsys):
    root = make_repo({"README.md": "# Example"})
    assert main([str(root), "--json", "--no-score"]) == 0
    assert json.loads(capsys.readouterr().out)["scores"] is None


def test_cli_nonexistent_directory_is_input_error(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main([str(tmp_path / "missing")])
    assert exc.value.code == 2


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == "repo-context-doctor 0.1.0"
