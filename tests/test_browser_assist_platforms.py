"""Round 82：browser_assist 多平台 API（微信主线）。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


def test_browser_assist_platforms_includes_wechat(tmp_path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "p.sqlite3")
    client = TestClient(create_app(cfg))
    data = client.get("/api/browser-assist/platforms").json()
    ids = {p["id"] for p in data["platforms"]}
    assert "wechat_official" in ids
    wechat = client.get("/api/browser-assist-plan").json()
    assert wechat["platform"] == "wechat_official"
