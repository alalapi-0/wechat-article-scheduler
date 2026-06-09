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
    record_browser_connection,
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


def _pass_connection_report() -> dict[str, object]:
    return {
        "mcp": "wechat-chrome-session",
        "connection_mode": "existing Chrome / autoConnect",
        "target_host": "mp.weixin.qq.com",
        "target_url": "https://mp.weixin.qq.com/cgi-bin/appmsg",
        "page_title": "公众号后台（脱敏）",
        "backend_visible": True,
        "login_required": False,
        "dom_snapshot_available": True,
        "screenshot_available": True,
        "write_actions_performed": 0,
        "result": "PASS",
        "block_reason": "none",
    }


def _blocked_connection_report() -> dict[str, object]:
    payload = _pass_connection_report()
    payload["backend_visible"] = False
    payload["result"] = "BLOCKED"
    payload["block_reason"] = "backend_not_visible"
    return payload


def test_start_session_blocks_on_login_gate(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        result = start_browser_assist_session(cfg, conn, job_id, export_task_package=False)

    assert result["ok"]
    assert result["status"] == "awaiting_browser_login"
    assert result["blocked"] is True
    assert "wechat-chrome-session" in result["prompt_zh"]
    assert "登录已过期" in result["prompt_zh"]
    assert result["login_gate"]["mcp_server"] == "wechat-chrome-session"
    assert result["login_gate"]["login_url"] == "https://mp.weixin.qq.com/"
    assert result["login_gate"]["target_host"] == "mp.weixin.qq.com"
    assert result["login_gate"]["connection_report_template"]["result"] == "PASS"
    assert any("wechat_chrome_session_runbook" in step for step in result["human"])
    assert result["dry_run_plan"]["login_gate_required"] is True


def test_confirm_login_requires_connection_report(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        started = start_browser_assist_session(cfg, conn, job_id, export_task_package=False)
        session_id = started["session_id"]
        blocked = confirm_browser_login(cfg, conn, session_id)
    assert blocked["ok"] is False
    assert "连接验收报告" in blocked["error"]


def test_confirm_login_then_draft_review_flow(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        started = start_browser_assist_session(cfg, conn, job_id, export_task_package=False)
        session_id = started["session_id"]
        recorded = record_browser_connection(
            cfg,
            conn,
            session_id,
            report=_pass_connection_report(),
        )
        assert recorded["ok"]
        assert recorded["connection_report"]["result"] == "PASS"
        login = confirm_browser_login(cfg, conn, session_id)
        assert login["ok"]
        assert login["status"] == "assist_in_progress"

        sched = confirm_schedule_setup(cfg, conn, session_id, scheduled_at="2026-06-08T20:00:00")
        assert sched["ok"]
        assert sched["status"] == "awaiting_proof"
        assert "发布前草稿准备完成" in "\n".join(sched["human"])
        assert "后台目标时间：2026-06-08T20:00:00" in "\n".join(sched["human"])

        view = get_browser_assist_session(cfg, session_id)
        assert view["ok"]
        assert view["status"] == "awaiting_proof"
        assert any("正式发表" in step for step in view["human_steps"])
        assert view["backend_schedule_target_at"] == "2026-06-08T20:00:00"


def test_blocked_connection_report_keeps_session_gated(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        started = start_browser_assist_session(cfg, conn, job_id, export_task_package=False)
        session_id = started["session_id"]
        recorded = record_browser_connection(
            cfg,
            conn,
            session_id,
            report=_blocked_connection_report(),
        )
        assert recorded["ok"]
        assert recorded["status"] == "awaiting_browser_login"
        assert recorded["connection_report"]["result"] == "BLOCKED"
        denied = confirm_browser_login(cfg, conn, session_id)
    assert denied["ok"] is False
    assert "连接验收报告（PASS）" in denied["error"]


def test_legacy_final_schedule_action_does_not_claim_backend_schedule(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        started = start_browser_assist_session(cfg, conn, job_id, export_task_package=False)
        session_id = started["session_id"]
        record_browser_connection(cfg, conn, session_id, report=_pass_connection_report())
        login = confirm_browser_login(cfg, conn, session_id)
        assert login["ok"]

        final = confirm_final_schedule(cfg, conn, session_id)
        assert final["ok"]
        assert final["status"] == "awaiting_proof"
        assert "不代表已发布或已创建后台定时任务" in "\n".join(final["human"])


def test_session_persisted_to_storage(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        result = start_browser_assist_session(cfg, conn, job_id, export_task_package=False)
    session_file = cfg.root / "storage" / "browser_assist_sessions" / f"{result['session_id']}.json"
    assert session_file.is_file()
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    assert payload["job_id"] == job_id
    assert payload["status"] == "awaiting_browser_login"
