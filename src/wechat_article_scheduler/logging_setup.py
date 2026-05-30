"""RotatingFileHandler 日志初始化（Round 7 加固）。"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from wechat_article_scheduler.config import AppConfig


def setup_logging(config: AppConfig) -> None:
    """
    配置根日志：控制台 INFO + 可选文件轮转。

    日志中不打印 access_token（由业务层 _safe_payload 与 redact_url 配合）。
    """
    root = logging.getLogger()
    if getattr(root, "_wechat_scheduler_configured", False):
        return

    level = logging.DEBUG if config.log_level == "DEBUG" else logging.INFO
    root.setLevel(level)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    if config.log_file:
        config.log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            config.log_file,
            maxBytes=config.log_max_bytes,
            backupCount=config.log_backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)

    root._wechat_scheduler_configured = True  # type: ignore[attr-defined]
