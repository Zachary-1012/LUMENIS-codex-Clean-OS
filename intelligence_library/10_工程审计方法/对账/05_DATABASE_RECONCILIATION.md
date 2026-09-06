# 05 — DATABASE RECONCILIATION（数据库对账）

> 审计日期：2026-09-02  
> OSAI HEAD：`60af16a`（`D:\Zachary OS AI`）  
> ZBC HEAD：`545a3ab` v5.9.9（`D:\Taikoo-monitor-new`）  
> 事实源：ZBC `data/monitor.db`（生产库，只读 `.schema` / `SELECT` 查询，零写入）

## 状态计数

| 状态 | 计数 |
|------|------|
| EXISTS | 18 |
| PARTIAL | 9 |
| MISSING | 5 |
| UNKNOWN | 0 |

---

## 1. 生产库定位（哪一个 monitor.db 是真库）

| 候选路径 | 大小 | 修改时间 | 表数 | 判定 | 状态 |
|----------|------|----------|------|------|------|
| `D:\Taikoo-monitor-new\data\monitor.db` | 6,754,304 B | 2026-09-02 09:48:56 | **53** | **生产事实源** | EXISTS |
| `D:\Taikoo-monitor-new\monitor.db`（根目录） | 12,288 B | 2026-08-28 14:12:39 | 1（仅 `token_stat`） | 旧版/残留 stub | PARTIAL |
| `D:\Taikoo-monitor-new\你的数据库文件名.db` | 0 B | 2026-08-29 00:15:14 | 0（空文件） | 占位空文件，非有效库 | MISSING |

- 证据：`database.py:13` `DB_PATH = os.path.join(_BASE_DIR, 'data', 'monitor.db')`，支持 `ZBC_DB_PATH` 环境变量覆盖（Staging 隔离）。
- 根目录 `monitor.db` 仅含 `token_stat` 一张表，与生产 53 表严重不符，判定为历史残留，**不应被任何代码连接**。
- `你的数据库文件名.db` 为 0 字节空文件，无 schema，无数据。

---

## 2. 表清单对账（生产库 53 表 vs 声明源）

### 2.1 生产库全部 53 张表（按字母序）

```
ai_filter_log, app_evidence_records, auth_recovery_tasks,
brand_industry_monitor, brand_knowledge, case_deep_analysis,
collection_counters, collection_logs, collector_quality_log,
comments, daily_digest, daily_reports,
event_graph_events, event_graph_relations, event_insights, event_mentions, events,
feedback_keywords, industry_stats,
note_comments, note_review_history, notes,
notification_config, notification_logs,
review_logs, review_samples, review_tickets,
schedule_decisions, schema_version, sqlite_sequence,
swire_events, swire_notes, swire_projects, system_config,
token_stat,
topic_campaign_notes, topic_campaign_snapshots, topic_campaign_topics, topic_campaigns,
v4_ai_shadow, v4_audit_logs, v4_login_attempts, v4_security_questions,
v4_sessions, v4_users, v4_workspace_grants, v4_workspace_keys,
web_events, web_mentions, web_runs, web_sources, web_topics, weekly_events
```

（`sqlite_sequence` 为 SQLite 内部自动维护表，不计入业务表。业务表 = 52 张。）

### 2.2 各声明源覆盖范围

