"""为已导入文章生成发布计划（publish_jobs）。"""

from __future__ import annotations

from datetime import datetime, timedelta

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig


def _schedule_rules(config: AppConfig) -> dict:
    rules = config.rules.get("schedule", {}) if isinstance(config.rules.get("schedule"), dict) else {}
    return {
        "max_per_day": int(rules.get("max_per_day", config.max_articles_per_day)),
        "min_hours_between": int(rules.get("min_hours_between", 4)),
        "preferred_hours": list(rules.get("preferred_hours", [9, 14, 20])),
    }


def _next_slot(
    start: datetime,
    *,
    day_counts: dict[str, int],
    max_per_day: int,
    min_hours_between: int,
    preferred_hours: list[int],
    last_scheduled: datetime | None,
) -> datetime:
    """在窗口内找下一个可用发布时间。"""
    current = start.replace(minute=0, second=0, microsecond=0)
    for _ in range(500):
        day_key = current.strftime("%Y-%m-%d")
        if day_counts.get(day_key, 0) >= max_per_day:
            current += timedelta(days=1)
            current = current.replace(hour=preferred_hours[0] if preferred_hours else 9)
            continue
        if current.hour not in preferred_hours:
            # 跳到当天下一个偏好小时
            later = [h for h in preferred_hours if h > current.hour]
            if later:
                current = current.replace(hour=later[0])
            else:
                current += timedelta(days=1)
                current = current.replace(hour=preferred_hours[0] if preferred_hours else 9)
            continue
        if last_scheduled and (current - last_scheduled).total_seconds() < min_hours_between * 3600:
            current += timedelta(hours=min_hours_between)
            continue
        return current
    return current


def build_plan(config: AppConfig) -> dict[str, int]:
    """
    为 status=imported 且尚无 pending 任务的文章创建 publish_jobs。

    返回：planned, skipped_has_job
    """
    sched = _schedule_rules(config)
    window_days = config.schedule_window_days
    now = datetime.now()
    end = now + timedelta(days=window_days)

    stats = {"planned": 0, "skipped_has_job": 0}

    with db.connect(config.database_path) as conn:
        articles = conn.execute(
            """
            SELECT a.id FROM articles a
            WHERE a.status = 'imported'
            AND NOT EXISTS (
                SELECT 1 FROM publish_jobs j
                WHERE j.article_id = a.id AND j.status IN ('pending', 'running')
            )
            ORDER BY a.created_at ASC
            """
        ).fetchall()

        existing_jobs = conn.execute(
            "SELECT scheduled_at FROM publish_jobs WHERE status IN ('pending', 'running', 'done')"
        ).fetchall()
        day_counts: dict[str, int] = {}
        last_scheduled: datetime | None = None
        for row in existing_jobs:
            try:
                dt = datetime.fromisoformat(row["scheduled_at"])
            except ValueError:
                continue
            day_key = dt.strftime("%Y-%m-%d")
            day_counts[day_key] = day_counts.get(day_key, 0) + 1
            if last_scheduled is None or dt > last_scheduled:
                last_scheduled = dt

        slot_start = now
        for row in articles:
            article_id = int(row["id"])
            pending = conn.execute(
                "SELECT id FROM publish_jobs WHERE article_id = ? AND status = 'pending' LIMIT 1",
                (article_id,),
            ).fetchone()
            if pending:
                stats["skipped_has_job"] += 1
                continue

            slot = _next_slot(
                slot_start,
                day_counts=day_counts,
                max_per_day=sched["max_per_day"],
                min_hours_between=sched["min_hours_between"],
                preferred_hours=sched["preferred_hours"],
                last_scheduled=last_scheduled,
            )
            if slot > end:
                break

            conn.execute(
                """
                INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
                VALUES (?, ?, 'pending', ?)
                """,
                (article_id, slot.isoformat(timespec="seconds"), config.wechat_mode),
            )
            day_key = slot.strftime("%Y-%m-%d")
            day_counts[day_key] = day_counts.get(day_key, 0) + 1
            last_scheduled = slot
            slot_start = slot + timedelta(hours=1)
            db.log_event(conn, entity_type="publish_job", entity_id=article_id, event_type="plan_created")
            stats["planned"] += 1
        conn.commit()

    return stats
