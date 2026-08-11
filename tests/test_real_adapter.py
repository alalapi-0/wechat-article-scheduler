"""RealWechatAdapter 单元测试（mock HTTP，不联网）。"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from wechat_article_scheduler.adapters.real import RealWechatAdapter
from wechat_article_scheduler.adapters.wechat_http import TokenCache, WechatApiError
from tests.test_web_upload import PNG


def _write_png(path: Path) -> Path:
    path.write_bytes(PNG)
    return path


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
    Image.new("RGB", (1, 1), (255, 0, 0)).save(jpg_path, format="JPEG")
    captured: dict = {}

    def fake_get(url: str, **kwargs) -> dict:  # noqa: ARG001
        return {"access_token": "ATOKEN", "expires_in": 7200}

    def fake_multipart(url: str, fields: dict, files: dict, **kwargs) -> dict:  # noqa: ARG001
        captured["files"] = files
        return {"errcode": 0, "media_id": "thumb_jpg"}

    adapter = RealWechatAdapter(
        "wxapp",
        "wxsec",
        default_thumb_path=str(_write_png(tmp_path / "default.png")),
        managed_roots=(tmp_path,),
        http_get=fake_get,
        http_post_multipart_fn=fake_multipart,
    )
    assert adapter.upload_thumb_media(str(jpg_path)) == "thumb_jpg"
    assert adapter.upload_thumb_media(str(jpg_path)) == "thumb_jpg"
    part = captured["files"]["media"]
    assert part[0] == "thumb.jpg"
    assert part[2] == "image/jpeg"


def test_create_draft_strips_duplicate_markdown_title(tmp_path: Path) -> None:
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
        default_thumb_path=str(_write_png(tmp_path / "default.png")),
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
    assert "##" not in article["content"]
    assert "&lt;p" not in article["content"]
    assert "正文" in article["content"]


def test_create_draft_with_mock_http(tmp_path: Path) -> None:
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
        default_thumb_path=str(_write_png(tmp_path / "default.png")),
        http_get=fake_get,
        http_post_json_fn=fake_post_json,
        http_post_multipart_fn=fake_multipart,
    )
    result = adapter.create_draft(title="标题", summary="摘要", body="<p>正文</p>")
    assert result.media_id == "draft_media_1"
    draft_calls = [p for p in posts if "draft/add" in p[0]]
    assert len(draft_calls) == 1
    assert draft_calls[0][1]["articles"][0]["title"] == "标题"


def test_missing_cover_rejected_before_any_http(tmp_path: Path) -> None:
    calls: list[str] = []

    def unexpected_get(*args, **kwargs) -> dict:  # noqa: ANN002, ANN003, ARG001
        calls.append("token")
        return {"access_token": "unexpected", "expires_in": 7200}

    def unexpected_post(*args, **kwargs) -> dict:  # noqa: ANN002, ANN003, ARG001
        calls.append("post")
        return {"media_id": "unexpected"}

    adapter = RealWechatAdapter(
        "wxapp",
        "wxsec",
        default_thumb_path=str(tmp_path / "missing-default.png"),
        managed_roots=(tmp_path,),
        http_get=unexpected_get,
        http_post_json_fn=unexpected_post,
        http_post_multipart_fn=unexpected_post,
    )

    with pytest.raises(RuntimeError, match="无法安全读取"):
        adapter.create_draft(
            title="标题",
            summary="摘要",
            body="正文",
            cover_path=str(tmp_path / "missing-article.png"),
        )

    assert calls == []


def test_unspecified_article_cover_uses_valid_default(tmp_path: Path) -> None:
    default_cover = _write_png(tmp_path / "default.png")
    multipart_calls = {"count": 0}

    def fake_get(*args, **kwargs) -> dict:  # noqa: ANN002, ANN003, ARG001
        return {"access_token": "ATOKEN", "expires_in": 7200}

    def fake_multipart(*args, **kwargs) -> dict:  # noqa: ANN002, ANN003, ARG001
        multipart_calls["count"] += 1
        return {"media_id": "default_thumb"}

    adapter = RealWechatAdapter(
        "wxapp",
        "wxsec",
        default_thumb_path=str(default_cover),
        http_get=fake_get,
        http_post_multipart_fn=fake_multipart,
    )

    assert adapter.upload_thumb_media() == "default_thumb"
    assert adapter.upload_thumb_media() == "default_thumb"
    assert multipart_calls["count"] == 1


@pytest.mark.parametrize("suffix", [".gif", ".webp"])
def test_unsupported_cover_rejected_before_any_http(tmp_path: Path, suffix: str) -> None:
    calls: list[str] = []
    cover = tmp_path / f"cover{suffix}"
    cover.write_bytes(b"unsupported-image")

    def unexpected_http(*args, **kwargs) -> dict:  # noqa: ANN002, ANN003, ARG001
        calls.append("http")
        return {"access_token": "unexpected", "expires_in": 7200}

    adapter = RealWechatAdapter(
        "wxapp",
        "wxsec",
        managed_roots=(tmp_path,),
        http_get=unexpected_http,
        http_post_json_fn=unexpected_http,
        http_post_multipart_fn=unexpected_http,
    )

    with pytest.raises(RuntimeError, match="仅支持 JPG/JPEG/PNG"):
        adapter.create_draft(
            title="标题",
            summary="摘要",
            body="正文",
            cover_path=str(cover),
        )

    assert calls == []


def test_missing_credentials_raises() -> None:
    adapter = RealWechatAdapter("", "")
    with pytest.raises(RuntimeError):
        adapter.create_draft(title="t", summary="s", body="b")


def test_wechat_api_error() -> None:
    err = WechatApiError(48001, "api unauthorized", endpoint="draft/add")
    assert err.errcode == 48001
