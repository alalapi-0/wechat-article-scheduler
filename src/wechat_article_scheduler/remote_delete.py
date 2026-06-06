"""远端草稿批量删除（稳定 media_id、清单、审计，Round 135）。"""

from __future__ import annotations

import json
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters import get_adapter
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.operation_runs import (
    complete_operation_run,
    get_operation_run,
    start_operation_run,
)
from wechat_article_scheduler.remote_sync import list_remote_mirrors, sync_remote_drafts


def build_delete_manifest(
    conn: Any,
    media_ids: list[str],
    *,
    remote_type: str = "draft",
) -> dict[str, Any]:
    """生成删除影响预览（按稳定 media_id，禁止按标题删除）。"""
    items: list[dict[str, Any]] = []
    for mid in media_ids:
        row = conn.execute(
            """
            SELECT media_id, title, update_time, sync_status, last_seen_at
            FROM remote_content_mirror
            WHERE remote_type = ? AND media_id = ?
            """,
            (remote_type, mid),
        ).fetchone()
        if row is None:
            items.append(
                {
                    "media_id": mid,
                    "found": False,
                    "title": None,
                    "warning": "镜像中未找到该 media_id，仍将尝试按 ID 删除",
                }
            )
        else:
            items.append(
                {
                    "media_id": mid,
                    "found": True,
                    "title": row["title"],
                    "update_time": row["update_time"],
                    "last_seen_at": row["last_seen_at"],
                    "sync_status": row["sync_status"],
                }
            )
    return {
        "count": len(items),
        "items": items,
        "policy": "仅按稳定 media_id 删除，禁止按标题匹配",
        "concurrency": 1,
    }


def execute_remote_delete(
    config: AppConfig,
    media_ids: list[str],
    *,
    dry_run: bool = False,
    resume_run_id: str | None = None,
    max_items: int | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    """
    逐条删除远端草稿（并发 1），支持续跑跳过已成功项。
    """
    if not confirmed and not dry_run:
        return {"ok": False, "error": "需要 confirmed=true 才能执行删除"}
    ids = list(dict.fromkeys(media_ids))
    if max_items is not None and max_items > 0:
        ids = ids[: max_items]

    adapter = get_adapter(config)
    results: list[dict[str, Any]] = []
    skipped_success = 0

    with db.connect(config.database_path) as conn:
        run_id = start_operation_run(
            conn,
            operation="remote_delete",
            dry_run=dry_run,
            resume_run_id=resume_run_id,
            max_items=max_items,
            manifest=build_delete_manifest(conn, ids),
        )
        conn.commit()

        prior_success: set[str] = set()
        if resume_run_id:
            prior = get_operation_run(conn, resume_run_id)
            if prior and prior.get("results"):
                for item in prior["results"].get("items", []):
                    if item.get("ok"):
                        prior_success.add(str(item.get("media_id")))

        for mid in ids:
            if mid in prior_success:
                skipped_success += 1
                results.append({"media_id": mid, "ok": True, "skipped": True, "reason": "prior_success"})
                continue
            if dry_run:
                results.append({"media_id": mid, "ok": True, "dry_run": True})
                continue
            try:
                resp = adapter.delete_draft(mid)
                ok = int(resp.get("errcode", 0) or 0) == 0
                results.append({"media_id": mid, "ok": ok, "response": {"errcode": resp.get("errcode")}})
                if ok:
                    conn.execute(
                        """
                        UPDATE remote_content_mirror
                        SET sync_status = 'deleted', updated_at = datetime('now')
                        WHERE remote_type = 'draft' AND media_id = ?
                        """,
                        (mid,),
                    )
            except Exception as exc:  # noqa: BLE001
                results.append({"media_id": mid, "ok": False, "error": str(exc)[:200]})

        success_count = sum(1 for r in results if r.get("ok"))
        stats = {
            "run_id": run_id,
            "dry_run": dry_run,
            "requested": len(ids),
            "success_count": success_count,
            "failure_count": len(ids) - success_count - skipped_success,
            "skipped_prior": skipped_success,
            "items": results,
        }
        if not dry_run:
            complete_operation_run(conn, run_id, status="completed", results=stats)
            db.log_event(
                conn,
                entity_type="remote_delete",
                entity_id=None,
                event_type="batch_delete",
                payload=json.dumps(
                    {"run_id": run_id, "success": success_count, "total": len(ids)},
                    ensure_ascii=False,
                ),
            )
            sync_remote_drafts(config, run_id=run_id)
        else:
            complete_operation_run(conn, run_id, status="dry_run", results=stats)
        conn.commit()

    return {"ok": True, **stats}
