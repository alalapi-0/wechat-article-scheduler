"""real_api_check 脚本单元测试（不联网）。"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "real_api_check.py"


def load_mod():
    spec = importlib.util.spec_from_file_location("real_api_check", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["real_api_check"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def rac():
    return load_mod()


def test_load_sample_parses_frontmatter(rac):
    path = ROOT / "fixtures" / "real_api_samples" / "01_normal.md"
    s = rac._load_sample(path)
    assert "[API-TEST]" in s["title"]
    assert "第一段" in s["body"]


def test_quality_notes_detects_escaped_html(rac):
    notes = rac._quality_notes("t", "&lt;p&gt;x&lt;/p&gt;")
    assert any("HTML" in n for n in notes)


def test_run_check_blocks_mock_mode(rac, monkeypatch):
    monkeypatch.delenv("WECHAT_APP_ID", raising=False)
    monkeypatch.delenv("WECHAT_APP_SECRET", raising=False)
    monkeypatch.setenv("WECHAT_MODE", "mock")
    report = rac.run_check(samples=1, dry_run=True, token_only=False)
    assert report.mock_used is True
    assert "real" in report.blocking_reason


def test_run_check_real_mode_defaults_to_draft_only_without_blocking(
    rac,
    monkeypatch,
):
    from wechat_article_scheduler.adapters.base import DraftResult
    import wechat_article_scheduler.adapters as adapters_mod

    monkeypatch.setenv("WECHAT_MODE", "real")
    monkeypatch.setenv("WECHAT_APP_ID", "wx")
    monkeypatch.setenv("WECHAT_APP_SECRET", "sec")
    monkeypatch.delenv("WECHAT_ENABLE_PUBLISH", raising=False)

    class FakeAdapter:
        def get_access_token(self) -> str:
            return "token"

        def create_draft(self, **kwargs):  # noqa: ANN001, ANN201
            return DraftResult(media_id="draft-real", raw_response={"media_id": "draft-real"})

        def submit_publish(self, media_id: str, *, force: bool = False) -> dict:
            assert force is False
            return {"skipped": True, "media_id": media_id}

    monkeypatch.setattr(adapters_mod, "get_adapter", lambda cfg: FakeAdapter())  # noqa: ARG005

    report = rac.run_check(samples=1, dry_run=False, token_only=False)

    assert report.blocking_reason == ""
    assert report.token_ok is True
    assert report.enable_publish is False
    assert report.allow_publish is False
    assert report.success_count == 1


def test_run_check_publish_flag_allows_submit(rac, monkeypatch):
    from wechat_article_scheduler.adapters.base import DraftResult
    import wechat_article_scheduler.adapters as adapters_mod

    monkeypatch.setenv("WECHAT_MODE", "real")
    monkeypatch.setenv("WECHAT_APP_ID", "wx")
    monkeypatch.setenv("WECHAT_APP_SECRET", "sec")
    monkeypatch.delenv("WECHAT_ENABLE_PUBLISH", raising=False)

    class FakeAdapter:
        def get_access_token(self) -> str:
            return "token"

        def create_draft(self, **kwargs):  # noqa: ANN001, ANN201
            return DraftResult(media_id="draft-real", raw_response={"media_id": "draft-real"})

        def submit_publish(self, media_id: str, *, force: bool = False) -> dict:
            assert force is True
            return {"publish_id": "pub-1", "media_id": media_id}

    monkeypatch.setattr(adapters_mod, "get_adapter", lambda cfg: FakeAdapter())  # noqa: ARG005

    report = rac.run_check(samples=1, dry_run=False, token_only=False, allow_publish=True)

    assert report.blocking_reason == ""
    assert report.enable_publish is True
    assert report.allow_publish is True
    assert report.success_count == 1


def test_write_report_creates_files(rac, tmp_path, monkeypatch):
    monkeypatch.setattr(rac, "REPORTS_DIR", tmp_path)
    report = rac.RunReport(started_at="2026-01-01T00:00:00Z", wechat_mode="mock")
    base = rac._write_report(report)
    assert base.with_suffix(".json").is_file()
    data = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))
    assert data["wechat_mode"] == "mock"
