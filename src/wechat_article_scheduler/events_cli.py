"""Round 2：查询审计事件。"""

from __future__ import annotations

import sqlite3

from wechat_article_scheduler.config import AppConfig


def list_events(config: AppConfig, limit: int = 20) -> list[sqlite3.Row]:
    """返回最近事件（不含 token）。"""
    with sqlite3.connect(config.database_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, entity_type, entity_id, event_type, payload_json, created_at "
            "FROM events ORDER BY id DESC LIMIT ?",
            (max(1, limit),),
        )
        return cur.fetchall()
