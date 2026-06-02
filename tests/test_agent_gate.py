"""agent_gate 脚本单元测试（不执行完整 pytest/冒烟）。"""

from __future__ import annotations

import importlib.util
import re
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


def test_round_order_covers_round_0_through_67(ag):
    assert len(ag.ROUND_ORDER) == 118
    assert ag.ROUND_ORDER[0] == "round_000"
    assert ag.ROUND_ORDER[-1] == "round_117"
    for round_id in ag.ROUND_ORDER:
        assert round_id in ag.ROUND_META
        assert ag.ROUND_META[round_id]["name"]
        assert ag.ROUND_META[round_id]["next_actions"]


def test_round_order_matches_rounds_doc_headings(ag):
    text = (ROOT / "docs" / "rounds.md").read_text(encoding="utf-8")
    headings = re.findall(r"^### Round (\d+) - (.+)$", text, flags=re.MULTILINE)
    doc_ids = [f"round_{int(num):03d}" for num, _title in headings]
    assert doc_ids == ag.ROUND_ORDER
    for num, title in headings:
        round_id = f"round_{int(num):03d}"
        assert title in ag.ROUND_META[round_id]["name"]


def test_rounds_doc_has_required_execution_fields(ag):
    text = (ROOT / "docs" / "rounds.md").read_text(encoding="utf-8")
    required = ["目标", "非目标", "验收标准", "建议测试/冒烟命令", "退出标准", "交付项"]
    for index, round_id in enumerate(ag.ROUND_ORDER):
        heading = ag.ROUND_META[round_id]["name"].replace(" - ", " - ", 1)
        start = text.index(f"### {heading}")
        if index + 1 < len(ag.ROUND_ORDER):
            next_heading = ag.ROUND_META[ag.ROUND_ORDER[index + 1]]["name"]
            end = text.index(f"### {next_heading}", start + 1)
        else:
            end = text.index("## 历史说明", start + 1)
        section = text[start:end]
        for field in required:
            assert field in section


