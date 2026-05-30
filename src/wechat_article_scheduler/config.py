"""从环境变量与 rules.yaml 加载配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# 项目根目录：src/wechat_article_scheduler -> 上两级
ROOT = Path(__file__).resolve().parents[2]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class AppConfig:
    """运行时配置（无密钥落盘）。"""

    root: Path
    database_path: Path
    inbox_dir: Path
    rules_path: Path
    wechat_mode: str
    schedule_window_days: int
    scheduler_poll_seconds: int
    max_articles_per_day: int
    log_redact_secrets: bool
    log_file: Path | None
    log_max_bytes: int
    log_backup_count: int
    log_level: str
    dry_run: bool
    max_job_retries: int
    wechat_app_id: str
    wechat_app_secret: str
    wechat_default_thumb_path: str
    wechat_enable_publish: bool
    web_host: str
    web_port: int
    rules: dict[str, Any]


def load_rules(path: Path) -> dict[str, Any]:
    """加载 YAML 规则文件。"""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def load_config(env_file: Path | None = None) -> AppConfig:
    """加载 .env 与 rules，供 CLI 与调度器使用。"""
    if env_file is None:
        env_file = ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    rules_path = Path(os.getenv("RULES_PATH", "config/rules.yaml"))
    if not rules_path.is_absolute():
        rules_path = ROOT / rules_path

    db_path = Path(os.getenv("DATABASE_PATH", "data/app.sqlite3"))
    if not db_path.is_absolute():
        db_path = ROOT / db_path

    inbox = Path(os.getenv("ARTICLES_INBOX", "articles/inbox"))
    if not inbox.is_absolute():
        inbox = ROOT / inbox

    rules = load_rules(rules_path)
    schedule_rules = rules.get("schedule", {}) if isinstance(rules.get("schedule"), dict) else {}

    return AppConfig(
        root=ROOT,
        database_path=db_path,
        inbox_dir=inbox,
        rules_path=rules_path,
        wechat_mode=os.getenv("WECHAT_MODE", "mock").strip().lower(),
        schedule_window_days=int(os.getenv("SCHEDULE_WINDOW_DAYS", "7")),
        scheduler_poll_seconds=int(os.getenv("SCHEDULER_POLL_SECONDS", "60")),
        max_articles_per_day=int(
            os.getenv("MAX_ARTICLES_PER_DAY", str(schedule_rules.get("max_per_day", 2)))
        ),
        log_redact_secrets=_env_bool("LOG_REDACT_SECRETS", True),
        log_file=_resolve_optional_path(os.getenv("LOG_FILE", "data/logs/app.log"), ROOT),
        log_max_bytes=int(os.getenv("LOG_MAX_BYTES", "1048576")),
        log_backup_count=int(os.getenv("LOG_BACKUP_COUNT", "3")),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        dry_run=_env_bool("DRY_RUN", False),
        max_job_retries=int(os.getenv("MAX_JOB_RETRIES", "3")),
        wechat_app_id=os.getenv("WECHAT_APP_ID", "").strip(),
        wechat_app_secret=os.getenv("WECHAT_APP_SECRET", "").strip(),
        wechat_default_thumb_path=os.getenv("WECHAT_DEFAULT_THUMB_PATH", "").strip(),
        wechat_enable_publish=_env_bool("WECHAT_ENABLE_PUBLISH", True),
        web_host=os.getenv("WEB_HOST", "127.0.0.1").strip(),
        web_port=int(os.getenv("WEB_PORT", "8080")),
        rules=rules,
    )


def _resolve_optional_path(raw: str, root: Path) -> Path | None:
    """解析可选路径；空字符串表示不写文件日志。"""
    value = raw.strip()
    if not value or value.lower() in {"none", "off", "false"}:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path
