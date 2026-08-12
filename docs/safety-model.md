# Safety and privacy model

Repo Context Doctor is a metadata reader, not a sandbox. Its design reduces side effects and accidental disclosure through independent controls.

## Read boundary

- Directory discovery uses `os.scandir` without following symlinks.
- Common VCS, dependency, environment, cache, build, coverage, IDE, and generated directories are excluded.
- Discovery is capped by depth and entry count.
- Only selected metadata is interpreted; text reads are capped and UTF-8 only.
- `.env`, private-key containers, credential files, and similar sensitive basenames are not read.

## Execution boundary

The runtime package does not import subprocess or network clients. Verification commands are treated as untrusted strings. The scanner does not run package managers, hooks, test runners, shells, containers, or repository scripts.

## Write boundary

Ordinary output goes to stdout. The CLI writes one report only when `--output` is explicitly supplied and the parent directory already exists. It does not create configuration or fix the target.

## Output boundary

- source paths are repository-relative;
- excerpts are length-limited and whitespace-normalized;
- common credential shapes and the test canary are redacted;
- privacy counters describe skipped/redacted material;
- incomplete reads generate visible uncertainty.

## Non-goals

These controls do not detect every secret, make hostile files safe for other applications, prevent time-of-check/time-of-use filesystem races, or establish that a repository command is safe. Use operating-system isolation for actively hostile repositories and manually review reports before sharing them.
