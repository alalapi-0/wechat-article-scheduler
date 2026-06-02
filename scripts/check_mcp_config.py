#!/usr/bin/env python3
"""检查 .cursor/mcp.json 是否存在、可解析且符合项目 MCP 安全约定。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MCP_PATH = ROOT / ".cursor" / "mcp.json"

SECRET_KEY_PATTERN = re.compile(
    r"(token|secret|password|api[_-]?key|authorization)",
    re.IGNORECASE,
)
SECRET_VALUE_PATTERN = re.compile(r"^(ghp_|gho_|ghu_|ghs_|ghr_|sk-|Bearer\s)", re.IGNORECASE)

DANGEROUS_PATH_EXACT = {"/", "\\", "C:\\", "C:/", "~", "${userHome}"}
HOME_ROOT_PATTERN = re.compile(r"^(/Users/[^/]+|/home/[^/]+)$")


def _redact_env(env: dict[str, Any]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in env.items():
        if SECRET_KEY_PATTERN.search(key) or (
            isinstance(value, str) and SECRET_VALUE_PATTERN.match(value.strip())
        ):
            redacted[key] = "<redacted>"
        elif isinstance(value, str) and value.startswith("${env:"):
            redacted[key] = value
        else:
            redacted[key] = "<set>"
    return redacted


def _check_filesystem_args(args: list[Any]) -> list[str]:
    issues: list[str] = []
    path_args = [a for a in args if isinstance(a, str) and not a.startswith("-")]
    for arg in path_args:
        normalized = arg.strip()
        if normalized in DANGEROUS_PATH_EXACT:
            issues.append(f"filesystem 授权路径过于宽泛: {normalized!r}")
        elif HOME_ROOT_PATTERN.match(normalized):
            issues.append(f"filesystem 指向用户主目录根路径: {normalized!r}")
        elif normalized == "/":
            issues.append("filesystem 指向系统根目录 /")
    if path_args and "${workspaceFolder}" not in path_args:
        issues.append(
            "filesystem 未使用 ${workspaceFolder}；请确认仅授权当前项目目录"
        )
    return issues


def _summarize_server(name: str, cfg: dict[str, Any]) -> str:
    cmd = cfg.get("command", "?")
    args = cfg.get("args", [])
    env = cfg.get("env", {})
    parts = [f"{name}: command={cmd!r}"]
    if args:
        safe_args = []
        for a in args:
            if isinstance(a, str) and SECRET_VALUE_PATTERN.match(a.strip()):
                safe_args.append("<redacted>")
            else:
                safe_args.append(a)
        parts.append(f"args={safe_args!r}")
    if env:
        parts.append(f"env={_redact_env(env)!r}")
    return ", ".join(parts)


def main() -> int:
    if not MCP_PATH.is_file():
        print("check_mcp_config: FAIL")
        print(f"  missing: {MCP_PATH.relative_to(ROOT)}")
        return 1

    try:
        raw = MCP_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print("check_mcp_config: FAIL")
        print(f"  invalid JSON: {exc}")
        return 1

    servers: dict[str, Any] = data.get("mcpServers") or {}
    if not servers:
        print("check_mcp_config: FAIL")
        print("  mcpServers is empty")
        return 1

    issues: list[str] = []
    warnings: list[str] = []

    if "playwright" not in servers:
        issues.append("缺少 playwright MCP（浏览器 E2E 验收必需）")

    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            issues.append(f"server {name!r} 配置不是 object")
            continue
        env = cfg.get("env") or {}
        if isinstance(env, dict):
            for key, value in env.items():
                if isinstance(value, str) and SECRET_VALUE_PATTERN.match(value.strip()):
                    issues.append(f"{name}: env.{key} 含疑似硬编码密钥，应改用 ${{env:...}}")

        if name == "filesystem":
            args = cfg.get("args") or []
            if isinstance(args, list):
                issues.extend(_check_filesystem_args(args))
            else:
                issues.append("filesystem args 必须是数组")

    if "github" in servers and "GITHUB_TOKEN" not in str(
        servers["github"].get("env", {})
    ):
        warnings.append(
            "github MCP 未引用 ${env:GITHUB_TOKEN}；请确认 token 通过环境变量注入"
        )

    print("check_mcp_config: PASS" if not issues else "check_mcp_config: FAIL")
    print(f"  path: {MCP_PATH.relative_to(ROOT)}")
    print(f"  servers ({len(servers)}): {', '.join(sorted(servers))}")
    for name in sorted(servers):
        if isinstance(servers[name], dict):
            print(f"  - {_summarize_server(name, servers[name])}")

    for w in warnings:
        print(f"  warning: {w}")
    for issue in issues:
        print(f"  issue: {issue}")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
