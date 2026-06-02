"""Round 108：微信 P0 主线 — overview 预检联动、status AUTO_APPROVE、队列摘要。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.generation_policy import build_generation_policy_status
from wechat_article_scheduler.web.workbench_mvp import build_workbench_hints
from tests.conftest import make_test_config


def test_generation_policy_badge_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTO_APPROVE_GENERATIONS", raising=False)
    monkeypatch.setenv("REVIEW_MODE", "auto")
    gp = build_generation_policy_status()
    assert gp["auto_approve_generations"] is True
    assert gp["badge"] == "AUTO_APPROVE"


def test_workbench_preflight_blocks_run() -> None:
    wb = build_workbench_hints(
        article_counts={"imported": 1},
        job_counts={"pending": 2},
        schedule_summary={"due_now_count": 1},
        publish_preflight={
            "ready": False,
            "checks": [
                {
                    "id": "cover",
                    "ok": False,
                    "required": True,
                    "label": "封面",
                    "detail": "缺少封面",
                }
            ],
        },
    )
    assert wb["primary_action"] == "preflight"
    assert wb["preflight_ready"] is False


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r108.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def test_status_includes_generation_policy(client: TestClient) -> None:
    data = client.get("/api/status").json()
    assert "generation_policy" in data
    assert data["generation_policy"]["badge"] in ("AUTO_APPROVE", "MANUAL_REVIEW")


def test_overview_preflight_and_workbench(client: TestClient, tmp_path: Path) -> None:
    cfg_db = tmp_path / "r108.sqlite3"
    with db.connect(cfg_db) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/x.md', 'T', 'S', 'body', 'h', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        when = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, ?, 'pending', 'mock')",
            (aid, when),
        )
        conn.commit()
    ov = client.get("/api/overview").json()
    assert "preflight_ready" in ov
    assert "generation_policy" in ov
    assert ov["workbench"].get("preflight_ready") is not None


def test_queue_summary_preflight_flag(client: TestClient) -> None:
    q = client.get("/api/queue-summary").json()
    assert "preflight_ready" in q
    assert "summary_label" in q


def test_home_shell_and_status_auto_approve(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUTO_APPROVE_GENERATIONS", "true")
    assert "nextSteps" in client.get("/").text
    assert client.get("/api/status").json()["generation_policy"]["badge"] == "AUTO_APPROVE"
