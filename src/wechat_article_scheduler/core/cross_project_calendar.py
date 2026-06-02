"""跨项目发布日历预研：从 projects.yaml + manifest targets 聚合视图与冲突检测（不写库）。"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from wechat_article_scheduler.core.manifest_loader import validate_manifest_file
from wechat_article_scheduler.core.projects_registry import (
    ProjectEntry,
    default_projects_path,
    load_projects_registry,
)

DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_MIN_GAP_MINUTES = 60


def parse_scheduled_at(raw: str) -> datetime | None:
    text = str(raw).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _event_dict(
    *,
    project_id: str,
    package_id: str,
    title: str,
    platform_account_id: str,
    adapter_type: str,
    scheduled_at: datetime,
    manifest_path: str,
    target_index: int,
) -> dict[str, Any]:
    iso = scheduled_at.isoformat()
    return {
        "project_id": project_id,
        "package_id": package_id,
        "title": title,
        "platform_account_id": platform_account_id,
        "adapter_type": adapter_type,
        "scheduled_at": iso,
        "scheduled_at_utc": scheduled_at.astimezone(timezone.utc).isoformat(),
        "manifest_path": manifest_path,
        "target_index": target_index,
        "calendar_day": scheduled_at.date().isoformat(),
    }


def collect_calendar_events(
    root: Path,
    *,
    projects_path: Path | None = None,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """从多项目 manifest 收集带 scheduled_at 的 targets。"""
    entries, _meta, validation = load_projects_registry(root, projects_path)
    errors: list[str] = []
    warnings: list[str] = []
    if not validation.ok:
        return [], [f"projects 注册表无效: {validation.errors}"], warnings

    events: list[dict[str, Any]] = []
    for entry in entries:
        if not entry.enabled:
            continue
        events.extend(_events_for_project(entry, errors, warnings))
    return events, errors, warnings


def _events_for_project(
    entry: ProjectEntry,
    errors: list[str],
    warnings: list[str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for mpath in entry.manifest_paths:
        data, mval = validate_manifest_file(mpath)
        if not data:
            errors.append(f"{entry.project_id}: {mpath} 校验失败")
            continue
        if str(data.get("project_id")) != entry.project_id:
            warnings.append(
                f"{entry.project_id}: manifest project_id={data.get('project_id')} 与注册表不一致"
            )
        title = str(data.get("title") or entry.project_id)
        package_id = str(data.get("package_id") or "")
        for i, target in enumerate(data.get("targets") or []):
            if not isinstance(target, dict):
                continue
            raw = target.get("scheduled_at")
            if not raw:
                warnings.append(f"{mpath} targets[{i}] 无 scheduled_at，未进入日历")
                continue
            when = parse_scheduled_at(str(raw))
            if when is None:
                errors.append(f"{mpath} targets[{i}] scheduled_at 无法解析: {raw!r}")
                continue
            account = str(target.get("platform_account_id") or "")
            adapter = str(target.get("adapter_type") or "")
            out.append(
                _event_dict(
                    project_id=entry.project_id,
                    package_id=package_id,
                    title=title,
                    platform_account_id=account,
                    adapter_type=adapter,
                    scheduled_at=when,
                    manifest_path=str(mpath.resolve()),
                    target_index=i,
                )
            )
    return out


def detect_calendar_conflicts(
    events: list[dict[str, Any]],
    *,
    min_gap_minutes: int = DEFAULT_MIN_GAP_MINUTES,
) -> list[dict[str, Any]]:
    """检测同账号同时刻冲突与同账号最小间隔冲突。"""
    conflicts: list[dict[str, Any]] = []

    by_account_slot: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for ev in events:
        key = (ev["platform_account_id"], ev["scheduled_at"])
        by_account_slot[key].append(ev)

    for (account, slot), group in by_account_slot.items():
        if len(group) < 2:
            continue
        conflicts.append(
            {
                "type": "same_slot_same_account",
                "severity": "error",
                "platform_account_id": account,
                "scheduled_at": slot,
                "events": [_conflict_ref(e) for e in group],
                "message": f"账号 {account} 在 {slot} 有 {len(group)} 个排期重叠",
            }
        )

    by_account: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ev in events:
        by_account[ev["platform_account_id"]].append(ev)

    gap = timedelta(minutes=max(0, min_gap_minutes))
    for account, group in by_account.items():
        ordered = sorted(group, key=lambda e: e["scheduled_at"])
        for prev, nxt in zip(ordered, ordered[1:]):
            t0 = parse_scheduled_at(prev["scheduled_at"])
            t1 = parse_scheduled_at(nxt["scheduled_at"])
            if t0 is None or t1 is None:
                continue
            delta = t1 - t0
            if delta < gap and (account, prev["scheduled_at"]) != (account, nxt["scheduled_at"]):
                conflicts.append(
                    {
                        "type": "min_gap_violation",
                        "severity": "warning",
                        "platform_account_id": account,
                        "min_gap_minutes": min_gap_minutes,
                        "actual_gap_minutes": round(delta.total_seconds() / 60, 1),
                        "events": [_conflict_ref(prev), _conflict_ref(nxt)],
                        "message": (
                            f"账号 {account} 相邻排期间隔 {round(delta.total_seconds() / 60, 1)} 分钟，"
                            f"低于建议 {min_gap_minutes} 分钟"
                        ),
                    }
                )

    return conflicts


def _conflict_ref(ev: dict[str, Any]) -> dict[str, str]:
    return {
        "project_id": ev["project_id"],
        "package_id": ev["package_id"],
        "title": ev["title"],
        "scheduled_at": ev["scheduled_at"],
    }


def build_calendar_view(events: list[dict[str, Any]]) -> dict[str, Any]:
    """按日历日聚合的 dry-run 视图（只读）。"""
    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ev in sorted(events, key=lambda e: e["scheduled_at"]):
        by_day[ev["calendar_day"]].append(
            {
                "time": ev["scheduled_at"],
                "project_id": ev["project_id"],
                "package_id": ev["package_id"],
                "title": ev["title"],
                "platform_account_id": ev["platform_account_id"],
                "adapter_type": ev["adapter_type"],
            }
        )
    days = [
        {"date": day, "event_count": len(items), "events": items}
        for day, items in sorted(by_day.items())
    ]
    accounts = sorted({e["platform_account_id"] for e in events})
    projects = sorted({e["project_id"] for e in events})
    return {
        "timezone_hint": DEFAULT_TIMEZONE,
        "day_count": len(days),
        "event_count": len(events),
        "project_ids": projects,
        "platform_account_ids": accounts,
        "days": days,
    }


def build_publish_calendar_dry_run(
    root: Path,
    *,
    projects_path: Path | None = None,
    min_gap_minutes: int = DEFAULT_MIN_GAP_MINUTES,
) -> dict[str, Any]:
    path = projects_path or default_projects_path(root)
    events, errors, warnings = collect_calendar_events(root, projects_path=projects_path)
    conflicts = detect_calendar_conflicts(events, min_gap_minutes=min_gap_minutes)
    view = build_calendar_view(events)
    hard = [c for c in conflicts if c.get("severity") == "error"]
    return {
        "ok": not errors and not hard,
        "phase": "phase5_cross_project_calendar",
        "mode": "dry_run",
        "projects_path": str(path.resolve()),
        "min_gap_minutes": min_gap_minutes,
        "event_count": len(events),
        "conflict_count": len(conflicts),
        "hard_conflict_count": len(hard),
        "calendar_view": view,
        "conflicts": conflicts,
        "collection_errors": errors,
        "warnings": warnings,
        "wechat_mainline": "未读取 SQLite publish_jobs；scan/plan 仍为微信 P0",
        "note": "跨项目日历预研；manifest scheduled_at 聚合，不写库。",
    }
