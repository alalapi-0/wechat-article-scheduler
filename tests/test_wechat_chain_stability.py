"""scan -> plan -> run-once 主链路 mock 回归。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.base import DraftResult
from wechat_article_scheduler.plan import build_plan
from wechat_article_scheduler.scanner import scan_inbox
from wechat_article_scheduler.scheduler import run_due_jobs

from tests.conftest import make_test_config
from tests.test_web_upload import PNG


def test_scan_plan_run_once_mock_chain(tmp_path: Path) -> None:
    root = tmp_path
    db_path = root / "data.sqlite3"
    db.init_db(db_path)

    inbox = root / "articles" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "chapter.md").write_text(
        "---\ntitle: 链路测试\ndigest: 摘要\n---\n\n正文。",
        encoding="utf-8",
    )
    (root / "articles" / "imported").mkdir(parents=True)
    (root / "articles" / "published").mkdir(parents=True)

    cfg = make_test_config(
        root,
        db_path,
        rules={
            "schedule": {
                "max_per_day": 2,
                "min_hours_between": 0,
                "preferred_hours": [9],
            }
        },
    )

    scan_stats = scan_inbox(cfg)
    assert scan_stats["imported"] == 1

    plan_stats = build_plan(cfg)
    assert plan_stats["planned"] >= 1

    past = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    with db.connect(db_path) as conn:
        conn.execute(
            "UPDATE publish_jobs SET scheduled_at = ? WHERE status = 'pending'",
            (past,),
        )
        conn.commit()

    run_stats = run_due_jobs(cfg)
    assert run_stats["processed"] >= 1

    with db.connect(db_path) as conn:
        job = conn.execute(
            "SELECT status, adapter_mode FROM publish_jobs"
        ).fetchone()
        draft_count = conn.execute(
            "SELECT COUNT(*) AS c FROM wechat_drafts"
        ).fetchone()["c"]
        assert job["status"] == "done"
        assert job["adapter_mode"] == "mock"
        assert draft_count >= 1


def test_real_draft_only_run_once_skips_submit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "real-chain.sqlite3"
    db.init_db(db_path)
    past = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('a.md', 'T', 'S', 'body', 'hash-r57', 'imported')
            """
        )
        aid = int(conn.execute("SELECT id FROM articles").fetchone()[0])
        conn.execute(
            """
            INSERT INTO publish_jobs (
                article_id, scheduled_at, status, adapter_mode,
                publish_config_json, retry_count
            )
            VALUES (?, ?, 'pending', 'real', ?, 0)
            """,
            (
                aid,
                past,
                '{"auto_execute":false,'
                '"need_open_comment":false,"only_fans_can_comment":false,'
                '"author":"","content_source_url":""}',
            ),
        )
        conn.commit()

    class FakeAdapter:
        def create_draft(self, **kwargs):  # noqa: ANN001, ANN201
            return DraftResult(media_id="draft-r57", raw_response={"media_id": "draft-r57"})

    monkeypatch.setattr(
        "wechat_article_scheduler.scheduler.domain.get_adapter",
        lambda config: FakeAdapter(),  # noqa: ARG005
    )
    cfg = make_test_config(
        tmp_path,
        db_path,
        wechat_mode="real",
        wechat_app_id="test-app",
        wechat_app_secret="test-secret",
        wechat_default_thumb_path=str(tmp_path / "default.png"),
        dry_run=False,
    )
    (tmp_path / "default.png").write_bytes(PNG)
    stats = run_due_jobs(cfg)
    assert stats["processed"] == 1
    assert stats["drafted"] == 1
    with db.connect(db_path) as conn:
        article = conn.execute("SELECT status FROM articles WHERE id = ?", (aid,)).fetchone()
        event = conn.execute(
            "SELECT event_type FROM events ORDER BY id DESC LIMIT 1",
        ).fetchone()
    assert article["status"] == "imported"
    assert event is not None
    assert event["event_type"] == "draft_created"
