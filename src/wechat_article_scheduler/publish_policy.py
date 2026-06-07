"""草稿创建策略：全局安全摘要 + 历史 publish_action 降级解释。"""

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
    raw_web_auto = bool(config.web_auto_publish)
    auto_publish_effective = pub_on and raw_web_auto
    if mode == "mock":
        headline = "演练模式：不联网，只模拟创建草稿"
        badge = "mock"
        env_hint = "默认 WECHAT_MODE=mock"
    else:
        headline = "真实 API · 按时创建公众号草稿（不自动发布）"
        badge = "real_draft_only"
        env_hint = (
            "本项目只调用草稿相关 API；后台发布或定时发布必须由用户在公众号后台人工确认。"
        )
    if raw_web_auto and not pub_on:
        env_hint = (
            f"{env_hint} · WEB_AUTO_PUBLISH=true 已忽略（WECHAT_ENABLE_PUBLISH=false，不会自动发布）"
        )
    return {
        "mode": mode,
        "publish_enabled": pub_on,
        "badge": badge,
        "headline": headline,
        "env_hint": env_hint,
        "web_auto_publish": raw_web_auto,
        "web_auto_publish_effective": auto_publish_effective,
        "web_auto_publish_ignored": raw_web_auto and not pub_on,
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
            "label": "演练模式只模拟创建草稿",
            "level": "mock",
        }
    if action == "draft":
        return {
            "will_submit": False,
            "publish_action": action,
            "badge": "草稿排期",
            "label": "到点创建/更新公众号草稿，后续后台发布需人工完成",
            "level": "task_draft_only",
        }
    return {
        "will_submit": False,
        "publish_action": action,
        "badge": "待人工后台发布",
        "label": "历史“正式发布”配置已降级：只按时创建草稿，不调用 freepublish/submit",
        "level": "manual_backend_publish",
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
