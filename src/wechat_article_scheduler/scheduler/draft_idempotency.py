"""草稿创建幂等：同一 article + content_hash 不重复调用 create_draft。"""

from __future__ import annotations

import sqlite3

from wechat_article_scheduler.adapters.base import DraftResult


def find_reusable_draft_media_id(
    conn: sqlite3.Connection,
    *,
    article_id: int,
    content_hash: str | None,
) -> str | None:
    """若已有相同内容指纹的草稿记录，返回可复用的 media_id。"""
    h = (content_hash or "").strip()
    if not h:
        return None
    row = conn.execute(
        """
        SELECT d.media_id
        FROM wechat_drafts d
        INNER JOIN articles a ON a.id = d.article_id
        WHERE d.article_id = ?
          AND d.status = 'created'
          AND d.media_id IS NOT NULL
          AND TRIM(d.media_id) != ''
          AND a.content_hash = ?
        ORDER BY d.id DESC
        LIMIT 1
        """,
        (article_id, h),
    ).fetchone()
    if row is None:
        return None
    return str(row["media_id"])


def draft_result_from_reuse(media_id: str) -> DraftResult:
    return DraftResult(
        media_id=media_id,
        raw_response={"idempotent_reuse": True, "media_id": media_id},
    )
