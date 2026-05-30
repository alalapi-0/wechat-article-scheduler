"""agent_gate 脚本单元测试（不执行完整 pytest/冒烟）。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_gate.py"


def load_agent_gate():
    spec = importlib.util.spec_from_file_location("agent_gate", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["agent_gate"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def ag():
    return load_agent_gate()


def test_is_secret_path(ag):
    assert ag.is_secret_path(".env")
    assert ag.is_secret_path("config/.env")
    assert not ag.is_secret_path("README.md")


def test_round_order_contains_governance_round(ag):
    assert "round_001" in ag.ROUND_ORDER
    assert ag.ROUND_META["round_001"]["next_actions"]


def test_round_order_covers_round_0_through_9(ag):
    assert len(ag.ROUND_ORDER) == 10
    assert ag.ROUND_ORDER[0] == "round_000"
    assert ag.ROUND_ORDER[-1] == "round_009"
    for round_id in ag.ROUND_ORDER:
        assert round_id in ag.ROUND_META
        assert ag.ROUND_META[round_id]["name"]
        assert ag.ROUND_META[round_id]["next_actions"]


def test_round_meta_aligns_with_rounds_doc_themes(ag):
    assert "CLI MVP" in ag.ROUND_META["round_000"]["name"]
    assert "治理" in ag.ROUND_META["round_001"]["name"]
    assert "封面资产" in ag.ROUND_META["round_007"]["name"]
    assert "可观测" in ag.ROUND_META["round_008"]["name"]
    assert "产品化" in ag.ROUND_META["round_009"]["name"]


def test_suggest_next_command_completed(ag):
    cmd = ag.suggest_next_command("round_001", "completed")
    assert "advance" in cmd


def test_get_current_round_id_reads_yaml(ag):
    rid = ag.get_current_round_id()
    assert rid.startswith("round_")


def test_gate_state_verdict(ag):
    state = ag.GateState()
    state.passed("a", "ok")
    state.warn("b", "warn")
    assert state.verdict == ag.WARNING
    state.block("c", "no")
    assert state.verdict == ag.BLOCKED
