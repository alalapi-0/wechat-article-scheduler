"""内容库领域模型。"""

from __future__ import annotations

from dataclasses import dataclass


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
    collection_slug: str
    tags: tuple[str, ...]
    source_path: str
    content_hash: str
    import_batch: str | None = None
