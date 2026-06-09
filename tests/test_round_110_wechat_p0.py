"""Round 110：执行到点与预检 blocking 联动、run-once 结果反馈。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.publish_preflight import build_publish_preflight
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r110.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def test_run_once_gate_allows_real_draft_creation_without_cover(tmp_path: Path) -> None:
    db_path = tmp_path / "r110b.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    cfg.wechat_mode = "real"
    cfg.wechat_enable_publish = True
    cfg.wechat_default_thumb_path = ""
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status, cover_path) "
            "VALUES ('inbox/x.md', '无封面', 'S', '正文', 'h', 'imported', '')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        when = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, ?, 'pending', 'mock')",
            (aid, when),
        )
        conn.commit()
        pf = build_publish_preflight(cfg, conn)
    assert pf["run_once_gate"]["blocked"] is False
    assert pf["ready"] is True
    client = TestClient(create_app(cfg))
    res = client.post("/api/run-once").json()
    assert res.get("blocked_by_preflight") is not True


def test_publish_preflight_has_run_once_gate(client: TestClient) -> None:
    pf = client.get("/api/publish-preflight").json()
    assert "run_once_gate" in pf
    assert "blocked" in pf["run_once_gate"]


def test_home_run_once_gate_markup(client: TestClient) -> None:
    html = client.get("/").text
    assert "runOnceBlockReason" in html
    assert "applyRunOncePreflightGate" in html or "run_once_gate" in html
    assert "showRunOnceOutcome" in html


def test_run_once_returns_human_and_overview_events(client: TestClient, tmp_path: Path) -> None:
    cfg_db = tmp_path / "r110.sqlite3"
    with db.connect(cfg_db) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status, cover_path) "
            "VALUES ('inbox/d.md', '到点', 'S', '正文内容', 'h3', 'imported', 'covers/x.jpg')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        when = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, ?, 'pending', 'mock')",
            (aid, when),
        )
        conn.commit()
    before = len(client.get("/api/overview").json().get("recent_events") or [])
    res = client.post("/api/run-once").json()
    assert res.get("human")
    after = client.get("/api/overview").json()
    assert len(after.get("recent_events") or []) >= before
