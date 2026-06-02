"""Round 66 / 收敛 Round 11：文章详情与预览页面。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.article_detail import build_article_detail, suggest_detail_actions
from tests.conftest import make_test_config


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    db_path = tmp_path / "detail.sqlite3"
    db.init_db(db_path)
    return make_test_config(tmp_path, db_path)


def _insert_article(conn, *, title: str = "测试文", summary: str = "摘要", body: str = "正文") -> int:
    conn.execute(
        """
        INSERT INTO articles (source_path, title, summary, body, content_hash, status)
        VALUES ('/t.md', ?, ?, ?, 'hash-d', 'imported')
        """,
        (title, summary, body),
    )
    return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])


def test_build_article_detail_next_action_schedule(app_config: AppConfig) -> None:
    with db.connect(app_config.database_path) as conn:
        aid = _insert_article(conn)
        conn.commit()
        detail = build_article_detail(app_config, conn, aid)
    assert detail["workflow_hint"] == "待安排发布"
    assert detail["workbench"]["primary_action"] == "schedule"


def test_detail_api_and_page(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        aid = _insert_article(conn, body="# 标题\n\n段落内容。")
        conn.commit()
    api = client.get(f"/api/articles/{aid}")
    assert api.status_code == 200
    data = api.json()
    assert data["title"] == "测试文"
    assert "preflight_checks" in data
    assert "workbench" in data
    assert data["preview_url"].endswith("/render-preview")

    page = client.get(f"/articles/{aid}")
    assert page.status_code == 200
    assert "返回工作台" in page.text
    assert "render-preview" in page.text
    assert str(aid) in page.text


def test_detail_page_404(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    assert client.get("/articles/99999").status_code == 404


def test_render_preview_from_detail_flow(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        aid = _insert_article(conn)
        conn.commit()
    r = client.get(f"/api/articles/{aid}/render-preview")
    assert r.status_code == 200
    assert r.json().get("html_body")


def test_detail_with_job_and_long_summary(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    long_summary = "摘" * 130
    with db.connect(app_config.database_path) as conn:
        aid = _insert_article(conn, summary=long_summary)
        when = (datetime.now() + timedelta(days=1)).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, ?, 'pending', 'mock')",
            (aid, when),
        )
        conn.commit()
    data = client.get(f"/api/articles/{aid}").json()
    assert data["latest_job"]["status_label"] == "待发布"
    digest_check = next(c for c in data["preflight_checks"] if c["id"] == "digest")
    assert digest_check["ok"] is False


def test_suggest_detail_actions_cover(app_config: AppConfig) -> None:
    row = {"status": "published", "cover_path": ""}
    wb = suggest_detail_actions(row=row, job=None, checks=[], config=app_config)
    assert wb["primary_action"] == "cover"
