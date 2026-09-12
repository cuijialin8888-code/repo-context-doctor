# Review a Repo Context Doctor report

Repo Context Doctor inventories what can be discovered locally before an agent changes a repository. A report is evidence with provenance, not a quality certification or a command execution result.

Use `repo-context-doctor .`, `repo-context-doctor . --json`, `repo-context-doctor . --markdown --output context-report.md`, or `repo-context-doctor . --no-score` as appropriate. For CI, add `--fail-on fail`, `--fail-on warn`, or `--fail-on unknown`; the default `none` keeps the tool informational. The scan does not modify the target repository.

Read provenance before drawing conclusions: check the source path and source kind (`MANIFEST`, `INSTRUCTION`, `DOCUMENTATION`, `CI`, `MAKEFILE`, or `INFERRED`); treat `UNKNOWN` as unreadable or insufficient evidence; distinguish documented commands from inferred commands; and review scan-limit metadata before calling an inventory complete.

The optional score is not a benchmark of code quality, agent success, security, or maintainability. The scanner is local, does not call an LLM or network service, never executes target commands, and does not upload reports. Review repository-relative paths and instruction excerpts before sharing output. If coverage is incomplete, adjust `--max-depth`, `--max-entries`, or `--max-file-bytes` deliberately and review the resulting scan-limit metadata.
