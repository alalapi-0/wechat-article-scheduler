-- 008: 发布任务级配置（批量预设置 + 到点自动发布）
ALTER TABLE publish_jobs ADD COLUMN publish_config_json TEXT;
