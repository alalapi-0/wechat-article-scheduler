"""单篇文章详情与草稿创建前检查。"""

from __future__ import annotations

from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.content_quality import article_content_hints
from wechat_article_scheduler.parser import clamp_summary
from wechat_article_scheduler.publish_config import (
    defaults_from_rules,
    human_publish_config_summary,
    parse_publish_config,
)
from wechat_article_scheduler.web.schedule_display import format_scheduled_at
from wechat_article_scheduler.publish_proof import (
    WAITING_CONFIRMATION,
    cannot_mark_published_without_proof,
    get_proof_for_job,
    publish_proof_eligibility,
)
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
    if str(out.get("status") or "") == "failed":
        from wechat_article_scheduler.web.queue_display import failure_reasons_for_jobs

        fr = failure_reasons_for_jobs(conn, [int(out["id"])]).get(int(out["id"]), "")
        out["failure_reason"] = fr
        out["failure_reason_short"] = (fr[:160] + "…") if len(fr) > 160 else fr
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
    from wechat_article_scheduler.web.article_preflight import article_preflight_checks

    return article_preflight_checks(row, config)


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
        headline = f"已排期：{job.get('scheduled_at_label') or '待创建草稿'}"
        actions.append("到时间后在工作台执行「执行到点草稿创建」")
    elif job and job.get("status") == WAITING_CONFIRMATION:
        primary = "proof"
        headline = "待在公众号后台确认并回填证明"
        actions.append("在公众号后台实际发布后，在本页填写公开链接或截图路径")
    elif job and job.get("status") == "failed":
        primary = "retry"
        headline = "上次草稿创建失败，可重试排队"
        actions.append("在草稿队列「失败」筛选中点「重试」，或返回工作台批量重试")
        if job.get("failure_reason_short") or job.get("failure_reason"):
            actions.append(job.get("failure_reason_short") or job.get("failure_reason"))
    elif job and job.get("status") == "done":
        primary = "draft_done"
        if bool(row.get("has_wechat_draft")):
            if (config.wechat_mode or "mock").strip().lower() == "mock":
                headline = "演练草稿已完成，未写入公众号后台"
                actions.append("切换 real 模式并重新创建后，才会产生真实公众号草稿")
                actions.append("当前更新操作也只修改本地演练记录")
            else:
                headline = "草稿已创建，可在公众号后台核对后人工发布"
                actions.append("本文仅创建草稿，未正式发布")
                actions.append("修改正文后可点「更新微信草稿」同步到已有草稿")
        else:
            headline = "草稿创建任务已完成"
            actions.append("返回工作台查看队列与事件记录")
    elif job and job.get("status") == "running":
        primary = "wait"
        headline = "正在创建草稿，请稍候"
        actions.append("完成后刷新本页查看状态")
    elif (row.get("status") or "") == "imported" and (
        job is None or job.get("status") not in ("pending", "running")
    ):
        primary = "schedule"
        headline = "尚未安排草稿创建时间"
        actions.append("返回工作台点「自动推荐时间」或「安排时间」")
    elif not (row.get("cover_path") or "").strip() and not config.wechat_default_thumb_path:
        primary = "cover"
        headline = "建议先设置封面"
        actions.append("返回工作台为作品上传或绑定封面")
    elif bool(row.get("has_wechat_draft")):
        actions.append("改稿后可在本页「更新微信草稿」同步（无草稿时需先执行草稿创建流程）")

    failed_checks = [c for c in checks if not c.get("ok")]
    for c in failed_checks[:2]:
        actions.append(c["detail"])

    return {"primary_action": primary, "headline": headline, "hints": actions[:4]}


def build_article_detail(config: AppConfig, conn: Any, article_id: int) -> dict[str, Any]:
    row = _article_row(conn, article_id)
    if row is None:
        return {}
    job = _latest_job(conn, article_id, config)
    confirmation = {
        "eligible": False,
        "can_start": False,
        "reason": "尚无已完成的真实草稿任务",
    }
    proof_block: dict[str, Any] | None = None
    if job:
        confirmation = publish_proof_eligibility(conn, int(job["id"]))
        confirmation["can_start"] = bool(
            confirmation["eligible"]
            and job.get("status") == "done"
            and row.get("status") != "published"
            and get_proof_for_job(conn, int(job["id"])) is None
        )
        confirmation["job_id"] = int(job["id"])
        if cannot_mark_published_without_proof(job.get("status")):
            proof_block = {
                "job_id": job["id"],
                "needs_proof": True,
                "existing": get_proof_for_job(conn, int(job["id"])),
                "hint": "仅在人工完成公众号发表后，提交公开链接或截图路径",
            }
    mode = (config.wechat_mode or "mock").strip().lower()
    draft = _draft_info(conn, article_id, mode=mode)
    checks = _article_preflight_checks(row, config)
    from wechat_article_scheduler.web.article_preflight import build_article_preflight_summary

    preflight_bar = build_article_preflight_summary(row, config)
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
        "publish_confirmation": confirmation,
        "publish_proof": proof_block,
        "wechat_draft": draft,
        "preflight_checks": checks,
        "preflight_bar": preflight_bar,
        "workbench": suggest_detail_actions(row=row, job=job, checks=checks, config=config),
        "mode_label": label_mode(mode),
        "preview_url": f"/api/articles/{article_id}/render-preview",
    }
