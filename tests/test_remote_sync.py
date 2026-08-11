"""远端草稿只读镜像与复用。"""

from __future__ import annotations

from pathlib import Path

from tests.conftest import make_test_config
from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.mock import MockWechatAdapter
from wechat_article_scheduler.capability_probe import probe_freepublish_batchget
from wechat_article_scheduler.publish_config import PublishConfig, publish_config_to_json
from wechat_article_scheduler.remote_sync import (
    REMOTE_TYPE_DRAFT,
    sync_remote_drafts,
    upsert_remote_mirror,
)
from wechat_article_scheduler.scheduler import run_due_jobs


def _config(tmp_path: Path):
    db_path = tmp_path / "remote.sqlite3"
    db.init_db(db_path)
    rules = {
        "schedule": {
            "max_per_day": 5,
            "min_hours_between": 3,
            "preferred_hours": [9, 12, 15, 18, 21],
            "window_days": 7,
        },
        "publish": {"auto_execute": True},
    }
    return make_test_config(
        tmp_path,
        db_path,
        rules=rules,
        schedule_window_days=7,
        max_articles_per_day=5,
        external_agent_task_outbox=tmp_path / "agent-outbox",
    )


def test_mock_remote_sync_is_idempotent(tmp_path: Path) -> None:
    config = _config(tmp_path)
    first = sync_remote_drafts(config)
    second = sync_remote_drafts(config)
    assert first["synced"] == first["inserted"] == 5
    assert second["synced"] == second["unchanged"] == 5
    assert second.get("inserted", 0) == 0


def test_capped_remote_sync_does_not_mark_unseen_drafts_stale(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _config(tmp_path)

    class ManyDraftsAdapter(MockWechatAdapter):
        _MOCK_REMOTE_DRAFTS = tuple(
            {
                "media_id": f"mock_remote_{index:03d}",
                "title": f"远端 {index}",
                "update_time": 1_700_000_000 + index,
            }
            for index in range(1, 26)
        )

    adapter = ManyDraftsAdapter()
    monkeypatch.setattr("wechat_article_scheduler.remote_sync.get_adapter", lambda _cfg: adapter)
    with db.connect(config.database_path) as conn:
        upsert_remote_mirror(
            conn,
            remote_type=REMOTE_TYPE_DRAFT,
            media_id="mock_remote_025",
            title="远端 25",
            update_time=1_700_000_025,
        )
        conn.commit()

    result = sync_remote_drafts(config, max_pages=1)
    assert result["complete_scan"] is False
    assert result["stale"] == 0
    assert result["stale_skipped_incomplete_scan"] is True
    with db.connect(config.database_path) as conn:
        row = conn.execute(
            "SELECT sync_status FROM remote_content_mirror WHERE media_id = ?",
            ("mock_remote_025",),
        ).fetchone()
    assert row["sync_status"] == "active"


def test_complete_empty_remote_sync_marks_existing_mirror_stale(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _config(tmp_path)

    class EmptyDraftsAdapter(MockWechatAdapter):
        _MOCK_REMOTE_DRAFTS = ()

    adapter = EmptyDraftsAdapter()
    monkeypatch.setattr("wechat_article_scheduler.remote_sync.get_adapter", lambda _cfg: adapter)
    with db.connect(config.database_path) as conn:
        upsert_remote_mirror(
            conn,
            remote_type=REMOTE_TYPE_DRAFT,
            media_id="old_remote",
            title="旧草稿",
            update_time=1,
        )
        conn.commit()

    result = sync_remote_drafts(config)
    assert result["complete_scan"] is True
    assert result["stale"] == 1
    with db.connect(config.database_path) as conn:
        row = conn.execute(
            "SELECT sync_status FROM remote_content_mirror WHERE media_id = 'old_remote'"
        ).fetchone()
    assert row["sync_status"] == "stale"


def test_published_list_capability_probe_remains_read_only(tmp_path: Path) -> None:
    probe = probe_freepublish_batchget(MockWechatAdapter())
    assert probe["state"] == "unauthorized"
    assert probe["item_count"] is None


def test_remote_draft_job_reuses_existing_media_id(tmp_path: Path) -> None:
    config = _config(tmp_path)
    with db.connect(config.database_path) as conn:
        article_id = int(
            conn.execute(
                "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
                "VALUES ('remote://x', '远端草稿', '', '正文', 'remote-hash', 'imported')"
            ).lastrowid
        )
        conn.execute(
            """
            INSERT INTO publish_jobs
                (article_id, scheduled_at, status, adapter_mode, source_kind,
                 remote_media_id, publish_config_json)
            VALUES (?, datetime('now', '-1 minute'), 'pending', 'mock',
                    'remote_draft', 'mock_remote_draft_001', ?)
            """,
            (article_id, publish_config_to_json(PublishConfig(auto_execute=True))),
        )
        conn.commit()

    stats = run_due_jobs(config)
    assert stats["processed"] == 1
    assert stats["remote_draft_reused"] == 1
    assert stats["drafted"] == 1
    with db.connect(config.database_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) AS count FROM wechat_drafts WHERE article_id = ?",
            (article_id,),
        ).fetchone()["count"]
    assert count == 0
