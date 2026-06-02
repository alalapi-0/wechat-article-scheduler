"""可选正式发布策略：全局开关 + 任务级 publish_action（Round 20）。"""

from __future__ import annotations

from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.publish_config import (
    PublishConfig,
    parse_publish_config,
    should_submit_publish,
)


def global_publish_policy(config: AppConfig) -> dict[str, Any]:
    """工作台顶部安全条与 /api/status 用的全局策略摘要。"""
    mode = (config.wechat_mode or "mock").strip().lower()
    pub_on = bool(config.wechat_enable_publish)
    if mode == "mock":
        headline = "演练模式：不联网，不会真的发到公众号"
        badge = "mock"
        env_hint = "默认 WECHAT_MODE=mock"
    elif not pub_on:
        headline = "真实 API · 全局草稿-only（WECHAT_ENABLE_PUBLISH=false）"
        badge = "real_draft_only"
        env_hint = "需要正式发布时设置 WECHAT_ENABLE_PUBLISH=true 且任务选「正式发布」"
    else:
        headline = "真实 API · 正式发布已开启（任务选「正式发布」时会 freepublish/submit）"
        badge = "real_publish_enabled"
        env_hint = "执行到点前有二次确认；预检未通过会阻断"
    return {
        "mode": mode,
        "publish_enabled": pub_on,
        "badge": badge,
        "headline": headline,
        "env_hint": env_hint,
        "web_auto_publish": bool(config.web_auto_publish),
    }


def resolve_effective_submit(
    *, app_config: AppConfig, job_config: PublishConfig
) -> dict[str, Any]:
    """单任务到点时的有效发布行为（供队列/详情展示）。"""
    mode = (app_config.wechat_mode or "mock").strip().lower()
    action = job_config.publish_action
    will_submit = should_submit_publish(app_config=app_config, job_config=job_config)
    if mode != "real":
        return {
            "will_submit": False,
            "publish_action": action,
            "badge": "演练",
            "label": "演练模式不调用真实发布接口",
            "level": "mock",
        }
    if action == "draft":
        return {
            "will_submit": False,
            "publish_action": action,
            "badge": "任务·仅草稿",
            "label": "任务设为仅草稿，不调用 freepublish/submit",
            "level": "task_draft_only",
        }
    if not app_config.wechat_enable_publish:
        return {
            "will_submit": False,
            "publish_action": action,
            "badge": "全局·草稿-only",
            "label": "WECHAT_ENABLE_PUBLISH=false，任务「正式发布」不会提交",
            "level": "global_draft_only",
        }
    if will_submit:
        return {
            "will_submit": True,
            "publish_action": action,
            "badge": "将正式发布",
            "label": "到点将调用 freepublish/submit",
            "level": "real_publish",
        }
    return {
        "will_submit": False,
        "publish_action": action,
        "badge": "不发布",
        "label": "当前配置不会提交发布",
        "level": "blocked",
    }


def count_pending_job_actions(conn: Any, config: AppConfig) -> dict[str, int]:
    """统计待发布任务的任务级 publish_action 分布。"""
    from wechat_article_scheduler.publish_config import defaults_from_rules

    defaults = defaults_from_rules(config)
    rows = conn.execute(
        """
        SELECT j.publish_config_json
        FROM publish_jobs j
        JOIN articles a ON a.id = j.article_id
        WHERE j.status = 'pending'
          AND (a.deleted_at IS NULL OR a.deleted_at = '')
        """
    ).fetchall()
    draft_tasks = publish_tasks = will_submit_tasks = blocked_publish_tasks = 0
    for row in rows:
        pub = parse_publish_config(row["publish_config_json"], defaults=defaults)
        if pub.publish_action == "publish":
            publish_tasks += 1
            eff = resolve_effective_submit(app_config=config, job_config=pub)
            if eff["will_submit"]:
                will_submit_tasks += 1
            elif (config.wechat_mode or "").strip().lower() == "real":
                blocked_publish_tasks += 1
        else:
            draft_tasks += 1
    return {
        "draft_tasks": draft_tasks,
        "publish_tasks": publish_tasks,
        "will_submit_tasks": will_submit_tasks,
        "blocked_publish_tasks": blocked_publish_tasks,
    }
