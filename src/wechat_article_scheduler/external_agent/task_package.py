"""Export standardized task packages for external browser Agents.

This module intentionally does not start a browser, call an LLM, or publish.
It only writes an auditable outbox package that a human can hand to Hermes,
Cursor Agent, Playwright MCP, Browser Use, or another external tool.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.external_agent.checklist_templates import render_checklist
from wechat_article_scheduler.external_agent.prompt_templates import render_browser_agent_prompt
from wechat_article_scheduler.external_agent.proof_templates import render_proof_template
from wechat_article_scheduler.external_agent.redaction import (
    assert_no_sensitive_values,
    redact_sensitive_values,
    redact_text,
)
from wechat_article_scheduler.parser import clamp_summary
from wechat_article_scheduler.publish_config import defaults_from_rules, parse_publish_config
from wechat_article_scheduler.publish_preview import render_for_publish

TASK_PACKAGE_VERSION = 1

REQUIRED_ACTIONS = [
    "wait_for_manual_login",
    "open_backend",
    "locate_draft",
    "compare_title",
    "compare_digest",
    "compare_cover",
    "check_cover_crop",
    "check_cover_display_in_body",
    "compare_article_body",
    "check_comment_setting",
    "check_recommend_notify",
    "check_original_declaration",
    "check_collection_setting",
    "set_pre_publish_fields",
    "set_target_schedule_if_available",
    "save_draft",
    "reopen_same_draft",
    "verify_saved_field_persistence",
    "record_manual_final_publish_steps",
    "report_non_api_field_gap",
    "take_screenshot",
    "generate_report",
    "stop_before_publish_or_schedule_confirm",
]

FORBIDDEN_ACTIONS = [
    "bypass_login",
    "bypass_qr_scan",
    "bypass_captcha",
    "save_cookie",
    "read_password",
    "change_account_security_settings",
    "delete_draft",
    "delete_article",
    "operate_outside_approved_manifest",
    "schedule_without_user_confirmation",
    "click_final_schedule_confirm",
    "click_final_publish_without_user_confirmation",
    "hide_browser_window",
    "ignore_platform_warning",
]


@dataclass(frozen=True)
class ExternalAgentTaskPackage:
    job_id: str
    article_id: str
    title: str
    draft_id: str | None
    media_id: str | None
    scheduled_at: str | None
    author: str | None
    digest: str | None
    comment_setting: str | None
    collection_name: str | None
    content_source_url: str | None
    required_actions: list[str] = field(default_factory=lambda: list(REQUIRED_ACTIONS))
    forbidden_actions: list[str] = field(default_factory=lambda: list(FORBIDDEN_ACTIONS))
    manual_confirmation_required: bool = True


def task_outbox_root(config: AppConfig) -> Path:
    root = config.external_agent_task_outbox
    if not root.is_absolute():
        root = config.root / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def _job_dir(root: Path, job_id: int) -> Path:
    return root / f"job-{job_id:06d}"


def _row_to_dict(row: Any | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _fetch_job(conn: Any, job_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT j.id AS job_id, j.article_id, j.scheduled_at, j.status AS job_status,
               j.adapter_mode, j.publish_config_json,
               a.title, a.summary, a.body, a.source_path, a.cover_path,
               a.cover_config_json, a.status AS article_status,
               COALESCE(c.name, '') AS collection_name
        FROM publish_jobs j
        JOIN articles a ON a.id = j.article_id
        LEFT JOIN collections c ON c.id = a.collection_id
        WHERE j.id = ?
          AND (a.deleted_at IS NULL OR a.deleted_at = '')
        """,
        (job_id,),
    ).fetchone()
    return _row_to_dict(row)


def _fetch_latest_draft(conn: Any, article_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id, media_id, status, payload_json, created_at
        FROM wechat_drafts
        WHERE article_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (article_id,),
    ).fetchone()
    return _row_to_dict(row)


