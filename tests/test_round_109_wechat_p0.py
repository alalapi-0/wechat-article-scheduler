"""Round 109：作品预检条、队列失败 Tab 重试与错误摘要。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.article_preflight import build_article_preflight_summary
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r109.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def test_article_preflight_summary_blocking(tmp_path: Path) -> None:
    row = {"title": "T", "summary": "", "body": "", "cover_path": ""}
    db_path = tmp_path / "pf.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    cfg.wechat_mode = "real"
    cfg.wechat_enable_publish = True
    summary = build_article_preflight_summary(row, cfg)
    assert summary["ready"] is False
    assert summary["bar_level"] == "err"
    assert summary["blocking_count"] >= 1


def test_articles_api_includes_preflight_bar(client: TestClient, tmp_path: Path) -> None:
    cfg_db = tmp_path / "r109.sqlite3"
    with db.connect(cfg_db) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/x.md', '预检条', 'S', '正文', 'h', 'imported')",
        )
        conn.commit()
    arts = client.get("/api/articles").json()
    assert len(arts) >= 1
    bar = arts[0].get("preflight_bar") or {}
    assert "bar_level" in bar
    assert "bar_text" in bar


def test_queue_summary_failed_preview(client: TestClient, tmp_path: Path) -> None:
    cfg_db = tmp_path / "r109.sqlite3"
    with db.connect(cfg_db) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/f.md', '失败篇', 'S', 'b', 'h2', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, '2026-01-01T10:00:00', 'failed', 'mock')",
            (aid,),
        )
        jid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            "INSERT INTO events (entity_type, entity_id, event_type, payload_json) "
            "VALUES ('publish_job', ?, 'job_failed', ?)",
            (jid, "模拟网络超时"),
        )
        conn.commit()
    q = client.get("/api/queue-summary").json()
    assert q.get("failed_count", 0) >= 1
    assert len(q.get("failed_preview") or []) >= 1
    assert "失败篇" in (q.get("failure_digest") or q.get("summary_label") or "")


def test_article_detail_preflight_bar(client: TestClient, tmp_path: Path) -> None:
    cfg_db = tmp_path / "r109.sqlite3"
    with db.connect(cfg_db) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/d.md', '详情', 'S', '正文', 'h3', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    d = client.get(f"/api/articles/{aid}").json()
    assert d.get("preflight_bar", {}).get("bar_text")
    assert "preflightBar" in client.get(f"/articles/{aid}").text


def test_home_has_queue_retry_and_preflight(client: TestClient) -> None:
    html = client.get("/").text
    assert "btnRetryAllFailed" in html
    assert "preflight-bar" in html
    assert "queue-fail-banner" in html
