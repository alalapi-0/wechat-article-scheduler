"""Round 113：待人工确认 Tab 快速 proof 与详情跳转。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.review.proof import mark_job_waiting_confirmation
from wechat_article_scheduler.review.proof_quick import build_quick_proof_input, quick_proof_allowed
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r113.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def _seed_waiting(tmp_path: Path) -> tuple[TestClient, int, int]:
    cfg = make_test_config(tmp_path, tmp_path / "r113.sqlite3")
    db.init_db(cfg.database_path)
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/w.md', '待确认', 'S', 'b', 'hw', 'imported')",
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
    return TestClient(create_app(cfg)), aid, jid


def test_quick_proof_allowed_mock(tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "r113.sqlite3")
    assert quick_proof_allowed(cfg) is True
    proof = build_quick_proof_input(cfg, 1)
    assert "mock.local" in (proof.public_url or "")
    assert proof.screenshot_path


def test_quick_proof_api(client: TestClient, tmp_path: Path) -> None:
    c, _aid, jid = _seed_waiting(tmp_path)
    r = c.post(f"/api/publish-jobs/{jid}/proof", json={"quick_dry_run": True}).json()
    assert r.get("ok") is True
    assert r.get("dry_run_proof") is True
    assert c.get(f"/api/publish-jobs/{jid}/proof").json().get("proof")


def test_waiting_confirmation_api_enriched(client: TestClient, tmp_path: Path) -> None:
    c, _aid, jid = _seed_waiting(tmp_path)
    wc = c.get("/api/waiting-confirmation").json()
    assert wc["count"] >= 1
    item = wc["items"][0]
    assert item["proof_form_url"].endswith("#proof")
    assert "quick_proof_available" in item
    assert wc.get("generation_policy", {}).get("badge") in ("AUTO_APPROVE", "MANUAL_REVIEW")


def test_bulk_quick_proof(client: TestClient, tmp_path: Path) -> None:
    c, _aid, jid = _seed_waiting(tmp_path)
    r = c.post("/api/waiting-confirmation/quick-proof-all").json()
    assert r.get("ok") is True
    assert r.get("completed", 0) >= 1


def test_home_proof_queue_markup(client: TestClient) -> None:
    html = client.get("/").text
    assert "quickProofJob" in html
    assert "bulkQuickProofWaiting" in html
    assert "queue-confirm-banner" in html
    assert "填写证明" in html
