"""Round 117：作品库合集筛选 localStorage 持久化。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r117.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def test_home_collection_filter_storage_markup(client: TestClient) -> None:
    html = client.get("/").text
    assert "wechat_workbench_collection_slug" in html
    assert "initCollectionFilter" in html
    assert "persistCollectionSlug" in html
    assert 'id="collectionFilter"' in html
    assert "全部合集" in html


def test_articles_filtered_by_collection_slug(client: TestClient, tmp_path: Path) -> None:
    db_path = tmp_path / "r117.sqlite3"
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO collections (slug, name, description) VALUES ('demo', '演示', '')",
        )
        cid = int(conn.execute("SELECT id FROM collections WHERE slug='demo'").fetchone()[0])
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status, collection_id) "
            "VALUES ('inbox/a.md', '合集A', 'S', 'B', 'h1', 'imported', ?)",
            (cid,),
        )
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/b.md', '无合集', 'S', 'B', 'h2', 'imported')",
        )
        conn.commit()
    all_arts = client.get("/api/articles").json()
    demo_arts = client.get("/api/articles?collection_slug=demo").json()
    assert len(all_arts) >= 2
    assert len(demo_arts) == 1
    assert demo_arts[0]["title"] == "合集A"
