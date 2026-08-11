"""不可跨越的草稿-only与远端只读边界。"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from wechat_article_scheduler.adapters.base import WechatAdapter
from wechat_article_scheduler.config import AppConfig

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "wechat_article_scheduler"


def test_adapter_surface_has_no_final_publish_or_remote_delete_operation() -> None:
    assert not hasattr(WechatAdapter, "submit_" + "publish")
    assert not hasattr(WechatAdapter, "delete_" + "draft")
    assert hasattr(WechatAdapter, "list_published_batchget")


def test_runtime_config_has_no_final_publish_switches() -> None:
    names = {item.name for item in fields(AppConfig)}
    assert "wechat_enable_" + "publish" not in names
    assert "web_auto_" + "publish" not in names


def test_source_has_no_final_publish_or_remote_delete_endpoint() -> None:
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SOURCE.rglob("*")
        if path.is_file() and path.suffix in {".py", ".html", ".js"}
    )
    assert "/cgi-bin/freepublish/" + "submit" not in text
    assert "/cgi-bin/draft/" + "delete" not in text
    assert "/api/remote-" + "delete" not in text
