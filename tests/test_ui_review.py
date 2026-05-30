"""Playwright 可用性诊断脚本测试（Round 19）。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
UI_REVIEW = ROOT / "tools" / "browser_automation" / "ui_review.py"
OUT_BASE = ROOT / "docs" / "reports" / "ui_review"


def _playwright_ready() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except ImportError:
        return False


def _chromium_ready() -> bool:
    if not _playwright_ready():
        return False
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


def test_ui_review_script_exists():
    assert UI_REVIEW.is_file()
    text = UI_REVIEW.read_text(encoding="utf-8")
    assert "sync_playwright" in text
    assert "--seed" in text


def test_principles_and_boundary_docs_exist():
    principles = ROOT / "docs" / "ordinary_user_workbench_principles.md"
    boundary = ROOT / "docs" / "info_layer_boundary.md"
    assert principles.is_file()
    assert boundary.is_file()
    assert "三层" in boundary.read_text(encoding="utf-8")
    assert "Desktop-first" in principles.read_text(encoding="utf-8")


def test_playwright_in_dev_dependencies():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "playwright" in pyproject


@pytest.mark.skipif(not _chromium_ready(), reason="playwright chromium not installed")
def test_ui_review_headless_seeded():
    """headless 复跑 seeded 基线，更新 docs/reports/ui_review/seeded/."""
    proc = subprocess.run(
        [sys.executable, str(UI_REVIEW), "--seed", "3", "--tag", "seeded"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "WECHAT_MODE": "mock"},
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    snap = OUT_BASE / "seeded" / "dom_snapshot.md"
    assert snap.is_file()
    text = snap.read_text(encoding="utf-8")
    assert "desktop_1280" in text
    assert (OUT_BASE / "seeded" / "desktop_1280.png").is_file()


@pytest.mark.skipif(not _chromium_ready(), reason="playwright chromium not installed")
def test_ui_review_headless_empty_state():
    proc = subprocess.run(
        [sys.executable, str(UI_REVIEW), "--seed", "0", "--tag", "empty_state"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "WECHAT_MODE": "mock"},
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    snap = OUT_BASE / "empty_state" / "dom_snapshot.md"
    assert snap.is_file()
    assert (OUT_BASE / "empty_state" / "mobile_375.png").is_file()
