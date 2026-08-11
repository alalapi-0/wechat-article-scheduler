"""微信草稿更新：适配器调用、本地记录与内容指纹幂等。"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters import get_adapter
from wechat_article_scheduler.adapters.base import DraftOptions, DraftResult
from wechat_article_scheduler.adapters.wechat_http import WechatApiError
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.content_quality import content_block_reason
from wechat_article_scheduler.publish_config import defaults_from_rules, parse_publish_config
from wechat_article_scheduler.parser import clamp_summary
from wechat_article_scheduler.scheduler.policies import safe_payload
from wechat_article_scheduler.wechat_errors import format_job_failure
from wechat_article_scheduler.cover_assets.index import (
    InvalidCoverError,
    check_configured_cover,
    managed_cover_bytes,
    secure_cover_bytes,
)

logger = logging.getLogger(__name__)

ACTIVE_DRAFT_STATUSES = ("created", "updated")


def draft_content_fingerprint(
    *,
    title: str,
    summary: str,
    body: str,
    cover_path: str | None,
    config: AppConfig | None = None,
) -> str:
    cover = (cover_path or "").strip()
    cover_digest = "<no-cover>"
    if cover and config is not None:
        try:
            cover_digest = hashlib.sha256(managed_cover_bytes(config, cover)).hexdigest()
        except (InvalidCoverError, OSError):
            cover_digest = "<invalid-cover>"
    elif cover:
        cover_digest = "<untrusted-cover>"
    elif config is not None and str(config.wechat_default_thumb_path or "").strip():
        default = Path(config.wechat_default_thumb_path)
        try:
            cover_digest = hashlib.sha256(
                secure_cover_bytes(default, allowed_roots=(default.parent,))
            ).hexdigest()
        except (InvalidCoverError, OSError):
            cover_digest = "<invalid-default-cover>"
    return draft_content_fingerprint_from_cover_digest(
        title=title,
        summary=summary,
        body=body,
        cover_digest=cover_digest,
    )


def draft_content_fingerprint_from_cover_digest(
    *, title: str, summary: str, body: str, cover_digest: str
) -> str:
    """Fingerprint the exact canonical fields and already-read cover payload."""
    normalized_summary = clamp_summary((summary or "").strip() or (title or ""), 120)
    blob = "\n".join(
        [
            (title or "").strip(),
            normalized_summary,
            (body or "").strip(),
            cover_digest,
        ]
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def fingerprint_from_payload(payload_json: str | None) -> str | None:
    raw = (payload_json or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    fp = data.get("content_fingerprint")
    return str(fp).strip() if fp else None


def find_active_draft(
    conn: Any,
    article_id: int,
    *,
    adapter_mode: str,
) -> dict[str, Any] | None:
    mode = (adapter_mode or "").strip().lower()
    if mode not in {"mock", "real"}:
        return None
    row = conn.execute(
        """
        SELECT d.id, d.media_id, d.status, d.payload_json, d.created_at,
               d.adapter_mode, d.publish_job_id
        FROM wechat_drafts AS d
        INNER JOIN publish_jobs AS j ON j.id = d.publish_job_id
        WHERE d.article_id = ?
          AND d.status IN ('created', 'updated')
          AND d.adapter_mode = ?
          AND j.article_id = d.article_id
          AND j.adapter_mode = d.adapter_mode
          AND j.status IN ('done', 'waiting_confirmation')
          AND d.media_id IS NOT NULL
          AND TRIM(d.media_id) != ''
        ORDER BY d.id DESC
        LIMIT 1
        """,
        (int(article_id), mode),
    ).fetchone()
    return dict(row) if row else None


def attach_fingerprint_to_payload(draft: DraftResult, fingerprint: str) -> str:
    raw = dict(draft.raw_response) if isinstance(draft.raw_response, dict) else {}
    raw.setdefault("content_fingerprint", fingerprint)
    return safe_payload(raw)


def humanize_update_result(result: dict[str, Any]) -> list[str]:
    if result.get("skipped_unchanged"):
        return ["作品内容与上次草稿一致，无需更新"]
    if result.get("ok"):
        mode = result.get("mode", "mock")
        if mode == "mock":
            return ["演练模式：已更新本地草稿记录（未改动公众号后台）"]
        return ["已更新微信公众号草稿"]
    err = result.get("error") or "更新失败"
    return [str(err)]


def update_article_wechat_draft(config: AppConfig, article_id: int) -> dict[str, Any]:
    """
    将当前作品内容同步到已有微信草稿（draft/update）。

    无活跃草稿时返回 ok=False；内容指纹未变时 skipped_unchanged=True。
    """
    mode = str(config.wechat_mode or "").strip().lower()
    if mode not in {"mock", "real"}:
        return {"ok": False, "error": "当前 WECHAT_MODE 无效，已拒绝更新草稿"}

    with db.connect(config.database_path) as conn:
        article = conn.execute(
            """
            SELECT id, title, summary, body, cover_path, content_hash, status
            FROM articles
            WHERE id = ? AND (deleted_at IS NULL OR deleted_at = '')
            """,
            (int(article_id),),
        ).fetchone()
        if article is None:
            return {"ok": False, "error": "作品不存在或已在回收站"}

        if mode == "real":
            blocked = content_block_reason(article["title"] or "", article["body"] or "")
            if blocked:
                return {
                    "ok": False,
                    "error": f"内容预检未通过：{blocked}",
                    "article_id": int(article_id),
                }

        draft_row = find_active_draft(conn, int(article_id), adapter_mode=mode)
        if draft_row is None:
            other = conn.execute(
                """
                SELECT adapter_mode, publish_job_id
                FROM wechat_drafts
                WHERE article_id = ?
                  AND status IN ('created', 'updated')
                  AND media_id IS NOT NULL
                  AND TRIM(media_id) != ''
                ORDER BY id DESC LIMIT 1
                """,
                (int(article_id),),
            ).fetchone()
            if other is not None:
                return {
                    "ok": False,
                    "error": "已有草稿缺少与当前模式匹配的完整来源记录，已拒绝跨模式更新",
                    "article_id": int(article_id),
                }
            return {
                "ok": False,
                "error": "尚未创建微信草稿，请先执行到点草稿创建",
                "fallback": "可先在工作台安排草稿创建时间并执行 run-once",
            }

        media_id = str(draft_row["media_id"])
        fingerprint = draft_content_fingerprint(
            title=article["title"] or "",
            summary=article["summary"] or "",
            body=article["body"] or "",
            cover_path=article["cover_path"],
            config=config,
        )
        prev_fp = fingerprint_from_payload(draft_row.get("payload_json"))
        if prev_fp and prev_fp == fingerprint:
            return {
                "ok": True,
                "skipped_unchanged": True,
                "article_id": int(article_id),
                "media_id": media_id,
                "mode": mode,
                "human": humanize_update_result(
                    {"ok": True, "skipped_unchanged": True, "mode": mode}
                ),
            }

        job_row = conn.execute(
            """
            SELECT publish_config_json FROM publish_jobs
            WHERE id = ? AND article_id = ? AND adapter_mode = ?
            """,
            (int(draft_row["publish_job_id"]), int(article_id), mode),
        ).fetchone()
        pub_cfg = parse_publish_config(
            job_row["publish_config_json"] if job_row else None,
            defaults=defaults_from_rules(config),
        )
        draft_opts = DraftOptions(
            need_open_comment=1 if pub_cfg.need_open_comment else 0,
            only_fans_can_comment=1 if pub_cfg.only_fans_can_comment else 0,
            author=pub_cfg.author,
            content_source_url=pub_cfg.content_source_url,
        )

        if mode == "real":
            if not (str(config.wechat_app_id or "").strip() and str(config.wechat_app_secret or "").strip()):
                return {"ok": False, "error": "真实模式凭证未配置，已在联网前拒绝更新"}
            cover_check = check_configured_cover(config, article["cover_path"])
            if not cover_check["ok"]:
                return {"ok": False, "error": str(cover_check["message"])}
        adapter = get_adapter(config)
        try:
            result = adapter.update_draft(
                media_id=media_id,
                title=article["title"] or "",
                summary=(article["summary"] or "").strip() or (article["title"] or ""),
                body=article["body"] or "",
                cover_path=article["cover_path"],
                options=draft_opts,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("草稿更新失败 article=%s: %s", article_id, exc)
            return {
                "ok": False,
                "error": format_job_failure(exc) if not isinstance(exc, WechatApiError) else exc.human_hint,
                "article_id": int(article_id),
            }

        payload = attach_fingerprint_to_payload(result, fingerprint)
        conn.execute(
            """
            UPDATE wechat_drafts
            SET status = 'superseded'
            WHERE article_id = ?
              AND adapter_mode = ?
              AND publish_job_id = ?
              AND status IN ('created', 'updated')
            """,
            (int(article_id), mode, int(draft_row["publish_job_id"])),
        )
        conn.execute(
            """
            INSERT INTO wechat_drafts (
                article_id, media_id, status, payload_json,
                adapter_mode, publish_job_id
            ) VALUES (?, ?, 'updated', ?, ?, ?)
            """,
            (
                int(article_id),
                result.media_id,
                payload,
                mode,
                int(draft_row["publish_job_id"]),
            ),
        )
        new_draft_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        db.log_event(
            conn,
            entity_type="wechat_draft",
            entity_id=new_draft_id,
            event_type="draft_updated",
            payload=json.dumps(
                {
                    "article_id": int(article_id),
                    "media_id": result.media_id[:32],
                    "superseded_draft_id": int(draft_row["id"]),
                    "mode": mode,
                },
                ensure_ascii=False,
            ),
        )
        conn.commit()

    return {
        "ok": True,
        "article_id": int(article_id),
        "draft_id": new_draft_id,
        "media_id": result.media_id,
        "mode": mode,
        "human": humanize_update_result({"ok": True, "mode": mode}),
    }
