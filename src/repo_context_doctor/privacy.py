"""Sensitive-path policy and defense-in-depth output redaction."""

from __future__ import annotations

import re
from pathlib import PurePath

CANARY = "RAD-CANARY-SECRET-7d4e91c2"

_SAFE_ENV_SUFFIXES = (".example", ".sample", ".template", ".dist")
_SENSITIVE_BASENAMES = {
    ".netrc",
    ".npmrc",
    "auth.json",
    "cookies.json",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "known_hosts",
    "pip.conf",
}
_SENSITIVE_SUFFIXES = {".key", ".p12", ".pem", ".pfx"}

_SECRET_PATTERNS = (
    re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"(?i)\bghp_[A-Za-z0-9]{8,}\b"),
    re.compile(r"(?i)\bgithub_pat_[A-Za-z0-9_]{8,}\b"),
    re.compile(r"(?i)\bBearer\s+[^\s'\"`]+"),
    re.compile(
        r"(?i)\b(?:OPENAI_API_KEY|ANTHROPIC_API_KEY|GOOGLE_API_KEY|GITHUB_TOKEN|"
        r"access_token|refresh_token)\b\s*[:=]\s*[^\s'\"`]+"
    ),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(re.escape(CANARY)),
)


def is_sensitive_path(path: PurePath) -> bool:
    """Return whether file content must not be read."""

    name = path.name.lower()
    if name == ".env":
        return True
    if name.startswith(".env.") and not name.endswith(_SAFE_ENV_SUFFIXES):
        return True
    if name in _SENSITIVE_BASENAMES:
        return True
    return path.suffix.lower() in _SENSITIVE_SUFFIXES


def redact_text(value: str) -> tuple[str, int]:
    """Replace credential-shaped values and the privacy canary."""

    redacted = value
    count = 0
    for pattern in _SECRET_PATTERNS:
        redacted, matches = pattern.subn("[REDACTED]", redacted)
        count += matches
    return redacted, count


def sanitize_excerpt(value: str, *, limit: int = 280) -> tuple[str, int]:
    """Normalize a short output excerpt and redact sensitive values."""

    compact = " ".join(value.strip().split())
    if len(compact) > limit:
        compact = compact[: limit - 1] + "…"
    return redact_text(compact)
