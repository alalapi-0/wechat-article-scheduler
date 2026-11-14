"""摘要 120 字、微信错误码可读说明、草稿创建幂等。"""

from __future__ import annotations

from datetime import datetime, timedelta
import json
from pathlib import Path
import urllib.error

import pytest

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.base import DraftResult
from wechat_article_scheduler.adapters.real import RealWechatAdapter
from wechat_article_scheduler.adapters.wechat_http import WechatApiError
from wechat_article_scheduler.capability_probe import (
    CAPABILITY_DRAFT_LIST,
    CAPABILITY_PUBLISHED_LIST,
    _classify_probe_response,
    cache_capability_probe,
    get_cached_capabilities,
    human_capability_summary,
    probe_all_capabilities,
)
from wechat_article_scheduler.draft_update import draft_content_fingerprint
from wechat_article_scheduler.parser import clamp_summary
from wechat_article_scheduler.scheduler import run_due_jobs
from wechat_article_scheduler.scheduler.draft_idempotency import find_reusable_draft_media_id
from wechat_article_scheduler.wechat_errors import (
    format_job_failure, human_wechat_error, wechat_error_diagnostic,
)

from tests.conftest import make_test_config


def test_clamp_summary_unified_120_chars() -> None:
    long_text = "字" * 200
    out = clamp_summary(long_text, 120)
    assert len(out) == 120


def test_human_wechat_error_known_code() -> None:
    msg = human_wechat_error(48001, "api unauthorized")
    assert "未授权" in msg or "48001" in msg


def test_format_job_failure_wechat_api_error() -> None:
    exc = WechatApiError(40001, "invalid credential", endpoint="draft/add")
    payload = format_job_failure(exc)
    assert "40001" in payload or "token" in payload or "凭证" in payload


@pytest.mark.parametrize("as_exception", [False, True])
@pytest.mark.parametrize("code,reason", [
    (48001, "endpoint_unauthorized"),
    (40164, "ip_whitelist"),
    (40243, "appsecret_frozen"),
    (40125, "invalid_appsecret"),
    (40013, "invalid_appid"),
    (40001, "token_error"),
    (40014, "token_error"),
    (41001, "token_error"),
    (42001, "token_error"),
    (45009, "rate_limited"),
    (45011, "rate_limited"),
    (45047, "rate_limited"),
    (123456, "api_error"),
])
def test_probe_error_reasons_preserve_code_without_leaking_response(
    code: int, reason: str, as_exception: bool,
) -> None:
    private = "https://example.invalid/?access_token=private-value&secret=secret-value"
    result = _classify_probe_response(
        None if as_exception else {"errcode": code, "errmsg": private},
        exc=WechatApiError(code, private, endpoint=private) if as_exception else None,
        list_key="item",
    )
    assert result["state"] == ("unauthorized" if code == 48001 else "error")
    assert result["error_code"] == code
    assert result["reason_code"] == reason
    assert result["action_hint"]
    assert "private-value" not in json.dumps(result)
    assert "secret-value" not in json.dumps(result)


@pytest.mark.parametrize("exc,reason", [
    (urllib.error.URLError("https://example.invalid/?secret=private-value"), "network_error"),
    (TimeoutError("access_token=private-value"), "network_error"),
    (RuntimeError("secret=private-value"), "request_error"),
])
def test_probe_request_failure_is_safe_and_not_permission_evidence(exc, reason) -> None:
    result = _classify_probe_response(None, exc=exc, list_key="item")
    assert result["state"] == "error"
    assert result["reason_code"] == reason
    assert result["error_code"] is None
    assert "private-value" not in json.dumps(result)


def test_probe_list_results_and_endpoint_results_remain_independent() -> None:
    class Adapter:
        def list_drafts_batchget(self, **kwargs):
            return {"item": [{"media_id": "known-draft"}]}

        def list_published_batchget(self, **kwargs):
            return {"errcode": 48001, "errmsg": "api unauthorized"}

    result = probe_all_capabilities(Adapter())
    assert result["draft_list"]["state"] == "authorized"
    assert result["draft_list"]["item_count"] == 1
    assert result["published_list"]["state"] == "unauthorized"
    assert result["probed_at"]
    empty = _classify_probe_response({"item": [], "total_count": 0}, exc=None, list_key="item")
    assert empty["state"] == "empty"
    assert empty["item_count"] == 0
    assert _classify_probe_response({}, exc=None, list_key="item")["state"] == "error"


def test_capability_cache_keeps_new_diagnostics_and_accepts_legacy_rows(tmp_path: Path) -> None:
    path = tmp_path / "diagnostics.sqlite3"
    db.init_db(path)
    probe = _classify_probe_response({"errcode": 40164}, exc=None, list_key="item")
    probe["capability_id"] = CAPABILITY_DRAFT_LIST
    with db.connect(path) as conn:
        cache_capability_probe(conn, probe)
        conn.execute(
            "INSERT INTO wechat_capability_cache "
            "(capability_id, state, message, item_count, probed_at, raw_redacted) "
            "VALUES (?, 'empty', '历史空列表', 0, '2026-01-01', ?)",
            (CAPABILITY_PUBLISHED_LIST, '{"state":"empty"'),
        )
        cached = get_cached_capabilities(conn)
    assert cached[CAPABILITY_DRAFT_LIST]["reason_code"] == "ip_whitelist"
    assert cached[CAPABILITY_DRAFT_LIST]["error_code"] == 40164
    assert cached[CAPABILITY_DRAFT_LIST]["action_hint"]
    assert cached[CAPABILITY_DRAFT_LIST]["probed_at"]
    assert cached[CAPABILITY_PUBLISHED_LIST]["state"] == "empty"
    assert "reason_code" not in cached[CAPABILITY_PUBLISHED_LIST]
    assert "无已发布" in human_capability_summary(cached)["published_list"]


