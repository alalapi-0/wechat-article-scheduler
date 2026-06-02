"""Round 73 / 收敛 Round 18：browser_assist 干跑计划。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from wechat_article_scheduler.adapters.browser_assist.workflow import (
    GUARDRAILS,
    HUMAN_CHECKPOINTS,
    build_dry_run_plan,
    browser_assist_field_rows,
)
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "browser_assist_runbook.md"


def test_guardrails_forbid_secrets_and_auto_publish() -> None:
    joined = " ".join(GUARDRAILS)
    assert "cookie" in joined or "密码" in joined
    assert "发布" in joined or "群发" in joined


def test_human_checkpoints_include_login_and_proof() -> None:
    ids = {c["id"] for c in HUMAN_CHECKPOINTS}
    assert "login" in ids
    assert "proof_backfill" in ids


def test_target_fields_from_matrix_gaps() -> None:
    rows = browser_assist_field_rows()
    ids = {r["field_id"] for r in rows}
    assert "wechat_backend_schedule" in ids
    assert "cover_crop" in ids


def test_dry_run_plan_awaits_human() -> None:
    plan = build_dry_run_plan(article_id="42", media_id="MOCK_1")
    assert plan["mode"] == "dry_run"
    assert plan["status"] == "awaiting_human_confirmation"
    assert plan["article_id"] == "42"
    assert plan["media_id"] == "MOCK_1"
    assert plan["target_field_ids"]
    assert plan["steps"]
    assert plan["proof_placeholder"]["screenshot_path"] is None


def test_runbook_doc_exists() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "browser_assist" in text
    assert "proof" in text.lower() or "proof" in text


def test_api_browser_assist_plan(tmp_path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "m.sqlite3")
    client = TestClient(create_app(cfg))
    data = client.get("/api/browser-assist-plan").json()
    assert data["status"] == "awaiting_human_confirmation"
    assert "guardrails" in data


def test_cli_browser_assist_plan() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "wechat_article_scheduler.cli",
            "browser-assist-plan",
            "--article-id",
            "1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["terminal_policy"]