def test_round_meta_aligns_with_rounds_doc_themes(ag):
    assert "CLI MVP" in ag.ROUND_META["round_000"]["name"]
    assert "治理" in ag.ROUND_META["round_001"]["name"]
    assert "封面资产" in ag.ROUND_META["round_007"]["name"]
    assert "可观测" in ag.ROUND_META["round_008"]["name"]
    assert "产品化" in ag.ROUND_META["round_009"]["name"]
    assert "可用性" in ag.ROUND_META["round_010"]["name"]
    assert "治理编排" in ag.ROUND_META["round_011"]["name"]
    assert "质量门禁" in ag.ROUND_META["round_012"]["name"]
    assert "Renderer" in ag.ROUND_META["round_013"]["name"]
    assert "Cover" in ag.ROUND_META["round_014"]["name"]
    assert "Content Library" in ag.ROUND_META["round_015"]["name"]
    assert "Scheduler" in ag.ROUND_META["round_016"]["name"]
    assert "真实发布" in ag.ROUND_META["round_017"]["name"]
    assert "AI 辅助" in ag.ROUND_META["round_018"]["name"]
    assert "普通用户" in ag.ROUND_META["round_019"]["name"]
    assert "Playwright" in ag.ROUND_META["round_019"]["name"]
    assert "术语" in ag.ROUND_META["round_020"]["name"]
    assert "信息减法" in ag.ROUND_META["round_021"]["name"]
    assert "三步操作" in ag.ROUND_META["round_022"]["name"]
    assert "反馈" in ag.ROUND_META["round_023"]["name"]
    assert "空状态" in ag.ROUND_META["round_024"]["name"]
    assert "安全发布" in ag.ROUND_META["round_025"]["name"]
    assert "桌面主布局" in ag.ROUND_META["round_026"]["name"]
    assert "文章列表" in ag.ROUND_META["round_027"]["name"]
    assert "发布队列" in ag.ROUND_META["round_028"]["name"]
    assert "事件日志" in ag.ROUND_META["round_029"]["name"]
    assert "高级信息" in ag.ROUND_META["round_030"]["name"]
    assert "帮助" in ag.ROUND_META["round_031"]["name"]
    assert "错误" in ag.ROUND_META["round_032"]["name"]
    assert "桌面效率" in ag.ROUND_META["round_033"]["name"]
    assert "窄屏兼容" in ag.ROUND_META["round_034"]["name"]
    assert "Playwright E2E" in ag.ROUND_META["round_035"]["name"]
    assert "非技术用户" in ag.ROUND_META["round_036"]["name"]
    assert "MVP 收口" in ag.ROUND_META["round_037"]["name"]
    assert "接入规范" in ag.ROUND_META["round_038"]["name"]
    assert "确认" in ag.ROUND_META["round_039"]["name"]
    assert "定时发布" in ag.ROUND_META["round_040"]["name"]
    assert "预检" in ag.ROUND_META["round_041"]["name"]
    assert "能力矩阵" in ag.ROUND_META["round_042"]["name"]
    assert "审核概念移除" in ag.ROUND_META["round_043"]["name"]
    assert "批量上传" in ag.ROUND_META["round_044"]["name"]
    assert "界面与配色" in ag.ROUND_META["round_045"]["name"]
    assert "发布确认护栏" in ag.ROUND_META["round_046"]["name"]
    assert "UI 细节" in ag.ROUND_META["round_047"]["name"]
    assert "标题去重" in ag.ROUND_META["round_048"]["name"]
    assert "预览修正" in ag.ROUND_META["round_049"]["name"]
    assert "回收站" in ag.ROUND_META["round_050"]["name"]
    assert "彻底删除" in ag.ROUND_META["round_051"]["name"]
    assert "批量管理" in ag.ROUND_META["round_052"]["name"]
    assert "内容质量" in ag.ROUND_META["round_053"]["name"]
    assert "真实微信" in ag.ROUND_META["round_054"]["name"]
    assert "Auto-Approved" in ag.ROUND_META["round_055"]["name"]
    assert "路线收敛" in ag.ROUND_META["round_056"]["name"]
    assert "链路稳定" in ag.ROUND_META["round_057"]["name"]
    assert "幂等" in ag.ROUND_META["round_058"]["name"] or "摘要" in ag.ROUND_META["round_058"]["name"]
    assert "HTML" in ag.ROUND_META["round_059"]["name"] or "渲染" in ag.ROUND_META["round_059"]["name"]
    assert "预览" in ag.ROUND_META["round_060"]["name"] or "快照" in ag.ROUND_META["round_060"]["name"]
    assert "封面" in ag.ROUND_META["round_061"]["name"]
    assert "裁剪" in ag.ROUND_META["round_062"]["name"] or "预览" in ag.ROUND_META["round_062"]["name"]
    assert "合集" in ag.ROUND_META["round_063"]["name"] or "内容库" in ag.ROUND_META["round_063"]["name"]
    assert "排期" in ag.ROUND_META["round_064"]["name"]
    assert "Web" in ag.ROUND_META["round_065"]["name"] or "控制台" in ag.ROUND_META["round_065"]["name"]
    assert "详情" in ag.ROUND_META["round_066"]["name"] or "预览" in ag.ROUND_META["round_066"]["name"]
    assert "队列" in ag.ROUND_META["round_067"]["name"]
    assert "草稿" in ag.ROUND_META["round_068"]["name"]
    assert "scheduler" in ag.ROUND_META["round_069"]["name"].lower()
    assert "常驻" in ag.ROUND_META["round_070"]["name"]
    assert "草稿更新" in ag.ROUND_META["round_071"]["name"]
    assert "字段" in ag.ROUND_META["round_072"]["name"]
    assert "browser_assist" in ag.ROUND_META["round_073"]["name"].lower()
    assert "proof" in ag.ROUND_META["round_074"]["name"].lower()
    assert "正式发布" in ag.ROUND_META["round_075"]["name"]
    assert "闭环" in ag.ROUND_META["round_076"]["name"]
    assert "manual_export" in ag.ROUND_META["round_077"]["name"].lower()
    assert "Phase 2" in ag.ROUND_META["round_078"]["name"] or "平台" in ag.ROUND_META["round_078"]["name"]
    assert "知乎" in ag.ROUND_META["round_079"]["name"]
    assert "豆瓣" in ag.ROUND_META["round_080"]["name"]
    assert "知乎" in ag.ROUND_META["round_081"]["name"]
    assert "browser_assist" in ag.ROUND_META["round_082"]["name"].lower()
    assert "豆瓣" in ag.ROUND_META["round_083"]["name"]
    assert "Phase2" in ag.ROUND_META["round_084"]["name"] or "收口" in ag.ROUND_META["round_084"]["name"]


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
