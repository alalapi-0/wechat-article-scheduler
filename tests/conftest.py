"""测试共用 fixtures。"""

from __future__ import annotations

import os
from pathlib import Path
import stat
import tempfile
from typing import Any

import pytest

from wechat_article_scheduler.config import AppConfig


@pytest.fixture
def rr_socket_dir():
    """Short exclusive socket paths; databases and other fixtures stay in tmp_path."""
    base = Path('/home/alalapi/Temp/wechat-article-scheduler')
    info = base.lstat()
    assert stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
    assert base.resolve(strict=True) == base
    parent = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    descriptor = None
    try:
        directory = Path(tempfile.mkdtemp(prefix='rr-', dir=base))
        descriptor = os.open(directory.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                             dir_fd=parent)
        initial = os.fstat(descriptor)
        assert initial.st_uid == os.getuid() and stat.S_IMODE(initial.st_mode) == 0o700
        assert len(os.fsencode(str(directory / 'browser.sock'))) < 108
        try:
            yield directory
        finally:
            current = os.stat(directory.name, dir_fd=parent, follow_symlinks=False)
            assert stat.S_ISDIR(current.st_mode)
            assert (current.st_dev, current.st_ino, current.st_uid, stat.S_IMODE(current.st_mode)) == (
                initial.st_dev, initial.st_ino, initial.st_uid, 0o700)
            # Tests must close/join their exact listeners, server tasks and CLI
            # children first. Unknown sockets or other residuals remain intact.
            assert not os.listdir(descriptor), 'RR socket fixture retained: unexpected residuals'
            os.rmdir(directory.name, dir_fd=parent)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)


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
        web_auto_run_due=False,
        web_host="127.0.0.1",
        web_port=8080,
        rules={},
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base
