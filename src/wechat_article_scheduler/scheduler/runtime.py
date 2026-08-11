"""调度运行时：轮询到期任务并驱动领域执行器。"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.publish_config import (
    defaults_from_rules,
    parse_publish_config,
)
from wechat_article_scheduler.scheduler.claim import (
    acquire_run_lock,
    log_misfire_if_needed,
    new_claim_token,
    recover_stale_running_jobs,
    release_run_lock,
    try_claim_job,
)
from wechat_article_scheduler.scheduler.domain import (
    AdapterModeMismatchError,
    execute_due_job,
    record_dry_run_job,
    require_matching_adapter_mode,
)
from wechat_article_scheduler.scheduler.policies import (
    max_retries_for,
    should_skip_max_retries,
    write_dry_run_report,
)
from wechat_article_scheduler.content_quality import content_block_reason
from wechat_article_scheduler.cover_assets.index import check_configured_cover
import wechat_article_scheduler.scheduler.domain as scheduler_domain

logger = logging.getLogger(__name__)


def _parse_job_time(raw: str | None) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    normalized = text.replace(" ", "T") if "T" not in text and " " in text else text
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _job_is_due(raw: str | None, *, now: datetime) -> bool:
    scheduled = _parse_job_time(raw)
    if scheduled is None:
        logger.warning("任务计划时间格式无效，暂不执行: %r", raw)
        return False
    if scheduled.tzinfo is not None and scheduled.utcoffset() is not None:
        compare_now = datetime.now(scheduled.tzinfo).replace(microsecond=0)
    else:
        compare_now = now
    return scheduled.replace(microsecond=0) <= compare_now


def _retry_is_due(raw: str | None) -> bool:
    retry = _parse_job_time(raw)
    if retry is None:
        return not str(raw or "").strip()
    if retry.tzinfo is not None and retry.utcoffset() is not None:
        current = datetime.now(retry.tzinfo)
    else:
        current = datetime.now(timezone.utc).replace(tzinfo=None)
    return retry.replace(microsecond=0) <= current.replace(microsecond=0)


def _record_adapter_mode_mismatch(
    conn,
    *,
    job_id: int,
    article_id: int,
    error: AdapterModeMismatchError,
    stats: dict[str, int],
) -> None:
    stats["skipped_mode_mismatch"] += 1
    logger.error("任务 %s 已拒绝执行：%s", job_id, error)
    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=job_id,
        event_type="adapter_mode_mismatch",
        payload=json.dumps(
            {
                "article_id": article_id,
                "job_mode": error.job_mode,
                "process_mode": error.process_mode,
            },
            ensure_ascii=False,
        ),
    )


def run_due_jobs(config: AppConfig, *, only_auto_execute: bool = False) -> dict[str, int]:
    """
    处理 scheduled_at <= now 的 pending 任务：创建/复用草稿并标记本地完成。

    only_auto_execute=True 时仅处理 publish_config.auto_execute 为真的任务（Web 后台自动执行）。
    DRY_RUN=true 时只记录计划动作，不调用适配器。
    """
    stats = {
        "processed": 0,
        "skipped_future": 0,
        "failed": 0,
        "dry_run": 0,
        "skipped_max_retries": 0,
        "skipped_content": 0,
        "drafted": 0,
        "draft_reused": 0,
        "skipped_manual": 0,
        "skipped_locked": 0,
        "skipped_claim": 0,
        "skipped_mode_mismatch": 0,
        "recovered_stale": 0,
        "misfired": 0,
        "retry_scheduled": 0,
        "skipped_preflight": 0,
    }
    now = datetime.now().replace(microsecond=0)
    max_retries = max_retries_for(config)

    with db.connect(config.database_path) as conn:
        jobs = conn.execute(
            """
            SELECT j.id AS job_id, j.article_id, j.scheduled_at, j.status, j.retry_count,
                   j.publish_config_json, j.next_retry_at, j.source_kind, j.remote_media_id,
                   j.adapter_mode,
                   a.title, a.summary, a.body, a.source_path, a.cover_path,
                   a.content_hash
            FROM publish_jobs j
            JOIN articles a ON a.id = j.article_id
            WHERE j.status = 'pending'
              AND (a.deleted_at IS NULL OR a.deleted_at = '')
            ORDER BY j.scheduled_at ASC
            """
        ).fetchall()
        def is_eligible(job: Any, *, record_skip: bool) -> bool:
            if not _job_is_due(job["scheduled_at"], now=now):
                if record_skip:
                    stats["skipped_future"] += 1
                return False
            if not _retry_is_due(job["next_retry_at"]):
                return False
            try:
                require_matching_adapter_mode(job, config)
            except AdapterModeMismatchError as exc:
                if record_skip:
                    stats["skipped_mode_mismatch"] += 1
                logger.error("任务 %s 已拒绝执行：%s", int(job["job_id"]), exc)
                return False
            pub_cfg = parse_publish_config(
                job["publish_config_json"], defaults=defaults_from_rules(config)
            )
            if only_auto_execute and not pub_cfg.auto_execute:
                if record_skip:
                    stats["skipped_manual"] += 1
                return False
            if should_skip_max_retries(int(job["retry_count"] or 0), max_retries):
                if record_skip:
                    stats["skipped_max_retries"] += 1
                return False
            if config.dry_run:
                return True
            block_reason = content_block_reason(job["title"] or "", job["body"] or "")
            if block_reason and config.wechat_mode == "real":
                if record_skip:
                    stats["skipped_content"] += 1
                return False
            if config.wechat_mode == "real":
                if not (
                    str(config.wechat_app_id or "").strip()
                    and str(config.wechat_app_secret or "").strip()
                ):
                    if record_skip:
                        stats["skipped_preflight"] += 1
                    return False
                cover_check = check_configured_cover(config, job["cover_path"])
                if not cover_check["ok"]:
                    if record_skip:
                        stats["skipped_preflight"] += 1
                    return False
            return True

        eligible_ids = {
            int(job["job_id"]) for job in jobs if is_eligible(job, record_skip=True)
        }
        stale_timeout = max(60, int(getattr(config, "scheduler_claim_timeout_seconds", 900)))
        stale_jobs = conn.execute(
            """
            SELECT j.id AS job_id, j.article_id, j.scheduled_at, j.status, j.retry_count,
                   j.publish_config_json, j.next_retry_at, j.source_kind, j.remote_media_id,
                   j.adapter_mode, a.title, a.summary, a.body, a.source_path, a.cover_path,
                   a.content_hash
            FROM publish_jobs j
            JOIN articles a ON a.id = j.article_id
            WHERE j.status = 'running'
              AND (a.deleted_at IS NULL OR a.deleted_at = '')
              AND datetime(j.updated_at) <= datetime('now', ?)
            """
            , (f"-{stale_timeout} seconds",)
        ).fetchall()
        eligible_stale_ids = {
            int(job["job_id"]) for job in stale_jobs if is_eligible(job, record_skip=False)
        }
        if not eligible_ids and not eligible_stale_ids:
            logger.info("run-once 预检后无可执行任务: %s", stats)
            return stats

        locked_ok, holder = acquire_run_lock(conn, config)
        if not locked_ok:
            stats["skipped_locked"] = 1
            logger.warning("run-once 跳过：调度锁被 %s 持有", holder)
            conn.commit()
            return stats
        try:
            stats["recovered_stale"] = recover_stale_running_jobs(
                conn, config, eligible_job_ids=eligible_stale_ids
            )
            if stats["recovered_stale"]:
                conn.commit()

            batch_adapter = None
            for job in jobs:
                if int(job["job_id"]) not in eligible_ids:
                    continue

                job_id = int(job["job_id"])
                article_id = int(job["article_id"])
                if log_misfire_if_needed(
                    conn,
                    job_id=job_id,
                    article_id=article_id,
                    scheduled_at=job["scheduled_at"],
                    config=config,
                ):
                    stats["misfired"] += 1

                if config.dry_run:
                    record_dry_run_job(conn, job, stats=stats)
                    continue

                token = new_claim_token()
                if not try_claim_job(conn, job_id, token):
                    stats["skipped_claim"] += 1
                    logger.info("任务 %s 已被其他执行者 claim，跳过", job_id)
                    continue
                conn.commit()

                claimed_job = conn.execute(
                    """
                    SELECT adapter_mode FROM publish_jobs
                    WHERE id = ? AND status = 'running' AND claim_token = ?
                    """,
                    (job_id, token),
                ).fetchone()
                try:
                    if claimed_job is None:
                        raise AdapterModeMismatchError(
                            job_mode="<claim-lost>",
                            process_mode=str(config.wechat_mode or ""),
                        )
                    require_matching_adapter_mode(claimed_job, config)
                except AdapterModeMismatchError as exc:
                    conn.execute(
                        """
                        UPDATE publish_jobs
                        SET status = 'pending', claim_token = NULL, claimed_at = NULL,
                            updated_at = datetime('now')
                        WHERE id = ? AND status = 'running' AND claim_token = ?
                        """,
                        (job_id, token),
                    )
                    _record_adapter_mode_mismatch(
                        conn,
                        job_id=job_id,
                        article_id=article_id,
                        error=exc,
                        stats=stats,
                    )
                    continue

                if batch_adapter is None:
                    batch_adapter = scheduler_domain.get_adapter(config)

                execute_due_job(
                    conn,
                    job,
                    config=config,
                    stats=stats,
                    adapter=batch_adapter,
                )
                conn.commit()
        finally:
            release_run_lock(conn, config)
            conn.commit()

    if config.dry_run and stats["dry_run"]:
        write_dry_run_report(config, stats)
    logger.info("run-once 完成: %s", stats)
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
            if any(
                stats.get(k)
                for k in (
                    "processed",
                    "failed",
                    "dry_run",
                    "recovered_stale",
                    "retry_scheduled",
                    "skipped_locked",
                )
            ):
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
