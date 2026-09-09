"""从环境变量与 rules.yaml 加载配置。"""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
import os
from pathlib import Path
from typing import Any

import yaml

# 项目根目录：src/wechat_article_scheduler -> 上两级
ROOT = Path(__file__).resolve().parents[2]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def require_loopback_web_host(value: str) -> str:
    """仅允许无鉴权工作台监听本机回环地址。"""
    host = value.strip()
    if host.lower() == "localhost":
        return host
    try:
        if ip_address(host).is_loopback:
            return host
    except ValueError:
        pass
    raise ValueError("WEB_HOST 仅允许 localhost 或回环 IP；工作台没有登录保护")


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
    log_file: Path | None
    log_max_bytes: int
    log_backup_count: int
    log_level: str
    dry_run: bool
    max_job_retries: int
    scheduler_claim_timeout_seconds: int
    scheduler_lock_ttl_seconds: int
    scheduler_misfire_grace_minutes: int
    wechat_app_id: str
    wechat_app_secret: str
    wechat_default_thumb_path: str
    web_auto_run_due: bool
    web_host: str
    web_port: int
    rules: dict[str, Any]
    external_agent_task_export_enabled: bool = True
    external_agent_task_outbox: Path = Path("outbox/wechat_agent_tasks")
    external_agent_include_article_preview: bool = True
    external_agent_include_article_source: bool = True
    external_agent_include_cover: bool = True
    external_agent_include_prompt: bool = True
    external_agent_include_checklist: bool = True
    external_agent_include_inspection_report: bool = True
    external_agent_redact_sensitive_values: bool = True

    @property
    def articles_dir(self) -> Path:
        """文章工作目录（inbox 的上级），隔离测试时只需改 ARTICLES_INBOX。"""
        return self.inbox_dir.parent

    @property
    def imported_dir(self) -> Path:
        return self.articles_dir / "imported"

    @property
    def rejected_dir(self) -> Path:
        return self.articles_dir / "rejected"

    @property
    def covers_dir(self) -> Path:
        return self.articles_dir / "covers"


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
        from dotenv import load_dotenv

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
    external_agent_rules = (
        rules.get("external_agent", {}) if isinstance(rules.get("external_agent"), dict) else {}
    )

    wechat_mode = os.getenv("WECHAT_MODE", "mock").strip().lower()
    if wechat_mode not in {"mock", "real"}:
        raise ValueError("WECHAT_MODE 仅支持 mock 或 real")
    agent_outbox = Path(
        os.getenv(
            "EXTERNAL_AGENT_TASK_OUTBOX",
            str(external_agent_rules.get("outbox_dir", "outbox/wechat_agent_tasks")),
        )
    )
    if not agent_outbox.is_absolute():
        agent_outbox = ROOT / agent_outbox

    return AppConfig(
        root=ROOT,
        database_path=db_path,
        inbox_dir=inbox,
        rules_path=rules_path,
        wechat_mode=wechat_mode,
        schedule_window_days=int(os.getenv("SCHEDULE_WINDOW_DAYS", "7")),
        scheduler_poll_seconds=int(os.getenv("SCHEDULER_POLL_SECONDS", "60")),
        max_articles_per_day=int(
            os.getenv("MAX_ARTICLES_PER_DAY", str(schedule_rules.get("max_per_day", 2)))
        ),
        log_file=_resolve_optional_path(os.getenv("LOG_FILE", "data/logs/app.log"), ROOT),
        log_max_bytes=int(os.getenv("LOG_MAX_BYTES", "1048576")),
        log_backup_count=int(os.getenv("LOG_BACKUP_COUNT", "3")),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        dry_run=_env_bool("DRY_RUN", False),
        max_job_retries=int(os.getenv("MAX_JOB_RETRIES", "3")),
        scheduler_claim_timeout_seconds=int(
            os.getenv("SCHEDULER_CLAIM_TIMEOUT_SECONDS", "900")
        ),
        scheduler_lock_ttl_seconds=int(os.getenv("SCHEDULER_LOCK_TTL_SECONDS", "300")),
        scheduler_misfire_grace_minutes=int(
            os.getenv("SCHEDULER_MISFIRE_GRACE_MINUTES", "60")
        ),
        wechat_app_id=os.getenv("WECHAT_APP_ID", "").strip(),
        wechat_app_secret=os.getenv("WECHAT_APP_SECRET", "").strip(),
        wechat_default_thumb_path=os.getenv("WECHAT_DEFAULT_THUMB_PATH", "").strip(),
        web_auto_run_due=_env_bool("WEB_AUTO_RUN_DUE", True),
        web_host=require_loopback_web_host(os.getenv("WEB_HOST", "127.0.0.1")),
        web_port=int(os.getenv("WEB_PORT", "8080")),
        rules=rules,
        external_agent_task_export_enabled=_env_bool(
            "EXTERNAL_AGENT_TASK_EXPORT_ENABLED",
            bool(external_agent_rules.get("enabled", True)),
        ),
        external_agent_task_outbox=agent_outbox,
        external_agent_include_article_preview=_env_bool(
            "EXTERNAL_AGENT_INCLUDE_ARTICLE_PREVIEW",
            bool(external_agent_rules.get("include_article_preview", True)),
        ),
        external_agent_include_article_source=bool(
            external_agent_rules.get("include_article_source", True)
        ),
        external_agent_include_cover=_env_bool(
            "EXTERNAL_AGENT_INCLUDE_COVER",
            bool(external_agent_rules.get("include_cover", True)),
        ),
        external_agent_include_prompt=_env_bool(
            "EXTERNAL_AGENT_INCLUDE_PROMPT",
            bool(external_agent_rules.get("include_prompt", True)),
        ),
        external_agent_include_checklist=bool(
            external_agent_rules.get("include_checklist", True)
        ),
        external_agent_include_inspection_report=bool(
            external_agent_rules.get("include_inspection_report", True)
        ),
        external_agent_redact_sensitive_values=bool(
            external_agent_rules.get("redact_sensitive_values", True)
        ),
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
