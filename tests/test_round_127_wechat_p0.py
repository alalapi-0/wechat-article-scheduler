"""Round 127：统一 export-outbox 成功 toast（共用 JS）。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config

ROOT = Path(__file__).resolve().parents[1]
JS_PATH = ROOT / "src/wechat_article_scheduler/web/export_outbox_ui.js"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r127.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def test_export_outbox_ui_js_served(client: TestClient) -> None:
    r = client.get("/assets/export-outbox-ui.js")
    assert r.status_code == 200
    text = r.text
    assert "ExportOutboxUi" in text
    assert "未自动发布" in text
    assert "buildSuccessHtml" in text


def test_workbench_and_detail_reference_shared_js(client: TestClient, tmp_path: Path) -> None:
    with db.connect(tmp_path / "r127.sqlite3") as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/t.md', 'T', 'S', 'B', 'h', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    home = client.get("/").text
    detail = client.get(f"/articles/{aid}").text
    assert "/assets/export-outbox-ui.js" in home
    assert "/assets/export-outbox-ui.js" in detail
    assert "export-toast-warn" in home
    assert "exportToast" in detail
    assert "ExportOutboxUi.buildSuccessHtml" in home
    assert "ExportOutboxUi.showInElement" in detail


def test_js_warn_text_constant() -> None:
    text = JS_PATH.read_text(encoding="utf-8")
    assert "未自动发布" in text
    assert "需您人工上传" in text
