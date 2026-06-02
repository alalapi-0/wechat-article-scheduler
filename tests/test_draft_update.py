"""Round 71 / 收敛 Round 16：微信草稿更新。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.mock import MockWechatAdapter
from wechat_article_scheduler.adapters.real import RealWechatAdapter
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.draft_update import (
    draft_content_fingerprint,
    update_article_wechat_draft,
)
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


def test_mock_update_draft_keeps_media_id() -> None:
    adapter = MockWechatAdapter()
    created = adapter.create_draft(title="A", summary="S", body="body1")
    updated = adapter.update_draft(
        media_id=created.media_id,
        title="A2",
        summary="S",
        body="body2",
    )
    assert updated.media_id == created.media_id
    assert updated.raw_response.get("updated") is True


def test_real_update_draft_calls_api() -> None:
    posts: list[tuple[str, dict]] = []

    def fake_get(url: str, **kwargs) -> dict:  # noqa: ARG001
        return {"access_token": "T", "expires_in": 7200}

    def fake_post_json(url: str, body: dict, **kwargs) -> dict:  # noqa: ARG001
        posts.append((url, body))
        if "draft/update" in url:
            return {"errcode": 0, "media_id": body["media_id"]}
        return {"errcode": 0}

    def fake_multipart(url: str, fields: dict, files: dict, **kwargs) -> dict:  # noqa: ARG001
        return {"errcode": 0, "media_id": "thumb_1"}

    adapter = RealWechatAdapter(
        "wx",
        "sec",
        http_get=fake_get,
        http_post_json_fn=fake_post_json,
        http_post_multipart_fn=fake_multipart,
    )
    adapter.update_draft(
        media_id="draft_media_9",
        title="新标题",
        summary="摘要",
        body="<p>新正文</p>",
    )
    upd = [p for p in posts if "draft/update" in p[0]]
    assert len(upd) == 1
    assert upd[0][1]["media_id"] == "draft_media_9"
    assert upd[0][1]["articles"]["title"] == "新标题"


@pytest.fixture
def draft_cfg(tmp_path: Path) -> AppConfig:
    db_path = tmp_path / "draft_upd.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status, cover_path)
            VALUES ('/x.md', 'T', 'S', 'body-old', 'h1', 'imported', '')
            """
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        fp = draft_content_fingerprint(
            title="T", summary="S", body="body-old", cover_path=""
        )
        payload = json.dumps(
            {"media_id": "mock_media_abc", "content_fingerprint": fp},
            ensure_ascii=False,
        )
        conn.execute(
            """
            INSERT INTO wechat_drafts (article_id, media_id, status, payload_json)
            VALUES (?, 'mock_media_abc', 'created', ?)
            """,
            (aid, payload),
        )
        conn.commit()
    return make_test_config(tmp_path, db_path), aid


def test_update_skips_unchanged_content(draft_cfg: tuple[AppConfig, int]) -> None:
    cfg, aid = draft_cfg
    result = update_article_wechat_draft(cfg, aid)
    assert result["ok"] is True
    assert result.get("skipped_unchanged") is True
    with db.connect(cfg.database_path) as conn:
        cnt = conn.execute(
            "SELECT COUNT(*) AS c FROM wechat_drafts WHERE article_id = ?",
            (aid,),
        ).fetchone()["c"]
    assert cnt == 1


def test_update_creates_updated_row(draft_cfg: tuple[AppConfig, int]) -> None:
    cfg, aid = draft_cfg
    with db.connect(cfg.database_path) as conn:
        conn.execute("UPDATE articles SET body = 'body-new' WHERE id = ?", (aid,))
        conn.commit()
    result = update_article_wechat_draft(cfg, aid)
    assert result["ok"] is True
    assert not result.get("skipped_unchanged")
    with db.connect(cfg.database_path) as conn:
        rows = conn.execute(
            "SELECT status FROM wechat_drafts WHERE article_id = ? ORDER BY id",
            (aid,),
        ).fetchall()
        ev = conn.execute(
            "SELECT event_type FROM events WHERE event_type = 'draft_updated' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert [r["status"] for r in rows] == ["superseded", "updated"]
    assert ev is not None


def test_update_api_and_detail_button(tmp_path: Path) -> None:
    db_path = tmp_path / "api_draft.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('/y.md', 'Y', 'S', 'b1', 'h2', 'imported')
            """
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            """
            INSERT INTO wechat_drafts (article_id, media_id, status, payload_json)
            VALUES (?, 'mock_media_y', 'created', '{"content_fingerprint":"old"}')
            """,
            (aid,),
        )
        conn.commit()
    cfg = make_test_config(tmp_path, db_path)
    client = TestClient(create_app(cfg))
    detail = client.get(f"/api/articles/{aid}").json()
    assert detail["wechat_draft"]["can_update"] is True
    page = client.get(f"/articles/{aid}").text
    assert "btnUpdateDraft" in page
    with db.connect(db_path) as conn:
        conn.execute("UPDATE articles SET body = 'b2' WHERE id = ?", (aid,))
        conn.commit()
    r = client.post(f"/api/articles/{aid}/update-draft")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_fingerprint_stable() -> None:
    a = draft_content_fingerprint(title="T", summary="S", body="B", cover_path=None)
    b = draft_content_fingerprint(title="T", summary="S", body="B", cover_path=None)
    assert a == b
