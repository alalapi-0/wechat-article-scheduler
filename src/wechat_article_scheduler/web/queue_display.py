"""发布队列展示与失败原因（收敛 Round 12 / round_067）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.publish_config import (
    defaults_from_rules,
    human_publish_config_summary,
    parse_publish_config,
)
from wechat_article_scheduler.web.schedule_display import format_scheduled_at
from wechat_article_scheduler.web.user_copy import label_job_status


def failure_reasons_for_jobs(conn: Any, job_ids: list[int]) -> dict[int, str]:
    """读取各任务最近一次 job_failed 事件载荷（人话原因）。"""
    if not job_ids:
        return {}
    placeholders = ",".join("?" * len(job_ids))
    rows = conn.execute(
        f"""
        SELECT e.entity_id, e.payload_json
        FROM events e
        INNER JOIN (
            SELECT entity_id, MAX(id) AS mid
            FROM events
            WHERE entity_type = 'publish_job'
              AND event_type = 'job_failed'
              AND entity_id IN ({placeholders})
            GROUP BY entity_id
        ) t ON e.entity_id = t.entity_id AND e.id = t.mid
        """,
        job_ids,
    ).fetchall()
    return {int(r["entity_id"]): str(r["payload_json"] or "").strip() for r in rows}


def _next_hint(*, status: str, is_due: bool, failure_reason: str) -> str:
    if status == "pending":
        return "已到发布时间，可执行到点发布" if is_due else "等待到点或手动执行"
    if status == "failed":
        return "可点「重试」重新排队，或去作品详情检查"
    if status == "running":
        return "正在发布中，请稍候刷新"
    if status == "done":
        return "已完成，可在作品详情查看结果"
    return ""


def enrich_queue_job(
    row: dict[str, Any],
    config: AppConfig,
    *,
    failure_reason: str = "",
) -> dict[str, Any]:
    pub = parse_publish_config(row.get("publish_config_json"), defaults=defaults_from_rules(config))
    status = str(row.get("status") or "")
    scheduled = row.get("scheduled_at") or ""
    now = datetime.now().isoformat(timespec="seconds")
    is_due = status == "pending" and bool(scheduled) and scheduled <= now
    out = dict(row)
    out["publish_config_label"] = " · ".join(human_publish_config_summary(pub))
    out["scheduled_at_label"] = format_scheduled_at(scheduled)
    out["status_label"] = label_job_status(status)
    out["failure_reason"] = failure_reason
    out["failure_reason_short"] = (failure_reason[:160] + "…") if len(failure_reason) > 160 else failure_reason
    out["is_due_now"] = is_due
    out["next_hint"] = _next_hint(status=status, is_due=is_due, failure_reason=failure_reason)
    out["detail_url"] = f"/articles/{row.get('article_id')}"
    return out


def list_queue_jobs(
    conn: Any,
    config: AppConfig,
    *,
    limit: int = 50,
    status: str | None = None,
) -> list[dict[str, Any]]:
    sql = """
        SELECT j.id, j.article_id, j.scheduled_at, j.status, j.retry_count,
               j.adapter_mode, j.updated_at, j.publish_config_json, a.title,
               COALESCE(c.slug, 'default') AS collection_slug,
               COALESCE(c.name, '默认集合') AS collection_name
        FROM publish_jobs j
        JOIN articles a ON a.id = j.article_id
        LEFT JOIN collections c ON c.id = a.collection_id
        WHERE (a.deleted_at IS NULL OR a.deleted_at = '')
          AND j.status != 'cancelled'
    """
    params: list[Any] = []
    if status and status.strip():
        sql += " AND j.status = ?"
        params.append(status.strip().lower())
    sql += " ORDER BY j.scheduled_at ASC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    failed_ids = [int(r["id"]) for r in rows if r.get("status") == "failed"]
    reasons = failure_reasons_for_jobs(conn, failed_ids)
    return [
        enrich_queue_job(r, config, failure_reason=reasons.get(int(r["id"]), ""))
        for r in rows
    ]


def queue_summary(conn: Any) -> dict[str, Any]:
    """各状态任务数与到点 pending 数。"""
    counts: dict[str, int] = {}
    for row in conn.execute(
        """
        SELECT j.status, COUNT(*) AS cnt
        FROM publish_jobs j
        JOIN articles a ON a.id = j.article_id
        WHERE (a.deleted_at IS NULL OR a.deleted_at = '')
          AND j.status != 'cancelled'
        GROUP BY j.status
        """
    ).fetchall():
        counts[str(row["status"])] = int(row["cnt"])
    now = datetime.now().isoformat(timespec="seconds")
    due = conn.execute(
        """
        SELECT COUNT(*) AS cnt FROM publish_jobs j
        JOIN articles a ON a.id = j.article_id
        WHERE j.status = 'pending'
          AND j.scheduled_at <= ?
          AND (a.deleted_at IS NULL OR a.deleted_at = '')
        """,
        (now,),
    ).fetchone()["cnt"]
    pending = counts.get("pending", 0)
    failed = counts.get("failed", 0)
    parts = [f"待发布 {pending}", f"失败 {failed}", f"已完成 {counts.get('done', 0)}"]
    if int(due) > 0:
        parts.insert(0, f"已到点 {due}")
    next_row = conn.execute(
        """
        SELECT j.scheduled_at FROM publish_jobs j
        JOIN articles a ON a.id = j.article_id
        WHERE j.status = 'pending'
          AND (a.deleted_at IS NULL OR a.deleted_at = '')
        ORDER BY j.scheduled_at ASC LIMIT 1
        """
    ).fetchone()
    next_at = str(next_row["scheduled_at"]) if next_row else None
    if next_at and int(due) == 0 and pending > 0:
        parts.append(f"最近排期 {next_at[:16].replace('T', ' ')}")
    return {
        "counts": counts,
        "due_now": int(due),
        "next_pending_at": next_at,
        "summary_label": " · ".join(parts),
    }
