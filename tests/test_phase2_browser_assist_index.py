"""Round 84：Phase 2 browser_assist 三平台索引。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from wechat_article_scheduler.adapters.browser_assist import (
    SUPPORTED_BROWSER_ASSIST,
    build_dry_run_plan,
)
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


def test_supported_platforms_include_text_sites() -> None:
    assert "zhihu" in SUPPORTED_BROWSER_ASSIST
    assert "douban" in SUPPORTED_BROWSER_ASSIST
    for pid in ("zhihu", "douban"):
        plan = build_dry_run_plan(platform=pid)
        assert plan["assessment"]["recommendation"] == "conditional"


def test_api_lists_three_assist_platforms(tmp_path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "x.sqlite3")
    client = TestClient(create_app(cfg))
    ids = {p["id"] for p in client.get("/api/browser-assist/platforms").json()["platforms"]}
    assert {"wechat_official", "zhihu", "douban"}.issubset(ids)
