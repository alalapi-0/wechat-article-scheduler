"""Export auditable, read-only packages for a user-approved external browser tool."""

from __future__ import annotations

import json
import os
import stat
import subprocess
from html import escape
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.external_agent.checklist_templates import render_checklist
from wechat_article_scheduler.external_agent.prompt_templates import render_browser_agent_prompt
from wechat_article_scheduler.external_agent.inspection_report_template import (
    render_inspection_report,
)
from wechat_article_scheduler.external_agent.redaction import (
    assert_no_sensitive_values,
    redact_sensitive_values,
    redact_text,
)
from wechat_article_scheduler.parser import clamp_summary
from wechat_article_scheduler.publish_config import defaults_from_rules, parse_publish_config
from wechat_article_scheduler.publish_preview import render_for_publish
from wechat_article_scheduler.cover_assets.index import InvalidCoverError, managed_cover_bytes
from wechat_article_scheduler.filesystem_safety import (
    UnsafePathError,
    ensure_directory,
    open_directory_handle,
    write_new_file,
)

TASK_PACKAGE_VERSION = 2

DATA_TASK_OUTPUT = Path('/data/ProjectOutputs/wechat-article-scheduler/task-packages')
DATA_OUTPUT_UUID = '98a6a740-bf5c-41b5-90fe-fd8e78fa5f55'


def data_task_outbox_root() -> Path:
    """Admit only the DATA task-package folder; no internal-disk fallback."""
    mount = Path('/data')
    DATA_TASK_OUTPUT.relative_to(mount)
    rows = json.loads(subprocess.check_output(
        ['/usr/bin/findmnt', '-J', '-T', str(mount), '-o', 'TARGET,FSTYPE,UUID,OPTIONS'],
        text=True, env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}, timeout=10,
    ))['filesystems']
    if len(rows) != 1 or rows[0].get('children'):
        raise RuntimeError('DATA output volume identity is ambiguous')
    row = rows[0]
    options = str(row.get('options', '')).split(',')
    if (row.get('target') != str(mount) or row.get('fstype') != 'ext4'
            or row.get('uuid') != DATA_OUTPUT_UUID or 'rw' not in options or 'ro' in options):
        raise RuntimeError('DATA output volume unavailable; no fallback')
    usage = os.statvfs(mount)
    if usage.f_flag & os.ST_RDONLY or usage.f_bavail * usage.f_frsize < 40 * 1024**3:
        raise RuntimeError('DATA output volume read-only or insufficient free space')
    current = Path('/')
    missing = []
    for part in DATA_TASK_OUTPUT.parts[1:]:
        current /= part
        if current.is_symlink():
            raise RuntimeError('DATA output path redirects through a symlink')
        if current.exists():
            info = current.stat()
            if not stat.S_ISDIR(info.st_mode):
                raise RuntimeError('DATA output parent is not a directory')
            if current == mount or current.is_relative_to(mount):
                if info.st_dev != mount.stat().st_dev:
                    raise RuntimeError('DATA output path changed device')
        else:
            missing.append(current)
    for path in missing:
        path.mkdir(mode=0o700)
    if DATA_TASK_OUTPUT.resolve(strict=True) != DATA_TASK_OUTPUT or DATA_TASK_OUTPUT.stat().st_dev != mount.stat().st_dev:
        raise RuntimeError('DATA output folder identity changed')
    return DATA_TASK_OUTPUT

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
    "operate_outside_approved_task_package",
    "modify_backend_fields",
    "save_draft",
    "schedule_backend_publish",
    "click_final_schedule_confirm",
    "click_final_publish",
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
    if root == DATA_TASK_OUTPUT or root.is_relative_to(DATA_TASK_OUTPUT):
        data_task_outbox_root()
    return ensure_directory(root, allowed_roots=(root,))


def _job_dir(root: Path, job_id: int) -> Path:
    return root / f"job-{job_id:06d}"


_MANAGED_FILENAMES = frozenset(
    {
        "task.json",
        "metadata.json",
        "browser_agent_prompt.md",
        "checklist.md",
        "inspection_report.md",
        "article_preview.html",
        "article_source.md",
    }
)


def _prepare_job_dir(root: Path, job_id: int) -> Path:
    """清除上次导出的受管文件，避免配置关闭后残留旧内容。"""
    dest = _job_dir(root, job_id)
    ensure_directory(dest, allowed_roots=(root,))
    with open_directory_handle(dest, allowed_roots=(dest,)) as handle:
        for name in handle.list_names():
            if name in _MANAGED_FILENAMES or name.startswith("cover."):
                snapshot = handle.read_regular_file(name)
                if not handle.unlink_if_unchanged(name, snapshot):
                    raise UnsafePathError("任务包目标在清理期间发生变化")
    return dest


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


