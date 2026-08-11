"""跨周续排不会重复选择已完成文章。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from tests.conftest import make_test_config
from wechat_article_scheduler import db
from wechat_article_scheduler.plan import build_plan


def test_plan_window_counts_calendar_days_without_including_day_eight(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "calendar-window.sqlite3"
    db.init_db(db_path)
    config = make_test_config(
        tmp_path,
        db_path,
        schedule_window_days=7,
        max_articles_per_day=5,
        rules={
            "schedule": {
                "max_per_day": 5,
                "min_hours_between": 3,
                "preferred_hours": [9, 12, 15, 18, 21],
                "window_days": 7,
            }
        },
    )
    with db.connect(db_path) as conn:
        for index in range(50):
            conn.execute(
                "INSERT INTO articles "
                "(source_path, title, summary, body, content_hash, status, schedule_state) "
                "VALUES (?, ?, '', 'body', ?, 'imported', 'imported')",
                (f"/tmp/calendar-{index}.md", f"文章{index:03d}", f"calendar-{index}"),
            )
        conn.commit()

    stats = build_plan(config, now=datetime(2026, 8, 5, 9, 0, 0))

    assert stats["planned"] == 35
    with db.connect(db_path) as conn:
        scheduled_dates = {
            row["scheduled_at"][:10]
            for row in conn.execute("SELECT scheduled_at FROM publish_jobs").fetchall()
        }
    assert scheduled_dates == {
        "2026-08-05",
        "2026-08-06",
        "2026-08-07",
        "2026-08-08",
        "2026-08-09",
        "2026-08-10",
        "2026-08-11",
    }


def test_three_schedule_windows_do_not_repeat_articles(tmp_path: Path) -> None:
    db_path = tmp_path / "weekly.sqlite3"
    db.init_db(db_path)
    config = make_test_config(
        tmp_path,
        db_path,
        schedule_window_days=7,
        max_articles_per_day=5,
        rules={
            "schedule": {
                "max_per_day": 5,
                "min_hours_between": 3,
                "preferred_hours": [9, 12, 15, 18, 21],
                "window_days": 7,
            },
            "publish": {"auto_execute": True},
        },
    )
    with db.connect(db_path) as conn:
        for index in range(100):
            conn.execute(
                "INSERT INTO articles "
                "(source_path, title, summary, body, content_hash, status, schedule_state) "
                "VALUES (?, ?, '', ?, ?, 'imported', 'imported')",
                (f"/tmp/{index}.md", f"文章{index:03d}", f"正文{index}", f"hash-{index}"),
            )
        conn.commit()

    batches: list[set[int]] = []
    fixed_now = datetime(2026, 8, 5, 21, 21, 32)
    for window_index in range(3):
        window_now = fixed_now + timedelta(days=window_index * 7)
        stats = build_plan(config, now=window_now)
        assert 28 <= stats["planned"] <= 35
        with db.connect(db_path) as conn:
            batch = {
                int(row["article_id"])
                for row in conn.execute(
                    "SELECT article_id FROM publish_jobs WHERE status = 'pending'"
                ).fetchall()
            }
            batches.append(batch)
            placeholders = ",".join("?" for _ in batch)
            conn.execute("UPDATE publish_jobs SET status = 'done' WHERE status = 'pending'")
            conn.execute(
                f"UPDATE articles SET schedule_state = 'remote_draft_ready' "
                f"WHERE id IN ({placeholders})",
                tuple(sorted(batch)),
            )
            conn.commit()

    assert batches[0].isdisjoint(batches[1])
    assert batches[0].isdisjoint(batches[2])
    assert batches[1].isdisjoint(batches[2])
