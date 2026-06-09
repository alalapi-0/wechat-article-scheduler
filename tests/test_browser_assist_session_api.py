"""browser_assist 会话 API：接管报告与登录门控。"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


def _seed_job(tmp_path: Path) -> tuple[object, int]:
    cfg = make_test_config(tmp_path, tmp_path / "ba_api.sqlite3")
    db.init_db(cfg.database_path)
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('api.md', 'API 门控测试', '摘要', '正文', 'hash-ba-api', 'imported')
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
            VALUES (?, 'mock_media_ba_api', 'created', '{}')
            """,
            (article_id,),
        )
        conn.commit()
    return cfg, job_id


def _pass_report() -> dict[str, object]:
    return {
        "mcp": "wechat-chrome-session",
        "connection_mode": "existing Chrome / autoConnect",
        "target_host": "mp.weixin.qq.com",
        "target_url": "https://mp.weixin.qq.com/cgi-bin/home",
        "page_title": "公众号后台（脱敏）",
        "backend_visible": True,
        "login_required": False,
        "dom_snapshot_available": True,
        "screenshot_available": True,
        "write_actions_performed": 0,
        "result": "PASS",
        "block_reason": "none",
    }


def test_confirm_login_requires_recorded_connection_report(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    client = TestClient(create_app(cfg))

    started = client.post("/api/browser-assist/sessions/start", json={"job_id": job_id})
    assert started.status_code == 200
    sid = started.json()["session_id"]

    denied = client.post(f"/api/browser-assist/sessions/{sid}/confirm-login", json={})
    assert denied.status_code == 400
    assert "连接验收报告" in denied.json()["detail"]


def test_record_connection_then_confirm_login_via_api(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    client = TestClient(create_app(cfg))

    started = client.post("/api/browser-assist/sessions/start", json={"job_id": job_id})
    assert started.status_code == 200
    sid = started.json()["session_id"]

    recorded = client.post(
        f"/api/browser-assist/sessions/{sid}/record-connection",
        json={"report": _pass_report()},
    )
    assert recorded.status_code == 200
    body = recorded.json()
    assert body["connection_report"]["result"] == "PASS"

    confirmed = client.post(
        f"/api/browser-assist/sessions/{sid}/confirm-login",
        json={},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "assist_in_progress"
