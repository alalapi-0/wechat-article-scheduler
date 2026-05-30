#!/usr/bin/env python3
"""校验 docs/rounds.md 与 agent_gate 轮次注册表一致（Round 12）。"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUNDS_DOC = ROOT / "docs" / "rounds.md"
TEMPLATE = ROOT / "docs" / "reports" / "round_report_template.md"
AGENT_GATE = ROOT / "scripts" / "agent_gate.py"

REQUIRED_ROUND_FIELDS = ("目标", "非目标", "验收标准", "建议测试/冒烟命令", "退出标准", "交付项")
REQUIRED_TEMPLATE_SECTIONS = (
    "## Summary",
    "## Scope",
    "## Deliverables Checklist",
    "## Acceptance Criteria",
    "## Validation Results",
    "## Next Actions",
)


def load_agent_gate():
    spec = importlib.util.spec_from_file_location("agent_gate", AGENT_GATE)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load agent_gate.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["agent_gate"] = mod
    spec.loader.exec_module(mod)
    return mod


def check_headings(ag, text: str) -> list[str]:
    errors: list[str] = []
    headings = re.findall(r"^### Round (\d+) - (.+)$", text, flags=re.MULTILINE)
    doc_ids = [f"round_{int(num):03d}" for num, _ in headings]
    if doc_ids != ag.ROUND_ORDER:
        errors.append(f"ROUND_ORDER mismatch: doc={len(doc_ids)} gate={len(ag.ROUND_ORDER)}")
    for num, title in headings:
        round_id = f"round_{int(num):03d}"
        if title not in ag.ROUND_META[round_id]["name"]:
            errors.append(f"{round_id}: heading title not in ROUND_META name")
    return errors


def check_required_fields(ag, text: str) -> list[str]:
    errors: list[str] = []
    for index, round_id in enumerate(ag.ROUND_ORDER):
        heading = ag.ROUND_META[round_id]["name"]
        start = text.index(f"### {heading}")
        if index + 1 < len(ag.ROUND_ORDER):
            next_heading = ag.ROUND_META[ag.ROUND_ORDER[index + 1]]["name"]
            end = text.index(f"### {next_heading}", start + 1)
        else:
            end = text.index("## 历史说明", start + 1)
        section = text[start:end]
        for field in REQUIRED_ROUND_FIELDS:
            if field not in section:
                errors.append(f"{round_id}: missing field {field}")
    return errors


def check_report_template() -> list[str]:
    if not TEMPLATE.exists():
        return ["round_report_template.md missing"]
    text = TEMPLATE.read_text(encoding="utf-8")
    return [f"template missing section: {s}" for s in REQUIRED_TEMPLATE_SECTIONS if s not in text]


def main() -> int:
    if not ROUNDS_DOC.exists():
        print("check_rounds_doc: FAIL — docs/rounds.md missing")
        return 1
    ag = load_agent_gate()
    text = ROUNDS_DOC.read_text(encoding="utf-8")
    errors: list[str] = []
    errors.extend(check_headings(ag, text))
    errors.extend(check_required_fields(ag, text))
    errors.extend(check_report_template())
    if errors:
        print("check_rounds_doc: FAIL")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(
        f"check_rounds_doc: PASS ({len(ag.ROUND_ORDER)} rounds, template ok)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
