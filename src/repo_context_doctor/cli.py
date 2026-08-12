"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from repo_context_doctor.models import TOOL_VERSION
from repo_context_doctor.privacy import redact_text
from repo_context_doctor.renderers.console import render_console
from repo_context_doctor.renderers.json_renderer import render_json
from repo_context_doctor.renderers.markdown import render_markdown
from repo_context_doctor.scanner import scan_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-context-doctor",
        description="Read-only evidence inventory for coding-agent context and verification paths.",
    )
    parser.add_argument("path", nargs="?", default=".", help="Local repository directory (default: .)")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="Render machine-readable JSON")
    output.add_argument("--markdown", action="store_true", help="Render Markdown")
    parser.add_argument("--output", type=Path, help="Write the report to this explicit path")
    parser.add_argument("--no-score", action="store_true", help="Omit the heuristic evidence score")
    parser.add_argument("--verbose", action="store_true", help="Show exception types for fatal errors")
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
        report = scan_repository(target, include_score=not args.no_score)
        output = _render(args, report)
        if args.output:
            parent = args.output.parent
            if not parent.exists() or not parent.is_dir():
                parser.error(f"output parent directory does not exist: {parent}")
            args.output.write_text(output, encoding="utf-8", newline="\n")
            print(f"Report written to {args.output.name}")
        else:
            sys.stdout.write(output)
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

