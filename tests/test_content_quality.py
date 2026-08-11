"""草稿创建前内容质量检查与真实 API 阻断。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.base import DraftResult
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.scheduler import run_due_jobs
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.content_quality import article_content_hints, content_block_reason
from wechat_article_scheduler.web.publish_preflight import build_publish_preflight
from tests.conftest import make_test_config


def test_content_block_reason_empty_and_escaped_html() -> None:
    assert content_block_reason("标题", "") == "正文为空"
    assert content_block_reason("标题", "   ") == "正文为空"
    body = "&lt;p&gt;段落&lt;/p&gt;"
    assert content_block_reason("标题", body) == "疑似 HTML 源码"
    assert content_block_reason("标题", "# 标题\n\n正文") is None


def test_article_content_hints_lists_issues() -> None:
    hints = article_content_hints("标题", "&lt;p&gt;x&lt;/p&gt;")
    assert "疑似 HTML 源码" in hints


def test_draft_preflight_blocks_real_empty_body(tmp_path: Path) -> None:
    db_path = tmp_path / "cq.sqlite3"
    db.init_db(db_path)
    cover_path = tmp_path / "cq-cover.png"
    cover_path.write_bytes(b"cover")
    past = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status, cover_path)
            VALUES ('a.md', 'T', '', '', 'h-cq', 'imported', ?)
            """,
            (str(cover_path),),
        )
        aid = int(conn.execute("SELECT id FROM articles").fetchone()[0])
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, publish_config_json)
            VALUES (?, ?, 'pending', 'real', ?)
            """,
            (
                aid,
                past,
                '{"auto_execute":false,"need_open_comment":false,'
                '"only_fans_can_comment":false,"author":"","content_source_url":""}',
            ),
        )
        conn.commit()
    cfg = make_test_config(
        tmp_path,
        db_path,
        wechat_mode="real",
    )
    with db.connect(db_path) as conn:
        pf = build_publish_preflight(cfg, conn)
    assert pf["ready"] is False
    assert any(c["id"] == "empty_body" and c["required"] for c in pf["checks"])


def test_run_due_real_draft_creation_skips_empty_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "run-cq.sqlite3"
    db.init_db(db_path)
    past = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('a.md', 'T', '', '', 'h-run', 'imported')
            """
        )
        aid = int(conn.execute("SELECT id FROM articles").fetchone()[0])
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, publish_config_json)
            VALUES (?, ?, 'pending', 'real', ?)
            """,
            (
                aid,
                past,
                '{"auto_execute":false,"need_open_comment":false,'
                '"only_fans_can_comment":false,"author":"","content_source_url":""}',
            ),
        )
        conn.commit()

    called: list[str] = []

    class FakeAdapter:
        def create_draft(self, **kwargs):  # noqa: ANN001, ANN201
            called.append("draft")
            return DraftResult(media_id="m1", raw_response={})

    monkeypatch.setattr(
        "wechat_article_scheduler.scheduler.domain.get_adapter",
        lambda config: FakeAdapter(),  # noqa: ARG005
    )
    cfg = make_test_config(
        tmp_path,
        db_path,
        wechat_mode="real",
        dry_run=False,
    )
    stats = run_due_jobs(cfg)
    assert stats["skipped_content"] == 1
    assert stats["processed"] == 0
    assert called == []
    with db.connect(db_path) as conn:
        event = conn.execute(
            "SELECT event_type FROM events WHERE event_type = 'draft_blocked_content'"
        ).fetchone()
        job = conn.execute(
            "SELECT status, claim_token FROM publish_jobs WHERE article_id = ?", (aid,)
        ).fetchone()
        lock_count = conn.execute("SELECT COUNT(*) FROM scheduler_locks").fetchone()[0]
        assert event is None
        assert dict(job) == {"status": "pending", "claim_token": None}
        assert lock_count == 0


def test_run_due_mock_does_not_skip_empty_body(tmp_path: Path) -> None:
    db_path = tmp_path / "mock-cq.sqlite3"
    db.init_db(db_path)
    past = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('a.md', 'T', '', '', 'h-mock', 'imported')
            """
        )
        aid = int(conn.execute("SELECT id FROM articles").fetchone()[0])
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, publish_config_json)
            VALUES (?, ?, 'pending', 'mock', ?)
            """,
            (
                aid,
                past,
                '{"auto_execute":false,"need_open_comment":false,'
                '"only_fans_can_comment":false,"author":"","content_source_url":""}',
            ),
        )
        conn.commit()
    cfg = make_test_config(tmp_path, db_path, wechat_mode="mock", dry_run=False)
    stats = run_due_jobs(cfg)
    assert stats.get("skipped_content", 0) == 0
    assert stats["processed"] == 1


@pytest.fixture
def real_draft_client(tmp_path: Path) -> tuple[TestClient, AppConfig]:
    db_path = tmp_path / "api-cq.sqlite3"
    db.init_db(db_path)
    cover_path = tmp_path / "api-cq-cover.png"
    cover_path.write_bytes(b"cover")
    cfg = make_test_config(
        tmp_path,
        db_path,
        wechat_mode="real",
    )
    past = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status, cover_path)
            VALUES ('a.md', 'T', '', '', 'h-api', 'imported', ?)
            """,
            (str(cover_path),),
        )
        aid = int(conn.execute("SELECT id FROM articles").fetchone()[0])
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, publish_config_json)
            VALUES (?, ?, 'pending', 'real', ?)
            """,
            (
                aid,
                past,
                '{"auto_execute":false,"need_open_comment":false,'
                '"only_fans_can_comment":false,"author":"","content_source_url":""}',
            ),
        )
        conn.commit()
    return TestClient(create_app(cfg)), cfg


def test_draft_preflight_api_blocks_real_empty_body(
    real_draft_client: tuple[TestClient, AppConfig],
) -> None:
    client, _cfg = real_draft_client
    data = client.get("/api/publish-preflight").json()
    assert data["ready"] is False
    assert data["mode"] == "real"
    assert any(c["id"] == "empty_body" and c["required"] for c in data["checks"])
