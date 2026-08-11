"""Adapter provenance is a fail-closed boundary for queued jobs and drafts."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from tests.conftest import make_test_config
from tests.test_web_upload import PNG
from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.base import DraftResult
from wechat_article_scheduler.draft_update import draft_content_fingerprint
from wechat_article_scheduler.schedule_assign import assign_article_schedule
from wechat_article_scheduler.scheduler import run_due_jobs


def _seed_due_job(db_path: Path, *, adapter_mode: str) -> tuple[int, int]:
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        article_id = int(
            conn.execute(
                """
                INSERT INTO articles (
                    source_path, title, summary, body, content_hash, status
                ) VALUES ('mode.md', 'Mode', 'Summary', 'Body', 'mode-hash', 'imported')
                """
            ).lastrowid
        )
        job_id = int(
            conn.execute(
                """
                INSERT INTO publish_jobs (
                    article_id, scheduled_at, status, adapter_mode
                ) VALUES (?, datetime('now', '-1 minute'), 'pending', ?)
                """,
                (article_id, adapter_mode),
            ).lastrowid
        )
        conn.commit()
    return article_id, job_id


@pytest.mark.parametrize(
    ("job_mode", "process_mode"),
    (("mock", "real"), ("real", "mock"), ("unknown", "mock")),
)
def test_due_job_mode_mismatch_stays_pending_before_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    job_mode: str,
    process_mode: str,
) -> None:
    db_path = tmp_path / f"{job_mode}-{process_mode}.sqlite3"
    _article_id, job_id = _seed_due_job(db_path, adapter_mode=job_mode)
    adapter_calls: list[str] = []

    def unexpected_adapter(_config):  # noqa: ANN001, ANN202
        adapter_calls.append("adapter")
        raise AssertionError("adapter construction would cross the mode boundary")

    monkeypatch.setattr(
        "wechat_article_scheduler.scheduler.domain.get_adapter",
        unexpected_adapter,
    )
    config = make_test_config(tmp_path, db_path, wechat_mode=process_mode)
    stats = run_due_jobs(config)

    assert stats["skipped_mode_mismatch"] == 1
    assert stats["processed"] == 0
    assert adapter_calls == []
    with db.connect(db_path) as conn:
        job = conn.execute(
            "SELECT status, adapter_mode, claim_token FROM publish_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        draft_count = conn.execute("SELECT COUNT(*) FROM wechat_drafts").fetchone()[0]
        event = conn.execute(
            """
            SELECT payload_json FROM events
            WHERE entity_id = ? AND event_type = 'adapter_mode_mismatch'
            ORDER BY id DESC LIMIT 1
            """,
            (job_id,),
        ).fetchone()
    assert dict(job) == {
        "status": "pending",
        "adapter_mode": job_mode,
        "claim_token": None,
    }
    assert draft_count == 0
    assert event is None


def test_explicit_reschedule_rearms_pending_job_in_current_mode(tmp_path: Path) -> None:
    db_path = tmp_path / "reschedule-mode.sqlite3"
    article_id, job_id = _seed_due_job(db_path, adapter_mode="mock")
    old_time = "2020-01-01T00:00:00"
    with db.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE publish_jobs
            SET scheduled_at = ?, retry_count = 2,
                next_retry_at = datetime('now', '+1 day')
            WHERE id = ?
            """,
            (old_time, job_id),
        )
        conn.commit()

    config = make_test_config(tmp_path, db_path, wechat_mode="real")
    scheduled_at = datetime.now().replace(microsecond=0) + timedelta(hours=2)
    result = assign_article_schedule(config, article_id, scheduled_at)
    assert result["created"] is False

    with db.connect(db_path) as conn:
        job = conn.execute(
            """
            SELECT scheduled_at, adapter_mode, retry_count, next_retry_at
            FROM publish_jobs WHERE id = ?
            """,
            (job_id,),
        ).fetchone()
    assert job["scheduled_at"] == scheduled_at.isoformat(timespec="seconds")
    assert job["adapter_mode"] == "real"
    assert job["retry_count"] == 0
    assert job["next_retry_at"] is None


