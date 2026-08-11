"""草稿创建幂等：同一 article + content_hash 不重复调用 create_draft。"""

from __future__ import annotations

import json
import sqlite3

from wechat_article_scheduler.adapters.base import DraftResult


def find_reusable_draft_media_id(
    conn: sqlite3.Connection,
    *,
    article_id: int,
    content_fingerprint: str | None,
    adapter_mode: str,
) -> str | None:
    """Return a same-content draft only when its adapter provenance matches."""
    fingerprint = (content_fingerprint or "").strip()
    mode = (adapter_mode or "").strip().lower()
    if not fingerprint or mode not in {"mock", "real"}:
        return None
    rows = conn.execute(
        """
        SELECT d.media_id, d.payload_json
        FROM wechat_drafts d
        INNER JOIN publish_jobs j ON j.id = d.publish_job_id
        WHERE d.article_id = ?
          AND d.status IN ('created', 'updated')
          AND d.adapter_mode = ?
          AND j.article_id = d.article_id
          AND j.adapter_mode = d.adapter_mode
          AND j.status IN ('done', 'waiting_confirmation')
          AND d.media_id IS NOT NULL
          AND TRIM(d.media_id) != ''
        ORDER BY d.id DESC
        """,
        (article_id, mode),
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(str(row["payload_json"] or ""))
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get("content_fingerprint") or "").strip() == fingerprint:
            return str(row["media_id"])
    return None


def draft_result_from_reuse(media_id: str) -> DraftResult:
    return DraftResult(
        media_id=media_id,
        raw_response={"idempotent_reuse": True, "media_id": media_id},
    )