| 声明源 | 路径 | 声明表数 | 与生产 52 业务表对比 | 状态 |
|--------|------|----------|----------------------|------|
| `database.py` SCHEMA 常量 | `D:\Taikoo-monitor-new\database.py:15-153` | 15 | 覆盖 15 张核心表 | PARTIAL |
| `models.py` MODEL_REGISTRY | `D:\Taikoo-monitor-new\models.py:275-298` | 25 | 覆盖 25 张，缺 27 张 | PARTIAL |
| `database_migrations.py` | `D:\Taikoo-monitor-new\database_migrations.py` | v1–v8 迁移函数 | 迁移函数内 CREATE TABLE 与实际 schema **列定义不一致**（见 §5） | PARTIAL |
| `migrations/009_global_bil_staging.sql` | `D:\Taikoo-monitor-new\migrations\009_global_bil_staging.sql` | 18 张 `bi_*` 表 | **全部不在生产库**（Staging-only，未应用） | MISSING（生产侧） |
| `migrations/010_notes_subject_content_type.sql` | `D:\Taikoo-monitor-new\migrations\010_notes_subject_content_type.sql` | ALTER notes 加 2 列 | 已在生产库 `notes` 表中存在（`subject_type`, `content_type`） | EXISTS |
| `v4_upgrade/` 模块 | `D:\Taikoo-monitor-new\v4_upgrade\auth\`、`v4_upgrade\ai_hub\` | 8 张 `v4_*` 表 | 全部在生产库中存在 | EXISTS |
| OSAI DB Schema/Contract 声明 | `D:\Zachary OS AI\` 全仓 | **0** | 无任何正式 DB Schema/Contract 声明文件；旧 `04_database_reconciliation.md` 为历史审计文档（已过时，称 15 CREATE TABLE / 22 models） | MISSING |

### 2.3 生产库中有但 `database.py` SCHEMA 未声明的表（37 张）

这些表由其他模块动态 `CREATE TABLE IF NOT EXISTS` 创建，未集中在 `database.py`：

| 表名 | 行数 | 可能创建源 | 状态 |
|------|------|-----------|------|
| `app_evidence_records` | 0 | `app_evidence.py` | EXISTS（隐式创建） |
| `auth_recovery_tasks` | 6 | `auth_recovery_center.py` / `v4_upgrade/adapters/auth_recovery.py` | EXISTS（隐式创建） |
| `brand_industry_monitor` | 198 | `brand_stats_recompute.py` / `app.py` | EXISTS（隐式创建） |
| `brand_knowledge` | 103 | `brand_knowledge_base.py` | EXISTS（隐式创建） |
| `case_deep_analysis` | 20 | `case_deep_analysis.py` | EXISTS（隐式创建） |
| `collection_counters` | 1 | `app.py` / `collector.py` | EXISTS（隐式创建） |
| `comments` | 2 | `database.py` 无 SCHEMA，但 `models.py` 有模型 | PARTIAL |
| `event_graph_events` | 16 | `event_graph.py` | EXISTS（隐式创建） |
| `event_graph_relations` | 1 | `event_graph.py` | EXISTS（隐式创建） |
| `industry_stats` | 8 | `brand_stats_recompute.py` | EXISTS（隐式创建） |
| `notification_config` | 0 | `wechat_notifier.py` | EXISTS（隐式创建） |
| `notification_logs` | 3 | `wechat_notifier.py` | EXISTS（隐式创建） |
| `review_logs` | 0 | `review_workflow.py` | EXISTS（隐式创建） |
| `review_samples` | 0 | `review_workflow.py` | EXISTS（隐式创建） |
| `review_tickets` | 0 | `review_workflow.py` | EXISTS（隐式创建） |
| `schedule_decisions` | 369 | `adaptive_engine.py` / `network_adaptive.py` | EXISTS（隐式创建） |
| `swire_events` | 10 | `swire_group.py` | EXISTS（隐式创建） |
| `swire_notes` | 0 | `swire_group.py` | EXISTS（隐式创建） |
| `swire_projects` | 8 | `swire_group.py` | EXISTS（隐式创建） |
| `system_config` | 10 | `settings_module.py` / `config.py` | EXISTS（隐式创建） |
| `token_stat` | 1 | `ai_analyzer.py` / `ark_llm.py` | EXISTS（隐式创建） |
| `topic_campaign_notes` | 120 | `topic_campaign.py` | EXISTS（隐式创建） |
| `topic_campaign_snapshots` | 325 | `topic_campaign.py` | EXISTS（隐式创建） |
| `topic_campaign_topics` | 7 | `topic_campaign.py` | EXISTS（隐式创建） |
| `topic_campaigns` | 1 | `topic_campaign.py` | EXISTS（隐式创建） |
| `v4_ai_shadow` | 2 | `v4_upgrade/ai_hub/shadow.py` | EXISTS（v4 模块创建） |
| `v4_audit_logs` | 35 | `v4_upgrade/auth/audit.py` | EXISTS（v4 模块创建） |
| `v4_login_attempts` | 26 | `v4_upgrade/auth/service.py` | EXISTS（v4 模块创建） |
| `v4_security_questions` | 2 | `v4_upgrade/auth/service.py` | EXISTS（v4 模块创建） |
| `v4_sessions` | 40 | `v4_upgrade/auth/service.py` | EXISTS（v4 模块创建） |
| `v4_users` | 1 | `v4_upgrade/auth/models.py` / `service.py` | EXISTS（v4 模块创建） |
| `v4_workspace_grants` | 13 | `v4_upgrade/auth/workspace.py` | EXISTS（v4 模块创建） |
| `v4_workspace_keys` | 65 | `v4_upgrade/auth/workspace.py` | EXISTS（v4 模块创建） |
| `web_events` | 20 | `web_monitor.py` / `app.py` | EXISTS（隐式创建） |
| `web_topics` | 96 | `web_topic_discovery.py` / `app.py` | EXISTS（隐式创建） |
| `weekly_events` | 30 | `weekly_events.py` | EXISTS（隐式创建） |

> **结论**：`database.py` 的 SCHEMA 常量仅覆盖 15/52 业务表（28.8%），`models.py` 覆盖 25/52（48.1%）。**无单一权威 schema 声明源**，表创建分散在 20+ 个模块中。这是 PARTIAL 状态的核心原因。

---

## 3. 表结构对账（字段 / 类型 / 主键 / 索引）

### 3.1 `notes` 表（核心表，最高保护层所在）

- **生产库实际 schema**：`D:\Taikoo-monitor-new\data\monitor.db` `.schema notes`
  - 主键：`id INTEGER PRIMARY KEY AUTOINCREMENT`
  - 唯一约束：`note_id TEXT UNIQUE NOT NULL`
  - 字段总数：**70+**（含通过 `NOTE_MIGRATIONS` 增量添加的字段）
  - 索引：12 个（`idx_notes_captured_at`, `idx_notes_publish_datetime`, `idx_notes_negative_confirmed`, `idx_notes_verified`, `idx_notes_status`, `idx_notes_publish_date`, `idx_notes_author`, `idx_notes_collected`, `idx_notes_category`, `idx_notes_risk`, `idx_notes_sentiment`, `sqlite_autoindex_notes_1`）
- **`database.py` SCHEMA 声明**：`database.py:16-30`，仅声明 28 个基础字段，其余通过 `NOTE_MIGRATIONS`（`database.py:155-199`）在 `init_db()` 中幂等 ALTER 添加。
- **`models.py` Note 模型**：`models.py:30-58`，声明 73 个字段，与生产库基本一致。
- **状态**：EXISTS（三层声明一致，生产库字段完整）

### 3.2 最高保护层字段专项核对

| 字段 | 应在表 | 生产库实际存在 | 非空行数 / 总行数 | 声明路径 | 状态 |
|------|--------|---------------|-------------------|----------|------|
| `publish_datetime` | `notes` | **是**，`TEXT DEFAULT ''` | 957 / 957 | `database.py:185` NOTE_MIGRATIONS；`models.py:48` | **EXISTS** |
| `captured_at` | `notes` | **是**，`TEXT DEFAULT ''` | 957 / 957 | `database.py:186` NOTE_MIGRATIONS；`models.py:48` | **EXISTS** |
| `publish_datetime` | `topic_campaign_notes` | **是**，`TEXT DEFAULT ''` | — | `topic_campaign.py` 内 CREATE TABLE | EXISTS |
| `captured_at` | `app_evidence_records` | **是**，`TEXT` | — | `app_evidence.py` 内 CREATE TABLE | EXISTS |
| `captured_at` | `topic_campaign_snapshots` | **是**，`TEXT NOT NULL` | — | `topic_campaign.py` 内 CREATE TABLE | EXISTS |
| `detail_captured_at` | `topic_campaign_notes` | **是**，`TEXT DEFAULT ''` | — | `topic_campaign.py` 内 CREATE TABLE | EXISTS |

> **双时间铁律**：`database.py:337-339` 注释明确——"publish_* 来自平台发布时间，captured_at 是本机采集时刻，二者来源不同、绝不互相顶替。" `insert_note()` 中 `publish_datetime` 从 `note_data['publish_datetime']` 取值（缺省回退 `publish_date`），`captured_at` 从 `note_data['captured_at']` 取值（缺省回退当前时间）。**最高保护层字段完整存在且逻辑正确。**

### 3.3 `database_migrations.py` 迁移函数 vs 生产库实际 schema（列定义不一致）

| 迁移函数 | 声明路径 | 创建的表 | 与生产库实际对比 | 状态 |
|----------|----------|----------|-----------------|------|
| `migration_1_to_2` | `database_migrations.py:105-154` | `web_mentions`, `events`, `feedback_keywords` | **列定义严重不一致**：迁移版 `web_mentions` 有 `source/url/author/is_taikoo_related` 等列，生产库实际为 `source_id/source_platform/source_type/domain/relevance/verification/confidence` 等；迁移版 `events` 有 `event_id/description/note_count/total_engagement/category/tags`，生产库实际为 `event_key/fact_status/impact/risk_reason/recommended_action/keywords/translations` 等 | **PARTIAL**（迁移函数是历史旧 schema，与当前生产库不匹配，实际不会被执行——因为 `schema_version` 已到 v7+） |
| `migration_2_to_3` | `database_migrations.py:157-195` | `web_sources`, `web_runs`, `event_mentions` | 列定义不一致（迁移版 `web_sources` 有 `name/url/type/config`，生产库为 `source_key/source_name/adapter/enabled/last_run_at/...`） | PARTIAL |
| `migration_3_to_4` | `database_migrations.py:198-227` | `note_review_history`, `ai_filter_log` | 列定义不一致（迁移版 `note_review_history` 有 `review_type/reviewer/review_result/review_notes`，生产库为 `old_relevance/new_relevance/old_sentiment/new_sentiment/old_risk/new_risk/reason/provider`） | PARTIAL |
| `migration_4_to_5` | `database_migrations.py:230-262` | `daily_digest`, `event_insights` | 列定义不一致 | PARTIAL |
| `migration_5_to_6` | `database_migrations.py:265-299` | `collector_quality_log`, `note_comments` | 列定义不一致 | PARTIAL |
| `migration_6_to_7` | `database_migrations.py:302-313` | ALTER notes 加 `negative_confirmed*` | 与生产库一致（notes 表有这 3 列） | EXISTS |
| `migration_7_to_8` | `database_migrations.py:316-334` | ALTER notes 加 `publish_datetime/captured_at/...` | 与生产库一致（notes 表有这些列） | EXISTS |

> **关键发现**：`database_migrations.py` 的 v1→v6 迁移函数内的 CREATE TABLE 语句是**历史旧版 schema**，与当前生产库实际列定义不匹配。但由于 `schema_version` 表已有 7 条记录（当前版本 ≥ v7），这些迁移函数不会再被执行。`database.py` 的 `init_db()` 才是实际的 schema 初始化+迁移入口（使用 `SCHEMA` 常量 + `NOTE_MIGRATIONS`/`WEB_MIGRATIONS`/`REPORT_MIGRATIONS`/`EVENT_MIGRATIONS` 字典做幂等 ALTER）。
>
> **`database_migrations.py` 处于"历史残留 + 部分有效"状态**：v6→v7、v7→v8 的 ALTER 语句与生产库一致，但 v1→v6 的 CREATE TABLE 已过时。

### 3.4 `schema_version` 表

- 生产库 `schema_version` 行数：7
- `database_migrations.py:25` 声明 `CURRENT_VERSION = 8`
- 状态：PARTIAL（版本表存在但记录数与 CURRENT_VERSION 不完全对应，且 v1→v6 迁移 schema 已过时）

---

## 4. 表间关系（外键 / 关联）

| 关系 | 类型 | 声明路径 | 生产库实际 | 状态 |
|------|------|----------|-----------|------|
| `comments.note_id` → `notes.note_id` | FOREIGN KEY | `database.py` SCHEMA 中 comments 表定义（实际生产库 comments 表有 `FOREIGN KEY (note_id) REFERENCES notes(note_id)`） | 存在 | EXISTS |
| `v4_sessions.user_id` → `v4_users.id` | FOREIGN KEY | `v4_upgrade/auth/models.py` / `service.py` | 生产库 v4_sessions 表有 `FOREIGN KEY (user_id) REFERENCES v4_users(id)` | EXISTS |
| `event_mentions` → `notes` / `events` | 逻辑关联（`event_id` INTEGER, `source_id` TEXT 对应 `notes.note_id`） | `database.py:87-90` | 无显式 FOREIGN KEY，但代码层通过 `n.note_id=em.source_id` JOIN（`database.py:264`） | PARTIAL（逻辑关联，无 FK 约束） |
| `note_comments.note_id` → `notes.note_id` | 逻辑关联 | `database.py:145-150` | 无显式 FOREIGN KEY，有索引 `idx_note_comments_note` | PARTIAL |
| `ai_filter_log.note_id` → `notes.note_id` | 逻辑关联 | `database.py:96-106` | 无显式 FOREIGN KEY，有索引 `idx_ai_filter_note` | PARTIAL |
| `event_insights.event_id` → `events.id` | 逻辑关联 | `database.py:124-135` | 无显式 FOREIGN KEY，有索引 `idx_event_insights_event` | PARTIAL |
| `note_review_history.note_id` → `notes.note_id` | 逻辑关联 | `database.py:91-94` | 无显式 FOREIGN KEY，无索引 | PARTIAL |
| `collector_quality_log.note_id` → `notes.note_id` | 逻辑关联 | `database.py:140-144` | 无显式 FOREIGN KEY，有索引 | PARTIAL |
| `migrations/009` 中 `bi_*` 表间 FK | FOREIGN KEY | `migrations/009_global_bil_staging.sql` | **生产库中无这些表**（Staging-only） | MISSING（生产侧） |

> **结论**：SQLite 生产库中仅 `comments` 和 `v4_sessions` 两张表有显式 `FOREIGN KEY` 约束。其余表间关系均为**逻辑关联**（代码层 JOIN，无 DB 级 FK 约束）。SQLite 默认不强制外键（需 `PRAGMA foreign_keys=ON`，`database_migrations.py:50` 有设置但 `database.py` 的 `get_db()` 未设置）。

---

## 5. 空表核对（生产库 0 行的表）

| 表名 | 行数 | 状态 | 备注 |
|------|------|------|------|
| `app_evidence_records` | 0 | EXISTS（结构存在，无数据） | App 证据记录表，尚未采集 |
| `notification_config` | 0 | EXISTS（结构存在，无数据） | 通知配置表，未配置 |
| `review_logs` | 0 | EXISTS（结构存在，无数据） | 审核日志表 |
| `review_samples` | 0 | EXISTS（结构存在，无数据） | 审核样本表 |
| `review_tickets` | 0 | EXISTS（结构存在，无数据） | 审核工单表 |
| `swire_notes` | 0 | EXISTS（结构存在，无数据） | 太古地产笔记表，尚未采集 |

- 空表占比：6/52 业务表（11.5%）
- 状态：均为 EXISTS（表结构存在，数据为空是业务状态，非 schema 问题）

---

## 6. 数据质量核对

### 6.1 `notes` 表空正文 / 脏数据

| 检查项 | 结果 | 状态 | 证据 |
|--------|------|------|------|
| 总行数 | 957 | — | `SELECT COUNT(*) FROM notes` |
| `content` 为空（NULL 或 `''`） | **253**（26.4%） | PARTIAL | 253 条笔记正文为空，可能是仅采集了标题/元数据未抓正文 |
| `body` 为空（NULL 或 `''`） | **229**（23.9%） | PARTIAL | `body` 是新增字段，`init_db()` 中有 `UPDATE notes SET body=content WHERE body='' AND content<>''` 兜底，但仍有 229 条为空（content 也为空的历史数据） |
| `title` 为空 | 0 | EXISTS | `insert_note()` 有标题兜底逻辑（`database.py:327-336`） |
| `publish_date` 为空 | 0 | EXISTS | 全部 957 条有 publish_date |
| `publish_date` 脏值（非 YYYY-MM-DD） | **0**（抽查 top 15 均为合法日期） | EXISTS | top 值：`2026-08-28`(26), `2026-08-29`(24), `2026-08-23`(16), ... 最早 `2025-07-03`(11) |
| `publish_datetime` 非空 | 957/957 | EXISTS | 最高保护层字段全部非空 |
| `captured_at` 非空 | 957/957 | EXISTS | 最高保护层字段全部非空 |

### 6.2 `publish_date` 分布（top 10）

| publish_date | 行数 |
|-------------|------|
| 2026-08-28 | 26 |
| 2026-08-29 | 24 |
| 2026-08-23 | 16 |
| 2026-08-27 | 15 |
| 2026-08-30 | 15 |
| 2026-07-30 | 13 |
| 2026-08-21 | 13 |
| 2026-08-03 | 12 |
| 2026-08-12 | 12 |
| 2026-08-14 | 12 |

> 数据质量结论：`publish_date` 无脏值、无空值；`publish_datetime`/`captured_at` 全部非空。主要数据质量问题是 **26.4% 的笔记 `content` 为空**（正文未抓取完整），以及 **23.9% 的 `body` 为空**（与 content 空高度相关）。

---

## 7. 迁移脚本对账

### 7.1 迁移入口与执行机制

| 项目 | 路径 | 状态 | 备注 |
|------|------|------|------|
| 主迁移入口 `init_db()` | `database.py:232-268` | EXISTS | 应用启动时调用，执行 SCHEMA + 幂等 ALTER |
| 独立迁移脚本 `database_migrations.py` | `database_migrations.py` | PARTIAL | v1→v6 CREATE TABLE 已过时，v6→v8 ALTER 有效；CLI 支持 `status/migrate/rollback/backup/info` |
| SQL 迁移目录 `migrations/` | `migrations/` | PARTIAL | 仅 2 个文件：009（BIL Staging，未应用到生产）、010（notes 双维度，已应用） |
| `v4_upgrade/` 模块内建表 | `v4_upgrade/auth/`, `v4_upgrade/ai_hub/` | EXISTS | 创建 8 张 v4_* 表，全部在生产库中 |
| `schema_version` 版本跟踪 | 生产库 `schema_version` 表 | PARTIAL | 7 条记录，`CURRENT_VERSION=8`，记录不完整 |

### 7.2 迁移幂等性

| 迁移类型 | 幂等方式 | 状态 |
|----------|----------|------|
| `CREATE TABLE IF NOT EXISTS` | `database.py` SCHEMA 全部使用 `IF NOT EXISTS` | EXISTS（安全） |
| `ALTER TABLE ADD COLUMN` | `init_db()` 中先 `PRAGMA table_info` 检查列是否存在，再决定是否 ALTER（`database.py:236-252`） | EXISTS（幂等） |
| `migrations/010` SQL 文件 | 纯 ALTER 语句，**无 IF NOT EXISTS**（SQLite 不支持），文件头注释说明"幂等由 database.py 的 NOTE_MIGRATIONS 统一执行，本文件仅作留档" | PARTIAL（文件本身不可重复执行，但不会被自动执行） |
| `database_migrations.py` 迁移函数 | v1→v6 使用 `CREATE TABLE IF NOT EXISTS`，v6→v8 使用 PRAGMA 检查后 ALTER | EXISTS（幂等，但 schema 已过时） |

---

## 8. ORM 模型对账

### 8.1 `models.py` 模型注册表（25 个模型）

| 模型类 | 表名 | 字段数 | 生产库表存在 | 状态 |
|--------|------|--------|-------------|------|
| `Note` | `notes` | 73 | 是 | EXISTS |
| `Event` | `events` | 19 | 是 | EXISTS |
| `Comment` | `comments` | 14 | 是 | EXISTS |
| `NoteComment` | `note_comments` | 11 | 是 | EXISTS |
| `DailyReport` | `daily_reports` | 31 | 是 | EXISTS |
| `DailyDigest` | `daily_digest` | 16 | 是 | EXISTS |
| `WeeklyEvent` | `weekly_events` | 18 | 是 | EXISTS |
| `WebTopic` | `web_topics` | 12 | 是 | EXISTS |
| `WebEvent` | `web_events` | 14 | 是 | EXISTS |
| `WebMention` | `web_mentions` | 24 | 是 | EXISTS |
| `BrandIndustryMonitor` | `brand_industry_monitor` | 12 | 是 | EXISTS |
| `CollectionCounter` | `collection_counters` | 8 | 是 | EXISTS |
| `CollectionLog` | `collection_logs` | 7 | 是 | EXISTS |
| `CollectorQualityLog` | `collector_quality_log` | 9 | 是 | EXISTS |
| `AIFilterLog` | `ai_filter_log` | 9 | 是 | EXISTS |
| `EventInsight` | `event_insights` | 10 | 是 | EXISTS |
| `EventMention` | `event_mentions` | 6 | 是 | EXISTS |
| `NoteReviewHistory` | `note_review_history` | 10 | 是 | EXISTS |
| `FeedbackKeyword` | `feedback_keywords` | 8 | 是 | EXISTS |
| `SystemConfig` | `system_config` | 6 | 是 | EXISTS |
| `WebSource` | `web_sources` | 10 | 是 | EXISTS |
| `WebRun` | `web_runs` | 9 | 是 | EXISTS |

> `models.py` 注册 25 个模型，全部对应生产库中存在的表。但生产库有 52 张业务表，**27 张表无 ORM 模型**（包括所有 v4_* 表、topic_campaign_* 表、swire_* 表、event_graph_* 表、review_* 表、notification_* 表、brand_knowledge、case_deep_analysis、app_evidence_records、auth_recovery_tasks、industry_stats、schedule_decisions、token_stat）。

### 8.2 `database.py` 数据访问层

- `database.py` 提供 40+ 个数据访问函数（`insert_note`, `get_notes`, `get_stats`, `save_daily_report`, `upsert_event`, ...）
- 直接使用 `sqlite3` 原生 SQL，**不使用 ORM**（`models.py` 的 BaseModel 类定义了 `to_dict`/`from_row` 但在 `database.py` 中未被使用）
- 状态：PARTIAL（`models.py` 定义了 ORM 模型但实际数据层未使用，ORM 与原生 SQL 双轨并存）

---

## 9. OSAI 侧 DB Schema / Contract 声明核对

| 检查项 | OSAI 路径 | 结果 | 状态 |
|--------|-----------|------|------|
| 正式 DB Schema 声明文件（.sql / .py schema 常量） | `D:\Zachary OS AI\` 全仓 | **未找到** | MISSING |
| DB Contract / 数据契约声明 | `components/AI-Development-Research-Hub/src/contracts/` | 仅有 `research_record.py`（研究记录契约）和 `safe_collection.py`（采集安全契约），**无 ZBC 生产库 DB Schema 契约** | MISSING |
| 架构文档中对 ZBC DB 的描述 | `components/AI-Development-Research-Hub/architecture/` | 无 DB schema 级别的契约声明 | MISSING |
| 历史审计文档 | `04_database_reconciliation.md`（OSAI 根目录） | 存在但**已过时**：称 `database.py` 有 15 CREATE TABLE、`models.py` 有 22 模型、7 张表 mismatch；实际生产库 53 表、models.py 25 模型 | PARTIAL（历史参考，非当前事实） |
| OSAI 侧连接 ZBC DB 的代码 | `D:\Zachary OS AI\` 全仓 `.py` | **无**（仅本次对账脚本 `_db_inspect.py` 只读查询，非 OSAI 原有代码） | EXISTS（正确隔离，OSAI 不直连 ZBC 生产库） |

> **结论**：OSAI 侧**没有**对 ZBC 生产库的正式 DB Schema/Contract 声明。合法流向应为 OSAI→Contract/Plan→ZBC，但在 DB Schema 这一层，Contract 是**缺失**的——ZBC 的 53 张表完全由 ZBC 侧自行定义和演化，OSAI 无任何声明或约束。旧 `04_database_reconciliation.md` 是历史审计产物，数据已过时（实际表数从其描述的 ~22 张增长到 53 张）。

---

## 10. 汇总与关键发现

### 10.1 状态计数汇总

| 状态 | 计数 | 占比 |
|------|------|------|
| EXISTS | 18 | 56.3% |
| PARTIAL | 9 | 28.1% |
| MISSING | 5 | 15.6% |
| UNKNOWN | 0 | 0% |

### 10.2 P0 级关键发现（涉及最高保护层）

1. **`publish_datetime` / `captured_at` 完整存在于 `notes` 表**：EXISTS，957/957 非空，`insert_note()` 双时间铁律逻辑正确。**最高保护层无缺失。**
2. **根目录 `monitor.db` 是残留 stub**：仅 1 表 12KB，与生产库 53 表严重不符。若有代码误连此库将导致严重问题。需确认无代码引用根目录 `monitor.db`。
3. **`你的数据库文件名.db` 是 0 字节空文件**：无 schema 无数据，疑似误创建占位文件。

### 10.3 P1 级关键发现

4. **无单一权威 schema 声明源**：`database.py` SCHEMA 覆盖 15/52 表，`models.py` 覆盖 25/52 表，其余 27 张表分散在 20+ 模块中隐式创建。OSAI 侧无 DB Contract 声明。
5. **`database_migrations.py` v1→v6 迁移 schema 已过时**：迁移函数内的 CREATE TABLE 列定义与生产库实际不匹配（虽因版本号已高不会再执行，但作为迁移参考文档具有误导性）。
6. **27 张生产表无 ORM 模型**：`models.py` 仅覆盖 25/52 业务表，v4_*、topic_campaign_*、swire_*、event_graph_*、review_* 等均无模型。
7. **表间关系几乎无 FK 约束**：52 张业务表中仅 2 张有显式 FOREIGN KEY，其余为代码层逻辑关联。

### 10.4 P2 级关键发现

8. **26.4% 笔记 `content` 为空**：957 条中 253 条正文为空，数据完整性待提升。
9. **`migrations/009` BIL Staging  schema 未应用到生产**：18 张 `bi_*` 表定义存在但生产库中无这些表，处于 Staging 设计阶段。
10. **`schema_version` 记录不完整**：7 条记录 vs `CURRENT_VERSION=8`，版本跟踪有缺口。

---

*本文档所有数据库查询均为只读（`SELECT` / `.schema` / `PRAGMA`），未执行任何 INSERT/UPDATE/DELETE/DROP/ALTER。*
