"""Playwright E2E 可用性基线（Round 35）。"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_IN_ORDINARY = (
    "publish_jobs",
    "payload_json",
    "wechat_enable_publish",
    "mode: mock",
    "imported",
    "pending",
)


def _playwright_ready() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
        return True
    except Exception:
        return False


def _wait_for_server(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def _start_server() -> tuple[subprocess.Popen, str, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="e2e_"))
    inbox = tmp / "inbox"
    inbox.mkdir()
    db = tmp / "db.sqlite3"
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = dict(os.environ)
    env.update(
        {
            "WECHAT_MODE": "mock",
            "DATABASE_PATH": str(db),
            "ARTICLES_INBOX": str(inbox),
            "PYTHONPATH": str(ROOT / "src"),
        }
    )
    subprocess.run(
        [sys.executable, "-m", "wechat_article_scheduler.cli", "init-db"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
    )
    proc = subprocess.Popen(
        [sys.executable, "-m", "wechat_article_scheduler.cli", "serve", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc, f"http://127.0.0.1:{port}/", tmp


@pytest.mark.skipif(not _playwright_ready(), reason="playwright chromium not available")
def test_ordinary_view_e2e_baseline():
    from playwright.sync_api import sync_playwright

    proc, url, tmp = _start_server()
    try:
        assert _wait_for_server(url), "临时 web 服务未就绪"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(800)
            text = page.inner_text("body")
            for term in FORBIDDEN_IN_ORDINARY:
                assert term not in text, f"普通视图可见文本含 {term}"
            assert "主操作" in text
            assert "作品库" in text
            assert "安排发布时间" in text
            assert "执行到点发布" in text
            overflow = page.evaluate(
                "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
            )
            assert overflow
            page.set_viewport_size({"width": 375, "height": 812})
            page.wait_for_timeout(400)
            narrow_ok = page.evaluate(
                "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
            )
            assert narrow_ok
            browser.close()
    finally:
        proc.terminate()
        proc.wait(timeout=10)
        import shutil

        shutil.rmtree(tmp, ignore_errors=True)


def test_e2e_module_documents_forbidden_list():
    assert "publish_jobs" in FORBIDDEN_IN_ORDINARY


@pytest.mark.skipif(not _playwright_ready(), reason="playwright chromium not available")
def test_ordinary_view_export_toast_manual_notice_e2e():
    """Round 128：普通视图（不开高级）作品卡导出后 alert 含「未自动发布」。"""
    from playwright.sync_api import sync_playwright

    proc, url, tmp = _start_server()
    try:
        assert _wait_for_server(url), "临时 web 服务未就绪"
        inbox = tmp / "inbox"
        (inbox / "e2e_export.md").write_text("# E2E\n\nbody\n", encoding="utf-8")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.add_init_script(
                "try{localStorage.removeItem('wechat_workbench_show_advanced');"
                "document.documentElement.classList.remove('show-advanced');}catch(e){}"
            )
            page.goto(url + "#works", wait_until="networkidle")
            page.wait_for_timeout(1200)
            page.get_by_role("button", name="扫描本地收件箱").click()
            page.wait_for_timeout(2000)
            drop = page.locator(".export-drop").first
            drop.click()
            item = page.locator(".export-drop-item").filter(has_text="通用").first
            page.once("dialog", lambda d: d.accept())
            item.click()
            page.wait_for_selector("#alertBox .export-toast-warn", timeout=15000)
            alert_text = page.inner_text("#alertBox")
            assert "未自动发布" in alert_text
            assert "路径：" in alert_text or "outbox/" in alert_text
            assert not page.locator("#advanced").is_visible()
            browser.close()
    finally:
        proc.terminate()
        proc.wait(timeout=10)
        import shutil

        shutil.rmtree(tmp, ignore_errors=True)
