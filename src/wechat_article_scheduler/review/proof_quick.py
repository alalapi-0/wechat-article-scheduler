"""待人工确认任务的演练快速 proof（mock dry-run 占位）。"""

from __future__ import annotations

import os

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.review.proof import ProofInput


def _auto_approve_enabled() -> bool:
    raw = os.getenv("AUTO_APPROVE_GENERATIONS")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    mode = (os.getenv("REVIEW_MODE") or "auto").strip().lower()
    return mode == "auto"


def quick_proof_allowed(config: AppConfig) -> bool:
    """仅非真实联网模式允许一键占位 proof。"""
    mode = (config.wechat_mode or "mock").strip().lower()
    return mode != "real"


def build_quick_proof_input(config: AppConfig, job_id: int) -> ProofInput:
    badge = "AUTO_APPROVE" if _auto_approve_enabled() else "MOCK"
    mode = (config.wechat_mode or "mock").strip().lower()
    return ProofInput(
        public_url=f"https://mock.local/dry-run/publish-proof/job/{job_id}",
        screenshot_path="mock/dry-run/proof-placeholder.png",
        confirmed_by=badge if badge == "AUTO_APPROVE" else "mock_workbench",
        note=(
            f"演练占位证明（{badge} dry-run）；"
            f"mode={mode}，非公众号后台真实发布凭证"
        ),
    )


def humanize_quick_proof_result(*, completed: int, skipped: int, badge: str) -> list[str]:
    lines: list[str] = []
    if completed:
        lines.append(f"已提交 {completed} 条占位证明（{badge} dry-run）")
    if skipped:
        lines.append(f"跳过 {skipped} 条（已有证明或状态不符）")
    if not lines:
        lines.append("没有可快速确认的任务")
    return lines