@pytest.mark.parametrize("operation", ["create", "update"])
def test_expired_token_does_not_automatically_replay_draft_writes(operation: str, monkeypatch) -> None:
    calls = {"token": 0, "write": 0}

    def token_get(url, **kwargs):
        calls["token"] += 1
        return {"access_token": "synthetic-token", "expires_in": 7200}

    def fail_write(url, body, **kwargs):
        calls["write"] += 1
        assert url.split("?")[0].endswith("/draft/" + ("add" if operation == "create" else "update"))
        raise WechatApiError(42001, "expired", endpoint=url.split("?")[0])

    adapter = RealWechatAdapter("synthetic-app", "synthetic-secret", http_get=token_get,
                                http_post_json_fn=fail_write)
    monkeypatch.setattr(adapter, "_build_article_fields", lambda **kwargs: {"title": "T"})
    with pytest.raises(WechatApiError) as failure:
        if operation == "create":
            adapter.create_draft(title="T", summary="S", body="B")
        else:
            adapter.update_draft(media_id="known-draft", title="T", summary="S", body="B")
    assert failure.value.errcode == 42001
    assert calls == {"token": 1, "write": 1}
    assert "未自动刷新重试" in human_wechat_error(42001)
    assert wechat_error_diagnostic(42001)["reason_code"] == "token_error"


def test_run_once_reuses_same_mode_draft_with_matching_fingerprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path
    db_path = root / "idem.sqlite3"
    db.init_db(db_path)
    past = (datetime.now() - timedelta(minutes=5)).isoformat(timespec="seconds")
    create_calls = 0

    class CountingAdapter:
        def create_draft(self, **kwargs):  # noqa: ANN001, ANN201
            nonlocal create_calls
            create_calls += 1
            return DraftResult(media_id=f"mock-{create_calls}", raw_response={})

    monkeypatch.setattr(
        "wechat_article_scheduler.scheduler.domain.get_adapter",
        lambda cfg: CountingAdapter(),  # noqa: ARG005
    )

    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('a.md', 'T', 'S', 'body', 'hash-idem', 'imported')
            """
        )
        aid = int(conn.execute("SELECT id FROM articles").fetchone()[0])
        prior_job_id = int(
            conn.execute(
                """
                INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
                VALUES (?, ?, 'done', 'mock')
                """,
                (aid, past),
            ).lastrowid
        )
        fingerprint = draft_content_fingerprint(
            title="T", summary="S", body="body", cover_path=None
        )
        conn.execute(
            """
            INSERT INTO wechat_drafts (
                article_id, media_id, status, payload_json,
                adapter_mode, publish_job_id
            ) VALUES (?, 'existing-mid', 'created', ?, 'mock', ?)
            """,
            (
                aid,
                f'{{"content_fingerprint":"{fingerprint}"}}',
                prior_job_id,
            ),
        )
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
            VALUES (?, ?, 'pending', 'mock')
            """,
            (aid, past),
        )
        conn.commit()

    cfg = make_test_config(root, db_path)
    stats = run_due_jobs(cfg)
    assert stats["processed"] == 1
    assert stats.get("draft_reused", 0) == 1
    assert create_calls == 0

    with db.connect(db_path) as conn:
        evt = conn.execute(
            "SELECT event_type FROM events WHERE event_type = 'draft_idempotent_reuse' LIMIT 1"
        ).fetchone()
        draft_rows = conn.execute(
            "SELECT COUNT(*) AS c FROM wechat_drafts WHERE article_id = ?",
            (aid,),
        ).fetchone()["c"]
    assert evt is not None
    assert draft_rows == 2


def test_find_reusable_draft_requires_matching_fingerprint_and_mode(tmp_path: Path) -> None:
    db_path = tmp_path / "find.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('a.md', 'T', '', '', 'hash-a', 'imported')
            """
        )
        aid = int(conn.execute("SELECT id FROM articles").fetchone()[0])
        mock_job_id = int(
            conn.execute(
                """
                INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
                VALUES (?, datetime('now'), 'done', 'mock')
                """,
                (aid,),
            ).lastrowid
        )
        conn.execute(
            """
            INSERT INTO wechat_drafts (
                article_id, media_id, status, payload_json,
                adapter_mode, publish_job_id
            ) VALUES (?, 'm1', 'created',
                      '{"content_fingerprint":"fp-a"}', 'mock', ?)
            """,
            (aid, mock_job_id),
        )
        conn.commit()
        assert (
            find_reusable_draft_media_id(
                conn,
                article_id=aid,
                content_fingerprint="fp-a",
                adapter_mode="mock",
            )
            == "m1"
        )
        assert (
            find_reusable_draft_media_id(
                conn,
                article_id=aid,
                content_fingerprint="fp-a",
                adapter_mode="real",
            )
            is None
        )
        assert (
            find_reusable_draft_media_id(
                conn,
                article_id=aid,
                content_fingerprint="other",
                adapter_mode="mock",
            )
            is None
        )
