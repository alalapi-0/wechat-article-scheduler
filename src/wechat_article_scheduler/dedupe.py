"""按 rules.yaml 对文章去重。"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from wechat_article_scheduler.parser import ParsedArticle


def normalize_title(title: str) -> str:
    """标题规范化，便于比对。"""
    return " ".join(title.strip().lower().split())


def find_existing_article(
    conn: sqlite3.Connection,
    article: ParsedArticle,
    rules: dict[str, Any],
) -> tuple[int | None, str]:
    """
    查找与待入库作品重复的已有记录。

    返回 (已有文章 id, 原因说明)；无重复时 id 为 None。
    """
    dedupe = rules.get("dedupe", {}) if isinstance(rules.get("dedupe"), dict) else {}

    if dedupe.get("by_content_hash", True):
        row = conn.execute(
            "SELECT id, status FROM articles WHERE content_hash = ? LIMIT 1",
            (article.content_hash,),
        ).fetchone()
        if row is not None:
            return int(row["id"]), f"content_hash 已存在 (id={row['id']}, status={row['status']})"

    if dedupe.get("by_normalized_title", True):
        norm = normalize_title(article.title)
        rows = conn.execute(
            "SELECT id, title, status FROM articles WHERE status != 'rejected'",
        ).fetchall()
        for row in rows:
            if normalize_title(row["title"]) == norm:
                return int(row["id"]), f"规范化标题重复 (id={row['id']})"

    return None, ""


def is_duplicate(
    conn: sqlite3.Connection,
    article: ParsedArticle,
    rules: dict[str, Any],
) -> tuple[bool, str]:
    """
    判断是否应跳过入库。

    返回 (是否重复, 原因说明)。
    """
    existing_id, reason = find_existing_article(conn, article, rules)
    return existing_id is not None, reason
