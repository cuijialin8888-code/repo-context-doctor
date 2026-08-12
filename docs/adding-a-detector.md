# Adding a detector

A detector converts bounded snapshot evidence into structured facts. It must never execute target code or make hidden network calls.

## 1. Define the evidence boundary

Before coding, write down:

- exact filenames or syntax to inspect;
- the primary convention or specification supporting the behavior;
- depth and size limits;
- malformed, missing, inaccessible, and ambiguous cases;
- privacy implications;
- whether the result is explicit or inferred.

Prefer presence-only reporting over pretending to understand an unsupported format.

## 2. Use the shared snapshot

Use `RepositorySnapshot` discovery and `read_text()`. Do not call recursive globbing, follow symlinks, read sensitive paths directly, or bypass size/UTF-8 limits. Treat `None` as unreadable/limited evidence and preserve `UNKNOWN` where that distinction matters.

## 3. Return structured output

Add a focused module under `src/repo_context_doctor/detectors/`. Return findings, verification paths, and/or boolean scoring facts as appropriate. Keep renderers free of detector logic.

A `Finding` must include:

```python
Finding(
    id="ecosystem.signal-name",
    category=Category.REPOSITORY,
    status=Status.INFO,
    summary="Short factual statement",
    details="What was and was not established",
    evidence="Sanitized evidence",
    recommendation="A proportional next step",
    confidence=Confidence.HIGH,
    source_paths=("relative/path",),
)
```

Verification paths also require `kind`, `command`, `provenance`, `confidence`, `source_path`, and `evidence`. Run excerpts through `sanitize_excerpt()`. Never assign high confidence to a generic inference.

## 4. Integrate once

Call the detector from `scanner.py` in a deterministic order. Deduplicate shared verification paths and keep sorting stable. Do not let duplicate files stack score indefinitely.

## 5. Test the boundary

Add synthetic tests for:

- one positive explicit signal;
- absence without false positives;
- malformed and unreadable metadata;
- nested/monorepo scope when relevant;
- determinism and relative paths;
- secret-like values and `RAD-CANARY-SECRET-7d4e91c2` when excerpts can reach output;
- platform-specific behavior where applicable.

The runtime import guard must continue to show no subprocess or network modules. Run all quality gates in `CONTRIBUTING.md`.

## 6. Document user-visible behavior

Update `docs/supported-signals.md`, both READMEs if the public capability changed, and the `Unreleased` changelog. A schema-breaking change requires a schema version decision rather than a silent field change.
