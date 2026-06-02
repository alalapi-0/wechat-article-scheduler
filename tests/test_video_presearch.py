"""Phase3 视频内容包预研 dry-run。"""

from pathlib import Path

from wechat_article_scheduler.content_packages.video_presearch import (
    build_video_package_dry_run,
    list_video_platforms,
)
from wechat_article_scheduler.adapters.registry import is_known_adapter
from wechat_article_scheduler.core.manifest_loader import validate_manifest_file

ROOT = Path(__file__).resolve().parents[1]
VIDEO_MANIFEST = ROOT / "manifests" / "examples" / "sample_video_manifest.json"


def test_bilibili_video_dry_run():
    plan = build_video_package_dry_run(platform="bilibili")
    assert plan["content_type"] == "video"
    assert plan["platform_assessment"]["recommendation"] == "manual_export_first"
    assert plan["registry_placeholders"]


def test_registry_bilibili_placeholders():
    assert is_known_adapter("bilibili", "manual_export")


def test_sample_video_manifest_valid():
    _data, result = validate_manifest_file(VIDEO_MANIFEST)
    assert result.ok, result.errors


def test_list_video_platforms():
    assert len(list_video_platforms()) >= 3
