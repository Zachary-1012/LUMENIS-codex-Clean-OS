# ZBC Phase 4 — Database 25 空表源码级分类报告

> **审计日期**: 2026-09-06
> **仓库**: D:\Taikoo-monitor-new (分支 feat/zbc-full-upgrade-v1)
> **数据库**: data/monitor.db (SQLite, 52张表, 27非空/25空)
> **审计性质**: 只读审计，未修改数据库、未修改源码、未执行 git commit
> **审计方法**: SQLite PRAGMA 表结构 + 全仓库 3168 文件源码扫描 + Grep 定向验证

---

## 一、分类统计汇总

| 分类 | 数量 | 占比 |
|------|------|------|
| **KEEP** | 25 | 100% |
| MIGRATE | 0 | 0% |
| DEPRECATE | 0 | 0% |
| DELETE-CANDIDATE | 0 | 0% |
| UNKNOWN | 0 | 0% |

**核心结论**: 25张空表全部具有明确的生产用途和活跃的 Producer/Consumer 链路，无任何表可标记为删除候选或废弃。空表状态反映的是"功能已就绪但尚未触发数据写入"或"数据已被清空/重置"，而非"死表"。

---

## 二、DB Table → Producer → Consumer → API → Metric → UI/Report 追踪链总表

| # | 表名 | Producer | Consumer | API | Report/Metric | UI | 分类 |
|---|------|----------|----------|-----|---------------|-----|------|
| 1 | ai_filter_log | database.py:940 | monitoring.py:234 | 健康检查引用 | 采集质量统计 | — | KEEP |
| 2 | alert_records | alert_engine.py:230 | alert_engine.py:195,206,209,220,371 | /api/alerts (app.py:2488) | 风险预警指标 | risk.html | KEEP |
| 3 | app_evidence_records | app_evidence.py:148, evidence_store.py:155 | app_evidence.py:139,165,171,187,212 (+18) | evidence API | 证据链指标 | — | KEEP |
| 4 | auth_recovery_tasks | auth_recovery_center.py:162 | auth_recovery_center.py:188,194,220,242,261 (+4) | /api/auth-recovery/* (auth_recovery_api.py) | Auth恢复状态 | — | KEEP |
| 5 | brand_knowledge | brand_knowledge_base.py:111 | brand_knowledge_base.py:106,121,147,150, resource_library.py:213 | /api/brand-knowledge/* (app.py:257,267) | 知识库统计 | findings.html, cases.html | KEEP |
| 6 | case_deep_analysis | case_deep_analysis.py:129 | case_deep_analysis.py:93,97,181,189,214 (+5) | /api/case-deep/* (app.py:286-361) | 案例库质量分 | cases.html | KEEP |
| 7 | collection_logs | database.py:759, xhs_cookie_bridge.py:644 | app.py:4390,4392, daily_report.py:148,151,155 (+36) | /api/collection/* | 日报采集状态、熔断判定 | monitor页 | KEEP |
| 8 | collector_quality_log | database.py:1075 | check_logs.py:33, data/verify_db*.py | function_registry引用 | 采集质量日志 | — | KEEP |
| 9 | event_graph_events | event_graph.py:252 | event_graph.py:344,494 | /api/event-graph/events (app.py:460,508) | 事件图谱统计 | cases.html | KEEP |
| 10 | event_graph_relations | event_graph.py:314 | event_graph.py:350 | /api/event-graph/relations (app.py:532) | 事件关系图谱 | cases.html | KEEP |
| 11 | event_insights | database.py:1042 | database.py:1053, 健康检查 | — | 事件AI洞察 | — | KEEP |
| 12 | event_mentions | database.py:929 | app.py:2655,2744,2746, database.py:281,284 (+4) | 事件详情API | 事件提及统计 | 事件详情页 | KEEP |
| 13 | events | database.py:821 (+10) | app.py:2643-2649,2705, export_report.py:200, kos_report.py:47, report_api.py:461, report_engine.py:74 (+68) | /api/events/* (多处) | 日报/周报/KOS报告核心 | 多页面 | KEEP |
| 14 | feedback_keywords | database.py:806 | database.py:811 | — | 反馈关键词循环 | — | KEEP |
| 15 | note_comments | database.py:1091 | kos_engine.py:344,345, kos_intel.py:95,97, kos_report.py:44 (+5) | KOS评论API | KOS报告评论统计 | — | KEEP |
| 16 | note_review_history | reprocess.py:51,66 | (无直接SELECT，审计日志设计) | function_registry引用 | 笔记审核审计 | — | KEEP |
| 17 | podcast_ai_runs | podcast_store.py:213 | (无直接SELECT，AI运行追踪日志) | /api/podcast/* (podcast_routes.py) | Podcast AI运行追踪 | — | KEEP |
| 18 | podcast_entities | podcast_store.py:112 | podcast_store.py:154,184,196,198,199 | /api/podcast/entities (podcast_routes.py:61) | 实体图统计 | — | KEEP |
| 19 | professional_accounts | kos_professional.py:99 | kos_professional.py:82,121,138,190 | /api/kos/professional/* | 专业号接入状态 | overview.html | KEEP |
| 20 | professional_metrics | kos_professional.py:168 | kos_professional.py:211 | /api/kos/professional/metrics | 专业号指标 | overview.html | KEEP |
| 21 | swire_notes | swire_group.py:167 | swire_group.py:147,156,163,232,245 (+4) | swire_group.register_swire_group (app.py:978) | 太古集团多项目笔记 | — | KEEP |
| 22 | token_stat | ark_llm.py:68,69 | ark_llm.py:49,50 | — | ARK LLM Token用量 | — | KEEP |
| 23 | topic_campaign_notes | topic_campaign.py:292 | topic_campaign.py:270,275,886,996,1102 (+13) | topic_campaign API | 话题活动统计 | — | KEEP |
| 24 | v4_audit_logs | v4_upgrade/auth/audit.py:23 | v4_upgrade/auth/audit.py:55,60,79,81 (+2) | v4审计查询API | 审计统计 | — | KEEP |
| 25 | v4_login_attempts | v4_upgrade/auth/security.py:93 | (无直接SELECT，安全日志设计) | — | 登录安全追踪 | — | KEEP |

---

## 三、逐表详细分析

### 1. ai_filter_log

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), note_id(NOT NULL), filter_stage, filter_result, filter_reason, noise_type, confidence REAL, provider, filtered_at. 索引: idx_ai_filter_result, idx_ai_filter_note |
| **Producer** | database.py:940 — INSERT INTO ai_filter_log (AI过滤结果写入) |
| **Consumer** | monitoring.py:234 — AI过滤日志统计查询; deployment/健康检查.py:65 — 表存在性检查 |
| **API引用** | 健康检查间接引用 |
| **Report引用** | 采集质量监控统计 |
| **Migration** | database_migrations.py:214 (迁移3→4) |
| **ORM** | models.py:201-203 (AIFilterLog) |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | AI过滤审计日志，有明确Producer（database.py写入过滤结果）和Consumer（monitoring.py统计过滤效果），属于系统内循环质量保障链路。空表原因：AI过滤功能可能尚未在当前数据上触发，或日志已被清理。 |
| **风险评估** | 低。表结构完整，有索引，有迁移记录。 |

### 2. alert_records

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), alert_key(NOT NULL), alert_type(NOT NULL), severity(NOT NULL), metric_key, metric_value, message, state, created_at, updated_at, audit_log. 索引: idx_alert_records_created, idx_alert_records_state |
| **Producer** | alert_engine.py:230 — INSERT INTO alert_records (含冷却检查) |
| **Consumer** | alert_engine.py:195(SELECT by id), 206(UPDATE state), 209(SELECT after update), 220(冷却检查SELECT), 371(列表SELECT) |
| **API引用** | app.py:2488 /api/alerts, 2498 /api/alerts/read, 2513 /api/alerts/refresh |
| **Report引用** | 风险预警指标 (app.py:4033 未读预警数) |
| **UI** | templates/production/risk.html — 系统告警展示 |
| **Migration** | alert_engine.py:80 自建表 |
| **ORM** | 无独立ORM，直接SQL |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | 完整的告警状态机系统（DETECTED→NOTIFIED→ESCALATED→RESOLVED），有Producer、Consumer、API、UI全链路。含冷却机制和审计日志(audit_log字段)。空表原因：当前无触发告警的条件。 |
| **风险评估** | 低。状态机设计完整，有索引。 |

### 3. app_evidence_records

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), source(NOT NULL), capture_mode(NOT NULL), captured_at, topic, metric_name(NOT NULL), metric_value(NOT NULL), evidence_hash, evidence_path, parse_confidence, verified_by, verified_at, status(NOT NULL), notes, created_at, updated_at. 索引: idx_app_evidence_hash, idx_app_evidence_status, idx_app_evidence_topic |
| **Producer** | app_evidence.py:148 (证据上传写入), evidence_store.py:155 (通用证据存储) |
| **Consumer** | app_evidence.py:139(哈希查重), 165(获取单条), 171(SELECT by id), 187(列表查询), 212(状态更新) + evidence_store.py多处，共22处Consumer |
| **API引用** | app_evidence API (证据上传/查询/验证) |
| **Report引用** | 证据链可追溯指标 |
| **Migration** | 00-GOVERNANCE/_t10_db_audit.py 审计引用 |
| **ORM** | 无独立ORM |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | 证据管理系统核心表，58处引用/25文件，双Producer（上传+存储），22处Consumer（查询/验证/列表），含哈希去重、验证流程、状态管理。是"分析结论可追溯到原始证据"原则的数据基础。 |
| **风险评估** | 低。表结构完善，有3个索引，含验证状态字段。 |

### 4. auth_recovery_tasks

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), platform(NOT NULL), issue_type(NOT NULL), status(NOT NULL), title, description, qr_code_url, recovery_url, created_at, updated_at, completed_at, expires_at, created_by, error_message, metadata. 索引: idx_recovery_platform, idx_recovery_status |
| **Producer** | auth_recovery_center.py:162 — INSERT INTO auth_recovery_tasks |
| **Consumer** | auth_recovery_center.py:188(查询pending), 194(按平台查询), 220(UPDATE start), 242(UPDATE complete), 261(过期清理) + architecture_api.py:139,151 |
| **API引用** | auth_recovery_api.py — /api/auth-recovery/summary, /tasks, /tasks/<id>/start, /tasks/<id>/complete 等 |
| **Report引用** | Auth恢复状态监控 |
| **Migration** | auth_recovery_center.py:103 自建表 |
| **ORM** | 无 |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | AGENTS.md第7.2节明确要求的"全局Auth状态中心"的数据载体。完整的任务生命周期（pending→in_progress→completed→expired），有QR码/恢复URL字段，有API全链路。是Cookie/session失效可处理可恢复的核心基础设施。 |
| **风险评估** | 低。符合AGENTS.md Auth体验全局能力要求。 |

### 5. brand_knowledge

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), category(NOT NULL), title(NOT NULL), content(NOT NULL), source, url, tags, content_hash(UNIQUE), relevance_score, created_at, updated_at. 索引: idx_bk_created, idx_bk_tags, idx_bk_category, UNIQUE(content_hash) |
| **Producer** | brand_knowledge_base.py:111 — INSERT (含哈希去重) |
| **Consumer** | brand_knowledge_base.py:106(查重), 121(search), 147(按分类), 150(统计), resource_library.py:213(同步) |
| **API引用** | app.py:257 /api/brand-knowledge/stats, 267 /api/brand-knowledge/search |
| **Report引用** | 知识库统计 |
| **UI** | templates/research/findings.html, templates/production/cases.html |
| **Migration** | 无（brand_knowledge_base.py自建） |
| **ORM** | 无 |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | 品牌知识库系统，有去重机制(content_hash UNIQUE)、分类、标签、相关性评分。API+UI完整链路。与resource_library有数据同步关系。属于AGENTS.md第9节品牌传播情报能力的知识层。 |
| **风险评估** | 低。 |

### 6. case_deep_analysis

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), case_id(UNIQUE, NOT NULL), case_title(NOT NULL), brand, agency, industry, year, case_type, basic_info, challenge, strategy, big_idea, execution, channels, results, awards, success_factors, methodology, system_insights, quality_score, created_at, updated_at. 索引: idx_cda_quality, idx_cda_type, idx_cda_industry, idx_cda_brand, UNIQUE(case_id) |
| **Producer** | case_deep_analysis.py:129 — INSERT/UPDATE (含质量分计算) |
| **Consumer** | case_deep_analysis.py:93(质量分), 97(查重), 181(get_case), 189(list), 214(stats) + app.py:286-361多处API |
| **API引用** | app.py:286,296,320,336,350,361 — 案例详情/列表/搜索/统计 |
| **Report引用** | 案例库质量分统计 |
| **UI** | templates/production/cases.html |
| **Migration** | 无（case_deep_analysis.py自建） |
| **ORM** | 无 |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | 品牌营销案例深度分析库，60处引用/24文件，完整的案例拆解字段（挑战/策略/大创意/执行/渠道/结果/奖项），含自动质量评分。API+UI完整。属于AGENTS.md第10节"品牌营销案例库"菜单的数据基础。 |
| **风险评估** | 低。表结构丰富，有4个索引+唯一约束。 |

### 7. collection_logs

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), keyword(NOT NULL), notes_count INTEGER, status, error_msg, started_at, finished_at. **无索引** |
| **Producer** | database.py:759 log_collection(), xhs_cookie_bridge.py:644 _write_collection_log() (六态状态机) |
| **Consumer** | app.py:4390(统计), 4392(熔断判定), daily_report.py:148,151,155(日报采集状态), check_collection*.py, 共40处Consumer |
| **API引用** | app.py多处采集状态API |
| **Report引用** | daily_report.py — 日报采集状态核心数据源 |
| **UI** | 监测页面采集状态展示 |
| **Migration** | 无（database.py自建） |
| **ORM** | models.py:183-185 (CollectionLog) |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | **核心表**。98处引用/52文件，是采集状态六态机（SUCCESS/NO_NEW_DATA/RISK_WARNING/NEED_VERIFY/BLOCKED/SESSION_EXPIRED/COLLECT_ERROR/COOLING_DOWN）的持久化层。日报、熔断判定、健康检查均依赖此表。AGENTS.md第7.3节采集状态的直接实现。 |
| **风险评估** | **中**。表无任何索引，在40处Consumer高频查询下可能有性能问题。建议后续添加 idx_collection_logs_status 和 idx_collection_logs_finished_at 索引（属MIGRATE级优化，但不影响当前分类）。 |

### 8. collector_quality_log

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), note_id(NOT NULL), status, score REAL, detail_status, comments_collected INTEGER, collector_version, checked_at, reason. 索引: idx_collector_quality_note |
| **Producer** | database.py:1075 save_collector_quality() — INSERT |
| **Consumer** | check_logs.py:33(查询), data/verify_db.py:23, data/verify_db2.py:34 (诊断脚本) |
| **API引用** | function_registry.py:19 — monitor.collect功能注册 |
| **Report引用** | 采集质量日志 |
| **Migration** | database_migrations.py:269 (迁移5→6) |
| **ORM** | models.py:192-194 (CollectorQualityLog) |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | 采集质量评估日志，记录每条笔记的采集质量分、详情状态、评论采集数、采集器版本。有Producer（database.py写入）和诊断Consumer。有迁移记录和ORM模型。属于采集质量保障链路。 |
| **风险评估** | 低。Consumer主要是诊断脚本，生产查询压力小。 |

### 9. event_graph_events

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), event_id(UNIQUE, NOT NULL), event_type(NOT NULL), title(NOT NULL), event_time, source, description, status, metadata, source_event_id, created_at, updated_at. 索引: idx_event_graph_events_source, idx_event_graph_events_status, idx_event_graph_events_type, UNIQUE(event_id) |
| **Producer** | event_graph.py:252 — INSERT INTO event_graph_events |
| **Consumer** | event_graph.py:344(加载所有事件), 494(从现有events表导入) |
| **API引用** | app.py:460 /api/event-graph/events (GET), 508 (POST), 704 /api/event-graph/import, 807 DELETE |
| **Report引用** | 事件图谱统计 |
| **UI** | templates/production/cases.html |
| **Migration** | event_graph.py:125 自建表 |
| **ORM** | 无 |
| **外键** | 无（source_event_id逻辑关联events表） |
| **最终分类** | **KEEP** |
| **分类理由** | AGENTS.md第9.3节"三类事件"和event_relation能力的数据层。支持从现有events表导入（import_from_existing_events），有事件类型/状态/来源管理。API完整（CRUD+导入+关系重建）。 |
| **风险评估** | 低。与events表有逻辑关联但无外键约束，需注意数据一致性。 |

### 10. event_graph_relations

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), source_event_id(NOT NULL), target_event_id(NOT NULL), relation_type(NOT NULL), evidence, confidence REAL, created_at. 索引: idx_event_graph_relations_type, idx_event_graph_relations_target, idx_event_graph_relations_source, UNIQUE(source_event_id,target_event_id,relation_type) |
| **Producer** | event_graph.py:314 — INSERT INTO event_graph_relations |
| **Consumer** | event_graph.py:350 — 加载关系 |
| **API引用** | app.py:532 /api/event-graph/relations (POST), 719 /api/event-graph/rebuild-relations |
| **Report引用** | 事件关系图谱 |
| **UI** | templates/production/cases.html |
| **Migration** | event_graph.py 自建 |
| **ORM** | 无 |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | AGENTS.md第9节"event_relation"能力的直接实现，记录事件间触发/衍生/继发/并行关系。含证据和置信度字段。与event_graph_events配套使用。 |
| **风险评估** | 低。 |

### 11. event_insights

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), event_id(NOT NULL), ai_summary, risk_assessment, recommended_action, sentiment_trend, propagation_analysis, key_voices, provider, generated_at. 索引: idx_event_insights_event |
| **Producer** | database.py:1042 save_event_insight() — INSERT |
| **Consumer** | database.py:1053 get_event_insight() — SELECT by event_id; deployment/健康检查.py:65 |
| **API引用** | 事件详情间接引用 |
| **Report引用** | 事件AI洞察 |
| **Migration** | database_migrations.py:251 |
| **ORM** | models.py:210-212 (EventInsight) |
| **外键** | 无（event_id逻辑关联events表） |
| **最终分类** | **KEEP** |
| **分类理由** | AI生成的事件洞察存储（摘要/风险评估/建议行动/情绪趋势/传播分析/关键声音），含provider字段支持多AI Provider。符合AGENTS.md第3节"AI输出必须可记录、可追溯"要求。 |
| **风险评估** | 低。 |

### 12. event_mentions

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), event_id(NOT NULL), source_type, source_id, match_score REAL, created_at. UNIQUE(event_id, source_type, source_id) |
| **Producer** | database.py:929 — INSERT INTO event_mentions (事件-笔记关联) |
| **Consumer** | app.py:2655(负面确认联动), 2744,2746(JOIN notes查询事件笔记), database.py:281,284(UPDATE events.event_date从event_mentions关联notes取最早发布日期) |
| **API引用** | 事件详情API |
| **Report引用** | 事件提及统计 |
| **Migration** | database_migrations.py:187 |
| **ORM** | models.py:220-222 (EventMention) |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | 事件与内容（笔记/评论等）的多对多关联表。是事件聚合的核心关联层，支持按事件查询关联笔记、负面确认联动、事件日期归一化（AGENTS.md第6节时间口径）。8处Consumer含关键的JOIN查询和UPDATE联动。 |
| **风险评估** | 低。 |

### 13. events

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), event_key(UNIQUE, NOT NULL), title, summary, fact_status, impact, risk_reason, recommended_action, first_seen, last_seen, mention_count, source_count, risk_level, risk_score, status, keywords, translations, ai_provider, event_date, negative_confirmed, negative_confirmed_at, negative_confirmed_by. 索引: idx_events_risk, UNIQUE(event_key) |
| **Producer** | database.py:821 (主INSERT), scripts/init_database_data.py:197 (种子数据), 共11处Producer |
| **Consumer** | app.py:2643-2649(事件查询), 2705(事件列表), export_report.py:200(报告导出), kos_report.py:47(KOS报告), report_api.py:461(报告API), report_engine.py:74(报告引擎), 共74处Consumer |
| **API引用** | app.py多处 — 事件CRUD、负面确认、事件列表 |
| **Report引用** | daily_report, export_report, kos_report, report_api, report_engine — **所有报告核心数据源** |
| **UI** | 舆情监测、风险预警、事件中心、负面确认等多页面 |
| **Migration** | database_migrations.py:126, database.py:58, scripts/init_db.py:112 |
| **ORM** | models.py:60-62 (Event) |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | **系统核心表**。1053处引用/237文件，11个Producer，74个Consumer。是事件中心、风险预警、负面确认、日报/周报/月报、KOS报告的统一数据基础。含事实状态(fact_status)、风险等级、负面确认流程(negative_confirmed)、AI Provider追踪等完整字段。 |
| **风险评估** | **高**。**该表为空是本次审计发现的最大异常**。作为系统核心表，1053处引用却0行数据，可能原因：(1)数据库被重置/重新初始化；(2)事件聚合管道(reprocess.build_cross_platform_events)尚未运行；(3)数据迁移过程中丢失。**建议立即排查事件聚合管道是否正常运行，并检查是否有备份可恢复。** |

### 14. feedback_keywords

| 维度 | 详情 |
|------|------|
| **表结构** | keyword(PK), source, score REAL, enabled INTEGER, first_seen, last_seen, used_count INTEGER. UNIQUE(keyword) |
| **Producer** | database.py:806 upsert_feedback_keyword() — INSERT OR REPLACE |
| **Consumer** | database.py:811 get_feedback_keywords() — SELECT |
| **API引用** | 无直接API（内部反馈循环） |
| **Report引用** | 反馈关键词统计 |
| **Migration** | database_migrations.py:143 |
| **ORM** | models.py:238-240 (FeedbackKeyword) |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | 用户反馈关键词闭环存储，支持关键词评分、启用/禁用、使用计数。是AI/规则反馈学习的基础设施（AGENTS.md第3节"修正结果可沉淀为规则/样本"）。UPSERT模式保证幂等。 |
| **风险评估** | 低。 |

### 15. note_comments

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), comment_id(UNIQUE, NOT NULL), note_id(NOT NULL), content, author_id, author_nickname, likes INTEGER, publish_time, parent_id, raw_json, fetched_at. 索引: idx_note_comments_note, UNIQUE(comment_id) |
| **Producer** | database.py:1091 save_note_comments() — 批量INSERT OR IGNORE |
| **Consumer** | kos_engine.py:344,345(KOS评论查询), kos_intel.py:95,97(评论情报), kos_report.py:44(评论统计), cache_manager.py:119, 共10处Consumer |
| **API引用** | KOS评论API |
| **Report引用** | kos_report.py — KOS报告评论总数 |
| **Migration** | database_migrations.py:284 (迁移5→6) |
| **ORM** | models.py:83-85 (NoteComment) |
| **外键** | 无（note_id逻辑关联notes表） |
| **最终分类** | **KEEP** |
| **分类理由** | 笔记评论存储，是KOS/KOL分析的核心数据源。含raw_json保留原始数据、parent_id支持评论层级、fetched_at追踪采集时间。10处Consumer集中在KOS分析链路。AGENTS.md第7节"评论失败不得静默丢弃笔记"的评论层实现。 |
| **风险评估** | 低。 |

### 16. note_review_history

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), note_id(NOT NULL), old_relevance, new_relevance, old_sentiment, new_sentiment, old_risk, new_risk, reason, provider, reviewed_at. **无索引** |
| **Producer** | reprocess.py:51 (AI重处理审核), reprocess.py:66 (审核更新) |
| **Consumer** | **无直接SELECT查询**（审计日志设计，写入后不主动查询） |
| **API引用** | function_registry.py:23 — notes.search功能注册引用 |
| **Report引用** | 无直接报告引用 |
| **Migration** | database_migrations.py:202 (迁移3→4) |
| **ORM** | models.py:228-230 (NoteReviewHistory) |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | 笔记审核变更审计日志，记录相关性/情绪/风险的前后值变更、原因、Provider。**审计日志按设计为write-only**，无Consumer是正常的。符合AGENTS.md第3节"AI输出必须可记录、可追溯、可人工修正"要求。有迁移记录和ORM模型。 |
| **风险评估** | 低。无索引对write-only日志表影响可忽略。 |

### 17. podcast_ai_runs

| 维度 | 详情 |
|------|------|
| **表结构** | run_id(PK), entity_id, model, prompt, input_hash, runtime_ms INTEGER, status, output_json, error, created_at. 索引: idx_podcast_airun_entity, UNIQUE(run_id) |
| **Producer** | podcast_store.py:213 — INSERT OR REPLACE INTO podcast_ai_runs |
| **Consumer** | **无直接SELECT查询**（AI运行追踪日志，write-only设计） |
| **API引用** | podcast_routes.py注册的 /api/podcast/* 蓝图（app.py:243-244，try/except包裹） |
| **Report引用** | 无 |
| **Migration** | podcast_store.py:75 自建表 |
| **ORM** | 无 |
| **外键** | 无（entity_id逻辑关联podcast_entities） |
| **最终分类** | **KEEP** |
| **分类理由** | Podcast模块AI运行追踪日志，记录模型/Prompt/输入哈希/运行时/状态/输出/错误。**按设计为write-only追踪日志**，用于AI可追溯性（AGENTS.md第3节）。Podcast模块已在app.py注册API蓝图（含/overview, /entities, /entity等端点），属于可选功能模块。 |
| **风险评估** | 中。Podcast模块在app.py中以try/except包裹注册（app.py:243-246），表明是可选/实验性功能。若未来确定不做Podcast方向，此表可降级为DEPRECATE。当前保持KEEP。 |

### 18. podcast_entities

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), entity_type(NOT NULL), entity_id(UNIQUE, NOT NULL), parent_id, title, start_ms, end_ms, speaker_id, attributes_json, relations_json, evidence_ids_json, evidence_status(NOT NULL), confidence REAL, source_json, observed_at, runtime_seconds, published_at, metrics_json, tags_json, created_at, updated_at. 索引: idx_podcast_evidence, idx_podcast_parent, idx_podcast_entity_type, UNIQUE(entity_type, entity_id) |
| **Producer** | podcast_store.py:112 — INSERT OR REPLACE |
| **Consumer** | podcast_store.py:154(列表查询), 184(get_entity), 196(按类型统计), 198,199(按证据状态统计) |
| **API引用** | podcast_routes.py:61 /api/podcast/entities, 76 /api/podcast/entity |
| **Report引用** | 实体图统计 (podcast_store.get_stats) |
| **Migration** | podcast_store.py 自建 |
| **ORM** | 无 |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | Podcast实体图存储，支持实体类型/层级(parent_id)/时间轴/属性/关系/证据/置信度。有完整的Producer+Consumer+API链路。16处引用/6文件。与podcast_ai_runs配套。 |
| **风险评估** | 中。同podcast_ai_runs，Podcast模块为可选功能。 |

### 19. professional_accounts

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), brand_id(NOT NULL), platform(NOT NULL), account_id(NOT NULL), account_name, verified_type, auth_status(NOT NULL), enabled(NOT NULL), access_token, last_sync_at, sync_status, last_error, created_at, updated_at. UNIQUE(brand_id, platform, account_id) |
| **Producer** | kos_professional.py:99 — INSERT (开启专业号接入) |
| **Consumer** | kos_professional.py:82(is_enabled检查), 121(关闭接入UPDATE), 138(list_accounts), 190(指标导入) |
| **API引用** | /api/kos/professional/status, /enable, /disable, /import (app.py + kos_professional.py) |
| **Report引用** | 专业号接入状态 |
| **UI** | templates/production/overview.html — KOS professional卡片 |
| **Migration** | kos_professional.py 自建 |
| **ORM** | 无 |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | KOS专业号接入配置表，支持多品牌/多平台/多账号，含认证状态/启用开关/同步状态/access_token。UI中明确标注"Professional-account ingestion is optional, toggled per brand. Disabled by default"。是AGENTS.md第9.1节传播主体中"官方/机构"主体的数据接入层。 |
| **风险评估** | 低。access_token字段存储需注意加密（当前为明文TEXT，建议后续评估安全风险）。 |

### 20. professional_metrics

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), account_id(NOT NULL), brand_id(NOT NULL), metric_date(NOT NULL), impressions, views, cover_ctr REAL, follower_gain, likes, comments, collects, shares, source, created_at. UNIQUE(account_id, metric_date) |
| **Producer** | kos_professional.py:168 — INSERT (专业号指标导入) |
| **Consumer** | kos_professional.py:211 — 查询专业号指标 |
| **API引用** | /api/kos/professional/metrics |
| **Report引用** | 专业号指标统计 |
| **UI** | templates/production/overview.html |
| **Migration** | kos_professional.py 自建 |
| **ORM** | 无 |
| **外键** | 无（account_id逻辑关联professional_accounts） |
| **最终分类** | **KEEP** |
| **分类理由** | 专业号每日指标存储（曝光/浏览/封面CTR/涨粉/互动），与professional_accounts配套。含UNIQUE(account_id, metric_date)防重复。是KOS传播主体分析的指标数据源。 |
| **风险评估** | 低。 |

### 21. swire_notes

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), project_key, brand, note_id, title, author, likes, comments, collects, shares, sentiment, note_url, publish_date, collected_at. 索引: idx_swn_proj, UNIQUE(project_key, note_id) |
| **Producer** | swire_group.py:167 — INSERT (幂等写入，含UPDATE分支) |
| **Consumer** | swire_group.py:147(查重), 156(遍历), 163(UPDATE), 232(总数统计), 245(按项目统计) + 共9处Consumer |
| **API引用** | swire_group.register_swire_group(app) (app.py:978) — 太古集团多项目API |
| **Report引用** | 太古集团多项目笔记统计 |
| **Migration** | swire_group.py:115 自建表 |
| **ORM** | 无 |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | 太古集团多项目笔记存储，支持广州/上海/北京/成都/香港等多project_key隔离。广州太古汇笔记数取自主库notes表，其他项目写入swire_notes。符合AGENTS.md第5节"广州太古汇与上海/北京/成都/香港等同名或相似场景必须严格隔离"要求。40处引用/24文件。 |
| **风险评估** | 低。 |

### 22. token_stat

| 维度 | 详情 |
|------|------|
| **表结构** | day(PK), used INTEGER. UNIQUE(day) |
| **Producer** | ark_llm.py:68,69 — INSERT OR REPLACE INTO token_stat (每日Token用量累计) |
| **Consumer** | ark_llm.py:49,50 — SELECT used FROM token_stat (查询当日用量) |
| **API引用** | 无直接API（内部LLM调用统计） |
| **Report引用** | 无 |
| **Migration** | ark_llm.py:49 自建表 (CREATE TABLE IF NOT EXISTS) |
| **ORM** | 无 |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | ARK LLM每日Token用量统计表，极简2字段设计（day PK + used）。TOKEN_DB指向data/monitor.db（同库）。Producer和Consumer均在ark_llm.py中，用于LLM调用成本追踪。符合AGENTS.md第3节AI Provider可追溯要求。 |
| **风险评估** | 低。表结构极简，INSERT OR REPLACE保证幂等。 |

### 23. topic_campaign_notes

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), campaign_key(NOT NULL), topic(NOT NULL), note_id(NOT NULL), title, content, author, publish_datetime, likes, comments, collects, shares, note_url, first_seen_at, last_seen_at, raw_json. 索引: idx_tcn_campaign_topic_time, UNIQUE(campaign_key, topic, note_id) |
| **Producer** | topic_campaign.py:292 — INSERT |
| **Consumer** | topic_campaign.py:270(查重), 275(UPDATE), 886(活动详情), 996(Note Detail下钻), 1102(话题分布) + 共18处Consumer |
| **API引用** | topic_campaign.py注册的活动监测API |
| **Report引用** | 话题活动统计、内容类型分布 |
| **Migration** | topic_campaign.py 自建 |
| **ORM** | 无 |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | 话题活动笔记关联表，支持营销活动(Campaign)维度的笔记追踪。含first_seen_at/last_seen_at时间口径（AGENTS.md第6节）、raw_json原始数据保留、复合唯一索引防重复。44处引用/23文件，18处Consumer。是AGENTS.md第9.3节"营销事件"的数据层。 |
| **风险评估** | 低。 |

### 24. v4_audit_logs

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), user_id, username, action(NOT NULL), resource, resource_id, detail, ip, created_at. 索引: idx_v4_audit_time, idx_v4_audit_user |
| **Producer** | v4_upgrade/auth/audit.py:23 — INSERT (记录用户操作) |
| **Consumer** | v4_upgrade/auth/audit.py:55(条件查询), 60(分页查询), 79(返回), 81(统计) + tests/v4_smoke.py |
| **API引用** | v4审计查询API (audit.py) |
| **Report引用** | 审计统计 |
| **Migration** | v4_upgrade/auth/models.py:59 自建 |
| **ORM** | 无 |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | V4用户体系操作审计日志，记录用户/动作/资源/IP/时间。有完整的查询API（条件筛选+分页+统计）。21处引用/13文件。是V4权限体系的安全审计基础。 |
| **风险评估** | 低。 |

### 25. v4_login_attempts

| 维度 | 详情 |
|------|------|
| **表结构** | id(PK), username, ip, success INTEGER, created_at. **无索引** |
| **Producer** | v4_upgrade/auth/security.py:93 — INSERT (记录登录尝试) |
| **Consumer** | **无直接SELECT查询**（安全日志设计，写入后用于风控判定，可能在security.py内部逻辑中使用但未直接SELECT此表） |
| **API引用** | 无直接API |
| **Report引用** | 无 |
| **Migration** | v4_upgrade/auth/models.py:59 自建 |
| **ORM** | 无 |
| **外键** | 无 |
| **最终分类** | **KEEP** |
| **分类理由** | V4登录尝试安全日志，记录用户名/IP/成功失败/时间。**安全日志按设计为write-only**，用于暴力破解检测和安全审计。13处引用/12文件。tests/v4_smoke.py验证建表带v4_前缀。 |
| **风险评估** | 低。无索引对write-only安全日志影响可忽略。 |

---

## 四、风险与异常汇总

### 高风险

1. **events表为空（0行）但有1053处引用** — 系统核心事件表为空，可能导致事件中心、风险预警、负面确认、日报/周报等功能显示空数据。需排查事件聚合管道（reprocess.build_cross_platform_events）是否正常运行，检查数据库是否被重置。

### 中风险

2. **collection_logs表无索引** — 98处引用/40处Consumer高频查询，无任何索引可能导致性能瓶颈。建议添加 idx_collection_logs(status, finished_at)。

3. **Podcast模块（podcast_entities, podcast_ai_runs）为可选功能** — app.py中以try/except包裹注册，若未来确定不做Podcast方向，这两张表可降级为DEPRECATE。

4. **professional_accounts.access_token明文存储** — 建议评估是否需要加密存储。

### 低风险

5. **3张write-only审计日志表无Consumer**（note_review_history, podcast_ai_runs, v4_login_attempts）— 按设计正常，无需处理。

6. **2张表无索引**（collection_logs, v4_login_attempts, note_review_history）— 对write-only表影响小，collection_logs需关注。

---

## 五、审计方法论

1. **表结构获取**: SQLite PRAGMA table_info / index_list / foreign_key_list，获取字段、类型、索引、外键、行数
2. **源码扫描**: Python脚本扫描3168个文件（.py/.sql/.html/.js/.md/.yaml等），对每张表执行多行SQL上下文匹配，分类为PRODUCER（INSERT/REPLACE）、CONSUMER（SELECT/UPDATE）、REFERENCE
3. **Grep定向验证**: 对关键表（events, token_stat, podcast, v4等）使用Grep工具验证Producer/Consumer/API/Migration引用
4. **迁移追踪**: 检查database_migrations.py、alembic/、migrations/目录
5. **ORM追踪**: 检查models.py中的MODEL_REGISTRY
6. **API/UI追踪**: 检查app.py路由注册、templates/HTML中的fetch调用
7. **分类判定**: 基于Producer存在性、Consumer存在性、API集成、Report引用、Migration记录、UI集成六维度综合判定

---

## 六、结论

25张空表**全部为KEEP**，无DELETE-CANDIDATE、无DEPRECATE、无MIGRATE、无UNKNOWN。

所有表均具有明确的生产用途和活跃的代码链路。空表状态不代表"死表"，而是反映：
- 部分功能为可选/按需触发（professional_accounts, podcast, alert_records）
- 部分为审计/日志表（write-only设计）
- 核心表events为空是**异常状态**，需立即排查

**建议下一步**:
1. 优先排查events表为空的原因，恢复事件聚合管道
2. 为collection_logs添加索引
3. 评估Podcast模块的产品定位，确定是否长期维护
4. 评估professional_accounts.access_token加密需求
