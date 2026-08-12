# Supported signals

Repo Context Doctor performs bounded static discovery. This document distinguishes interpreted evidence from presence-only signals.

## Instruction surfaces

| Surface | Reported behavior |
|---|---|
| `AGENTS.md` | Root and nested scope; root-to-leaf convention; shadowing note when the same directory has `AGENTS.override.md` |
| `AGENTS.override.md` | Root and nested scope; reported as the Codex override for its directory |
| `CLAUDE.md` | Root/nested scope based on location |
| `.claude/CLAUDE.md` | Repository Claude Code context surface |
| `CLAUDE.local.md` | Local Claude Code context surface; content is still treated as untrusted input |
| `.claude/rules/*.md` | `paths` frontmatter is reported without expanding its globs |
| `GEMINI.md` | Root/nested scope based on location |
| `.github/copilot-instructions.md` | Repository-wide GitHub Copilot instruction surface |
| `.github/instructions/*.instructions.md` | `applyTo` frontmatter is reported; missing `applyTo` is a high-confidence `FAIL` |
| `.cursor/rules/*.mdc` | `globs` and `alwaysApply` metadata is reported; activation semantics are not evaluated |
| `.cursorrules` | Reported as a legacy Cursor surface |

The scanner inventories surfaces; it does not grade prose quality or guarantee a vendor will load the file. Vendor behavior can evolve independently.

## Ecosystems and manifests

Deep verification logic exists for:

- Python: `pyproject.toml`, `setup.cfg`, `setup.py`, `requirements.txt`, `tox.ini`;
- Node.js: `package.json`, `pnpm-workspace.yaml`, package manager declaration, scripts, and common lockfiles;
- Rust: `Cargo.toml` and conventional inferred commands;
- Go: `go.mod` and conventional inferred commands;
- PowerShell: `.ps1`, `.psd1`, `.psm1`, and `.Tests.ps1` structure;
- Generic repositories: instructions, documentation, Make targets, CI presence, root orientation, and common manifests.

Presence-only ecosystem signals include Maven/Gradle, PHP Composer, Ruby Bundler, Swift Package Manager, and .NET project/solution files. Presence-only means the report does not invent ecosystem commands.

Manifests deeper than four directory levels or below `fixtures`/`testdata` directories are not semantically interpreted. Invalid JSON/TOML manifests produce a `FAIL` rather than being treated as absent.

## Verification provenance

Verification commands carry one of these provenance values:

| Provenance | Meaning |
|---|---|
| `MANIFEST` | Structured repository manifest or script declaration |
| `INSTRUCTION` | Fenced or indented command in a supported instruction surface |
| `DOCUMENTATION` | Fenced or indented command in selected README/contributor docs |
| `CI` | Supported GitHub Actions `run:` step |
| `MAKEFILE` | Recognized verification target in Makefile/GNUmakefile |
| `INFERRED` | Stable ecosystem convention, not explicit repository guidance |

Currently recognized command families include pytest, Ruff, mypy, Pyright, tox, nox, common Node package-manager scripts, Cargo, Go, Pester, PSScriptAnalyzer, and selected Make targets. Commands composed through variables, reusable actions, shell conditionals, or custom wrappers may be missed.

GitHub Actions receives shallow `run:` inspection. GitLab CI, Azure Pipelines, and CircleCI are presence-only in version 0.1.0.

## Repository and dependency signals

- root README and CONTRIBUTING/docs orientation;
- conventional source and test directory names;
- workspace or multi-manifest monorepo hints;
- common Node, Rust, Go, Python lockfiles;
- mismatch between Node `packageManager` and lockfile family;
- multiple Node lockfile families.

Lockfile detection is presence-only and does not check freshness or dependency security.

## Scan limits

Defaults are fixed in version 0.1.0:

- maximum directory depth: 10;
- maximum discovered entries: 20,000;
- maximum interpreted text file: 256 KiB;
- UTF-8 text only;
- symlinks are skipped;
- VCS, virtual environment, dependency, build, cache, IDE, and common generated directories are excluded.

Limit hits, decode failures, and read failures remain visible as `UNKNOWN` findings or scan metadata.