def _is_simulation_export(media_id: str | None, adapter_mode: str | None) -> bool:
    mid = (media_id or "").strip()
    mode = (adapter_mode or "").strip().lower()
    return mode == "mock" or mid.startswith("mock_")


def _simulation_required_actions() -> list[str]:
    return [
        a
        for a in REQUIRED_ACTIONS
        if a not in ("wait_for_manual_login", "open_backend", "locate_draft")
    ]


def _parse_cover_config(raw: str | None) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _backend_field_targets(
    package: ExternalAgentTaskPackage,
    pub_cfg: Any,
    row: dict[str, Any],
) -> dict[str, Any]:
    cover_cfg = _parse_cover_config(row.get("cover_config_json"))
    return {
        "fixed_collection": pub_cfg.fixed_collection or package.collection_name,
        "need_open_comment": pub_cfg.need_open_comment,
        "only_fans_can_comment": pub_cfg.only_fans_can_comment,
        "wechat_backend_schedule": "agent_prepare_and_save_draft_user_final_publish",
        "scheduled_draft_creation": package.scheduled_at,
        "manual_backend_publish": "user_only_final_publish_and_security_verification",
        "backend_schedule_final_confirm": "user_only",
        "recommend_notify": "browser_required",
        "show_cover_pic": "browser_required_verify_in_backend",
        "cover_crop": cover_cfg or "verify_crop_in_backend",
        "original_declaration": "browser_required_if_applicable",
    }


def _comment_setting(need_open_comment: bool, only_fans_can_comment: bool) -> str:
    if not need_open_comment:
        return "comments_closed"
    if only_fans_can_comment:
        return "comments_open_fans_only"
    return "comments_open"


def _bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _write_text(path: Path, text: str, *, redact: bool) -> None:
    final = redact_text(text) if redact else text
    assert_no_sensitive_values(final)
    path.write_text(final, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any], *, redact: bool) -> None:
    final = redact_sensitive_values(payload) if redact else payload
    assert_no_sensitive_values(final)
    path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")


def _copy_cover(row: dict[str, Any], dest: Path, *, include_cover: bool) -> str | None:
    if not include_cover:
        return None
    cover_raw = (row.get("cover_path") or "").strip()
    if not cover_raw:
        return None
    cover = Path(cover_raw)
    if not cover.is_file():
        return None
    suffix = cover.suffix.lower() or ".png"
    target_name = "cover.png" if suffix == ".png" else f"cover{suffix}"
    shutil.copy2(cover, dest / target_name)
    return target_name


def _build_package(
    config: AppConfig,
    row: dict[str, Any],
    draft: dict[str, Any] | None,
) -> tuple[ExternalAgentTaskPackage, dict[str, Any]]:
    defaults = defaults_from_rules(config)
    pub_cfg = parse_publish_config(row.get("publish_config_json"), defaults=defaults)
    digest = clamp_summary((row.get("summary") or "").strip() or row.get("title") or "", 120)
    draft_id = str(draft["id"]) if draft and draft.get("id") is not None else None
    media_id = str(draft["media_id"]) if draft and draft.get("media_id") else None
    package = ExternalAgentTaskPackage(
        job_id=str(row["job_id"]),
        article_id=str(row["article_id"]),
        title=row.get("title") or "",
        draft_id=draft_id,
        media_id=media_id,
        scheduled_at=row.get("scheduled_at"),
        author=pub_cfg.author or None,
        digest=digest or None,
        comment_setting=_comment_setting(
            pub_cfg.need_open_comment,
            pub_cfg.only_fans_can_comment,
        ),
        collection_name=(pub_cfg.fixed_collection or row.get("collection_name") or None),
        content_source_url=pub_cfg.content_source_url or None,
    )
    metadata = {
        "schema_version": TASK_PACKAGE_VERSION,
        "job_status_at_export": row.get("job_status"),
        "article_status_at_export": row.get("article_status"),
        "adapter_mode": row.get("adapter_mode"),
        "publish_action": pub_cfg.publish_action,
        "auto_execute": pub_cfg.auto_execute,
        "need_open_comment": pub_cfg.need_open_comment,
        "only_fans_can_comment": pub_cfg.only_fans_can_comment,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "safety": {
            "manual_confirmation_required": True,
            "final_publish_default": False,
            "does_not_run_browser": True,
            "does_not_call_llm": True,
            "does_not_store_login_state": True,
        },
    }
    return package, metadata


