"""远端镜像内容展示（Round 132 只读）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from wechat_article_scheduler.capability_probe import (
    CAPABILITY_DRAFT_LIST,
    CAPABILITY_PUBLISHED_LIST,
    human_capability_summary,
)
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.remote_sync import list_remote_mirrors


def _format_ts(ts: int | None) -> str:
    if not ts:
        return "—"
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except (OSError, OverflowError, ValueError):
        return str(ts)


def enrich_remote_row(row: dict[str, Any], *, mode: str) -> dict[str, Any]:
    out = dict(row)
    mid = row.get("media_id") or ""
    out["media_id_label"] = (
        f"演练远端 · {mid[:24]}…" if mode == "mock" and mid.startswith("mock_") else f"{mid[:28]}…"
    )
    out["update_time_label"] = _format_ts(row.get("update_time"))
    out["last_seen_label"] = (row.get("last_seen_at") or "—").replace("T", " ").split(".")[0]
    out["remote_type_label"] = "公众号草稿" if row.get("remote_type") == "draft" else "已发布"
    return out


def list_remote_drafts_display(
    conn: Any,
    config: AppConfig,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    mode = (config.wechat_mode or "mock").strip().lower()
    rows = list_remote_mirrors(conn, remote_type="draft", limit=limit)
    return [enrich_remote_row(r, mode=mode) for r in rows]


def remote_sync_summary(conn: Any, config: AppConfig) -> dict[str, Any]:
    from wechat_article_scheduler.capability_probe import get_cached_capabilities

    mode = (config.wechat_mode or "mock").strip().lower()
    cached = get_cached_capabilities(conn)
    human = human_capability_summary(cached)
    draft_cap = cached.get(CAPABILITY_DRAFT_LIST, {})
    pub_cap = cached.get(CAPABILITY_PUBLISHED_LIST, {})
    total = conn.execute(
        "SELECT COUNT(*) AS cnt FROM remote_content_mirror WHERE remote_type = 'draft' AND sync_status = 'active'"
    ).fetchone()["cnt"]
    published_state = pub_cap.get("state", "unknown")
    published_label: str
    if published_state == "unauthorized":
        published_label = "未授权：无法读取已发布列表"
    elif published_state == "empty":
        published_label = "已授权，当前无已发布文章"
    elif published_state == "authorized":
        cnt = pub_cap.get("item_count")
        published_label = f"已授权（约 {cnt} 条）" if cnt is not None else "已授权"
    elif published_state == "error":
        published_label = pub_cap.get("message", "探测失败")
    else:
        published_label = "尚未同步探测"
    return {
        "mode": mode,
        "local_draft_note": "下方「本地草稿」仅含本项目创建的记录",
        "remote_draft_count": int(total),
        "remote_draft_label": f"远端草稿镜像 {total} 篇",
        "draft_list_capability": draft_cap,
        "published_list_capability": pub_cap,
        "published_list_label": published_label,
        "published_delete_enabled": published_state == "authorized",
        "published_delete_reason": human.get("published_delete"),
        "can_sync": draft_cap.get("state") in ("authorized", "empty", None, "unknown")
        or mode == "mock",
    }
