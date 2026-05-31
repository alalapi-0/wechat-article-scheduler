"""RealWechatAdapter 单元测试（mock HTTP，不联网）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from wechat_article_scheduler.adapters.real import RealWechatAdapter
from wechat_article_scheduler.adapters.wechat_http import TokenCache, WechatApiError


def test_token_url_redacts_secret() -> None:
    adapter = RealWechatAdapter("wx123", "secret_value")
    url = adapter.build_token_request_url()
    assert "wx123" in url
    assert "secret_value" not in url
    assert "***REDACTED***" in url


def test_token_cache_reuses_token() -> None:
    calls = {"n": 0}

    def fetcher() -> dict:
        calls["n"] += 1
        return {"access_token": "tok_abc", "expires_in": 7200}

    cache = TokenCache(refresh_skew_seconds=60)
    assert cache.get_token(fetcher) == "tok_abc"
    assert cache.get_token(fetcher) == "tok_abc"
    assert calls["n"] == 1


def test_upload_thumb_jpg_multipart_metadata(tmp_path: Path) -> None:
    jpg_path = tmp_path / "cover.jpg"
    jpg_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 64)
    captured: dict = {}

    def fake_get(url: str, **kwargs) -> dict:  # noqa: ARG001
        return {"access_token": "ATOKEN", "expires_in": 7200}

    def fake_multipart(url: str, fields: dict, files: dict, **kwargs) -> dict:  # noqa: ARG001
        captured["files"] = files
        return {"errcode": 0, "media_id": "thumb_jpg"}

    adapter = RealWechatAdapter(
        "wxapp",
        "wxsec",
        default_thumb_path=str(jpg_path),
        http_get=fake_get,
        http_post_multipart_fn=fake_multipart,
    )
    assert adapter.upload_thumb_media() == "thumb_jpg"
    part = captured["files"]["media"]
    assert part[0] == "thumb.jpg"
    assert part[2] == "image/jpeg"


def test_create_draft_strips_duplicate_markdown_title() -> None:
    posts: list[tuple[str, dict]] = []

    def fake_get(url: str, **kwargs) -> dict:  # noqa: ARG001
        return {"access_token": "ATOKEN", "expires_in": 7200}

    def fake_post_json(url: str, body: dict, **kwargs) -> dict:  # noqa: ARG001
        posts.append((url, body))
        if "draft/add" in url:
            return {"errcode": 0, "media_id": "draft_media_1"}
        return {"errcode": 0}

    def fake_multipart(url: str, fields: dict, files: dict, **kwargs) -> dict:  # noqa: ARG001
        return {"errcode": 0, "media_id": "thumb_1"}

    adapter = RealWechatAdapter(
        "wxapp",
        "wxsec",
        http_get=fake_get,
        http_post_json_fn=fake_post_json,
        http_post_multipart_fn=fake_multipart,
    )
    adapter.create_draft(
        title="重复标题",
        summary="摘要",
        body="# 重复标题\n\n<p>正文</p>",
    )
    article = posts[-1][1]["articles"][0]
    assert article["title"] == "重复标题"
    assert "<h1" not in article["content"].lower()
    assert "正文" in article["content"]


def test_create_draft_with_mock_http() -> None:
    posts: list[tuple[str, dict]] = []

    def fake_get(url: str, **kwargs) -> dict:  # noqa: ARG001
        assert "cgi-bin/token" in url
        return {"access_token": "ATOKEN", "expires_in": 7200}

    def fake_post_json(url: str, body: dict, **kwargs) -> dict:  # noqa: ARG001
        posts.append((url, body))
        if "draft/add" in url:
            return {"errcode": 0, "media_id": "draft_media_1"}
        return {"errcode": 0}

    def fake_multipart(url: str, fields: dict, files: dict, **kwargs) -> dict:  # noqa: ARG001
        assert "add_material" in url
        return {"errcode": 0, "media_id": "thumb_1"}

    adapter = RealWechatAdapter(
        "wxapp",
        "wxsec",
        http_get=fake_get,
        http_post_json_fn=fake_post_json,
        http_post_multipart_fn=fake_multipart,
    )
    result = adapter.create_draft(title="标题", summary="摘要", body="<p>正文</p>")
    assert result.media_id == "draft_media_1"
    draft_calls = [p for p in posts if "draft/add" in p[0]]
    assert len(draft_calls) == 1
    assert draft_calls[0][1]["articles"][0]["title"] == "标题"


def test_submit_publish_skipped_when_disabled() -> None:
    adapter = RealWechatAdapter("wx", "sec", enable_publish=False)
    out = adapter.submit_publish("media_x")
    assert out.get("skipped") is True


def test_submit_publish_calls_api() -> None:
    def fake_get(url: str, **kwargs) -> dict:  # noqa: ARG001
        return {"access_token": "T", "expires_in": 7200}

    def fake_post_json(url: str, body: dict, **kwargs) -> dict:  # noqa: ARG001
        if "freepublish/submit" in url:
            assert body["media_id"] == "m1"
            return {"errcode": 0, "publish_id": "pub_1"}
        return {"errcode": 0}

    adapter = RealWechatAdapter(
        "wx",
        "sec",
        http_get=fake_get,
        http_post_json_fn=fake_post_json,
        http_post_multipart_fn=lambda *a, **k: {"media_id": "thumb"},
    )
    out = adapter.submit_publish("m1")
    assert out["publish_id"] == "pub_1"


def test_missing_credentials_raises() -> None:
    adapter = RealWechatAdapter("", "")
    with pytest.raises(RuntimeError):
        adapter.create_draft(title="t", summary="s", body="b")


def test_wechat_api_error() -> None:
    err = WechatApiError(48001, "api unauthorized", endpoint="draft/add")
    assert err.errcode == 48001
