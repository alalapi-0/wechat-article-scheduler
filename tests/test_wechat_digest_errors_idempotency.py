"""收敛 Round 3：摘要 120 字、微信错误码可读说明、草稿创建幂等。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.base import DraftResult
from wechat_article_scheduler.adapters.wechat_http import WechatApiError
from wechat_article_scheduler.parser import clamp_summary
from wechat_article_scheduler.scheduler import run_due_jobs
from wechat_article_scheduler.scheduler.draft_idempotency import find_reusable_draft_media_id
from wechat_article_scheduler.wechat_errors import format_job_failure, human_wechat_error

from tests.conftest import make_test_config


def test_clamp_summary_unified_120_chars() -> None:
    long_text = "字" * 200
    out = clamp_summary(long_text, 120)
    assert len(out) == 120


def test_human_wechat_error_known_code() -> None:
    msg = human_wechat_error(48001, "api unauthorized")
    assert "未授权" in msg or "48001" in msg


def test_format_job_failure_wechat_api_error() -> None:
    exc = WechatApiError(40001, "invalid credential", endpoint="draft/add")
    payload = format_job_failure(exc)
    assert "40001" in payload or "token" in payload or "凭证" in payload


def test_run_once_reuses_draft_on_same_content_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path
    db_path = root / "idem.sqlite3"
    db.init_db(db_path)
    past = (datetime.now() - timedelta(minutes=5)).isoformat(timespec="seconds")
    create_calls = 0

    class CountingAdapter:
        def create_draft(self, **kwargs):  # noqa: ANN001, ANN201
            nonlocal create_calls
            create_calls += 1
            return DraftResult(media_id=f"mock-{create_calls}", raw_response={})

        def submit_publish(self, media_id: str, *, force: bool = False) -> dict:
            return {"skipped": True, "media_id": media_id}

    monkeypatch.setattr(
        "wechat_article_scheduler.scheduler.domain.get_adapter",
        lambda cfg: CountingAdapter(),  # noqa: ARG005
    )

    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('a.md', 'T', 'S', 'body', 'hash-idem', 'imported')
            """
        )
        aid = int(conn.execute("SELECT id FROM articles").fetchone()[0])
        conn.execute(
            """
            INSERT INTO wechat_drafts (article_id, media_id, status, payload_json)
            VALUES (?, 'existing-mid', 'created', '{}')
            """,
            (aid,),
        )
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
            VALUES (?, ?, 'pending', 'mock')
            """,
            (aid, past),
        )
        conn.commit()

    cfg = make_test_config(root, db_path)
    stats = run_due_jobs(cfg)
    assert stats["processed"] == 1
    assert stats.get("draft_reused", 0) == 1
    assert create_calls == 0

    with db.connect(db_path) as conn:
        evt = conn.execute(
            "SELECT event_type FROM events WHERE event_type = 'draft_idempotent_reuse' LIMIT 1"
        ).fetchone()
        draft_rows = conn.execute(
            "SELECT COUNT(*) AS c FROM wechat_drafts WHERE article_id = ?",
            (aid,),
        ).fetchone()["c"]
    assert evt is not None
    assert draft_rows == 1


def test_find_reusable_draft_requires_matching_hash(tmp_path: Path) -> None:
    db_path = tmp_path / "find.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('a.md', 'T', '', '', 'hash-a', 'imported')
            """
        )
        aid = int(conn.execute("SELECT id FROM articles").fetchone()[0])
        conn.execute(
            "INSERT INTO wechat_drafts (article_id, media_id, status) VALUES (?, 'm1', 'created')",
            (aid,),
        )
        conn.commit()
        assert find_reusable_draft_media_id(conn, article_id=aid, content_hash="hash-a") == "m1"
        assert find_reusable_draft_media_id(conn, article_id=aid, content_hash="other") is None
