# Repo Context Doctor

[![CI](https://github.com/cuijialin8888-code/repo-context-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/cuijialin8888-code/repo-context-doctor/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/cuijialin8888-code/repo-context-doctor)](https://github.com/cuijialin8888-code/repo-context-doctor/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A read-only, local evidence inventory for coding-agent instructions and repository verification paths.**

Repo Context Doctor shows what a coding agent can discover before it changes a repository:

- instruction surfaces and their scopes;
- test, lint, format, type-check, and build commands, with provenance and confidence;
- CI, dependency, lockfile, ecosystem, and repository-orientation evidence;
- clear `PASS`, `WARN`, `FAIL`, `INFO`, and `UNKNOWN` findings;
- Console, JSON, and Markdown reports.

It is deterministic, has no runtime dependencies, does not call an LLM or API, does not use the network, and never executes commands found in the target repository.

[中文说明](README.zh-CN.md)

## Quick start

Python 3.11 or newer is required. Install from a tagged GitHub release:

```bash
python -m pip install "repo-context-doctor @ git+https://github.com/cuijialin8888-code/repo-context-doctor.git@v0.1.0"
repo-context-doctor .
```

Or work from a source checkout:

```bash
git clone https://github.com/cuijialin8888-code/repo-context-doctor.git
cd repo-context-doctor
python -m venv .venv
python -m pip install ".[dev]"
repo-context-doctor .
```

The commands above install the tool. A scan itself is local and offline.

## Usage

```text
repo-context-doctor [PATH] [--json | --markdown] [--output FILE] [--no-score]
```

```bash
# Concise terminal report
repo-context-doctor .

# Machine-readable report
repo-context-doctor . --json

# Write a Markdown artifact (the only requested target-side write)
repo-context-doctor . --markdown --output context-report.md

# Inventory without the optional heuristic score
repo-context-doctor . --no-score
```

Exit code `0` means the scan completed, even when findings include gaps. Argument errors use `2`; an unexpected fatal scan error uses `3`. Findings and the optional score are evidence, not a CI quality gate.

## What the report looks like

```text
# Repo Context Doctor 0.1.0

Repository
Name:          example-project
Ecosystems:    Python
Git:           Yes
Monorepo:      No

Agent Context
[PASS] Found coding-agent instruction surfaces

Verification paths (not executed)
- test: pytest [MANIFEST, HIGH] (pyproject.toml)
- lint: ruff check . [INSTRUCTION, HIGH] (AGENTS.md)
```

Every verification path includes a source path, evidence origin, and confidence level. Commands are reported as strings and are never run.

## Supported evidence

Repo Context Doctor inventories common instruction surfaces, including:

- `AGENTS.md` and `AGENTS.override.md` from root to nested scopes;
- `CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md`, and `.claude/rules/*.md`;
- `GEMINI.md`;
- `.github/copilot-instructions.md` and scoped `.github/instructions/*.instructions.md`;
- `.cursor/rules/*.mdc` and legacy `.cursorrules`.

It has deeper verification detection for Python, Node.js, Rust, Go, and PowerShell, plus generic manifest and CI signals for mixed repositories. Sources are distinguished as `MANIFEST`, `INSTRUCTION`, `DOCUMENTATION`, `CI`, `MAKEFILE`, or `INFERRED`.

See [supported signals](docs/supported-signals.md) and the [report format](docs/report-format.md) for exact behavior.

## Safety and privacy

The scanner is intentionally bounded:

- target files are read only; report files are written only with explicit `--output`;
- repository commands are never executed;
- symlinks are not followed;
- dependency, build, cache, VCS, and common secret directories are excluded;
- likely secret files and values are skipped or redacted;
- report source paths are repository-relative;
- large and undecodable text files are reported as `UNKNOWN`, not silently treated as absent.

This is defense in depth, not a secret-scanning or sandbox product. Review a report before publishing it when the target repository is sensitive.

## Heuristic score

The optional score summarizes supported evidence in five capped categories: agent context (30%), verification discoverability (30%), automation (15%), dependency reproducibility (15%), and repository orientation (10%). Duplicate instruction files do not stack unlimited credit, and explicit commands receive more credit than inferred defaults.

The score is **not** a benchmark of code quality, agent success, security, or maintainability. Use `--no-score` if a numeric summary would distract from the findings. The full formula is documented in [scoring](docs/scoring.md).

## What it does not do

Repo Context Doctor does not:

- generate or rewrite agent instructions;
- fix repository files or initialize configuration;
- run tests, linters, builds, package managers, hooks, containers, or scripts;
- clone or scan remote repositories;
- upload reports, collect telemetry, or require an account;
- use AI to grade instruction quality;
- promise that an inferred or documented command will succeed.

## Known limitations

- Detection is evidence-based and intentionally conservative; custom wrappers can be missed.
- Instruction precedence is described from known conventions, but vendor behavior can evolve.
- YAML, Markdown, and manifest parsing is shallow and dependency-free rather than a full semantic parser.
- A completed scan does not prove that every file was readable or every tool surface was recognized; check `UNKNOWN` findings and scan-limit metadata.

## Development

```bash
python -m venv .venv
python -m pip install ".[dev]"
pytest
ruff check .
ruff format --check .
python -m build
```

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a detector. The extension contract is described in [Adding a detector](docs/adding-a-detector.md).

## Support and security

- Questions and reproducible bugs: [GitHub Issues](https://github.com/cuijialin8888-code/repo-context-doctor/issues)
- Security reports: [SECURITY.md](SECURITY.md)
- Release history: [CHANGELOG.md](CHANGELOG.md)

Repo Context Doctor is an independent open-source project. It is not affiliated with or endorsed by OpenAI, Anthropic, Google, GitHub, Cursor, or any other coding-agent vendor.

## License

[MIT](LICENSE)
