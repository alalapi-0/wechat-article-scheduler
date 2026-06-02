"""内容库 SQLite 仓储。"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone

from typing import TYPE_CHECKING

from wechat_article_scheduler.content_library.models import (
    Collection,
    ContentItem,
    Tag,
)

if TYPE_CHECKING:
    from wechat_article_scheduler.content_library.collection_config import CollectionConfig

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
        SET collection_id = ?, import_batch = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (cid, batch, article_id),
    )
    if tag_names:
        assign_article_tags(conn, article_id, tag_names)


def list_content_items(
    conn: sqlite3.Connection,
    *,
    limit: int = 50,
    collection_slug: str | None = None,
) -> list[ContentItem]:
    sql = """
        SELECT a.id AS article_id, a.title, a.source_path,
               a.content_hash, a.import_batch, COALESCE(c.slug, 'default') AS collection_slug
        FROM articles a
        LEFT JOIN collections c ON c.id = a.collection_id
        WHERE 1=1
    """
    params: list[object] = []
    if collection_slug:
        sql += " AND COALESCE(c.slug, 'default') = ?"
        params.append(collection_slug)
    sql += " ORDER BY a.id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
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
        items.append(
            ContentItem(
                article_id=int(row["article_id"]),
                title=row["title"],
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


def upsert_collection(conn: sqlite3.Connection, cfg: "CollectionConfig") -> int:
    """将 collection.yaml 同步到 collections 表。"""
    config_json = cfg.to_config_json()
    row = conn.execute(
        "SELECT id FROM collections WHERE slug = ?",
        (cfg.slug,),
    ).fetchone()
    if row:
        conn.execute(
            """
            UPDATE collections
            SET name = ?, description = ?, config_json = ?
            WHERE slug = ?
            """,
            (cfg.name, cfg.description or None, config_json, cfg.slug),
        )
        return int(row["id"])
    cur = conn.execute(
        """
        INSERT INTO collections (slug, name, description, config_json)
        VALUES (?, ?, ?, ?)
        """,
        (cfg.slug, cfg.name, cfg.description or None, config_json),
    )
    return int(cur.lastrowid)


def get_collection_id_by_slug(conn: sqlite3.Connection, slug: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM collections WHERE slug = ?",
        (slug,),
    ).fetchone()
    return int(row["id"]) if row else None


def apply_collection_defaults(
    conn: sqlite3.Connection,
    root: Path,
    article_id: int,
    cfg: "CollectionConfig | None",
) -> None:
    if cfg is None:
        return
    row = conn.execute(
        "SELECT title, cover_path FROM articles WHERE id = ?",
        (article_id,),
    ).fetchone()
    if row is None:
        return
    updates: list[str] = []
    params: list[object] = []
    if cfg.title_template and row["title"]:
        new_title = cfg.title_template.replace("{title}", row["title"])
        if new_title != row["title"]:
            updates.append("title = ?")
            params.append(new_title)
    cover = (row["cover_path"] or "").strip()
    if not cover and cfg.default_cover:
        candidate = Path(cfg.default_cover)
        if not candidate.is_absolute():
            candidate = root / candidate
        if candidate.is_file():
            updates.append("cover_path = ?")
            params.append(str(candidate.resolve()))
    if updates:
        params.append(article_id)
        conn.execute(
            f"UPDATE articles SET {', '.join(updates)}, updated_at = datetime('now') WHERE id = ?",
            params,
        )


def list_collections_summary(conn: sqlite3.Connection) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT c.id, c.slug, c.name, c.description, c.config_json,
               COUNT(a.id) AS article_count
        FROM collections c
        LEFT JOIN articles a ON a.collection_id = c.id
            AND (a.deleted_at IS NULL OR a.deleted_at = '')
        GROUP BY c.id
        ORDER BY c.slug
        """
    ).fetchall()
    out: list[dict[str, object]] = []
    for r in rows:
        out.append(
            {
                "id": int(r["id"]),
                "slug": r["slug"],
                "name": r["name"],
                "description": r["description"],
                "config_json": r["config_json"],
                "article_count": int(r["article_count"] or 0),
            }
        )
    return out
