# ZBC Phase 15 - Historical Data 历史数据治理审计报告

> **版本**: V1.0
> **日期**: 2026-09-06
> **分支**: feat/zbc-full-upgrade-v1 (HEAD 5e0ccd0)
> **执行**: 豆包本地开发环境（只读审计 + ADD COLUMN 迁移 + 新建模块/测试）
> **核心原则**: 历史数据不得被新规则静默改写；CTH 独立 namespace；新字段 ADD COLUMN 可空，不修改现有数据

---

## 1. 历史数据现状

### 1.1 数据库概览

| 指标 | 值 |
|------|-----|
| 数据库文件 | `data/monitor.db` |
| 总表数 | 57 |
| 非空表 | 30 |
| 空表 | 27 |
| 数据库大小 | ~2.49 MB |
| Schema 版本 | v10（Phase15 迁移后） |

### 1.2 历史数据表统计

| 表名 | 行数 | 时间范围 (publish) | 来源平台 | 主体过滤 | Hash/Provenance | rule_version |
|------|------|---------------------|----------|----------|-----------------|--------------|
| `notes` | 3 | 2026-08-31 | xhs (3) | is_taikoo_verified=0 (3) | 无 | 无（新增可空列） |
| `web_mentions` | 10 | 2018-03-14 ~ 2026-09-04 | sogou_search (10) | 无字段 | 无 | 无 |
| `daily_reports` | 15 | 2026-09-04 ~ 2026-09-06 | - | - | artifact_hash 有 | generator_version/data_version 有 |
| `swire_notes` | 0 | - | - | - | - | - |
| `canonical_data` | 13 | 2018-03-14 ~ 2026-09-04 | xhs(3) + sogou_search(10) | - | content_hash + provenance 有 | 无（新增可空列） |

### 1.3 notes 表详情（3行，均为测试数据）

| note_id | title | publish_datetime | source_platform | is_taikoo_verified |
|---------|-------|------------------|-----------------|---------------------|
| qgate_ok_001 | 测试笔记 | 2026-08-31 | xhs | 0 |
| qgate_warn_001 | 缺url | (空) | xhs | 0 |
| qgate_explicit_001 | explicit | 2026-08-31 | xhs | 0 |

> **注意**: notes 表现有 3 行均为质量门测试数据（qgate_*），非真实舆情数据。is_taikoo_verified 全部为 0。

### 1.4 canonical_data 表详情（13行）

- **product_id**: 全部为 `CTH`（已实现 namespace 隔离）
- **来源**: 3 条 xhs note（来自 notes 表）+ 10 条 sogou_search web_mention
- **content_hash**: 16位短哈希，已存在
- **provenance**: 格式 `source_table:source_id`，已存在
- **publish_datetime 范围**: 2018-03-14 ~ 2026-09-04

### 1.5 时间口径

- `notes.publish_datetime`: 真实发布时间（2026-08-31）
- `notes.captured_at`: 采集时间（2026-09-04 22:51:31）
- `web_mentions.published_at`: 网页发布时间
- `web_mentions.fetched_at`: 采集时间
- **双时间已分离**，符合 AGENTS.md 第6节要求

---

## 2. 备份数据库清单

`data/backups/` 目录下共 **6 个 .db 文件** + **8 个 WAL** + **8 个 SHM**：

| 备份文件 | 大小 | 表数 | notes | web_mentions | daily_reports | canonical_data |
|----------|------|------|-------|--------------|---------------|----------------|
| before_recovery_20260905_034254.db | 0.68 MB | 44 | 3 | 10 | 5 | 0 |
| before_recovery_20260905_153434.db | 1.53 MB | 46 | 3 | 10 | 5 | 0 |
| before_recovery_20260905_154118.db | 1.54 MB | 46 | 3 | 10 | 5 | 0 |
| before_recovery_20260905_154750.db | 1.55 MB | 46 | 3 | 10 | 5 | 0 |
| before_recovery_20260905_190600.db | 1.75 MB | 46 | 3 | 10 | 5 | 0 |
| kos_test_data_20260905_052856.db | 0.07 MB | 6 | 0 | 0 | 0 | 0 |

**备份汇总（跨所有备份）**:
- notes 总计: 15 行（各备份均3行）
- web_mentions 总计: 50 行（各备份均10行）
- daily_reports 总计: 25 行（各备份均5行）
- canonical_data: 0 行（canonical_data 是较新表，备份中尚无）

> **所有备份均未删除**，符合"不要删除备份数据库"要求。

---

## 3. 历史数据目录

