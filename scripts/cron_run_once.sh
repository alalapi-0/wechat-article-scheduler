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

if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PY="${ROOT}/.venv/bin/python"
else
  PY="python3"
fi

exec "${PY}" -m wechat_article_scheduler.cli run-once "$@"
