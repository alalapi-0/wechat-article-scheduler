"""合集排期规则（Round 64 / 收敛 Phase 1 Round 9）。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.content_library.collection_config import CollectionConfig


@dataclass(frozen=True)
class CollectionScheduleRules:
    """单合集或全局默认的排期参数。"""

    max_per_day: int
    min_hours_between: int
    preferred_hours: tuple[int, ...]
    stagger_hours: int
    window_days: int | None = None

    def label(self) -> str:
        hours = ",".join(str(h) for h in self.preferred_hours)
        return (
            f"每日最多 {self.max_per_day} 篇，间隔 ≥{self.min_hours_between} 小时，"
            f"偏好时段 {hours}"
        )


def global_schedule_rules(config: AppConfig) -> CollectionScheduleRules:
    block = config.rules.get("schedule", {}) if isinstance(config.rules.get("schedule"), dict) else {}
    hours = block.get("preferred_hours", [9, 14, 20])
    return CollectionScheduleRules(
        max_per_day=int(block.get("max_per_day", config.max_articles_per_day)),
        min_hours_between=int(block.get("min_hours_between", 4)),
        preferred_hours=tuple(int(h) for h in hours),
        stagger_hours=0,
        window_days=int(block["window_days"]) if block.get("window_days") else None,
    )


def schedule_rules_from_yaml_block(
    block: dict[str, Any] | None,
    *,
    fallback: CollectionScheduleRules,
) -> CollectionScheduleRules:
    if not block or not isinstance(block, dict):
        return fallback
    hours = block.get("preferred_hours", list(fallback.preferred_hours))
    return CollectionScheduleRules(
        max_per_day=int(block.get("max_per_day", fallback.max_per_day)),
        min_hours_between=int(block.get("min_hours_between", fallback.min_hours_between)),
        preferred_hours=tuple(int(h) for h in hours),
        stagger_hours=int(block.get("stagger_hours", fallback.stagger_hours)),
        window_days=int(block["window_days"]) if block.get("window_days") is not None else fallback.window_days,
    )


def schedule_rules_for_collection(
    config: AppConfig,
    coll: CollectionConfig | None,
) -> CollectionScheduleRules:
    base = global_schedule_rules(config)
    if coll is None:
        return base
    if coll.schedule_raw is not None:
        return schedule_rules_from_yaml_block(coll.schedule_raw, fallback=base)
    raw = yaml_schedule_from_path(coll.yaml_path)
    return schedule_rules_from_yaml_block(raw, fallback=base)


def yaml_schedule_from_path(yaml_path: Any) -> dict[str, Any] | None:
    import yaml

    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except OSError:
        return None
    if not isinstance(data, dict):
        return None
    sched = data.get("schedule")
    return sched if isinstance(sched, dict) else None


def schedule_rules_from_config_json(config_json: str | None, *, fallback: CollectionScheduleRules) -> CollectionScheduleRules:
    if not config_json:
        return fallback
    try:
        data = json.loads(config_json)
    except json.JSONDecodeError:
        return fallback
    sched = data.get("schedule") if isinstance(data, dict) else None
    return schedule_rules_from_yaml_block(sched if isinstance(sched, dict) else None, fallback=fallback)


def day_count_key(collection_slug: str, day: str) -> str:
    return f"{collection_slug}:{day}"


def load_existing_schedule_state(conn: Any) -> tuple[dict[str, int], datetime | None]:
    """从已有任务统计各合集每日篇数与最近排期时间。"""
    rows = conn.execute(
        """
        SELECT j.scheduled_at, COALESCE(c.slug, 'default') AS collection_slug
        FROM publish_jobs j
        JOIN articles a ON a.id = j.article_id
        LEFT JOIN collections c ON c.id = a.collection_id
        WHERE j.status IN ('pending', 'running', 'done')
        """
    ).fetchall()
    day_counts: dict[str, int] = {}
    last_scheduled: datetime | None = None
    for row in rows:
        try:
            dt = datetime.fromisoformat(row["scheduled_at"])
        except (TypeError, ValueError):
            continue
        slug = row["collection_slug"] or "default"
        day_key = day_count_key(slug, dt.strftime("%Y-%m-%d"))
        day_counts[day_key] = day_counts.get(day_key, 0) + 1
        if last_scheduled is None or dt > last_scheduled:
            last_scheduled = dt
    return day_counts, last_scheduled


def collection_plan_window_days(config: AppConfig, rules: CollectionScheduleRules) -> int:
    if rules.window_days is not None:
        return rules.window_days
    return config.schedule_window_days
