-- 007: 封面裁剪/位置配置（批量设置封面时可复用）
ALTER TABLE articles ADD COLUMN cover_config_json TEXT;
