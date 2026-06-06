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
    "ACCESS_TOKEN",
)

_KEY_RE = re.compile("|".join(re.escape(k) for k in SENSITIVE_KEYWORDS), re.IGNORECASE)
_ASSIGNMENT_RE = re.compile(
    r"(?i)\b("
    + "|".join(re.escape(k) for k in SENSITIVE_KEYWORDS)
    + r")(\s*[:=]\s*)([^\s,;]+)"
)
_AUTHORIZATION_RE = re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+")


def is_sensitive_key(key: str) -> bool:
    """Return True when a mapping key names credential-like data."""
    return bool(_KEY_RE.search(key or ""))


def redact_text(value: str) -> str:
    """Mask credential-looking assignments inside user-provided text."""
    if not value:
        return ""
    redacted = _ASSIGNMENT_RE.sub(r"\1\2<redacted>", value)
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
    text = str(value)
    for match in _ASSIGNMENT_RE.finditer(text):
        candidate = match.group(3).strip("\"'，。")
        if candidate != "<redacted>":
            raise ValueError("external Agent task package contains sensitive-looking values")
    if _AUTHORIZATION_RE.search(text):
        raise ValueError("external Agent task package contains sensitive-looking values")
