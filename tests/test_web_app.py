"""FastAPI 管理后台测试（Round 6）。"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    db_path = tmp_path / "test.sqlite3"
    db.init_db(db_path)
    return make_test_config(tmp_path, db_path)


def test_status_endpoint(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    r = client.get("/api/status")
    assert r.status_code == 200
    assert r.json()["wechat_mode"] == "mock"
    assert "wechat_enable_publish" in r.json()


def test_articles_empty(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    assert client.get("/api/articles").json() == []


def test_index_html(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    r = client.get("/")
    assert r.status_code == 200
    assert "工作台" in r.text
    assert "主操作" in r.text
    assert "发布队列" in r.text
    assert "操作记录" in r.text
    assert "高级排错" in r.text


def test_round47_brand_polish(app_config: AppConfig) -> None:
    """Round 47：轻量品牌标识与无审核概念回归。"""
    client = TestClient(create_app(app_config))
    html = client.get("/").text
    assert "border-radius: 50%" in html
    assert "review_status" not in html.lower()
    assert ">发<" not in html


def test_user_labels_endpoint(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    r = client.get("/api/user-labels")
    assert r.status_code == 200
    assert r.json()["job_status"]["pending"] == "待发布"


def test_render_preview_endpoint(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("/tmp/preview.md", "预览文", "摘要", "# 标题\n\n段落。", "abc123", "imported"),
        )
        conn.commit()
        article_id = conn.execute("SELECT id FROM articles").fetchone()[0]
    r = client.get(f"/api/articles/{article_id}/render-preview")
    assert r.status_code == 200
    data = r.json()
    assert data["read_only"] is True
    assert "<h1" not in data["html_body"]
    assert "font-size: 22px" in data["html_body"]
    assert "font-weight: 700" in data["html_body"]
    assert data["render_error"] is None
    assert data.get("approximation_note")
    assert "snapshot_version" in data


def test_render_preview_save_snapshot(app_config: AppConfig) -> None:
    """Round 60：?save_snapshot=true 落盘 JSON/HTML。"""
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("/tmp/snap.md", "快照文", "摘要", "段落。", "snaphash", "imported"),
        )
        conn.commit()
        article_id = conn.execute("SELECT id FROM articles").fetchone()[0]
    r = client.get(f"/api/articles/{article_id}/render-preview?save_snapshot=true")
    assert r.status_code == 200
    data = r.json()
    assert data["snapshot_path"].startswith("storage/preview_snapshots/")
    snap_dir = app_config.root / "storage" / "preview_snapshots"
    assert list(snap_dir.glob(f"article_{article_id}_*.json"))


def test_preview_snapshot_post(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("/tmp/post.md", "POST", "", "正文", "posthash", "imported"),
        )
        conn.commit()
        article_id = conn.execute("SELECT id FROM articles").fetchone()[0]
    r = client.post(f"/api/articles/{article_id}/preview-snapshot")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "preview_snapshots" in body["snapshot_path"]


def test_render_preview_no_raw_html_entities(app_config: AppConfig) -> None:
    """Round 49：预览为渲染后正文，不展示转义源码。"""
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("/tmp/esc.md", "标题", "", "&lt;p&gt;段落&lt;/p&gt;", "eschash", "imported"),
        )
        conn.commit()
        article_id = conn.execute("SELECT id FROM articles").fetchone()[0]
    data = client.get(f"/api/articles/{article_id}/render-preview").json()
    assert "&lt;p&gt;" not in data["html_body"]
    assert "段落" in data["html_body"]


def test_render_preview_strips_duplicate_title(app_config: AppConfig) -> None:
    """Round 48：预览与草稿同源，正文不重复首标题。"""
    client = TestClient(create_app(app_config))
    body = "# 重复标题\n\n正文段。"
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("/tmp/dup.md", "重复标题", "摘要", body, "duphash", "imported"),
        )
        conn.commit()
        article_id = conn.execute("SELECT id FROM articles").fetchone()[0]
    data = client.get(f"/api/articles/{article_id}/render-preview").json()
    assert data["raw_body"] == body
    assert "正文段" in data["html_body"]
    assert "重复标题" not in data["html_body"]


def test_overview_endpoint_empty(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    r = client.get("/api/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["status"]["wechat_mode"] == "mock"
    assert data["recent_jobs"] == []
    assert data["recent_events"] == []
    assert any(item["path"] == "docs/web_console_design.md" for item in data["docs"])
