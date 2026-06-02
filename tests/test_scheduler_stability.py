"""Round 69 / 收敛 Round 14：本地 scheduler 稳定化。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.scheduler import run_due_jobs
from wechat_article_scheduler.scheduler.claim import (
    acquire_run_lock,
    new_claim_token,
    recover_stale_running_jobs,
    release_run_lock,
    try_claim_job,
)
from wechat_article_scheduler.scheduler.health import build_scheduler_health
from tests.conftest import make_test_config


@pytest.fixture
def sched_db(tmp_path: Path) -> tuple[AppConfig, int]:
    db_path = tmp_path / "stab.sqlite3"
    db.init_db(db_path)
    past = (datetime.now() - timedelta(hours=2)).isoformat(timespec="seconds")
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('a.md', 'T', 'S', 'body', 'h1', 'imported')
            """
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, retry_count)
            VALUES (?, ?, 'pending', 'mock', 0)
            """,
            (aid, past),
        )
        jid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    cfg = make_test_config(tmp_path, db_path, scheduler_claim_timeout_seconds=60)
    return cfg, jid


def test_try_claim_is_atomic(sched_db: tuple[AppConfig, int]) -> None:
    cfg, jid = sched_db
    with db.connect(cfg.database_path) as conn:
        t1 = new_claim_token()
        assert try_claim_job(conn, jid, t1) is True
        t2 = new_claim_token()
        assert try_claim_job(conn, jid, t2) is False
        conn.commit()


def test_recover_stale_running(sched_db: tuple[AppConfig, int]) -> None:
    cfg, jid = sched_db
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            UPDATE publish_jobs
            SET status = 'running',
                updated_at = datetime('now', '-2 hours')
            WHERE id = ?
            """,
            (jid,),
        )
        conn.commit()
        n = recover_stale_running_jobs(conn, cfg)
        conn.commit()
        st = conn.execute("SELECT status FROM publish_jobs WHERE id = ?", (jid,)).fetchone()["status"]
        ev = conn.execute(
            "SELECT event_type FROM events WHERE entity_id = ? ORDER BY id DESC LIMIT 1",
            (jid,),
        ).fetchone()["event_type"]
    assert n == 1
    assert st == "pending"
    assert ev == "job_stale_recovered"


def test_run_lock_blocks_second_holder(sched_db: tuple[AppConfig, int]) -> None:
    cfg, _jid = sched_db
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            INSERT INTO scheduler_locks (lock_name, owner, expires_at)
            VALUES ('run_once', 'other-worker', datetime('now', '+10 minutes'))
            """
        )
        conn.commit()
    stats = run_due_jobs(cfg)
    assert stats["skipped_locked"] == 1
    assert stats["processed"] == 0


def test_failure_schedules_backoff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "backoff.sqlite3"
    db.init_db(db_path)
    past = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('b.md', 'B', 'S', 'body', 'hb', 'imported')
            """
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, retry_count)
            VALUES (?, ?, 'pending', 'mock', 0)
            """,
            (aid, past),
        )
        jid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()

    class BoomAdapter:
        def create_draft(self, **kwargs):  # noqa: ANN003, ANN201
            raise RuntimeError("演练失败")

        def submit_publish(self, media_id: str, *, force: bool = False) -> dict:
            return {"skipped": True}

    monkeypatch.setattr(
        "wechat_article_scheduler.scheduler.domain.get_adapter",
        lambda config: BoomAdapter(),  # noqa: ARG005
    )
    cfg = make_test_config(tmp_path, db_path, max_job_retries=3)
    stats = run_due_jobs(cfg)
    assert stats["retry_scheduled"] == 1
    with db.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, retry_count, next_retry_at FROM publish_jobs WHERE id = ?",
            (jid,),
        ).fetchone()
        ev = conn.execute(
            "SELECT event_type FROM events WHERE entity_id = ? ORDER BY id DESC LIMIT 1",
            (jid,),
        ).fetchone()["event_type"]
    assert row["status"] == "pending"
    assert int(row["retry_count"]) == 1
    assert row["next_retry_at"]
    assert ev == "job_retry_scheduled"


def test_scheduler_health_reports_counts(sched_db: tuple[AppConfig, int]) -> None:
    cfg, _jid = sched_db
    health = build_scheduler_health(cfg)
    assert "counts" in health
    assert health["counts"]["pending"] >= 1
    assert "summary" in health


def test_misfire_event_logged(sched_db: tuple[AppConfig, int]) -> None:
    cfg, jid = sched_db
    cfg = make_test_config(
        cfg.root,
        cfg.database_path,
        scheduler_misfire_grace_minutes=0,
    )
    old = (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
    with db.connect(cfg.database_path) as conn:
        conn.execute("UPDATE publish_jobs SET scheduled_at = ? WHERE id = ?", (old, jid))
        conn.commit()
    stats = run_due_jobs(cfg)
    assert stats.get("misfired", 0) >= 1
    with db.connect(cfg.database_path) as conn:
        ev = conn.execute(
            "SELECT 1 FROM events WHERE entity_id = ? AND event_type = 'job_misfire'",
            (jid,),
        ).fetchone()
    assert ev is not None


def test_acquire_and_release_lock(sched_db: tuple[AppConfig, int]) -> None:
    cfg, _ = sched_db
    with db.connect(cfg.database_path) as conn:
        ok, holder = acquire_run_lock(conn, cfg)
        assert ok is True
        assert holder is None
        ok2, holder2 = acquire_run_lock(conn, cfg)
        assert ok2 is True
        release_run_lock(conn, cfg)
        conn.commit()
