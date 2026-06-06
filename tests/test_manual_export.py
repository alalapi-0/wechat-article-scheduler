"""Round 77 / Phase 2：manual_export outbox 导出。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.manual_export import (
    export_article_to_outbox,
    list_outbox_packages,
)
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "manual_export_runbook.md"


def _seed_article(tmp_path: Path) -> tuple[object, int]:
    cfg = make_test_config(tmp_path, tmp_path / "e.sqlite3")
    db.init_db(cfg.database_path)
    cover = tmp_path / "cover.png"
    cover.write_bytes(b"\x89PNG\r\n\x1a\n")
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status, cover_path)
            VALUES ('inbox/t.md', '测试标题', '摘要', '# 正文\n\n段落', 'hash1', 'imported', ?)
            """,
            (str(cover),),
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
    return cfg, int(aid)


def test_export_creates_outbox_files(tmp_path: Path) -> None:
    cfg, aid = _seed_article(tmp_path)
    with db.connect(cfg.database_path) as conn:
        result = export_article_to_outbox(cfg, conn, aid)
    assert result["ok"]
    out_dir = Path(result["outbox_path"])
    assert (out_dir / "article.md").is_file()
    assert (out_dir / "article.html").is_file()
    assert (out_dir / "manifest.json").is_file()
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["proof_required"] is True
    assert manifest["article_id"] == aid
    with db.connect(cfg.database_path) as conn:
        row = conn.execute("SELECT status FROM articles WHERE id = ?", (aid,)).fetchone()
    assert row["status"] == "imported"


def test_list_outbox_packages(tmp_path: Path) -> None:
    cfg, aid = _seed_article(tmp_path)
    with db.connect(cfg.database_path) as conn:
        export_article_to_outbox(cfg, conn, aid)
    items = list_outbox_packages(cfg)
    assert len(items) >= 1
    assert items[0]["article_id"] == aid


def test_api_export_outbox(tmp_path: Path) -> None:
    cfg, aid = _seed_article(tmp_path)
    client = TestClient(create_app(cfg))
    r = client.post(f"/api/articles/{aid}/export-outbox")
    assert r.json()["ok"]
    lst = client.get("/api/outbox-packages").json()
    assert lst["count"] >= 1


def test_manual_export_outbox_respects_config(tmp_path: Path) -> None:
    custom = tmp_path / "outbox" / "user_view_test_manual"
    cfg, aid = _seed_article(tmp_path)
    cfg = make_test_config(tmp_path, cfg.database_path, manual_export_outbox=custom)
    with db.connect(cfg.database_path) as conn:
        result = export_article_to_outbox(cfg, conn, aid)
    assert result["ok"]
    out_dir = Path(result["outbox_path"])
    assert out_dir.is_relative_to(custom)
    assert not str(out_dir).startswith(str(tmp_path / "outbox" / "outbox_"))


def test_runbook_doc() -> None:
    assert "export-outbox" in DOC.read_text(encoding="utf-8")
