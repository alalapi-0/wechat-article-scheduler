"""远端微信公众号内容只读同步（draft/batchget 分页镜像）。"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters import get_adapter
from wechat_article_scheduler.capability_probe import (
    cache_capability_probe,
    probe_all_capabilities,
)
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.external_agent.redaction import redact_sensitive_values

REMOTE_TYPE_DRAFT = "draft"
REMOTE_TYPE_PUBLISHED = "published"
PAGE_SIZE = 20


def _content_hash(title: str, update_time: int | None) -> str:
    raw = f"{title}|{update_time or 0}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _redact_summary(item: dict[str, Any]) -> str:
    safe = redact_sensitive_values(
        {
            "media_id": (item.get("media_id") or "")[:32],
            "update_time": item.get("update_time"),
            "title": (item.get("content", {}) or {}).get("news_item", [{}])[0].get("title", "")
            if isinstance(item.get("content"), dict)
            else item.get("title", ""),
        }
    )
    return json.dumps(safe, ensure_ascii=False)[:400]


def _extract_draft_items(page: dict[str, Any]) -> list[dict[str, Any]]:
    items = page.get("item") or []
    out: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        media_id = str(raw.get("media_id") or "")
        if not media_id:
            continue
        news = []
        content = raw.get("content")
        if isinstance(content, dict):
            news = content.get("news_item") or []
        title = ""
        if news and isinstance(news[0], dict):
            title = str(news[0].get("title") or "")
        out.append(
            {
                "media_id": media_id,
                "update_time": int(raw.get("update_time") or 0),
                "title": title,
                "raw": raw,
            }
        )
    return out


def upsert_remote_mirror(
    conn: Any,
    *,
    remote_type: str,
    media_id: str,
    title: str,
    update_time: int | None,
    article_id: str | None = None,
    raw_item: dict[str, Any] | None = None,
) -> str:
    """幂等写入镜像表，返回 action: inserted|updated|unchanged。"""
    ch = _content_hash(title, update_time)
    summary = _redact_summary(raw_item or {"title": title, "media_id": media_id})
    existing = conn.execute(
        """
        SELECT id, content_hash, sync_status FROM remote_content_mirror
        WHERE remote_type = ? AND media_id = ?
        """,
        (remote_type, media_id),
    ).fetchone()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    if existing is None:
        conn.execute(
            """
            INSERT INTO remote_content_mirror
                (remote_type, media_id, article_id, title, update_time,
                 last_seen_at, content_hash, sync_status, raw_summary_redacted)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
            """,
            (remote_type, media_id, article_id, title, update_time, now, ch, summary),
        )
        return "inserted"
    if existing["content_hash"] == ch and existing["sync_status"] == "active":
        conn.execute(
            "UPDATE remote_content_mirror SET last_seen_at = ?, updated_at = datetime('now') WHERE id = ?",
            (now, existing["id"]),
        )
        return "unchanged"
    conn.execute(
        """
        UPDATE remote_content_mirror
        SET title = ?, update_time = ?, last_seen_at = ?, content_hash = ?,
            sync_status = 'active', raw_summary_redacted = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (title, update_time, now, ch, summary, existing["id"]),
    )
    return "updated"


def list_remote_mirrors(
    conn: Any,
    *,
    remote_type: str | None = None,
    sync_status: str = "active",
    limit: int = 100,
) -> list[dict[str, Any]]:
    sql = """
        SELECT id, remote_type, media_id, article_id, title, update_time,
               last_seen_at, content_hash, sync_status, raw_summary_redacted, created_at
        FROM remote_content_mirror
        WHERE sync_status = ?
    """
    params: list[Any] = [sync_status]
    if remote_type:
        sql += " AND remote_type = ?"
        params.append(remote_type)
    sql += " ORDER BY update_time DESC, id DESC LIMIT ?"
    params.append(limit)
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def sync_remote_drafts(
    config: AppConfig,
    *,
    max_pages: int = 50,
    dry_run: bool = False,
    run_id: str | None = None,
) -> dict[str, Any]:
    """
    分页同步 draft/batchget 到本地镜像表（幂等，不泄露 token）。

    返回统计：synced, inserted, updated, unchanged, stale, pages, capability
    """
    adapter = get_adapter(config)
    stats: dict[str, Any] = {
        "synced": 0,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "stale": 0,
        "pages": 0,
        "dry_run": dry_run,
        "run_id": run_id,
        "seen_media_ids": [],
    }
    seen: set[str] = set()
    offset = 0

    with db.connect(config.database_path) as conn:
        caps = probe_all_capabilities(adapter)
        if not dry_run:
            for key in ("draft_list", "published_list"):
                cache_capability_probe(conn, caps[key])

        draft_probe = caps["draft_list"]
        if draft_probe.get("state") == "unauthorized":
            stats["blocked"] = True
            stats["reason"] = draft_probe.get("message", "草稿列表未授权")
            conn.commit()
            return stats
        if draft_probe.get("state") == "error":
            stats["blocked"] = True
            stats["reason"] = draft_probe.get("message", "草稿列表探测失败")
            conn.commit()
            return stats

        while stats["pages"] < max_pages:
            page = adapter.list_drafts_batchget(offset=offset, count=PAGE_SIZE)
            stats["pages"] += 1
            items = _extract_draft_items(page)
            if not items:
                break
            for item in items:
                mid = item["media_id"]
                seen.add(mid)
                stats["seen_media_ids"].append(mid)
                if dry_run:
                    stats["synced"] += 1
                    continue
                action = upsert_remote_mirror(
                    conn,
                    remote_type=REMOTE_TYPE_DRAFT,
                    media_id=mid,
                    title=item["title"],
                    update_time=item["update_time"],
                    raw_item=item["raw"],
                )
                stats["synced"] += 1
                stats[action] = int(stats.get(action, 0)) + 1
            if len(items) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        if not dry_run and seen:
            placeholders = ",".join("?" for _ in seen)
            stale_rows = conn.execute(
                f"""
                SELECT media_id FROM remote_content_mirror
                WHERE remote_type = ? AND sync_status = 'active'
                  AND media_id NOT IN ({placeholders})
                """,
                (REMOTE_TYPE_DRAFT, *seen),
            ).fetchall()
            for row in stale_rows:
                conn.execute(
                    """
                    UPDATE remote_content_mirror
                    SET sync_status = 'stale', updated_at = datetime('now')
                    WHERE remote_type = ? AND media_id = ?
                    """,
                    (REMOTE_TYPE_DRAFT, row["media_id"]),
                )
                stats["stale"] += 1

        if not dry_run:
            db.log_event(
                conn,
                entity_type="remote_sync",
                entity_id=None,
                event_type="sync_remote_drafts",
                payload=json.dumps(
                    {
                        "synced": stats["synced"],
                        "inserted": stats.get("inserted", 0),
                        "updated": stats.get("updated", 0),
                        "stale": stats["stale"],
                        "dry_run": False,
                        "run_id": run_id,
                    },
                    ensure_ascii=False,
                ),
            )
        conn.commit()

    stats["capability"] = caps
    return stats
