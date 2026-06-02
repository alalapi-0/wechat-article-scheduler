"""Round 116：高级信息开关 localStorage 与 Desktop-first 默认隐藏。"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r116.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def test_home_advanced_storage_and_hidden_debug(client: TestClient) -> None:
    html = client.get("/").text
    assert "wechat_workbench_show_advanced" in html
    assert "initAdvancedToggle" in html
    assert "persistShowAdvanced" in html
    assert re.search(r'href="/debug"[^>]*class="[^"]*advanced-only', html)
    assert 'id="advanced"' in html or 'id="advRaw"' in html
    assert "显示高级信息" in html


def test_debug_links_are_advanced_only(client: TestClient) -> None:
    html = client.get("/").text
    assert re.search(
        r'<a[^>]*href="/debug"[^>]*class="[^"]*advanced-only',
        html,
    )
    assert re.search(r'class="advanced-only"[\s\S]*?<a[^>]*href="/debug"', html)
