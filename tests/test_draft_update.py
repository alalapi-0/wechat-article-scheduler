"""微信草稿更新。"""

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
from tests.test_web_upload import PNG


def _write_png(path: Path) -> Path:
    path.write_bytes(PNG)
    return path


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


def test_real_update_draft_calls_api(tmp_path: Path) -> None:
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
        default_thumb_path=str(_write_png(tmp_path / "default.png")),
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


def test_real_update_missing_cover_rejected_before_any_http(tmp_path: Path) -> None:
    calls: list[str] = []

    def unexpected_http(*args, **kwargs) -> dict:  # noqa: ANN002, ANN003, ARG001
        calls.append("http")
        return {"access_token": "unexpected", "media_id": "unexpected"}

    adapter = RealWechatAdapter(
        "wx",
        "sec",
        default_thumb_path=str(tmp_path / "missing-default.png"),
        managed_roots=(tmp_path,),
        http_get=unexpected_http,
        http_post_json_fn=unexpected_http,
        http_post_multipart_fn=unexpected_http,
    )

    with pytest.raises(RuntimeError, match="无法安全读取"):
        adapter.update_draft(
            media_id="draft_media_9",
            title="新标题",
            summary="摘要",
            body="正文",
            cover_path=str(tmp_path / "missing-article.png"),
        )

    assert calls == []


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
        job_id = int(
            conn.execute(
                """
                INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
                VALUES (?, datetime('now'), 'done', 'mock')
                """,
                (aid,),
            ).lastrowid
        )
        fp = draft_content_fingerprint(
            title="T", summary="S", body="body-old", cover_path=""
        )
        payload = json.dumps(
            {"media_id": "mock_media_abc", "content_fingerprint": fp},
            ensure_ascii=False,
        )
        conn.execute(
            """
            INSERT INTO wechat_drafts (
                article_id, media_id, status, payload_json,
                adapter_mode, publish_job_id
            ) VALUES (?, 'mock_media_abc', 'created', ?, 'mock', ?)
            """,
            (aid, payload, job_id),
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
            """
            SELECT status, adapter_mode, publish_job_id
            FROM wechat_drafts WHERE article_id = ? ORDER BY id
            """,
            (aid,),
        ).fetchall()
        ev = conn.execute(
            "SELECT event_type FROM events WHERE event_type = 'draft_updated' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert [r["status"] for r in rows] == ["superseded", "updated"]
    assert {r["adapter_mode"] for r in rows} == {"mock"}
    assert len({r["publish_job_id"] for r in rows}) == 1
    assert ev is not None


def test_update_rejects_cross_mode_draft_before_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "cross-mode-update.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        aid = int(
            conn.execute(
                """
                INSERT INTO articles (
                    source_path, title, summary, body, content_hash, status
                ) VALUES ('cross.md', 'T', 'S', 'changed', 'cross-hash', 'imported')
                """
            ).lastrowid
        )
        mock_job_id = int(
            conn.execute(
                """
                INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
                VALUES (?, datetime('now'), 'done', 'mock')
                """,
                (aid,),
            ).lastrowid
        )
        conn.execute(
            """
            INSERT INTO wechat_drafts (
                article_id, media_id, status, payload_json,
                adapter_mode, publish_job_id
            ) VALUES (?, 'mock_media_cross', 'created',
                      '{"content_fingerprint":"old"}', 'mock', ?)
            """,
            (aid, mock_job_id),
        )
        conn.commit()

    adapter_calls: list[str] = []

    def unexpected_adapter(_config):  # noqa: ANN001, ANN202
        adapter_calls.append("adapter")
        raise AssertionError("adapter must not be constructed")

    monkeypatch.setattr(
        "wechat_article_scheduler.draft_update.get_adapter",
        unexpected_adapter,
    )
    cfg = make_test_config(tmp_path, db_path, wechat_mode="real")
    result = update_article_wechat_draft(cfg, aid)
    assert result["ok"] is False
    assert "跨模式" in result["error"]
    assert adapter_calls == []
    with db.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, adapter_mode, publish_job_id FROM wechat_drafts"
        ).fetchone()
    assert dict(row) == {
        "status": "created",
        "adapter_mode": "mock",
        "publish_job_id": mock_job_id,
    }


@pytest.mark.parametrize("blocked_body", ["", "&lt;p&gt;escaped source&lt;/p&gt;"])
def test_real_update_blocks_invalid_content_before_adapter_or_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, blocked_body: str
) -> None:
    db_path = tmp_path / "real-content-gate.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        aid = int(conn.execute(
            "INSERT INTO articles(source_path,title,summary,body,content_hash,status) "
            "VALUES ('blocked.md','T','S',?,'blocked-hash','imported')",
            (blocked_body,),
        ).lastrowid)
        job_id = int(conn.execute(
            "INSERT INTO publish_jobs(article_id,scheduled_at,status,adapter_mode) "
            "VALUES (?,datetime('now'),'done','real')", (aid,)
        ).lastrowid)
        conn.execute(
            "INSERT INTO wechat_drafts(article_id,media_id,status,payload_json,adapter_mode,publish_job_id) "
            "VALUES (?,'real-media','created','{\"content_fingerprint\":\"old\"}','real',?)",
            (aid, job_id),
        )
        conn.commit()
    calls: list[str] = []
    monkeypatch.setattr(
        "wechat_article_scheduler.draft_update.get_adapter",
        lambda _cfg: calls.append("adapter"),
    )
    cfg = make_test_config(
        tmp_path, db_path, wechat_mode="real", wechat_app_id="app", wechat_app_secret="secret"
    )
    result = update_article_wechat_draft(cfg, aid)
    assert result["ok"] is False
    assert "内容预检未通过" in result["error"]
    assert calls == []
    with db.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM wechat_drafts").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


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
        job_id = int(
            conn.execute(
                """
                INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
                VALUES (?, datetime('now'), 'done', 'mock')
                """,
                (aid,),
            ).lastrowid
        )
        conn.execute(
            """
            INSERT INTO wechat_drafts (
                article_id, media_id, status, payload_json,
                adapter_mode, publish_job_id
            ) VALUES (?, 'mock_media_y', 'created',
                      '{"content_fingerprint":"old"}', 'mock', ?)
            """,
            (aid, job_id),
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
