#!/usr/bin/env python3
"""校验治理必需文件是否存在（Round 4）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "AGENTS.md",
    "README.md",
    "project.yaml",
    "governance/repo_protocol_standard.yaml",
    "governance/round_state.yaml",
    "governance/agent_policy.yaml",
    "governance/file_role_map.yaml",
    "docs/rounds.md",
    "scripts/agent_gate.py",
    "scripts/check_rounds_doc.py",
    "scripts/check_test_coverage_hints.py",
    "governance/round_smoke_hints.yaml",
    "src/wechat_article_scheduler/cli.py",
]


def main() -> int:
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    if missing:
        print("check_repo_contract: FAIL")
        for p in missing:
            print(f"  missing: {p}")
        return 1
    print("check_repo_contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
