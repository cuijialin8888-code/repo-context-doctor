# Heuristic evidence score

The score is a compact summary of signals already present in the report. It is deliberately secondary to findings, optional through `--no-score`, and never changes the process exit code.

It is not a benchmark of repository quality, coding-agent success, security, or maintainability. A repository can be excellent and receive a low score because it uses an unsupported convention. A high score only means the supported evidence was easy to discover.

## Formula

Each category is capped at 100 before its weight is applied.

| Category | Weight | Signals |
|---|---:|---|
| Agent context | 30% | Any instruction surface 60; repository-root surface 25; nested/scoped surface 15 |
| Verification discoverability | 30% | Explicit test 40 or inferred test 20; explicit lint 20 or inferred lint 10; explicit build 20 or inferred build 10; explicit type/format 20 or inferred type/format 10 |
| Automation / CI | 15% | Supported CI configuration 50; recognized CI verification command 50 |
| Dependency reproducibility | 15% | Manifest 35; recognized lockfile 40; consistent Node package-manager signals 25 |
| Repository orientation | 10% | Root README 45; CONTRIBUTING or `docs/` 25; conventional source directory 15; conventional test directory 15 |

The overall value is the rounded weighted sum:

```text
overall = round(sum(category_score * category_weight) / 100)
```

Labels are fixed:

- 85–100: `STRONG EVIDENCE`
- 65–84: `PARTIAL EVIDENCE`
- 0–64: `LIMITED EVIDENCE`

## Anti-gaming rules

- Multiple instruction files satisfy presence once; they do not add unlimited points.
- Explicit repository-owned commands receive more credit than ecosystem inference.
- A test filename alone is not a runnable test command.
- Malformed metadata remains a `FAIL` finding even if other score signals are present.
- No finding is hidden because the score is high.

Changing weights, thresholds, or signal definitions is a user-visible behavior change and requires tests plus a changelog entry.
