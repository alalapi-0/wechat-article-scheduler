"""内容库 SQLite 仓储。"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone

from wechat_article_scheduler.content_library.models import (
    REVIEW_STATUSES,
    Collection,
    ContentItem,
    ReviewStatus,
    Tag,
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    base = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return base or "item"


def ensure_default_collection(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT id FROM collections WHERE slug = 'default' LIMIT 1"
    ).fetchone()
    if row:
        return int(row["id"])
    cur = conn.execute(
        """
        INSERT INTO collections (slug, name, description)
        VALUES ('default', '默认集合', '扫描导入的默认内容集合')
        """
    )
    return int(cur.lastrowid)


def get_or_create_tag(conn: sqlite3.Connection, name: str) -> Tag:
    slug = slugify(name)
    row = conn.execute("SELECT id, slug, name FROM tags WHERE slug = ?", (slug,)).fetchone()
    if row:
        return Tag(id=int(row["id"]), slug=row["slug"], name=row["name"])
    cur = conn.execute("INSERT INTO tags (slug, name) VALUES (?, ?)", (slug, name.strip()))
    return Tag(id=int(cur.lastrowid), slug=slug, name=name.strip())


def assign_article_tags(conn: sqlite3.Connection, article_id: int, tag_names: list[str]) -> None:
    conn.execute("DELETE FROM article_tags WHERE article_id = ?", (article_id,))
    for name in tag_names:
        tag = get_or_create_tag(conn, name)
        conn.execute(
            "INSERT OR IGNORE INTO article_tags (article_id, tag_id) VALUES (?, ?)",
            (article_id, tag.id),
        )


def set_review_status(
    conn: sqlite3.Connection,
    article_id: int,
    review_status: ReviewStatus,
) -> bool:
    if review_status not in REVIEW_STATUSES:
        raise ValueError(f"invalid review_status: {review_status}")
    cur = conn.execute(
        """
        UPDATE articles
        SET review_status = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (review_status, article_id),
    )
    return cur.rowcount > 0


def register_imported_article(
    conn: sqlite3.Connection,
    *,
    article_id: int,
    collection_id: int | None = None,
    import_batch: str | None = None,
    tag_names: list[str] | None = None,
) -> None:
    cid = collection_id or ensure_default_collection(conn)
    batch = import_batch or datetime.now(timezone.utc).strftime("%Y%m%d")
    conn.execute(
        """
        UPDATE articles
        SET collection_id = ?, review_status = 'draft', import_batch = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (cid, batch, article_id),
    )
    if tag_names:
        assign_article_tags(conn, article_id, tag_names)


def list_content_items(conn: sqlite3.Connection, *, limit: int = 50) -> list[ContentItem]:
    rows = conn.execute(
        """
        SELECT a.id AS article_id, a.title, a.review_status, a.source_path,
               a.content_hash, a.import_batch, COALESCE(c.slug, 'default') AS collection_slug
        FROM articles a
        LEFT JOIN collections c ON c.id = a.collection_id
        ORDER BY a.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    items: list[ContentItem] = []
    for row in rows:
        tags = conn.execute(
            """
            SELECT t.name FROM tags t
            JOIN article_tags at ON at.tag_id = t.id
            WHERE at.article_id = ?
            ORDER BY t.name
            """,
            (int(row["article_id"]),),
        ).fetchall()
        review = row["review_status"] or "draft"
        items.append(
            ContentItem(
                article_id=int(row["article_id"]),
                title=row["title"],
                review_status=review,  # type: ignore[arg-type]
                collection_slug=row["collection_slug"],
                tags=tuple(t["name"] for t in tags),
                source_path=row["source_path"],
                content_hash=row["content_hash"],
                import_batch=row["import_batch"],
            )
        )
    return items


def list_collections(conn: sqlite3.Connection) -> list[Collection]:
    rows = conn.execute(
        "SELECT id, slug, name, description FROM collections ORDER BY id"
    ).fetchall()
    return [
        Collection(
            id=int(r["id"]),
            slug=r["slug"],
            name=r["name"],
            description=r["description"],
        )
        for r in rows
    ]