def _fetch_job_draft(
    conn: Any,
    *,
    article_id: int,
    job_id: int,
    adapter_mode: str,
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id, media_id, status, payload_json, created_at,
               adapter_mode, publish_job_id
        FROM wechat_drafts
        WHERE article_id = ?
          AND publish_job_id = ?
          AND adapter_mode = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (article_id, job_id, adapter_mode),
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


def _expected_backend_fields(
    package: ExternalAgentTaskPackage,
    pub_cfg: Any,
    row: dict[str, Any],
) -> dict[str, Any]:
    cover_cfg = _parse_cover_config(row.get("cover_config_json"))
    return {
        "fixed_collection": pub_cfg.fixed_collection or package.collection_name,
        "need_open_comment": pub_cfg.need_open_comment,
        "only_fans_can_comment": pub_cfg.only_fans_can_comment,
        "wechat_backend_schedule": "read_only_compare_with_local_schedule",
        "scheduled_draft_creation": package.scheduled_at,
        "manual_backend_publish": "user_only_final_publish_and_security_verification",
        "backend_schedule_final_confirm": "user_only",
        "recommend_notify": "inspect_if_visible",
        "show_cover_pic": "inspect_if_visible",
        "cover_crop": cover_cfg or "inspect_if_visible",
        "original_declaration": "inspect_if_visible",
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
    write_new_file(path, final.encode("utf-8"), allowed_roots=(path.parent,))


def _write_json(path: Path, payload: dict[str, Any], *, redact: bool) -> None:
    final = redact_sensitive_values(payload) if redact else payload
    assert_no_sensitive_values(final)
    write_new_file(
        path,
        json.dumps(final, ensure_ascii=False, indent=2).encode("utf-8"),
        allowed_roots=(path.parent,),
    )


def _copy_cover(config: AppConfig, row: dict[str, Any], dest: Path, *, include_cover: bool) -> str | None:
    if not include_cover:
        return None
    cover_raw = (row.get("cover_path") or "").strip()
    if not cover_raw:
        return None
    cover = Path(cover_raw)
    try:
        cover_data = managed_cover_bytes(config, cover)
    except InvalidCoverError:
        return None
    suffix = cover.suffix.lower() or ".png"
    target_name = "cover.png" if suffix == ".png" else f"cover{suffix}"
    write_new_file(dest / target_name, cover_data, allowed_roots=(dest,))
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
        return {"ok": False, "error": "草稿任务不存在"}

    draft = _fetch_job_draft(
        conn,
        article_id=int(row["article_id"]),
        job_id=job_id,
        adapter_mode=str(row.get("adapter_mode") or ""),
    )
    package, metadata = _build_package(config, row, draft)
    simulation = _is_simulation_export(package.media_id, row.get("adapter_mode"))
    pub_cfg = parse_publish_config(row.get("publish_config_json"), defaults=defaults_from_rules(config))
    root = task_outbox_root(config)
    dest = _prepare_job_dir(root, job_id)

    cover_file = _copy_cover(config, row, dest, include_cover=config.external_agent_include_cover)
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
            else "wechat_official_draft_read_only_inspection",
            "simulation": simulation,
            "target_backend": "local_mock" if simulation else "wechat_official_account_admin",
            "expected_field_values": _expected_backend_fields(package, pub_cfg, row),
            "human_confirmation_steps": {
                "manual_login": "用户扫码登录后在本项目或 CLI 确认",
                "draft_check": "Agent 只读定位和核对草稿，不得修改或保存",
                "backend_changes": "所有公众号后台修改均由用户自行完成",
                "final_publish": "最终发表或定时确认只能由用户完成",
            },
            "local_files": {
                "browser_agent_prompt": "browser_agent_prompt.md"
                if config.external_agent_include_prompt
                else None,
                "checklist": "checklist.md"
                if config.external_agent_include_checklist
                else None,
                "inspection_report": "inspection_report.md"
                if config.external_agent_include_inspection_report
                else None,
                "article_preview": "article_preview.html"
                if config.external_agent_include_article_preview
                else None,
                "article_source": "article_source.md"
                if config.external_agent_include_article_source
                else None,
                "cover": cover_file,
                "metadata": "metadata.json",
            },
            "inspection_report_required": True,
            "completion_rule": (
                "只读检查需生成 inspection_report.md；该报告不能作为发布 proof，"
                "也不能将文章标记为 published。"
            ),
            "human_confirmation": (
                "演练任务包：不得在真实公众号后台定位 mock 草稿；仅供本地核对流程。"
                if simulation
                else "只读检查；外部 Agent 不得修改字段、保存草稿、发表、群发或确认定时。"
            ),
        }
    )
    _write_json(
        dest / "task.json",
        package_payload,
        redact=config.external_agent_redact_sensitive_values,
    )

    prompt_context = dict(package_payload)
    prompt_context["required_actions"] = _bullet_list(package_payload["required_actions"])
    prompt_context["forbidden_actions"] = _bullet_list(package_payload["forbidden_actions"])
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
    if config.external_agent_include_inspection_report:
        _write_text(
            dest / "inspection_report.md",
            render_inspection_report(
                {"job_id": job_id, "title": title, "draft_id": package.draft_id}
            ),
            redact=config.external_agent_redact_sensitive_values,
        )
    if config.external_agent_include_article_preview:
        preview = (
            '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
            f"<title>{escape(str(title))}</title></head><body>{render_for_publish(title, body)}</body></html>"
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
        "inspection_report_required": True,
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
                "inspection_report_required": True,
            },
            ensure_ascii=False,
        ),
    )
    conn.commit()
    files: list[str] = []
    with open_directory_handle(dest, allowed_roots=(dest,)) as handle:
        for name in handle.list_names():
            try:
                handle.read_regular_file(name)
            except UnsafePathError:
                continue
            files.append(name)
    handoff = (
        "请把 browser_agent_prompt.md 交给外部工具；它只能执行只读核对。"
        if config.external_agent_include_prompt
        else "任务包只授权只读核对；不得执行任何公众号后台写操作。"
    )
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
            handoff,
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
            JOIN wechat_drafts d
              ON d.article_id = j.article_id
             AND d.publish_job_id = j.id
             AND d.adapter_mode = j.adapter_mode
            JOIN articles a ON a.id = j.article_id
            WHERE d.status = 'created'
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
