"""Round 63：多合集内容库。"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from wechat_article_scheduler import db
from wechat_article_scheduler.content_library import (
    discover_collection_configs,
    list_collections_summary,
    sync_discovered_collections,
)
from wechat_article_scheduler.content_library.collection_config import load_collection_yaml
from wechat_article_scheduler.scanner import scan_inbox
from tests.conftest import make_test_config


@pytest.fixture
def multi_config(tmp_path: Path):
    db_path = tmp_path / "multi.sqlite3"
    db.init_db(db_path)
    root = tmp_path
    inbox = root / "articles" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "root.md").write_text("# 根目录\n\n正文。", encoding="utf-8")
    coll_base = root / "content" / "collections" / "serial"
    coll_inbox = coll_base / "inbox"
    coll_inbox.mkdir(parents=True)
    (coll_inbox / "ep01.md").write_text("# 第一话\n\n合集正文。", encoding="utf-8")
    (coll_base / "collection.yaml").write_text(
        yaml.safe_dump(
            {
                "slug": "serial",
                "name": "连载专栏",
                "description": "测试合集",
                "title_template": "【{title}】",
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return make_test_config(root, db_path)


def test_discover_collection_yaml(multi_config) -> None:
    configs = discover_collection_configs(multi_config.root)
    assert len(configs) == 1
    assert configs[0].slug == "serial"
    assert configs[0].name == "连载专栏"


def test_scan_imports_default_and_collection(multi_config) -> None:
    stats = scan_inbox(multi_config)
    assert stats["imported"] == 2
    coll = stats.get("collections") or {}
    assert coll.get("serial", {}).get("imported") == 1
    with db.connect(multi_config.database_path) as conn:
        rows = conn.execute(
            """
            SELECT COALESCE(c.slug, 'default') AS slug, a.title
            FROM articles a
            LEFT JOIN collections c ON c.id = a.collection_id
            ORDER BY a.id
            """
        ).fetchall()
    slugs = [r["slug"] for r in rows]
    assert "default" in slugs
    assert "serial" in slugs
    serial_titles = [r["title"] for r in rows if r["slug"] == "serial"]
    assert serial_titles[0].startswith("【")


def test_collections_api_filter(multi_config) -> None:
    from fastapi.testclient import TestClient
    from wechat_article_scheduler.web import create_app

    scan_inbox(multi_config)
    client = TestClient(create_app(multi_config))
    cols = client.get("/api/collections").json()
    assert any(c["slug"] == "serial" for c in cols["collections"])
    serial_only = client.get("/api/articles", params={"collection_slug": "serial"}).json()
    assert len(serial_only) == 1
    assert serial_only[0]["collection_slug"] == "serial"


def test_legacy_inbox_subdir_compat(multi_config) -> None:
    legacy = multi_config.root / "articles" / "inbox" / "legacybox"
    legacy.mkdir(parents=True)
    (legacy / "old.md").write_text("# 旧目录\n\n文。", encoding="utf-8")
    lb = multi_config.root / "content" / "collections" / "legacybox"
    lb.mkdir(parents=True)
    (lb / "collection.yaml").write_text(
        yaml.safe_dump({"slug": "legacybox", "name": "旧目录合集"}, allow_unicode=True),
        encoding="utf-8",
    )
    stats = scan_inbox(multi_config)
    assert stats["imported"] >= 1
    with db.connect(multi_config.database_path) as conn:
        sync_discovered_collections(multi_config, conn)
        summary = list_collections_summary(conn)
    assert any(s["slug"] == "legacybox" for s in summary)
