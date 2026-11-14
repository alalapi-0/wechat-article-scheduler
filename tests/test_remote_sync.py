"""远端草稿只读镜像与复用。"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import make_test_config
from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.mock import MockWechatAdapter
from wechat_article_scheduler.adapters.wechat_http import WechatApiError
from wechat_article_scheduler.capability_probe import probe_freepublish_batchget
from wechat_article_scheduler.publish_config import PublishConfig, publish_config_to_json
from wechat_article_scheduler.remote_sync import (
    REMOTE_TYPE_DRAFT,
    inspect_known_draft,
    sync_remote_drafts,
    upsert_remote_mirror,
)
from wechat_article_scheduler.scheduler import run_due_jobs


def _inspection_adapter(monkeypatch, response):
    calls = []

    class ReadAdapter(MockWechatAdapter):
        def get_draft(self, *, media_id):
            calls.append(media_id)
            if isinstance(response, Exception):
                raise response
            return response

        def create_draft(self, **kwargs):
            pytest.fail("inspection must not create a draft")

        def update_draft(self, **kwargs):
            pytest.fail("inspection must not update a draft")

        def upload_thumb_media(self, *args, **kwargs):
            pytest.fail("inspection must not upload media")

    monkeypatch.setattr("wechat_article_scheduler.remote_sync.get_adapter", lambda config: ReadAdapter())
    return calls


def test_inspect_known_draft_compares_selected_article_without_database(tmp_path, monkeypatch):
    config = _config(tmp_path)
    before = config.database_path.read_bytes()
    calls = _inspection_adapter(monkeypatch, {"news_item": [
        {"title": "第一篇", "content": "<p>一</p>"},
        {"title": "第二篇", "digest": "摘要", "content": "<p>二</p>", "thumb_media_id": "thumb-2"},
    ]})

    def forbidden(*args, **kwargs):
        pytest.fail("inspection must not connect to SQLite")

    monkeypatch.setattr("wechat_article_scheduler.remote_sync.db.connect", forbidden)
    result = inspect_known_draft(config, media_id="known-id", index=1, expected_fields={
        "title": "第二篇", "digest": "摘要", "content": "<p>二</p>", "thumb_media_id": "thumb-2",
    })
    assert result["state"] == "readable"
    assert result["comparison"] == "match"
    assert result["media_id"] == "known-id" and result["index"] == 1
    assert calls == ["known-id"]
    assert config.database_path.read_bytes() == before


@pytest.mark.parametrize("expected,comparison,state,unknown", [
    (None, "unknown", "readable", {}),
    ({}, "unknown", "readable", {}),
    ({"content": "<p>旧正文</p>"}, "mismatch", "mismatch", {}),
    ({"digest": "摘要"}, "unknown", "readable", {"digest": "remote_missing"}),
    ({"title": None}, "unknown", "readable", {"title": "expected_unknown"}),
    ({"thumb_media_id": "thumb"}, "unknown", "readable", {"thumb_media_id": "remote_unknown"}),
])
def test_inspect_comparison_retains_missing_and_unknown(tmp_path, monkeypatch, expected, comparison, state, unknown):
    config = make_test_config(tmp_path, tmp_path / "must-not-create.sqlite3")
    calls = _inspection_adapter(monkeypatch, {"news_item": [{"title": "标题", "content": "<p>正文</p>", "thumb_media_id": None}]})
    result = inspect_known_draft(config, media_id="known-id", expected_fields=expected)
    assert result["state"] == state
    assert result["comparison"] == comparison
    assert result["unknown_fields"] == unknown
    if comparison == "mismatch":
        assert result["differences"] == {"content": {"expected": "<p>旧正文</p>", "actual": "<p>正文</p>"}}
    assert calls == ["known-id"]
    assert not config.database_path.exists()


@pytest.mark.parametrize("kwargs,reason", [
    ({"media_id": ""}, "invalid_media_id"),
    ({"media_id": "  "}, "invalid_media_id"),
    ({"media_id": None}, "invalid_media_id"),
    ({"media_id": "id", "index": -1}, "invalid_index"),
    ({"media_id": "id", "index": True}, "invalid_index"),
    ({"media_id": "id", "index": "0"}, "invalid_index"),
    ({"media_id": "id", "expected_fields": {"access_token": "secret"}}, "invalid_expected_fields"),
    ({"media_id": "id", "expected_fields": []}, "invalid_expected_fields"),
])
def test_inspect_rejects_invalid_input_before_adapter(tmp_path, monkeypatch, kwargs, reason):
    def forbidden(config):
        pytest.fail("invalid input must not create an adapter or reach HTTP")

    monkeypatch.setattr("wechat_article_scheduler.remote_sync.get_adapter", forbidden)
    result = inspect_known_draft(make_test_config(tmp_path, tmp_path / "unused"), **kwargs)
    assert result["state"] == "error"
    assert result["reason_code"] == reason


def test_inspect_mock_is_optional_and_offline(tmp_path):
    config = make_test_config(tmp_path, tmp_path / "unused")
    result = inspect_known_draft(config, media_id="known-mock-id")
    assert result["state"] == "unsupported"
    assert result["comparison"] == "unknown"
    assert not config.database_path.exists()


@pytest.mark.parametrize("code,state", [(61452, "missing"), (61453, "missing"), (48001, "error"), (42001, "error")])
@pytest.mark.parametrize("raw", [False, True])
def test_inspect_api_errors_keep_code_without_replay_or_raw_secrets(tmp_path, monkeypatch, code, state, raw):
    response = {"errcode": code, "errmsg": "access_token=TEST_SECRET"} if raw else WechatApiError(code, "TEST_SECRET", endpoint="https://example.test/?access_token=TEST_SECRET")
    calls = _inspection_adapter(monkeypatch, response)
    result = inspect_known_draft(make_test_config(tmp_path, tmp_path / "unused"), media_id="known-id")
    assert result["state"] == state
    assert result["error_code"] == code
    assert result["comparison"] == "unknown"
    assert "TEST_SECRET" not in str(result)
    assert calls == ["known-id"]


@pytest.mark.parametrize("response,state,reason", [
    (OSError("https://example.test/?access_token=TEST_SECRET"), "error", "request_failed"),
    ({}, "error", "invalid_response"),
    ({"news_item": {}}, "error", "invalid_response"),
    ({"news_item": [None]}, "error", "invalid_response"),
    ({"news_item": []}, "missing", "article_index_missing"),
])
def test_inspect_unknown_response_is_not_success(tmp_path, monkeypatch, response, state, reason):
    calls = _inspection_adapter(monkeypatch, response)
    result = inspect_known_draft(make_test_config(tmp_path, tmp_path / "unused"), media_id="known-id")
    assert (result["state"], result["reason_code"]) == (state, reason)
    assert result["comparison"] == "unknown"
    assert "TEST_SECRET" not in str(result)
    assert calls == ["known-id"]


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
