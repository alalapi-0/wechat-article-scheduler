"""Round 65 / 收敛路线图 Round 10：Web 控制台 MVP 缺口补齐。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.workbench_mvp import build_workbench_hints
from tests.conftest import make_test_config


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    db_path = tmp_path / "mvp.sqlite3"
    db.init_db(db_path)
    return make_test_config(tmp_path, db_path)


def test_workbench_hints_suggest_run_when_due() -> None:
    wb = build_workbench_hints(
        article_counts={"imported": 1},
        job_counts={"pending": 1},
        schedule_summary={"due_now_count": 2, "next_summary": "有 2 篇已到点"},
    )
    assert wb["primary_action"] == "run"
    assert "已到草稿创建时间" in wb["headline"]


def test_workbench_hints_suggest_plan_when_unscheduled(app_config: AppConfig) -> None:
    wb = build_workbench_hints(
        article_counts={"imported": 3},
        job_counts={},
        schedule_summary={"due_now_count": 0, "next_summary": "暂无"},
        chain_summary={
            "recommended_next_action": "plan",
            "imported_without_pending_job": 3,
        },
    )
    assert wb["primary_action"] == "plan"
    assert "待安排" in wb["headline"] or "待生成" in wb["headline"]


def test_overview_includes_workbench(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    data = client.get("/api/overview").json()
    assert "workbench" in data
    assert data["workbench"]["headline"]
    assert "wechat_chain_summary" in data
    assert data["workbench"].get("chain_recommended_action") == "scan"
    assert "scan" in (data["workbench"].get("recommended_cli") or "")


def test_index_mvp_controls(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    html = client.get("/").text
    assert "扫描本地收件箱" in html
    assert "nextSteps" in html
    assert "safety-dashboard" in html
    assert "dashboardPrimaryAction" in html
    assert "安全状态与下一步" in html
    assert "queueFilters" in html
    assert "显示高级信息" in html
    assert "草稿队列" in html


def test_jobs_api_status_filter(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('/a.md', 'A', 'S', 'B', 'h1', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        when = (datetime.now() + timedelta(days=1)).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, ?, 'pending', 'mock')",
            (aid, when),
        )
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, ?, 'done', 'mock')",
            (aid, when),
        )
        conn.commit()
    pending = client.get("/api/jobs", params={"status": "pending"}).json()
    assert len(pending) == 1
    assert pending[0]["status"] == "pending"


def test_scan_endpoint_human(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    r = client.post("/api/scan")
    assert r.status_code == 200
    assert "human" in r.json()
