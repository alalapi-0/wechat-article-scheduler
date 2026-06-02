"""Round 118：发布队列 Tab 筛选 localStorage 持久化。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r118.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def test_home_queue_filter_storage_markup(client: TestClient) -> None:
    html = client.get("/").text
    assert "wechat_workbench_queue_filter" in html
    assert "initQueueFilter" in html
    assert "persistQueueFilter" in html
    assert 'id="queueFilters"' in html
    assert 'data-qf="err"' in html
    assert "失败" in html


def test_jobs_api_status_filter(client: TestClient, tmp_path: Path) -> None:
    db_path = tmp_path / "r118.sqlite3"
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/a.md', '队列测', 'S', 'B', 'h1', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, datetime('now'), 'failed', 'mock')",
            (aid,),
        )
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, datetime('now'), 'pending', 'mock')",
            (aid,),
        )
        conn.commit()
    failed = client.get("/api/jobs", params={"status": "failed"}).json()
    pending = client.get("/api/jobs", params={"status": "pending"}).json()
    assert len(failed) >= 1
    assert all(j.get("status") == "failed" for j in failed)
    assert len(pending) >= 1
    assert all(j.get("status") == "pending" for j in pending)
