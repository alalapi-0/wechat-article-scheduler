"""调度策略：重试上限、DRY_RUN 报告与安全序列化。"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from wechat_article_scheduler.config import AppConfig

logger = logging.getLogger(__name__)


def safe_payload(data: dict) -> str:
    """序列化事件载荷，剔除疑似密钥字段。"""
    redacted = {k: v for k, v in data.items() if "token" not in k.lower() and "secret" not in k.lower()}
    return json.dumps(redacted, ensure_ascii=False)


def max_retries_for(config: AppConfig) -> int:
    return max(1, config.max_job_retries)


def should_skip_max_retries(retry_count: int, max_retries: int) -> bool:
    return retry_count >= max_retries


def write_dry_run_report(config: AppConfig, stats: dict[str, int]) -> None:
    """将 dry-run 摘要写入 data/reports/（便于人工核对）。"""
    report_dir = config.root / "data" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = report_dir / f"dry_run_{stamp}.json"
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "stats": stats,
        "wechat_mode": config.wechat_mode,
        "dry_run": True,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("DRY_RUN 报告已写入 %s", path)
