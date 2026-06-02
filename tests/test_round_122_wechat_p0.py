"""Round 122：文档同步与 round_108–121 抛光摘要登记。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    cfg = make_test_config(tmp_path, tmp_path / "r122.sqlite3")
    return TestClient(create_app(cfg))


def test_rounds_doc_has_wechat_p0_polish_summary() -> None:
    text = (ROOT / "docs/rounds.md").read_text(encoding="utf-8")
    assert "## 微信 P0 抛光摘要（Round 108–121）" in text
    assert "| 108 |" in text
    assert "| 121 |" in text
    assert "wechat_workbench_section_hash" in text


def test_readme_milestone_mentions_round_108_121() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "round_108–121" in readme or "round_108-121" in readme
    assert "localStorage" in readme


def test_agent_gate_meta_has_summaries_for_108_121() -> None:
    from tests.test_agent_gate import load_agent_gate

    ag = load_agent_gate()
    for rid in [f"round_{n}" for n in range(108, 123)]:
        meta = ag.ROUND_META[rid]
        assert meta.get("summary"), rid
        assert len(meta["summary"]) >= 8
