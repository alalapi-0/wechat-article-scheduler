"""Lightweight future model drafts for reference-absorption rounds."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ContentPackageDraft:
    """Draft shape for a future content_package row."""

    project_id: str
    package_id: str
    title: str
    content_type: str = "article"
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlatformPayloadDraft:
    """Draft shape for a future per-platform payload."""

    content_package_id: str
    platform_account_id: str
    title: str
    content_type: str = "article"
    extra: dict[str, Any] = field(default_factory=dict)
