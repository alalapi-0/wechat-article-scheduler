"""用户视角测试报告四轮优化（Round 132–135）回归。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters import get_adapter
from wechat_article_scheduler.adapters.mock import MockWechatAdapter
from wechat_article_scheduler.capability_probe import (
    CAPABILITY_PUBLISHED_LIST,
    human_capability_summary,
    probe_freepublish_batchget,
)
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.external_agent.task_package import export_task_package
from wechat_article_scheduler.plan import build_plan
from wechat_article_scheduler.publish_config import publish_config_to_json, PublishConfig
from wechat_article_scheduler.remote_delete import build_delete_manifest, execute_remote_delete
from wechat_article_scheduler.remote_sync import sync_remote_drafts, upsert_remote_mirror
from wechat_article_scheduler.scheduler import run_due_jobs
from wechat_article_scheduler.field_settings import list_backend_field_capabilities
from wechat_article_scheduler.web.article_preflight import build_article_preflight_summary
from tests.conftest import make_test_config


def _cfg(root: Path, db_path: Path, **kw) -> AppConfig:
    rules = {
        "schedule": {
            "max_per_day": 5,
            "min_hours_between": 3,
            "preferred_hours": [9, 12, 15, 18, 21],
            "window_days": 7,
        },
        "publish": {"default_action": "draft", "auto_execute": True},
    }
    return make_test_config(
        root,
        db_path,
        rules=rules,
        schedule_window_days=7,
        max_articles_per_day=5,
        external_agent_task_export_enabled=True,
        **kw,
    )


def _seed_articles(conn, n: int) -> list[int]:
    ids: list[int] = []
    for i in range(n):
        cur = conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status, schedule_state)
            VALUES (?, ?, '', ?, ?, 'imported', 'imported')
            """,
            (f"/tmp/a{i}.md", f"文章{i:03d}", f"正文{i}", f"hash{i}"),
        )
        ids.append(int(cur.lastrowid))
    conn.commit()
    return ids


# --- Round A ---


def test_remote_sync_idempotent_five_drafts(tmp_path: Path) -> None:
    root = tmp_path
    db_path = root / "d.sqlite3"
    db.init_db(db_path)
    cfg = _cfg(root, db_path)
    first = sync_remote_drafts(cfg)
    assert first["synced"] == 5
    assert first["inserted"] == 5
    second = sync_remote_drafts(cfg)
    assert second["synced"] == 5
    assert second.get("inserted", 0) == 0
    assert second["unchanged"] == 5
    with db.connect(db_path) as conn:
        cnt = conn.execute("SELECT COUNT(*) AS c FROM remote_content_mirror").fetchone()["c"]
        assert cnt == 5


def test_freepublish_probe_unauthorized_not_zero(tmp_path: Path) -> None:
    adapter = MockWechatAdapter()
    probe = probe_freepublish_batchget(adapter)
    assert probe["state"] == "unauthorized"
    assert "未授权" in probe["message"]
    assert probe["item_count"] is None
    cached = {CAPABILITY_PUBLISHED_LIST: probe}
    human = human_capability_summary(cached)
    assert "未授权" in human["published_list"]
    assert "禁用" in human["published_delete"]


# --- Round B ---


def test_weekly_plan_three_weeks_zero_repeat(tmp_path: Path) -> None:
    root = tmp_path
    db_path = root / "d.sqlite3"
    db.init_db(db_path)
    cfg = _cfg(root, db_path)
    with db.connect(db_path) as conn:
        _seed_articles(conn, 100)

    week_planned: list[set[int]] = []
    for _week in range(3):
        stats = build_plan(cfg)
        assert 28 <= stats["planned"] <= 35
        with db.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT article_id FROM publish_jobs WHERE status = 'pending' ORDER BY id"
            ).fetchall()
            batch = {int(r["article_id"]) for r in rows}
            week_planned.append(batch)
            conn.execute(
                "UPDATE publish_jobs SET scheduled_at = datetime('now', '-1 minute') WHERE status = 'pending'"
            )
            conn.commit()
        run_due_jobs(cfg)

    assert week_planned[0].isdisjoint(week_planned[1])
    assert week_planned[1].isdisjoint(week_planned[2])
    assert len(week_planned[0]) == 35


