"""Round 128：普通视图（不开高级）作品卡 export toast 含「未自动发布」。"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config
from tests.test_web_ordinary_copy import _ordinary_html

ROOT = Path(__file__).resolve().parents[1]
JS_PATH = ROOT / "src/wechat_article_scheduler/web/export_outbox_ui.js"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r128.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def _insert_article(db_path: Path) -> int:
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/r128.md', '普通导出', 'S', 'B', 'h128', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    return aid


def test_ordinary_surface_export_toast_wiring(client: TestClient) -> None:
    """普通视图：alertBox 可见；导出走共用 JS（非 advanced-only 区块）。"""
    raw = client.get("/").text
    surf = _ordinary_html(raw)
    assert 'id="alertBox"' in surf
    assert "/assets/export-outbox-ui.js" in raw
    assert "exportOutboxArticle" in raw
    assert "ExportOutboxUi.buildSuccessHtml" in raw
    adv = re.search(r'id="advanced"[\s\S]{0,4000}', raw)
    if adv:
        assert "exportOutboxArticle" not in adv.group(0)


def test_export_api_and_toast_contract_for_ordinary_view(
    client: TestClient, tmp_path: Path,
) -> None:
    """普通视图导出走共用 toast：API 成功 + JS 含未自动发布文案。"""
    aid = _insert_article(tmp_path / "r128.sqlite3")
    exp = client.post(f"/api/articles/{aid}/export-outbox?platform=generic").json()
    assert exp.get("ok") is True
    assert exp.get("relative_path")

    js = JS_PATH.read_text(encoding="utf-8")
    assert "未自动发布" in js
    assert "需您人工上传" in js

    home = client.get("/").text
    assert "exportOutboxArticle" in home
    assert "el('alertBox').innerHTML = ExportOutboxUi.buildSuccessHtml" in home


def test_build_success_html_contains_manual_notice() -> None:
    """静态断言：共用 JS 生成的 toast HTML 含醒目人工提示。"""
    js = JS_PATH.read_text(encoding="utf-8")
    assert "export-toast-warn" in js
    assert "WARN_TEXT" in js
    assert "未自动发布" in js
    assert "relative_path" in js
