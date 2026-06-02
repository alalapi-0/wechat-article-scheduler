"""单篇文章详情与发布前检查（收敛 Round 11 / round_066）。"""

from __future__ import annotations

from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.content_quality import article_content_hints
from wechat_article_scheduler.parser import clamp_summary
from wechat_article_scheduler.publish_body import publish_body_for
from wechat_article_scheduler.publish_config import human_publish_config_summary, parse_publish_config, defaults_from_rules
from wechat_article_scheduler.publish_preview import _maybe_unescape_html
from wechat_article_scheduler.web.schedule_display import format_scheduled_at
from wechat_article_scheduler.web.user_copy import (
    article_workflow_hint,
    label_article_status,
    label_job_status,
    label_mode,
)


def _article_row(conn: Any, article_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT a.id, a.title, a.summary, a.body, a.status, a.source_path, a.cover_path,
               a.cover_config_json, a.created_at, a.updated_at,
               COALESCE(c.slug, 'default') AS collection_slug,
               COALESCE(c.name, '默认集合') AS collection_name,
               EXISTS(SELECT 1 FROM wechat_drafts d WHERE d.article_id = a.id) AS has_wechat_draft
        FROM articles a
        LEFT JOIN collections c ON c.id = a.collection_id
        WHERE a.id = ? AND (a.deleted_at IS NULL OR a.deleted_at = '')
        """,
        (article_id,),
    ).fetchone()
    return dict(row) if row else None


def _latest_job(conn: Any, article_id: int, config: AppConfig) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT j.id, j.scheduled_at, j.status, j.retry_count, j.adapter_mode,
               j.publish_config_json, j.updated_at
        FROM publish_jobs j
        WHERE j.article_id = ? AND j.status != 'cancelled'
        ORDER BY j.id DESC LIMIT 1
        """,
        (article_id,),
    ).fetchone()
    if not row:
        return None
    out = dict(row)
    pub = parse_publish_config(out.get("publish_config_json"), defaults=defaults_from_rules(config))
    out["publish_config_label"] = " · ".join(human_publish_config_summary(pub))
    out["scheduled_at_label"] = format_scheduled_at(out.get("scheduled_at"))
    out["status_label"] = label_job_status(out.get("status"))
    return out


