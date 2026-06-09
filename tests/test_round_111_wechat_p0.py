"""Round 111：生成排期预检联动、待人工确认首页入口。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.review.proof import WAITING_CONFIRMATION, mark_job_waiting_confirmation
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.publish_preflight import build_publish_preflight
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r111.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def test_plan_gate_allows_draft_schedule_without_cover(tmp_path: Path) -> None:
    db_path = tmp_path / "r111b.sqlite3"
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
    assert pf["plan_gate"]["blocked"] is False
    client = TestClient(create_app(cfg))
    res = client.post("/api/plan").json()
    assert res.get("blocked_by_preflight") is not True


def test_publish_preflight_has_plan_gate(client: TestClient) -> None:
    pf = client.get("/api/publish-preflight").json()
    assert "plan_gate" in pf


def test_waiting_confirmation_api(client: TestClient, tmp_path: Path) -> None:
    cfg_db = tmp_path / "r111.sqlite3"
    with db.connect(cfg_db) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/w.md', '待确认篇', 'S', 'b', 'hw', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, '2026-01-01T10:00:00', 'running', 'mock')",
            (aid,),
        )
        jid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        mark_job_waiting_confirmation(conn, jid)
        conn.commit()
    wc = client.get("/api/waiting-confirmation").json()
    assert wc["count"] >= 1
    assert wc["items"][0]["article_title"] == "待确认篇"
    ov = client.get("/api/overview").json()
    assert ov.get("waiting_confirmation", {}).get("count", 0) >= 1


def test_home_plan_and_waiting_markup(client: TestClient) -> None:
    html = client.get("/").text
    assert "btnPlan" in html
    assert "生成排期" in html
    assert "planBlockReason" in html
    assert "waitingConfirmEntry" in html
    assert "goWaitingConfirmQueue" in html
    assert "待人工确认" in html
    assert "plan_gate" in html or "applyPreflightGates" in html
