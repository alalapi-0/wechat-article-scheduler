"""Adapter registry capability list."""

from wechat_article_scheduler.adapters.registry import (
    capability_for,
    infer_platform_from_account_id,
    is_known_adapter,
    list_adapter_capabilities,
)


def test_builtin_capabilities_include_wechat_and_phase2():
    caps = list_adapter_capabilities()
    keys = {(c["platform"], c["adapter_type"]) for c in caps}
    assert ("wechat_mp", "official_api") in keys
    assert ("zhihu", "manual_export") in keys
    assert ("douban", "browser_assist") in keys


def test_filter_by_platform():
    zhihu = list_adapter_capabilities(platform="zhihu")
    assert zhihu
    assert all(c["platform"] == "zhihu" for c in zhihu)


def test_is_known_adapter():
    assert is_known_adapter("wechat_mp", "official_api")
    assert not is_known_adapter("wechat_mp", "webhook")


def test_infer_platform_from_account_id():
    assert infer_platform_from_account_id("wechat_mp_main") == "wechat_mp"
    assert infer_platform_from_account_id("zhihu_main") == "zhihu"
    assert capability_for("douban", "manual_export") is not None