def _draft_info(conn: Any, article_id: int, *, mode: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT id, media_id, status, created_at FROM wechat_drafts
        WHERE article_id = ? AND status IN ('created', 'updated')
        ORDER BY id DESC LIMIT 1
        """,
        (article_id,),
    ).fetchone()
    if not row:
        return {
            "has_draft": False,
            "can_update": False,
            "label": "尚未创建微信草稿",
            "mock_note": None,
        }
    media = row["media_id"] or ""
    note = None
    if mode == "mock" and str(media).startswith("mock_"):
        note = "当前为演练模式：更新仅写入本地记录，不会改动公众号后台"
    status = row["status"] or "created"
    label = "已更新微信草稿（演练）" if status == "updated" and mode == "mock" else (
        "已更新微信草稿" if status == "updated" else (
            "已创建微信草稿（演练记录）" if mode == "mock" else "已创建微信草稿"
        )
    )
    return {
        "has_draft": True,
        "can_update": True,
        "draft_id": int(row["id"]),
        "label": label,
        "created_at": row["created_at"],
        "mock_note": note,
        "update_hint": "修改标题/正文/封面后，可点「更新微信草稿」同步到已有草稿",
    }


def _article_preflight_checks(row: dict[str, Any], config: AppConfig) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    mode = (config.wechat_mode or "mock").strip().lower()
    publish_on = bool(config.wechat_enable_publish)
    will_publish = mode == "real" and publish_on

    checks.append(
        {
            "id": "mode",
            "ok": True,
            "label": "运行模式",
            "detail": label_mode(mode),
        }
    )

    has_cover = bool((row.get("cover_path") or "").strip()) or bool(config.wechat_default_thumb_path)
    checks.append(
        {
            "id": "cover",
            "ok": has_cover,
            "label": "封面",
            "detail": "已设置封面" if (row.get("cover_path") or "").strip() else (
                "将使用默认封面" if config.wechat_default_thumb_path else "缺少封面，建议上传"
            ),
        }
    )

    summary = (row.get("summary") or "").strip()
    digest_truncated = bool(summary) and len(summary) > 120
    checks.append(
        {
            "id": "digest",
            "ok": not digest_truncated,
            "label": "摘要",
            "detail": "摘要长度正常"
            if not digest_truncated
            else f"摘要超过 120 字，发布时将截断为：{clamp_summary(summary, 120)[:40]}…",
        }
    )

    title = (row.get("title") or "").strip()
    body = row.get("body") or ""
    if not body.strip():
        checks.append({"id": "body", "ok": False, "label": "正文", "detail": "正文为空"})
    elif title and publish_body_for(title, body) != body.strip():
        checks.append({"id": "title_dup", "ok": False, "label": "标题重复", "detail": "正文首行与标题重复，发布时会自动处理"})
    if "&lt;" in body and _maybe_unescape_html(body) != body:
        checks.append({"id": "html", "ok": False, "label": "正文格式", "detail": "正文疑似转义 HTML，请先预览确认"})

    if will_publish:
        blocking = [c for c in checks if not c.get("ok") and c["id"] in ("cover", "body", "html")]
    else:
        blocking = []
    for c in checks:
        c["required"] = c["id"] in ("cover", "body", "html") and will_publish and not c["ok"]
    return checks


def suggest_detail_actions(
    *,
    row: dict[str, Any],
    job: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    config: AppConfig,
) -> dict[str, Any]:
    actions: list[str] = []
    primary = "preview"
    headline = "查看预览确认正文与封面"

    if job and job.get("status") == "pending":
        primary = "wait"
        headline = f"已排期：{job.get('scheduled_at_label') or '待发布'}"
        actions.append("到时间后在工作台执行「执行到点发布」")
    elif job and job.get("status") == "failed":
        primary = "retry"
        headline = "上次发布失败"
        actions.append("请重新安排发布时间或检查正文/封面")
    elif (row.get("status") or "") == "imported" and (
        job is None or job.get("status") not in ("pending", "running")
    ):
        primary = "schedule"
        headline = "尚未安排发布时间"
        actions.append("返回工作台点「自动推荐时间」或「安排时间」")
    elif not (row.get("cover_path") or "").strip() and not config.wechat_default_thumb_path:
        primary = "cover"
        headline = "建议先设置封面"
        actions.append("返回工作台为作品上传或绑定封面")
    elif bool(row.get("has_wechat_draft")):
        actions.append("改稿后可在本页「更新微信草稿」同步（无草稿时需先执行发布流程）")

    failed_checks = [c for c in checks if not c.get("ok")]
    for c in failed_checks[:2]:
        actions.append(c["detail"])

    return {"primary_action": primary, "headline": headline, "hints": actions[:4]}


def build_article_detail(config: AppConfig, conn: Any, article_id: int) -> dict[str, Any]:
    row = _article_row(conn, article_id)
    if row is None:
        return {}
    job = _latest_job(conn, article_id, config)
    mode = (config.wechat_mode or "mock").strip().lower()
    draft = _draft_info(conn, article_id, mode=mode)
    checks = _article_preflight_checks(row, config)
    workflow = article_workflow_hint(
        status=row.get("status"),
        latest_job_status=job.get("status") if job else None,
        has_wechat_draft=bool(row.get("has_wechat_draft")),
    )
    body = row.get("body") or ""
    return {
        "id": article_id,
        "title": row.get("title") or "",
        "summary": row.get("summary") or "",
        "summary_preview": clamp_summary((row.get("summary") or "").strip() or row.get("title") or "", 120),
        "body_chars": len(body),
        "status": row.get("status"),
        "status_label": label_article_status(row.get("status")),
        "workflow_hint": workflow,
        "collection_slug": row.get("collection_slug"),
        "collection_name": row.get("collection_name"),
        "has_cover": bool((row.get("cover_path") or "").strip()),
        "cover_url": f"/media/cover/{article_id}" if (row.get("cover_path") or "").strip() else None,
        "content_hints": article_content_hints(row.get("title") or "", body),
        "latest_job": job,
        "wechat_draft": draft,
        "preflight_checks": checks,
        "workbench": suggest_detail_actions(row=row, job=job, checks=checks, config=config),
        "mode_label": label_mode(mode),
        "preview_url": f"/api/articles/{article_id}/render-preview",
    }
