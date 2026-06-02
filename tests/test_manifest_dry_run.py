"""Manifest dry-run -> content_package drafts."""

from pathlib import Path

from wechat_article_scheduler.content_packages.from_manifest import (
    manifest_dry_run_summary,
    manifest_to_drafts,
)
from wechat_article_scheduler.core.manifest_loader import load_manifest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "manifests" / "examples" / "sample_publish_manifest.json"


def test_manifest_to_drafts_two_targets():
    manifest = load_manifest(SAMPLE)
    package, payloads, _warnings = manifest_to_drafts(manifest)
    assert package.project_id == "demo-novel"
    assert len(payloads) == 2
    assert payloads[0].extra["adapter_type"] == "official_api"


def test_manifest_dry_run_summary_registry_checks():
    manifest = load_manifest(SAMPLE)
    summary = manifest_dry_run_summary(manifest)
    assert summary["ok"] is True
    assert summary["target_count"] == 2
    checks = summary["registry_checks"]
    assert all(c["registered"] for c in checks)
