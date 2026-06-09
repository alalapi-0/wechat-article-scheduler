#!/usr/bin/env python3
"""轻量只读工具探针：盘点当前环境可用工具，输出 reports/tool_probe_report.json。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "tool_probe_report.json"


def probe_command(name: str, cmd: list[str], *, timeout: int = 15) -> dict:
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (result.stdout or result.stderr or "").strip()
        return {
            "name": name,
            "command": " ".join(cmd),
            "available": result.returncode == 0,
            "exit_code": result.returncode,
            "output": out[:500],
        }
    except FileNotFoundError:
        return {
            "name": name,
            "command": " ".join(cmd),
            "available": False,
            "exit_code": None,
            "output": "command not found",
        }
    except subprocess.TimeoutExpired:
        return {
            "name": name,
            "command": " ".join(cmd),
            "available": False,
            "exit_code": None,
            "output": "timeout",
        }


def probe_mcp_config() -> dict:
    mcp_path = ROOT / ".cursor" / "mcp.json"
    servers: list[dict] = []
    configured = mcp_path.is_file()
    if configured:
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        for name, cfg in (data.get("mcpServers") or {}).items():
            servers.append(
                {
                    "name": name,
                    "configured": True,
                    "callable_now": "unknown",
                    "safe_probe_command": "npm run check:mcp",
                    "probe_result": "config_present",
                    "allowed_scope": "workspace",
                    "recommended_use_cases": [],
                    "risks": ["requires Cursor thread tool registry"],
                    "fallback": "shell + local scripts",
                }
            )
    return {
        "configured": configured,
        "path": str(mcp_path.relative_to(ROOT)),
        "servers": servers,
        "thread_note": "callable_now must be verified in active Agent thread tool list",
    }


def main() -> int:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()

    probes = [
        probe_command("shell", ["pwd"]),
        probe_command("git", ["git", "status", "--short"]),
        probe_command("git_branch", ["git", "branch", "--show-current"]),
        probe_command("node", ["node", "-v"]),
        probe_command("npm", ["npm", "-v"]),
        probe_command("python3", ["python3", "--version"]),
        probe_command("uv", ["uv", "--version"]),
        probe_command("pytest", ["pytest", "--version"]),
        probe_command("gh", ["gh", "--version"]),
        probe_command("make", ["make", "--version"]),
        probe_command("ffmpeg", ["ffmpeg", "-version"]),
        probe_command("playwright_npx", ["npx", "playwright", "--version"]),
        probe_command("mcp_check", ["npm", "run", "check:mcp"]),
    ]

    mcp = probe_mcp_config()
    cursor_rules = list((ROOT / ".cursor" / "rules").glob("*")) if (ROOT / ".cursor" / "rules").is_dir() else []

    report = {
        "version": 1,
        "timestamp": ts,
        "repo": str(ROOT),
        "agent_surface": os.environ.get("AGENT_SURFACE", "cursor"),
        "curator_config_visibility": "limited",
        "curator_notes": [
            "MCP callable_now requires verification in active thread tool registry",
            "Cursor UI settings (Cloud Agent, Hooks) need manual confirmation",
        ],
        "codex_available": "unknown",
        "web_search": {
            "available": True,
            "tool": "WebSearch (Cursor agent)",
            "note": "Official docs preferred; encode findings in docs/RESEARCH_NOTES.md",
        },
        "probes": probes,
        "mcp": mcp,
        "cursor_rules_count": len(cursor_rules),
        "cursor_rules": [p.name for p in sorted(cursor_rules)],
        "remote": {
            "configured": (ROOT / ".git").is_dir(),
            "origin": probe_command("git_remote", ["git", "remote", "-v"]),
        },
    }

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"tool_probe: wrote {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
