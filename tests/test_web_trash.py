"""回收站与删除。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.web.app import create_app
from wechat_article_scheduler.web.trash import safe_unlink
from tests.test_web_upload import PNG


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    from wechat_article_scheduler.config import load_config

    db_path = tmp_path / "trash.sqlite3"
    articles = tmp_path / "articles"
    inbox = articles / "inbox"
    imported = articles / "imported"
    covers = articles / "covers"
    for d in (inbox, imported, covers):
        d.mkdir(parents=True)
    cfg = load_config()
    return AppConfig(
        **{**cfg.__dict__, "root": tmp_path, "database_path": db_path, "inbox_dir": inbox}
    )


def _insert_article(conn, *, title: str = "测试", body: str = "正文") -> int:
    cur = conn.execute(
        """
        INSERT INTO articles (source_path, title, summary, body, content_hash, status)
        VALUES (?, ?, ?, ?, ?, 'imported')
        """,
        (str(Path("/tmp/x.md")), title, "", body, "hash_" + title),
    )
    return int(cur.lastrowid)


def test_soft_delete_hides_from_library(app_config: AppConfig) -> None:
    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        aid = _insert_article(conn)
        conn.commit()
    assert client.post(f"/api/articles/{aid}/trash").status_code == 200
    arts = client.get("/api/articles").json()
    assert all(a["id"] != aid for a in arts)
    trash = client.get("/api/trash").json()
    assert any(t["id"] == aid for t in trash)


def test_restore_returns_to_library(app_config: AppConfig) -> None:
    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        aid = _insert_article(conn)
        conn.commit()
    client.post(f"/api/articles/{aid}/trash")
    assert client.post(f"/api/articles/{aid}/restore").status_code == 200
    arts = client.get("/api/articles").json()
    assert any(a["id"] == aid for a in arts)


def test_trash_cancels_pending_job(app_config: AppConfig) -> None:
    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        aid = _insert_article(conn)
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
            VALUES (?, datetime('now'), 'pending', 'mock')
            """,
            (aid,),
        )
        conn.commit()
    client.post(f"/api/articles/{aid}/trash")
    jobs = client.get("/api/jobs").json()
    assert all(j["article_id"] != aid for j in jobs)


def test_purge_removes_db_and_safe_files(app_config: AppConfig) -> None:
    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    src = app_config.imported_dir / "gone.md"
    src.write_text("# t\n\nb", encoding="utf-8")
    cover = app_config.covers_dir / "gone.png"
    cover.write_bytes(PNG)
    with db.connect(app_config.database_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status, cover_path, deleted_at)
            VALUES (?, 't', '', 'b', 'h1', 'imported', ?, datetime('now'))
            """,
            (str(src), str(cover)),
        )
        aid = int(cur.lastrowid)
        conn.commit()
    out = client.post("/api/trash/purge").json()
    assert out["purged"] == 1
    assert not src.exists()
    assert not cover.exists()
    with db.connect(app_config.database_path) as conn:
        assert conn.execute("SELECT id FROM articles WHERE id = ?", (aid,)).fetchone() is None


def test_purge_never_deletes_forged_project_file(app_config: AppConfig) -> None:
    db.init_db(app_config.database_path)
    protected = app_config.root / ".env"
    protected.write_text("SECRET=keep", encoding="utf-8")
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path,title,summary,body,content_hash,status,deleted_at) "
            "VALUES (?, 't','','b','forged-delete','imported',datetime('now'))",
            (str(protected),),
        )
        conn.commit()
    response = TestClient(create_app(app_config)).post("/api/trash/purge")
    assert response.status_code == 200
    assert protected.read_text(encoding="utf-8") == "SECRET=keep"


def test_purge_preserves_cover_referenced_by_relative_alias(app_config: AppConfig) -> None:
    db.init_db(app_config.database_path)
    cover = app_config.covers_dir / "shared.png"
    cover.write_bytes(PNG)
    relative = str(cover.relative_to(app_config.root))
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path,title,summary,body,content_hash,status,cover_path,deleted_at) "
            "VALUES ('a.md','a','','b','alias-a','imported',?,datetime('now'))",
            (relative,),
        )
        conn.execute(
            "INSERT INTO articles (source_path,title,summary,body,content_hash,status,cover_path) "
            "VALUES ('b.md','b','','b','alias-b','imported',?)",
            (str(cover),),
        )
        conn.commit()
    TestClient(create_app(app_config)).post("/api/trash/purge")
    assert cover.is_file()
    with db.connect(app_config.database_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 1


def test_purge_does_not_remove_active_articles(app_config: AppConfig) -> None:
    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        active = _insert_article(conn, title="仍保留")
        conn.commit()
    out = client.post("/api/trash/purge").json()
    assert out["purged"] == 0
    assert any(a["id"] == active for a in client.get("/api/articles").json())


def test_purge_removes_article_events(app_config: AppConfig) -> None:
    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        aid = _insert_article(conn)
        conn.execute(
            """
            INSERT INTO events (entity_type, entity_id, event_type, payload_json)
            VALUES ('article', ?, 'article_trashed', '{}')
            """,
            (aid,),
        )
        conn.execute(
            "UPDATE articles SET deleted_at = datetime('now') WHERE id = ?",
            (aid,),
        )
        conn.commit()
    client.post("/api/trash/purge")
    with db.connect(app_config.database_path) as conn:
        assert (
            conn.execute(
                "SELECT id FROM events WHERE entity_type = 'article' AND entity_id = ?",
                (aid,),
            ).fetchone()
            is None
        )


def test_purge_removes_jobs_and_drafts(app_config: AppConfig) -> None:
    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        aid = _insert_article(conn)
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
            VALUES (?, datetime('now'), 'cancelled', 'mock')
            """,
            (aid,),
        )
        conn.execute(
            "INSERT INTO wechat_drafts (article_id, media_id, status) VALUES (?, 'm1', 'created')",
            (aid,),
        )
        draft_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            """
            INSERT INTO events (entity_type, entity_id, event_type, payload_json)
            VALUES ('wechat_draft', ?, 'draft_updated', '{}')
            """,
            (draft_id,),
        )
        conn.execute(
            "UPDATE articles SET deleted_at = datetime('now') WHERE id = ?",
            (aid,),
        )
        conn.commit()
    client.post("/api/trash/purge")
    with db.connect(app_config.database_path) as conn:
        assert conn.execute("SELECT id FROM articles WHERE id = ?", (aid,)).fetchone() is None
        assert conn.execute(
            "SELECT id FROM publish_jobs WHERE article_id = ?", (aid,)
        ).fetchone() is None
        assert conn.execute(
            "SELECT id FROM wechat_drafts WHERE article_id = ?", (aid,)
        ).fetchone() is None
        assert conn.execute(
            "SELECT id FROM events WHERE entity_type = 'wechat_draft' AND entity_id = ?",
            (draft_id,),
        ).fetchone() is None


