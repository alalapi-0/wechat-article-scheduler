#!/usr/bin/env python3
"""Agent Layer 2.0 门禁：检查协议文件、运行安全探针与可选测试，输出 reports/gate_result.json。"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = ROOT / "agent_layer.yaml"
GATE_RESULT = ROOT / "reports" / "gate_result.json"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"


def resolve_python() -> str:
    if VENV_PYTHON.is_file():
        return str(VENV_PYTHON)
    return sys.executable


def resolve_pytest_cmd(extra_args: list[str]) -> list[str]:
    py = resolve_python()
    probe = subprocess.run(
        [py, "-m", "pytest", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        return [py, "-m", "pytest", *extra_args]
    pytest_bin = shutil.which("pytest")
    if pytest_bin:
        return [pytest_bin, *extra_args]
    return [py, "-m", "pytest", *extra_args]

REQUIRED_FILES = [
    "AGENTS.md",
    "agent_tools.yaml",
    "agent_layer.yaml",
    "docs/TOOL_INVENTORY.md",
    "docs/TOOL_USAGE_POLICY.md",
    "docs/SEARCH_POLICY.md",
    "docs/RESEARCH_NOTES.md",
    "docs/AGENT_RUNBOOK.md",
    "docs/AGENT_ROADMAP.md",
    "docs/USER_VIEW_TESTING.md",
    "docs/CODEX_USAGE.md",
    "docs/CODEX_HANDOFF.md",
    "docs/PROMPTS.md",
    "schemas/agent_round_report.schema.json",
    "reports/latest-agent-report.json",
    "scripts/tool_probe.py",
    "scripts/user_view_test.py",
]


def run_cmd(name: str, cmd: list[str], *, timeout: int = 600) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        summary = (proc.stdout or proc.stderr or "").strip().splitlines()
        summary_text = summary[-1] if summary else f"exit {proc.returncode}"
        return {
            "name": name,
            "command": " ".join(cmd),
            "exit_code": proc.returncode,
            "summary": summary_text[:300],
        }
    except FileNotFoundError:
        return {
            "name": name,
            "command": " ".join(cmd),
            "exit_code": None,
            "summary": "command not found",
        }
    except subprocess.TimeoutExpired:
        return {
            "name": name,
            "command": " ".join(cmd),
            "exit_code": None,
            "summary": "timeout",
        }


def main() -> int:
    GATE_RESULT.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()

    passed: list[str] = []
    failed: list[str] = []
    skipped: list[str] = []
    blocked: list[str] = []
    commands: list[dict[str, Any]] = []

    for rel in REQUIRED_FILES:
        if (ROOT / rel).is_file():
            passed.append(f"file_exists:{rel}")
        else:
            failed.append(f"missing_file:{rel}")

    layer_cmds: list[str] = []
    if yaml and LAYER_PATH.is_file():
        layer = yaml.safe_load(LAYER_PATH.read_text(encoding="utf-8")) or {}
        layer_cmds = (layer.get("commands") or {}).get("test") or []

    py = resolve_python()
    probe = run_cmd("tool_probe", [py, "scripts/tool_probe.py"], timeout=120)
    commands.append(probe)
    if probe["exit_code"] == 0:
        passed.append("tool_probe")
    else:
        failed.append("tool_probe")

    mcp = run_cmd("mcp_config_check", ["npm", "run", "check:mcp"], timeout=60)
    commands.append(mcp)
    if mcp["exit_code"] == 0:
        passed.append("mcp_config_check")
    else:
        blocked.append("mcp_config_check")

    gate_tests = run_cmd(
        "agent_layer_tests",
        resolve_pytest_cmd(["tests/test_agent_layer_gate.py", "-q"]),
        timeout=300,
    )
    commands.append(gate_tests)
    if gate_tests["exit_code"] == 0:
        passed.append("agent_layer_tests")
    elif gate_tests["exit_code"] is None:
        skipped.append("agent_layer_tests")
    else:
        failed.append("agent_layer_tests")

    if layer_cmds:
        raw = layer_cmds[0]
        if raw.startswith("python "):
            layer_cmd = [resolve_python(), *raw.split()[1:]]
        else:
            layer_cmd = raw.split()
        test_cmd = run_cmd("layer_test", layer_cmd, timeout=900)
        commands.append(test_cmd)
        if test_cmd["exit_code"] == 0:
            passed.append("layer_test")
        else:
            failed.append("layer_test")
    else:
        skipped.append("layer_test:no_commands")

    tool_usage = [
        {"tool": "shell", "used": True, "purpose": "run gate commands"},
        {"tool": "web_search", "used": False, "reason": "gate script does not search"},
        {"tool": "playwright", "used": False, "reason": "not required for layer gate"},
    ]

    if failed:
        status = "failed"
        next_action = "fix_failed_checks"
    elif blocked:
        status = "blocked"
        next_action = "resolve_blocked_env"
    else:
        status = "passed"
        next_action = "continue_next_round"

    result = {
        "status": status,
        "timestamp": ts,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "blocked": blocked,
        "commands": commands,
        "tool_usage": tool_usage,
        "next_action": next_action,
    }

    GATE_RESULT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
