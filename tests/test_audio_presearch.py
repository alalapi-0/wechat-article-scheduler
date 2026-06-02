"""Round 100：Phase4 音频预研。"""

from pathlib import Path

from wechat_article_scheduler.adapters.registry import is_known_adapter
from wechat_article_scheduler.content_packages.audio_presearch import (
    build_audio_package_dry_run,
    list_audio_platforms,
)
from wechat_article_scheduler.core.manifest_loader import validate_manifest_file

ROOT = Path(__file__).resolve().parents[1]


def test_podcast_dry_run():
    plan = build_audio_package_dry_run(platform="podcast")
    assert plan["content_type"] == "podcast"
    assert any("版权" in g for g in plan["guardrails"])


def test_audio_manifest_valid():
    _data, result = validate_manifest_file(
        ROOT / "manifests" / "examples" / "sample_audio_manifest.json"
    )
    assert result.ok, result.errors


def test_podcast_manifest_valid():
    _data, result = validate_manifest_file(
        ROOT / "manifests" / "examples" / "sample_podcast_manifest.json"
    )
    assert result.ok, result.errors


def test_registry_podcast_placeholder():
    assert is_known_adapter("podcast", "manual_export")
    assert len(list_audio_platforms()) >= 3
