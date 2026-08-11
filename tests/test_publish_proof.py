"""人工发布 proof 记录。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.base import DraftResult
from wechat_article_scheduler.publish_proof import (
    ProofInput,
    cannot_mark_published_without_proof,
    mark_job_waiting_confirmation,
    proof_has_evidence,
    record_publish_proof,
)
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.scheduler import run_due_jobs
from tests.conftest import make_test_config
from tests.test_web_upload import PNG


def _seed_job(
    tmp_path: Path,
    *,
    status: str = "done",
    adapter_mode: str = "real",
    media_id: str = "real_media_001",
) -> tuple[object, int, int]:
    cfg = make_test_config(tmp_path, tmp_path / "p.sqlite3", wechat_mode=adapter_mode)
    db.init_db(cfg.database_path)
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('inbox/a.md', 'T', 'S', 'body', 'h1', 'imported')
            """
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
            VALUES (?, ?, ?, ?)
            """,
            (aid, (datetime.now() - timedelta(hours=1)).isoformat(), status, adapter_mode),
        )
        jid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """
            INSERT INTO wechat_drafts (
                article_id, media_id, status, payload_json,
                adapter_mode, publish_job_id
            ) VALUES (?, ?, 'created', '{}', ?, ?)
            """,
            (aid, media_id, adapter_mode, jid),
        )
        conn.commit()
    return cfg, int(aid), int(jid)


def test_proof_requires_evidence() -> None:
    assert not proof_has_evidence(ProofInput())
    assert proof_has_evidence(ProofInput(public_url="https://example.com/p"))


def test_real_done_job_waits_then_records_actual_publish_proof(tmp_path: Path) -> None:
    cfg, _aid, jid = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        assert mark_job_waiting_confirmation(conn, jid)["ok"]
        assert mark_job_waiting_confirmation(conn, jid)["already_waiting"] is True
        assert cannot_mark_published_without_proof("waiting_confirmation")
        bad = record_publish_proof(conn, jid, ProofInput())
        assert not bad["ok"]
        ok = record_publish_proof(
            conn,
            jid,
            ProofInput(public_url="https://example.com/article", confirmed_by="me"),
        )
        assert ok["ok"]
        row = conn.execute(
            "SELECT status FROM publish_jobs WHERE id = ?", (jid,)
        ).fetchone()
        assert row["status"] == "done"
        art = conn.execute("SELECT status FROM articles WHERE id = ?", (_aid,)).fetchone()
        assert art["status"] == "published"


def test_mock_and_incomplete_jobs_cannot_enter_publish_confirmation(tmp_path: Path) -> None:
    cfg, _aid, mock_job = _seed_job(
        tmp_path,
        adapter_mode="mock",
        media_id="mock_media_001",
    )
    with db.connect(cfg.database_path) as conn:
        rejected = mark_job_waiting_confirmation(conn, mock_job)
        assert rejected["ok"] is False
        conn.execute(
            "UPDATE publish_jobs SET adapter_mode = 'real', status = 'pending' WHERE id = ?",
            (mock_job,),
        )
        conn.execute(
            """
            UPDATE wechat_drafts
            SET media_id = 'real_media_002', adapter_mode = 'real'
            WHERE article_id = ?
            """,
            (_aid,),
        )
        conn.commit()
        assert mark_job_waiting_confirmation(conn, mock_job)["ok"] is False


def test_record_proof_rechecks_mock_waiting_eligibility(tmp_path: Path) -> None:
    cfg, _aid, jid = _seed_job(
        tmp_path,
        status="waiting_confirmation",
        adapter_mode="mock",
        media_id="mock_media_legacy",
    )
    with db.connect(cfg.database_path) as conn:
        result = record_publish_proof(
            conn,
            jid,
            ProofInput(public_url="https://example.com/not-real"),
        )
    assert result["ok"] is False


def test_mock_remote_draft_cannot_bypass_publish_confirmation(tmp_path: Path) -> None:
    cfg, _aid, jid = _seed_job(
        tmp_path,
        adapter_mode="mock",
        media_id="mock_local_media",
    )
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            "UPDATE publish_jobs SET source_kind = 'remote_draft', remote_media_id = ? WHERE id = ?",
            ("remote_media_looks_real", jid),
        )
        conn.commit()
        result = mark_job_waiting_confirmation(conn, jid)
    assert result["ok"] is False


def test_proof_requires_draft_linked_to_exact_real_job(tmp_path: Path) -> None:
    cfg, aid, first_job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        second_job_id = int(
            conn.execute(
                """
                INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
                VALUES (?, datetime('now'), 'done', 'real')
                """,
                (aid,),
            ).lastrowid
        )
        conn.commit()
        assert mark_job_waiting_confirmation(conn, second_job_id)["ok"] is False

        conn.execute(
            """
            INSERT INTO wechat_drafts (
                article_id, media_id, status, payload_json,
                adapter_mode, publish_job_id
            ) VALUES (?, 'real_second_media', 'created', '{}', 'real', ?)
            """,
            (aid, second_job_id),
        )
        conn.commit()
        assert mark_job_waiting_confirmation(conn, second_job_id)["ok"] is True
        assert first_job_id != second_job_id


def test_unknown_draft_provenance_is_never_publish_eligible(tmp_path: Path) -> None:
    cfg, _aid, jid = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            "UPDATE wechat_drafts SET adapter_mode = 'unknown' WHERE publish_job_id = ?",
            (jid,),
        )
        conn.commit()
        result = mark_job_waiting_confirmation(conn, jid)
    assert result["ok"] is False


def test_scheduler_real_draft_to_publish_proof_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "scheduler-proof.sqlite3"
    cover = tmp_path / "articles" / "covers" / "cover.png"
    cover.parent.mkdir(parents=True, exist_ok=True)
    cover.write_bytes(PNG)
    cfg = make_test_config(
        tmp_path,
        db_path,
        wechat_mode="real",
        wechat_app_id="test-app",
        wechat_app_secret="test-secret",
    )
    db.init_db(db_path)

    class FakeRealAdapter:
        def create_draft(self, **_kwargs) -> DraftResult:
            return DraftResult(media_id="real_scheduler_media", raw_response={"ok": True})

    monkeypatch.setattr(
        "wechat_article_scheduler.scheduler.domain.get_adapter",
        lambda _config: FakeRealAdapter(),
    )
    with db.connect(db_path) as conn:
        aid = int(
            conn.execute(
                "INSERT INTO articles "
                "(source_path, title, summary, body, content_hash, status, cover_path) "
                "VALUES ('a.md', '真实草稿', '摘要', '正文', 'proof-flow', 'imported', ?)",
                (str(cover),),
            ).lastrowid
        )
        jid = int(
            conn.execute(
                "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
                "VALUES (?, datetime('now', '-1 minute'), 'pending', 'real')",
                (aid,),
            ).lastrowid
        )
        conn.commit()

    assert run_due_jobs(cfg)["drafted"] == 1
    with db.connect(db_path) as conn:
        assert conn.execute(
            "SELECT status FROM publish_jobs WHERE id = ?", (jid,)
        ).fetchone()["status"] == "done"
        assert mark_job_waiting_confirmation(conn, jid)["ok"] is True
        assert record_publish_proof(
            conn,
            jid,
            ProofInput(public_url="https://mp.example.com/published"),
        )["ok"] is True
        assert conn.execute(
            "SELECT status FROM articles WHERE id = ?", (aid,)
        ).fetchone()["status"] == "published"


def test_api_proof_flow(tmp_path: Path) -> None:
    cfg, aid, jid = _seed_job(tmp_path)
    client = TestClient(create_app(cfg))
    r = client.post(f"/api/publish-jobs/{jid}/waiting-confirmation")
    assert r.json()["ok"]
    r2 = client.post(
        f"/api/publish-jobs/{jid}/proof",
        json={"public_url": "https://mp.example.com/1", "confirmed_by": "tester"},
    )
    assert r2.json()["ok"]
    detail = client.get(f"/api/articles/{aid}").json()
    assert detail.get("publish_proof") is None or detail["status"] == "published"
    wc = client.get("/api/waiting-confirmation").json()
    assert wc["count"] == 0
    assert client.get(f"/api/publish-jobs/{jid}/proof").json()["proof"] is not None
    assert detail["status"] == "published"
