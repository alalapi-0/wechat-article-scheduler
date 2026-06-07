"""browser_assist 手动登录门控会话。"""

from __future__ import annotations

import json
from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.browser_assist.session import (
    confirm_browser_login,
    confirm_final_schedule,
    confirm_schedule_setup,
    get_browser_assist_session,
    start_browser_assist_session,
)
from tests.conftest import make_test_config


def _seed_job(tmp_path: Path) -> tuple[object, int]:
    cfg = make_test_config(
        tmp_path,
        tmp_path / "ba.sqlite3",
        external_agent_task_outbox=tmp_path / "outbox" / "wechat_agent_tasks",
    )
    db.init_db(cfg.database_path)
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('a.md', '门控测试', '摘要', '正文', 'hash-ba', 'imported')
            """
        )
        article_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
            VALUES (?, '2026-06-08T10:00:00', 'pending', 'mock')
            """,
            (article_id,),
        )
        job_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            """
            INSERT INTO wechat_drafts (article_id, media_id, status, payload_json)
            VALUES (?, 'mock_media_ba', 'created', '{}')
            """,
            (article_id,),
        )
        conn.commit()
    return cfg, job_id


def test_start_session_blocks_on_login_gate(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        result = start_browser_assist_session(cfg, conn, job_id, export_task_package=False)

    assert result["ok"]
    assert result["status"] == "awaiting_browser_login"
    assert result["blocked"] is True
    assert "扫码登录" in result["prompt_zh"]
    assert result["login_gate"]["mcp_server"] == "wechat-chrome-session"
    assert result["dry_run_plan"]["login_gate_required"] is True


def test_confirm_login_then_schedule_flow(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        started = start_browser_assist_session(cfg, conn, job_id, export_task_package=False)
        session_id = started["session_id"]
        login = confirm_browser_login(cfg, conn, session_id)
        assert login["ok"]
        assert login["status"] == "assist_in_progress"

        sched = confirm_schedule_setup(cfg, conn, session_id)
        assert sched["ok"]
        assert sched["status"] == "awaiting_final_schedule_confirm"

        final = confirm_final_schedule(cfg, conn, session_id)
        assert final["ok"]
        assert final["status"] == "awaiting_proof"

        view = get_browser_assist_session(cfg, session_id)
        assert view["ok"]
        assert view["status"] == "awaiting_proof"


def test_session_persisted_to_storage(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        result = start_browser_assist_session(cfg, conn, job_id, export_task_package=False)
    session_file = cfg.root / "storage" / "browser_assist_sessions" / f"{result['session_id']}.json"
    assert session_file.is_file()
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    assert payload["job_id"] == job_id
    assert payload["status"] == "awaiting_browser_login"