def test_purge_removes_publish_proof_and_job_events(app_config: AppConfig) -> None:
    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        aid = _insert_article(conn)
        jid = int(
            conn.execute(
                """
                INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
                VALUES (?, datetime('now'), 'done', 'real')
                """,
                (aid,),
            ).lastrowid
        )
        conn.execute(
            """
            INSERT INTO publish_proofs
                (publish_job_id, article_id, public_url, confirmed_by, confirmed_at)
            VALUES (?, ?, 'https://example.invalid/proof', 'user', datetime('now'))
            """,
            (jid, aid),
        )
        conn.execute(
            """
            INSERT INTO events (entity_type, entity_id, event_type, payload_json)
            VALUES ('publish_job', ?, 'proof_submitted', '{}')
            """,
            (jid,),
        )
        conn.execute(
            "UPDATE articles SET deleted_at = datetime('now') WHERE id = ?",
            (aid,),
        )
        conn.commit()

    response = client.post("/api/trash/purge")
    assert response.status_code == 200
    assert response.json()["purged"] == 1
    with db.connect(app_config.database_path) as conn:
        assert conn.execute(
            "SELECT id FROM publish_proofs WHERE article_id = ?", (aid,)
        ).fetchone() is None
        assert conn.execute(
            "SELECT id FROM events WHERE entity_type = 'publish_job' AND entity_id = ?",
            (jid,),
        ).fetchone() is None


def test_purge_skips_files_outside_project_root(app_config: AppConfig) -> None:
    outside = app_config.root.parent / "outside_purge_guard.md"
    outside.write_text("must remain", encoding="utf-8")
    try:
        db.init_db(app_config.database_path)
        client = TestClient(create_app(app_config))
        with db.connect(app_config.database_path) as conn:
            conn.execute(
                """
                INSERT INTO articles (source_path, title, summary, body, content_hash, status, deleted_at)
                VALUES (?, '外', '', 'b', 'h_out', 'imported', datetime('now'))
                """,
                (str(outside),),
            )
            conn.commit()
        client.post("/api/trash/purge")
        assert outside.exists()
        assert outside.read_text(encoding="utf-8") == "must remain"
    finally:
        outside.unlink(missing_ok=True)


def test_safe_unlink_rejects_outside_root(app_config: AppConfig) -> None:
    assert safe_unlink(app_config, "/etc/passwd") is False


