"""SQLite 连接与 schema 初始化。"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    body TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'inbox',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_content_hash ON articles(content_hash);

CREATE TABLE IF NOT EXISTS publish_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL REFERENCES articles(id),
    scheduled_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    adapter_mode TEXT NOT NULL DEFAULT 'mock',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS wechat_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL REFERENCES articles(id),
    media_id TEXT,
    status TEXT NOT NULL DEFAULT 'created',
    payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    event_type TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    """打开数据库并返回连接（Row 工厂便于按列名访问）。"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """轻量 schema 迁移（新增列等）。"""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(publish_jobs)").fetchall()}
    if "retry_count" not in cols:
        conn.execute(
            "ALTER TABLE publish_jobs ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0"
        )


def init_db(db_path: Path) -> None:
    """创建表结构（幂等）。"""
    with connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        _migrate_schema(conn)
        conn.commit()


def log_event(
    conn: sqlite3.Connection,
    *,
    entity_type: str,
    entity_id: int | None,
    event_type: str,
    payload: str | None = None,
) -> None:
    """写入审计事件（不记录 token）。"""
    conn.execute(
        "INSERT INTO events (entity_type, entity_id, event_type, payload_json) VALUES (?, ?, ?, ?)",
        (entity_type, entity_id, event_type, payload),
    )
    conn.commit()


def fetch_one(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    cur = conn.execute(sql, params)
    return cur.fetchone()
