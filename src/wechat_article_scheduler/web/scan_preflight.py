"""扫描收件箱前的轻量预检（路径存在性，不触库）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from wechat_article_scheduler.config import AppConfig


def build_scan_preflight(config: AppConfig) -> dict[str, Any]:
    inbox = Path(config.inbox_dir)
    blocked = False
    reason = ""
    if inbox.exists() and not inbox.is_dir():
        blocked = True
        reason = f"收件箱路径不是目录：{inbox}"
    elif not inbox.exists():
        try:
            inbox.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            blocked = True
            reason = f"无法创建收件箱目录：{exc}"
    file_count = 0
    if inbox.is_dir():
        for pattern in ("*.md", "*.markdown", "*.txt", "*.html", "*.htm"):
            file_count += len(list(inbox.glob(pattern)))
    hint = None
    if not blocked and file_count == 0:
        hint = f"收件箱暂无文稿（{inbox}），可放入 .md/.txt 后重试"
    return {
        "ready": not blocked,
        "blocked": blocked,
        "reason": reason,
        "inbox_path": str(inbox.resolve()),
        "inbox_exists": inbox.exists(),
        "inbox_file_count": file_count,
        "hint": hint,
    }
