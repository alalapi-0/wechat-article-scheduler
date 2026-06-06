-- Round 132: 远端内容只读镜像与能力探测缓存

CREATE TABLE IF NOT EXISTS remote_content_mirror (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    remote_type TEXT NOT NULL,
    media_id TEXT NOT NULL,
    article_id TEXT,
    title TEXT,
    update_time INTEGER,
    last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    content_hash TEXT,
    sync_status TEXT NOT NULL DEFAULT 'active',
    raw_summary_redacted TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_remote_mirror_type_media
    ON remote_content_mirror(remote_type, media_id);

CREATE TABLE IF NOT EXISTS wechat_capability_cache (
    capability_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    message TEXT,
    item_count INTEGER,
    probed_at TEXT NOT NULL DEFAULT (datetime('now')),
    raw_redacted TEXT
);
