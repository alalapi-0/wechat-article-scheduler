#!/usr/bin/env python3
"""列出 tests/ 中未被 agent_gate 冒烟引用的测试模块（Round 12 提醒，非阻断）。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
AGENT_GATE = ROOT / "scripts" / "agent_gate.py"

# agent_gate round_smoke 与全量 pytest 已覆盖的模块（手工维护最小集）
REFERENCED_TEST_STEMS = {
    "test_agent_gate",
    "test_workflow",
    "test_digest_limits",
    "test_parser",
    "test_real_adapter",
    "test_scheduler_plan",
    "test_web_app",
    "test_renderer_markdown",
    "test_scheduler_hardening",
    "test_check_rounds_doc",
}


def collect_smoke_stems() -> set[str]:
    """从 agent_gate 源码静态提取 pytest 路径，避免执行 round_000 CLI 闭环。"""
    stems = set(REFERENCED_TEST_STEMS)
    text = AGENT_GATE.read_text(encoding="utf-8")
    for match in re.findall(r"tests/test_[a-zA-Z0-9_]+\.py", text):
        stems.add(Path(match).stem)
    for match in re.findall(r"tests/test_[a-zA-Z0-9_]+", text):
        if "/" not in match:
            stems.add(match.split("/")[-1])
    return stems


def main() -> int:
    stems = collect_smoke_stems()
    all_tests = sorted(p.stem for p in TESTS.glob("test_*.py"))
    unreferenced = [t for t in all_tests if t not in stems]
    if unreferenced:
        print("check_test_coverage_hints: WARNING — 以下测试未在冒烟路径中显式引用:")
        for name in unreferenced:
            print(f"  - {name}")
        print("  建议：为关键模块补充 round 冒烟或在本脚本 REFERENCED_TEST_STEMS 登记原因")
        return 0
    print(f"check_test_coverage_hints: PASS ({len(all_tests)} test modules referenced)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
