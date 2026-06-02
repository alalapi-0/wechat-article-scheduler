"""publish_manifest validation."""

import json
from pathlib import Path

from wechat_article_scheduler.core.manifest_loader import (
    load_manifest,
    validate_manifest,
    validate_manifest_file,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "manifests" / "examples" / "sample_publish_manifest.json"


def test_sample_manifest_file_valid():
    data, result = validate_manifest_file(SAMPLE)
    assert data is not None
    assert result.ok, result.errors


def test_validate_manifest_rejects_empty_targets():
    raw = json.loads(SAMPLE.read_text(encoding="utf-8"))
    raw["targets"] = []
    result = validate_manifest(raw)
    assert not result.ok
    assert any("targets" in e for e in result.errors)


def test_load_manifest_roundtrip():
    data = load_manifest(SAMPLE)
    assert data["schema_version"] == 1
    assert data["project_id"] == "demo-novel"


def test_video_manifest_requires_video_path():
    video = ROOT / "manifests" / "examples" / "sample_video_manifest.json"
    data, result = validate_manifest_file(video)
    assert result.ok
    raw = load_manifest(video)
    del raw["video_path"]
    bad = validate_manifest(raw)
    assert not bad.ok
