"""调度领域：单条发布任务的状态流转与执行。"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters import get_adapter
from wechat_article_scheduler.adapters.base import DraftOptions
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.parser import clamp_summary
from wechat_article_scheduler.publish_config import (
    defaults_from_rules,
    parse_publish_config,
    should_submit_publish,
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

    conn.execute(
        "UPDATE publish_jobs SET status = 'running', updated_at = datetime('now') WHERE id = ?",
        (job_id,),
    )
    conn.commit()

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
        draft = adapter.create_draft(
            title=job["title"],
            summary=digest_summary,
            body=job["body"],
            cover_path=_row_get(job, "cover_path"),
            options=draft_opts,
        )
        conn.execute(
            """
            INSERT INTO wechat_drafts (article_id, media_id, status, payload_json)
            VALUES (?, ?, 'created', ?)
            """,
            (article_id, draft.media_id, safe_payload(draft.raw_response)),
        )
        force_publish = should_submit_publish(app_config=config, job_config=pub_cfg)
        pub = adapter.submit_publish(draft.media_id, force=force_publish)
        conn.execute(
            "UPDATE publish_jobs SET status = 'done', updated_at = datetime('now') WHERE id = ?",
            (job_id,),
        )
        draft_only = bool(pub.get("skipped"))
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
        logger.exception("任务 %s 失败 (retry %s)", job_id, new_retry)
        stats["failed"] += 1


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
