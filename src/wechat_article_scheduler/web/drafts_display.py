"""微信草稿记录展示（收敛 Round 13 / round_068）。"""

from __future__ import annotations

import json
from typing import Any

from wechat_article_scheduler.config import AppConfig


DRAFT_STATUS_LABELS: dict[str, str] = {
    "created": "已创建",
    "updated": "已更新",
    "superseded": "已替代",
}


def label_draft_status(status: str | None) -> str:
    key = (status or "").strip().lower()
    return DRAFT_STATUS_LABELS.get(key, status or "未知")


def _format_created_at(iso: str | None) -> str:
    if not iso:
        return "—"
    return iso.replace("T", " ").split(".")[0]


def _media_id_label(media_id: str | None, *, mode: str) -> str:
    mid = (media_id or "").strip()
    if not mid:
        return "（无 media_id）"
    if mode == "mock" and mid.startswith("mock_"):
        return f"演练草稿 · {mid[:24]}{'…' if len(mid) > 24 else ''}"
    return f"{mid[:28]}{'…' if len(mid) > 28 else ''}"


def _payload_preview(payload_json: str | None) -> str:
    raw = (payload_json or "").strip()
    if not raw:
        return ""
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            return json.dumps(data, ensure_ascii=False)[:300]
        except json.JSONDecodeError:
            pass
    return raw[:300]


def enrich_draft_row(row: dict[str, Any], config: AppConfig) -> dict[str, Any]:
    mode = (config.wechat_mode or "mock").strip().lower()
    media = row.get("media_id")
    out = dict(row)
    out["status_label"] = label_draft_status(row.get("status"))
    out["created_at_label"] = _format_created_at(row.get("created_at"))
    out["media_id_label"] = _media_id_label(media, mode=mode)
    out["is_mock_draft"] = mode == "mock" and str(media or "").startswith("mock_")
    out["mock_note"] = (
        "演练模式：此 media_id 为本地模拟，未在公众号后台创建真实草稿"
        if out["is_mock_draft"]
        else None
    )
    out["article_detail_url"] = f"/articles/{row.get('article_id')}"
    out["payload_preview"] = _payload_preview(row.get("payload_json"))
    article_status = (row.get("article_status") or "").strip().lower()
    if article_status == "published":
        out["next_hint"] = "作品已发布，可在作品详情查看最终状态"
    else:
        out["next_hint"] = "可在作品详情继续排期或更新草稿"
    return out


def list_wechat_drafts(
    conn: Any,
    config: AppConfig,
    *,
    limit: int = 50,
    status: str | None = None,
) -> list[dict[str, Any]]:
    sql = """
        SELECT d.id, d.article_id, d.media_id, d.status, d.payload_json, d.created_at,
               a.title, a.status AS article_status,
               COALESCE(c.slug, 'default') AS collection_slug,
               COALESCE(c.name, '默认集合') AS collection_name
        FROM wechat_drafts d
        JOIN articles a ON a.id = d.article_id
        LEFT JOIN collections c ON c.id = a.collection_id
        WHERE (a.deleted_at IS NULL OR a.deleted_at = '')
          AND d.status IN ('created', 'updated')
    """
    params: list[Any] = []
    if status and status.strip():
        sql += " AND d.status = ?"
        params.append(status.strip().lower())
    sql += " ORDER BY d.created_at DESC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    return [enrich_draft_row(r, config) for r in rows]


def get_wechat_draft(conn: Any, config: AppConfig, draft_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT d.id, d.article_id, d.media_id, d.status, d.payload_json, d.created_at,
               a.title, a.summary, a.status AS article_status, a.cover_path,
               COALESCE(c.slug, 'default') AS collection_slug,
               COALESCE(c.name, '默认集合') AS collection_name
        FROM wechat_drafts d
        JOIN articles a ON a.id = d.article_id
        LEFT JOIN collections c ON c.id = a.collection_id
        WHERE d.id = ? AND (a.deleted_at IS NULL OR a.deleted_at = '')
        """,
        (int(draft_id),),
    ).fetchone()
    if row is None:
        return None
    out = enrich_draft_row(dict(row), config)
    out["has_cover"] = bool((row["cover_path"] or "").strip())
    out["cover_url"] = f"/media/cover/{row['article_id']}" if out["has_cover"] else None
    out["summary_preview"] = (row["summary"] or "")[:160]
    return out


def drafts_summary(conn: Any, config: AppConfig) -> dict[str, Any]:
    total = conn.execute(
        """
        SELECT COUNT(*) AS cnt FROM wechat_drafts d
        JOIN articles a ON a.id = d.article_id
        WHERE (a.deleted_at IS NULL OR a.deleted_at = '')
        """
    ).fetchone()["cnt"]
    by_status = conn.execute(
        """
        SELECT d.status, COUNT(*) AS cnt FROM wechat_drafts d
        JOIN articles a ON a.id = d.article_id
        WHERE (a.deleted_at IS NULL OR a.deleted_at = '')
        GROUP BY d.status
        """
    ).fetchall()
    counts = {str(r["status"]): int(r["cnt"]) for r in by_status}
    mode = (config.wechat_mode or "mock").strip().lower()
    draft_only = mode == "real" and not bool(config.wechat_enable_publish)
    note = (
        "当前为演练模式：列表中的 media_id 均为本地记录，不代表公众号后台真实草稿。"
        if mode == "mock"
        else "列表仅包含通过本工具创建并写入数据库的草稿记录。"
    )
    cleanup_hint = None
    cleanup_cli = None
    if draft_only:
        cleanup_hint = (
            "真实草稿-only 测试会在公众号后台留下草稿。"
            "测试后请登录公众号后台手动删除测试草稿；"
            "本页 media_id 可对照核对，避免残留占用草稿箱配额。"
        )
        cleanup_cli = "python scripts/real_api_check.py --samples 3  # 报告见 reports/real_api_runs/"
    return {
        "total": int(total),
        "counts": counts,
        "mode": mode,
        "draft_only": draft_only,
        "summary_label": f"共 {total} 条本地草稿记录",
        "mode_note": note,
        "cleanup_hint": cleanup_hint,
        "cleanup_cli": cleanup_cli,
    }
