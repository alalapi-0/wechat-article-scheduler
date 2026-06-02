"""Round 123：/api/status 路线图只读字段与高级面板 advRoadmap。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler.config import ROOT
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.roadmap_state import build_roadmap_status_fields
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    cfg = make_test_config(tmp_path, tmp_path / "r123.sqlite3")
    return TestClient(create_app(cfg))


def test_api_status_exposes_roadmap_fields(client: TestClient) -> None:
    data = client.get("/api/status").json()
    assert "roadmap_hint" in data
    assert "last_completed_round" in data
    hint = data["roadmap_hint"]
    assert hint.get("current_round_id")
    assert hint.get("position_label")
    assert any(l.get("path") == "docs/backlog/README.md" for l in hint.get("doc_links", []))
    lcr = data["last_completed_round"]
    assert lcr is None or lcr.get("id")


def test_overview_status_includes_roadmap_fields(client: TestClient) -> None:
    ov = client.get("/api/overview").json()
    st = ov.get("status") or {}
    assert st.get("roadmap_hint", {}).get("current_round_id")
    assert "last_completed_round" in st


def test_build_roadmap_status_fields_reads_repo_state() -> None:
    fields = build_roadmap_status_fields()
    assert fields["roadmap_hint"]["state_file"] == "governance/round_state.yaml"
    assert (ROOT / "governance" / "round_state.yaml").is_file()


def test_home_advanced_roadmap_panel_markup(client: TestClient) -> None:
    html = client.get("/").text
    assert 'id="advRoadmap"' in html
    assert "当前路线图位置" in html
    assert "renderAdvanced" in html
    assert "doc_links" in html
