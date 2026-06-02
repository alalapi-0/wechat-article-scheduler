"""Round 119：工作台 URL hash 深链与区块恢复。"""

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
    db_path = tmp_path / "r119.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def test_home_hash_deep_link_markup(client: TestClient) -> None:
    html = client.get("/").text
    assert "wechat_workbench_section_hash" in html
    assert "initWorkbenchHash" in html
    assert "normalizeWorkbenchSection" in html
    assert 'href="#queue"' in html
    assert 'id="queue"' in html
    assert 'id="works"' in html
    assert 'id="drafts"' in html


def test_articles_hash_alias_to_works(client: TestClient) -> None:
    html = client.get("/").text
    assert "articles" in html
    assert re.search(r"h === 'articles'.*works|articles.*return 'works'", html)


def test_nav_sections_present(client: TestClient) -> None:
    html = client.get("/").text
    for sec in ("works", "queue", "drafts", "actions"):
        assert f'id="{sec}"' in html
        assert f'href="#{sec}"' in html
