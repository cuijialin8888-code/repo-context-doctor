from __future__ import annotations

import pytest
from conftest import finding

from repo_context_doctor.models import Provenance, Status
from repo_context_doctor.scanner import scan_repository


def commands(report, kind: str) -> list[str]:
    return [item.command for item in report.verification_paths if item.kind == kind]


def test_node_scripts_use_declared_package_manager(make_repo):
    root = make_repo(
        {
            "package.json": (
                '{"name":"x","packageManager":"pnpm@10.0.0",'
                '"scripts":{"test":"vitest","lint":"eslint .","build":"tsc"}}'
            ),
            "pnpm-lock.yaml": "lockfileVersion: '9.0'\n",
        }
    )
    report = scan_repository(root)

    assert report.ecosystems == ["Node.js"]
    assert commands(report, "test") == ["pnpm test"]
    assert commands(report, "lint") == ["pnpm lint"]
    assert commands(report, "build") == ["pnpm build"]


def test_multiple_node_lockfiles_warn(make_repo):
    root = make_repo({"package.json": "{}", "package-lock.json": "{}", "yarn.lock": ""})
    report = scan_repository(root)

    assert finding(report, "dependencies.node-lockfiles").status is Status.WARN


def test_declared_manager_mismatch_warns(make_repo):
    root = make_repo({"package.json": '{"packageManager":"pnpm@10"}', "package-lock.json": "{}"})
    report = scan_repository(root)

    assert finding(report, "dependencies.package-manager-declaration").status is Status.WARN


@pytest.mark.parametrize("lock_name", ["pylock.toml", "pylock.ci.toml"])
def test_standard_python_lockfile_is_detected(make_repo, lock_name):
    root = make_repo(
        {
            "pyproject.toml": "[project]\nname='x'\nversion='0.1.0'\n",
            lock_name: "lock-version = '1.0'\n",
        }
    )
    report = scan_repository(root)

    lock_finding = finding(report, "dependencies.lock-signal")
    assert lock_finding.status is Status.PASS
    assert lock_finding.source_paths == (lock_name,)


def test_fixture_lockfiles_do_not_change_repository_reproducibility(make_repo):
    root = make_repo(
        {
            "pyproject.toml": "[project]\nname='x'\nversion='0.1.0'\n",
            "tests/fixtures/node/package-lock.json": "{}",
            "testdata/python/pylock.toml": "lock-version = '1.0'\n",
        }
    )
    report = scan_repository(root)

    assert finding(report, "dependencies.lock-signal").status is Status.INFO


def test_malformed_package_json_fails_without_crashing(make_repo):
    root = make_repo({"package.json": "{"})
    report = scan_repository(root)

    assert any(
        item.status is Status.FAIL and item.source_paths == ("package.json",)
        for item in report.findings
    )


def test_python_tool_configs_create_inferred_commands(make_repo):
    root = make_repo(
        {
            "pyproject.toml": (
                "[project]\nname='x'\nversion='0.1.0'\n"
                "[tool.pytest.ini_options]\naddopts='-q'\n"
                "[tool.ruff]\nline-length=100\n"
                "[tool.mypy]\nstrict=true\n"
            )
        }
    )
    report = scan_repository(root)

    assert {item.command for item in report.verification_paths} >= {
        "pytest",
        "ruff check .",
        "mypy .",
    }
    assert all(item.provenance is Provenance.INFERRED for item in report.verification_paths)


def test_malformed_pyproject_fails_without_crashing(make_repo):
    root = make_repo({"pyproject.toml": "[project\n"})
    report = scan_repository(root)

    assert any(
        item.status is Status.FAIL and item.source_paths == ("pyproject.toml",)
        for item in report.findings
    )


def test_rust_commands_are_clearly_inferred(make_repo):
    root = make_repo({"Cargo.toml": "[package]\nname='x'\nversion='0.1.0'\n"})
    report = scan_repository(root)

    assert commands(report, "test") == ["cargo test"]
    assert all(item.provenance is Provenance.INFERRED for item in report.verification_paths)


def test_go_commands_are_clearly_inferred(make_repo):
    root = make_repo({"go.mod": "module example.com/x\n\ngo 1.24\n"})
    report = scan_repository(root)

    assert commands(report, "test") == ["go test ./..."]
    assert commands(report, "build") == ["go build ./..."]


def test_powershell_test_structure_does_not_fabricate_invocation(make_repo):
    root = make_repo(
        {"src/Tool.psm1": "function Get-X {}", "tests/Tool.Tests.ps1": "Describe 'x' {}"}
    )
    report = scan_repository(root)

    assert "PowerShell" in report.ecosystems
    assert not commands(report, "test")
    assert finding(report, "powershell.pester-structure").status is Status.INFO


def test_node_workspace_is_monorepo(make_repo):
    root = make_repo(
        {"package.json": '{"workspaces":["packages/*"]}', "packages/a/package.json": "{}"}
    )
    report = scan_repository(root)

    assert report.repository["monorepo"] is True
    assert finding(report, "repository.monorepo").status is Status.INFO


def test_nested_fixture_manifests_do_not_change_repository_ecosystem(make_repo):
    root = make_repo(
        {
            "pyproject.toml": "[project]\nname='x'\nversion='0.1.0'\n",
            "tests/fixtures/node/package.json": '{"scripts":{"test":"vitest"}}',
            "testdata/rust/Cargo.toml": "[package]\nname='fixture'\nversion='0.1.0'\n",
        }
    )
    report = scan_repository(root)

    assert report.ecosystems == ["Python"]
    assert all("fixtures" not in item.source_path for item in report.verification_paths)
    assert all("testdata" not in item.source_path for item in report.verification_paths)


def test_unsupported_ecosystem_is_presence_only(make_repo):
    root = make_repo({"pom.xml": "<project/>", "README.md": "Java project"})
    report = scan_repository(root)

    assert report.ecosystems == ["Java"]
    assert not report.verification_paths
