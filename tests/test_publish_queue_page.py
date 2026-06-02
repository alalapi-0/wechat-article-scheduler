"""Round 67 / 收敛 Round 12：发布队列页面增强。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.queue_display import failure_reasons_for_jobs, list_queue_jobs
from wechat_article_scheduler.workflow import retry_failed_jobs, retry_publish_job
from tests.conftest import make_test_config


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    db_path = tmp_path / "queue.sqlite3"
    db.init_db(db_path)
    return make_test_config(tmp_path, db_path)


def test_failure_reason_from_events(app_config: AppConfig) -> None:
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('/a.md', 'A', 'S', 'B', 'h1', 'imported')",
        )
        jid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, ?, 'failed', 'mock')",
            (jid, datetime.now().isoformat(timespec="seconds")),
        )
        db.log_event(
            conn,
            entity_type="publish_job",
            entity_id=jid,
            event_type="job_failed",
            payload="演练：模拟网络错误",
        )
        conn.commit()
        reasons = failure_reasons_for_jobs(conn, [jid])
    assert reasons[jid] == "演练：模拟网络错误"


def test_list_queue_jobs_marks_due(app_config: AppConfig) -> None:
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('/b.md', 'B', 'S', 'B', 'h2', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        past = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, ?, 'pending', 'mock')",
            (aid, past),
        )
        conn.commit()
        jobs = list_queue_jobs(conn, app_config, status="pending")
    assert jobs[0]["is_due_now"] is True
    assert "到点" in jobs[0]["next_hint"]


def test_retry_publish_job_api(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('/c.md', 'C', 'S', 'B', 'h3', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, ?, 'failed', 'mock')",
            (aid, datetime.now().isoformat(timespec="seconds")),
        )
        jid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    r = client.post(f"/api/jobs/{jid}/retry")
    assert r.status_code == 200
    assert r.json()["retried"] == 1
    with db.connect(app_config.database_path) as conn:
        st = conn.execute("SELECT status FROM publish_jobs WHERE id = ?", (jid,)).fetchone()["status"]
    assert st == "pending"


def test_bulk_retry_and_queue_summary(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        for i in range(2):
            conn.execute(
                "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
                "VALUES (?, 'T', 'S', 'B', ?, 'imported')",
                (f"/{i}.md", f"h{i}"),
            )
            aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
            conn.execute(
                "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
                "VALUES (?, ?, 'failed', 'mock')",
                (aid, datetime.now().isoformat(timespec="seconds")),
            )
        conn.commit()
    assert retry_failed_jobs(app_config) == 2
    summary = client.get("/api/queue-summary").json()
    assert "counts" in summary
    jobs = client.get("/api/jobs", params={"status": "pending"}).json()
    assert len(jobs) == 2


def test_index_has_queue_retry_controls(app_config: AppConfig) -> None:
    html = TestClient(create_app(app_config)).get("/").text
    assert "btnRetryAllFailed" in html
    assert "queue-table" in html
    assert "重试" in html
