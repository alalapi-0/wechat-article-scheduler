"""调度领域：单条发布任务的状态流转与执行。"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters import get_adapter
from wechat_article_scheduler.adapters.base import DraftOptions, DraftResult
from wechat_article_scheduler.adapters.wechat_http import WechatApiError
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.parser import clamp_summary
from wechat_article_scheduler.scheduler.draft_idempotency import (
    draft_result_from_reuse,
    find_reusable_draft_media_id,
)
from wechat_article_scheduler.wechat_errors import format_job_failure
from wechat_article_scheduler.publish_config import (
    defaults_from_rules,
    parse_publish_config,
    should_submit_publish,
)
from wechat_article_scheduler.scheduler.claim import clear_job_claim, schedule_failure_retry
from wechat_article_scheduler.draft_update import (
    attach_fingerprint_to_payload,
    draft_content_fingerprint,
)
from wechat_article_scheduler.scheduler.policies import safe_payload

logger = logging.getLogger(__name__)


def _row_get(row: sqlite3.Row, key: str) -> str | None:
    """安全读取可选列（行可能不含该列）。"""
    try:
        return row[key]
    except (IndexError, KeyError):
        return None


def execute_due_job(
    conn: sqlite3.Connection,
    job: sqlite3.Row,
    *,
    config: AppConfig,
    adapter_mode: str,
    published_dir: Path,
    stats: dict[str, int],
) -> None:
    """执行一条已到期的 pending 任务（非 DRY_RUN）。"""
    job_id = int(job["job_id"])
    article_id = int(job["article_id"])
    retry_count = int(job["retry_count"] or 0)
    adapter = get_adapter(config)

    try:
        raw_summary = (job["summary"] or "").strip() or (job["title"] or "")
        digest_summary = clamp_summary(raw_summary, 120)
        if digest_summary != raw_summary:
            db.log_event(
                conn,
                entity_type="publish_job",
                entity_id=job_id,
                event_type="digest_truncated_warning",
                payload=json.dumps(
                    {
                        "article_id": article_id,
                        "from_chars": len(raw_summary),
                        "to_chars": len(digest_summary),
                    },
                    ensure_ascii=False,
                ),
            )
        pub_cfg = parse_publish_config(
            _row_get(job, "publish_config_json"),
            defaults=defaults_from_rules(config),
        )
        draft_opts = DraftOptions(
            need_open_comment=1 if pub_cfg.need_open_comment else 0,
            only_fans_can_comment=1 if pub_cfg.only_fans_can_comment else 0,
            author=pub_cfg.author,
            content_source_url=pub_cfg.content_source_url,
        )
        content_hash = _row_get(job, "content_hash")
        reused_media = find_reusable_draft_media_id(
            conn, article_id=article_id, content_hash=content_hash
        )
        draft: DraftResult
        if reused_media:
            draft = draft_result_from_reuse(reused_media)
            db.log_event(
                conn,
                entity_type="publish_job",
                entity_id=job_id,
                event_type="draft_idempotent_reuse",
                payload=json.dumps(
                    {"article_id": article_id, "media_id": reused_media[:32]},
                    ensure_ascii=False,
                ),
            )
            stats["draft_reused"] = stats.get("draft_reused", 0) + 1
        else:
            draft = adapter.create_draft(
                title=job["title"],
                summary=digest_summary,
                body=job["body"],
                cover_path=_row_get(job, "cover_path"),
                options=draft_opts,
            )
            fp = draft_content_fingerprint(
                title=job["title"] or "",
                summary=job["summary"] or "",
                body=job["body"] or "",
                cover_path=_row_get(job, "cover_path"),
            )
            conn.execute(
                """
                INSERT INTO wechat_drafts (article_id, media_id, status, payload_json)
                VALUES (?, ?, 'created', ?)
                """,
                (article_id, draft.media_id, attach_fingerprint_to_payload(draft, fp)),
            )
        force_publish = should_submit_publish(app_config=config, job_config=pub_cfg)
        pub = adapter.submit_publish(draft.media_id, force=force_publish)
        conn.execute(
            """
            UPDATE publish_jobs
            SET status = 'done',
                claim_token = NULL,
                claimed_at = NULL,
                next_retry_at = NULL,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (job_id,),
        )
        draft_only = bool(pub.get("skipped"))
        if draft_only and pub_cfg.publish_action == "publish" and not force_publish:
            db.log_event(
                conn,
                entity_type="publish_job",
                entity_id=job_id,
                event_type="publish_skipped_draft_only",
                payload=safe_payload(
                    {
                        "reason": "WECHAT_ENABLE_PUBLISH=false 或任务/模式不允许正式发布",
                        "publish_action": pub_cfg.publish_action,
                    }
                ),
            )
        if draft_only:
            conn.execute(
                "UPDATE articles SET updated_at = datetime('now') WHERE id = ?",
                (article_id,),
            )
            stats["drafted"] = stats.get("drafted", 0) + 1
        else:
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
            event_type="draft_created" if draft_only else "job_done",
            payload=safe_payload(pub),
        )
        stats["processed"] += 1
    except Exception as exc:  # noqa: BLE001 — CLI 需汇总失败数
        failure_payload = format_job_failure(exc)
        final_status = schedule_failure_retry(
            conn,
            job_id=job_id,
            article_id=article_id,
            retry_count=retry_count,
            config=config,
            failure_payload=failure_payload,
        )
        clear_job_claim(conn, job_id)
        if isinstance(exc, WechatApiError):
            logger.warning(
                "任务 %s 失败: %s (status=%s)",
                job_id,
                exc.human_hint,
                final_status,
            )
        else:
            logger.exception("任务 %s 失败 (status=%s)", job_id, final_status)
        if final_status == "failed":
            stats["failed"] += 1
        else:
            stats["retry_scheduled"] = stats.get("retry_scheduled", 0) + 1


def record_dry_run_job(
    conn: sqlite3.Connection,
    job: sqlite3.Row,
    *,
    stats: dict[str, int],
) -> None:
    job_id = int(job["job_id"])
    article_id = int(job["article_id"])
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
