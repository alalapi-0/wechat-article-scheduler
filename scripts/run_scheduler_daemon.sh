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

PY="${ROOT}/.venv/bin/python"
if [[ ! -x "${PY}" ]]; then
  echo "未找到 ${PY}；请先按 README 初始化虚拟环境" >&2
  exit 1
fi

mkdir -p "${ROOT}/data/logs"
echo "[$(date -Iseconds)] scheduler-daemon start mode=${WECHAT_MODE} root=${ROOT}" >> "${ROOT}/data/logs/scheduler-daemon.log"

exec "${PY}" -m wechat_article_scheduler.cli scheduler-daemon "$@"
