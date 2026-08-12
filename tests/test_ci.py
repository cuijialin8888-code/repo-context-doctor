from __future__ import annotations

from conftest import finding

from repo_context_doctor.models import Provenance, Status
from repo_context_doctor.scanner import scan_repository


def test_github_actions_run_steps_become_verification_paths(make_repo):
    root = make_repo(
        {
            ".github/workflows/ci.yml": (
                "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
                "    steps:\n      - run: python -m pytest -q\n"
                "      - run: |\n          ruff check .\n          ruff format --check .\n"
            )
        }
    )
    report = scan_repository(root)

    assert {item.command for item in report.verification_paths} == {
        "python -m pytest -q",
        "ruff check .",
        "ruff format --check .",
    }
    assert all(item.provenance is Provenance.CI for item in report.verification_paths)
    assert finding(report, "verification.test").status is Status.PASS


def test_other_ci_is_presence_only(make_repo):
    root = make_repo({".gitlab-ci.yml": "test:\n  script: pytest\n"})
    report = scan_repository(root)

    assert finding(report, "automation.ci").status is Status.PASS
    assert not report.verification_paths


def test_github_actions_without_known_commands_is_info(make_repo):
    root = make_repo(
        {".github/workflows/ci.yml": "jobs:\n  noop:\n    steps:\n      - run: echo ok\n"}
    )
    report = scan_repository(root)

    assert finding(report, "automation.ci-verification").status is Status.INFO
