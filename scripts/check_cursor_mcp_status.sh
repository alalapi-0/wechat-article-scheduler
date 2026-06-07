#!/usr/bin/env bash
# 检查 Cursor CLI 层 MCP 状态（不打印任何 key / token）。
# 重要：该脚本只检查 CLI 层，不代表当前 Agent 对话线程已暴露工具。
# 对话线程检查见 docs/cursor_tool_registry_check.md

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCP_JSON="${ROOT}/.cursor/mcp.json"

echo "== Cursor MCP CLI Status Check =="
echo "Repo: ${ROOT}"
echo ""

# --- cursor-agent availability ---
if ! command -v cursor-agent >/dev/null 2>&1; then
  echo "[INFO] cursor-agent 未安装或不在 PATH 中。"
  echo "       跳过 cursor-agent mcp list / list-tools 检查。"
  echo "       仍可通过 npm run check:mcp 检查 .cursor/mcp.json 配置。"
  echo ""
  echo "== 重要提示 =="
  echo "该脚本（及 cursor-agent CLI）只检查 CLI / 配置层。"
  echo "不代表当前 Agent 对话线程已暴露 MCP 工具。"
  echo "浏览器任务开始前必须在对话中确认工具可用；见 docs/cursor_tool_registry_check.md"
  exit 0
fi

echo "[OK] 找到 cursor-agent: $(command -v cursor-agent)"
echo ""

# --- mcp list ---
echo "--- cursor-agent mcp list ---"
if cursor-agent mcp list 2>&1; then
  :
else
  echo "[WARN] cursor-agent mcp list 执行失败（可能需在 Cursor 内批准 MCP 或重启 Cursor）"
fi
echo ""

# --- helpers ---
list_tools() {
  local server="$1"
  echo "--- cursor-agent mcp list-tools ${server} ---"
  if cursor-agent mcp list-tools "${server}" 2>&1; then
    echo "[OK] ${server}: list-tools 成功"
  else
    echo "[WARN] ${server}: list-tools 失败或未加载（可能需 Settings → Tools & MCP 批准并完全重启 Cursor）"
  fi
  echo ""
}

# --- standard servers ---
STANDARD_SERVERS=(
  chrome-devtools
  playwright
  stitch
  filesystem
  context7
  github
)

for srv in "${STANDARD_SERVERS[@]}"; do
  list_tools "${srv}"
done

# --- wechat-chrome-session (wechat project) ---
if [[ -f "${MCP_JSON}" ]] && grep -q '"wechat-chrome-session"' "${MCP_JSON}" 2>/dev/null; then
  list_tools "wechat-chrome-session"
  list_tools "wechat_chrome_session"
fi

echo "== 重要提示 =="
echo "该脚本只检查 CLI 层，不代表当前 Agent 对话线程已暴露工具。"
echo ""
echo "若 list / list-tools 显示 not loaded 或 needs approval："
echo "  1. 打开 Cursor Settings → Tools & MCP"
echo "  2. 批准所需 MCP server"
echo "  3. 完全退出 Cursor 并重新打开本仓库"
echo "  4. 新建普通前台 Agent 对话（禁用 Multitask）"
echo "  5. 在对话中确认 chrome-devtools / playwright / stitch 等工具可见"
echo ""
echo "文档：docs/cursor_tool_registry_check.md"
echo "      docs/cursor_browser_ui_runbook.md"
