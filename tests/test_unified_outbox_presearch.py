"""Phase5 统一 outbox 预研 dry-run。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.core.unified_outbox_presearch import (
    build_unified_outbox_dry_run,
    index_outbox_directories,
)
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config

ROOT = Path(__file__).resolve().parents[1]


def test_index_outbox_empty_or_existing():
    summary = index_outbox_directories(ROOT, scan_roots=["outbox"])
    assert summary["scan_roots"] == ["outbox"]
    assert summary["package_count"] >= 0


def test_unified_outbox_dry_run_includes_manifest_summary():
    summary = build_unified_outbox_dry_run(ROOT)
    assert summary["phase"] == "phase5_unified_outbox"
    assert summary["publish_manifest_summary"] is not None
    assert summary["publish_manifest_summary"]["manifest_count"] >= 2
    assert "移动" in " ".join(summary["guardrails"])


def test_index_reads_sample_package(tmp_path: Path) -> None:
    ob = tmp_path / "outbox" / "demo-pkg"
    ob.mkdir(parents=True)
    (ob / "article.md").write_text("# t", encoding="utf-8")
    (ob / "manifest.json").write_text(
        json.dumps(
            {
                "platform": "zhihu",
                "article_id": 1,
                "title": "测试",
                "exported_at": "2026-06-02T12:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    idx = index_outbox_directories(tmp_path, scan_roots=["outbox"])
    assert idx["package_count"] == 1
    assert idx["by_platform"]["zhihu"][0]["title"] == "测试"


def test_api_unified_outbox_dry_run(tmp_path: Path) -> None:
    db_path = tmp_path / "u.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    client = TestClient(create_app(cfg))
    r = client.get("/api/unified-outbox/dry-run")
    assert r.status_code == 200
    assert r.json()["phase"] == "phase5_unified_outbox"
