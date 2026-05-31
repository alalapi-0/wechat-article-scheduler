"""调度器 dry-run 与重试上限测试（Round 7）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.base import DraftResult
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.scheduler import run_due_jobs
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


def test_run_due_jobs_has_no_approval_gate(sched_config: AppConfig) -> None:
    """产品重定位后不再有审核闸门：统计中不应出现 skipped_not_approved。"""
    sched_config.dry_run = False
    stats = run_due_jobs(sched_config)
    assert "skipped_not_approved" not in stats
    # mock 模式下到点任务直接处理
    assert stats["processed"] == 1


def test_max_retries_skips_job(sched_config: AppConfig) -> None:
    sched_config.dry_run = False
    with db.connect(sched_config.database_path) as conn:
        conn.execute("UPDATE publish_jobs SET retry_count = 3 WHERE id = 1")
        conn.commit()
    stats = run_due_jobs(sched_config)
    assert stats["skipped_max_retries"] == 1
    assert stats["processed"] == 0


def test_real_draft_only_keeps_article_unpublished(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = tmp_path / "articles" / "imported" / "real.md"
    src.parent.mkdir(parents=True)
    src.write_text("# T\n\nbody", encoding="utf-8")
    db_path = tmp_path / "draft.sqlite3"
    db.init_db(db_path)
    past = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES (?, 'T', 'S', '# T\n\nbody', 'hash-draft', 'imported')
            """,
            (str(src),),
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, retry_count)
            VALUES (?, ?, 'pending', 'real', 0)
            """,
            (aid, past),
        )
        conn.commit()

    class FakeAdapter:
        def create_draft(self, **kwargs):  # noqa: ANN001, ANN201
            return DraftResult(media_id="draft-real-1", raw_response={"media_id": "draft-real-1"})

        def submit_publish(self, media_id: str) -> dict:
            return {"errcode": 0, "skipped": True, "media_id": media_id}

    monkeypatch.setattr(
        "wechat_article_scheduler.scheduler.domain.get_adapter",
        lambda config: FakeAdapter(),  # noqa: ARG005
    )
    cfg = make_test_config(
        tmp_path,
        db_path,
        wechat_mode="real",
        wechat_enable_publish=False,
        dry_run=False,
    )
    stats = run_due_jobs(cfg)
    assert stats["processed"] == 1
    assert stats["drafted"] == 1
    assert src.exists()
    with db.connect(db_path) as conn:
        article = conn.execute("SELECT status, source_path FROM articles WHERE id = ?", (aid,)).fetchone()
        job = conn.execute("SELECT status FROM publish_jobs WHERE article_id = ?", (aid,)).fetchone()
        drafts = conn.execute("SELECT COUNT(*) AS cnt FROM wechat_drafts WHERE article_id = ?", (aid,)).fetchone()
        event = conn.execute("SELECT event_type FROM events ORDER BY id DESC LIMIT 1").fetchone()
    assert article["status"] == "imported"
    assert article["source_path"] == str(src)
    assert job["status"] == "done"
    assert drafts["cnt"] == 1
    assert event["event_type"] == "draft_created"
