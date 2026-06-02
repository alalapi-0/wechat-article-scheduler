"""人工确认与 proof_of_publish（Round 19）。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig

WAITING_CONFIRMATION = "waiting_confirmation"
PROOF_REQUIRED_STATUSES = frozenset({WAITING_CONFIRMATION})


@dataclass(frozen=True)
class ProofInput:
    screenshot_path: str | None = None
    public_url: str | None = None
    confirmed_by: str | None = None
    note: str | None = None


def proof_has_evidence(proof: ProofInput) -> bool:
    return bool((proof.public_url or "").strip() or (proof.screenshot_path or "").strip())


def _job_row(conn: Any, job_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, article_id, status FROM publish_jobs WHERE id = ?",
        (job_id,),
    ).fetchone()
    return dict(row) if row else None


def mark_job_waiting_confirmation(conn: Any, job_id: int) -> dict[str, Any]:
    """将任务置为待人工确认（browser_assist / manual_export 出口）。"""
    job = _job_row(conn, job_id)
    if not job:
        return {"ok": False, "error": "任务不存在"}
    if job["status"] in ("cancelled", "done"):
        return {"ok": False, "error": f"当前状态不可改为待确认：{job['status']}"}
    conn.execute(
        """
        UPDATE publish_jobs
        SET status = ?, claim_token = NULL, claimed_at = NULL,
            next_retry_at = NULL, updated_at = datetime('now')
        WHERE id = ?
        """,
        (WAITING_CONFIRMATION, job_id),
    )
    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=job_id,
        event_type="waiting_confirmation",
        payload=json.dumps({"article_id": job["article_id"]}, ensure_ascii=False),
    )
    conn.commit()
    return {"ok": True, "job_id": job_id, "status": WAITING_CONFIRMATION}


def get_proof_for_job(conn: Any, job_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id, publish_job_id, article_id, screenshot_path, public_url,
               confirmed_by, confirmed_at, note, created_at
        FROM publish_proofs WHERE publish_job_id = ?
        """,
        (job_id,),
    ).fetchone()
    return dict(row) if row else None


def submit_publish_proof(conn: Any, job_id: int, proof: ProofInput) -> dict[str, Any]:
    """提交 proof；若任务为 waiting_confirmation 则完成发布并更新文章状态。"""
    job = _job_row(conn, job_id)
    if not job:
        return {"ok": False, "error": "任务不存在"}
    if not proof_has_evidence(proof):
        return {"ok": False, "error": "需提供公开链接或截图路径至少一项"}
    confirmed_by = (proof.confirmed_by or "").strip() or "local_user"
    if job["status"] not in PROOF_REQUIRED_STATUSES:
        if job["status"] == "done" and get_proof_for_job(conn, job_id):
            return {"ok": True, "job_id": job_id, "already_recorded": True}
        return {
            "ok": False,
            "error": f"仅 waiting_confirmation 任务需 proof 后完成，当前：{job['status']}",
        }

    conn.execute(
        """
        INSERT INTO publish_proofs (
            publish_job_id, article_id, screenshot_path, public_url,
            confirmed_by, confirmed_at, note
        ) VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
        ON CONFLICT(publish_job_id) DO UPDATE SET
            screenshot_path = excluded.screenshot_path,
            public_url = excluded.public_url,
            confirmed_by = excluded.confirmed_by,
            confirmed_at = datetime('now'),
            note = excluded.note
        """,
        (
            job_id,
            job["article_id"],
            (proof.screenshot_path or "").strip() or None,
            (proof.public_url or "").strip() or None,
            confirmed_by,
            (proof.note or "").strip() or None,
        ),
    )
    conn.execute(
        """
        UPDATE publish_jobs
        SET status = 'done', updated_at = datetime('now')
        WHERE id = ?
        """,
        (job_id,),
    )
    conn.execute(
        """
        UPDATE articles SET status = 'published', updated_at = datetime('now')
        WHERE id = ?
        """,
        (job["article_id"],),
    )
    payload = {
        "job_id": job_id,
        "article_id": job["article_id"],
        "public_url": (proof.public_url or "").strip() or None,
        "screenshot_path": (proof.screenshot_path or "").strip() or None,
        "confirmed_by": confirmed_by,
    }
    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=job_id,
        event_type="proof_submitted",
        payload=json.dumps(payload, ensure_ascii=False),
    )
    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=job_id,
        event_type="job_done",
        payload=json.dumps({"via": "proof_of_publish"}, ensure_ascii=False),
    )
    conn.commit()
    return {"ok": True, "job_id": job_id, "article_id": job["article_id"], "status": "done"}


def enrich_waiting_confirmation_item(
    item: dict[str, Any],
    config: AppConfig | None = None,
) -> dict[str, Any]:
    from wechat_article_scheduler.review.proof_quick import quick_proof_allowed
    from wechat_article_scheduler.web.schedule_display import format_scheduled_at

    out = dict(item)
    aid = int(out["article_id"])
    out["article_detail_url"] = f"/articles/{aid}"
    out["proof_form_url"] = f"/articles/{aid}#proof"
    out["scheduled_at_label"] = format_scheduled_at(out.get("scheduled_at"))
    has_proof = bool(out.get("has_proof"))
    allow_quick = quick_proof_allowed(config) if config is not None else True
    out["quick_proof_available"] = allow_quick and not has_proof
    out["status"] = WAITING_CONFIRMATION
    out["status_label"] = "待人工确认"
    return out


def list_waiting_confirmation(
    conn: Any,
    *,
    limit: int = 50,
    config: AppConfig | None = None,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT j.id AS job_id, j.article_id, j.scheduled_at, j.updated_at,
               a.title AS article_title, a.status AS article_status
        FROM publish_jobs j
        JOIN articles a ON a.id = j.article_id
        WHERE j.status = ?
        ORDER BY j.updated_at DESC
        LIMIT ?
        """,
        (WAITING_CONFIRMATION, limit),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["has_proof"] = get_proof_for_job(conn, int(item["job_id"])) is not None
        out.append(enrich_waiting_confirmation_item(item, config))
    return out


def cannot_mark_published_without_proof(job_status: str | None) -> bool:
    return (job_status or "").strip().lower() in PROOF_REQUIRED_STATUSES
