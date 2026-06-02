"""Round 125：作品卡导出下拉（generic + manual_export 平台）。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.manual_export.platforms.registry import (
    SUPPORTED_PLATFORMS,
)
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r125.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def _insert_article(db_path: Path) -> int:
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/r125.md', '导出下拉测', 'S', '正文', 'h125', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    return aid


def test_manual_export_platforms_api(client: TestClient) -> None:
    data = client.get("/api/manual-export/platforms").json()
    ids = {p["id"] for p in data.get("platforms", [])}
    assert "generic" in ids
    assert ids == set(SUPPORTED_PLATFORMS.keys())


def test_export_outbox_zhihu_platform(client: TestClient, tmp_path: Path) -> None:
    cfg_db = tmp_path / "r125.sqlite3"
    aid = _insert_article(cfg_db)
    r = client.post(f"/api/articles/{aid}/export-outbox?platform=zhihu").json()
    assert r.get("ok") is True
    assert r.get("relative_path")


def test_home_export_dropdown_markup(client: TestClient) -> None:
    html = client.get("/").text
    assert "loadManualExportPlatforms" in html
    assert "workExportMenuHtml" in html
    assert 'class="export-drop"' in html
    assert "export-drop-menu" in html
    assert "/api/manual-export/platforms" in html
    assert "exportOutboxArticle" in html