def test_mode_is_rechecked_after_atomic_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "claim-race.sqlite3"
    _article_id, job_id = _seed_due_job(db_path, adapter_mode="mock")
    adapter_calls: list[str] = []

    def unexpected_adapter(_config):  # noqa: ANN001, ANN202
        adapter_calls.append("adapter")
        raise AssertionError("adapter must not be constructed")

    from wechat_article_scheduler.scheduler.claim import try_claim_job as real_claim

    def retag_then_claim(conn, claimed_job_id: int, token: str) -> bool:  # noqa: ANN001
        conn.execute(
            "UPDATE publish_jobs SET adapter_mode = 'real' WHERE id = ?",
            (claimed_job_id,),
        )
        return real_claim(conn, claimed_job_id, token)

    monkeypatch.setattr(
        "wechat_article_scheduler.scheduler.runtime.try_claim_job",
        retag_then_claim,
    )
    monkeypatch.setattr(
        "wechat_article_scheduler.scheduler.domain.get_adapter",
        unexpected_adapter,
    )
    stats = run_due_jobs(make_test_config(tmp_path, db_path, wechat_mode="mock"))
    assert stats["skipped_mode_mismatch"] == 1
    assert adapter_calls == []
    with db.connect(db_path) as conn:
        job = conn.execute(
            "SELECT status, adapter_mode, claim_token FROM publish_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
    assert dict(job) == {
        "status": "pending",
        "adapter_mode": "real",
        "claim_token": None,
    }


@pytest.mark.parametrize(
    ("prior_mode", "current_mode"),
    (("mock", "real"), ("real", "mock")),
)
def test_scheduler_never_reuses_opposite_mode_draft(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    prior_mode: str,
    current_mode: str,
) -> None:
    db_path = tmp_path / f"reuse-{prior_mode}-{current_mode}.sqlite3"
    db.init_db(db_path)
    fingerprint = draft_content_fingerprint(
        title="T", summary="S", body="Body", cover_path=None
    )
    with db.connect(db_path) as conn:
        article_id = int(
            conn.execute(
                """
                INSERT INTO articles (
                    source_path, title, summary, body, content_hash, status
                ) VALUES ('reuse.md', 'T', 'S', 'Body', 'reuse-hash', 'imported')
                """
            ).lastrowid
        )
        prior_job_id = int(
            conn.execute(
                """
                INSERT INTO publish_jobs (
                    article_id, scheduled_at, status, adapter_mode
                ) VALUES (?, datetime('now', '-2 minutes'), 'done', ?)
                """,
                (article_id, prior_mode),
            ).lastrowid
        )
        conn.execute(
            """
            INSERT INTO wechat_drafts (
                article_id, media_id, status, payload_json,
                adapter_mode, publish_job_id
            ) VALUES (?, ?, 'created', ?, ?, ?)
            """,
            (
                article_id,
                f"{prior_mode}_existing_media",
                json.dumps({"content_fingerprint": fingerprint}),
                prior_mode,
                prior_job_id,
            ),
        )
        current_job_id = int(
            conn.execute(
                """
                INSERT INTO publish_jobs (
                    article_id, scheduled_at, status, adapter_mode
                ) VALUES (?, datetime('now', '-1 minute'), 'pending', ?)
                """,
                (article_id, current_mode),
            ).lastrowid
        )
        conn.commit()

    create_calls: list[str] = []

    class MatchingAdapter:
        def create_draft(self, **_kwargs) -> DraftResult:
            create_calls.append(current_mode)
            return DraftResult(
                media_id=f"{current_mode}_new_media",
                raw_response={"created": True},
            )

    monkeypatch.setattr(
        "wechat_article_scheduler.scheduler.domain.get_adapter",
        lambda _config: MatchingAdapter(),
    )
    default_cover = tmp_path / "default.png"
    default_cover.write_bytes(PNG)
    config = make_test_config(
        tmp_path,
        db_path,
        wechat_mode=current_mode,
        wechat_app_id="test-app" if current_mode == "real" else "",
        wechat_app_secret="test-secret" if current_mode == "real" else "",
        wechat_default_thumb_path=str(default_cover),
    )
    stats = run_due_jobs(config)
    assert stats["processed"] == 1
    assert stats["draft_reused"] == 0
    assert create_calls == [current_mode]

    with db.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT media_id, adapter_mode, publish_job_id
            FROM wechat_drafts WHERE article_id = ? ORDER BY id
            """,
            (article_id,),
        ).fetchall()
    assert [dict(row) for row in rows] == [
        {
            "media_id": f"{prior_mode}_existing_media",
            "adapter_mode": prior_mode,
            "publish_job_id": prior_job_id,
        },
        {
            "media_id": f"{current_mode}_new_media",
            "adapter_mode": current_mode,
            "publish_job_id": current_job_id,
        },
    ]