| 目录 | 内容 | 用途判断 |
|------|------|----------|
| `2026-08-30/new-chat/` | outputs/, work/ | ChatGPT 会话输出，非结构化历史数据 |
| `2026-08-30/new-chat-2/` | outputs/, work/ | ChatGPT 会话输出，非结构化历史数据 |
| `2026-09-01/new-chat/` | outputs/, work/ | ChatGPT 会话输出，非结构化历史数据 |
| `staging/evidence-export/` | 67个 evidence-snapshot-*.json | 证据链导出快照（2026-09-04 ~ 2026-09-06） |
| `staging/ai-budget.jsonl` | AI 预算日志 | AI 调用预算记录 |

> 以上目录均不含可直接导入的结构化历史舆情数据，暂不纳入导入流水线。

---

## 4. 历史数据导入规范（historical_data_importer.py）

### 4.1 模块位置

`D:\Taikoo-monitor-new\historical_data_importer.py`

### 4.2 导入流水线

```
raw_record → normalize → compute_hash → dedup_check → subject_filter →
provenance_build → timestamp_validate → INSERT(ONLY) → log_import
```

### 4.3 核心 API

| 函数 | 功能 |
|------|------|
| `compute_content_hash(title, content, body)` | SHA256 内容哈希（前16位），归一化去URL/HTML/空白 |
| `check_duplicate(conn, content_hash, note_id, table)` | 双重去重：先 content_hash，后 note_id |
| `build_provenance(source_table, source_id, ...)` | 构建溯源字符串 `source_table:source_id` |
| `validate_timestamps(publish_datetime, captured_at, publish_date)` | 双时间校验，publish 不得被 captured 顶替 |
| `normalize_platform(source_platform)` | 平台标准化（xhs→xiaohongshu 等） |
| `resolve_product_id(product_id)` | 产品标识解析，默认 CTH |
| `apply_subject_filter(title, body, content, ...)` | 主体过滤（复用 subject_rules.subject_hit()） |
| `register_rule_version(conn, version, ...)` | 注册规则版本，旧版本自动设为非激活 |
| `ensure_baseline_rule_version(conn)` | 确保基线版本 hist-v1.0 已注册（幂等） |
| `import_historical_note(raw, conn, batch_id, ...)` | 单条导入（INSERT ONLY，永不 UPDATE） |
| `import_historical_batch(records, ...)` | 批量导入，返回统计摘要 |
| `verify_historical_integrity(db_path)` | 历史数据完整性审计（只读） |
| `log_import(conn, ...)` | 写入 historical_import_log 审计日志 |

### 4.4 安全保证

1. **永不 UPDATE 现有行**: 导入器只执行 INSERT，重复数据跳过并记录
2. **双时间铁律**: publish_datetime 缺失时不用 captured_at 顶替，标记警告
3. **主体过滤复用**: 直接调用 subject_rules.subject_hit()，不修改 SUBJECT_WORDS
4. **rule_version 固化**: 每条记录导入时的规则版本永久保存，新规则不覆盖
5. **全链路审计**: 每次导入写入 historical_import_log，可追溯可回滚
6. **dry_run 模式**: 支持预演导入，不写入数据库

---

## 5. rule_version 追踪机制

### 5.1 数据库变更（Migration 9→10）

**新增字段（ADD COLUMN，可空，不修改现有数据）**:

| 表 | 字段 | 类型 | 说明 |
|----|------|------|------|
| `notes` | `rule_version` | TEXT | 规则版本，历史数据保持原始版本 |
| `notes` | `content_hash` | TEXT | SHA256 内容哈希（去重用） |
| `notes` | `provenance` | TEXT | 来源溯源 source_table:source_id |
| `notes` | `product_id` | TEXT | 产品标识 CTH/ZBC（namespace 隔离） |
| `canonical_data` | `rule_version` | TEXT | 规则版本 |

**新增表**:

| 表名 | 用途 |
|------|------|
| `rule_version_registry` | 规则版本注册表（版本号/词表哈希/激活状态/变更日志） |
| `historical_import_log` | 历史导入审计日志（批次/来源/哈希/去重/主体/状态） |

### 5.2 规则版本注册机制

```
register_rule_version() → 旧版本 is_active=0 → 新版本 is_active=1
```

- 每次规则变更注册新版本，记录 subject_words_hash / exclude_words_hash
- 历史数据的 rule_version 字段永久保存导入时的版本
- 新规则注册不影响已有数据的 rule_version

### 5.3 当前注册版本

| version | 描述 | subject_words | exclude_words | is_active |
|---------|------|---------------|---------------|-----------|
| hist-v1.0 | ZBC Phase15 历史数据基线规则版本 | 17 | 18 | 1 |

