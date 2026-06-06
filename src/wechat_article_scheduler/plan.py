"""为已导入文章生成发布计划（publish_jobs），支持合集级排期规则。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.content_library.collection_config import (
    CollectionConfig,
    discover_collection_configs,
)
from wechat_article_scheduler.content_library.collection_schedule import (
    CollectionScheduleRules,
    collection_plan_window_days,
    day_count_key,
    global_schedule_rules,
    load_existing_schedule_state,
    schedule_rules_for_collection,
    schedule_rules_from_config_json,
)
from wechat_article_scheduler.weekly_plan import advance_cursor


def _next_slot(
    start: datetime,
    *,
    floor: datetime | None = None,
    day_counts: dict[str, int],
    collection_slug: str,
    max_per_day: int,
    min_hours_between: int,
    preferred_hours: list[int] | tuple[int, ...],
    last_scheduled: datetime | None,
) -> datetime:
    """在窗口内找下一个可用发布时间（不早于 floor）。"""
    not_before = (floor or start).replace(microsecond=0)
    current = start.replace(minute=0, second=0, microsecond=0)
    if current < not_before:
        current = not_before.replace(second=0)
        if current < not_before:
            current = not_before
    pref = list(preferred_hours)
    for _ in range(500):
        day = current.strftime("%Y-%m-%d")
        key = day_count_key(collection_slug, day)
        if day_counts.get(key, 0) >= max_per_day:
            current += timedelta(days=1)
            current = current.replace(hour=pref[0] if pref else 9, minute=0, second=0)
            continue
        if pref and current.hour not in pref:
            later = [h for h in pref if h > current.hour]
            if later:
                current = current.replace(hour=later[0], minute=0, second=0)
            else:
                current += timedelta(days=1)
                current = current.replace(hour=pref[0], minute=0, second=0)
            continue
        if last_scheduled and (current - last_scheduled).total_seconds() < min_hours_between * 3600:
            current += timedelta(hours=min_hours_between)
            continue
        if current < not_before:
            current = not_before.replace(second=0)
            if current < not_before:
                current = not_before
            continue
        return current
    if current < not_before:
        return not_before
    return current


def _schedule_rules(config: AppConfig) -> dict[str, int | list[int]]:
    """向后兼容：全局 schedule 规则 dict。"""
    g = global_schedule_rules(config)
    return {
        "max_per_day": g.max_per_day,
        "min_hours_between": g.min_hours_between,
        "preferred_hours": list(g.preferred_hours),
    }


def _collection_config_map(config: AppConfig) -> dict[str, CollectionConfig]:
    return {c.slug: c for c in discover_collection_configs(config.root)}


def _fetch_plan_groups(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT a.id, a.created_at,
               COALESCE(c.slug, 'default') AS collection_slug,
               COALESCE(c.name, '默认集合') AS collection_name,
               c.config_json
        FROM articles a
        LEFT JOIN collections c ON c.id = a.collection_id
        WHERE a.status = 'imported'
          AND COALESCE(a.schedule_state, 'imported') = 'imported'
          AND (a.deleted_at IS NULL OR a.deleted_at = '')
          AND NOT EXISTS (
              SELECT 1 FROM publish_jobs j
              WHERE j.article_id = a.id AND j.status IN ('pending', 'running')
          )
        ORDER BY collection_slug, a.created_at ASC
        """
    ).fetchall()
    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        slug = row["collection_slug"] or "default"
        if slug not in groups:
            groups[slug] = {
                "slug": slug,
                "name": row["collection_name"] or slug,
                "config_json": row["config_json"],
                "article_ids": [],
            }
        groups[slug]["article_ids"].append(int(row["id"]))
    order = sorted(groups.keys(), key=lambda s: (0 if s == "default" else 1, s))
    return [groups[s] for s in order]


def build_plan(config: AppConfig) -> dict[str, Any]:
    """
    为 status=imported 且尚无 pending 任务的文章创建 publish_jobs（按合集规则错峰）。

    返回：planned, skipped_has_job, by_collection, hints
    """
    global_rules = global_schedule_rules(config)
    coll_map = _collection_config_map(config)
    now = datetime.now()

    stats: dict[str, Any] = {
        "planned": 0,
        "skipped_has_job": 0,
        "by_collection": {},
        "hints": [],
    }

    with db.connect(config.database_path) as conn:
        day_counts, last_scheduled = load_existing_schedule_state(conn)
        groups = _fetch_plan_groups(conn)

        for group in groups:
            slug = str(group["slug"])
            name = str(group["name"])
            coll_cfg = coll_map.get(slug)
            if coll_cfg is None and group.get("config_json"):
                rules = schedule_rules_from_config_json(
                    group["config_json"],
                    fallback=global_rules,
                )
            else:
                rules = schedule_rules_for_collection(config, coll_cfg)
            window_days = collection_plan_window_days(config, rules)
            end = now + timedelta(days=window_days)

            if last_scheduled and rules.stagger_hours:
                slot_start = last_scheduled + timedelta(hours=rules.stagger_hours)
            else:
                slot_start = now

            coll_stats = {"planned": 0, "skipped_window": 0, "rules_label": rules.label()}
            article_ids: list[int] = group["article_ids"]

            for article_id in article_ids:
                pending = conn.execute(
                    "SELECT id FROM publish_jobs WHERE article_id = ? AND status = 'pending' LIMIT 1",
                    (article_id,),
                ).fetchone()
                if pending:
                    stats["skipped_has_job"] = int(stats["skipped_has_job"]) + 1
                    continue

                effective_min_gap = max(global_rules.min_hours_between, rules.min_hours_between)
                slot = _next_slot(
                    slot_start,
                    floor=now,
                    day_counts=day_counts,
                    collection_slug=slug,
                    max_per_day=rules.max_per_day,
                    min_hours_between=effective_min_gap,
                    preferred_hours=rules.preferred_hours,
                    last_scheduled=last_scheduled,
                )
                if slot > end:
                    coll_stats["skipped_window"] += 1
                    stats["hints"].append(
                        f"合集「{name}」部分作品超出 {window_days} 天排期窗口，请手动安排或调大 window_days"
                    )
                    break

                conn.execute(
                    """
                    INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, source_kind)
                    VALUES (?, ?, 'pending', ?, 'local')
                    """,
                    (article_id, slot.isoformat(timespec="seconds"), config.wechat_mode),
                )
                conn.execute(
                    """
                    UPDATE articles SET schedule_state = 'scheduled_local', updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (article_id,),
                )
                key = day_count_key(slug, slot.strftime("%Y-%m-%d"))
                day_counts[key] = day_counts.get(key, 0) + 1
                last_scheduled = slot
                slot_start = slot + timedelta(hours=1)
                db.log_event(
                    conn,
                    entity_type="publish_job",
                    entity_id=article_id,
                    event_type="plan_created",
                    payload=slug,
                )
                coll_stats["planned"] += 1
                stats["planned"] = int(stats["planned"]) + 1

            if coll_stats["planned"]:
                advance_cursor(conn, slug, delta=coll_stats["planned"])
            if coll_stats["planned"] or coll_stats["skipped_window"]:
                stats["by_collection"][slug] = coll_stats
                stats["hints"].append(
                    f"合集「{name}」：{coll_stats['planned']} 篇已排期（{rules.label()}）"
                )

        conn.commit()

    return stats
