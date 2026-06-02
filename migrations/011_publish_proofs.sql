-- 011: 人工发布 proof 记录（Round 19 / browser_assist、manual_export）
CREATE TABLE IF NOT EXISTS publish_proofs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    publish_job_id INTEGER NOT NULL UNIQUE REFERENCES publish_jobs(id),
    article_id INTEGER NOT NULL REFERENCES articles(id),
    screenshot_path TEXT,
    public_url TEXT,
    confirmed_by TEXT,
    confirmed_at TEXT NOT NULL DEFAULT (datetime('now')),
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_publish_proofs_article ON publish_proofs(article_id);
