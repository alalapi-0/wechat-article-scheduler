"""Round 81：知乎 browser_assist 评估 dry-run。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from wechat_article_scheduler.adapters.browser_assist import build_dry_run_plan
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "zhihu_browser_assist.md"


def test_zhihu_plan_has_assessment() -> None:
    plan = build_dry_run_plan(platform="zhihu", article_id="1")
    assert plan["platform"] == "zhihu"
    assert plan["status"] == "awaiting_human_confirmation"
    assert plan["assessment"]["recommendation"] == "conditional"
    assert len(plan["human_checkpoints"]) >= 5


def test_api_zhihu_browser_assist_plan(tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "b.sqlite3")
    client = TestClient(create_app(cfg))
    data = client.get("/api/browser-assist-plan?platform=zhihu").json()
    assert data["platform"] == "zhihu"
    plats = client.get("/api/browser-assist/platforms").json()
    assert "zhihu" in {p["id"] for p in plats["platforms"]}


def test_cli_zhihu_browser_assist_plan() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "wechat_article_scheduler.cli",
            "browser-assist-plan",
            "--platform",
            "zhihu",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["platform"] == "zhihu"


def test_zhihu_browser_assist_doc() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "dry-run" in text.lower() or "干跑" in text
