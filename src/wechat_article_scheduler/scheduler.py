"""执行到期发布任务与后台调度循环。"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters import get_adapter
from wechat_article_scheduler.config import AppConfig

logger = logging.getLogger(__name__)


def _safe_payload(data: dict) -> str:
    """序列化事件载荷，剔除疑似密钥字段。"""
    redacted = {k: v for k, v in data.items() if "token" not in k.lower() and "secret" not in k.lower()}
    return json.dumps(redacted, ensure_ascii=False)


def run_due_jobs(config: AppConfig) -> dict[str, int]:
    """
    处理 scheduled_at <= now 的 pending 任务：创建草稿、标记完成、移动文章。

    DRY_RUN=true 时只记录计划动作，不调用适配器。
    返回：processed, skipped_future, failed, dry_run, skipped_max_retries
    """
    stats = {
        "processed": 0,
        "skipped_future": 0,
        "failed": 0,
        "dry_run": 0,
        "skipped_max_retries": 0,
    }
    now = datetime.now().isoformat(timespec="seconds")
    adapter = get_adapter(config) if not config.dry_run else None
    published_dir = config.root / "articles" / "published"
    published_dir.mkdir(parents=True, exist_ok=True)
    max_retries = max(1, config.max_job_retries)

    with db.connect(config.database_path) as conn:
        jobs = conn.execute(
            """
            SELECT j.id AS job_id, j.article_id, j.scheduled_at, j.status, j.retry_count,
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
            retry_count = int(job["retry_count"] or 0)
            if retry_count >= max_retries:
                stats["skipped_max_retries"] += 1
                logger.warning(
                    "任务 %s 已达最大重试 %s/%s，跳过",
                    job_id,
                    retry_count,
                    max_retries,
                )
                continue

            if config.dry_run:
                logger.info(
                    "[DRY_RUN] 将处理 job=%s article=%s title=%r",
                    job_id,
                    article_id,
                    job["title"],
                )
                db.log_event(
                    conn,
                    entity_type="publish_job",
                    entity_id=job_id,
                    event_type="dry_run_planned",
                    payload=json.dumps({"article_id": article_id, "title": job["title"]}, ensure_ascii=False),
                )
                stats["dry_run"] += 1
                continue

            conn.execute(
                "UPDATE publish_jobs SET status = 'running', updated_at = datetime('now') WHERE id = ?",
                (job_id,),
            )
            conn.commit()

            try:
                assert adapter is not None
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
                new_retry = retry_count + 1
                conn.execute(
                    """
                    UPDATE publish_jobs
                    SET status = 'failed', retry_count = ?, updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (new_retry, job_id),
                )
                db.log_event(
                    conn,
                    entity_type="publish_job",
                    entity_id=job_id,
                    event_type="job_failed",
                    payload=str(exc)[:500],
                )
                logger.exception("任务 %s 失败 (retry %s/%s)", job_id, new_retry, max_retries)
                stats["failed"] += 1
            conn.commit()

    if config.dry_run and stats["dry_run"]:
        _write_dry_run_report(config, stats)
    return stats


def _write_dry_run_report(config: AppConfig, stats: dict[str, int]) -> None:
    """将 dry-run 摘要写入 data/reports/（便于人工核对）。"""
    report_dir = config.root / "data" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = report_dir / f"dry_run_{stamp}.json"
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "stats": stats,
        "wechat_mode": config.wechat_mode,
        "dry_run": True,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("DRY_RUN 报告已写入 %s", path)


def scheduler_loop(config: AppConfig) -> None:
    """按 SCHEDULER_POLL_SECONDS 轮询执行到期任务（Ctrl+C 退出）。"""
    poll = max(5, config.scheduler_poll_seconds)
    logger.info("调度器启动：每 %ss 检查到期任务（mode=%s dry_run=%s）", poll, config.wechat_mode, config.dry_run)
    print(f"调度器启动：每 {poll}s 检查一次到期任务（mode={config.wechat_mode}）")
    consecutive_errors = 0
    while True:
        try:
            stats = run_due_jobs(config)
            consecutive_errors = 0
            if any(stats.get(k) for k in ("processed", "failed", "dry_run")):
                print(f"run-once: {stats}")
                logger.info("调度轮次结果: %s", stats)
        except Exception:  # noqa: BLE001 — 保持调度循环存活
            consecutive_errors += 1
            logger.exception("调度循环异常 (连续 %s 次)", consecutive_errors)
            if consecutive_errors >= 5:
                logger.error("连续异常过多，延长休眠至 %ss", poll * 2)
                time.sleep(poll * 2)
                consecutive_errors = 0
                continue
        time.sleep(poll)
