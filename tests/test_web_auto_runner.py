"""Web 到点自动创建草稿的启停条件。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import make_test_config
from wechat_article_scheduler import db
from wechat_article_scheduler.publish_config import PublishConfig, publish_config_to_json
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.app import _web_auto_runner_state
from wechat_article_scheduler.web.schedule_display import format_scheduled_at, summarize_schedule


def _seed_auto_job(config, *, auto_execute: bool = True) -> int:
    with db.connect(config.database_path) as conn:
        article_id = int(
            conn.execute(
                "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
                "VALUES ('a.md', '测试文', '摘要', '正文', 'auto-hash', 'imported')"
            ).lastrowid
        )
        conn.execute(
            "INSERT INTO publish_jobs "
            "(article_id, scheduled_at, status, adapter_mode, publish_config_json) "
            "VALUES (?, '2099-01-01T10:00:00', 'pending', 'mock', ?)",
            (article_id, publish_config_to_json(PublishConfig(auto_execute=auto_execute))),
        )
        conn.commit()
    return article_id


def test_auto_runner_requires_enabled_flag_and_opted_in_job(tmp_path: Path) -> None:
    db_path = tmp_path / "runner.sqlite3"
    db.init_db(db_path)
    disabled = make_test_config(tmp_path, db_path, web_auto_run_due=False)
    _seed_auto_job(disabled)
    assert _web_auto_runner_state(disabled) == (False, "WEB_AUTO_RUN_DUE=false")

    disabled.web_auto_run_due = True
    enabled, reason = _web_auto_runner_state(disabled)
    assert enabled is True
    assert "到点自动执行" in reason


def test_auto_runner_ignores_jobs_without_auto_execute(tmp_path: Path) -> None:
    db_path = tmp_path / "manual.sqlite3"
    db.init_db(db_path)
    config = make_test_config(tmp_path, db_path, web_auto_run_due=True)
    _seed_auto_job(config, auto_execute=False)
    assert _web_auto_runner_state(config) == (False, "暂无到点自动执行任务")


def test_auto_runner_follows_trash_state(tmp_path: Path) -> None:
    db_path = tmp_path / "lifecycle.sqlite3"
    db.init_db(db_path)
    config = make_test_config(
        tmp_path,
        db_path,
        web_auto_run_due=True,
        scheduler_poll_seconds=60,
    )
    article_id = _seed_auto_job(config)
    with TestClient(create_app(config)) as client:
        assert client.get("/api/status").json()["web_auto_runner_active"] is True
        assert client.post(f"/api/articles/{article_id}/trash").status_code == 200
        status = client.get("/api/status").json()
        assert status["web_auto_runner_active"] is False
        assert "暂无到点自动执行任务" in status["web_auto_runner_reason"]


def test_schedule_display_marks_due_jobs(tmp_path: Path) -> None:
    db_path = tmp_path / "schedule.sqlite3"
    db.init_db(db_path)
    config = make_test_config(tmp_path, db_path)
    article_id = _seed_auto_job(config)
    due = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    with db.connect(db_path) as conn:
        conn.execute(
            "UPDATE publish_jobs SET scheduled_at = ? WHERE article_id = ?",
            (due, article_id),
        )
        conn.commit()
        summary = summarize_schedule(conn)
    assert summary["due_now_count"] == 1
    assert "已到草稿创建时间" in summary["next_summary"]
    assert "2026年05月31日" in format_scheduled_at("2026-05-31T14:30:00")
