#!/usr/bin/env bash
# 常驻调度入口：供 launchd / systemd 调用。默认 WECHAT_MODE=mock。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
  set +a
fi

export WECHAT_MODE="${WECHAT_MODE:-mock}"

if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PY="${ROOT}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  echo "未找到 python3 或 .venv/bin/python" >&2
  exit 1
fi

mkdir -p "${ROOT}/data/logs"
echo "[$(date -Iseconds)] scheduler-daemon start mode=${WECHAT_MODE} root=${ROOT}" >> "${ROOT}/data/logs/scheduler-daemon.log"

exec "${PY}" -m wechat_article_scheduler.cli scheduler "$@"