def export_task_package(config: AppConfig, conn: Any, job_id: int) -> dict[str, Any]:
    """Export one external browser Agent task package for a publish job."""
    if not config.external_agent_task_export_enabled:
        return {"ok": False, "error": "external Agent task export is disabled"}
    row = _fetch_job(conn, job_id)
    if not row:
        return {"ok": False, "error": "发布任务不存在"}

    draft = _fetch_latest_draft(conn, int(row["article_id"]))
    package, metadata = _build_package(config, row, draft)
    simulation = _is_simulation_export(package.media_id, row.get("adapter_mode"))
    pub_cfg = parse_publish_config(row.get("publish_config_json"), defaults=defaults_from_rules(config))
    root = task_outbox_root(config)
    dest = _job_dir(root, job_id)
    dest.mkdir(parents=True, exist_ok=True)

    cover_file = _copy_cover(row, dest, include_cover=config.external_agent_include_cover)
    body = row.get("body") or ""
    title = row.get("title") or ""
    digest = package.digest or ""
    package_payload = asdict(package)
    if simulation:
        package_payload["required_actions"] = _simulation_required_actions()
    package_payload.update(
        {
            "schema_version": TASK_PACKAGE_VERSION,
            "task_type": "wechat_official_draft_simulation"
            if simulation
            else "wechat_official_draft_external_agent_assist",
            "simulation": simulation,
            "target_backend": "local_mock" if simulation else "wechat_official_account_admin",
            "target_field_values": _backend_field_targets(package, pub_cfg, row),
            "human_confirmation_steps": {
                "manual_login": "用户扫码登录后在本项目或 CLI 确认",
                "draft_check": "Agent 可辅助定位和核对草稿，不得点击发布/群发/定时确认",
                "manual_backend_publish": "用户必须在公众号后台自行发布或定时",
                "final_publish": "禁止 Agent 点击最终发布",
            },
            "local_files": {
                "browser_agent_prompt": "browser_agent_prompt.md",
                "checklist": "checklist.md",
                "proof_template": "proof_template.md",
                "article_preview": "article_preview.html"
                if config.external_agent_include_article_preview
                else None,
                "article_source": "article_source.md"
                if config.external_agent_include_article_source
                else None,
                "cover": cover_file,
                "metadata": "metadata.json",
            },
            "proof_required": True,
            "completion_rule": "没有 proof 的任务不能标记为已完成。",
            "human_confirmation": (
                "演练任务包：不得在真实公众号后台定位 mock 草稿；仅供本地核对流程。"
                if simulation
                else "需要人工确认；外部 Agent 不得点击发布、群发或后台定时确认按钮。"
            ),
        }
    )
    _write_json(
        dest / "task.json",
        package_payload,
        redact=config.external_agent_redact_sensitive_values,
    )

    prompt_context = dict(package_payload)
    prompt_context["required_actions"] = _bullet_list(package.required_actions)
    prompt_context["forbidden_actions"] = _bullet_list(package.forbidden_actions)
    if config.external_agent_include_prompt:
        _write_text(
            dest / "browser_agent_prompt.md",
            render_browser_agent_prompt(prompt_context),
            redact=config.external_agent_redact_sensitive_values,
        )
    if config.external_agent_include_checklist:
        _write_text(
            dest / "checklist.md",
            render_checklist(),
            redact=config.external_agent_redact_sensitive_values,
        )
    if config.external_agent_include_proof_template:
        _write_text(
            dest / "proof_template.md",
            render_proof_template({"job_id": job_id, "title": title, "draft_id": package.draft_id}),
            redact=config.external_agent_redact_sensitive_values,
        )
    if config.external_agent_include_article_preview:
        preview = (
            '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
            f"<title>{title}</title></head><body>{render_for_publish(title, body)}</body></html>"
        )
        _write_text(
            dest / "article_preview.html",
            preview,
            redact=config.external_agent_redact_sensitive_values,
        )
    if config.external_agent_include_article_source:
        source = f"# {title}\n\n> 摘要：{digest}\n\n{body}\n"
        _write_text(
            dest / "article_source.md",
            source,
            redact=config.external_agent_redact_sensitive_values,
        )

    metadata_payload = {
        **metadata,
        "simulation": simulation,
        "title": title,
        "digest": digest,
        "author": package.author,
        "scheduled_at": package.scheduled_at,
        "collection_name": package.collection_name,
        "content_source_url": package.content_source_url,
        "comment_setting": package.comment_setting,
        "cover_file": cover_file,
        "proof_required": True,
        "task_package_status": "external_agent_task_ready",
    }
    _write_json(
        dest / "metadata.json",
        metadata_payload,
        redact=config.external_agent_redact_sensitive_values,
    )

    rel = dest.relative_to(config.root) if dest.is_relative_to(config.root) else dest
    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=job_id,
        event_type="external_agent_task_ready",
        payload=json.dumps(
            {
                "article_id": row["article_id"],
                "task_package_path": str(rel),
                "manual_confirmation_required": True,
                "proof_required": True,
            },
            ensure_ascii=False,
        ),
    )
    conn.commit()
    files = sorted(path.name for path in dest.iterdir() if path.is_file())
    return {
        "ok": True,
        "job_id": job_id,
        "article_id": int(row["article_id"]),
        "task_package_path": str(dest),
        "relative_path": str(rel),
        "status_hint": "external_agent_task_ready",
        "files": files,
        "human": [
            f"外部 Agent 任务包已生成：{rel}",
            "请把 browser_agent_prompt.md 交给外部工具；它必须停在人类确认阶段。",
        ],
    }