def test_remote_draft_job_skips_create_draft(tmp_path: Path) -> None:
    root = tmp_path
    db_path = root / "d.sqlite3"
    db.init_db(db_path)
    cfg = _cfg(root, db_path)
    with db.connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('remote://x', '远端', '', 'body', 'h1', 'imported')
            """
        )
        aid = int(cur.lastrowid)
        conn.execute(
            """
            INSERT INTO publish_jobs
                (article_id, scheduled_at, status, adapter_mode, source_kind, remote_media_id, publish_config_json)
            VALUES (?, datetime('now', '-1 minute'), 'pending', 'mock', 'remote_draft', 'mock_remote_draft_001', ?)
            """,
            (aid, publish_config_to_json(PublishConfig(publish_action="draft", auto_execute=True))),
        )
        conn.commit()
    stats = run_due_jobs(cfg)
    assert stats["processed"] == 1
    assert stats.get("remote_draft_reused") == 1
    assert stats.get("drafted") == 1
    with db.connect(db_path) as conn:
        drafts = conn.execute("SELECT COUNT(*) AS c FROM wechat_drafts WHERE article_id = ?", (aid,)).fetchone()["c"]
        assert drafts == 0


# --- Round C ---


def test_field_capability_model() -> None:
    caps = list_backend_field_capabilities()
    ids = {c["field_id"] for c in caps}
    assert "fixed_collection" in ids
    assert "wechat_backend_schedule" in ids
    coll = next(c for c in caps if c["field_id"] == "fixed_collection")
    schedule = next(c for c in caps if c["field_id"] == "wechat_backend_schedule")
    notify = next(c for c in caps if c["field_id"] == "recommend_notify")
    assert coll["level"] == "browser_required"
    assert schedule["level"] == "browser_required"
    assert notify["level"] == "browser_required"


def test_batch_publish_config_fixed_collection_persists(tmp_path: Path) -> None:
    root = tmp_path
    db_path = root / "d.sqlite3"
    db.init_db(db_path)
    cfg = _cfg(root, db_path)
    with db.connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('/a.md', 't', '', 'b', 'h', 'imported')"
        )
        aid = int(cur.lastrowid)
        cfg_json = publish_config_to_json(
            PublishConfig(fixed_collection="每周专栏", publish_action="draft")
        )
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, publish_config_json) "
            "VALUES (?, datetime('now'), 'pending', 'mock', ?)",
            (aid, cfg_json),
        )
        conn.commit()
        row = conn.execute(
            "SELECT publish_config_json FROM publish_jobs WHERE article_id = ?", (aid,)
        ).fetchone()
    data = json.loads(row["publish_config_json"])
    assert data["fixed_collection"] == "每周专栏"


# --- Round D + E ---


def test_empty_body_blocked_preflight(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path, tmp_path / "d.sqlite3")
    row = {"title": "空", "body": "   ", "cover_path": ""}
    summary = build_article_preflight_summary(row, cfg)
    assert summary["ready"] is False
    assert any(c["id"] == "body" and c["required"] for c in summary["checks"])


def test_mock_task_package_simulation_no_backend_locate(tmp_path: Path) -> None:
    root = tmp_path
    db_path = root / "d.sqlite3"
    db.init_db(db_path)
    cfg = _cfg(root, db_path, external_agent_task_outbox=root / "outbox")
    with db.connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('/a.md', 'mock文', '', '正文', 'h', 'imported')"
        )
        aid = int(cur.lastrowid)
        cur = conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, publish_config_json) "
            "VALUES (?, datetime('now'), 'done', 'mock', ?)",
            (aid, publish_config_to_json(PublishConfig())),
        )
        jid = int(cur.lastrowid)
        conn.execute(
            "INSERT INTO wechat_drafts (article_id, media_id, status, payload_json) "
            "VALUES (?, 'mock_media_abc123', 'created', '{}')",
            (aid,),
        )
        conn.commit()
        result = export_task_package(cfg, conn, jid)
    assert result["ok"] is True
    task = json.loads((Path(result["task_package_path"]) / "task.json").read_text(encoding="utf-8"))
    assert task["simulation"] is True
    assert "locate_draft" not in task["required_actions"]
    assert task["target_backend"] == "local_mock"
    assert "wechat_backend_schedule" in task["target_field_values"]
    assert (
        task["target_field_values"]["wechat_backend_schedule"]
        == "agent_prepare_and_save_draft_user_final_publish"
    )


def test_delete_manifest_stable_media_id(tmp_path: Path) -> None:
    root = tmp_path
    db_path = root / "d.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        upsert_remote_mirror(
            conn,
            remote_type="draft",
            media_id="mock_remote_draft_001",
            title="测试稿",
            update_time=123,
        )
        conn.commit()
        manifest = build_delete_manifest(conn, ["mock_remote_draft_001", "missing_id"])
    assert manifest["count"] == 2
    assert manifest["items"][0]["found"] is True
    assert manifest["items"][0]["title"] == "测试稿"


def test_remote_delete_dry_run_and_permission_gate(tmp_path: Path) -> None:
    root = tmp_path
    db_path = root / "d.sqlite3"
    db.init_db(db_path)
    cfg = _cfg(root, db_path)
    result = execute_remote_delete(
        cfg,
        ["mock_remote_draft_001"],
        dry_run=True,
        confirmed=True,
    )
    assert result["ok"] is True
    assert result["success_count"] == 1


def test_mock_submit_publish_respects_force_false() -> None:
    adapter = MockWechatAdapter()
    skipped = adapter.submit_publish("mock_media_x", force=False)
    assert skipped.get("skipped") is True
    published = adapter.submit_publish("mock_media_x", force=True)
    assert "publish_id" in published


def test_mock_draft_only_sets_drafted_stat(tmp_path: Path) -> None:
    root = tmp_path
    db_path = root / "d.sqlite3"
    db.init_db(db_path)
    cfg = _cfg(root, db_path)
    with db.connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status, schedule_state) "
            "VALUES ('/a.md', 't', '', 'body', 'h', 'imported', 'scheduled_local')"
        )
        aid = int(cur.lastrowid)
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, publish_config_json)
            VALUES (?, datetime('now', '-1 minute'), 'pending', 'mock', ?)
            """,
            (aid, publish_config_to_json(PublishConfig(publish_action="draft", auto_execute=True))),
        )
        conn.commit()
    stats = run_due_jobs(cfg)
    assert stats.get("drafted") == 1
    with db.connect(db_path) as conn:
        row = conn.execute("SELECT schedule_state, status FROM articles WHERE id = ?", (aid,)).fetchone()
        assert row["schedule_state"] == "remote_draft_ready"
        assert row["status"] == "imported"
