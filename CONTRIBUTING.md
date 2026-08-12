# Contributing

Thanks for helping improve Repo Context Doctor. Small, evidence-backed changes are easiest to review.

## Before opening a pull request

For a new detector, output field, or behavioral change, open an issue first and describe:

- the repository evidence to recognize;
- a primary specification or real public fixture that supports the behavior;
- false-positive and privacy risks;
- whether the evidence is explicit or inferred;
- expected status, provenance, and confidence.

Typo fixes and focused regression fixes can go directly to a pull request.

## Local setup

```bash
git clone https://github.com/cuijialin8888-code/repo-context-doctor.git
cd repo-context-doctor
python -m venv .venv
python -m pip install ".[dev]"
```

On Windows with a non-ASCII checkout path, do not use editable installation if the Python distribution misdecodes `.pth` files. The standard install above and pytest's configured `src` path avoid that issue.

## Quality gates

```bash
pytest
ruff check .
ruff format --check .
python -m build
repo-context-doctor .
repo-context-doctor . --json
repo-context-doctor . --markdown
```

Tests must not call the network, execute a target repository command, or rely on developer credentials. Use synthetic fixtures. Keep intentionally fake secret values confined to privacy fixtures.

## Detector expectations

Every finding needs a stable ID, category, status, summary, details, evidence, recommendation, confidence, and repository-relative source paths where applicable. Every verification command needs a kind, command, provenance, confidence, source path, and evidence.

Prefer high-confidence explicit metadata. Inference must be labeled `INFERRED`, use no higher than medium confidence, and never claim the command succeeds. See [Adding a detector](docs/adding-a-detector.md).

## Pull requests

- Keep unrelated formatting or refactors out of the change.
- Add focused positive, negative, malformed-input, and privacy tests as relevant.
- Update `CHANGELOG.md` under `Unreleased` for user-visible behavior.
- Update both READMEs when usage or safety boundaries change.
- Confirm the full cross-platform CI matrix passes.

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
