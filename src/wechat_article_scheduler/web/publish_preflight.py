"""发布前预检清单（替代旧的审核闸门）。

产品重定位后不再有"审核"步骤：用户上传的作品即视为想发布的内容。
真实发布的安全保障 = 默认演练(mock) + 显式开关(WECHAT_ENABLE_PUBLISH) +
执行到点前的二次确认 + 这里列出的可读检查项。
"""

from __future__ import annotations

from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.publish_body import publish_body_for
from wechat_article_scheduler.publish_preview import _maybe_unescape_html


def build_publish_preflight(config: AppConfig, conn: Any) -> dict[str, Any]:
    """汇总真实发布前的可读检查项（不触发网络请求）。"""
    checks: list[dict[str, Any]] = []
    mode = (config.wechat_mode or "mock").strip().lower()
    publish_on = bool(config.wechat_enable_publish)
    will_publish = mode == "real" and publish_on

    checks.append(
        {
            "id": "mode",
            "ok": True,
            "required": False,
            "label": "运行模式",
            "detail": "当前为演练模式，不会真的发布"
            if mode == "mock"
            else (
                "真实连接已启用：执行到点会创建公众号草稿，不会提交发布"
                if not publish_on
                else "已连接真实公众号且允许发布"
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
            "detail": "待发布作品都已配置封面"
            if no_cover == 0
            else (
                f"有 {no_cover} 篇待发布作品没有单独封面，将使用默认封面"
                if has_default_cover
                else f"有 {no_cover} 篇待发布作品缺少封面，且未配置默认封面，请先上传封面"
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
                "detail": f"有 {quality['duplicate_title']} 篇待发布作品正文含与标题重复的首标题，发布时会自动去掉",
            }
        )
    if quality["empty_body"]:
        checks.append(
            {
                "id": "empty_body",
                "ok": False,
                "required": will_publish,
                "label": "正文为空",
                "detail": f"有 {quality['empty_body']} 篇待发布作品正文为空",
            }
        )
    if quality["escaped_html"]:
        checks.append(
            {
                "id": "escaped_html",
                "ok": False,
                "required": False,
                "label": "疑似 HTML 源码",
                "detail": f"有 {quality['escaped_html']} 篇作品正文像转义后的 HTML，预览可能异常",
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
