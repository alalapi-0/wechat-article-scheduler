"""Round 120：详情页返回工作台保留来源 hash。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r120.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def test_workbench_captures_return_context_markup(client: TestClient) -> None:
    html = client.get("/").text
    assert "wechat_workbench_return_hash" in html
    assert "captureWorkbenchReturnContext" in html
    assert "setupWorkbenchReturnCapture" in html


def test_article_detail_return_links_markup(client: TestClient, tmp_path: Path) -> None:
    db_path = tmp_path / "r120.sqlite3"
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/x.md', '返回测', 'S', 'B', 'hx', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    html = client.get(f"/articles/{aid}").text
    assert "workbenchReturnUrl" in html
    assert "applyWorkbenchReturnLinks" in html
    assert 'id="backWorkbench"' in html
    assert "wechat_workbench_section_hash" in html
