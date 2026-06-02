"""Round 39+ Web 能力：发布前确认、定时发布 UX、真实发布预检（已去审核）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.app import _web_auto_runner_state
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


def _seed_article(conn) -> int:
    conn.execute(
        """
        INSERT INTO articles (source_path, title, summary, body, content_hash, status)
        VALUES ('a.md', '测试文', '摘要', 'body', 'hash-r39', 'imported')
        """
    )
    conn.commit()
    return int(conn.execute("SELECT id FROM articles").fetchone()[0])


def test_overview_has_no_review_section(client: TestClient, app_config: AppConfig) -> None:
    """产品重定位后概览不再有审核区块。"""
    with db.connect(app_config.database_path) as conn:
        _seed_article(conn)
    data = client.get("/api/overview").json()
    assert "pending_review" not in data
    assert "publish_preflight" in data


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


def test_articles_include_content_hints(client: TestClient, app_config: AppConfig) -> None:
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('a.md', '标题', '', '', 'h-empty', 'imported')
            """
        )
        conn.commit()
    arts = client.get("/api/articles").json()
    assert any("正文为空" in (a.get("content_hints") or []) for a in arts)


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


def test_web_auto_runner_enabled_with_auto_execute_job(tmp_path: Path) -> None:
    from wechat_article_scheduler import db

    db_path = tmp_path / "auto.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(
        tmp_path,
        db_path,
        web_auto_run_due=True,
        web_auto_publish=True,
        wechat_mode="real",
        wechat_enable_publish=False,
    )
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('a.md', 't', 's', 'b', 'h3', 'imported')
            """
        )
        aid = int(conn.execute("SELECT id FROM articles").fetchone()[0])
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, publish_config_json)
            VALUES (?, '2099-01-01T10:00:00', 'pending', 'real', ?)
            """,
            (
                aid,
                '{"publish_action":"draft","auto_execute":true,"need_open_comment":false,'
                '"only_fans_can_comment":false,"author":"","content_source_url":""}',
            ),
        )
        conn.commit()
    enabled, reason = _web_auto_runner_state(cfg)
    assert enabled is True
    assert "到点自动执行" in reason


def test_web_auto_runner_blocks_when_auto_publish_off(tmp_path: Path) -> None:
    from wechat_article_scheduler import db

    db_path = tmp_path / "auto.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(
        tmp_path,
        db_path,
        web_auto_run_due=True,
        web_auto_publish=False,
        wechat_mode="real",
        wechat_enable_publish=True,
    )
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('a.md', 't', 's', 'b', 'h1', 'imported')
            """
        )
        aid = int(conn.execute("SELECT id FROM articles").fetchone()[0])
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, publish_config_json)
            VALUES (?, '2099-01-01T10:00:00', 'pending', 'real', ?)
            """,
            (
                aid,
                '{"publish_action":"publish","auto_execute":true,"need_open_comment":false,'
                '"only_fans_can_comment":false,"author":"","content_source_url":""}',
            ),
        )
        conn.commit()
    enabled, reason = _web_auto_runner_state(cfg)
    assert enabled is False
    assert "WEB_AUTO_PUBLISH=false" in reason


def test_web_auto_runner_with_auto_execute_job(tmp_path: Path) -> None:
    from wechat_article_scheduler import db

    db_path = tmp_path / "auto2.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(
        tmp_path,
        db_path,
        web_auto_run_due=True,
        web_auto_publish=True,
        wechat_mode="real",
        wechat_enable_publish=True,
    )
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('a.md', 't', 's', 'b', 'h2', 'imported')
            """
        )
        aid = int(conn.execute("SELECT id FROM articles").fetchone()[0])
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, publish_config_json)
            VALUES (?, '2099-01-01T10:00:00', 'pending', 'real', ?)
            """,
            (
                aid,
                '{"publish_action":"publish","auto_execute":true,"need_open_comment":false,'
                '"only_fans_can_comment":false,"author":"","content_source_url":""}',
            ),
        )
        conn.commit()
    enabled, reason = _web_auto_runner_state(cfg)
    assert enabled is True
    assert "到点自动执行" in reason


def test_web_auto_runner_follows_pending_jobs(app_config: AppConfig) -> None:
    app_config.web_auto_run_due = True
    app_config.wechat_mode = "mock"
    app_config.scheduler_poll_seconds = 60
    with TestClient(create_app(app_config)) as c:
        status = c.get("/api/status").json()
        assert status["web_auto_runner_active"] is False
        assert "暂无到点自动执行任务" in status["web_auto_runner_reason"]

        with db.connect(app_config.database_path) as conn:
            aid = _seed_article(conn)
        future = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
        scheduled = c.post(
            f"/api/articles/{aid}/schedule",
            json={
                "scheduled_at": future,
                "publish_action": "draft",
                "auto_execute": True,
            },
        )
        assert scheduled.status_code == 200
        status = c.get("/api/status").json()
        assert status["web_auto_runner_active"] is True

        trashed = c.post(f"/api/articles/{aid}/trash")
        assert trashed.status_code == 200
        status = c.get("/api/status").json()
        assert status["web_auto_runner_active"] is False
        assert "暂无到点自动执行任务" in status["web_auto_runner_reason"]
