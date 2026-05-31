-- 006: 作品软删除（回收站）
ALTER TABLE articles ADD COLUMN deleted_at TEXT;
