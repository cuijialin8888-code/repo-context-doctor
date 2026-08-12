# Report format

Console and Markdown are human views of the same `ScanReport` used by JSON. Renderers do not make diagnostic decisions.

## JSON stability

Version 0.1.0 emits `schema_version: "1"`. Within schema version 1, existing fields will not be removed or change meaning in a patch release. New finding IDs or additive fields may appear, so consumers should ignore unknown fields.

Top-level fields appear in stable order:

| Field | Type | Meaning |
|---|---|---|
| `tool` | object | Tool name and version |
| `schema_version` | string | Report schema major version |
| `timestamp` | string | UTC scan time |
| `repository` | object | Relative identity and repository facts; no absolute path |
| `ecosystems` | array | Sorted ecosystem labels |
| `instruction_surfaces` | array | Path, kind, scope, recognized vendors, precedence note |
| `verification_paths` | array | Kind, command, provenance, confidence, source path, evidence |
| `findings` | array | Structured diagnostic records |
| `scores` | object/null | Optional transparent heuristic score |
| `summary` | object | Counts by status |
| `recommendations` | array | Deduplicated prioritized next steps |
| `privacy` | object | Sensitive/large/undecodable skips, redactions, path policy |
| `scan` | object | Entry count, limits, partial-scan and skipped-link metadata |

## Finding contract

Each finding contains:

- `id`: stable machine-oriented identifier;
- `category`: one of `agent_context`, `verification`, `automation`, `reproducibility`, `orientation`, `repository`, `privacy`;
- `status`: `PASS`, `WARN`, `FAIL`, `INFO`, or `UNKNOWN`;
- `summary` and `details`;
- `evidence` and `recommendation`;
- `confidence`: `HIGH`, `MEDIUM`, or `LOW`;
- `source_paths`: repository-relative paths;
- `provenance`: a provenance value or null.

Status meanings:

- `PASS`: supported evidence positively satisfies the check;
- `WARN`: an actionable gap or ambiguity, not necessarily an error;
- `FAIL`: machine-verifiable invalid metadata or a required field missing from a detected surface;
- `INFO`: neutral inventory evidence;
- `UNKNOWN`: the scanner could not establish the state safely.

## Exit codes

Finding status does not determine the process exit code:

- `0`: scan and rendering completed;
- `2`: command-line usage error;
- `3`: unexpected fatal scan failure.

This separation keeps the tool an evidence inventory rather than an opaque quality gate. Consumers can implement their own policy against stable fields if needed.

## Privacy

All output modes use repository-relative source paths. Recognized credential patterns and the public fake privacy canary are redacted. A report can still contain non-secret repository metadata, filenames, and commands, so review it before external publication.
