from __future__ import annotations

import json
import os

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


def test_cli_sarif_output_is_machine_readable(make_repo, capsys):
    root = make_repo({})

    code = main([str(root), "--sarif"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["version"] == "2.1.0"
    assert payload["runs"][0]["tool"]["driver"]["name"] == "Repo Context Doctor"
    assert payload["runs"][0]["properties"]["read_only"] is True


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


def test_cli_fail_on_warn_keeps_json_parseable(make_repo, capsys):
    root = make_repo({})

    code = main([str(root), "--json", "--fail-on", "warn"])
    captured = capsys.readouterr()

    assert code == 1
    assert json.loads(captured.out)["summary"]["WARN"] > 0
    assert "CI gate failed at --fail-on warn" in captured.err


def test_cli_fail_on_fail_ignores_warnings(make_repo, capsys):
    root = make_repo({"README.md": "# Example"})

    code = main([str(root), "--json", "--fail-on", "fail"])
    captured = capsys.readouterr()

    assert code == 0
    assert json.loads(captured.out)["summary"]["FAIL"] == 0
    assert captured.err == ""


def test_cli_scan_limits_are_reported(make_repo, capsys):
    root = make_repo({"nested/AGENTS.md": "rules"})

    assert (
        main(
            [
                str(root),
                "--json",
                "--max-depth",
                "0",
                "--max-entries",
                "100",
                "--max-file-bytes",
                "1024",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["scan"]["limits"] == {
        "max_depth": 0,
        "max_entries": 100,
        "max_file_bytes": 1024,
    }


def test_cli_rejects_invalid_scan_limit(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main([str(tmp_path), "--max-entries", "0"])
    assert exc.value.code == 2


def test_cli_nonexistent_directory_is_input_error(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main([str(tmp_path / "missing")])
    assert exc.value.code == 2


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == "repo-context-doctor 0.1.0"


def test_cli_cannot_overwrite_repository_sources(make_repo):
    root = make_repo({"AGENTS.md": "keep these instructions"})
    output = root / "AGENTS.md"
    before = output.read_bytes()
    with pytest.raises(SystemExit) as exc:
        main([str(root), "--json", "--output", str(output)])
    assert exc.value.code == 2
    assert output.read_bytes() == before


def test_cli_can_create_new_report_but_not_git_metadata(make_repo, capsys):
    root = make_repo({"README.md": "# Example", ".git/config": "preserve"})
    output = root / "report.json"
    assert main([str(root), "--json", "--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["schema_version"] == "1"
    capsys.readouterr()
    with pytest.raises(SystemExit) as exc:
        main([str(root), "--output", str(root / ".git" / "new-report.json")])
    assert exc.value.code == 2
    assert not (root / ".git" / "new-report.json").exists()


def test_cli_cannot_follow_output_symlink(make_repo, tmp_path):
    root = make_repo({"README.md": "# Example"})
    protected = tmp_path / "original.txt"
    protected.write_text("preserve", encoding="utf-8")
    output = tmp_path / "link.json"
    try:
        output.symlink_to(protected)
    except OSError:
        pytest.skip("symbolic links unavailable")
    with pytest.raises(SystemExit) as exc:
        main([str(root), "--output", str(output)])
    assert exc.value.code == 2
    assert protected.read_text(encoding="utf-8") == "preserve"


@pytest.mark.parametrize("source", ["README.md", "AGENTS.md", ".git/config"])
def test_cli_cannot_overwrite_sources_through_external_hard_link(
    make_repo, tmp_path, monkeypatch, capsys, source
):
    root = make_repo({source: "preserve these source bytes"})
    protected = root / source
    output = tmp_path / "external-report.json"
    try:
        os.link(protected, output)
    except OSError:
        pytest.skip("hard links unavailable")
    before = protected.read_bytes()

    def unexpected_scan(*args, **kwargs):
        pytest.fail("invalid output must be rejected before scanning")

    monkeypatch.setattr("repo_context_doctor.cli.scan_repository", unexpected_scan)
    with pytest.raises(SystemExit) as exc:
        main([str(root), "--json", "--output", str(output)])

    assert exc.value.code == 2
    assert protected.read_bytes() == before
    assert output.read_bytes() == before
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "hard links" in captured.err


def test_cli_can_replace_regular_external_report(make_repo, tmp_path, capsys):
    root = make_repo({"README.md": "# Example"})
    output = tmp_path / "existing-report.json"
    output.write_text("old report", encoding="utf-8")

    assert main([str(root), "--json", "--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["schema_version"] == "1"
    assert root.joinpath("README.md").read_text(encoding="utf-8") == "# Example"
    assert "Report written to existing-report.json" in capsys.readouterr().out
