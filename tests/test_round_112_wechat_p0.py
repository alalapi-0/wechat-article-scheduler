"""Round 112：扫描收件箱反馈增强与 chain_summary 联动。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.scan_preflight import build_scan_preflight
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r112.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def test_scan_preflight_blocks_non_directory(tmp_path: Path) -> None:
    db_path = tmp_path / "r112b.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    inbox_file = tmp_path / "inbox_file"
    inbox_file.write_text("x", encoding="utf-8")
    cfg.inbox_dir = inbox_file
    pre = build_scan_preflight(cfg)
    assert pre["blocked"] is True
    client = TestClient(create_app(cfg))
    res = client.post("/api/scan").json()
    assert res.get("blocked_by_scan_preflight") is True


def test_scan_preflight_api(client: TestClient) -> None:
    data = client.get("/api/scan-preflight").json()
    assert "inbox_path" in data
    assert "ready" in data


def test_scan_returns_summary_and_chain(client: TestClient, tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "r112.sqlite3")
    inbox = Path(cfg.inbox_dir)
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "demo.md").write_text("# 标题\n\n正文", encoding="utf-8")
    app_client = TestClient(create_app(cfg))
    res = app_client.post("/api/scan").json()
    assert res.get("ok") is True
    assert res.get("scan_summary", {}).get("summary_label")
    assert res.get("chain_summary", {}).get("recommended_next_action")
    assert res.get("human")


def test_home_scan_markup(client: TestClient) -> None:
    html = client.get("/").text
    assert "scanBlockReason" in html
    assert "chainScanHint" in html
    assert "showScanOutcome" in html
    assert "onScan" in html
    assert "scan-preflight" in html or "scan_preflight" in html
