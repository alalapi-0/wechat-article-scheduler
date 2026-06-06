"""每周续排游标（Round 133）：避免 draft-only 完成后重复排同一批。"""

from __future__ import annotations

from typing import Any

# 文章排期状态（articles.schedule_state）
STATE_IMPORTED = "imported"
STATE_SCHEDULED_LOCAL = "scheduled_local"
STATE_REMOTE_DRAFT_READY = "remote_draft_ready"
STATE_SUBMITTED = "submitted"

# 已完成排期、不应再被 plan 选中的状态
EXCLUDED_SCHEDULE_STATES = frozenset(
    {STATE_SCHEDULED_LOCAL, STATE_REMOTE_DRAFT_READY, STATE_SUBMITTED}
)


def get_cursor(conn: Any, scope_key: str) -> int:
    row = conn.execute(
        "SELECT cursor_index FROM weekly_plan_cursor WHERE scope_key = ?",
        (scope_key,),
    ).fetchone()
    return int(row["cursor_index"]) if row else 0


def advance_cursor(conn: Any, scope_key: str, *, delta: int) -> int:
    current = get_cursor(conn, scope_key)
    new_index = current + int(delta)
    conn.execute(
        """
        INSERT INTO weekly_plan_cursor (scope_key, cursor_index, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(scope_key) DO UPDATE SET
            cursor_index = excluded.cursor_index,
            updated_at = excluded.updated_at
        """,
        (scope_key, new_index),
    )
    return new_index


def slice_articles_for_week(
    article_ids: list[int],
    cursor_index: int,
    *,
    max_items: int | None = None,
) -> tuple[list[int], int]:
    """从游标位置截取本批可排文章，返回 (slice, consumed_count)。"""
    if cursor_index >= len(article_ids):
        return [], 0
    remaining = article_ids[cursor_index:]
    if max_items is not None and max_items > 0:
        remaining = remaining[:max_items]
    return remaining, len(remaining)


def mark_article_schedule_state(conn: Any, article_id: int, state: str) -> None:
    conn.execute(
        "UPDATE articles SET schedule_state = ?, updated_at = datetime('now') WHERE id = ?",
        (state, int(article_id)),
    )
