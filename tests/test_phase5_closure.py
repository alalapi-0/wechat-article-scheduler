"""Phase5 收口摘要 round_107。"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.core.phase5_closure_summary import build_phase5_closure_summary
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config

ROOT = Path(__file__).resolve().parents[1]


def test_phase5_closure_summary(tmp_path: Path) -> None:
    db_path = tmp_path / "p5.sqlite3"
    db.init_db(db_path)
    (tmp_path / "articles" / "inbox").mkdir(parents=True)
    cfg = make_test_config(tmp_path, db_path)
    summary = build_phase5_closure_summary(cfg)
    assert summary["phase"] == "phase5_closure"
    assert "round_103" in summary["agent_rounds"][0]
    assert summary["modules"]["round_103_multi_project"]["manifest_count"] >= 2


def test_phase5_closure_api(tmp_path: Path) -> None:
    db_path = tmp_path / "api.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    client = TestClient(create_app(cfg))
    r = client.get("/api/phase5/closure-summary")
    assert r.status_code == 200
    assert r.json()["phase"] == "phase5_closure"


def test_closure_doc_exists() -> None:
    assert (ROOT / "docs" / "phase5_closure.md").is_file()
