"""发布排期：防过去时间、单篇与批量错峰。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.plan import _next_slot, build_plan
from wechat_article_scheduler.schedule_assign import (
    assign_batch_schedule,
    compute_batch_times,
    ensure_future,
    parse_scheduled_at,
)
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path):
    db_path = tmp_path / "schedule.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg)), cfg


def test_ensure_future_clamps_past() -> None:
    now = datetime(2026, 5, 31, 20, 30, 0)
    past = datetime(2026, 5, 31, 20, 0, 0)
    assert ensure_future(past, now=now) == now


def test_next_slot_not_before_floor() -> None:
    """20:30 时不应落到当天 20:00。"""
    now = datetime(2026, 5, 31, 20, 30, 0)
    slot = _next_slot(
        now,
        floor=now,
        day_counts={},
        max_per_day=3,
        min_hours_between=1,
        preferred_hours=[9, 14, 20],
        last_scheduled=None,
    )
    assert slot >= now


def test_build_plan_never_schedules_in_past(tmp_path: Path) -> None:
    root = tmp_path
    db_path = root / "data.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('/x.md', 'T', 'S', 'B', 'hash1', 'imported')",
        )
        conn.commit()

    cfg = make_test_config(
        root,
        db_path,
        rules={
            "schedule": {
                "max_per_day": 3,
                "min_hours_between": 1,
                "preferred_hours": [9, 14, 20],
            }
        },
    )
    fake_now = datetime(2026, 5, 31, 20, 30, 0)
    with patch("wechat_article_scheduler.plan.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        stats = build_plan(cfg)

    assert stats["planned"] == 1
    with db.connect(db_path) as conn:
        row = conn.execute("SELECT scheduled_at FROM publish_jobs").fetchone()
        scheduled = datetime.fromisoformat(row["scheduled_at"])
    assert scheduled >= fake_now


def test_compute_batch_times_sort_and_stagger() -> None:
    anchor = datetime(2026, 6, 1, 10, 0, 0)
    titles = [(2, "Beta"), (1, "Alpha"), (3, "Gamma")]
    slots = compute_batch_times(
        anchor=anchor,
        count=3,
        sort_order="asc",
        interval=30,
        interval_unit="minutes",
        titles=titles,
        now=anchor - timedelta(hours=1),
    )
    assert [aid for aid, _ in slots] == [1, 2, 3]
    assert slots[0][1] == anchor
    assert slots[1][1] == anchor + timedelta(minutes=30)
    assert slots[2][1] == anchor + timedelta(minutes=60)

    desc = compute_batch_times(
        anchor=anchor,
        count=3,
        sort_order="desc",
        interval=1,
        interval_unit="hours",
        titles=titles,
        now=anchor - timedelta(hours=1),
    )
    assert [aid for aid, _ in desc] == [3, 2, 1]


def test_parse_scheduled_at_accepts_space_separated() -> None:
    dt = parse_scheduled_at("2026-06-01 15:30")
    assert dt == datetime(2026, 6, 1, 15, 30)


def _insert_imported(conn, title: str) -> int:
    conn.execute(
        "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
        "VALUES (?, ?, 'S', 'B', ?, 'imported')",
        (f"/{title}.md", title, f"hash-{title}"),
    )
    return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])


def test_single_schedule_api(client) -> None:
    c, cfg = client
    with db.connect(cfg.database_path) as conn:
        aid = _insert_imported(conn, "单篇")
        conn.commit()
    future = (datetime.now() + timedelta(hours=2)).replace(second=0, microsecond=0)
    r = c.post(
        f"/api/articles/{aid}/schedule",
        json={"scheduled_at": future.strftime("%Y-%m-%d %H:%M")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["scheduled_at"] == future.isoformat(timespec="seconds")
    with db.connect(cfg.database_path) as conn:
        row = conn.execute(
            "SELECT scheduled_at, status FROM publish_jobs WHERE article_id = ?",
            (aid,),
        ).fetchone()
    assert row["status"] == "pending"
    assert row["scheduled_at"] == future.isoformat(timespec="seconds")


def test_single_schedule_rejects_past(client) -> None:
    c, cfg = client
    with db.connect(cfg.database_path) as conn:
        aid = _insert_imported(conn, "过去")
        conn.commit()
    past = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    r = c.post(f"/api/articles/{aid}/schedule", json={"scheduled_at": past})
    assert r.status_code == 200
    with db.connect(cfg.database_path) as conn:
        row = conn.execute(
            "SELECT scheduled_at FROM publish_jobs WHERE article_id = ?",
            (aid,),
        ).fetchone()
    scheduled = datetime.fromisoformat(row["scheduled_at"])
    assert scheduled >= datetime.now().replace(microsecond=0) - timedelta(seconds=2)


def test_batch_schedule_api(client) -> None:
    c, cfg = client
    with db.connect(cfg.database_path) as conn:
        a = _insert_imported(conn, "Apple")
        b = _insert_imported(conn, "Banana")
        conn.commit()
    anchor = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    r = c.post(
        "/api/articles/batch-schedule",
        json={
            "ids": [b, a],
            "anchor_at": anchor.strftime("%Y-%m-%d %H:%M"),
            "sort_order": "asc",
            "interval": 45,
            "interval_unit": "minutes",
        },
    )
    assert r.status_code == 200
    assert r.json()["scheduled"] == 2
    with db.connect(cfg.database_path) as conn:
        rows = conn.execute(
            """
            SELECT a.title, j.scheduled_at FROM publish_jobs j
            JOIN articles a ON a.id = j.article_id
            WHERE j.status = 'pending'
            ORDER BY j.scheduled_at ASC
            """
        ).fetchall()
    assert len(rows) == 2
    assert rows[0]["title"] == "Apple"
    assert rows[1]["title"] == "Banana"
    t0 = datetime.fromisoformat(rows[0]["scheduled_at"])
    t1 = datetime.fromisoformat(rows[1]["scheduled_at"])
    assert t1 - t0 == timedelta(minutes=45)


def test_batch_schedule_api_defaults_to_five_minutes(client) -> None:
    c, cfg = client
    with db.connect(cfg.database_path) as conn:
        a = _insert_imported(conn, "001")
        b = _insert_imported(conn, "002")
        conn.commit()
    anchor = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    r = c.post(
        "/api/articles/batch-schedule",
        json={
            "ids": [b, a],
            "anchor_at": anchor.strftime("%Y-%m-%d %H:%M"),
            "sort_order": "asc",
        },
    )
    assert r.status_code == 200
    with db.connect(cfg.database_path) as conn:
        rows = conn.execute(
            """
            SELECT j.scheduled_at FROM publish_jobs j
            JOIN articles a ON a.id = j.article_id
            WHERE j.status = 'pending'
            ORDER BY j.scheduled_at ASC
            """
        ).fetchall()
    assert datetime.fromisoformat(rows[1]["scheduled_at"]) - datetime.fromisoformat(
        rows[0]["scheduled_at"]
    ) == timedelta(minutes=5)


def test_batch_schedule_assign_direct(tmp_path: Path) -> None:
    db_path = tmp_path / "d.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    with db.connect(db_path) as conn:
        ids = [_insert_imported(conn, "Zulu"), _insert_imported(conn, "Alpha")]
        conn.commit()
    anchor = datetime(2026, 7, 1, 12, 0, 0)
    stats = assign_batch_schedule(
        cfg,
        ids,
        anchor=anchor,
        sort_order="desc",
        interval=2,
        interval_unit="hours",
        now=datetime(2026, 6, 1, 0, 0, 0),
    )
    assert stats["scheduled"] == 2
    with db.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT a.title, j.scheduled_at FROM publish_jobs j
            JOIN articles a ON a.id = j.article_id
            ORDER BY j.scheduled_at ASC
            """
        ).fetchall()
    assert rows[0]["title"] == "Zulu"
    assert rows[1]["title"] == "Alpha"


def test_index_has_schedule_ui(client) -> None:
    c, _cfg = client
    html = c.get("/").text
    assert "批量发布设置" in html
    assert "scheduleModalBack" in html
    assert "flatpickr" in html
    assert "安排时间" in html
