-- 002: 内容库集合、标签与审核状态
CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS article_tags (
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, tag_id)
);

ALTER TABLE articles ADD COLUMN collection_id INTEGER REFERENCES collections(id);
ALTER TABLE articles ADD COLUMN review_status TEXT NOT NULL DEFAULT 'draft';
ALTER TABLE articles ADD COLUMN import_batch TEXT;

INSERT OR IGNORE INTO collections (slug, name, description)
VALUES ('default', '默认集合', '扫描导入的默认内容集合');

UPDATE articles SET review_status = 'draft' WHERE review_status IS NULL OR review_status = '';
