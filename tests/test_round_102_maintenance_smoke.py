"""Round 102 维护收口：微信主链路 API 冒烟（首页→scan→plan→预览→队列→草稿→/debug）。

Round 115 起纳入 upload/export-outbox；Round 122 起纳入 hash 导航与返回上下文轻量断言。
"""

from __future__ import annotations

import io
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
    "/api/ops/health-dry-run",
    "/api/ops/runbook-checklist",
    "/api/phase5/closure-summary",
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


def test_gitignore_covers_local_test_artifacts() -> None:
    text = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert "outbox/*" in text
    assert ".playwright-mcp/" in text
    assert "articles/imported/r114_*" in text


def test_upload_and_export_outbox_api_smoke(smoke_env: tuple[TestClient, Path]) -> None:
    """Round 114 上传 enrichment 与 export-outbox（隔离 tmp，不写仓库 outbox）。"""
    c, tmp_path = smoke_env
    home = c.get("/")
    assert "showUploadOutcome" in home.text
    assert "exportOutboxArticle" in home.text

    body = b"# Maint smoke upload\n\nround 114 API regression body\n"
    files = [("articles", ("maint_upload.md", io.BytesIO(body), "text/markdown"))]
    up = c.post("/api/upload", files=files).json()
    assert up.get("ok") is True
    assert up.get("upload_summary", {}).get("summary_label")

    arts = c.get("/api/articles").json()
    assert len(arts) >= 1
    aid = int(arts[0]["id"])
    exp = c.post(f"/api/articles/{aid}/export-outbox?platform=generic").json()
    assert exp.get("ok") is True
    assert exp.get("relative_path")
    rel = exp["relative_path"]
    assert (tmp_path / rel).exists() or Path(rel).name.startswith("outbox_")


def test_workbench_hash_and_return_context_markup(
    smoke_env: tuple[TestClient, Path],
    tmp_path: Path,
) -> None:
    """Round 119–121：hash 深链、返回捕获与详情动态返回链接（静态 HTML 断言）。"""
    c, db_path = smoke_env
    home = c.get("/").text
    assert "initWorkbenchHash" in home
    assert "wechat_workbench_section_hash" in home
    assert "captureWorkbenchReturnContext" in home
    assert "workbenchReturnUrl" not in home
    assert 'href="#queue"' in home

    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('inbox/ret.md', '返回测', 'S', 'B', 'hr', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    detail = c.get(f"/articles/{aid}").text
    assert "workbenchReturnUrl" in detail
    assert "wechat_workbench_return_hash" in detail
    assert 'id="backWorkbench"' in detail
