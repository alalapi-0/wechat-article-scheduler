"""用户指定发布时间：单篇与批量错峰排期。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Literal

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.publish_config import (
    PublishConfig,
    defaults_from_rules,
    publish_config_to_json,
)

SortOrder = Literal["asc", "desc"]
IntervalUnit = Literal["minutes", "hours"]


def ensure_future(dt: datetime, *, now: datetime | None = None) -> datetime:
    """确保时间不早于当前时刻（秒级）。"""
    floor = (now or datetime.now()).replace(microsecond=0)
    candidate = dt.replace(microsecond=0)
    if candidate < floor:
        return floor
    return candidate


def parse_scheduled_at(raw: str) -> datetime:
    """解析 ISO 或 flatpickr 常见格式。"""
    text = (raw or "").strip()
    if not text:
        raise ValueError("请填写发布时间")
    normalized = text.replace(" ", "T") if "T" not in text and " " in text else text
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("发布时间格式无效，请重新选择") from exc


def _upsert_pending_job(
    conn: Any,
    *,
    article_id: int,
    scheduled_at: datetime,
    adapter_mode: str,
    publish_config: PublishConfig | None = None,
) -> bool:
    """创建或更新 pending 任务。返回 True 表示新建，False 表示更新。"""
    iso = scheduled_at.isoformat(timespec="seconds")
    config_json = publish_config_to_json(publish_config) if publish_config else None
    pending = conn.execute(
        "SELECT id FROM publish_jobs WHERE article_id = ? AND status = 'pending' LIMIT 1",
        (article_id,),
    ).fetchone()
    if pending:
        if config_json is not None:
            conn.execute(
                """
                UPDATE publish_jobs
                SET scheduled_at = ?, publish_config_json = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (iso, config_json, pending["id"]),
            )
        else:
            conn.execute(
                """
                UPDATE publish_jobs
                SET scheduled_at = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (iso, pending["id"]),
            )
        return False
    if config_json is not None:
        conn.execute(
            """
            INSERT INTO publish_jobs
            (article_id, scheduled_at, status, adapter_mode, publish_config_json)
            VALUES (?, ?, 'pending', ?, ?)
            """,
            (article_id, iso, adapter_mode, config_json),
        )
    else:
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
            VALUES (?, ?, 'pending', ?)
            """,
            (article_id, iso, adapter_mode),
        )
    return True


def assign_article_schedule(
    config: AppConfig,
    article_id: int,
    scheduled_at: datetime,
    *,
    now: datetime | None = None,
    publish_config: PublishConfig | None = None,
) -> dict[str, Any]:
    """为单篇文章设定发布时间与发布配置。"""
    when = ensure_future(scheduled_at, now=now)
    pub_cfg = publish_config or defaults_from_rules(config)
    with db.connect(config.database_path) as conn:
        row = conn.execute(
            """
            SELECT id, title, status FROM articles
            WHERE id = ? AND (deleted_at IS NULL OR deleted_at = '')
            """,
            (article_id,),
        ).fetchone()
        if row is None:
            raise ValueError("作品不存在")
        if row["status"] not in ("imported",):
            raise ValueError("仅「已收录」作品可安排发布时间")

        created = _upsert_pending_job(
            conn,
            article_id=article_id,
            scheduled_at=when,
            adapter_mode=config.wechat_mode,
            publish_config=pub_cfg,
        )
        db.log_event(
            conn,
            entity_type="publish_job",
            entity_id=article_id,
            event_type="plan_created",
        )
        conn.commit()

    return {
        "article_id": article_id,
        "title": row["title"],
        "scheduled_at": when.isoformat(timespec="seconds"),
        "created": created,
        "publish_config": pub_cfg.normalized().__dict__,
    }


def compute_batch_times(
    *,
    anchor: datetime,
    count: int,
    sort_order: SortOrder,
    interval: int,
    interval_unit: IntervalUnit,
    titles: list[tuple[int, str]],
    now: datetime | None = None,
) -> list[tuple[int, datetime]]:
    """按标题排序后，从锚点时间起错峰生成发布时间。"""
    if count <= 0:
        return []
    if interval < 1:
        raise ValueError("间隔必须至少为 1")
    step = timedelta(minutes=interval) if interval_unit == "minutes" else timedelta(hours=interval)
    floor = ensure_future(anchor, now=now)

    ordered = sorted(titles, key=lambda x: (x[1] or "").casefold())
    if sort_order == "desc":
        ordered.reverse()

    out: list[tuple[int, datetime]] = []
    for i, (article_id, _title) in enumerate(ordered[:count]):
        slot = floor + step * i
        out.append((article_id, ensure_future(slot, now=now)))
    return out


def assign_batch_schedule(
    config: AppConfig,
    article_ids: list[int],
    *,
    anchor: datetime,
    sort_order: SortOrder = "asc",
    interval: int = 5,
    interval_unit: IntervalUnit = "minutes",
    now: datetime | None = None,
    publish_config: PublishConfig | None = None,
) -> dict[str, int]:
    """批量错峰安排发布时间与统一发布配置。"""
    pub_cfg = (publish_config or defaults_from_rules(config)).normalized()
    unique_ids = []
    seen: set[int] = set()
    for raw in article_ids:
        aid = int(raw)
        if aid not in seen:
            seen.add(aid)
            unique_ids.append(aid)
    if not unique_ids:
        return {"scheduled": 0, "skipped": 0, "updated": 0}

    stats = {"scheduled": 0, "skipped": 0, "updated": 0}
    with db.connect(config.database_path) as conn:
        titles: list[tuple[int, str]] = []
        for aid in unique_ids:
            row = conn.execute(
                """
                SELECT id, title, status FROM articles
                WHERE id = ? AND (deleted_at IS NULL OR deleted_at = '')
                """,
                (aid,),
            ).fetchone()
            if row is None or row["status"] != "imported":
                stats["skipped"] += 1
                continue
            titles.append((int(row["id"]), str(row["title"] or "")))

        slots = compute_batch_times(
            anchor=anchor,
            count=len(titles),
            sort_order=sort_order,
            interval=interval,
            interval_unit=interval_unit,
            titles=titles,
            now=now,
        )
        for article_id, when in slots:
            created = _upsert_pending_job(
                conn,
                article_id=article_id,
                scheduled_at=when,
                adapter_mode=config.wechat_mode,
                publish_config=pub_cfg,
            )
            if created:
                stats["scheduled"] += 1
            else:
                stats["updated"] += 1
            db.log_event(
                conn,
                entity_type="publish_job",
                entity_id=article_id,
                event_type="plan_created",
            )
        conn.commit()

    return {**stats, "publish_config": pub_cfg.normalized().__dict__}
