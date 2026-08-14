# Maintenance checklist

Keep maintenance focused on evidence detection and reproducibility. The scanner must remain local, deterministic, read-only with respect to the target repository, and free of runtime dependencies.

## Review triggers

- A new instruction-file convention, manifest, lockfile, CI surface, or supported ecosystem needs evidence-based detection.
- A privacy, redaction, symlink, scan-limit, report-schema, or safety edge case is reproduced.
- A supported Python version changes, or a release is prepared.

## Routine checks

Run the repository checks in an isolated Python environment:

```bash
pytest
ruff check .
ruff format --check .
python -m build
```

The CI workflow also exercises Python 3.11 and 3.13 on Windows, macOS, and Linux, plus the privacy-canary regression. Keep detector tests focused and preserve `UNKNOWN` when evidence cannot be read.

## Release checks

- Update the version, CHANGELOG, and user-facing installation examples together.
- Create a matching `vX.Y.Z` tag so the release workflow builds the wheel and source distribution.
- Verify the installed wheel with `repo-context-doctor --version` and retain the generated SHA-256 checksums.
- Review the release notes and a sample report before sharing results from a sensitive repository.

## Safety boundaries

- Do not add runtime dependencies, network access, subprocess execution, command execution from target repositories, symlink traversal, telemetry, or implicit target-repository writes.
- Never weaken the privacy canary or turn unreadable evidence into an absence finding.
- Do not create activity-only commits or claim support that has not been tested.
