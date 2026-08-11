"""草稿创建前预检清单（替代旧的审核闸门）。

产品重定位后不再有"审核"步骤：用户上传的作品即视为想发布的内容。
真实 API 测试策略 = 默认演练(mock) 不联网；WECHAT_MODE=real 显式启用真实 API；
当前产品目标是按计划创建草稿；后台发布/定时发布由用户人工完成。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.cover_assets.index import check_configured_cover
from wechat_article_scheduler.publish_body import publish_body_for
from wechat_article_scheduler.publish_preview import _maybe_unescape_html


def _preflight_action_gate(checks: list[dict[str, Any]]) -> dict[str, Any]:
    blocking = [c for c in checks if c.get("required") and not c["ok"]]
    block_reasons = [str(c.get("detail") or c.get("label") or "") for c in blocking]
    return {
        "blocked": len(blocking) > 0,
        "reason": block_reasons[0] if block_reasons else "",
        "reasons": block_reasons,
    }


def _due_now(raw: str | None) -> bool:
    try:
        scheduled = datetime.fromisoformat((raw or "").replace(" ", "T"))
    except ValueError:
        return False
    now = datetime.now(scheduled.tzinfo) if scheduled.tzinfo else datetime.now()
    return scheduled <= now


def build_publish_preflight(config: AppConfig, conn: Any) -> dict[str, Any]:
    """汇总草稿创建前的可读检查项（不触发网络请求）。"""
    checks: list[dict[str, Any]] = []
    mode = (config.wechat_mode or "mock").strip().lower()

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

    pending_rows = conn.execute(
        """
        SELECT a.cover_path, j.scheduled_at FROM publish_jobs j
        JOIN articles a ON a.id = j.article_id
        WHERE j.status = 'pending'
          AND j.adapter_mode = ?
          AND (a.deleted_at IS NULL OR a.deleted_at = '')
        """,
        (mode,),
    ).fetchall()
    pending_covers = [row for row in pending_rows if _due_now(row["scheduled_at"])]
    credentials_ok = bool(
        str(config.wechat_app_id or "").strip()
        and str(config.wechat_app_secret or "").strip()
    )
    checks.append(
        {
            "id": "credentials",
            "ok": mode != "real" or credentials_ok or not pending_covers,
            "required": mode == "real" and bool(pending_covers) and not credentials_ok,
            "label": "微信凭证",
            "detail": "真实模式凭证已配置"
            if credentials_ok
            else "真实模式缺少 WECHAT_APP_ID / WECHAT_APP_SECRET",
        }
    )
    default_cover = (config.wechat_default_thumb_path or "").strip()
    cover_results = [
        check_configured_cover(config, row["cover_path"])
        for row in pending_covers
    ]
    failed_covers = [result for result in cover_results if not result["ok"]]
    defaulted_covers = [result for result in cover_results if result.get("using_default")]
    cover_ok = not failed_covers
    if not pending_covers:
        cover_detail = "当前没有待创建草稿作品"
    elif not failed_covers and not defaulted_covers:
        cover_detail = "待创建草稿作品都已配置可用封面"
    elif not failed_covers:
        cover_detail = (
            f"有 {len(defaulted_covers)} 篇待创建草稿作品未指定单独封面，"
            f"将使用默认封面：{default_cover}"
        )
    else:
        cover_detail = (
            f"有 {len(failed_covers)} 篇待创建草稿作品封面不可用；"
            f"{failed_covers[0]['message']}"
        )
    checks.append(
        {
            "id": "cover",
            "ok": cover_ok,
            "required": mode == "real" and not cover_ok,
            "label": "封面素材",
            "detail": cover_detail,
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
            else f"有 {long_digest} 篇文章摘要超过 120 字，创建草稿时会自动截断",
        }
    )

    quality = _content_quality_issues(conn, mode=mode)
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
                "required": mode == "real",
                "label": "正文为空",
                "detail": f"有 {quality['empty_body']} 篇待创建草稿作品正文为空",
            }
        )
    if quality["escaped_html"]:
        checks.append(
            {
                "id": "escaped_html",
                "ok": False,
                "required": mode == "real",
                "label": "疑似 HTML 源码",
                "detail": f"有 {quality['escaped_html']} 篇作品正文像转义后的 HTML，创建草稿前请先预览/修复",
            }
        )

    action_gate = _preflight_action_gate(checks)
    run_once_gate = action_gate
    plan_gate = _preflight_action_gate([c for c in checks if c["id"] != "cover"])
    human: list[str] = []
    if mode == "mock":
        human.append("当前为演练模式，执行到点任务只模拟创建草稿。")
    else:
        human.append("真实连接已启用，执行到点任务只会创建公众号草稿。")
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
        "checks": checks,
        "human": human,
        "content_quality": quality,
    }


def _content_quality_issues(conn: Any, *, mode: str) -> dict[str, int]:
    pending_rows = conn.execute(
        """
        SELECT a.id, a.title, a.body, j.scheduled_at
        FROM articles a
        JOIN publish_jobs j ON j.article_id = a.id
        WHERE j.status = 'pending'
          AND j.adapter_mode = ?
          AND (a.deleted_at IS NULL OR a.deleted_at = '')
        """,
        (mode,),
    ).fetchall()
    rows = [row for row in pending_rows if _due_now(row["scheduled_at"])]
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
