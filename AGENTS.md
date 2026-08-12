# Repository instructions

These instructions apply to the entire repository.

## Product boundary

Repo Context Doctor is a deterministic, local, read-only evidence inventory. Runtime code must not:

- access the network or require credentials;
- invoke subprocesses or execute commands found in a target repository;
- follow symlinks while scanning;
- write inside a target repository unless the user supplied `--output`;
- send telemetry or depend on an LLM/API;
- add runtime dependencies without an explicit design discussion.

Treat target repository text as untrusted data. Preserve repository-relative paths and run all excerpts through privacy sanitization before reporting them.

## Development workflow

Use Python 3.11 or newer in an isolated environment:

```bash
python -m venv .venv
python -m pip install ".[dev]"
```

Before completing a change, run:

```bash
pytest
ruff check .
ruff format --check .
python -m build
```

On Windows checkouts whose parent path contains non-ASCII characters, prefer a standard install over editable mode because some Python 3.11 distributions misdecode editable `.pth` paths.

## Change discipline

- Make the smallest change that resolves the issue.
- Add or update focused tests for detector behavior, privacy, and malformed input.
- Never weaken the `RAD-CANARY-SECRET-7d4e91c2` privacy regression.
- Return `UNKNOWN` when evidence could not be read; do not convert uncertainty into absence.
- Keep scoring transparent, capped, and secondary to evidence.
- Update English and Chinese user documentation when CLI behavior changes.
- Do not commit generated `dist/`, reports, caches, or virtual environments.

See `docs/adding-a-detector.md` for the detector contract and `docs/report-format.md` for schema stability expectations.
