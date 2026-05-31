"""调度运行时：轮询到期任务并驱动领域执行器。"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.scheduler.domain import execute_due_job, record_dry_run_job
from wechat_article_scheduler.publish_body import publish_body_for
from wechat_article_scheduler.scheduler.policies import (
    max_retries_for,
    should_skip_max_retries,
    write_dry_run_report,
)

logger = logging.getLogger(__name__)


def _content_block_reason(title: str | None, body: str | None) -> str | None:
    raw_body = body or ""
    if not raw_body.strip():
        return "正文为空"
    t = (title or "").strip()
    if t and publish_body_for(t, raw_body) != raw_body.strip():
        return "标题重复"
    return None


def run_due_jobs(config: AppConfig) -> dict[str, int]:
    """
    处理 scheduled_at <= now 的 pending 任务：创建草稿、标记完成、移动文章。

    DRY_RUN=true 时只记录计划动作，不调用适配器。
    真实发布是否联网由 WECHAT_MODE / WECHAT_ENABLE_PUBLISH 控制；不再有"审核"闸门。
    返回：processed, skipped_future, failed, dry_run, skipped_max_retries
    """
    stats = {
        "processed": 0,
        "skipped_future": 0,
        "failed": 0,
        "dry_run": 0,
        "skipped_max_retries": 0,
        "skipped_content": 0,
    }
    now = datetime.now().isoformat(timespec="seconds")
    published_dir = config.published_dir
    published_dir.mkdir(parents=True, exist_ok=True)
    max_retries = max_retries_for(config)

    with db.connect(config.database_path) as conn:
        jobs = conn.execute(
            """
            SELECT j.id AS job_id, j.article_id, j.scheduled_at, j.status, j.retry_count,
                   a.title, a.summary, a.body, a.source_path, a.cover_path
            FROM publish_jobs j
            JOIN articles a ON a.id = j.article_id
            WHERE j.status = 'pending'
              AND (a.deleted_at IS NULL OR a.deleted_at = '')
            ORDER BY j.scheduled_at ASC
            """
        ).fetchall()

        for job in jobs:
            if job["scheduled_at"] > now:
                stats["skipped_future"] += 1
                continue

            job_id = int(job["job_id"])
            retry_count = int(job["retry_count"] or 0)
            if should_skip_max_retries(retry_count, max_retries):
                stats["skipped_max_retries"] += 1
                logger.warning(
                    "任务 %s 已达最大重试 %s/%s，跳过",
                    job_id,
                    retry_count,
                    max_retries,
                )
                continue

            if config.dry_run:
                record_dry_run_job(conn, job, stats=stats)
                continue

            block_reason = _content_block_reason(job["title"], job["body"])
            if (
                block_reason
                and config.wechat_mode == "real"
                and config.wechat_enable_publish
            ):
                stats["skipped_content"] += 1
                logger.warning("任务 %s 因内容质量跳过: %s", job_id, block_reason)
                db.log_event(
                    conn,
                    entity_type="publish_job",
                    entity_id=job_id,
                    event_type="publish_blocked_content",
                    payload=json.dumps({"reason": block_reason}),
                )
                continue

            execute_due_job(
                conn,
                job,
                config=config,
                adapter_mode=config.wechat_mode,
                published_dir=published_dir,
                stats=stats,
            )
            conn.commit()

    if config.dry_run and stats["dry_run"]:
        write_dry_run_report(config, stats)
    return stats


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
