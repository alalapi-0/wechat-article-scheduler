"""定时发布展示辅助（Round 40）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def format_scheduled_at(iso: str | None) -> str:
    """将 ISO 时间转为普通用户可读文案。"""
    if not iso:
        return "未安排"
    raw = iso.strip()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw
    return dt.strftime("%Y年%m月%d日 %H:%M")


def summarize_schedule(conn: Any, *, limit: int = 5) -> dict[str, Any]:
    """汇总最近待发布任务与下一篇到点文章。"""
    rows = conn.execute(
        """
        SELECT j.id, j.scheduled_at, j.status, a.title, a.review_status
        FROM publish_jobs j
        JOIN articles a ON a.id = j.article_id
        WHERE j.status = 'pending'
        ORDER BY j.scheduled_at ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    pending = [dict(r) for r in rows]
    now = datetime.now().isoformat(timespec="seconds")
    due_now = [j for j in pending if (j.get("scheduled_at") or "") <= now]
    next_job = pending[0] if pending else None
    summary = "暂无待发布任务"
    if next_job:
        title = (next_job.get("title") or "（无标题）").strip()
        when = format_scheduled_at(next_job.get("scheduled_at"))
        if due_now:
            summary = f"有 {len(due_now)} 篇已到发布时间，最近一篇是《{title}》"
        else:
            summary = f"下一篇《{title}》计划在 {when} 发布"
    return {
        "pending_count": len(pending),
        "due_now_count": len(due_now),
        "next_job": next_job,
        "next_summary": summary,
        "upcoming": [
            {
                **j,
                "scheduled_at_label": format_scheduled_at(j.get("scheduled_at")),
            }
            for j in pending
        ],
    }
