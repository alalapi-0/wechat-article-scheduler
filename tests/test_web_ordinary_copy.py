"""普通视图文案与禁止词测试（Round 20+）。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler.web import create_app
import re

from wechat_article_scheduler.web.user_copy import (
    FORBIDDEN_ORDINARY_TERMS,
    export_labels_json,
    label_job_status,
    label_mode,
)
from tests.conftest import make_test_config
from wechat_article_scheduler import db


@pytest.fixture
def client(tmp_path: Path):
    db_path = tmp_path / "t.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def test_user_labels_single_source(client: TestClient) -> None:
    r = client.get("/api/user-labels")
    assert r.status_code == 200
    data = r.json()
    assert data["article_status"]["imported"] == "已收录"
    assert data["job_status"]["pending"] == "待发布"
    assert "forbidden_ordinary_terms" in data


def test_label_helpers():
    assert label_mode("mock") == "演练（不会真的发到公众号）"
    assert label_job_status("pending") == "待发布"


def _ordinary_html(html: str) -> str:
    """去掉脚本、样式与高级区块，近似普通视图可见表面。"""
    html = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", "", html, flags=re.IGNORECASE)
    html = re.sub(
        r'<section class="panel advanced-only">[\s\S]*?</section>',
        "",
        html,
        flags=re.IGNORECASE,
    )
    return html


def test_index_avoids_forbidden_ordinary_terms(client: TestClient) -> None:
    html = _ordinary_html(client.get("/").text)
    for term in FORBIDDEN_ORDINARY_TERMS:
        assert not re.search(rf"\b{re.escape(term)}\b", html), (
            f"普通视图 HTML 不应包含 {term}"
        )


def test_debug_page_has_internal_fields(client: TestClient) -> None:
    r = client.get("/debug")
    assert r.status_code == 200
    assert "高级排错" in r.text
    assert "/api/status" in r.text


def test_scan_returns_human_summary(client: TestClient, tmp_path: Path) -> None:
    inbox = tmp_path / "articles" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "a.md").write_text("# t\n\nbody", encoding="utf-8")
    r = client.post("/api/scan")
    assert r.status_code == 200
    data = r.json()
    assert "human" in data
    assert any("收录" in line for line in data["human"])


def test_export_matches_module():
    assert export_labels_json()["mode"]["mock"] == label_mode("mock")
