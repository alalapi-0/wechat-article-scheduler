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


def test_articles_empty(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    assert client.get("/api/articles").json() == []


def test_index_html(app_config: AppConfig) -> None:
    client = TestClient(create_app(app_config))
    r = client.get("/")
    assert r.status_code == 200
    assert "文章调度器" in r.text
