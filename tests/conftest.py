"""测试共用 fixtures。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from wechat_article_scheduler.config import AppConfig


def make_test_config(root: Path, db_path: Path, **overrides: Any) -> AppConfig:
    """构造测试用 AppConfig，覆盖新增字段默认值。"""
    base = AppConfig(
        root=root,
        database_path=db_path,
        inbox_dir=root / "articles" / "inbox",
        rules_path=root / "config" / "rules.yaml",
        wechat_mode="mock",
        schedule_window_days=7,
        scheduler_poll_seconds=60,
        max_articles_per_day=2,
        log_redact_secrets=True,
        log_file=None,
        log_max_bytes=1024,
        log_backup_count=1,
        log_level="INFO",
        dry_run=False,
        max_job_retries=3,
        scheduler_claim_timeout_seconds=900,
        scheduler_lock_ttl_seconds=300,
        scheduler_misfire_grace_minutes=60,
        wechat_app_id="",
        wechat_app_secret="",
        wechat_default_thumb_path="",
        wechat_enable_publish=False,
        web_auto_run_due=False,
        web_auto_publish=False,
        web_host="127.0.0.1",
        web_port=8080,
        rules={},
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base
