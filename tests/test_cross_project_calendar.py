"""Phase5 跨项目发布日历 dry-run 与冲突检测。"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.core.cross_project_calendar import (
    build_publish_calendar_dry_run,
    detect_calendar_conflicts,
    parse_scheduled_at,
)
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "config" / "projects.example.yaml"


def test_parse_scheduled_at_offset():
    dt = parse_scheduled_at("2026-06-02T20:00:00+08:00")
    assert dt is not None
    assert dt.hour == 20


def test_publish_calendar_dry_run_example_projects():
    summary = build_publish_calendar_dry_run(ROOT, projects_path=PROJECTS)
    assert summary["ok"] is True
    assert summary["event_count"] >= 3
    assert summary["calendar_view"]["day_count"] >= 1
    assert summary["conflict_count"] == 0


def test_detect_same_slot_same_account():
    t = "2026-06-02T20:00:00+08:00"
    events = [
        {
            "project_id": "a",
            "package_id": "p1",
            "title": "T1",
            "platform_account_id": "wechat_mp_main",
            "adapter_type": "official_api",
            "scheduled_at": t,
            "calendar_day": "2026-06-02",
        },
        {
            "project_id": "b",
            "package_id": "p2",
            "title": "T2",
            "platform_account_id": "wechat_mp_main",
            "adapter_type": "manual_export",
            "scheduled_at": t,
            "calendar_day": "2026-06-02",
        },
    ]
    conflicts = detect_calendar_conflicts(events, min_gap_minutes=60)
    assert any(c["type"] == "same_slot_same_account" for c in conflicts)


def test_api_publish_calendar_dry_run(tmp_path: Path) -> None:
    db_path = tmp_path / "cal.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    client = TestClient(create_app(cfg))
    r = client.get("/api/publish-calendar/dry-run")
    assert r.status_code == 200
    data = r.json()
    assert data["phase"] == "phase5_cross_project_calendar"
    assert "calendar_view" in data
