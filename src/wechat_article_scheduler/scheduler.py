"""执行到期发布任务与后台调度循环。"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters import get_adapter
from wechat_article_scheduler.config import AppConfig


def _safe_payload(data: dict) -> str:
    """序列化事件载荷，剔除疑似密钥字段。"""
    redacted = {k: v for k, v in data.items() if "token" not in k.lower() and "secret" not in k.lower()}
    return json.dumps(redacted, ensure_ascii=False)


def run_due_jobs(config: AppConfig) -> dict[str, int]:
    """
    处理 scheduled_at <= now 的 pending 任务：创建草稿、标记完成、移动文章。

    返回：processed, skipped_future, failed
    """
    stats = {"processed": 0, "skipped_future": 0, "failed": 0}
    now = datetime.now().isoformat(timespec="seconds")
    adapter = get_adapter(config)
    published_dir = config.root / "articles" / "published"
    published_dir.mkdir(parents=True, exist_ok=True)

    with db.connect(config.database_path) as conn:
        jobs = conn.execute(
            """
            SELECT j.id AS job_id, j.article_id, j.scheduled_at, j.status,
                   a.title, a.summary, a.body, a.source_path
            FROM publish_jobs j
            JOIN articles a ON a.id = j.article_id
            WHERE j.status = 'pending'
            ORDER BY j.scheduled_at ASC
            """
        ).fetchall()

        for job in jobs:
            if job["scheduled_at"] > now:
                stats["skipped_future"] += 1
                continue

            job_id = int(job["job_id"])
            article_id = int(job["article_id"])
            conn.execute(
                "UPDATE publish_jobs SET status = 'running', updated_at = datetime('now') WHERE id = ?",
                (job_id,),
            )
            conn.commit()

            try:
                draft = adapter.create_draft(
                    title=job["title"],
                    summary=job["summary"] or "",
                    body=job["body"],
                )
                conn.execute(
                    """
                    INSERT INTO wechat_drafts (article_id, media_id, status, payload_json)
                    VALUES (?, ?, 'created', ?)
                    """,
                    (article_id, draft.media_id, _safe_payload(draft.raw_response)),
                )
                pub = adapter.submit_publish(draft.media_id)
                conn.execute(
                    "UPDATE publish_jobs SET status = 'done', updated_at = datetime('now') WHERE id = ?",
                    (job_id,),
                )
                conn.execute(
                    "UPDATE articles SET status = 'published', updated_at = datetime('now') WHERE id = ?",
                    (article_id,),
                )
                src = Path(job["source_path"])
                if src.exists():
                    dest = published_dir / src.name
                    if dest.exists():
                        dest = published_dir / f"{src.stem}_{article_id}{src.suffix}"
                    src.rename(dest)
                    conn.execute(
                        "UPDATE articles SET source_path = ? WHERE id = ?",
                        (str(dest), article_id),
                    )
                db.log_event(
                    conn,
                    entity_type="publish_job",
                    entity_id=job_id,
                    event_type="job_done",
                    payload=_safe_payload(pub),
                )
                stats["processed"] += 1
            except Exception as exc:  # noqa: BLE001 — CLI 需汇总失败数
                conn.execute(
                    "UPDATE publish_jobs SET status = 'failed', updated_at = datetime('now') WHERE id = ?",
                    (job_id,),
                )
                db.log_event(
                    conn,
                    entity_type="publish_job",
                    entity_id=job_id,
                    event_type="job_failed",
                    payload=str(exc)[:500],
                )
                stats["failed"] += 1
            conn.commit()

    return stats


def scheduler_loop(config: AppConfig) -> None:
    """按 SCHEDULER_POLL_SECONDS 轮询执行到期任务（Ctrl+C 退出）。"""
    poll = max(5, config.scheduler_poll_seconds)
    print(f"调度器启动：每 {poll}s 检查一次到期任务（mode={config.wechat_mode}）")
    while True:
        stats = run_due_jobs(config)
        if stats["processed"] or stats["failed"]:
            print(f"run-once: {stats}")
        time.sleep(poll)
