#!/usr/bin/env bash
# cron 用：每分钟执行一次 run-once（勿与常驻 scheduler 同时启用）。
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

exec "${PY}" -m wechat_article_scheduler.cli run-once "$@"
