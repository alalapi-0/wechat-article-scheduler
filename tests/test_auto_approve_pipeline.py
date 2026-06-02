"""auto_approve_pipeline 脚本单元测试（不联网）。"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "auto_approve_pipeline.py"
REAL_API = ROOT / "scripts" / "real_api_check.py"


def load_mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def pipeline():
    return load_mod(SCRIPT, "auto_approve_pipeline")


@pytest.fixture
def rac():
    return load_mod(REAL_API, "real_api_check")


def test_pipeline_auto_approve_default_auto(pipeline, monkeypatch):
    monkeypatch.delenv("AUTO_APPROVE_GENERATIONS", raising=False)
    monkeypatch.delenv("SKIP_HUMAN_REVIEW", raising=False)
    monkeypatch.setenv("REVIEW_MODE", "auto")
    assert pipeline._pipeline_auto_approve_enabled() is True


def test_pipeline_auto_approve_manual_off(pipeline, monkeypatch):
    monkeypatch.setenv("AUTO_APPROVE_GENERATIONS", "false")
    monkeypatch.setenv("REVIEW_MODE", "manual")
    assert pipeline._pipeline_auto_approve_enabled() is False


def test_auto_review_metadata(rac):
    meta = rac._auto_review_metadata(auto_approve=True)
    assert meta["review_status"] == "auto_approved"
    assert meta["review_mode"] == "auto"
    assert meta["reviewer"] == "agent"
    assert meta["source"] == "real_api"
    assert meta["mock"] == "false"


def test_quality_status_pass_with_issues(rac):
    status = rac._quality_status(ok=True, body="x", notes=["warn"])
    assert status == "pass_with_issues"


def test_run_pipeline_mock_skip_downstream(pipeline, monkeypatch, tmp_path):
    monkeypatch.setenv("WECHAT_MODE", "mock")
    monkeypatch.delenv("WECHAT_APP_ID", raising=False)
    monkeypatch.delenv("WECHAT_APP_SECRET", raising=False)
    monkeypatch.setattr(pipeline, "REPORTS_DIR", tmp_path)
    payload = pipeline.run_pipeline(
        round_num=88,
        samples=1,
        skip_downstream=True,
        dry_run=True,
    )
    assert payload["mock"] is True
    assert payload["auto_approve_enabled"] is True
    assert payload["round"] == 88
    assert payload["downstream"] is None


def test_main_skip_if_blocked_mock(pipeline, monkeypatch, capsys):
    monkeypatch.setenv("WECHAT_MODE", "mock")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "auto_approve_pipeline",
            "--round",
            "1",
            "--dry-run",
            "--skip-downstream",
            "--skip-if-blocked",
        ],
    )
    assert pipeline.main() == 0
    captured = capsys.readouterr()
    assert "pipeline_report:" in captured.out


def test_write_round_report(pipeline, tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "REPORTS_DIR", tmp_path)
    payload = {
        "round": 1,
        "provider": "wechat_official",
        "model": "draft/add",
        "mock": False,
        "success_count": 3,
        "failure_count": 0,
        "auto_approve_enabled": True,
        "auto_approved_count": 3,
        "api_report_json": "reports/real_api_runs/run_x.json",
    }
    base = pipeline._write_round_report(payload)
    assert base.with_suffix(".json").is_file()
    data = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))
    assert data["round"] == 1