def find_job_ids_for_export(conn: Any, *, status: str, limit: int = 20) -> list[int]:
    """Find job ids for batch export without changing scheduler behavior."""
    normalized = (status or "draft_created").strip().lower()
    if normalized == "draft_created":
        rows = conn.execute(
            """
            SELECT DISTINCT j.id
            FROM publish_jobs j
            JOIN wechat_drafts d ON d.article_id = j.article_id
            JOIN articles a ON a.id = j.article_id
            WHERE d.status = 'created'
              AND (a.deleted_at IS NULL OR a.deleted_at = '')
            ORDER BY j.updated_at DESC, j.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    elif normalized == "manual_settings_required":
        rows = conn.execute(
            """
            SELECT j.id
            FROM publish_jobs j
            JOIN articles a ON a.id = j.article_id
            WHERE j.status IN ('waiting_confirmation', 'manual_settings_required')
              AND (a.deleted_at IS NULL OR a.deleted_at = '')
            ORDER BY j.updated_at DESC, j.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT j.id
            FROM publish_jobs j
            JOIN articles a ON a.id = j.article_id
            WHERE j.status = ?
              AND (a.deleted_at IS NULL OR a.deleted_at = '')
            ORDER BY j.updated_at DESC, j.id DESC
            LIMIT ?
            """,
            (normalized, limit),
        ).fetchall()
    return [int(row["id"]) for row in rows]


def export_task_packages_by_status(
    config: AppConfig,
    conn: Any,
    *,
    status: str = "draft_created",
    limit: int = 20,
) -> dict[str, Any]:
    job_ids = find_job_ids_for_export(conn, status=status, limit=limit)
    results = [export_task_package(config, conn, job_id) for job_id in job_ids]
    return {
        "ok": all(result.get("ok") for result in results),
        "status": status,
        "count": len(results),
        "results": results,
    }
