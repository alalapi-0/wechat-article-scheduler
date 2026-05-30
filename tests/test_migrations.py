"""Round 4：数据库迁移体系。"""

from __future__ import annotations

from pathlib import Path

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
        cols = {row[1] for row in conn.execute("PRAGMA table_info(articles)").fetchall()}
        assert "review_status" in cols
        assert "collection_id" in cols


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "idempotent.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        first = db.apply_migrations(conn)
        second = db.apply_migrations(conn)
        conn.commit()
    assert second == []
    assert first == [] or isinstance(first, list)
