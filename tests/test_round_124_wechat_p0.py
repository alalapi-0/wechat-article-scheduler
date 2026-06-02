"""Round 124：/api/agent-gate-status 与高级面板 advAgentGate。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.agent_gate_status import build_agent_gate_status_api
from tests.conftest import make_test_config
from tests.test_agent_gate import load_agent_gate


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    cfg = make_test_config(tmp_path, tmp_path / "r124.sqlite3")
    return TestClient(create_app(cfg))


def test_api_agent_gate_status_matches_cli_payload(client: TestClient) -> None:
    api = client.get("/api/agent-gate-status").json()
    cli = load_agent_gate().build_status_payload()
    assert api["current_round"]["id"] == cli["current_round"]["id"]
    assert api["gate_summary"]
    assert "acceptance_criteria" in api
    assert "next_actions" in api
    assert "suggested_command" in api
    assert "wechat_app_secret" not in api
    assert "token" not in {k.lower() for k in api.keys()}


def test_build_agent_gate_status_api_has_no_secrets() -> None:
    data = build_agent_gate_status_api()
    blob = str(data).lower()
    for forbidden in ("app_secret", "token", "password", "api_key"):
        assert forbidden not in blob


def test_home_adv_agent_gate_markup(client: TestClient) -> None:
    html = client.get("/").text
    assert 'id="advAgentGate"' in html
    assert "renderAgentGatePanel" in html
    assert "/api/agent-gate-status" in html
    assert "Agent gate" in html
