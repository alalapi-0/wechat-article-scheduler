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
    assert "文章调度器" in r.text
    assert "基础工作台" in r.text
    assert "安全状态" in r.text
    assert "发布队列 / 最近任务" in r.text
    assert "事件日志" in r.text
    assert "docs/rounds.md" in r.text


def test_overview_endpoint_empty(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    r = client.get("/api/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["status"]["wechat_mode"] == "mock"
    assert data["recent_jobs"] == []
    assert data["recent_events"] == []
    assert any(item["path"] == "docs/web_console_design.md" for item in data["docs"])
