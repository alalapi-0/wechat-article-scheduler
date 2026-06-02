"""Round 130：文章详情页（高级开）展示 publish-dry-run 摘要。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r130.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def _insert_article(db_path: Path) -> int:
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/r130.md', '详情 dry-run', 'S', 'B', 'h130', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    return aid


def test_detail_page_dry_run_markup(client: TestClient, tmp_path: Path) -> None:
    aid = _insert_article(tmp_path / "r130.sqlite3")
    html = client.get(f"/articles/{aid}").text
    assert 'id="dryRunCard"' in html
    assert 'id="dryRunSummary"' in html
    assert 'id="dryRunJson"' in html
    assert "loadPublishDryRun" in html
    assert "renderDetailDryRun" in html
    assert "/publish-dry-run" in html
    assert "发布 dry-run" in html
    assert "wechat_workbench_show_advanced" in html


def test_publish_dry_run_api_for_detail(client: TestClient, tmp_path: Path) -> None:
    aid = _insert_article(tmp_path / "r130.sqlite3")
    data = client.get(f"/api/articles/{aid}/publish-dry-run").json()
    assert data["ok"] is True
    assert data["mode"] == "dry_run"
    assert data["mock_safe"] is True
    assert data["gate_summary"]
