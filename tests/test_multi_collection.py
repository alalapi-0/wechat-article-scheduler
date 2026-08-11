"""多合集内容库。"""

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
from wechat_article_scheduler.filesystem_safety import UnsafePathError
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


def test_collection_discovery_uses_safe_listing_and_rejects_linked_root(
    multi_config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "glob", lambda _path, _pattern: (_ for _ in ()).throw(AssertionError("glob")))
    assert [item.slug for item in discover_collection_configs(multi_config.root)] == ["serial"]

    outside = tmp_path / "outside-collections"
    (outside / "leaked").mkdir(parents=True)
    (outside / "leaked" / "collection.yaml").write_text("slug: leaked\n", encoding="utf-8")
    linked_root = tmp_path / "linked-root"
    (linked_root / "content").mkdir(parents=True)
    (linked_root / "content" / "collections").symlink_to(outside, target_is_directory=True)
    assert discover_collection_configs(linked_root) == []


def test_collection_discovery_reads_yaml_from_original_held_directory(
    multi_config, monkeypatch: pytest.MonkeyPatch
) -> None:
    from wechat_article_scheduler import filesystem_safety as fs

    base = multi_config.root / "content" / "collections"
    detached = multi_config.root / "detached-collections"
    original_list = fs.DirectoryHandle.list_names
    swapped = {"done": False}

    def list_then_replace(handle):
        names = original_list(handle)
        if handle.path == base.absolute() and not swapped["done"]:
            swapped["done"] = True
            base.rename(detached)
            replacement = base / "serial"
            replacement.mkdir(parents=True)
            (replacement / "collection.yaml").write_text(
                "slug: serial\nname: replacement-must-not-be-read\n", encoding="utf-8"
            )
        return names

    monkeypatch.setattr(fs.DirectoryHandle, "list_names", list_then_replace)
    configs = discover_collection_configs(multi_config.root)
    assert [item.name for item in configs] == ["连载专栏"]


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


def test_collection_config_rejects_traversal_and_linked_yaml(tmp_path: Path) -> None:
    base = tmp_path / "content" / "collections" / "bad"
    base.mkdir(parents=True)
    yaml_path = base / "collection.yaml"
    yaml_path.write_text("slug: ../escape\ninbox_dir: ../../outside\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_collection_yaml(yaml_path, root=tmp_path)

    outside = tmp_path / "outside.yaml"
    outside.write_text("slug: linked\n", encoding="utf-8")
    yaml_path.unlink()
    yaml_path.symlink_to(outside)
    with pytest.raises(UnsafePathError):
        load_collection_yaml(yaml_path, root=tmp_path)


def test_collections_get_does_not_register_discovered_yaml(multi_config) -> None:
    from fastapi.testclient import TestClient
    from wechat_article_scheduler.web import create_app

    with db.connect(multi_config.database_path) as conn:
        before = conn.execute("SELECT COUNT(*) FROM collections").fetchone()[0]
    response = TestClient(create_app(multi_config)).get("/api/collections")
    assert response.status_code == 200
    assert any(item["slug"] == "serial" for item in response.json()["collections"])
    with db.connect(multi_config.database_path) as conn:
        after = conn.execute("SELECT COUNT(*) FROM collections").fetchone()[0]
    assert after == before
