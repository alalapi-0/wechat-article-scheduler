#!/usr/bin/env python3
"""用户视角测试入口（dry-run 默认）：检查 Web 工作台关键路径与产物格式。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "docs" / "reports" / "ux_loop"


def main() -> int:
    parser = argparse.ArgumentParser(description="User-view test runner (safe defaults)")
    parser.add_argument("--dry-run", action="store_true", help="Do not start server or hit network")
    parser.add_argument("--pytest", action="store_true", help="Run pytest user-view subset")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORT_DIR / f"USER_VIEW_{ts}.json"

    checks: list[dict] = []

    template = ROOT / "src/wechat_article_scheduler/web/drafts_page_template.html"
    checks.append(
        {
            "name": "drafts_template_exists",
            "ok": template.is_file(),
            "detail": str(template.relative_to(ROOT)),
        }
    )

    app_module = ROOT / "src/wechat_article_scheduler/web/app.py"
    checks.append(
        {
            "name": "web_app_module_exists",
            "ok": app_module.is_file(),
            "detail": "FastAPI workbench entry",
        }
    )

    if args.pytest and not args.dry_run:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_user_view_rounds_abcd.py", "-q"],
            cwd=ROOT,
        )
        checks.append({"name": "pytest_user_view", "ok": proc.returncode == 0, "exit_code": proc.returncode})
    elif args.pytest:
        checks.append({"name": "pytest_user_view", "ok": True, "detail": "skipped in dry-run"})

    ok = all(c.get("ok", False) for c in checks)
    payload = {
        "timestamp": ts,
        "dry_run": args.dry_run,
        "status": "passed" if ok else "failed",
        "checks": checks,
        "next_steps": [
            "Start: python -m wechat_article_scheduler.cli serve",
            "Open: http://127.0.0.1:8080/",
            "Use playwright or chrome-devtools MCP for console/network/screenshots",
        ],
    }
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
