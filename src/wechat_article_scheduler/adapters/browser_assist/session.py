"""browser_assist 手动登录门控与草稿检查状态（人在环，不自动登录/发布）。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.browser_assist.workflow import (
    GUARDRAILS,
    HUMAN_CHECKPOINTS,
    build_dry_run_plan,
)
from wechat_article_scheduler.config import AppConfig

MP_LOGIN_URL = "https://mp.weixin.qq.com/"
MP_DRAFT_BOX_HINT = "https://mp.weixin.qq.com/cgi-bin/appmsg?begin=0&count=10&type=10&action=list_card"
MP_HOST = "mp.weixin.qq.com"

SESSION_STATUSES = frozenset(
    {
        "awaiting_browser_login",
        "browser_session_ready",
        "assist_in_progress",
        "draft_review_in_progress",
        "awaiting_proof",
        "completed",
        "cancelled",
    }
)

LOGIN_GATE_PROMPT = (
    "请先按 Chrome 会话手册用 wechat-chrome-session 连接现有公众号页面（不要新开登录页）；"
    "若登录已过期，由用户本人扫码后点击「已登录，继续」。"
    "Agent 不得代填账号密码、不得绕过扫码或验证码。"
)

CHROME_SESSION_DOC = "docs/wechat_chrome_session_runbook.md"


def _coerce_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _sanitize_page_url(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    parsed = urlsplit(text)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "", "", ""))


def _connection_report_template(*, scheduled_at: str | None = None) -> dict[str, Any]:
    return {
        "mcp": "wechat-chrome-session",
        "connection_mode": "existing Chrome / autoConnect",
        "target_host": MP_HOST,
        "target_url": "https://mp.weixin.qq.com/cgi-bin/home",
        "page_title": "微信公众号后台（脱敏）",
        "backend_visible": True,
        "login_required": False,
        "dom_snapshot_available": True,
        "screenshot_available": True,
        "write_actions_performed": 0,
        "result": "PASS",
        "block_reason": "none",
        "target_scheduled_at": (scheduled_at or "").strip() or None,
    }


def _normalize_connection_report(raw: dict[str, Any] | None) -> dict[str, Any]:
    payload = raw or {}
    mcp = str(payload.get("mcp") or "wechat-chrome-session").strip() or "wechat-chrome-session"
    target_url = _sanitize_page_url(payload.get("target_url") or payload.get("url") or "")
    parsed = urlsplit(target_url) if target_url else None
    host = str(payload.get("target_host") or (parsed.netloc if parsed else "")).strip().lower()
    title = str(payload.get("page_title") or "").strip() or "微信公众号后台（脱敏）"
    connection_mode = (
        str(payload.get("connection_mode") or "existing Chrome / autoConnect").strip()
        or "existing Chrome / autoConnect"
    )
    mode_lower = connection_mode.lower()
    backend_visible = _coerce_bool(payload.get("backend_visible"), default=False)
    login_required = _coerce_bool(payload.get("login_required"), default=False)
    dom_snapshot_available = _coerce_bool(payload.get("dom_snapshot_available"), default=False)
    screenshot_available = _coerce_bool(payload.get("screenshot_available"), default=False)
    try:
        write_actions_performed = max(0, int(payload.get("write_actions_performed") or 0))
    except (TypeError, ValueError):
        write_actions_performed = 0

    blockers: list[str] = []
    if host != MP_HOST:
        blockers.append(f"target_host_not_mp:{host or 'none'}")
    if "existing" not in mode_lower:
        blockers.append("connection_mode_not_existing")
    if not target_url:
        blockers.append("target_url_missing")
    if login_required:
        blockers.append("login_required")
    if not backend_visible:
        blockers.append("backend_not_visible")
    if not dom_snapshot_available:
        blockers.append("dom_snapshot_missing")
    if not screenshot_available:
        blockers.append("screenshot_missing")
    if write_actions_performed > 0:
        blockers.append("write_actions_detected")

    limitations: list[str] = []
    if mcp != "wechat-chrome-session":
        limitations.append(
            "当前记录不是 wechat-chrome-session；"
            "若是工具限制下的替代流程，请在报告中注明并由用户人工确认。"
        )

    requested_result = str(payload.get("result") or "").strip().upper()
    if requested_result in {"PASS", "BLOCKED"}:
        result = requested_result
    else:
        result = "PASS" if not blockers else "BLOCKED"
    if blockers:
        result = "BLOCKED"
    block_reason = str(payload.get("block_reason") or "").strip()
    if result == "BLOCKED" and not block_reason:
        block_reason = blockers[0] if blockers else "unknown_block"
    if result == "PASS":
        block_reason = "none"

    return {
        "mcp": mcp,
        "connection_mode": connection_mode,
        "target_host": host or MP_HOST,
        "target_url": target_url or "https://mp.weixin.qq.com/",
        "page_title": title,
        "backend_visible": backend_visible,
        "login_required": login_required,
        "dom_snapshot_available": dom_snapshot_available,
        "screenshot_available": screenshot_available,
        "write_actions_performed": write_actions_performed,
        "result": result,
        "block_reason": block_reason or "none",
        "strict_mcp_match": mcp == "wechat-chrome-session",
        "limitations": limitations,
    }


def _connection_report_passed(session: dict[str, Any]) -> bool:
    raw = session.get("connection_report")
    if not isinstance(raw, dict):
        return False
    return (
        str(raw.get("result") or "").upper() == "PASS"
        and not _coerce_bool(raw.get("login_required"), default=True)
    )


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
        "target_host": MP_HOST,
        "target_scheduled_at": job.get("scheduled_at"),
        "connection_report_template": _connection_report_template(
            scheduled_at=str(job.get("scheduled_at") or "").strip() or None
        ),
        "verification_hints": [
            "页面 URL 不再停留在 login 或扫码页",
            "能看到公众号后台导航或草稿箱",
            "用户本人确认已完成扫码登录",
        ],
        "forbidden": [
            "不得导出或保存 cookie",
            "不得读取 .env 或 token",
            "不得自动点击最终发布、群发或后台定时确认",
        ],
        "job_id": job["job_id"],
        "article_id": job["article_id"],
        "title": job.get("title") or "",
        "media_id": job.get("media_id"),
    }


def _human_steps_for_status(status: str) -> list[str]:
    if status == "awaiting_browser_login":
        return [
            "按 docs/wechat_chrome_session_runbook.md 连接现有 Chrome",
            "确认 wechat-chrome-session 已找到 mp.weixin.qq.com 标签页",
            "先记录连接验收报告（list_pages/select_page/snapshot/screenshot），再点「已登录，继续」",
            LOGIN_GATE_PROMPT,
        ]
    if status == "browser_session_ready":
        return [
            "在已登录页面打开草稿箱",
            "按任务包 checklist 设置发布前字段并保存草稿",
            "重新打开同一草稿核验字段；不得点击正式发表、群发或定时最终确认",
        ]
    if status in ("assist_in_progress", "draft_review_in_progress"):
        return [
            "在公众号后台定位草稿并核对标题、摘要、封面和正文",
            "设置合集、通知、封面和目标时间，保存后重新打开核验",
            "完成后记录 proof；正式发表、扫码和定时最终确认由用户完成",
        ]
    if status == "awaiting_proof":
        return [
            "回填保存后重新打开的截图、字段持久化结果或用户确认备注",
            "正式发表、扫码/手机确认和定时最终确认仍由用户本人完成",
            "使用 POST /api/publish-jobs/{id}/proof",
        ]
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
                "scheduled_at": session.get("scheduled_at"),
            },
            session_id=str(session.get("session_id") or ""),
        )
    raw_report = out.get("connection_report")
    if isinstance(raw_report, dict):
        out["connection_report"] = _normalize_connection_report(raw_report)
        out["connection_verified"] = _connection_report_passed(out)
        out["connection_report_brief"] = (
            f"{out['connection_report']['result']} / "
            f"{out['connection_report']['target_host']} / "
            f"{out['connection_report']['mcp']}"
        )
    else:
        out["connection_verified"] = False
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
        "draft_review_completed_at": None,
        "connection_report": None,
        "connection_verified_at": None,
        "connection_verified_result": None,
        "backend_schedule_target_at": job.get("scheduled_at"),
        "backend_schedule_recorded_at": None,
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
            "真实页面连接说明见 docs/wechat_chrome_session_runbook.md。",
            f"会话 id={session_id}；确认登录：browser-assist-session confirm-login --session-id {session_id}",
            f"Chrome 会话说明见 {CHROME_SESSION_DOC}",
        ],
    }


def record_browser_connection(
    config: AppConfig,
    conn: Any,
    session_id: str,
    *,
    report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """记录已接管公众号页面的只读验收报告（PASS/BLOCKED）。"""
    session = _load_session(config, session_id)
    if not session:
        return {"ok": False, "error": "会话不存在"}
    if session.get("status") in {"cancelled", "completed"}:
        return {"ok": False, "error": f"当前状态不可记录连接：{session['status']}"}

    normalized = _normalize_connection_report(report)
    normalized["recorded_at"] = _utc_now()
    session["connection_report"] = normalized
    session["connection_verified_at"] = _utc_now()
    session["connection_verified_result"] = normalized["result"]
    if normalized["result"] == "PASS" and not normalized["login_required"]:
        if session["status"] == "awaiting_browser_login":
            session["status"] = "browser_session_ready"
    session["updated_at"] = _utc_now()
    _save_session(config, session)

    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=int(session["job_id"]),
        event_type="browser_assist_connection_reported",
        payload=json.dumps(
            {
                "session_id": session_id,
                "result": normalized["result"],
                "target_host": normalized["target_host"],
                "target_url": normalized["target_url"],
                "mcp": normalized["mcp"],
                "strict_mcp_match": normalized["strict_mcp_match"],
            },
            ensure_ascii=False,
        ),
    )
    conn.commit()

    view = enrich_session_view(config, session)
    human = [
        "连接验收报告已记录。",
        "请确认该报告来自当前已登录公众号页面，且未执行写操作。",
    ]
    if normalized["result"] == "PASS":
        human.append("连接验收为 PASS，可继续点击「已登录，继续」。")
        if normalized["limitations"]:
            human.append("注意：当前记录包含工具限制，请用户再次人工确认账号与页面。")
    else:
        human.append(f"连接验收为 BLOCKED：{normalized['block_reason']}")
    return {
        "ok": True,
        "session_id": session_id,
        "status": session.get("status"),
        "connection_report": normalized,
        "human": human,
        **{k: view[k] for k in ("human_steps", "guardrails") if k in view},
    }


def confirm_browser_login(
    config: AppConfig,
    conn: Any,
    session_id: str,
    *,
    attestation_note: str | None = None,
    connection_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """用户确认已完成登录；需先有接管页面验收报告。"""
    session = _load_session(config, session_id)
    if not session:
        return {"ok": False, "error": "会话不存在"}
    if session["status"] not in ("awaiting_browser_login", "browser_session_ready"):
        return {
            "ok": False,
            "error": f"当前状态不可确认登录：{session['status']}",
        }

    if connection_report:
        normalized = _normalize_connection_report(connection_report)
        normalized["recorded_at"] = _utc_now()
        session["connection_report"] = normalized
        session["connection_verified_at"] = _utc_now()
        session["connection_verified_result"] = normalized["result"]

    if not _connection_report_passed(session):
        return {
            "ok": False,
            "error": "请先记录接管页面的连接验收报告（PASS）后再确认登录",
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
            "登录已确认。请在外部 Agent / wechat-chrome-session 已登录页定位草稿并继续 checklist。",
            "Agent 可设置发布前字段、填写目标时间并保存草稿，随后重新打开核验。",
            "完成草稿准备后记录 proof；不要点击正式发表、群发或定时最终确认。",
        ],
        **{k: view[k] for k in ("human_steps", "guardrails", "task_package_path") if k in view},
    }


def confirm_schedule_setup(
    config: AppConfig,
    conn: Any,
    session_id: str,
    *,
    note: str | None = None,
    scheduled_at: str | None = None,
) -> dict[str, Any]:
    """兼容旧入口：记录草稿检查完成并进入 proof 阶段，不表示已设置后台定时。"""
    session = _load_session(config, session_id)
    if not session:
        return {"ok": False, "error": "会话不存在"}
    if session["status"] not in (
        "browser_session_ready",
        "assist_in_progress",
        "draft_review_in_progress",
    ):
        return {
            "ok": False,
            "error": f"当前状态不可确认草稿检查：{session['status']}",
        }

    session["status"] = "awaiting_proof"
    session["draft_review_completed_at"] = _utc_now()
    session["draft_review_note"] = (note or "").strip() or None
    target_schedule = (scheduled_at or "").strip() or str(session.get("scheduled_at") or "").strip() or None
    session["backend_schedule_target_at"] = target_schedule
    session["backend_schedule_recorded_at"] = _utc_now()
    session["updated_at"] = _utc_now()
    _save_session(config, session)

    job_id = int(session["job_id"])
    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=job_id,
        event_type="browser_assist_draft_reviewed",
        payload=json.dumps(
            {
                "session_id": session_id,
                "status": "awaiting_proof",
            },
            ensure_ascii=False,
        ),
    )
    conn.commit()

    view = enrich_session_view(config, session)
    return {
        "ok": True,
        "session_id": session_id,
        "status": "awaiting_proof",
        "blocked": True,
        "human": [
            "已记录发布前草稿准备完成，等待 proof。",
            (
                f"后台目标时间：{target_schedule}（请记录保存后是否仍存在；最终发表由用户完成）。"
                if target_schedule
                else "如需后台定时，请由 Agent 填写目标时间、保存草稿并重新打开核验。"
            ),
            "正式发表、扫码/手机确认和定时最终确认由用户本人完成；本项目不记录为自动发布成功。",
            f"请回填 proof：POST /api/publish-jobs/{job_id}/proof 或作品详情 #proof",
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
    """兼容旧入口：不确认最终定时发布，只进入 proof 阶段。"""
    session = _load_session(config, session_id)
    if not session:
        return {"ok": False, "error": "会话不存在"}
    if session["status"] not in (
        "browser_session_ready",
        "assist_in_progress",
        "draft_review_in_progress",
        "awaiting_proof",
    ):
        return {
            "ok": False,
            "error": f"当前状态不可记录草稿检查 proof：{session['status']}",
        }

    session["status"] = "awaiting_proof"
    session["draft_review_completed_at"] = session.get("draft_review_completed_at") or _utc_now()
    session["draft_review_attestation"] = (
        attestation_note or ""
    ).strip() or "user_confirmed_draft_review_requires_manual_backend_publish"
    session["updated_at"] = _utc_now()
    _save_session(config, session)

    job_id = int(session["job_id"])
    from wechat_article_scheduler.review.proof import mark_job_waiting_confirmation

    mark_result = mark_job_waiting_confirmation(conn, job_id)
    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=job_id,
        event_type="browser_assist_draft_review_proof_requested",
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
            "已记录发布前草稿准备完成，等待用户回填 proof。",
            "这不代表已发布或已创建后台定时任务；最终发表与平台安全验证仍需人工完成。",
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
