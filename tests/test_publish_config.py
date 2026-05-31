"""发布任务级配置与自动发布执行。"""

from __future__ import annotations

from pathlib import Path

import pytest

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.publish_config import (
    PublishConfig,
    defaults_from_rules,
    parse_publish_config,
    should_submit_publish,
)
from tests.conftest import make_test_config


def test_should_submit_publish_per_job_overrides_global(tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "pc.sqlite3", wechat_mode="real", wechat_enable_publish=False)
    assert should_submit_publish(app_config=cfg, job_config=PublishConfig(publish_action="publish")) is True
    assert should_submit_publish(app_config=cfg, job_config=PublishConfig(publish_action="draft")) is False


def test_defaults_from_rules() -> None:
    cfg = AppConfig(
        root=Path("."),
        database_path=Path("x"),
        inbox_dir=Path("in"),
        rules_path=Path("r"),
        wechat_mode="mock",
        schedule_window_days=7,
        scheduler_poll_seconds=60,
        max_articles_per_day=2,
        log_redact_secrets=True,
        log_file=None,
        log_max_bytes=1,
        log_backup_count=1,
        log_level="INFO",
        dry_run=False,
        max_job_retries=3,
        wechat_app_id="",
        wechat_app_secret="",
        wechat_default_thumb_path="",
        wechat_enable_publish=False,
        web_auto_run_due=True,
        web_auto_publish=True,
        web_host="127.0.0.1",
        web_port=8080,
        rules={"publish": {"default_action": "publish", "auto_execute": True}},
    )
    defaults = defaults_from_rules(cfg)
    assert defaults.publish_action == "publish"
    assert defaults.auto_execute is True


def test_parse_publish_config_merges_defaults() -> None:
    defaults = PublishConfig(publish_action="draft", auto_execute=False)
    cfg = parse_publish_config({"publish_action": "publish", "auto_execute": True}, defaults=defaults)
    assert cfg.publish_action == "publish"
    assert cfg.auto_execute is True
