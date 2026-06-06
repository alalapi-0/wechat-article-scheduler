-- Round 135: 不可变操作运行记录（sync/plan/delete 审计）

CREATE TABLE IF NOT EXISTS operation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation TEXT NOT NULL,
    run_id TEXT NOT NULL UNIQUE,
    dry_run INTEGER NOT NULL DEFAULT 0,
    resume_run_id TEXT,
    max_items INTEGER,
    status TEXT NOT NULL DEFAULT 'running',
    manifest_json TEXT,
    results_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);
