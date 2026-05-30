"""调度器 dry-run 与重试上限测试（Round 7）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.scheduler import run_due_jobs
from wechat_article_scheduler.scheduler.runtime import requires_publish_approval
from tests.conftest import make_test_config


@pytest.fixture
def sched_config(tmp_path: Path) -> AppConfig:
    db_path = tmp_path / "sched.sqlite3"
    db.init_db(db_path)
    past = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('a.md', 'T', 'S', 'body', 'hash1', 'planned')
            """
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, retry_count)
            VALUES (?, ?, 'pending', 'mock', 0)
            """,
            (aid, past),
        )
        conn.commit()
    return make_test_config(tmp_path, db_path, dry_run=True)


def test_dry_run_does_not_publish(sched_config: AppConfig) -> None:
    stats = run_due_jobs(sched_config)
    assert stats["dry_run"] == 1
    assert stats["processed"] == 0
    report_dir = sched_config.root / "data" / "reports"
    assert report_dir.exists()
    assert list(report_dir.glob("dry_run_*.json"))


def test_real_publish_skips_unapproved_article(tmp_path: Path) -> None:
    db_path = tmp_path / "gate.sqlite3"
    db.init_db(db_path)
    past = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status, review_status)
            VALUES ('a.md', 'T', 'S', 'body', 'hash-gate', 'planned', 'draft')
            """
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, retry_count)
            VALUES (?, ?, 'pending', 'real', 0)
            """,
            (aid, past),
        )
        conn.commit()
    cfg = make_test_config(tmp_path, db_path, dry_run=False)
    cfg.wechat_mode = "real"
    cfg.wechat_enable_publish = True
    stats = run_due_jobs(cfg)
    assert stats["skipped_not_approved"] == 1
    assert stats["processed"] == 0
    assert requires_publish_approval(cfg) is True


def test_max_retries_skips_job(sched_config: AppConfig) -> None:
    sched_config.dry_run = False
    with db.connect(sched_config.database_path) as conn:
        conn.execute("UPDATE publish_jobs SET retry_count = 3 WHERE id = 1")
        conn.commit()
    stats = run_due_jobs(sched_config)
    assert stats["skipped_max_retries"] == 1
    assert stats["processed"] == 0
