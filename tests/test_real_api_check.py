"""real_api_check 脚本单元测试（不联网）。"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

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
def rac(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    mod = load_mod()
    monkeypatch.setattr(mod, "_load_dotenv", lambda: None)
    import dotenv
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setenv("RULES_PATH", str(tmp_path / "missing-rules.yaml"))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "real-api.sqlite3"))
    monkeypatch.setenv("ARTICLES_INBOX", str(tmp_path / "articles" / "inbox"))
    monkeypatch.setenv("LOG_FILE", "")
    return mod


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
    report = rac.run_check(samples=1, dry_run=False, token_only=False)
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

    created: list[str] = []

    class FakeAdapter:
        def get_access_token(self) -> str:
            return "token"

        def create_draft(self, **kwargs):  # noqa: ANN001, ANN201
            created.append(kwargs["title"])
            return DraftResult(media_id="draft-real", raw_response={"media_id": "draft-real"})

    monkeypatch.setattr(adapters_mod, "get_adapter", lambda cfg: FakeAdapter())  # noqa: ARG005

    report = rac.run_check(samples=1, dry_run=False, token_only=False)

    assert report.blocking_reason == ""
    assert report.token_ok is True
    assert report.success_count == 1
    assert created
    assert "draft/add" in report.model


def test_credential_status_mock_mode(rac):
    cfg = SimpleNamespace(
        wechat_mode="mock",
        wechat_app_id="",
        wechat_app_secret="",
    )
    status = rac.credential_status(cfg)
    assert status.ready is False
    assert "real" in status.reason


def test_run_check_dry_run_real_creds_uses_no_adapter_or_wechat_api(rac, monkeypatch):
    import wechat_article_scheduler.adapters as adapters_mod

    monkeypatch.setenv("WECHAT_MODE", "real")
    monkeypatch.setenv("WECHAT_APP_ID", "wx")
    monkeypatch.setenv("WECHAT_APP_SECRET", "sec")

    def unexpected_get_adapter(cfg):  # noqa: ANN001, ANN202, ARG001
        raise AssertionError("dry_run must not construct an adapter")

    monkeypatch.setattr(adapters_mod, "get_adapter", unexpected_get_adapter)

    report = rac.run_check(samples=3, dry_run=True, token_only=False)
    assert report.token_ok is False
    assert report.dry_run is True
    assert report.blocking_reason == "DRY_RUN：仅验证本地配置，不调用微信 API"
    assert report.success_count == 0


def test_run_check_token_only_fetches_token_without_creating_draft(rac, monkeypatch):
    import wechat_article_scheduler.adapters as adapters_mod

    monkeypatch.setenv("WECHAT_MODE", "real")
    monkeypatch.setenv("WECHAT_APP_ID", "wx")
    monkeypatch.setenv("WECHAT_APP_SECRET", "sec")
    calls: list[str] = []

    class FakeAdapter:
        def get_access_token(self) -> str:
            calls.append("token")
            return "token"

        def create_draft(self, **kwargs):  # noqa: ANN001, ANN201
            raise AssertionError("token_only must not create drafts")

    monkeypatch.setattr(adapters_mod, "get_adapter", lambda cfg: FakeAdapter())  # noqa: ARG005

    report = rac.run_check(samples=3, dry_run=False, token_only=True)
    assert report.token_ok is True
    assert report.token_only is True
    assert report.blocking_reason == ""
    assert report.success_count == 0
    assert calls == ["token"]


def test_main_skip_if_blocked_mock_exit_zero(
    rac,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("WECHAT_MODE", "mock")
    report_dir = tmp_path / "reports"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "real_api_check",
            "--dry-run",
            "--skip-if-blocked",
            "--report-dir",
            str(report_dir),
        ],
    )
    assert rac.main() == 0
    assert "blocking" in capsys.readouterr().err
    assert list(report_dir.glob("run_*.json"))


def test_write_report_creates_files(rac, tmp_path: Path) -> None:
    report = rac.RunReport(started_at="2026-01-01T00:00:00Z", wechat_mode="mock")
    base = rac._write_report(report, reports_dir=tmp_path)
    assert base.with_suffix(".json").is_file()
    data = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))
    assert data["wechat_mode"] == "mock"
