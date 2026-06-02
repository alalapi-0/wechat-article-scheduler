"""Round 126：文章详情页导出下拉（与 round_125 同款）。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r126.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def _insert_article(db_path: Path) -> int:
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/r126.md', '详情导出测', 'S', '正文', 'h126', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    return aid


def test_detail_page_export_dropdown_markup(client: TestClient, tmp_path: Path) -> None:
    aid = _insert_article(tmp_path / "r126.sqlite3")
    html = client.get(f"/articles/{aid}").text
    assert "loadManualExportPlatforms" in html
    assert "detailExportMenuHtml" in html
    assert 'id="exportOutboxSlot"' in html
    assert 'class="export-drop"' in html
    assert "/api/manual-export/platforms" in html
    assert "btnExportZhihu" not in html
    assert "btnExportDouban" not in html
    assert "doExportOutbox" in html


def test_detail_export_outbox_douban(client: TestClient, tmp_path: Path) -> None:
    aid = _insert_article(tmp_path / "r126.sqlite3")
    r = client.post(f"/api/articles/{aid}/export-outbox?platform=douban").json()
    assert r.get("ok") is True
    assert r.get("relative_path")
