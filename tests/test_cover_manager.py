"""Round 61：封面资产扫描、绑定与孤儿清理。"""

from __future__ import annotations

from pathlib import Path

import pytest

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.cover_assets.manager import (
    bind_covers_by_stem,
    cleanup_orphan_covers,
    list_orphan_covers,
    repair_invalid_cover_paths,
    scan_cover_assets,
)
from tests.conftest import make_test_config


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    db_path = tmp_path / "cover.sqlite3"
    db.init_db(db_path)
    covers = tmp_path / "articles" / "covers"
    covers.mkdir(parents=True)
    cfg = make_test_config(tmp_path, db_path)
    return cfg


def test_bind_covers_by_stem(app_config: AppConfig) -> None:
    cover = app_config.covers_dir / "chapter1.jpg"
    cover.write_bytes(b"\xff\xd8\xff" + b"\x00" * 8)
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(app_config.inbox_dir / "chapter1.md"), "第一章", "", "正文", "h1", "imported"),
        )
        conn.commit()
        report = bind_covers_by_stem(app_config, conn)
        row = conn.execute("SELECT cover_path FROM articles").fetchone()
    assert report["bound"] == 1
    assert row["cover_path"] == str(cover)


def test_repair_invalid_cover_path(app_config: AppConfig) -> None:
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status, cover_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("/tmp/x.md", "X", "", "", "hx", "imported", "/no/such/cover.jpg"),
        )
        conn.commit()
        out = repair_invalid_cover_paths(app_config, conn)
        row = conn.execute("SELECT cover_path FROM articles").fetchone()
    assert out["cleared"] == 1
    assert row["cover_path"] == ""


def test_orphan_covers_across_directories(app_config: AppConfig) -> None:
    orphan = app_config.root / "cover_assets" / "unused.png"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_bytes(b"\x89PNG")
    with db.connect(app_config.database_path) as conn:
        items = list_orphan_covers(app_config, conn)
    assert any(i["name"] == "unused.png" for i in items)


def test_cleanup_orphan_covers(app_config: AppConfig) -> None:
    orphan = app_config.covers_dir / "gone.jpg"
    orphan.write_bytes(b"\xff\xd8\xff" + b"\x00" * 8)

    def _unlink(cfg: AppConfig, rel: str) -> bool:
        path = cfg.root / rel if not Path(rel).is_absolute() else Path(rel)
        if path.is_file():
            path.unlink()
            return True
        return False

    with db.connect(app_config.database_path) as conn:
        out = cleanup_orphan_covers(app_config, conn, unlink=_unlink)
    assert out["removed"] == 1
    assert not orphan.exists()


def test_covers_scan_api(app_config: AppConfig) -> None:
    from fastapi.testclient import TestClient
    from wechat_article_scheduler.web import create_app

    client = TestClient(create_app(app_config))
    r = client.get("/api/covers/scan")
    assert r.status_code == 200
    assert "human" in r.json()
    assert "asset_count" in r.json()


def test_scan_cover_assets_report(app_config: AppConfig) -> None:
    (app_config.covers_dir / "a.jpg").write_bytes(b"\xff\xd8\xff" + b"\x00" * 8)
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(app_config.inbox_dir / "a.md"), "A", "", "", "ha", "imported"),
        )
        conn.commit()
        report = scan_cover_assets(app_config, conn)
    assert report["asset_count"] >= 1
    assert report["bindable_count"] >= 1
