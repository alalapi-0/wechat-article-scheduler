"""不可变操作运行记录（sync / delete / plan 审计，Round 135）。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any


def new_run_id(operation: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{operation}-{stamp}-{uuid.uuid4().hex[:8]}"


def start_operation_run(
    conn: Any,
    *,
    operation: str,
    dry_run: bool = False,
    resume_run_id: str | None = None,
    max_items: int | None = None,
    manifest: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> str:
    rid = run_id or new_run_id(operation)
    conn.execute(
        """
        INSERT INTO operation_runs
            (operation, run_id, dry_run, resume_run_id, max_items, status, manifest_json)
        VALUES (?, ?, ?, ?, ?, 'running', ?)
        """,
        (
            operation,
            rid,
            1 if dry_run else 0,
            resume_run_id,
            max_items,
            json.dumps(manifest or {}, ensure_ascii=False),
        ),
    )
    return rid


def complete_operation_run(
    conn: Any,
    run_id: str,
    *,
    status: str,
    results: dict[str, Any],
) -> None:
    conn.execute(
        """
        UPDATE operation_runs
        SET status = ?, results_json = ?, completed_at = datetime('now')
        WHERE run_id = ?
        """,
        (status, json.dumps(results, ensure_ascii=False), run_id),
    )


def get_operation_run(conn: Any, run_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM operation_runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if row is None:
        return None
    out = dict(row)
    for key in ("manifest_json", "results_json"):
        raw = out.get(key)
        if raw:
            try:
                out[key.replace("_json", "")] = json.loads(raw)
            except json.JSONDecodeError:
                out[key.replace("_json", "")] = raw
    return out
