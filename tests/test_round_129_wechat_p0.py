"""Round 129：GET /api/articles/{id}/publish-dry-run 与高级面板 advDryRun。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.publish_dry_run import build_article_publish_dry_run
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r129.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def _insert_article(db_path: Path) -> int:
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/r129.md', 'Dry-run 作品', 'S', 'B', 'h129', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    return aid


def test_publish_dry_run_api_mock_safe(client: TestClient, tmp_path: Path) -> None:
    aid = _insert_article(tmp_path / "r129.sqlite3")
    data = client.get(f"/api/articles/{aid}/publish-dry-run").json()
    assert data["ok"] is True
    assert data["mode"] == "dry_run"
    assert data["mock_safe"] is True
    assert data["network"] is False
    assert data["gate_summary"]
    assert data["report"]["simulated_steps"]
    assert "wechat_app_secret" not in str(data).lower()


def test_publish_dry_run_404(client: TestClient) -> None:
    r = client.get("/api/articles/99999/publish-dry-run")
    assert r.status_code == 404


def test_build_article_publish_dry_run_direct(tmp_path: Path) -> None:
    db_path = tmp_path / "r129b.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    aid = _insert_article(db_path)
    with db.connect(db_path) as conn:
        out = build_article_publish_dry_run(cfg, conn, aid)
    assert out["ok"] is True
    assert out["mock_safe"] is True


def test_home_adv_dry_run_markup(client: TestClient) -> None:
    html = client.get("/").text
    assert 'id="advDryRun"' in html
    assert "renderPublishDryRunPanel" in html
    assert "/publish-dry-run" in html
    assert "发布 dry-run" in html
