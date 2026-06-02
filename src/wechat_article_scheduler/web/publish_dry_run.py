"""单篇作品发布 dry-run 摘要（只读、不联网，mock 安全）。"""

from __future__ import annotations

from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.core.state_machine import PublishStatus, ScheduleState
from wechat_article_scheduler.publish_config import parse_publish_config, defaults_from_rules
from wechat_article_scheduler.publish_policy import resolve_effective_submit
from wechat_article_scheduler.web.article_preflight import (
    article_preflight_checks,
    build_article_preflight_summary,
)
from wechat_article_scheduler.web.user_copy import label_mode


def _load_article_row(conn: Any, article_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT a.id, a.title, a.summary, a.body, a.status, a.cover_path,
               a.source_path, a.updated_at
        FROM articles a
        WHERE a.id = ? AND (a.deleted_at IS NULL OR a.deleted_at = '')
        """,
        (article_id,),
    ).fetchone()
    return dict(row) if row else None


def _latest_job_row(conn: Any, article_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id, status, scheduled_at, adapter_mode, publish_config_json, retry_count
        FROM publish_jobs
        WHERE article_id = ? AND status != 'cancelled'
        ORDER BY id DESC LIMIT 1
        """,
        (article_id,),
    ).fetchone()
    return dict(row) if row else None


def _simulate_steps(
    *,
    config: AppConfig,
    job: dict[str, Any] | None,
    preflight_ready: bool,
) -> list[dict[str, str]]:
    mode = (config.wechat_mode or "mock").strip().lower()
    steps: list[dict[str, str]] = [
        {"state": "imported", "label": "作品已入库", "outcome": "ok"},
    ]
    if job:
        steps.append(
            {
                "state": str(job.get("status") or "pending"),
                "label": "发布任务",
                "outcome": "scheduled",
            }
        )
    else:
        steps.append(
            {
                "state": ScheduleState.PENDING.value,
                "label": "尚未创建发布任务",
                "outcome": "pending",
            }
        )

    if not preflight_ready:
        steps.append(
            {
                "state": PublishStatus.READY.value,
                "label": "预检未通过",
                "outcome": "blocked",
            }
        )
        return steps

    if mode == "mock" or config.dry_run:
        steps.append(
            {
                "state": PublishStatus.PUBLISHING.value,
                "label": "演练执行（mock）",
                "outcome": "dry_run",
            }
        )
        steps.append(
            {
                "state": PublishStatus.PUBLISHED.value,
                "label": "演练完成",
                "outcome": "simulated",
            }
        )
    else:
        steps.append(
            {
                "state": PublishStatus.WAITING_CONFIRMATION.value,
                "label": "可能需人工确认",
                "outcome": "hint",
            }
        )
    return steps


def build_article_publish_dry_run(
    config: AppConfig,
    conn: Any,
    article_id: int,
) -> dict[str, Any]:
    """构建只读 dry-run JSON；不调用微信 API、不写库。"""
    row = _load_article_row(conn, article_id)
    if not row:
        return {"ok": False, "error": "作品不存在", "article_id": article_id}

    preflight = build_article_preflight_summary(row, config)
    checks = article_preflight_checks(row, config)
    job = _latest_job_row(conn, article_id)
    mode = (config.wechat_mode or "mock").strip().lower()

    effective = None
    if job:
        pub = parse_publish_config(
            job.get("publish_config_json"),
            defaults=defaults_from_rules(config),
        )
        effective = resolve_effective_submit(app_config=config, job_config=pub)

    steps = _simulate_steps(
        config=config,
        job=job,
        preflight_ready=bool(preflight.get("ready")),
    )
    network = False
    mock_safe = mode == "mock" or bool(config.dry_run) or not config.wechat_enable_publish

    human: list[str] = [
        f"作品 #{article_id}「{row.get('title') or '（无标题）'}」发布 dry-run（只读）",
        "不会联网、不会修改数据库或公众号后台。",
    ]
    if mock_safe:
        human.append("当前配置为 mock/演练安全：即使执行到点也不会真实发布。")
    else:
        human.append("真实 API 已启用：dry-run 仅模拟，run-once 仍可能真实发布。")
    if not preflight.get("ready"):
        human.append(preflight.get("bar_text") or "预检未通过")
    elif job:
        human.append(f"最近任务状态：{job.get('status')}")
    else:
        human.append("尚无发布任务，需先安排时间。")

    report = {
        "article": {
            "id": article_id,
            "title": row.get("title"),
            "status": row.get("status"),
        },
        "job": job,
        "preflight": preflight,
        "effective_submit": effective,
        "simulated_steps": steps,
        "state_machine_reference": {
            "publish_statuses": [s.value for s in PublishStatus],
            "schedule_states": [s.value for s in ScheduleState],
        },
    }

    return {
        "ok": True,
        "article_id": article_id,
        "mode": "dry_run",
        "mock_safe": mock_safe,
        "network": network,
        "wechat_mode": mode,
        "dry_run_flag": bool(config.dry_run),
        "preflight_ready": bool(preflight.get("ready")),
        "summary": human[0],
        "gate_summary": (
            f"{'可通过' if preflight.get('ready') else '阻塞'} · "
            f"{'mock 安全' if mock_safe else '真实模式'} · "
            f"{len(steps)} 步模拟"
        ),
        "checks": checks,
        "human": human,
        "report": report,
    }
