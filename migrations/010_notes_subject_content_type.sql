-- GAP-06：notes 表传播主体(subject_type)/内容(content_type)双维度
-- 向后兼容纯增量迁移。SQLite 的 ALTER TABLE ADD COLUMN 不支持 IF NOT EXISTS，
-- 幂等由 database.py 的 NOTE_MIGRATIONS（PRAGMA table_info 检查后再 ADD）统一执行；
-- 本文件仅作结构留档与手工执行参考，生产库不手工跑，随启动迁移自动补齐。
--
-- subject_type 枚举（固定白名单）：
--   official / kos / kol / koc / normal_user / media / institution
-- content_type 枚举（固定白名单）：
--   ugc / commercial / official / review / experience / complaint / event
-- 默认空串 '' 表示历史数据/分类器未标注，绝不影响既有主体过滤、风险与统计口径。

ALTER TABLE notes ADD COLUMN subject_type TEXT DEFAULT '';
ALTER TABLE notes ADD COLUMN content_type TEXT DEFAULT '';
