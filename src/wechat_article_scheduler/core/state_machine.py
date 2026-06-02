"""Future publish state constants.

These enums are documentation-backed drafts. Existing publish_jobs currently use
pending/running/done/failed/cancelled and are not migrated in this round.
"""

from __future__ import annotations

from enum import StrEnum


class PublishStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    SCHEDULED = "scheduled"
    WAITING_CONFIRMATION = "waiting_confirmation"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    RETRY_WAITING = "retry_waiting"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ScheduleState(StrEnum):
    PENDING = "pending"
    CLAIMED = "claimed"
    PROCESSED = "processed"
    MISFIRED = "misfired"
    PAUSED = "paused"
