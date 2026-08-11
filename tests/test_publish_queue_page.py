"""草稿队列页面增强。"""

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


def test_waiting_confirmation_never_suggests_placeholder_proof(
    app_config: AppConfig,
) -> None:
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('/proof.md', 'Proof', 'S', 'B', 'proof-hash', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, ?, 'waiting_confirmation', 'real')",
            (aid, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        jobs = list_queue_jobs(conn, app_config, status="waiting_confirmation")

    assert "公开链接或截图" in jobs[0]["next_hint"]
    assert "占位" not in jobs[0]["next_hint"]


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
    assert "btnClearFailed" in html
    assert "清除失败记录" in html
    assert "此操作不可逆" in html
    assert "不会删除文章、微信草稿或远端内容" in html
    assert "JSON.stringify({ confirmed: true })" in html
    assert "queue-table" in html
    assert "重试" in html


def test_clear_failed_jobs_requires_explicit_confirmation(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('/confirm.md', 'Confirm', 'S', 'B', 'confirm-h', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, datetime('now'), 'failed', 'mock')",
            (aid,),
        )
        conn.commit()

    for payload in ({}, {"confirmed": False}):
        response = client.post("/api/jobs/clear-failed", json=payload)
        assert response.status_code == 400
        with db.connect(app_config.database_path) as conn:
            remaining = conn.execute(
                "SELECT COUNT(*) FROM publish_jobs WHERE status = 'failed'"
            ).fetchone()[0]
        assert remaining == 1


def test_clear_failed_jobs_only_removes_failed_records(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    protected_tables = (
        "articles",
        "wechat_drafts",
        "remote_content_mirror",
        "events",
        "publish_proofs",
    )
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('/cleanup.md', 'Cleanup', 'S', 'B', 'cleanup-h', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        for status in ("failed", "pending", "done"):
            conn.execute(
                "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
                "VALUES (?, datetime('now'), ?, 'mock')",
                (aid, status),
            )
        job_rows = conn.execute(
            "SELECT id, status FROM publish_jobs ORDER BY id"
        ).fetchall()
        failed_id = next(int(row["id"]) for row in job_rows if row["status"] == "failed")
        pending_id = next(int(row["id"]) for row in job_rows if row["status"] == "pending")
        conn.execute(
            "INSERT INTO wechat_drafts (article_id, media_id, status, payload_json) "
            "VALUES (?, 'local-media', 'created', '{}')",
            (aid,),
        )
        conn.execute(
            "INSERT INTO remote_content_mirror (remote_type, media_id, article_id, title) "
            "VALUES ('draft', 'remote-media', ?, 'Remote')",
            (str(aid),),
        )
        conn.execute(
            "INSERT INTO events (entity_type, entity_id, event_type, payload_json) "
            "VALUES ('publish_job', ?, 'job_failed', 'local failure')",
            (failed_id,),
        )
        conn.execute(
            "INSERT INTO publish_proofs (publish_job_id, article_id, note) "
            "VALUES (?, ?, 'keep proof')",
            (pending_id, aid),
        )
        conn.commit()
        protected_before = {
            table: [tuple(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY id")]
            for table in protected_tables
        }
        non_failed_before = [
            tuple(row)
            for row in conn.execute(
                "SELECT * FROM publish_jobs WHERE status != 'failed' ORDER BY id"
            )
        ]

    response = client.post("/api/jobs/clear-failed", json={"confirmed": True})
    assert response.status_code == 200
    result = response.json()
    assert result["deleted"] == 1
    assert "本地失败队列" in "；".join(result["human"])
    assert "不会删除文章、微信草稿或远端内容" in "；".join(result["human"])

    with db.connect(app_config.database_path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM publish_jobs WHERE status = 'failed'"
        ).fetchone()[0] == 0
        assert [
            tuple(row)
            for row in conn.execute(
                "SELECT * FROM publish_jobs WHERE status != 'failed' ORDER BY id"
            )
        ] == non_failed_before
        assert {
            table: [tuple(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY id")]
            for table in protected_tables
        } == protected_before

    assert client.get("/api/jobs", params={"status": "failed"}).json() == []
    assert client.get("/api/queue-summary").json()["failed_count"] == 0


def test_clear_failed_jobs_rolls_back_on_database_error(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config), raise_server_exceptions=False)
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('/rollback.md', 'Rollback', 'S', 'B', 'rollback-h', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        for _ in range(2):
            conn.execute(
                "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
                "VALUES (?, datetime('now'), 'failed', 'mock')",
                (aid,),
            )
        blocked_id = int(conn.execute("SELECT MAX(id) FROM publish_jobs").fetchone()[0])
        conn.execute(
            "CREATE TRIGGER block_failed_cleanup BEFORE DELETE ON publish_jobs "
            f"WHEN OLD.id = {blocked_id} "
            "BEGIN SELECT RAISE(ABORT, 'blocked cleanup'); END",
        )
        conn.commit()

    response = client.post("/api/jobs/clear-failed", json={"confirmed": True})
    assert response.status_code == 500
    with db.connect(app_config.database_path) as conn:
        remaining = conn.execute(
            "SELECT COUNT(*) FROM publish_jobs WHERE status = 'failed'"
        ).fetchone()[0]
    assert remaining == 2
