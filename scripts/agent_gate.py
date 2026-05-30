#!/usr/bin/env python3
"""治理门控 + 多轮自主推进（Round 0-4）。

用法（仓库根目录）:
    python scripts/agent_gate.py           # 校验当前轮，通过则提交并推进
    python scripts/agent_gate.py --check-only  # 仅校验，不 git commit
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "reports" / "agent_gate_report.md"
ROUND_STATE_PATH = ROOT / "governance" / "round_state.yaml"
ROUNDS_DOC = ROOT / "docs" / "rounds.md"

PASS, WARNING, BLOCKED = "PASS", "WARNING", "BLOCKED"
SEVERITY_RANK = {PASS: 0, WARNING: 1, BLOCKED: 2}
EXIT_CODE = {PASS: 0, WARNING: 1, BLOCKED: 2}

ROUND_ORDER = [
    "round_000",
    "round_001",
    "round_002",
    "round_003",
    "round_004",
    "round_005",
    "round_006",
    "round_007",
]


@dataclass
class Finding:
    check: str
    severity: str
    message: str


@dataclass
class GateState:
    findings: list[Finding] = field(default_factory=list)

    def add(self, check: str, severity: str, message: str) -> None:
        self.findings.append(Finding(check, severity, message))

    def passed(self, check: str, message: str) -> None:
        self.add(check, PASS, message)

    def warn(self, check: str, message: str) -> None:
        self.add(check, WARNING, message)

    def block(self, check: str, message: str) -> None:
        self.add(check, BLOCKED, message)

    @property
    def verdict(self) -> str:
        worst = PASS
        for f in self.findings:
            if SEVERITY_RANK[f.severity] > SEVERITY_RANK[worst]:
                worst = f.severity
        return worst


def load_yaml(path: Path) -> dict[str, Any] | None:
    if yaml is None or not path.exists():
        return None
    with path.open("r", encoding="utf-8") as h:
        data = yaml.safe_load(h) or {}
    return data if isinstance(data, dict) else None


def venv_python() -> str:
    vp = ROOT / ".venv" / "bin" / "python"
    return str(vp) if vp.exists() else (sys.executable or "python3")


def run_cmd(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True, check=False)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def git_tracked() -> list[str]:
    code, out, _ = run_cmd(["git", "ls-files"])
    if code != 0:
        return []
    return [l for l in out.splitlines() if l]


def check_env_tracking(state: GateState, tracked: list[str]) -> None:
    if any(p == ".env" or p.endswith("/.env") for p in tracked):
        state.block("env_tracking", ".env 被 Git 跟踪，请先 untrack")
    else:
        state.passed("env_tracking", ".env 未被跟踪")


def check_wechat_mock_default(state: GateState) -> None:
    example = ROOT / ".env.example"
    if not example.exists():
        state.warn("wechat_mode", "缺少 .env.example")
        return
    text = example.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"^WECHAT_MODE\s*=\s*mock", text, re.MULTILINE):
        state.passed("wechat_mode", "默认 WECHAT_MODE=mock")
    else:
        state.warn("wechat_mode", ".env.example 未声明 WECHAT_MODE=mock")


def get_current_round_id() -> str:
    data = load_yaml(ROUND_STATE_PATH) or {}
    cur = data.get("current_round", {})
    if isinstance(cur, dict):
        return str(cur.get("id", "round_000"))
    return "round_000"


def round_smoke(round_id: str, py: str) -> tuple[bool, str]:
    """按轮次运行 CLI 冒烟（需已 init-db 与示例配置）。"""
    base = [py, "-m", "wechat_article_scheduler.cli"]
    if round_id == "round_000":
        steps = [
            ([*base, "init-db"], "init-db"),
            ([*base, "scan"], "scan"),
            ([*base, "plan"], "plan"),
            ([*base, "run-once"], "run-once"),
        ]
    elif round_id == "round_001":
        steps = [([py, "-m", "pytest", "tests/test_workflow.py", "-q"], "pytest workflow")]
    elif round_id == "round_002":
        steps = [([*base, "events", "--limit", "5"], "events")]
    elif round_id == "round_003":
        steps = [([py, "-m", "pytest", "tests/test_real_adapter.py", "-q"], "pytest real adapter")]
    elif round_id == "round_004":
        steps = [([py, "scripts/check_repo_contract.py"], "check_repo_contract")]
    elif round_id == "round_005":
        steps = [([py, "-m", "pytest", "tests/test_real_adapter.py", "-q"], "pytest real adapter")]
    elif round_id == "round_006":
        steps = [([py, "-m", "pytest", "tests/test_web_app.py", "-q"], "pytest web app")]
    elif round_id == "round_007":
        steps = [([py, "-m", "pytest", "tests/test_scheduler_hardening.py", "-q"], "pytest hardening")]
    else:
        return True, "unknown round skipped"

    notes = []
    for cmd, name in steps:
        code, so, se = run_cmd(cmd)
        if code != 0:
            return False, f"{name} failed (exit {code}): {se or so}"
        notes.append(f"{name}: ok")
    return True, "; ".join(notes)


def run_pytest(py: str) -> tuple[bool, str]:
    code, so, se = run_cmd([py, "-m", "pytest", "-q"])
    if code != 0:
        return False, se or so
    return True, so.strip() or "pytest ok"


def advance_round_state(current_id: str) -> str | None:
    """将 round_state 推进到下一轮；若已是最后一轮则返回 None。"""
    if yaml is None:
        return None
    try:
        idx = ROUND_ORDER.index(current_id)
    except ValueError:
        idx = 0
    if idx >= len(ROUND_ORDER) - 1:
        return None
    next_id = ROUND_ORDER[idx + 1]
    data = load_yaml(ROUND_STATE_PATH) or {}
    data["current_round"] = {
        "id": next_id,
        "name": f"Round {idx + 1}",
        "status": "active",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    data["last_completed_round"] = {
        "id": current_id,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    ROUND_STATE_PATH.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return next_id


def git_commit_round(round_id: str) -> tuple[bool, str]:
    run_cmd(["git", "add", "-A"])
    msg = f"chore(agent_gate): complete {round_id}\n\nAutomated round gate commit."
    code, so, se = run_cmd(["git", "commit", "-m", msg])
    if code != 0:
        if "nothing to commit" in (so + se):
            return True, "nothing to commit"
        return False, se or so
    return True, so.strip()


def git_push_main() -> tuple[bool, str]:
    code, so, se = run_cmd(["git", "push", "origin", "main"])
    if code != 0:
        return False, se or so
    return True, so.strip()


def write_report(state: GateState, extra: dict[str, str]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Agent Gate Report",
        "",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        f"- verdict: **{state.verdict}**",
        "",
    ]
    for f in state.findings:
        if f.severity != PASS:
            lines.append(f"- [{f.severity}] {f.check}: {f.message}")
    for k, v in extra.items():
        lines.append(f"- {k}: {v}")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true", help="不提交、不推进 round")
    args = parser.parse_args()

    state = GateState()
    tracked = git_tracked()
    check_env_tracking(state, tracked)
    check_wechat_mock_default(state)

    if not (ROOT / "governance" / "repo_protocol_standard.yaml").exists():
        state.block("protocol", "governance/repo_protocol_standard.yaml missing")
    else:
        state.passed("protocol", "protocol present")

    py = venv_python()
    ok, msg = run_pytest(py)
    if ok:
        state.passed("pytest", msg)
    else:
        state.block("pytest", msg[:800])

    round_id = get_current_round_id()
    smoke_ok, smoke_msg = round_smoke(round_id, py)
    if smoke_ok:
        state.passed("round_smoke", f"{round_id}: {smoke_msg}")
    else:
        state.block("round_smoke", smoke_msg[:800])

    extra: dict[str, str] = {"current_round": round_id}
    write_report(state, extra)

    print(f"Agent gate: {state.verdict} (round={round_id})")
    if state.verdict == BLOCKED:
        return EXIT_CODE[BLOCKED]

    if args.check_only:
        return EXIT_CODE[state.verdict]

    # 提交并推进
    committed, cmsg = git_commit_round(round_id)
    extra["git_commit"] = cmsg
    if not committed:
        state.block("git_commit", cmsg)
        write_report(state, extra)
        return EXIT_CODE[BLOCKED]

    nxt = advance_round_state(round_id)
    if nxt:
        extra["advanced_to"] = nxt
        print(f"Advanced round: {round_id} -> {nxt}")
    else:
        extra["advanced_to"] = "complete"
        print("All rounds complete")

    push_ok, push_msg = git_push_main()
    extra["git_push"] = push_msg if push_ok else f"skipped/failed: {push_msg}"
    write_report(state, extra)

    return EXIT_CODE[state.verdict]


if __name__ == "__main__":
    raise SystemExit(main())
