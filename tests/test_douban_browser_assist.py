"""Round 83：豆瓣 browser_assist 评估 dry-run。"""

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
DOC = ROOT / "docs" / "douban_browser_assist.md"


def test_douban_plan_assessment() -> None:
    plan = build_dry_run_plan(platform="douban", article_id="2")
    assert plan["platform"] == "douban"
    assert plan["assessment"]["recommendation"] == "conditional"
    assert len(plan["human_checkpoints"]) >= 6


def test_api_douban_browser_assist(tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "d.sqlite3")
    client = TestClient(create_app(cfg))
    data = client.get("/api/browser-assist-plan?platform=douban").json()
    assert data["platform"] == "douban"
    ids = {p["id"] for p in client.get("/api/browser-assist/platforms").json()["platforms"]}
    assert "douban" in ids


def test_cli_douban_plan() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "wechat_article_scheduler.cli",
            "browser-assist-plan",
            "--platform",
            "douban",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["platform"] == "douban"


def test_douban_doc() -> None:
    assert "douban" in DOC.read_text(encoding="utf-8")
