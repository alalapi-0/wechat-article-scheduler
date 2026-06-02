"""Round 114：上传 .md 反馈增强与作品卡导出 outbox。"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r114.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def test_upload_returns_summary_and_chain(client: TestClient, tmp_path: Path) -> None:
    body = b"# Round114\n\nupload body for test\n"
    files = [("articles", ("r114.md", io.BytesIO(body), "text/markdown"))]
    res = client.post("/api/upload", files=files).json()
    assert res.get("ok") is True
    assert res.get("upload_summary", {}).get("summary_label")
    assert "human" in res
    if res.get("chain_summary"):
        assert res["chain_summary"].get("recommended_next_action")


def test_export_outbox_api(client: TestClient, tmp_path: Path) -> None:
    cfg_db = tmp_path / "r114.sqlite3"
    with db.connect(cfg_db) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/e.md', '导出测', 'S', '正文', 'he', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    r = client.post(f"/api/articles/{aid}/export-outbox?platform=generic").json()
    assert r.get("ok") is True
    assert r.get("human")
    assert r.get("relative_path")


def test_home_upload_and_outbox_markup(client: TestClient) -> None:
    html = client.get("/").text
    assert "showUploadOutcome" in html
    assert "exportOutboxArticle" in html
    assert "export-drop" in html or "导出" in html
    assert "正在上传并扫描入库" in html
