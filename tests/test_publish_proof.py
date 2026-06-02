"""Round 74 / 收敛 Round 19：proof_of_publish 记录。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.review.proof import (
    ProofInput,
    cannot_mark_published_without_proof,
    mark_job_waiting_confirmation,
    proof_has_evidence,
    submit_publish_proof,
)
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "proof_of_publish.md"


def _seed_job(tmp_path: Path) -> tuple[Any, int, int]:
    cfg = make_test_config(tmp_path, tmp_path / "p.sqlite3")
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
            VALUES (?, ?, 'pending', 'mock')
            """,
            (aid, (datetime.now() - timedelta(hours=1)).isoformat()),
        )
        jid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
    return cfg, int(aid), int(jid)


def test_proof_requires_evidence() -> None:
    assert not proof_has_evidence(ProofInput())
    assert proof_has_evidence(ProofInput(public_url="https://example.com/p"))


def test_waiting_confirmation_blocks_without_proof(tmp_path: Path) -> None:
    cfg, _aid, jid = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        assert mark_job_waiting_confirmation(conn, jid)["ok"]
        assert cannot_mark_published_without_proof("waiting_confirmation")
        bad = submit_publish_proof(conn, jid, ProofInput())
        assert not bad["ok"]
        ok = submit_publish_proof(
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


def test_proof_doc_exists() -> None:
    assert "waiting_confirmation" in DOC.read_text(encoding="utf-8")


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
