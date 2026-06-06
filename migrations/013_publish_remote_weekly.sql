-- Round 133: 远端草稿排期与每周续排游标

ALTER TABLE publish_jobs ADD COLUMN remote_media_id TEXT;
ALTER TABLE publish_jobs ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'local';

ALTER TABLE articles ADD COLUMN schedule_state TEXT NOT NULL DEFAULT 'imported';

CREATE TABLE IF NOT EXISTS weekly_plan_cursor (
    scope_key TEXT PRIMARY KEY,
    cursor_index INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_publish_jobs_remote_media_active
    ON publish_jobs(remote_media_id)
    WHERE remote_media_id IS NOT NULL AND source_kind = 'remote_draft'
      AND status IN ('pending', 'running', 'done');
