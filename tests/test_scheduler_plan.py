from datetime import datetime, timedelta
from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.plan import build_plan
from wechat_article_scheduler.scheduler import run_due_jobs
from tests.conftest import make_test_config


def _config(root: Path, db_path: Path) -> AppConfig:
    return make_test_config(
        root,
        db_path,
        rules={
            "schedule": {
                "max_per_day": 2,
                "min_hours_between": 1,
                "preferred_hours": [9, 14],
            }
        },
    )


def test_build_plan_creates_pending_job(tmp_path: Path) -> None:
    root = tmp_path
    db_path = root / "data.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('/x.md', 'T', 'S', 'B', 'hash1', 'imported')",
        )
        conn.commit()

    cfg = _config(root, db_path)
    stats = build_plan(cfg)
    assert stats["planned"] == 1

    with db.connect(db_path) as conn:
        row = conn.execute("SELECT status, adapter_mode FROM publish_jobs").fetchone()
        assert row["status"] == "pending"
        assert row["adapter_mode"] == "mock"


def test_run_once_processes_due_job(tmp_path: Path) -> None:
    root = tmp_path
    (root / "articles" / "published").mkdir(parents=True)
    src = root / "articles" / "imported" / "a.md"
    src.parent.mkdir(parents=True)
    src.write_text("body", encoding="utf-8")

    db_path = root / "data.sqlite3"
    db.init_db(db_path)
    past = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")

    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES (?, 'T', 'S', 'B', 'h2', 'imported')",
            (str(src),),
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, ?, 'pending', 'mock')",
            (aid, past),
        )
        conn.commit()

    cfg = _config(root, db_path)
    stats = run_due_jobs(cfg)
    assert stats["processed"] == 1
    assert stats.get("drafted") == 1

    with db.connect(db_path) as conn:
        job = conn.execute("SELECT status FROM publish_jobs").fetchone()
        art = conn.execute("SELECT status, schedule_state FROM articles").fetchone()
        draft = conn.execute("SELECT media_id FROM wechat_drafts").fetchone()
        assert job["status"] == "done"
        assert art["status"] == "imported"
        assert art["schedule_state"] == "remote_draft_ready"
        assert draft["media_id"].startswith("mock_media_")
