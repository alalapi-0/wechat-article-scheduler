#!/usr/bin/env python3
"""本地 Web 工作台可用性诊断脚本（Playwright，只读、可复跑）。

用途：在隔离的临时数据库与临时端口上启动现有 FastAPI 工作台（`cli serve`），
用 Playwright Chromium 打开首页，在多种视口宽度下截图，并抓取页面结构、可见
文本与各功能区清单，输出到 docs/reports/ui_review/。

边界：
- 不改动仓库内的 data/app.sqlite3；使用临时目录 + DATABASE_PATH/ARTICLES_INBOX。
- 默认 WECHAT_MODE=mock，不联网、不真实发布。
- 仅做读取与截图，不点击会写库的操作按钮。

依赖（开发依赖）：
    pip install playwright
    playwright install chromium

运行：
    .venv/bin/python tools/browser_automation/ui_review.py

可选参数：
    --port 8088        指定临时端口（默认自动挑选）
    --keep-db          保留临时数据库目录（调试用）
    --seed N           种子文章数量（默认 5，0 表示展示空状态）
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "docs" / "reports" / "ui_review"
SAMPLE_SOURCE = ROOT / "articles" / "imported"
VIEWPORTS = [
    ("desktop_1280", 1280, 900),
    ("tablet_768", 768, 1024),
    ("mobile_375", 375, 812),
]


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def wait_for_server(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def seed_database(env: dict[str, str], seed: int) -> None:
    base = [sys.executable, "-m", "wechat_article_scheduler.cli"]
    steps = [["init-db"]]
    if seed > 0:
        steps += [["scan"], ["plan"], ["run-once"]]
    for step in steps:
        proc = subprocess.run(
            base + step, cwd=ROOT, env=env, capture_output=True, text=True
        )
        print(f"  seed {' '.join(step)}: exit={proc.returncode} {proc.stdout.strip()[:120]}")


def capture(page, name: str) -> dict:
    """抓取页面关键结构，返回可序列化字典。"""
    info: dict = {"viewport": name}
    info["title"] = page.title()
    info["h1"] = [t.strip() for t in page.locator("h1").all_inner_texts()]
    info["panels"] = [t.strip() for t in page.locator(".panel h2").all_inner_texts()]
    info["alert"] = page.locator("#alert").inner_text().strip()
    info["buttons"] = [t.strip() for t in page.locator("button").all_inner_texts()]
    info["tables"] = page.locator("table").count()
    # 是否出现横向滚动（布局溢出信号）
    info["doc_scroll_width"] = page.evaluate("document.documentElement.scrollWidth")
    info["client_width"] = page.evaluate("document.documentElement.clientWidth")
    info["has_horizontal_overflow"] = info["doc_scroll_width"] > info["client_width"] + 1
    return info


def main() -> int:
    parser = argparse.ArgumentParser(description="Web 工作台 Playwright 可用性诊断")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--keep-db", action="store_true")
    parser.add_argument("--seed", type=int, default=5)
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("缺少 playwright，请先： pip install playwright && playwright install chromium")
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_dir = ROOT / ".ui_review_tmp"
    inbox = tmp_dir / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    db_path = tmp_dir / "ui_review.sqlite3"

    if args.seed > 0 and SAMPLE_SOURCE.exists():
        samples = sorted(SAMPLE_SOURCE.glob("*.md"))[: args.seed]
        for src in samples:
            shutil.copy(src, inbox / src.name)

    env = dict(os.environ)
    env["WECHAT_MODE"] = "mock"
    env["DATABASE_PATH"] = str(db_path)
    env["ARTICLES_INBOX"] = str(inbox)
    env["LOG_FILE"] = str(tmp_dir / "app.log")
    env.setdefault("PYTHONPATH", str(ROOT / "src"))

    print("[1/4] 初始化并种子化临时数据库…")
    seed_database(env, args.seed)

    port = args.port or pick_free_port()
    url = f"http://127.0.0.1:{port}/"
    print(f"[2/4] 启动临时 web 服务 (port={port})…")
    server = subprocess.Popen(
        [sys.executable, "-m", "wechat_article_scheduler.cli", "serve", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    captures: list[dict] = []
    try:
        if not wait_for_server(url):
            print("服务未在超时内就绪")
            return 1
        print("[3/4] Playwright 多视口截图与结构抓取…")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for name, w, h in VIEWPORTS:
                pg = browser.new_page(viewport={"width": w, "height": h})
                pg.goto(url, wait_until="networkidle")
                pg.wait_for_timeout(600)
                shot = OUT_DIR / f"{name}.png"
                pg.screenshot(path=str(shot), full_page=True)
                info = capture(pg, name)
                info["screenshot"] = str(shot.relative_to(ROOT))
                captures.append(info)
                print(f"  {name}: {shot.name} overflow={info['has_horizontal_overflow']}")
                pg.close()
            browser.close()
    finally:
        print("[4/4] 关闭临时服务…")
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        if not args.keep_db:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # 写结构快照
    snapshot = OUT_DIR / "dom_snapshot.md"
    lines = [
        "# Web 工作台 DOM 结构快照（自动生成）",
        "",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        f"- seed_articles: {args.seed}",
        "- generator: tools/browser_automation/ui_review.py",
        "",
    ]
    for info in captures:
        lines.append(f"## 视口 {info['viewport']}")
        lines.append("")
        lines.append(f"- 截图：`{info['screenshot']}`")
        lines.append(f"- 标题：{info['title']}")
        lines.append(f"- H1：{info['h1']}")
        lines.append(f"- 功能区(h2)：{info['panels']}")
        lines.append(f"- 顶部提示：{info['alert']}")
        lines.append(f"- 按钮：{info['buttons']}")
        lines.append(f"- 表格数量：{info['tables']}")
        lines.append(
            f"- 横向溢出：{info['has_horizontal_overflow']} "
            f"(scrollWidth={info['doc_scroll_width']} / clientWidth={info['client_width']})"
        )
        lines.append("")
    snapshot.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"完成。结构快照：{snapshot.relative_to(ROOT)}；截图目录：{OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
