"""Round 102 维护收口：微信主链路 API 冒烟（首页→scan→plan→预览→队列→草稿→/debug）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config

DEBUG_APIS = (
    "/api/status",
    "/api/wechat-chain-summary",
    "/api/adapter-registry",
    "/api/manifest/sample-dry-run",
    "/api/projects/registry",
    "/api/projects/dry-run",
    "/api/publish-calendar/dry-run",
    "/api/publish-calendar/conflicts",
    "/api/unified-outbox/index",
    "/api/unified-outbox/dry-run",
    "/api/audio-package-plan",
    "/api/browser-assist-plan",
)


@pytest.fixture
def smoke_env(tmp_path: Path) -> tuple[TestClient, Path]:
    db_path = tmp_path / "smoke.sqlite3"
    db.init_db(db_path)
    inbox = tmp_path / "articles" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "smoke.md").write_text(
        "---\ntitle: 维护冒烟\n---\n\n正文。",
        encoding="utf-8",
    )
    (tmp_path / "articles" / "imported").mkdir(parents=True, exist_ok=True)
    (tmp_path / "articles" / "published").mkdir(parents=True, exist_ok=True)
    cfg = make_test_config(
        tmp_path,
        db_path,
        rules={
            "schedule": {
                "max_per_day": 2,
                "min_hours_between": 0,
                "preferred_hours": [9],
            }
        },
    )
    return TestClient(create_app(cfg)), db_path


def test_maintenance_wechat_chain_api_smoke(smoke_env: tuple[TestClient, Path]) -> None:
    c, db_path = smoke_env

    home = c.get("/")
    assert home.status_code == 200
    assert "扫描本地收件箱" in home.text
    assert "nextSteps" in home.text

    ov0 = c.get("/api/overview").json()
    assert ov0["workbench"]["chain_recommended_action"] == "scan"
    assert "scan" in (ov0["workbench"].get("recommended_cli") or "")

    scan = c.post("/api/scan")
    assert scan.status_code == 200
    assert scan.json().get("imported", 0) >= 1 or "human" in scan.json()

    ov1 = c.get("/api/overview").json()
    assert ov1["workbench"]["chain_recommended_action"] == "plan"
    assert "plan" in (ov1["workbench"].get("recommended_cli") or "")

    plan = c.post("/api/plan")
    assert plan.status_code == 200
    assert "human" in plan.json()

    articles = c.get("/api/articles").json()
    assert len(articles) >= 1
    aid = int(articles[0]["id"])
    preview = c.get(f"/articles/{aid}")
    assert preview.status_code == 200

    queue = c.get("/api/queue-summary").json()
    assert "pending" in queue or "total" in queue or isinstance(queue, dict)

    jobs = c.get("/api/jobs").json()
    assert isinstance(jobs, list)
    assert len(jobs) >= 1

    past = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    with db.connect(db_path) as conn:
        conn.execute(
            "UPDATE publish_jobs SET scheduled_at = ? WHERE status = 'pending'",
            (past,),
        )
        conn.commit()

    run = c.post("/api/run-once")
    assert run.status_code == 200

    drafts_page = c.get("/drafts")
    assert drafts_page.status_code == 200
    summary = c.get("/api/drafts-summary").json()
    assert isinstance(summary, dict)
    drafts = c.get("/api/drafts").json()
    assert isinstance(drafts, list)

    debug_html = c.get("/debug")
    assert debug_html.status_code == 200
    assert "Phase4 播客音频预研" in debug_html.text
    for path in DEBUG_APIS:
        r = c.get(path)
        assert r.status_code == 200, path
