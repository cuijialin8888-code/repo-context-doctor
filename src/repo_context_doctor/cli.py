"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from repo_context_doctor.models import Status, TOOL_VERSION
from repo_context_doctor.privacy import redact_text
from repo_context_doctor.renderers.console import render_console
from repo_context_doctor.renderers.json_renderer import render_json
from repo_context_doctor.renderers.markdown import render_markdown
from repo_context_doctor.scanner import scan_repository
from repo_context_doctor.snapshot import ScanLimits


def _integer_at_least(value: str, *, minimum: int, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{name} must be an integer") from exc
    if parsed < minimum:
        raise argparse.ArgumentTypeError(f"{name} must be at least {minimum}")
    return parsed


def _max_depth(value: str) -> int:
    return _integer_at_least(value, minimum=0, name="--max-depth")


def _positive_limit(value: str) -> int:
    return _integer_at_least(value, minimum=1, name="scan limit")


def _gate_failures(report, threshold: str) -> list:
    statuses = {
        "none": set(),
        "fail": {Status.FAIL},
        "warn": {Status.FAIL, Status.WARN},
        "unknown": {Status.FAIL, Status.WARN, Status.UNKNOWN},
    }[threshold]
    return [finding for finding in report.findings if finding.status in statuses]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-context-doctor",
        description="Read-only evidence inventory for coding-agent context and verification paths.",
    )
    parser.add_argument(
        "path", nargs="?", default=".", help="Local repository directory (default: .)"
    )
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    output.add_argument("--markdown", action="store_true", help="Render Markdown")
    parser.add_argument("--output", type=Path, help="Write the report to this explicit path")
    parser.add_argument("--no-score", action="store_true", help="Omit the heuristic evidence score")
    parser.add_argument(
        "--fail-on",
        choices=("none", "fail", "warn", "unknown"),
        default="none",
        help="Return exit code 1 when findings reach this severity (default: none)",
    )
    parser.add_argument(
        "--max-depth",
        type=_max_depth,
        default=ScanLimits().max_depth,
        help="Maximum directory depth to inspect (default: 10)",
    )
    parser.add_argument(
        "--max-entries",
        type=_positive_limit,
        default=ScanLimits().max_entries,
        help="Maximum discovered entries (default: 20000)",
    )
    parser.add_argument(
        "--max-file-bytes",
        type=_positive_limit,
        default=ScanLimits().max_file_bytes,
        help="Maximum text file size to interpret (default: 262144)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show exception types for fatal errors"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {TOOL_VERSION}")
    return parser


def _render(args: argparse.Namespace, report) -> str:
    if args.json:
        return render_json(report)
    if args.markdown:
        return render_markdown(report)
    return render_console(report)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    target = Path(args.path)
    if not target.exists():
        parser.error(f"directory does not exist: {args.path}")
    if not target.is_dir():
        parser.error(f"path is not a directory: {args.path}")

    try:
        report = scan_repository(
            target,
            include_score=not args.no_score,
            limits=ScanLimits(
                max_depth=args.max_depth,
                max_entries=args.max_entries,
                max_file_bytes=args.max_file_bytes,
            ),
        )
        output = _render(args, report)
        if args.output:
            parent = args.output.parent
            if not parent.exists() or not parent.is_dir():
                parser.error(f"output parent directory does not exist: {parent}")
            args.output.write_text(output, encoding="utf-8", newline="\n")
            print(f"Report written to {args.output.name}")
        else:
            sys.stdout.write(output)
        failures = _gate_failures(report, args.fail_on)
        if failures:
            statuses = ", ".join(sorted({finding.status.value for finding in failures}))
            print(
                f"CI gate failed at --fail-on {args.fail_on}: "
                f"{len(failures)} finding(s) ({statuses})",
                file=sys.stderr,
            )
            return 1
        return 0
    except SystemExit:
        raise
    except Exception as exc:  # ordinary mode must not print a traceback
        message = f"fatal scan error: {exc}"
        if args.verbose:
            message = f"fatal scan error ({type(exc).__name__}): {exc}"
        safe, _ = redact_text(message)
        print(safe, file=sys.stderr)
        return 3
