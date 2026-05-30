"""内容库领域模型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ReviewStatus = Literal["draft", "pending_review", "approved", "rejected"]

REVIEW_STATUSES: tuple[ReviewStatus, ...] = (
    "draft",
    "pending_review",
    "approved",
    "rejected",
)


@dataclass(frozen=True)
class Collection:
    id: int
    slug: str
    name: str
    description: str | None = None


@dataclass(frozen=True)
class Tag:
    id: int
    slug: str
    name: str


@dataclass(frozen=True)
class ContentItem:
    article_id: int
    title: str
    review_status: ReviewStatus
    collection_slug: str
    tags: tuple[str, ...]
    source_path: str
    content_hash: str
    import_batch: str | None = None
