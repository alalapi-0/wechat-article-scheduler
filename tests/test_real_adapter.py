import pytest

from wechat_article_scheduler.adapters.real import RealWechatAdapter


def test_token_url_redacts_secret() -> None:
    adapter = RealWechatAdapter("wx123", "secret_value")
    url = adapter.build_token_request_url()
    assert "wx123" in url
    assert "secret_value" not in url
    assert "***REDACTED***" in url


def test_create_draft_not_implemented() -> None:
    adapter = RealWechatAdapter("wx", "sec")
    with pytest.raises(NotImplementedError):
        adapter.create_draft(title="t", summary="s", body="b")
