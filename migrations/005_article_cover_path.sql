-- 005: 每篇作品可绑定独立封面（网页批量上传作品+封面）
-- cover_path 指向 articles/covers/ 下的本地封面文件；为空时回退默认封面。
ALTER TABLE articles ADD COLUMN cover_path TEXT;
