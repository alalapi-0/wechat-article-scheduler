"""Sensitive-value redaction for external browser Agent task packages."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

SENSITIVE_KEYWORDS = (
    "WECHAT_APP_SECRET",
    "WECHAT_ACCESS_TOKEN",
    "WECHAT_TOKEN",
    "WECHAT_ENCODING_AES_KEY",
    "COOKIE",
    "SESSION",
    "AUTHORIZATION",
    "LLM_API_KEY",
    "OPENAI_API_KEY",
    "APPSECRET",
    "SECRET",
    "TOKEN",
    "CLIENT_SECRET",
    "ACCESS_TOKEN",
    "REFRESH_TOKEN",
    "SESSION_ID",
    "COOKIE_VALUE",
    "BEARER",
    "PASSWORD",
    "PASSWD",
    "API_KEY",
    "PRIVATE_KEY",
    "PEM",
    "AUTH",
    "AUTHENTICATION",
    "KEY",
    "CREDENTIAL",
    "CREDENTIALS",
    "CLIENT_KEY",
    "SIGNING_KEY",
    "ACCESS_KEY",
)

_NORMALIZED_KEYWORDS = frozenset(
    re.sub(r"[^A-Z0-9]", "", item.upper()) for item in SENSITIVE_KEYWORDS
)
_KEY_COMPOUND_PREFIXES = frozenset(
    {
        "API",
        "ACCESS",
        "AUTH",
        "CLIENT",
        "SIGNING",
        "PRIVATE",
        "PUBLIC",
        "SECRET",
        "ENCRYPTION",
    }
)
_SENSITIVE_KEY_PATTERN = (
    r"(?:(?:[A-Z0-9]+[\s._-]+)*(?:SECRET|TOKEN|CREDENTIALS?|PASS[\s._-]*(?:WORD|WD))"
    r"|APPSECRET|AUTH(?:ENTICATION|ORIZATION)?|BEARER|COOKIE(?:[\s._-]*VALUE)?"
    r"|SESSION(?:[\s._-]*ID)?|PEM|KEY"
    r"|(?:[A-Z0-9]+[\s._-]+)*(?:API|ACCESS|CLIENT|SIGNING|PRIVATE|PUBLIC|SECRET|ENCRYPTION)"
    r"[\s._-]*KEY)"
)
_ASSIGNMENT_RE = re.compile(
    r"(?i)((?<![A-Z0-9])[\"']?" + _SENSITIVE_KEY_PATTERN
    + r"[\"']?(?![A-Z0-9])\s*[:=]\s*)(\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\r\n]+)"
)
_AUTHORIZATION_RE = re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+")
# Deliberately independent from the replacement expression: this recognizes a
# broad key/value shape and delegates key classification to is_sensitive_key.
# The zero-width lookahead makes matches overlap, so an earlier harmless
# assignment cannot consume and hide a later credential on the same line.
_ASSERT_ASSIGNMENT_RE = re.compile(
    r"(?im)(?=(?<![A-Z0-9_.-])[\"']?"
    r"([A-Z][A-Z0-9._-]*(?:[ ][A-Z0-9._-]+){0,4})[\"']?\s*[:=]\s*"
    r"(\"[^\"\r\n]*\"|'[^'\r\n]*'|[^;?&,}\r\n]+))"
)
_ASSERT_AUTH_VALUE_RE = re.compile(
    r"(?i)\b(?:Bearer|Basic)\s+(?!<redacted>)[A-Za-z0-9._~+/=-]+"
)
_PEM_BLOCK_RE = re.compile(
    r"-----BEGIN ([A-Z0-9 ][A-Z0-9 -]*)-----.*?(?:-----END \1-----|\Z)",
    re.IGNORECASE | re.DOTALL,
)


def is_sensitive_key(key: str) -> bool:
    """Return True when a mapping key names credential-like data."""
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key or "")
    words = [item for item in re.split(r"[^A-Z0-9]+", expanded.upper()) if item]
    normalized = "".join(words)
    if normalized in _NORMALIZED_KEYWORDS:
        return True
    if words and words[-1] in {"SECRET", "TOKEN", "PASSWORD", "PASSWD", "CREDENTIAL", "CREDENTIALS"}:
        return True
    if len(words) >= 2 and words[-1] in {"AUTH", "AUTHENTICATION", "AUTHORIZATION"}:
        return True
    return len(words) >= 2 and words[-1] == "KEY" and words[-2] in _KEY_COMPOUND_PREFIXES


def redact_text(value: str) -> str:
    """Mask credential-looking assignments inside user-provided text."""
    if not value:
        return ""
    redacted = _PEM_BLOCK_RE.sub("<redacted-pem>", value)
    redacted = _ASSIGNMENT_RE.sub(r"\1<redacted>", redacted)
    return _AUTHORIZATION_RE.sub(r"\1 <redacted>", redacted)


def redact_sensitive_values(value: Any) -> Any:
    """Recursively redact secrets by key and text pattern."""
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            text_key = str(key)
            out[text_key] = "<redacted>" if is_sensitive_key(text_key) else redact_sensitive_values(item)
        return out
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [redact_sensitive_values(item) for item in value]
    return value


def assert_no_sensitive_values(value: Any) -> None:
    """Raise if a rendered task payload still contains unmasked sensitive assignments."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if is_sensitive_key(str(key)) and str(item).strip() not in {
                "<redacted>",
                "\"<redacted>\"",
                "'<redacted>'",
            }:
                raise ValueError("external Agent task package contains sensitive-looking values")
            assert_no_sensitive_values(item)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            assert_no_sensitive_values(item)
        return
    text = str(value)
    for match in _ASSERT_ASSIGNMENT_RE.finditer(text):
        if not is_sensitive_key(match.group(1)):
            continue
        candidate = match.group(2).strip("\"'，。")
        redacted_structured = candidate.startswith("<redacted>") and (
            len(candidate) == len("<redacted>")
            or candidate[len("<redacted>")] in "\"',;})]"
        )
        if not redacted_structured:
            raise ValueError("external Agent task package contains sensitive-looking values")
    if _ASSERT_AUTH_VALUE_RE.search(text):
        raise ValueError("external Agent task package contains sensitive-looking values")
    if _PEM_BLOCK_RE.search(text):
        raise ValueError("external Agent task package contains a PEM block")