---

## 6. 静默改写风险检查结果

### 6.1 reprocess.py 风险评估

**风险等级**: MEDIUM（有审计保护）

| 检查项 | 结果 |
|--------|------|
| 是否有 UPDATE notes | **是**（第49/57/62/65行：更新 is_taikoo_verified, relevance_status, sentiment, risk_level 等） |
| 是否有审计日志 | **是**（写入 note_review_history，记录 old/new 值） |
| 是否有备份机制 | **是**（full_refresh() 先调用 backup_database()） |
| 是否可静默改写历史结论 | **潜在风险**：reprocess_notes() 会重新分析并覆盖现有结论 |
| 缓解措施 | note_review_history 审计链 + 备份 + 主体硬过滤优先 |

**结论**: reprocess.py 确实会 UPDATE notes 表的分析结论，但具备完整的审计链（note_review_history）和备份机制。对于 pre-Phase15 的历史数据（rule_version 为空的 3 条 notes），运行 reprocess.py 会覆盖其原始结论。**建议**: 对 rule_version 为空的历史数据，reprocess 前应先标注 rule_version=hist-v1.0 并备份。

### 6.2 populate_empty_tables.py 风险评估

**风险等级**: LOW（安全）

| 检查项 | 结果 |
|--------|------|
| 是否有 UPDATE | **否**（全文无 UPDATE 语句） |
| 是否使用 INSERT OR IGNORE | **是** |
| 是否先检查 COUNT>0 | **是**（每个函数先检查已有数据，有则跳过） |
| 操作的表 | web_topics, web_events, weekly_events, notification_logs（当前 schema 中均不存在） |

**结论**: populate_empty_tables.py 只对空表做 INSERT OR IGNORE，不触碰现有数据，无静默改写风险。但其引用的表在当前 57 表 schema 中不存在，属于遗留脚本。

### 6.3 database.py insert_note() 风险评估

**风险等级**: MEDIUM（对已有 note_id 会 UPDATE）

`insert_note()` 在 note_id 已存在时执行 UPDATE（第388行起），可能覆盖历史数据。historical_data_importer.py **不使用** insert_note()，而是独立实现 INSERT ONLY 逻辑。

### 6.4 历史数据保护验证

```
verify_historical_integrity() 输出:
- notes_total: 3
- notes_without_rule_version: 3 (pre-Phase15 历史数据，需保护)
- canonical_total: 13 (全部 CTH)
- canonical_cth: 13
- warnings: 3 notes have no rule_version - these must NOT be silently overwritten
```

---

## 7. CTH Namespace 隔离方案

### 7.1 现状

- `canonical_data.product_id`: 13 行全部为 `CTH` ✅
- `notes.product_id`: 新增可空列，现有 3 行为 NULL（pre-Phase15 数据）
- `subject_rules.ACTIVE_BRAND`: `"guangzhou_taikoo_hui"`（CTH 生产主体，红线锁定）

### 7.2 隔离机制

| 层级 | 机制 | 说明 |
|------|------|------|
| 数据层 | `product_id` 字段 | notes/canonical_data 均有 product_id，CTH 与 ZBC 物理可分 |
| 规则层 | `subject_rules.BRAND_PROFILES` | 多品牌配置，ACTIVE_BRAND 默认 CTH |
| 导入层 | `resolve_product_id()` | 历史导入默认 CTH，显式指定可切换 |
| 查询层 | 可按 product_id 过滤 | 未来报告/统计可按 namespace 隔离 |
| 审计层 | `historical_import_log.product_id` | 每次导入记录产品标识 |

### 7.3 历史数据标注建议

现有 3 条 pre-Phase15 notes（product_id=NULL），建议在首次历史导入时标注：
- `product_id = 'CTH'`
- `rule_version = 'hist-v1.0'`
- `provenance = 'notes:pre_phase15'`
- `content_hash` = 基于现有 title/content 计算

> 本次执行**未修改**现有数据（符合"绝对不要修改现有数据库数据"要求），标注留待用户确认后执行。

---

## 8. 测试结果

### 8.1 测试文件

`tests/test_historical_data.py` — 29 个测试用例，全部使用临时内存数据库，不触碰生产库。

### 8.2 测试覆盖

