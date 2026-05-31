"""Web 启动时应自动应用迁移，避免旧库缺列导致 500。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.config import load_config
from wechat_article_scheduler.web.app import create_app


def test_create_app_applies_deleted_at_migration(tmp_path: Path) -> None:
    """模拟未跑 006 的旧库：仅 create_app 后 overview 仍应返回 JSON。"""
    cfg = load_config()
    db_path = tmp_path / "legacy.sqlite3"
    with db.connect(db_path) as conn:
        conn.executescript(db.SCHEMA_SQL)
        conn.commit()
    cols_before = {
        row[1]
        for row in sqlite3.connect(db_path).execute("PRAGMA table_info(articles)")
    }
    assert "deleted_at" not in cols_before

    legacy_cfg = type(cfg)(
        **{**cfg.__dict__, "database_path": db_path}
    )
    client = TestClient(create_app(legacy_cfg))
    r = client.get("/api/overview")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")

    cols_after = {
        row[1]
        for row in sqlite3.connect(db_path).execute("PRAGMA table_info(articles)")
    }
    assert "deleted_at" in cols_after
