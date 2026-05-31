-- 004: 移除审核状态字段（产品重定位：上传即发布，不再有"审核"步骤）
-- 历史迁移 002 曾为 articles 增加 review_status；本工具不再有审核流程，
-- 真实发布安全改为「发布前二次确认 + 预检清单」，故删除该列。
ALTER TABLE articles DROP COLUMN review_status;
