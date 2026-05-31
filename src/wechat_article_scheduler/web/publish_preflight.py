"""真实发布预检清单（Round 41）。"""

from __future__ import annotations

from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.scheduler.runtime import requires_publish_approval


def build_publish_preflight(config: AppConfig, conn: Any) -> dict[str, Any]:
    """汇总真实发布前的可读检查项（不触发网络请求）。"""
    checks: list[dict[str, Any]] = []
    mode = (config.wechat_mode or "mock").strip().lower()
    publish_on = bool(config.wechat_enable_publish)

    checks.append(
        {
            "id": "mode",
            "ok": mode == "mock" or not publish_on,
            "required": False,
            "label": "运行模式",
            "detail": "当前为演练模式，不会真的发布"
            if mode == "mock"
            else ("真实发布已关闭" if not publish_on else "已连接真实公众号且允许发布"),
        }
    )

    unapproved = conn.execute(
        """
        SELECT COUNT(*) AS cnt FROM publish_jobs j
        JOIN articles a ON a.id = j.article_id
        WHERE j.status = 'pending' AND COALESCE(a.review_status, 'draft') != 'approved'
        """
    ).fetchone()["cnt"]
    approval_required = requires_publish_approval(config)
    checks.append(
        {
            "id": "approval",
            "ok": not approval_required or unapproved == 0,
            "required": approval_required,
            "label": "文章审核",
            "detail": "待发布文章均已审核通过"
            if unapproved == 0
            else f"还有 {unapproved} 篇待发布文章未审核通过",
        }
    )

    has_default_cover = bool(config.wechat_default_thumb_path)
    checks.append(
        {
            "id": "cover",
            "ok": has_default_cover,
            "required": False,
            "label": "封面素材",
            "detail": "已配置默认封面，缺失时会自动使用"
            if has_default_cover
            else "未配置默认封面，发布前请确认每篇文章封面",
        }
    )

    long_digest = conn.execute(
        """
        SELECT COUNT(*) AS cnt FROM articles
        WHERE length(summary) > 120
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

    blocking = [c for c in checks if c.get("required") and not c["ok"]]
    human: list[str] = []
    if mode == "mock":
        human.append("当前为演练模式，执行到点任务不会真的发到公众号。")
    elif not publish_on:
        human.append("真实连接已启用，但发布开关关闭，不会真的发布。")
    else:
        human.append("真实发布已启用，执行到点前请确认以下检查项。")
    for c in checks:
        if c["required"] and not c["ok"]:
            human.append(f"需处理：{c['detail']}")
        elif not c["ok"]:
            human.append(f"提示：{c['detail']}")

    return {
        "ready": len(blocking) == 0,
        "mode": mode,
        "publish_enabled": publish_on,
        "checks": checks,
        "human": human,
    }
