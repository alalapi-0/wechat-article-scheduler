"""Round 39+ Web 能力：审核闸门、定时发布 UX、真实发布预检。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.schedule_display import format_scheduled_at, summarize_schedule
from tests.conftest import make_test_config


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    db_path = tmp_path / "r39.sqlite3"
    db.init_db(db_path)
    return make_test_config(tmp_path, db_path)


@pytest.fixture
def client(app_config: AppConfig) -> TestClient:
    return TestClient(create_app(app_config))


def _seed_article(conn, *, review_status: str = "draft") -> int:
    conn.execute(
        """
        INSERT INTO articles (source_path, title, summary, body, content_hash, status, review_status)
        VALUES ('a.md', '测试文', '摘要', 'body', 'hash-r39', 'imported', ?)
        """,
        (review_status,),
    )
    conn.commit()
    return int(conn.execute("SELECT id FROM articles").fetchone()[0])


def test_review_endpoint_approves_article(client: TestClient, app_config: AppConfig) -> None:
    with db.connect(app_config.database_path) as conn:
        aid = _seed_article(conn)
    r = client.post(f"/api/articles/{aid}/review", json={"status": "approved"})
    assert r.status_code == 200
    data = r.json()
    assert data["review_status"] == "approved"
    assert data["review_status_label"] == "已通过"
    assert data["human"]


def test_overview_includes_pending_review(client: TestClient, app_config: AppConfig) -> None:
    with db.connect(app_config.database_path) as conn:
        _seed_article(conn, review_status="pending_review")
    data = client.get("/api/overview").json()
    assert len(data["pending_review"]) == 1
    assert data["pending_review"][0]["review_status_label"] == "待审核"


def test_schedule_summary_human_labels(client: TestClient, app_config: AppConfig) -> None:
    future = (datetime.now() + timedelta(days=1)).isoformat(timespec="seconds")
    with db.connect(app_config.database_path) as conn:
        aid = _seed_article(conn)
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
            VALUES (?, ?, 'pending', 'mock')
            """,
            (aid, future),
        )
        conn.commit()
    data = client.get("/api/schedule-summary").json()
    assert data["pending_count"] == 1
    assert "下一篇" in data["next_summary"]
    assert data["upcoming"][0]["scheduled_at_label"]


def test_publish_preflight_mock_mode(client: TestClient) -> None:
    data = client.get("/api/publish-preflight").json()
    assert data["mode"] == "mock"
    assert data["ready"] is True
    assert any("演练" in line for line in data["human"])


def test_format_scheduled_at():
    iso = "2026-05-31T14:30:00"
    assert "2026年05月31日" in format_scheduled_at(iso)


def test_summarize_schedule_due_now(app_config: AppConfig) -> None:
    past = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    with db.connect(app_config.database_path) as conn:
        aid = _seed_article(conn)
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
            VALUES (?, ?, 'pending', 'mock')
            """,
            (aid, past),
        )
        conn.commit()
        summary = summarize_schedule(conn)
    assert summary["due_now_count"] == 1
    assert "已到发布时间" in summary["next_summary"]
