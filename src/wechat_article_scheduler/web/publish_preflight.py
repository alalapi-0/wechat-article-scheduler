"""草稿创建前预检清单（替代旧的审核闸门）。

产品重定位后不再有"审核"步骤：用户上传的作品即视为想发布的内容。
真实 API 测试策略 = 默认演练(mock) 不联网；WECHAT_MODE=real 显式启用真实 API；
当前产品目标是按计划创建草稿；后台发布/定时发布由用户人工完成。
"""

from __future__ import annotations

from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.publish_body import publish_body_for
from wechat_article_scheduler.publish_policy import (
    count_pending_job_actions,
    global_publish_policy,
)
from wechat_article_scheduler.publish_config import PublishConfig, should_submit_publish
from wechat_article_scheduler.publish_preview import _maybe_unescape_html


def _preflight_action_gate(checks: list[dict[str, Any]]) -> dict[str, Any]:
    blocking = [c for c in checks if c.get("required") and not c["ok"]]
    block_reasons = [str(c.get("detail") or c.get("label") or "") for c in blocking]
    return {
        "blocked": len(blocking) > 0,
        "reason": block_reasons[0] if block_reasons else "",
        "reasons": block_reasons,
    }


def build_publish_preflight(config: AppConfig, conn: Any) -> dict[str, Any]:
    """汇总真实发布前的可读检查项（不触发网络请求）。"""
    checks: list[dict[str, Any]] = []
    mode = (config.wechat_mode or "mock").strip().lower()
    publish_on = bool(config.wechat_enable_publish)
    will_publish = should_submit_publish(
        app_config=config,
        job_config=PublishConfig(publish_action="publish"),
    )

    checks.append(
        {
            "id": "mode",
            "ok": True,
            "required": False,
            "label": "运行模式",
            "detail": "当前为演练模式，只模拟创建草稿"
            if mode == "mock"
            else (
                "真实连接已启用：执行到点会创建公众号草稿，不会提交发布"
            ),
        }
    )

    no_cover = conn.execute(
        """
        SELECT COUNT(*) AS cnt FROM publish_jobs j
        JOIN articles a ON a.id = j.article_id
        WHERE j.status = 'pending'
          AND (a.deleted_at IS NULL OR a.deleted_at = '')
          AND (a.cover_path IS NULL OR a.cover_path = '')
        """
    ).fetchone()["cnt"]
    has_default_cover = bool(config.wechat_default_thumb_path)
    cover_ok = has_default_cover or no_cover == 0
    checks.append(
        {
            "id": "cover",
            "ok": cover_ok,
            "required": will_publish and not cover_ok,
            "label": "封面素材",
            "detail": "待创建草稿作品都已配置封面"
            if no_cover == 0
            else (
                f"有 {no_cover} 篇待创建草稿作品没有单独封面，将使用默认封面"
                if has_default_cover
                else f"有 {no_cover} 篇待创建草稿作品缺少封面，且未配置默认封面，请先上传封面"
            ),
        }
    )

    long_digest = conn.execute(
        """
        SELECT COUNT(*) AS cnt FROM articles
        WHERE length(summary) > 120
          AND (deleted_at IS NULL OR deleted_at = '')
        """
    ).fetchone()["cnt"]
    checks.append(
        {
            "id": "digest",
            "ok": long_digest == 0,
            "required": False,
            "label": "摘要长度",
            "detail": "摘要长度符合 120 字限制"
            if long_digest == 0
            else f"有 {long_digest} 篇文章摘要超过 120 字，发布前会自动截断",
        }
    )

    quality = _content_quality_issues(conn)
    if quality["duplicate_title"]:
        checks.append(
            {
                "id": "duplicate_title",
                "ok": False,
                "required": False,
                "label": "标题重复",
                "detail": f"有 {quality['duplicate_title']} 篇待创建草稿作品正文含与标题重复的首标题，创建草稿时会自动去掉",
            }
        )
    if quality["empty_body"]:
        checks.append(
            {
                "id": "empty_body",
                "ok": False,
                "required": will_publish,
                "label": "正文为空",
                "detail": f"有 {quality['empty_body']} 篇待创建草稿作品正文为空",
            }
        )
    if quality["escaped_html"]:
        checks.append(
            {
                "id": "escaped_html",
                "ok": False,
                "required": will_publish,
                "label": "疑似 HTML 源码",
                "detail": f"有 {quality['escaped_html']} 篇作品正文像转义后的 HTML，创建草稿前请先预览/修复",
            }
        )

    task_mix = count_pending_job_actions(conn, config)
    if task_mix["publish_tasks"] > 0:
        checks.append(
            {
                "id": "task_publish_mix",
                "ok": task_mix["blocked_publish_tasks"] == 0 or publish_on,
                "required": False,
                "label": "任务级发布方式",
                "detail": (
                    f"待创建草稿 {task_mix['draft_tasks']} 个仅草稿、"
                    f"{task_mix['publish_tasks']} 个标记为草稿后人工后台发布"
                    + (
                        f"（其中 {task_mix['will_submit_tasks']} 个会提交发布，当前应为 0）"
                        if publish_on
                        else f"（{task_mix['blocked_publish_tasks']} 个历史正式发布任务已降级，不会提交）"
                    )
                ),
            }
        )

    action_gate = _preflight_action_gate(checks)
    run_once_gate = action_gate
    plan_gate = action_gate
    human: list[str] = []
    if mode == "mock":
        human.append("当前为演练模式，执行到点任务只模拟创建草稿。")
    elif not publish_on:
        human.append("真实连接已启用，执行到点任务会创建公众号草稿，不会发布。")
    else:
        human.append("真实连接已启用；本项目仍只创建草稿，不自动发布。")
    for c in checks:
        if c["required"] and not c["ok"]:
            human.append(f"需处理：{c['detail']}")
        elif not c["ok"]:
            human.append(f"提示：{c['detail']}")

    return {
        "ready": len(action_gate["reasons"]) == 0,
        "run_once_gate": run_once_gate,
        "plan_gate": plan_gate,
        "mode": mode,
        "publish_enabled": publish_on,
        "publish_policy": global_publish_policy(config),
        "pending_task_mix": task_mix,
        "checks": checks,
        "human": human,
        "content_quality": quality,
    }


def _content_quality_issues(conn: Any) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT a.id, a.title, a.body
        FROM articles a
        JOIN publish_jobs j ON j.article_id = a.id
        WHERE j.status = 'pending'
          AND (a.deleted_at IS NULL OR a.deleted_at = '')
        """
    ).fetchall()
    duplicate_title = empty_body = escaped_html = 0
    for row in rows:
        title = (row["title"] or "").strip()
        body = row["body"] or ""
        if not body.strip():
            empty_body += 1
        if title and publish_body_for(title, body) != body.strip():
            duplicate_title += 1
        if "&lt;" in body and _maybe_unescape_html(body) != body:
            escaped_html += 1
    return {
        "duplicate_title": duplicate_title,
        "empty_body": empty_body,
        "escaped_html": escaped_html,
    }
