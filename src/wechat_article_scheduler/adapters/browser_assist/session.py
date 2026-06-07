"""browser_assist 手动登录门控与会话状态（人在环，不自动登录/发布）。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.browser_assist.workflow import (
    GUARDRAILS,
    HUMAN_CHECKPOINTS,
    build_dry_run_plan,
)
from wechat_article_scheduler.config import AppConfig

MP_LOGIN_URL = "https://mp.weixin.qq.com/"
MP_DRAFT_BOX_HINT = "https://mp.weixin.qq.com/cgi-bin/appmsg?begin=0&count=10&type=10&action=list_card"

SESSION_STATUSES = frozenset(
    {
        "awaiting_browser_login",
        "browser_session_ready",
        "assist_in_progress",
        "awaiting_schedule_setup",
        "awaiting_final_schedule_confirm",
        "awaiting_proof",
        "completed",
        "cancelled",
    }
)

LOGIN_GATE_PROMPT = (
    "请在本浏览器窗口扫码登录微信公众平台，完成后点击「已登录，继续」。"
    "Agent 不得代填账号密码、不得绕过扫码或验证码。"
)

CHROME_SESSION_DOC = "docs/wechat_chrome_session_runbook.md"


def sessions_root(config: AppConfig) -> Path:
    root = config.root / "storage" / "browser_assist_sessions"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _session_path(config: AppConfig, session_id: str) -> Path:
    safe = "".join(ch for ch in session_id if ch.isalnum() or ch in "-_")
    return sessions_root(config) / f"{safe}.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_session(config: AppConfig, session_id: str) -> dict[str, Any] | None:
    path = _session_path(config, session_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save_session(config: AppConfig, payload: dict[str, Any]) -> None:
    session_id = str(payload["session_id"])
    path = _session_path(config, session_id)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _fetch_job_context(conn: Any, job_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT j.id AS job_id, j.article_id, j.scheduled_at, j.status AS job_status,
               a.title, a.status AS article_status
        FROM publish_jobs j
        JOIN articles a ON a.id = j.article_id
        WHERE j.id = ?
          AND (a.deleted_at IS NULL OR a.deleted_at = '')
        """,
        (job_id,),
    ).fetchone()
    if row is None:
        return None
    draft = conn.execute(
        """
        SELECT media_id FROM wechat_drafts
        WHERE article_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (int(row["article_id"]),),
    ).fetchone()
    out = dict(row)
    out["media_id"] = draft["media_id"] if draft else None
    return out


def _login_gate_block(*, job: dict[str, Any], session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "status": "awaiting_browser_login",
        "blocked": True,
        "prompt_zh": LOGIN_GATE_PROMPT,
        "confirm_action": "confirm-login",
        "confirm_label_zh": "已登录，继续",
        "login_url": MP_LOGIN_URL,
        "draft_box_hint_url": MP_DRAFT_BOX_HINT,
        "mcp_server": "wechat-chrome-session",
        "mcp_doc": CHROME_SESSION_DOC,
        "verification_hints": [
            "页面 URL 不再停留在 login 或扫码页",
            "能看到公众号后台导航或草稿箱",
            "用户本人确认已完成扫码登录",
        ],
        "forbidden": [
            "不得导出或保存 cookie",
            "不得读取 .env 或 token",
            "不得自动点击最终发布或定时群发确认",
        ],
        "job_id": job["job_id"],
        "article_id": job["article_id"],
        "title": job.get("title") or "",
        "media_id": job.get("media_id"),
    }


def _human_steps_for_status(status: str) -> list[str]:
    if status == "awaiting_browser_login":
        return [
            "打开 mp.weixin.qq.com 或连接 wechat-chrome-session",
            LOGIN_GATE_PROMPT,
        ]
    if status == "browser_session_ready":
        return [
            "在已登录页面打开草稿箱",
            "按任务包 checklist 核对字段",
            "可辅助填写非最终字段，不得点击最终发布",
        ]
    if status == "awaiting_schedule_setup":
        return [
            "在公众号后台设置定时群发时间（对照本地 scheduled_at）",
            "设置完成后在本项目点击「已设置定时，继续」",
            "仍未到最终确认：不得代为点击定时群发确认/发布",
        ]
    if status == "awaiting_final_schedule_confirm":
        return [
            "请用户在公众号后台亲自确认定时群发",
            "Agent 不得代替点击最终确认按钮",
            "确认后在本项目点击「已完成后台最终确认」并回填 proof",
        ]
    if status == "awaiting_proof":
        return ["回填截图路径或公开链接", "使用 POST /api/publish-jobs/{id}/proof"]
    return []


def enrich_session_view(config: AppConfig, session: dict[str, Any]) -> dict[str, Any]:
    status = session.get("status") or ""
    out = dict(session)
    out["human_steps"] = _human_steps_for_status(status)
    out["guardrails"] = GUARDRAILS
    out["human_checkpoints"] = HUMAN_CHECKPOINTS
    if status == "awaiting_browser_login":
        out["login_gate"] = _login_gate_block(
            job={
                "job_id": session.get("job_id"),
                "article_id": session.get("article_id"),
                "title": session.get("title"),
                "media_id": session.get("media_id"),
            },
            session_id=str(session.get("session_id") or ""),
        )
    rel = _session_path(config, str(session["session_id"]))
    if rel.is_relative_to(config.root):
        out["session_file"] = str(rel.relative_to(config.root))
    else:
        out["session_file"] = str(rel)
    return out


def get_browser_assist_session(config: AppConfig, session_id: str) -> dict[str, Any]:
    session = _load_session(config, session_id)
    if not session:
        return {"ok": False, "error": "会话不存在"}
    return {"ok": True, **enrich_session_view(config, session)}


def list_browser_assist_sessions(
    config: AppConfig,
    *,
    active_only: bool = True,
) -> dict[str, Any]:
    root = sessions_root(config)
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if active_only and raw.get("status") in ("completed", "cancelled"):
            continue
        items.append(enrich_session_view(config, raw))
    return {"ok": True, "count": len(items), "sessions": items}


def start_browser_assist_session(
    config: AppConfig,
    conn: Any,
    job_id: int,
    *,
    export_task_package: bool = True,
) -> dict[str, Any]:
    """启动 browser_assist 会话：打开登录门控，等待用户扫码确认。"""
    job = _fetch_job_context(conn, job_id)
    if not job:
        return {"ok": False, "error": "发布任务不存在"}
    if job["job_status"] in ("cancelled",):
        return {"ok": False, "error": f"任务已取消，无法启动：{job['job_status']}"}

    session_id = uuid.uuid4().hex[:16]
    dry_plan = build_dry_run_plan(
        article_id=str(job["article_id"]),
        media_id=str(job["media_id"]) if job.get("media_id") else None,
    )
    dry_plan["login_gate"] = _login_gate_block(job=job, session_id=session_id)
    dry_plan["session_status"] = "awaiting_browser_login"
    dry_plan["manual_trigger_only"] = True

    task_package: dict[str, Any] | None = None
    if export_task_package and config.external_agent_task_export_enabled:
        from wechat_article_scheduler.external_agent import export_task_package as export_pkg

        task_package = export_pkg(config, conn, job_id)

    session = {
        "session_id": session_id,
        "job_id": job_id,
        "article_id": int(job["article_id"]),
        "title": job.get("title") or "",
        "media_id": job.get("media_id"),
        "scheduled_at": job.get("scheduled_at"),
        "status": "awaiting_browser_login",
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "login_confirmed_at": None,
        "schedule_setup_at": None,
        "final_schedule_confirmed_at": None,
        "task_package_path": (task_package or {}).get("relative_path")
        or (task_package or {}).get("task_package_path"),
    }
    _save_session(config, session)

    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=job_id,
        event_type="browser_assist_session_started",
        payload=json.dumps(
            {
                "session_id": session_id,
                "status": "awaiting_browser_login",
                "manual_login_required": True,
            },
            ensure_ascii=False,
        ),
    )
    conn.commit()

    view = enrich_session_view(config, session)
    return {
        "ok": True,
        "session_id": session_id,
        "status": "awaiting_browser_login",
        "blocked": True,
        "prompt_zh": LOGIN_GATE_PROMPT,
        "login_gate": view["login_gate"],
        "dry_run_plan": dry_plan,
        "task_package": task_package,
        "human": [
            LOGIN_GATE_PROMPT,
            f"会话 id={session_id}；确认登录：browser-assist-session confirm-login --session-id {session_id}",
            f"Chrome 会话说明见 {CHROME_SESSION_DOC}",
        ],
    }


def confirm_browser_login(
    config: AppConfig,
    conn: Any,
    session_id: str,
    *,
    attestation_note: str | None = None,
) -> dict[str, Any]:
    """用户确认已完成扫码登录；不在此自动校验页面（仅记录用户 attestation）。"""
    session = _load_session(config, session_id)
    if not session:
        return {"ok": False, "error": "会话不存在"}
    if session["status"] != "awaiting_browser_login":
        return {
            "ok": False,
            "error": f"当前状态不可确认登录：{session['status']}",
        }

    session["status"] = "browser_session_ready"
    session["login_confirmed_at"] = _utc_now()
    session["updated_at"] = _utc_now()
    session["login_attestation"] = (attestation_note or "").strip() or "user_confirmed_logged_in"
    _save_session(config, session)

    job_id = int(session["job_id"])
    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=job_id,
        event_type="browser_assist_login_confirmed",
        payload=json.dumps(
            {"session_id": session_id, "status": "browser_session_ready"},
            ensure_ascii=False,
        ),
    )
    conn.commit()

    session["status"] = "assist_in_progress"
    session["updated_at"] = _utc_now()
    _save_session(config, session)

    view = enrich_session_view(config, session)
    return {
        "ok": True,
        "session_id": session_id,
        "status": "assist_in_progress",
        "blocked": False,
        "human": [
            "登录已确认。请在外部 Agent / wechat-chrome-session 已登录页继续 checklist。",
            "完成字段核对与后台定时设置后，调用 confirm-schedule-setup。",
            "最终定时群发确认必须由用户本人在公众号后台操作。",
        ],
        **{k: view[k] for k in ("human_steps", "guardrails", "task_package_path") if k in view},
    }


def confirm_schedule_setup(
    config: AppConfig,
    conn: Any,
    session_id: str,
    *,
    note: str | None = None,
) -> dict[str, Any]:
    """用户/Agent 已在后台设置定时，但仍未到最终群发确认。"""
    session = _load_session(config, session_id)
    if not session:
        return {"ok": False, "error": "会话不存在"}
    if session["status"] not in ("browser_session_ready", "assist_in_progress", "awaiting_schedule_setup"):
        return {
            "ok": False,
            "error": f"当前状态不可确认定时设置：{session['status']}",
        }

    session["status"] = "awaiting_final_schedule_confirm"
    session["schedule_setup_at"] = _utc_now()
    session["schedule_setup_note"] = (note or "").strip() or None
    session["updated_at"] = _utc_now()
    _save_session(config, session)

    job_id = int(session["job_id"])
    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=job_id,
        event_type="browser_assist_schedule_setup",
        payload=json.dumps(
            {
                "session_id": session_id,
                "status": "awaiting_final_schedule_confirm",
            },
            ensure_ascii=False,
        ),
    )
    conn.commit()

    view = enrich_session_view(config, session)
    return {
        "ok": True,
        "session_id": session_id,
        "status": "awaiting_final_schedule_confirm",
        "blocked": True,
        "human": [
            "后台定时已标记为已设置。",
            "请用户在公众号后台亲自点击最终定时群发确认；Agent 不得代点。",
            f"完成后：browser-assist-session confirm-final-schedule --session-id {session_id}",
        ],
        "human_steps": view["human_steps"],
    }


def confirm_final_schedule(
    config: AppConfig,
    conn: Any,
    session_id: str,
    *,
    attestation_note: str | None = None,
) -> dict[str, Any]:
    """用户确认已在公众号后台完成最终定时群发确认（仍不自动标记 published）。"""
    session = _load_session(config, session_id)
    if not session:
        return {"ok": False, "error": "会话不存在"}
    if session["status"] != "awaiting_final_schedule_confirm":
        return {
            "ok": False,
            "error": f"当前状态不可确认最终定时：{session['status']}",
        }

    session["status"] = "awaiting_proof"
    session["final_schedule_confirmed_at"] = _utc_now()
    session["final_schedule_attestation"] = (
        attestation_note or ""
    ).strip() or "user_confirmed_final_schedule_in_backend"
    session["updated_at"] = _utc_now()
    _save_session(config, session)

    job_id = int(session["job_id"])
    from wechat_article_scheduler.review.proof import mark_job_waiting_confirmation

    mark_result = mark_job_waiting_confirmation(conn, job_id)
    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=job_id,
        event_type="browser_assist_final_schedule_confirmed",
        payload=json.dumps(
            {"session_id": session_id, "status": "awaiting_proof"},
            ensure_ascii=False,
        ),
    )
    conn.commit()

    view = enrich_session_view(config, session)
    return {
        "ok": True,
        "session_id": session_id,
        "status": "awaiting_proof",
        "waiting_confirmation": mark_result,
        "human": [
            "已记录后台最终定时确认（用户 attestation）。",
            f"请回填 proof：POST /api/publish-jobs/{job_id}/proof 或作品详情 #proof",
        ],
        "human_steps": view["human_steps"],
    }


def cancel_browser_assist_session(
    config: AppConfig,
    conn: Any,
    session_id: str,
    *,
    reason: str | None = None,
) -> dict[str, Any]:
    session = _load_session(config, session_id)
    if not session:
        return {"ok": False, "error": "会话不存在"}
    session["status"] = "cancelled"
    session["cancelled_at"] = _utc_now()
    session["cancel_reason"] = (reason or "").strip() or None
    session["updated_at"] = _utc_now()
    _save_session(config, session)
    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=int(session["job_id"]),
        event_type="browser_assist_session_cancelled",
        payload=json.dumps({"session_id": session_id}, ensure_ascii=False),
    )
    conn.commit()
    return {"ok": True, "session_id": session_id, "status": "cancelled"}
