"""Round 68 / 收敛 Round 13：微信草稿管理页面。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.drafts_display import (
    drafts_summary,
    get_wechat_draft,
    list_wechat_drafts,
)
from tests.conftest import make_test_config


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    db_path = tmp_path / "drafts.sqlite3"
    db.init_db(db_path)
    return make_test_config(tmp_path, db_path)


def _seed_draft(conn, *, title: str = "测试稿", media_id: str = "mock_media_abc123") -> tuple[int, int]:
    conn.execute(
        "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
        "VALUES ('/d.md', ?, 'S', 'B', 'hd', 'imported')",
        (title,),
    )
    aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    conn.execute(
        "INSERT INTO wechat_drafts (article_id, media_id, status, payload_json) "
        "VALUES (?, ?, 'created', ?)",
        (aid, media_id, json.dumps({"ok": True}, ensure_ascii=False)),
    )
    did = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    return aid, did


def test_list_wechat_drafts_mock_label(app_config: AppConfig) -> None:
    with db.connect(app_config.database_path) as conn:
        _seed_draft(conn)
        conn.commit()
        rows = list_wechat_drafts(conn, app_config, status="created")
    assert len(rows) == 1
    assert rows[0]["is_mock_draft"] is True
    assert "演练" in rows[0]["media_id_label"]
    assert rows[0]["mock_note"]
    assert rows[0]["article_detail_url"].startswith("/articles/")


def test_drafts_api_and_summary(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        _seed_draft(conn, title="API 稿")
        conn.commit()
    summary = client.get("/api/drafts-summary").json()
    assert summary["total"] == 1
    assert summary["mode"] == "mock"
    assert "演练" in summary["mode_note"]
    drafts = client.get("/api/drafts", params={"status": "created"}).json()
    assert len(drafts) == 1
    assert drafts[0]["title"] == "API 稿"
    detail = client.get(f"/api/drafts/{drafts[0]['id']}").json()
    assert detail["status_label"] == "已创建"
    assert detail["payload_preview"]


def test_draft_detail_404(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    assert client.get("/api/drafts/9999").status_code == 404


def test_drafts_pages_in_html(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    index = client.get("/").text
    assert 'id="drafts"' in index
    assert "draftFilters" in index
    page = client.get("/drafts").text
    assert "微信草稿记录" in page
    assert "/api/drafts-summary" in page


def test_get_wechat_draft_missing(app_config: AppConfig) -> None:
    with db.connect(app_config.database_path) as conn:
        assert get_wechat_draft(conn, app_config, 42) is None
        assert drafts_summary(conn, app_config)["total"] == 0
