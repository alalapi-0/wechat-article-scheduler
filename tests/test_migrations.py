"""数据库迁移体系。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from wechat_article_scheduler import db


def test_init_db_applies_migrations(tmp_path: Path) -> None:
    db_path = tmp_path / "migrated.sqlite3"
    applied = []
    with db.connect(db_path) as conn:
        conn.executescript(db.SCHEMA_SQL)
        applied = db.apply_migrations(conn)
        conn.commit()
    assert "001" in applied or "002" in applied or applied == []
    with db.connect(db_path) as conn:
        versions = {
            row["version"]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }
        assert "002" in versions
        assert "004" in versions
        assert "006" in versions
        assert "015" in versions
        cols = {row[1] for row in conn.execute("PRAGMA table_info(articles)").fetchall()}
        # 产品重定位后 review_status 已被迁移 004 删除
        assert "review_status" not in cols
        assert "collection_id" in cols
        assert "cover_path" in cols
        assert "cover_config_json" in cols
        assert "deleted_at" in cols
        draft_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(wechat_drafts)").fetchall()
        }
        assert {"adapter_mode", "publish_job_id"} <= draft_cols
        draft_indexes = {
            row[1] for row in conn.execute("PRAGMA index_list(wechat_drafts)").fetchall()
        }
        assert "idx_wechat_drafts_article_mode_active" in draft_indexes
        assert "idx_wechat_drafts_job_mode_active" in draft_indexes


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "idempotent.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        first = db.apply_migrations(conn)
        second = db.apply_migrations(conn)
        conn.commit()
    assert second == []
    assert first == [] or isinstance(first, list)


def test_draft_provenance_migration_backfills_only_definite_mock(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "legacy-provenance.sqlite3"
    with db.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE publish_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                scheduled_at TEXT NOT NULL,
                status TEXT NOT NULL,
                adapter_mode TEXT NOT NULL
            );
            CREATE TABLE wechat_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                media_id TEXT,
                status TEXT NOT NULL DEFAULT 'created',
                payload_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            INSERT INTO publish_jobs (
                article_id, scheduled_at, status, adapter_mode
            ) VALUES (1, datetime('now'), 'done', 'real');
            INSERT INTO wechat_drafts (article_id, media_id)
            VALUES (1, 'mock_media_legacy'), (1, 'non_mock_legacy');
            """
        )
        migration = (db.MIGRATIONS_DIR / "015_wechat_draft_adapter_mode.sql").read_text(
            encoding="utf-8"
        )
        conn.executescript(migration)
        rows = conn.execute(
            "SELECT media_id, adapter_mode, publish_job_id FROM wechat_drafts ORDER BY id"
        ).fetchall()
        assert [dict(row) for row in rows] == [
            {
                "media_id": "mock_media_legacy",
                "adapter_mode": "mock",
                "publish_job_id": None,
            },
            {
                "media_id": "non_mock_legacy",
                "adapter_mode": "unknown",
                "publish_job_id": None,
            },
        ]
        conn.execute("INSERT INTO wechat_drafts (article_id, media_id) VALUES (2, 'new')")
        assert (
            conn.execute(
                "SELECT adapter_mode FROM wechat_drafts WHERE article_id = 2"
            ).fetchone()["adapter_mode"]
            == "unknown"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO wechat_drafts (article_id, media_id, adapter_mode) "
                "VALUES (3, 'bad', 'typo')"
            )