def test_plan_skips_trashed_articles(app_config: AppConfig) -> None:
    """软删除作品不参与排期，未删除作品仍可 plan。"""
    from wechat_article_scheduler.plan import build_plan

    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        keep = _insert_article(conn, title="保留")
        gone = _insert_article(conn, title="回收")
        conn.commit()
    client.post(f"/api/articles/{gone}/trash")
    stats = build_plan(app_config)
    assert stats["planned"] >= 1
    with db.connect(app_config.database_path) as conn:
        rows = conn.execute(
            "SELECT article_id FROM publish_jobs WHERE status = 'pending'"
        ).fetchall()
        planned_ids = {int(r["article_id"]) for r in rows}
    assert keep in planned_ids
    assert gone not in planned_ids


def test_delete_preview_counts_pending_jobs(app_config: AppConfig) -> None:
    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        aid = _insert_article(conn)
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
            VALUES (?, datetime('now'), 'pending', 'mock')
            """,
            (aid,),
        )
        conn.commit()
    data = client.post("/api/articles/delete-preview", json={"ids": [aid]}).json()
    assert data["article_count"] == 1
    assert data["pending_jobs_to_cancel"] == 1


def test_cancel_publish_job_api(app_config: AppConfig) -> None:
    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        aid = _insert_article(conn)
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
            VALUES (?, datetime('now'), 'pending', 'mock')
            """,
            (aid,),
        )
        conn.commit()
        jid = int(conn.execute("SELECT id FROM publish_jobs").fetchone()[0])
    assert client.post(f"/api/jobs/{jid}/cancel").status_code == 200
    jobs = client.get("/api/jobs").json()
    assert all(j.get("id") != jid for j in jobs)


def test_cancelled_job_can_be_planned_again(app_config: AppConfig) -> None:
    from wechat_article_scheduler.plan import build_plan

    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        aid = _insert_article(conn)
        jid = int(
            conn.execute(
                """
                INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
                VALUES (?, datetime('now'), 'pending', 'mock')
                """,
                (aid,),
            ).lastrowid
        )
        conn.execute(
            "UPDATE articles SET schedule_state = 'scheduled_local' WHERE id = ?",
            (aid,),
        )
        conn.commit()

    assert client.post(f"/api/jobs/{jid}/cancel").status_code == 200
    assert build_plan(app_config)["planned"] == 1


def test_trash_restore_can_be_planned_again(app_config: AppConfig) -> None:
    from wechat_article_scheduler.plan import build_plan

    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        aid = _insert_article(conn)
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
            VALUES (?, datetime('now'), 'pending', 'mock')
            """,
            (aid,),
        )
        conn.execute(
            "UPDATE articles SET schedule_state = 'scheduled_local' WHERE id = ?",
            (aid,),
        )
        conn.commit()

    assert client.post(f"/api/articles/{aid}/trash").status_code == 200
    assert client.post(f"/api/articles/{aid}/restore").status_code == 200
    assert build_plan(app_config)["planned"] == 1


def test_orphan_cover_cleanup_skips_referenced(app_config: AppConfig) -> None:
    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    used = app_config.covers_dir / "used.png"
    orphan = app_config.covers_dir / "orphan.png"
    used.write_bytes(PNG)
    orphan.write_bytes(PNG)
    with db.connect(app_config.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status, cover_path)
            VALUES ('a.md', 't', '', 'b', 'h', 'imported', ?)
            """,
            (str(used),),
        )
        conn.commit()
    listed = client.get("/api/covers/orphans").json()
    assert listed["count"] == 1
    assert listed["orphans"][0]["name"] == "orphan.png"
    out = client.post("/api/covers/cleanup-orphans").json()
    assert out["removed"] == 1
    assert used.exists()
    assert not orphan.exists()


def test_bulk_trash_only_affects_selected(app_config: AppConfig) -> None:
    """批量删除仅作用于选中作品。"""
    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        keep = _insert_article(conn, title="保留篇")
        drop = _insert_article(conn, title="删除篇")
        conn.commit()
    client.post("/api/articles/bulk-trash", json={"ids": [drop]})
    arts = {a["id"] for a in client.get("/api/articles").json()}
    trash = {t["id"] for t in client.get("/api/trash").json()}
    assert keep in arts
    assert drop not in arts
    assert drop in trash
    assert keep not in trash


def test_bulk_trash_and_restore(app_config: AppConfig) -> None:
    db.init_db(app_config.database_path)
    client = TestClient(create_app(app_config))
    with db.connect(app_config.database_path) as conn:
        ids = [_insert_article(conn, title=f"t{i}") for i in range(2)]
        conn.commit()
    client.post("/api/articles/bulk-trash", json={"ids": ids})
    assert len(client.get("/api/trash").json()) == 2
    client.post("/api/articles/bulk-restore", json={"ids": ids})
    assert len(client.get("/api/articles").json()) == 2
