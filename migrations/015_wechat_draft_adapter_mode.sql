-- Record exact adapter/job provenance for every local draft record.
-- Historical runtime ignored publish_jobs.adapter_mode, so legacy rows cannot be
-- inferred as real from a related job. Only the production mock media-id prefix
-- is definitive; every other legacy row remains unknown and fails closed.

ALTER TABLE wechat_drafts
    ADD COLUMN adapter_mode TEXT NOT NULL DEFAULT 'unknown'
        CHECK(adapter_mode IN ('unknown', 'mock', 'real'));

ALTER TABLE wechat_drafts
    ADD COLUMN publish_job_id INTEGER
        REFERENCES publish_jobs(id) ON DELETE SET NULL;

UPDATE wechat_drafts
SET adapter_mode = CASE
    WHEN lower(trim(COALESCE(media_id, ''))) LIKE 'mock_%' THEN 'mock'
    ELSE 'unknown'
END;

CREATE INDEX IF NOT EXISTS idx_wechat_drafts_article_mode_active
    ON wechat_drafts(article_id, adapter_mode, status, id);

CREATE INDEX IF NOT EXISTS idx_wechat_drafts_job_mode_active
    ON wechat_drafts(publish_job_id, adapter_mode, status, id);
