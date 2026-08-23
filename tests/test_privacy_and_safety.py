from __future__ import annotations

import ast
import hashlib
import shutil
from pathlib import Path

import pytest
from conftest import finding

from repo_context_doctor.models import Status
from repo_context_doctor.privacy import CANARY, redact_text, sanitize_excerpt
from repo_context_doctor.renderers.console import render_console
from repo_context_doctor.renderers.json_renderer import render_json
from repo_context_doctor.renderers.markdown import render_markdown
from repo_context_doctor.scanner import scan_repository
from repo_context_doctor.snapshot import ScanLimits


def tree_state(root: Path) -> dict[str, tuple[int, int, str]]:
    result = {}
    for path in sorted(
        item for item in root.rglob("*") if item.is_file() and not item.is_symlink()
    ):
        stat = path.stat()
        result[path.relative_to(root).as_posix()] = (
            stat.st_size,
            stat.st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    return result


def test_scan_is_read_only_for_content_tree_and_mtime(make_repo):
    root = make_repo(
        {
            "README.md": "# Example\n",
            "AGENTS.md": "Run tests.\n",
            "package.json": '{"scripts":{"test":"vitest"}}',
            "src/app.js": "export const x = 1;\n",
        }
    )
    before = tree_state(root)
    report = scan_repository(root)
    after = tree_state(root)

    assert before == after
    assert report.scan["read_only"] is True
    assert report.scan["project_commands_executed"] is False
    assert report.scan["network_used"] is False


def test_sensitive_files_are_counted_but_never_decoded(make_repo):
    root = make_repo({".env": b"\xff\xfeSECRET", "README.md": "safe"})
    report = scan_repository(root)

    assert report.privacy.sensitive_files_skipped == 1
    assert report.privacy.undecodable_files_skipped == 0


def test_canary_never_leaks_to_any_renderer(tmp_path):
    source = Path(__file__).parent / "fixtures" / "privacy_canary"
    root = tmp_path / "隐私夹具"
    shutil.copytree(source, root)

    outputs = []
    for renderer in (render_console, render_json, render_markdown):
        outputs.append(renderer(scan_repository(root)))
    assert all(CANARY not in output for output in outputs)
    assert all("[REDACTED]" in output for output in outputs)


@pytest.mark.parametrize("prefix", ["ghp", "gho", "ghu", "ghs", "ghr"])
def test_github_token_families_are_redacted_without_assignment(prefix):
    token = f"{prefix}_FAKE1234567890"

    safe, count = redact_text(f"probe output: {token}")

    assert token not in safe
    assert safe == "probe output: [REDACTED]"
    assert count == 1


def test_fine_grained_github_token_is_redacted_without_assignment():
    token = "github_pat_FAKE_TOKEN_1234567890"

    safe, count = redact_text(f"probe output: {token}")

    assert token not in safe
    assert safe == "probe output: [REDACTED]"
    assert count == 1


def test_excerpt_redacts_before_truncating_at_a_token_boundary():
    token = "ghp_FAKE1234567890"

    safe, count = sanitize_excerpt(f"{'x' * 271} {token}", limit=280)

    assert token not in safe
    assert "ghp_" not in safe
    assert safe.endswith("…")
    assert count == 1


def test_absolute_repository_path_is_not_serialized(make_repo):
    root = make_repo({"README.md": "safe"}, name="中文 仓库")
    report = scan_repository(root)
    serialized = render_json(report)

    assert str(root.resolve()) not in serialized
    assert report.repository["name"] == "中文 仓库"
    assert report.repository["path"] == "."


def test_oversized_instruction_is_safely_skipped(make_repo):
    root = make_repo({"AGENTS.md": "x" * 300_000})
    report = scan_repository(root)

    assert report.privacy.oversized_files_skipped == 1
    assert finding(report, "scan.text-skipped").status is Status.UNKNOWN


def test_invalid_utf8_instruction_is_safely_skipped(make_repo):
    root = make_repo({"AGENTS.md": b"\xff\xfe\x00"})
    report = scan_repository(root)

    assert report.privacy.undecodable_files_skipped == 1
    assert finding(report, "scan.text-skipped").status is Status.UNKNOWN


def test_symlink_outside_root_is_not_followed(make_repo, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "package.json").write_text('{"scripts":{"test":"bad"}}', encoding="utf-8")
    root = make_repo({"README.md": "safe"})
    link = root / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    report = scan_repository(root)
    assert report.scan["symlinks_skipped"] == 1
    assert "Node.js" not in report.ecosystems


def test_entry_bound_returns_partial_unknown(make_repo):
    root = make_repo({f"files/{index}.txt": "x" for index in range(20)})
    report = scan_repository(root, limits=ScanLimits(max_entries=5))

    assert finding(report, "scan.bounds").status is Status.UNKNOWN


def test_runtime_package_has_no_network_or_command_execution_imports():
    source_root = Path(__file__).parents[1] / "src" / "repo_context_doctor"
    forbidden = {
        "asyncio.subprocess",
        "http.client",
        "requests",
        "socket",
        "subprocess",
        "urllib.request",
    }
    found = set()
    for path in source_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names if alias.name in forbidden)
            elif isinstance(node, ast.ImportFrom) and node.module in forbidden:
                found.add(node.module)
    assert found == set()
