"""Phase5 运维健康 dry-run 与 runbook 清单。"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.core.ops_health_presearch import build_ops_health_dry_run
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config

ROOT = Path(__file__).resolve().parents[1]


def test_ops_health_dry_run(tmp_path: Path) -> None:
    db_path = tmp_path / "ops.sqlite3"
    db.init_db(db_path)
    (tmp_path / "articles" / "inbox").mkdir(parents=True)
    cfg = make_test_config(tmp_path, db_path)
    summary = build_ops_health_dry_run(cfg)
    assert summary["phase"] == "phase5_ops_maintenance"
    assert summary["metrics"]["database"]["exists"] is True
    assert len(summary["runbook_checklist"]) >= 5
    assert any(c["auto_check"] == "manual_only" for c in summary["runbook_checklist"])


def test_ops_api(tmp_path: Path) -> None:
    db_path = tmp_path / "api.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    client = TestClient(create_app(cfg))
    assert client.get("/api/ops/health-dry-run").status_code == 200
    chk = client.get("/api/ops/runbook-checklist").json()
    assert "items" in chk


def test_deploy_examples_listed_in_repo(tmp_path: Path) -> None:
    db_path = tmp_path / "ops2.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(ROOT, db_path)
    summary = build_ops_health_dry_run(cfg)
    examples = summary["deploy_examples_in_repo"]
    assert all(e["present"] for e in examples)
