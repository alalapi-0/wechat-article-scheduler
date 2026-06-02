"""人工确认与 proof（browser_assist / manual_export）。"""

from wechat_article_scheduler.review.proof import (
    ProofInput,
    WAITING_CONFIRMATION,
    cannot_mark_published_without_proof,
    get_proof_for_job,
    list_waiting_confirmation,
    mark_job_waiting_confirmation,
    proof_has_evidence,
    submit_publish_proof,
)

__all__ = [
    "ProofInput",
    "WAITING_CONFIRMATION",
    "cannot_mark_published_without_proof",
    "get_proof_for_job",
    "list_waiting_confirmation",
    "mark_job_waiting_confirmation",
    "proof_has_evidence",
    "submit_publish_proof",
]
