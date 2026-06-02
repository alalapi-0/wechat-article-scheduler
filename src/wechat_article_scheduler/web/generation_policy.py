"""生成/审核策略只读状态（与 AUTO_APPROVE_GENERATIONS 对齐，不写库）。"""

from __future__ import annotations

import os
from typing import Any


def auto_approve_generations_enabled() -> bool:
    raw = os.getenv("AUTO_APPROVE_GENERATIONS")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    mode = (os.getenv("REVIEW_MODE") or "auto").strip().lower()
    if mode == "auto":
        return True
    return (os.getenv("SKIP_HUMAN_REVIEW") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def build_generation_policy_status() -> dict[str, Any]:
    enabled = auto_approve_generations_enabled()
    review_mode = (os.getenv("REVIEW_MODE") or ("auto" if enabled else "manual")).strip().lower()
    return {
        "auto_approve_generations": enabled,
        "review_mode": review_mode,
        "badge": "AUTO_APPROVE" if enabled else "MANUAL_REVIEW",
        "headline": "生成内容默认自动通过（AUTO_APPROVE）"
        if enabled
        else "生成内容需人工确认（REVIEW_MODE=manual）",
        "detail": "与 scripts/auto_approve_pipeline.py 环境变量一致；不影响微信 scan/plan。",
    }
