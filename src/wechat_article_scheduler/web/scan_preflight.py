"""扫描收件箱前的轻量预检（路径存在性，不触库）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.filesystem_safety import (
    UnsafePathError,
    open_directory_handle,
    path_chain_is_unaliased,
    safe_directory_exists,
)


def build_scan_preflight(config: AppConfig) -> dict[str, Any]:
    inbox = Path(config.inbox_dir)
    blocked = False
    reason = ""
    if not path_chain_is_unaliased(inbox):
        blocked = True
        reason = f"收件箱路径包含符号链接或不安全的中间目录：{inbox}"
    elif inbox.exists() and not safe_directory_exists(inbox, allowed_roots=(inbox,)):
        blocked = True
        reason = f"收件箱路径包含符号链接或不是安全目录：{inbox}"
    elif inbox.exists() and not inbox.is_dir():
        blocked = True
        reason = f"收件箱路径不是目录：{inbox}"
    elif not inbox.exists():
        reason = "收件箱尚未创建；执行扫描时将安全创建"
    file_count = 0
    if not blocked and inbox.is_dir():
        try:
            allowed = {".md", ".markdown", ".txt", ".html", ".htm"}
            with open_directory_handle(inbox, allowed_roots=(inbox,)) as handle:
                file_count = sum(
                    1 for name in handle.list_names()
                    if Path(name).suffix.lower() in allowed
                )
        except (OSError, UnsafePathError):
            blocked = True
            reason = f"收件箱在预检期间发生变化：{inbox}"
    hint = None
    if not blocked and file_count == 0:
        hint = "收件箱暂无文稿，可放入 .md/.txt 后重试"
    return {
        "ready": not blocked,
        "blocked": blocked,
        "reason": reason,
        "inbox_path": str(inbox.absolute()),
        "inbox_path_advanced": str(inbox.absolute()),
        "inbox_exists": inbox.exists(),
        "inbox_file_count": file_count,
        "hint": hint,
    }