| 测试类 | 用例数 | 覆盖内容 |
|--------|--------|----------|
| TestHashDedup | 6 | 相同内容同哈希/不同内容异哈希/URL忽略/hash去重/note_id去重/无误判 |
| TestProvenance | 2 | provenance格式/导入时记录 |
| TestTimestamp | 2 | 发布采集分离/缺失不顶替 |
| TestSourcePlatform | 1 | 平台标准化 |
| TestCTHNamespace | 3 | 默认CTH/记录product_id/ZBC隔离 |
| TestSubjectFilter | 3 | CTH命中/排除词否决/导入记录 |
| TestRuleVersion | 4 | 注册/新旧切换/导入记录/基线幂等 |
| TestHistoricalProtection | 4 | 不UPDATE现有行/保持原始rule_version/导入日志/去重日志 |
| TestSilentOverwriteRisk | 4 | reprocess审计链/reprocess备份/populate INSERT IGNORE/populate检查 |

### 8.3 运行结果

```
============================= 29 passed in 0.26s =============================
```

**全部通过**。

---

## 9. 变更文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `database_migrations.py` | 修改 | 新增 migration_9_to_10，CURRENT_VERSION→10 |
| `historical_data_importer.py` | 新建 | 历史数据导入规范模块 |
| `tests/test_historical_data.py` | 新建 | 29个测试用例 |
| `data/monitor.db` | 迁移 | ADD COLUMN（可空，未修改现有数据）+ 新建2表 + 注册基线规则版本 |
| `audit/historical_data_audit.md` | 新建 | 本报告 |

### 9.1 数据库变更明细（均为向后兼容）

```sql
-- notes 表新增4列（可空，现有3行保持NULL）
ALTER TABLE notes ADD COLUMN rule_version TEXT;
ALTER TABLE notes ADD COLUMN content_hash TEXT;
ALTER TABLE notes ADD COLUMN provenance TEXT;
ALTER TABLE notes ADD COLUMN product_id TEXT;

-- canonical_data 表新增1列（可空，现有13行保持NULL）
ALTER TABLE canonical_data ADD COLUMN rule_version TEXT;

-- 新建2表
CREATE TABLE rule_version_registry (...);
CREATE TABLE historical_import_log (...);
```

---

## 10. 未完成项与风险

### 10.1 未完成项

| 项 | 状态 | 原因 |
|----|------|------|
| 现有3条notes标注 product_id/rule_version | 未执行 | 禁止修改现有数据库数据，留待用户确认 |
| web_mentions 添加 rule_version | 未执行 | 任务仅要求 notes 和 canonical_data |
| 真实历史数据导入 | 未执行 | 无可导入的结构化历史数据源 |
| reprocess.py 增加 rule_version 保护 | 未执行 | 超出本次范围，建议后续 Phase |
| Git commit | 未执行 | 任务明确禁止 |

### 10.2 已知风险

1. **reprocess.py 可覆盖历史结论**: 对 rule_version 为空的 pre-Phase15 数据，运行 reprocess_notes() 会重新分析并 UPDATE。建议后续在 reprocess.py 中增加 rule_version 检查，对历史数据跳过或先备份。
2. **database.insert_note() 对已有 note_id 做 UPDATE**: 历史导入不应使用此函数，historical_data_importer.py 已独立实现 INSERT ONLY。
3. **populate_empty_tables.py 引用不存在的表**: web_topics/web_events/weekly_events/notification_logs 在当前 schema 中不存在，脚本运行会报错但不影响数据。

### 10.3 下一步建议

1. 用户确认后，对现有3条 pre-Phase15 notes 标注 product_id='CTH', rule_version='hist-v1.0'
2. 在 reprocess.py 中增加 rule_version 保护：对 rule_version 非空的历史数据跳过重分析
3. 收集真实历史数据（备份库/导出文件）后，使用 historical_data_importer.py 批量导入
4. 报告/统计模块增加 product_id 过滤，实现 CTH/ZBC 视图隔离

---

## 11. 验收标准对照

| 验收标准 | 状态 | 证据 |
|----------|------|------|
| 历史数据现状已审计 | ✅ | 第1-3节 |
| 导入规范已建立（Hash→Dedup→Provenance→Timestamp→Source→Product→Subject） | ✅ | 第4节，historical_data_importer.py |
| rule_version 追踪已建立 | ✅ | 第5节，migration_9_to_10 + rule_version_registry |
| 历史数据不被新规则静默改写 | ✅ | 第6节，导入器 INSERT ONLY + rule_version 固化 + 测试验证 |
| CTH 历史数据独立 namespace | ✅ | 第7节，product_id 字段 + canonical_data 全部 CTH |
| 测试通过 | ✅ | 第8节，29/29 passed |
| 审计报告已创建 | ✅ | 本文件 |

---

*报告结束。所有操作均遵循 AGENTS.md "先审计、再修改；先兼容、再重构" 原则，未删除/修改任何现有数据库数据。*
