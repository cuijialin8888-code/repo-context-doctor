# Security policy

## Supported versions

During the 0.x series, only the latest tagged minor release receives security fixes.

| Version | Supported |
|---|---|
| 0.1.x | Yes |
| Older | No |

## Reporting a vulnerability

Please do not open a public issue for a vulnerability or suspected secret disclosure.

Use GitHub's private vulnerability reporting for this repository: [report a vulnerability privately](https://github.com/cuijialin8888-code/repo-context-doctor/security/advisories/new). Include affected versions, operating system, a minimal synthetic fixture, impact, and any suggested mitigation. Do not include real credentials or confidential repositories.

You should receive an acknowledgement within seven days. Valid reports will be investigated, fixed on a private branch when appropriate, and disclosed with credit if the reporter wants it.

## Security boundary

Repo Context Doctor is designed to read bounded repository metadata without executing target commands. It skips common sensitive paths, redacts credential-shaped excerpts, avoids symlinks, and emits relative paths. These controls reduce accidental disclosure; they do not make the tool a sandbox, malware analyzer, access-control system, or comprehensive secret scanner.

If you scan an untrusted repository, run the tool with the operating-system permissions and isolation you would use for any local file reader. Review generated reports before publishing them.
