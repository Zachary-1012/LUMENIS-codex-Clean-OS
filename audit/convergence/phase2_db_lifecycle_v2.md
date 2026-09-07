# Phase 2: 数据库表生命周期分类审计报告 V2 (增强版)

> 生成时间: 2026-09-07 17:46:36
> 数据库: `data/monitor.db` (SQLite, 只读模式 mode=ro)
> 仓库: `D:\Taikoo-monitor-new` (Zachary-1012/Z-Brand-Core, main)
> 审计范围: 全部 **129** 张表 = 128 业务表 + 1 系统表(`sqlite_sequence`)
> V1基线: phase2_db_lifecycle.md (128表, KEEP=98/MIGRATE=27/DEPRECATE=3)
> 本版本: V2增强版，新增完整追踪链、git引入历史、重复表合并评估、空表分类

## 0. V2 审计方法增强

| 维度 | V1 | V2增强 |
|------|----|--------|
| 表数量 | 128(用户口径129存疑) | **129确认** = 128业务 + 1系统表(sqlite_sequence) |
| 行数查询 | COUNT(*) | COUNT(*) + 最新记录时间(MAX timestamp列) + schema列 |
| 代码引用 | 文件级匹配 | **文件+行号+函数名+引用类型**(CREATE/INSERT/SELECT/UPDATE/DELETE) |
| 核心代码识别 | 人工分类 | 程序化排除audit/scripts/tests/_check等非生产代码 |
| Git历史 | 无 | **每张表首次引入commit+时间+方法**(CREATE TABLE检索 / -S首次提及) |
| 迁移溯源 | 概览 | 精确定位每张表的CREATE来源文件(migration/database.py/adapter等) |
| 重复表分析 | 列出疑似 | **5组逐一深挖**：schema对比+写入链路+合并建议+影响评估 |
| 空表分类 | 有/无INSERT | **预留扩展 vs 真正无用** 二级分类 |
| 平台表决策 | MIGRATE(15张无adapter) | **用户决策：32张平台预留表统一KEEP**，设置中开启 |

## 1. 分类汇总

| 分类 | 数量 | 占比 | 说明 |
|------|------|------|------|
| KEEP | 118 | 92.2% | 生产核心表，有代码引用+有数据或明确业务用途/预留扩展 |
| MIGRATE | 7 | 5.5% | 有代码引用但schema需演进/合并，或功能未完成需决策 |
| DEPRECATE | 3 | 2.3% | 被新表替代的遗留表，保留历史数据 |
| DELETE-CANDIDATE | 0 | 0.0% | 无代码引用、无数据、无业务用途(本次未发现) |
| UNKNOWN | 0 | 0.0% | 无法确定用途或引用关系(本次未发现) |
| **合计** | **128** | **100%** | |

### 按产品域分布

| 产品域 | 表数 | KEEP | MIGRATE | DEPRECATE |
|--------|------|------|---------|-----------|
| 采集 | 51 | 47 | 1 | 3 |
| 系统 | 33 | 33 | 0 | 0 |
| 品牌 | 15 | 13 | 2 | 0 |
| AI | 11 | 9 | 2 | 0 |
| KOS | 8 | 6 | 2 | 0 |
| 事件 | 5 | 5 | 0 | 0 |
| 风险/舆情 | 3 | 3 | 0 | 0 |
| 报告 | 2 | 2 | 0 | 0 |

## 2. 全表追踪链汇总 (按分类分组)

> 追踪链格式: 表名 → 行数 → 最新记录 → CREATE来源 → INSERT来源 → 核心引用文件 → Git引入 → 分类

### 2.1 KEEP (118 张)

| 表名 | 行数 | 最新记录 | CREATE来源 | INSERT来源 | 核心引用Top3 | Git引入 | 分类理由 |
|------|------|---------|-----------|-----------|-------------|---------|----------|
| ai_call_logs | 1128 | 2026-09-07T17:23:28 | ai_call_logger.py | ai_call_logger.py:253(None); tests\test_ai_evaluation.py:52(_seed_calls) | ai_call_logger.py(15); ai_call_logger.py(15); ai_call_log... | 4501ff6 | 2026-09-06 | firs... | 生产核心表，1128行数据，最新记录2026-09-07T17:23:28，有活跃INSERT写入逻辑 |
| ai_filter_log | 921 | 2026-09-07 15:51:59 | database.py, database_migrations.py | database.py:978(update_note_ai_filter) | evaluation_dimensions.py(7); evaluation_dimensions.py(7);... | e9ef5ad | 2026-09-06 | CREA... | 生产核心表，921行数据，最新记录2026-09-07 15:51:59，有活跃INSERT写入逻辑 |
| ai_task | 2144 | 2026-09-07T17:21:06.16... | ai_task_engine.py | ai_task_engine.py:556(create_task) | ai_task_engine.py(14); ai_task_engine.py(14); ai_task_eng... | f8f3681 | 2026-09-07 | firs... | 生产核心表，2144行数据，最新记录2026-09-07T17:21:06.169471，有活跃INSERT写入逻辑 |
| ai_task_evidence | 2993 | 2026-09-07T17:21:06.18... | ai_task_engine.py | ai_task_engine.py:493(_db_add_evidence) | ai_task_engine.py(9); ai_task_engine.py(9); ai_task_engin... | 32434a3 | 2026-09-07 | firs... | 生产核心表，2993行数据，最新记录2026-09-07T17:21:06.182211，有活跃INSERT写入逻辑 |
| ai_task_step | 4908 | 2026-09-07T17:21:06.17... | ai_task_engine.py | ai_task_engine.py:444(_db_add_step) | ai_task_engine.py(6); ai_task_engine.py(6); ai_task_engin... | 32434a3 | 2026-09-07 | firs... | 生产核心表，4908行数据，最新记录2026-09-07T17:21:06.172907，有活跃INSERT写入逻辑 |
| ai_task_trace | 6176 | 2026-09-07T17:21:06.19... | ai_task_engine.py | ai_task_engine.py:525(_db_add_trace) | ai_task_engine.py(7); ai_task_engine.py(7); ai_task_engin... | 32434a3 | 2026-09-07 | firs... | 生产核心表，6176行数据，最新记录2026-09-07T17:21:06.193849，有活跃INSERT写入逻辑 |
| alert_configs | 13 | 2026-09-06 04:57:40 | alert_engine.py | alert_engine.py:174(set_config); alert_engine.py:178(set_config) | alert_engine.py(10); alert_engine.py(10); alert_engine.py... | 6a74aa7 | 2026-09-04 | firs... | 生产核心表，13行数据，最新记录2026-09-06 04:57:40，有活跃INSERT写入逻辑 |
| alert_records | 0 | - | alert_engine.py | alert_engine.py:230(_record_alert) | alert_engine.py(11); alert_engine.py(11); alert_engine.py... | e9ef5ad | 2026-09-06 | CREA... | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| app_evidence_records | 17 | 2026-09-07 13:10:59 | app_evidence.py, tests\test_batch2_intel_security.py | app_evidence.py:151(create_evidence); evidence_store.py:445(None) | app_evidence.py(18); app_evidence.py(18); app_evidence.py... | 7ea03bf | 2026-09-02 | CREA... | 生产核心表，17行数据，最新记录2026-09-07 13:10:59，有活跃INSERT写入逻辑 |
| auth_recovery_tasks | 6 | 2026-09-07 16:42:29 | auth_recovery_center.py | auth_recovery_center.py:167(create_task) | auth_recovery_center.py(9); auth_recovery_center.py(9); a... | e9ef5ad | 2026-09-06 | CREA... | 生产核心表，6行数据，最新记录2026-09-07 16:42:29，有活跃INSERT写入逻辑 |
| bilibili_comments | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(2); audit\convergen... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| bilibili_users | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(2); audit\convergen... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| bilibili_videos | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | tests\test_platform_data_dict_v1.py(3); tests\test_platfo... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| brand_industry_monitor | 198 | 2026-08-29 13:15:10 | scripts\init_db.py, web_topic_discovery.py | scripts\init_database_data.py:371(init_brand_industry_monitor) | tests\test_refscan_consistency.py(9); tests\test_refscan_... | b69b68f | 2026-08-30 | firs... | 生产核心表，198行数据，最新记录2026-08-29 13:15:10，有活跃INSERT写入逻辑 |
| brand_knowledge | 0 | - | brand_knowledge_base.py | brand_knowledge_base.py:113(add_knowledge) | brand_knowledge_base.py(10); brand_knowledge_base.py(10);... | e9ef5ad | 2026-09-06 | CREA... | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| brands | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | app.py(67); app.py(67); app.py(67) | b69b68f | 2026-08-30 | firs... | Z-Brand多品牌架构核心表，29个核心文件引用，schema已建待品牌数据写入 |
| browser_evidence | 1421 | 2026-09-07T17:21:34.61... | ai_browser_runtime.py | ai_browser_runtime.py:616(record) | ai_browser_runtime.py(11); ai_browser_runtime.py(11); ai_... | 32434a3 | 2026-09-07 | firs... | 生产核心表，1421行数据，最新记录2026-09-07T17:21:34.619374，有活跃INSERT写入逻辑 |
| canonical_data | 14 | neutral | tests\test_historical_data.py | - | canonical_data.py(31); canonical_data.py(31); canonical_d... | 431572c | 2026-09-06 | CREA... | 生产核心表，14行数据，最新记录neutral |
| case_deep_analysis | 0 | - | case_deep_analysis.py | case_deep_analysis.py:131(add_case) | case_deep_analysis.py(14); case_deep_analysis.py(14); cas... | e9ef5ad | 2026-09-06 | CREA... | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| channels_comments | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| channels_videos | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| collection_logs | 502 | 2026-09-07 15:42:29 | database.py | database.py:797(log_collection); xhs_cookie_bridge.py:644(_write_collection_log) | app.py(12); app.py(12); app.py(12) | e9ef5ad | 2026-09-06 | CREA... | 生产核心表，502行数据，最新记录2026-09-07 15:42:29，有活跃INSERT写入逻辑 |
| collection_quality_log | 0 | - | database_migrations.py | - | database_migrations.py(7); database_migrations.py(7); dat... | 559e4d7 | 2026-09-06 | firs... | 采集质量门日志表，database_migrations.py v11迁移创建，待质量门触发写入 |
| collector_quality_log | 7 | 2026-08-29 02:37:56 | database.py, database_migrations.py | database.py:1113(save_collector_quality) | viz_data_provider.py(7); viz_data_provider.py(7); viz_dat... | e9ef5ad | 2026-09-06 | CREA... | 生产核心表，7行数据，最新记录2026-08-29 02:37:56，有活跃INSERT写入逻辑 |
| content_evaluation | 34 | 2026-09-07 04:47:29 | content_generation.py | content_generation.py:442(record_evaluation) | content_generation.py(4); content_generation.py(4); conte... | 9695f5c | 2026-09-07 | firs... | 生产核心表，34行数据，最新记录2026-09-07 04:47:29，有活跃INSERT写入逻辑 |
| content_generation_evidence | 34 | 2026-09-07 04:47:29 | content_generation.py | content_generation.py:418(record_evidence) | content_generation.py(10); content_generation.py(10); con... | 9695f5c | 2026-09-07 | firs... | 生产核心表，34行数据，最新记录2026-09-07 04:47:29，有活跃INSERT写入逻辑 |
| daily_digest | 9 | 2026-09-07 17:22:21 | database.py, database_migrations.py | database.py:1057(save_daily_digest) | database.py(7); database.py(7); database.py(7) | b69b68f | 2026-08-30 | firs... | 生产核心表，9行数据，最新记录2026-09-07 17:22:21，有活跃INSERT写入逻辑 |
| daily_reports | 35 | 暂无数据，无法进行舆情分析。 | database.py, scripts\init_db.py | app.py:4108(_generate_daily_report); database.py:716(save_daily_report) | database.py(24); database.py(24); database.py(24) | 5b10180 | 2026-09-02 | CREA... | 生产核心表，35行数据，最新记录暂无数据，无法进行舆情分析。，有活跃INSERT写入逻辑 |
| douyin_comments | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(2); audit\convergen... | 7ddefdc | 2026-09-05 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| douyin_users | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(2); audit\convergen... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| douyin_videos | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | tests\test_platform_data_dict_v1.py(4); tests\test_platfo... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| event_graph_events | 0 | - | event_graph.py | event_graph.py:252(save_to_db) | event_graph.py(8); event_graph.py(8); event_graph.py(8) | e9ef5ad | 2026-09-06 | CREA... | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| event_graph_relations | 0 | - | event_graph.py | - | event_graph.py(8); event_graph.py(8); event_graph.py(8) | e9ef5ad | 2026-09-06 | CREA... | 有代码引用，业务用途明确 |
| event_insights | 17 | 负面为主，需关注扩散 | database.py, database_migrations.py | database.py:1080(save_event_insight) | daily_report.py(6); daily_report.py(6); daily_report.py(6) | e9ef5ad | 2026-09-06 | CREA... | 生产核心表，17行数据，最新记录负面为主，需关注扩散，有活跃INSERT写入逻辑 |
| event_mentions | 789 | 2026-09-07 15:50:58 | database.py, database_migrations.py | database.py:967(link_event_mentions); scripts\migrate_historical_data.py:651(migrate_event_mentions) | scripts\migrate_historical_data.py(11); scripts\migrate_h... | e9ef5ad | 2026-09-06 | CREA... | 生产核心表，789行数据，最新记录2026-09-07 15:50:58，有活跃INSERT写入逻辑 |
| events | 494 | 2026-09-06 | database.py, database_migrations.py | database.py:859(upsert_event); tests\test_brand_insight.py:22(_mkdb) | app.py(46); app.py(46); app.py(46) | 5b10180 | 2026-09-02 | CREA... | 生产核心表，494行数据，最新记录2026-09-06，有活跃INSERT写入逻辑 |
| feedback_keywords | 16 | - | database.py, database_migrations.py | database.py:844(upsert_feedback_keyword) | database.py(3); database.py(3); database.py(3) | e9ef5ad | 2026-09-06 | CREA... | 生产核心表，16行数据，最新记录N/A，有活跃INSERT写入逻辑 |
| github_issues | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| github_pull_requests | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | data_center_api.py(1); audit\convergence\_generate_report... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| github_releases | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | data_center_api.py(1); audit\convergence\_generate_report... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| github_repositories | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\github.py(2); platform_adapters\github.... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| historical_import_log | 0 | - | database_migrations.py, tests\test_historical_data.py | historical_data_importer.py:198(log_import) | database_migrations.py(7); database_migrations.py(7); dat... | 431572c | 2026-09-06 | CREA... | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| industry_stats | 8 | 2026-08-28T00:40:41.60... | - | - | tests\test_schema_registry.py(3); tests\test_schema_regis... | b69b68f | 2026-08-30 | firs... | 生产核心表，8行数据，最新记录2026-08-28T00:40:41.607183 |
| instagram_comments | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(2); audit\convergen... | 971e58a | 2026-09-05 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| instagram_media | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(2); audit\convergen... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| instagram_users | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(2); audit\convergen... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| intelligence_assets | 711 | 2026-09-06T20:28:24 | migrations\create_intelligence_assets_table.py, scripts\p1c_part2_metadata_db.py | scripts\p1c_part2_metadata_db.py:298(import_to_db) | scripts\p1c_part2_metadata_db.py(19); scripts\p1c_part2_m... | 1085104 | 2026-09-06 | firs... | 生产核心表，711行数据，最新记录2026-09-06T20:28:24，有活跃INSERT写入逻辑 |
| kos_executions | 494 | 2026-09-07 11:45:23 | database_migrations.py, kos_execution.py | kos_execution.py:81(create_execution) | kos_execution.py(8); kos_execution.py(8); kos_execution.p... | 552eb82 | 2026-09-03 | firs... | 生产核心表，494行数据，最新记录2026-09-07 11:45:23，有活跃INSERT写入逻辑 |
| kos_operations | 440 | 2026-09-07 17:22:04 | kos_ops.py | kos_ops.py:83(save_lead); kos_ops.py:120(update_cooperation) | kos_ops.py(9); kos_ops.py(9); kos_ops.py(9) | c8b6bc0 | 2026-09-03 | firs... | 生产核心表，440行数据，最新记录2026-09-07 17:22:04，有活跃INSERT写入逻辑 |
| kos_paid_plans | 176 | 2026-09-07 17:22:04 | kos_paid.py | kos_paid.py:100(execute_paid_plan) | kos_paid.py(7); kos_paid.py(7); kos_paid.py(7) | df9aab9 | 2026-09-03 | firs... | 生产核心表，176行数据，最新记录2026-09-07 17:22:04，有活跃INSERT写入逻辑 |
| kos_profiles | 375 | 2026-09-07 17:22:04 | kos_engine.py, tests\test_batch2_intel_security.py | kos_engine.py:224(None); tests\test_batch2_intel_security.py:616(kreport_temp_db) | kos_engine.py(20); kos_engine.py(20); kos_engine.py(20) | ad02634 | 2026-09-03 | firs... | 生产核心表，375行数据，最新记录2026-09-07 17:22:04，有活跃INSERT写入逻辑 |
| kos_rewards | 88 | 2026-09-07 17:22:04 | kos_paid.py | kos_paid.py:191(execute_reward) | kos_paid.py(5); kos_paid.py(5); kos_paid.py(5) | df9aab9 | 2026-09-03 | firs... | 生产核心表，88行数据，最新记录2026-09-07 17:22:04，有活跃INSERT写入逻辑 |
| linkedin_posts | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| linkedin_users | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| metric_snapshots | 1087 | 2026-09-07 12:26:16 | 00-GOVERNANCE\_path_backup\tests_test_topic_snapshot.py, database.py | database.py:510(record_note_metric_snapshot); database.py:538(record_topic_snapshot) | database.py(7); database.py(7); database.py(7) | 35b2a1e | 2026-09-03 | CREA... | 生产核心表，1087行数据，最新记录2026-09-07 12:26:16，有活跃INSERT写入逻辑 |
| note_comments | 141 | 昨天 09:45浙江 | database.py, database_migrations.py | database.py:1129(upsert_note_comments) | kos_intel.py(5); kos_intel.py(5); kos_intel.py(5) | 8bba987 | 2026-09-06 | CREA... | 生产核心表，141行数据，最新记录昨天 09:45浙江，有活跃INSERT写入逻辑 |
| note_review_history | 8387 | positive | database.py, database_migrations.py | reprocess.py:54(analyze_note_row); reprocess.py:69(analyze_note_row) | evaluation_dimensions.py(4); evaluation_dimensions.py(4);... | e9ef5ad | 2026-09-06 | CREA... | 生产核心表，8387行数据，最新记录positive，有活跃INSERT写入逻辑 |
| notes | 1020 | positive | 00-GOVERNANCE\_path_backup\tests_test_kol_analysis.py, database.py | database.py:467(None); historical_data_importer.py:269(None) | audit\_gen_batch2_csv.py(166); audit\_gen_batch2_csv.py(1... | 2aecc71 | 2026-09-02 | CREA... | 生产核心表，1020行数据，最新记录positive，有活跃INSERT写入逻辑 |
| notification_config | 0 | - | wechat_notifier.py | wechat_notifier.py:1127(add_channel) | wechat_notifier.py(3); wechat_notifier.py(3); wechat_noti... | b69b68f | 2026-08-30 | firs... | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| notification_logs | 3 | 2026-09-06T22:41:24.33... | wechat_notifier.py | populate_empty_tables.py:270(populate_notification_logs); wechat_notifier.py:685(_log_notification) | populate_empty_tables.py(4); populate_empty_tables.py(4);... | b69b68f | 2026-08-30 | firs... | 生产核心表，3行数据，最新记录2026-09-06T22:41:24.336840，有活跃INSERT写入逻辑 |
| platform_accounts | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(3); audit\convergen... | 32434a3 | 2026-09-07 | firs... | 跨平台Canonical统一层预留表，schema已建，待数据汇聚写入 |
| platform_comments | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(2); audit\convergen... | 32434a3 | 2026-09-07 | firs... | 跨平台Canonical统一层预留表，schema已建，待数据汇聚写入 |
| platform_contents | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(6); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 跨平台Canonical统一层预留表，schema已建，待数据汇聚写入 |
| platform_evidence | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(2); audit\convergen... | 32434a3 | 2026-09-07 | firs... | 跨平台Canonical统一层预留表，schema已建，待数据汇聚写入 |
| platform_registry | 12 | 2026-09-06 19:32:14 | migrations\init_platform_registry.py | migrations\init_platform_registry.py:183(init_platform_registry) | migrations\init_platform_registry.py(13); migrations\init... | 969a2cc | 2026-09-05 | firs... | 生产核心表，12行数据，最新记录2026-09-06 19:32:14，有活跃INSERT写入逻辑 |
| podcast_ai_runs | 0 | - | podcast_store.py | podcast_store.py:213(record_ai_run) | audit\convergence\_generate_report.py(4); audit\convergen... | e9ef5ad | 2026-09-06 | CREA... | podcast_store.py有CREATE但需确认INSERT链路，播客AI运行功能状态待验证，有INSERT逻辑属预留扩展 |
| podcast_entities | 0 | - | podcast_store.py | podcast_store.py:112(upsert_entity) | podcast_store.py(10); podcast_store.py(10); podcast_store... | e9ef5ad | 2026-09-06 | CREA... | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| professional_accounts | 0 | - | kos_professional.py | kos_professional.py:99(enable) | kos_professional.py(6); kos_professional.py(6); kos_profe... | e9ef5ad | 2026-09-06 | CREA... | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| reddit_comments | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| reddit_posts | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| reddit_subreddits | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| rule_version_registry | 1 | 2026-09-06 12:44:07 | database_migrations.py, tests\test_historical_data.py | historical_data_importer.py:166(register_rule_version) | database_migrations.py(6); database_migrations.py(6); dat... | 431572c | 2026-09-06 | CREA... | 生产核心表，1行数据，最新记录2026-09-06 12:44:07，有活跃INSERT写入逻辑 |
| runtime_guardian_checkpoints | 74 | 2026-09-07 17:22:59 | runtime_guardian.py | runtime_guardian.py:580(save_checkpoint) | evaluation_dimensions.py(7); evaluation_dimensions.py(7);... | 4501ff6 | 2026-09-06 | firs... | 生产核心表，74行数据，最新记录2026-09-07 17:22:59，有活跃INSERT写入逻辑 |
| runtime_guardian_dlq | 0 | - | runtime_guardian.py, tests\test_evidence_write_failed_health.py | evidence_store.py:341(None); runtime_guardian.py:446(enqueue) | runtime_guardian.py(12); runtime_guardian.py(12); runtime... | 431572c | 2026-09-06 | firs... | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| runtime_guardian_workers | 2551 | 2026-09-07 17:23:12 | runtime_guardian.py | runtime_guardian.py:764(register_worker) | runtime_guardian.py(20); runtime_guardian.py(20); runtime... | 431572c | 2026-09-06 | firs... | 生产核心表，2551行数据，最新记录2026-09-07 17:23:12，有活跃INSERT写入逻辑 |
| schedule_decisions | 15151 | 2026-09-07 18:26:03 | platform_adapters\scheduling\store.py | platform_adapters\scheduling\store.py:77(record) | platform_adapters\scheduling\store.py(7); platform_adapte... | 7e247a9 | 2026-08-30 | firs... | 生产核心表，15151行数据，最新记录2026-09-07 18:26:03，有活跃INSERT写入逻辑 |
| schema_version | 4 | 2026-09-07T11:03:35.65... | database_migrations.py | database_migrations.py:98(set_version); database_migrations.py:622(rollback) | canonical_data.py(8); canonical_data.py(8); canonical_dat... | b69b68f | 2026-08-30 | firs... | 生产核心表，4行数据，最新记录2026-09-07T11:03:35.654617，有活跃INSERT写入逻辑 |
| skill_executions | 18 | 2026-09-07 01:29:03 | skill_execution_chain.py | skill_execution_chain.py:262(write_trace) | skill_execution_chain.py(3); skill_execution_chain.py(3);... | d97f590 | 2026-09-07 | firs... | 生产核心表，18行数据，最新记录2026-09-07 01:29:03，有活跃INSERT写入逻辑 |
| skills_registry | 12 | 2026-09-07 00:17:09 | account\models.py | account\skills.py:36(ensure_builtin_skills); account\skills.py:118(add_custom_skill) | account\skills.py(10); account\skills.py(10); account\ski... | 1085104 | 2026-09-06 | firs... | 生产核心表，12行数据，最新记录2026-09-07 00:17:09，有活跃INSERT写入逻辑 |
| swire_events | 10 | positive | swire_group.py | swire_group.py:133(None); swire_group.py:330(swire_event_add) | swire_group.py(13); swire_group.py(13); swire_group.py(13) | b69b68f | 2026-08-30 | firs... | 生产核心表，10行数据，最新记录positive，有活跃INSERT写入逻辑 |
| swire_notes | 0 | - | swire_group.py | swire_group.py:167(_upsert_brand_notes) | swire_group.py(15); swire_group.py(15); swire_group.py(15) | e9ef5ad | 2026-09-06 | CREA... | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| swire_projects | 8 | 2026-09-07 17:23:20 | swire_group.py | swire_group.py:127(init_swire); swire_group.py:424(swire_brand_save) | swire_group.py(23); swire_group.py(23); swire_group.py(23) | b69b68f | 2026-08-30 | firs... | 生产核心表，8行数据，最新记录2026-09-07 17:23:20，有活跃INSERT写入逻辑 |
| tiktok_comments | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| tiktok_users | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| tiktok_videos | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| token_stat | 0 | - | ark_llm.py | ark_llm.py:74(save_daily_token) | audit\convergence\_generate_report.py(5); audit\convergen... | e9ef5ad | 2026-09-06 | CREA... | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| topic_campaign_notes | 79 | 2026-08-31 00:30:57 | topic_campaign.py | topic_campaign.py:308(_subject_hit); scripts\migrate_historical_data.py:555(migrate_topic_campaign_notes) | topic_campaign.py(12); topic_campaign.py(12); topic_campa... | e9ef5ad | 2026-09-06 | CREA... | 生产核心表，79行数据，最新记录2026-08-31 00:30:57，有活跃INSERT写入逻辑 |
| topic_campaign_snapshots | 325 | 2026-09-06 17:11:25 | topic_campaign.py | topic_campaign.py:187(_insert_snapshot) | topic_campaign.py(9); topic_campaign.py(9); topic_campaig... | b69b68f | 2026-08-30 | firs... | 生产核心表，325行数据，最新记录2026-09-06 17:11:25，有活跃INSERT写入逻辑 |
| topic_campaign_topics | 7 | 2026-09-04 22:33:08 | topic_campaign.py | topic_campaign.py:1235(tc_campaign_save) | topic_campaign.py(8); topic_campaign.py(8); topic_campaig... | b69b68f | 2026-08-30 | firs... | 生产核心表，7行数据，最新记录2026-09-04 22:33:08，有活跃INSERT写入逻辑 |
| topic_campaigns | 1 | 2026-10-07 | topic_campaign.py | topic_campaign.py:1230(tc_campaign_save); scripts\migrate_historical_data.py:610(migrate_topic_campaigns) | topic_campaign.py(11); topic_campaign.py(11); topic_campa... | b69b68f | 2026-08-30 | firs... | 生产核心表，1行数据，最新记录2026-10-07，有活跃INSERT写入逻辑 |
| user_nav_config | 0 | - | account\models.py | account\nav_config.py:82(save_nav_config) | account\nav_config.py(3); account\nav_config.py(3); accou... | 1085104 | 2026-09-06 | firs... | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| v4_audit_logs | 76 | 2026-09-07 17:23:22 | account\models.py, tests\test_evidence_write_failed_health.py | evidence_store.py:315(_record_write_failure); account\audit.py:20(log_audit) | account\audit.py(7); account\audit.py(7); account\audit.p... | e9ef5ad | 2026-09-06 | CREA... | 生产核心表，76行数据，最新记录2026-09-07 17:23:22，有活跃INSERT写入逻辑 |
| v4_login_approvals | 0 | - | account\models.py | - | account\api.py(5); account\api.py(5); account\api.py(5) | 1085104 | 2026-09-06 | firs... | 有代码引用，业务用途明确 |
| v4_login_attempts | 58 | 2026-09-07 17:23:22 | account\models.py, v4_upgrade\auth\models.py | account\security.py:160(record_login_attempt); v4_upgrade\auth\security.py:93(record_login_attempt) | system_ai_data_api.py(3); system_ai_data_api.py(3); syste... | e9ef5ad | 2026-09-06 | CREA... | 生产核心表，58行数据，最新记录2026-09-07 17:23:22，有活跃INSERT写入逻辑 |
| v4_member_authorizations | 2 | 2026-09-06 21:44:28 | account\models.py | account\authorization.py:61(set_member_authorizations) | account\authorization.py(5); account\authorization.py(5);... | 1085104 | 2026-09-06 | firs... | 生产核心表，2行数据，最新记录2026-09-06 21:44:28，有活跃INSERT写入逻辑 |
| v4_product_protection | 0 | - | account\models.py | account\product_protection.py:104(set_protection_config) | account\product_protection.py(5); account\product_protect... | 1085104 | 2026-09-06 | firs... | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| v4_security_questions | 2 | 2026-09-04 22:33:10 | account\models.py, v4_upgrade\auth\models.py | account\models.py:273(_ensure_default_security_questions); v4_upgrade\auth\models.py:118(_ensure_default_security_questions) | v4_upgrade\settings\routes.py(4); v4_upgrade\settings\rou... | b69b68f | 2026-08-30 | firs... | 生产核心表，2行数据，最新记录2026-09-04 22:33:10，有活跃INSERT写入逻辑 |
| v4_sessions | 137 | 2026-09-14 17:23:22 | account\models.py, v4_upgrade\auth\models.py | account\api.py:489(api_totp_verify); tests\test_api_smoke.py:29(test_api_smoke_release_gate) | account\service.py(7); account\service.py(7); account\ser... | b69b68f | 2026-08-30 | firs... | 生产核心表，137行数据，最新记录2026-09-14 17:23:22，有活跃INSERT写入逻辑 |
| v4_totp_secrets | 2 | 2026-09-07 17:23:22 | account\models.py | account\totp.py:175(setup_totp) | account\totp.py(9); account\totp.py(9); account\totp.py(9) | 1085104 | 2026-09-06 | firs... | 生产核心表，2行数据，最新记录2026-09-07 17:23:22，有活跃INSERT写入逻辑 |
| v4_users | 9 | 2026-09-07 17:23:22 | account\models.py, v4_upgrade\auth\models.py | account\models.py:255(_ensure_owner_account); account\service.py:181(create_member) | account\service.py(14); account\service.py(14); account\s... | b69b68f | 2026-08-30 | firs... | 生产核心表，9行数据，最新记录2026-09-07 17:23:22，有活跃INSERT写入逻辑 |
| v4_verification_codes | 0 | - | account\models.py | account\verification.py:140(None) | account\verification.py(11); account\verification.py(11);... | 1085104 | 2026-09-06 | firs... | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| v4_workspace_grants | 78 | 2026-09-07 17:59:07 | account\models.py, v4_upgrade\auth\workspace.py | account\verification.py:286(_issue_grant); v4_upgrade\auth\workspace.py:156(grant_session) | v4_upgrade\auth\workspace.py(5); v4_upgrade\auth\workspac... | e382160 | 2026-09-01 | firs... | 生产核心表，78行数据，最新记录2026-09-07 17:59:07，有活跃INSERT写入逻辑 |
| v4_workspace_keys | 437 | 2026-10-06 21:44:28 | account\models.py, v4_upgrade\auth\workspace.py | app.py:5948(api_v4_api_keys_generate); account\workspace_keys.py:80(create_workspace_key) | account\workspace_keys.py(10); account\workspace_keys.py(... | e382160 | 2026-09-01 | firs... | 生产核心表，437行数据，最新记录2026-10-06 21:44:28，有活跃INSERT写入逻辑 |
| web_mentions | 90 | neutral | database.py, database_migrations.py | database.py:808(insert_web_mention); tests\test_canonical_data_t4.py:317(test_sync_notes_and_web) | canonical_data.py(18); canonical_data.py(18); canonical_d... | 550d644 | 2026-09-06 | CREA... | 生产核心表，90行数据，最新记录neutral，有活跃INSERT写入逻辑 |
| web_runs | 33 | 2026-09-07 15:42:16 | database.py, database_migrations.py | database.py:824(log_web_run); v4_upgrade\adapters\persist.py:226(persist_result) | database_migrations.py(3); database_migrations.py(3); dat... | b69b68f | 2026-08-30 | firs... | 生产核心表，33行数据，最新记录2026-09-07 15:42:16，有活跃INSERT写入逻辑 |
| web_sources | 1 | 2026-09-07 14:55:10 | database.py, database_migrations.py | database.py:819(log_web_source); v4_upgrade\adapters\persist.py:234(persist_result) | database_migrations.py(4); database_migrations.py(4); dat... | b69b68f | 2026-08-30 | firs... | 生产核心表，1行数据，最新记录2026-09-07 14:55:10，有活跃INSERT写入逻辑 |
| x_posts | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(2); audit\convergen... | b69b68f | 2026-08-30 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| x_users | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(2); audit\convergen... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| youtube_channels | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| youtube_comments | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| youtube_videos | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| zbc_canonical_data | 4 | negative | evidence_chain.py | evidence_chain.py:656(create_canonical) | evidence_chain.py(17); evidence_chain.py(17); evidence_ch... | 4501ff6 | 2026-09-06 | firs... | 生产核心表，4行数据，最新记录negative，有活跃INSERT写入逻辑 |
| zbc_evidence | 6 | 2026-09-06 14:51:44 | evidence_chain.py | evidence_chain.py:513(None) | evidence_chain.py(18); evidence_chain.py(18); evidence_ch... | 4501ff6 | 2026-09-06 | firs... | 生产核心表，6行数据，最新记录2026-09-06 14:51:44，有活跃INSERT写入逻辑 |
| zbc_lifecycle_tracking | 8 | 2026-09-06 14:40:18 | evidence_chain.py | evidence_chain.py:825(record_stage) | evidence_chain.py(8); evidence_chain.py(8); evidence_chai... | 4501ff6 | 2026-09-06 | firs... | 生产核心表，8行数据，最新记录2026-09-06 14:40:18，有活跃INSERT写入逻辑 |
| zhihu_answers | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(2); audit\convergen... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| zhihu_articles | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(2); audit\convergen... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| zhihu_comments | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(2); audit\convergen... | 7ddefdc | 2026-09-05 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| zhihu_questions | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(2); audit\convergen... | 32434a3 | 2026-09-07 | firs... | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |

### 2.2 MIGRATE (7 张)

| 表名 | 行数 | 最新记录 | CREATE来源 | INSERT来源 | 核心引用Top3 | Git引入 | 分类理由 |
|------|------|---------|-----------|-----------|-------------|---------|----------|
| brand_propagation_entities | 0 | - | brand_propagation.py | brand_propagation.py:224(create_entity) | brand_propagation.py(3); brand_propagation.py(3); brand_p... | 559e4d7 | 2026-09-06 | firs... | AGENTS.md 9.1/9.3规划的传播主体/三类事件表，brand_propagation.py有CREATE但无INSERT，P1能力待演进 |
| brand_propagation_events | 0 | - | brand_propagation.py | brand_propagation.py:292(create_event) | brand_propagation.py(8); brand_propagation.py(8); brand_p... | 559e4d7 | 2026-09-06 | firs... | AGENTS.md 9.1/9.3规划的传播主体/三类事件表，brand_propagation.py有CREATE但无INSERT，P1能力待演进 |
| collection_runs | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(4); audit\convergen... | 32434a3 | 2026-09-07 | firs... | 与collection_logs职责重叠，仅migration CREATE无INSERT无SELECT，collection_logs已在databas... |
| content_analysis | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(4); audit\convergen... | 32434a3 | 2026-09-07 | firs... | 与content_evaluation功能重叠，仅migration CREATE无INSERT无SELECT，content_generation.py... |
| creators | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | audit\convergence\_generate_report.py(3); audit\convergen... | af57d8a | 2026-09-03 | firs... | KOS创作者主体，仅migration CREATE无INSERT，kos_profiles已覆盖主体画像能力，需确认合并或补实现 |
| evaluation_records | 0 | - | evaluation_recorder.py | evaluation_recorder.py:230(None); evaluation_recorder.py:250(record_evaluation_raw) | evaluation_recorder.py(10); evaluation_recorder.py(10); e... | 4501ff6 | 2026-09-06 | firs... | evaluation_recorder/runner有完整逻辑但0行，与content_evaluation并存需统一口径 |
| professional_metrics | 0 | - | kos_professional.py | kos_professional.py:168(import_metrics) | kos_professional.py(3); kos_professional.py(3); kos_profe... | e9ef5ad | 2026-09-06 | CREA... | kos_professional.py有CREATE但无INSERT，专业账号指标未接入，需补实现或合并入kos_profiles |

### 2.3 DEPRECATE (3 张)

| 表名 | 行数 | 最新记录 | CREATE来源 | INSERT来源 | 核心引用Top3 | Git引入 | 分类理由 |
|------|------|---------|-----------|-----------|-------------|---------|----------|
| xhs_note_comments | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 早期小红书采集schema，已被notes/note_comments替代，无INSERT无生产SELECT，仅platform_naming.py别名注册残留 |
| xhs_notes | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | tests\test_platform_data_dict_v1.py(4); tests\test_platfo... | 32434a3 | 2026-09-07 | firs... | 早期小红书采集schema，已被notes/note_comments替代，无INSERT无生产SELECT，仅platform_naming.py别名注册残留 |
| xhs_users | 0 | - | migrations\migrate_platform_data_dict_v1.py | - | platform_adapters\platform_naming.py(2); platform_adapter... | 32434a3 | 2026-09-07 | firs... | 早期小红书采集schema，已被notes/note_comments替代，无INSERT无生产SELECT，仅platform_naming.py别名注册残留 |

## 3. 五组疑似重复表深挖与合并建议

### 3.1 collection_runs → collection_logs

**结论**: collection_runs 合并入 collection_logs

**分析**:
- **collection_runs**: 0行，仅 `migrations/migrate_platform_data_dict_v1.py:655` CREATE TABLE，无INSERT无SELECT，核心引用仅6个文件(多为审计脚本)
- **collection_logs**: 502行，`database.py:51` CREATE + `database.py:797` INSERT(func=log_collection) + `xhs_cookie_bridge.py:644` INSERT(func=_write_collection_log)，36个核心文件引用，采集主链路活跃写入
- **schema对比**: collection_runs设计更细(collection_run_id/platform/collector_version/task_id/duration_ms等18列)，collection_logs较简(keyword/notes_count/status/error_msg/started_at/finished_at)，但collection_logs已承载生产流量

**建议**: 短期：collection_runs标记MIGRATE，保留schema作为未来增强目标；中期：将collection_logs字段扩展对齐collection_runs设计(加platform/collector_version/duration_ms)，然后废弃collection_runs；**不建议直接删除**，因schema设计更完善可作为演进目标

**影响评估**: 低风险：collection_runs无数据无写入，合并不影响生产；需更新data_center_api.py注册表引用

### 3.2 content_analysis → content_evaluation

**结论**: content_analysis 合并入 content_evaluation

**分析**:
- **content_analysis**: 0行，仅 `migrations/migrate_platform_data_dict_v1.py:707` CREATE，无INSERT无SELECT，核心引用仅6个文件(全为审计/迁移脚本)
- **content_evaluation**: 34行，`content_generation.py:186` CREATE + `content_generation.py:442` INSERT(func=record_evaluation) + `content_generation.py:606` SELECT(func=get_evidence)，活跃生产链路
- **schema对比**: content_analysis设计更全面(analysis_id/platform/content_id/sentiment/emotion/risk_level/topic/intent/brand_relevance/event_relevance/ai_model/prompt_version/confidence/analyzed_at共17列)，content_evaluation较简但已在用

**建议**: content_analysis标记MIGRATE；将content_evaluation schema扩展对齐content_analysis(加platform/sentiment/risk/topic等字段)，数据迁移后废弃content_analysis；**当前content_analysis完全无生产流量可安全清理引用**

**影响评估**: 低风险：0行0写入；需清理migrate_platform_data_dict_v1.py中CREATE语句和data_center_api.py注册

### 3.3 token_stat → ai_call_logs

**结论**: 保留两者但明确职责边界，token_stat为日聚合缓存

**分析**:
- **token_stat**: 0行，`ark_llm.py:54/73` CREATE + `ark_llm.py:74` INSERT OR REPLACE(func=save_daily_token)，schema极简(day TEXT PK, used INTEGER)，仅按天聚合token用量
- **ai_call_logs**: 1128行，`ai_call_logger.py:57` CREATE + `ai_call_logger.py:253` INSERT，详细记录每次AI调用(provider/model/tokens_in/tokens_out/latency/status等)，11个核心文件引用
- **关系**: token_stat是ai_call_logs的按天聚合视图(简化版)，两者非严格重复而是**明细+聚合**关系；但token_stat当前0行说明聚合功能未实际运行

**建议**: **不合并**，明确职责：ai_call_logs=明细审计(必须保留)，token_stat=日用量缓存(可选优化)；若token_stat持续0行且无消费方，可降级为MIGRATE评估是否用ai_call_logs的SQL聚合替代；**当前保留KEEP因ark_llm.py有活跃INSERT逻辑**

**影响评估**: 无风险：两者职责不同；建议在ark_llm.py中补充token_stat的消费方(如API用量查询)

### 3.4 platform_*通用表 vs adapter专用表

**结论**: 保留Canonical层通用表，明确为汇聚层而非采集层

**分析**:
- **4张通用表**: 全部0行，全部仅 `migrations/migrate_platform_data_dict_v1.py` CREATE，无INSERT(NORMALIZED_TABLES_SQL定义)，platform_contents有SELECT引用(platform_naming.py)
- **32张adapter专用表**: 全部0行，全部仅migration CREATE，无INSERT，分布在11个平台前缀下
- **架构关系**: AGENTS.md第8节定义 `BasePlatformAdapter → XiaohongshuAdapter/...`，平台层负责原始采集，上层统一负责标准化/去重/主体过滤。platform_*通用表是**标准化汇聚层**，各平台专用表是**原始采集层**，两者是分层关系而非重复

**建议**: **全部保留KEEP**(用户决策)：platform_*=Canonical汇聚层预留，各平台专用表=Adapter采集层预留；当前均为schema预留状态，待对应平台adapter实现后从专用表汇聚到通用表；**建议在platform_naming.py中明确两层映射关系文档**

**影响评估**: 无风险：均为预留schema；实现新平台时需同时考虑原始表写入和通用表汇聚

### 3.5 collector_quality_log vs collection_quality_log

**结论**: 命名极易混淆但实际为不同用途，需重命名或合并

**分析**:
- **collector_quality_log**: 7行，`database.py:150` CREATE + `database.py:1113` INSERT(func=save_collector_quality) + `database_migrations.py:287` 迁移 + `scripts/init_db.py:292`，18个核心文件引用，**活跃生产表**
- **collection_quality_log**: 0行，仅 `database_migrations.py:471` CREATE(migration_10_to_11)，无INSERT无SELECT，6个核心文件引用(全为迁移/审计)
- **命名差异**: collector(采集器) vs collection(采集行为)，前者是采集器进程质量监控，后者是采集任务质量门控；但命名相似度>90%，极易混淆

**建议**: **短期**: collection_quality_log标记KEEP(预留扩展，v11迁移创建)，collector_quality_log保持KEEP(活跃)；**中期**: 统一命名规范，建议将collection_quality_log重命名为`collection_quality_gate_log`(明确质量门控)，collector_quality_log重命名为`collector_process_quality_log`(明确进程质量)；**若collection_quality_log长期0行无写入，降级为MIGRATE评估**

**影响评估**: 低风险：collector_quality_log有7行数据需保护；重命名需同步更新所有引用

## 4. 无Adapter实现的平台表决策 (15张)

> V1将这15张标为MIGRATE。**V2用户决策：全部平台预留表统一KEEP(预留扩展)**，在系统设置中按需开启平台采集。

| 平台 | 表数 | 表名 | CREATE来源 | 状态 | 决策 |
|------|------|------|-----------|------|------|
| B站 | 3 | bilibili_videos | migrations\migrate_platform_data_dict_v1.py | 0行/无INSERT/无adapter | KEEP(预留扩展) |
|  |  | bilibili_comments | migrations\migrate_platform_data_dict_v1.py | 0行/无INSERT/无adapter | KEEP(预留扩展) |
|  |  | bilibili_users | migrations\migrate_platform_data_dict_v1.py | 0行/无INSERT/无adapter | KEEP(预留扩展) |
| 抖音 | 3 | douyin_videos | migrations\migrate_platform_data_dict_v1.py | 0行/无INSERT/无adapter | KEEP(预留扩展) |
|  |  | douyin_comments | migrations\migrate_platform_data_dict_v1.py | 0行/无INSERT/无adapter | KEEP(预留扩展) |
|  |  | douyin_users | migrations\migrate_platform_data_dict_v1.py | 0行/无INSERT/无adapter | KEEP(预留扩展) |
| Instagram | 3 | instagram_media | migrations\migrate_platform_data_dict_v1.py | 0行/无INSERT/无adapter | KEEP(预留扩展) |
|  |  | instagram_comments | migrations\migrate_platform_data_dict_v1.py | 0行/无INSERT/无adapter | KEEP(预留扩展) |
|  |  | instagram_users | migrations\migrate_platform_data_dict_v1.py | 0行/无INSERT/无adapter | KEEP(预留扩展) |
| X(Twitter) | 2 | x_posts | migrations\migrate_platform_data_dict_v1.py | 0行/无INSERT/无adapter | KEEP(预留扩展) |
|  |  | x_users | migrations\migrate_platform_data_dict_v1.py | 0行/无INSERT/无adapter | KEEP(预留扩展) |
| 知乎 | 4 | zhihu_questions | migrations\migrate_platform_data_dict_v1.py | 0行/无INSERT/无adapter | KEEP(预留扩展) |
|  |  | zhihu_answers | migrations\migrate_platform_data_dict_v1.py | 0行/无INSERT/无adapter | KEEP(预留扩展) |
|  |  | zhihu_articles | migrations\migrate_platform_data_dict_v1.py | 0行/无INSERT/无adapter | KEEP(预留扩展) |
|  |  | zhihu_comments | migrations\migrate_platform_data_dict_v1.py | 0行/无INSERT/无adapter | KEEP(预留扩展) |

**合计: 15张表，5个平台**

### 决策依据

1. **AGENTS.md第8节**明确多平台Adapter为Core架构方向：`BasePlatformAdapter → XiaohongshuAdapter/WeiboAdapter/BilibiliAdapter/FutureAdapter`
2. **schema已完整定义**：每张表均有完整的平台原生字段(如bilibili_videos有aid/bvid/title/pubdate/view/danmaku等20+列)，非空壳
3. **platform_naming.py已注册别名**：所有平台均在`get_platform_aliases()`中注册了content/comment/user表名映射
4. **用户明确决策**：其他平台放设置里开启，不删除schema

### 已实现Adapter的平台 (6个，对照参考)

| 平台 | Adapter文件 | 表数 | 状态 |
|------|-----------|------|------|
| Reddit | platform_adapters/reddit.py | 3 | schema预留，adapter代码存在 |
| TikTok | platform_adapters/tiktok.py | 3 | schema预留，adapter代码存在 |
| YouTube | platform_adapters/youtube.py | 3 | schema预留，adapter代码存在 |
| LinkedIn | platform_adapters/linkedin.py | 2 | schema预留，adapter代码存在 |
| GitHub | platform_adapters/github.py | 4 | schema预留，adapter代码存在 |
| Channels | platform_adapters/channels.py | 2 | schema预留，adapter代码存在 |
| **合计** | | **17** | |

## 5. xhs_* 三张遗留表确认 DEPRECATE

| 表名 | 行数 | CREATE来源 | 生产引用 | INSERT | SELECT | 替代表 |
|------|------|-----------|---------|--------|--------|--------|
| xhs_notes | 0 | migrations\migrate_platform_data_dict_v1.py | 8个核心文件 | 否 | 否 | notes |
| xhs_note_comments | 0 | migrations\migrate_platform_data_dict_v1.py | 8个核心文件 | 否 | 否 | note_comments |
| xhs_users | 0 | migrations\migrate_platform_data_dict_v1.py | 8个核心文件 | 否 | 否 | notes(内嵌用户字段) |

### 确认依据

1. **schema不兼容**: `xhs_notes` 无 `id` 主键(用note_id TEXT PRIMARY KEY)，列名风格不同(liked_count vs likes, collected_count vs collects, time INTEGER vs publish_datetime)
2. **无生产写入**: 三张表均无INSERT语句，仅在 `migrations/migrate_platform_data_dict_v1.py` 中CREATE
3. **无生产查询**: 仅 `platform_adapters/platform_naming.py:391` 作为别名注册(`get_platform_aliases`返回xhs_notes等)，以及 `data_center_api.py:22` 注册表列表
4. **已被完全替代**: `notes`表(1020行)承载小红书笔记采集，`note_comments`表(141行)承载评论，用户信息内嵌于notes表的user_id/nickname/avatar字段
5. **测试残留**: `tests/test_platform_data_dict_v1.py` 有4处引用验证xhs_notes schema字段命名合规性，属于迁移验证测试非生产依赖

### 处理建议

- **当前**: 保持DEPRECATE，保留schema和空表，不执行删除
- **中期**: 从 `platform_naming.py` 的xiaohongshu别名中移除xhs_*映射，改为指向notes/note_comments
- **长期**: 确认无历史数据迁移需求后，可在迁移脚本中DROP TABLE(需用户明确授权)

## 6. 空表分类：预留扩展 vs 真正无用

空表总数: **65** 张

### 6.1 功能就绪待数据 (有活跃INSERT逻辑) — 15 张

| 表名 | INSERT来源 | 产品域 | 说明 |
|------|-----------|--------|------|
| alert_records | alert_engine.py:230(_record_alert) | - | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| brand_knowledge | brand_knowledge_base.py:113(add_knowledge) | - | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| case_deep_analysis | case_deep_analysis.py:131(add_case) | - | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| event_graph_events | event_graph.py:252(save_to_db) | - | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| historical_import_log | historical_data_importer.py:198(log_import) | - | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| notification_config | wechat_notifier.py:1127(add_channel) | - | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| podcast_ai_runs | podcast_store.py:213(record_ai_run) | - | podcast_store.py有CREATE但需确认INSERT链路，播客AI运行功能状态待验证，有INSERT逻辑属预留扩展 |
| podcast_entities | podcast_store.py:112(upsert_entity) | - | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| professional_accounts | kos_professional.py:99(enable) | - | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| runtime_guardian_dlq | evidence_store.py:341(None); runtime_guardian.py:446(enqueue) | - | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| swire_notes | swire_group.py:167(_upsert_brand_notes) | - | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| token_stat | ark_llm.py:74(save_daily_token) | - | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| user_nav_config | account\nav_config.py:82(save_nav_config) | - | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| v4_product_protection | account\product_protection.py:104(set_protection_config) | - | 空表但有活跃INSERT逻辑，功能就绪待数据 |
| v4_verification_codes | account\verification.py:140(None) | - | 空表但有活跃INSERT逻辑，功能就绪待数据 |

### 6.2 预留扩展 (schema已建，待功能实现/平台开启) — 40 张

| 表名 | CREATE来源 | 预留类型 | 说明 |
|------|-----------|---------|------|
| bilibili_comments | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| bilibili_users | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| bilibili_videos | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| brands | migrations\migrate_platform_data_dict_v1.py | 多品牌架构核心预留 | Z-Brand多品牌架构核心表，29个核心文件引用，schema已建待品牌数据写入 |
| channels_comments | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| channels_videos | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| collection_quality_log | database_migrations.py | 采集质量门预留 | 采集质量门日志表，database_migrations.py v11迁移创建，待质量门触发写入 |
| douyin_comments | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| douyin_users | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| douyin_videos | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| event_graph_relations | event_graph.py | 功能预留 | 有代码引用，业务用途明确 |
| github_issues | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| github_pull_requests | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| github_releases | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| github_repositories | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| instagram_comments | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| instagram_media | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| instagram_users | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| linkedin_posts | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| linkedin_users | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| platform_accounts | migrations\migrate_platform_data_dict_v1.py | Canonical汇聚层预留 | 跨平台Canonical统一层预留表，schema已建，待数据汇聚写入 |
| platform_comments | migrations\migrate_platform_data_dict_v1.py | Canonical汇聚层预留 | 跨平台Canonical统一层预留表，schema已建，待数据汇聚写入 |
| platform_contents | migrations\migrate_platform_data_dict_v1.py | Canonical汇聚层预留 | 跨平台Canonical统一层预留表，schema已建，待数据汇聚写入 |
| platform_evidence | migrations\migrate_platform_data_dict_v1.py | Canonical汇聚层预留 | 跨平台Canonical统一层预留表，schema已建，待数据汇聚写入 |
| reddit_comments | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| reddit_posts | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| reddit_subreddits | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| tiktok_comments | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| tiktok_users | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| tiktok_videos | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| v4_login_approvals | account\models.py | 功能预留 | 有代码引用，业务用途明确 |
| x_posts | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| x_users | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| youtube_channels | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| youtube_comments | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| youtube_videos | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| zhihu_answers | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| zhihu_articles | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| zhihu_comments | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |
| zhihu_questions | migrations\migrate_platform_data_dict_v1.py | 平台Adapter预留 | 多平台Adapter预留扩展表，schema已建，adapter实现后写入(用户决策：设置中开启) |

### 6.3 待决策/需演进 (MIGRATE) — 7 张

| 表名 | 问题 | 建议 |
|------|------|------|
| brand_propagation_entities | AGENTS.md 9.1/9.3规划的传播主体/三类事件表，brand_propagation.py有CREATE但无INSERT，P1能力待演进 | 见第3节重复表分析或第4节平台表决策 |
| brand_propagation_events | AGENTS.md 9.1/9.3规划的传播主体/三类事件表，brand_propagation.py有CREATE但无INSERT，P1能力待演进 | 见第3节重复表分析或第4节平台表决策 |
| collection_runs | 与collection_logs职责重叠，仅migration CREATE无INSERT无SELECT，collection_logs已在database.py/xhs_cookie_bridge.py活跃写入(502行) | 见第3节重复表分析或第4节平台表决策 |
| content_analysis | 与content_evaluation功能重叠，仅migration CREATE无INSERT无SELECT，content_generation.py已用content_evaluation | 见第3节重复表分析或第4节平台表决策 |
| creators | KOS创作者主体，仅migration CREATE无INSERT，kos_profiles已覆盖主体画像能力，需确认合并或补实现 | 见第3节重复表分析或第4节平台表决策 |
| evaluation_records | evaluation_recorder/runner有完整逻辑但0行，与content_evaluation并存需统一口径 | 见第3节重复表分析或第4节平台表决策 |
| professional_metrics | kos_professional.py有CREATE但无INSERT，专业账号指标未接入，需补实现或合并入kos_profiles | 见第3节重复表分析或第4节平台表决策 |

## 7. GitHub 引入历史摘要

### 7.1 总体时间线

| 时间段 | 引入表数 | 关键commit | 说明 |
|--------|---------|-----------|------|
| 2026-08 | 19 | `b69b68f`(08-30) | Z-Brand Core/CTH-POMS初始入库，引入brands/x_posts/schedule_decisions等基础表 |
| 2026-09-01~05 | ~30 | `2aecc71`(09-02), `5b10180`(09-02) | DB schema registry、evidence exporter、notes/events等核心表CREATE定义 |
| 2026-09-06 | ~50 | `e9ef5ad`(09-06), `559e4d7`(09-06) | Repository Registry+Runtime Guardian+双域隔离，引入collection_logs/token_stat/event_graph_*/podcast_*/note_review_history等 |
| 2026-09-07 | ~29 | `32434a3`(09-07), `9695f5c`(09-07) | v5.9.9巡检+全平台数据字典V1迁移，引入32张平台预留表+4张canonical表+collection_runs/content_analysis/creators |

### 7.2 关键迁移脚本

| 迁移文件 | 创建表数 | 表类型 | 执行状态 |
|---------|---------|--------|---------|
| `migrations/migrate_platform_data_dict_v1.py` | ~46 | 12平台Raw层(35)+Normalized层(3)+Evidence层(2)+Business层(3)+索引+events扩展 | 已执行(表已存在) |
| `database_migrations.py` (内嵌) | ~20 | collector_quality_log/collection_quality_log/daily_digest/event_insights/event_mentions/feedback_keywords/historical_import_log/note_comments/note_review_history/rule_version_registry/schema_version/web_mentions/web_runs/web_sources等 | 已执行 |
| `database.py` (启动时CREATE) | ~15 | collection_logs/collector_quality_log/daily_reports/events/metric_snapshots/note_comments/notes等核心表 | 启动时自动执行 |
| `migrations/009_global_bil_staging.sql` | - | B站staging全局表 | SQL迁移文件 |
| `migrations/010_notes_subject_content_type.sql` | - | notes表subject/content_type字段扩展 | SQL迁移文件 |
| `migrations/create_intelligence_assets_table.py` | 1 | intelligence_assets | 已执行(711行) |
| `migrations/init_platform_registry.py` | 1 | platform_registry(含12平台注册数据) | 已执行(12行) |

### 7.3 引入方式分布

| 引入方式 | 表数 | 说明 |
|---------|------|------|
| CREATE TABLE 直接检索 | 32 | git log -S 'CREATE TABLE table_name' 命中 |
| 首次 -S 提及 | 96 | 通过git log -S table_name首次出现定位(多为migration批量引入) |

## 8. Top 5 关键发现

### 发现1: 表数量差异已澄清 — 129 = 128业务 + 1系统表
- V1报告存疑的129 vs 128差异已确认：`sqlite_sequence`是SQLite内部系统表(AUTOINCREMENT序列号)，非业务表
- 实际业务表128张，其中63张非空、65张空；含系统表共129张(64非空+65空)，与用户口径完全一致
- `sqlite_sequence`当前50行，记录了50张使用AUTOINCREMENT的表的序列号，无需分类管理

### 发现2: 单迁移文件创建46张表，全平台数据字典V1是最大schema来源
- `migrations/migrate_platform_data_dict_v1.py` 一次性创建了约46张表，包括12个平台的Raw层表(35张)、Canonical Normalized层(3张)、Evidence层(2张)、Business层(3张)
- 这解释了为什么大量平台表(32张)同时出现且均无INSERT：它们是统一规划的schema预留，非逐个实现的功能表
- 该迁移使用`CREATE TABLE IF NOT EXISTS`，安全无破坏，且包含完整索引定义和events表字段扩展

### 发现3: 5组重复表中2组可安全合并(collection_runs/content_analysis)，3组需保留但明确边界
- **collection_runs/content_analysis**: 均为0行0写入0生产查询，仅migration CREATE，可安全标记MIGRATE并规划合并
- **token_stat/ai_call_logs**: 非重复而是明细+聚合关系，ai_call_logs(1128行)是明细必须保留，token_stat是日聚合缓存需补消费方
- **platform_*通用 vs adapter专用**: 分层架构(Canonical汇聚层 vs Raw采集层)，非重复，用户决策全部KEEP
- **collector_quality_log vs collection_quality_log**: 命名混淆但用途不同(进程质量 vs 任务质量门)，前者7行活跃，后者0行预留，建议中期重命名

### 发现4: xhs_*三张遗留表确认完全DEPRECATE，无任何生产依赖
- 三张表均0行、无INSERT、无生产SELECT，仅在platform_naming.py作为别名注册和data_center_api.py注册表列表
- schema与notes/note_comments不兼容(主键类型/列名风格差异)，无法直接迁移数据
- 已被notes(1020行)/note_comments(141行)完全替代，用户信息内嵌于notes表
- 唯一非审计引用是tests/test_platform_data_dict_v1.py的schema合规性验证，属于迁移测试

### 发现5: 空表65张中仅7张需决策(MIGRATE)，其余55张均有明确保留理由
- 功能就绪待数据: **15张**(有活跃INSERT逻辑，如alert_records/brand_knowledge/case_deep_analysis/event_graph_events/podcast_ai_runs/token_stat等)
- 预留扩展: **40张**(32张平台Adapter预留 + 4张Canonical层 + brands + collection_quality_log + event_graph_relations + v4_login_approvals)
- 待决策MIGRATE: **7张**(collection_runs/content_analysis/evaluation_records/creators/brand_propagation_entities/brand_propagation_events/professional_metrics)
- DEPRECATE: **3张**(xhs_*系列)
- 合计: 15+40+7+3 = 65
- **无任何表符合DELETE-CANDIDATE严格标准**(无引用+无数据+无业务用途)

## 9. V1 → V2 差异对比

| 维度 | V1 | V2 | 变化 |
|------|----|----|------|
| 表总数 | 128(存疑) | 128业务+1系统=129 | 澄清差异来源 |
| KEEP | 98 | 118 | +20 (平台表从MIGRATE改为KEEP) |
| MIGRATE | 27 | 7 | -20 (15张无adapter平台表→KEEP，token_stat/3张platform_*/event_graph_relations/podcast_ai_runs→KEEP，evaluation_records从KEEP→MIGRATE) |
| DEPRECATE | 3 | 3 | 0 (xhs_*三张保持) |
| DELETE-CANDIDATE | 0 | 0 | 0 (仍未发现符合标准的表) |
| UNKNOWN | 0 | 0 | 0 (全部128表均可确定用途) |
| 行数数据 | 静态快照 | 实时查询(63非空) | 数据有增长(如schedule_decisions 14408→15151) |
| 代码引用 | 文件级 | 文件+行号+函数+类型 | 精度大幅提升 |
| Git历史 | 无 | 全表引入commit+时间 | 新增维度 |
| 重复表分析 | 列出5组疑似 | 5组逐一深挖+合并建议+影响评估 | 从发现到可执行 |
| 空表分类 | 有/无INSERT | 功能就绪/预留扩展/待决策 三级 | 更精细 |

## 10. 下一步建议

### P0 (立即执行，低风险)
1. **确认分类基线**: 将本V2报告作为数据库表生命周期管理的基线文档
2. **xhs_*别名清理**: 从platform_naming.py的xiaohongshu别名映射中移除xhs_*，改为notes/note_comments(需测试验证)
3. **token_stat消费方补充**: 在ark_llm.py或AI用量API中补充token_stat的查询消费，否则0行无意义

### P1 (短期规划，需方案设计)
4. **collection_runs合并方案**: 设计collection_logs字段扩展方案(加platform/collector_version/duration_ms)，迁移后废弃collection_runs
5. **content_analysis合并方案**: 设计content_evaluation schema扩展(加sentiment/risk/topic字段)，迁移后废弃content_analysis
6. **quality_log命名规范**: 制定collector_quality_log/collection_quality_log重命名方案，消除命名混淆

### P2 (中期演进，依赖功能实现)
7. **平台Adapter实现优先级**: 按业务需求排序5个未实现平台(B站/抖音/Instagram/X/知乎)的adapter开发优先级
8. **brand_propagation演进**: 按AGENTS.md 9.1/9.3推进传播主体和三类事件表的INSERT逻辑实现
9. **Canonical汇聚层实现**: 实现platform_contents等通用表的数据汇聚逻辑，从各平台专用表标准化写入
10. **professional_metrics接入**: 补全kos_professional.py的专业账号指标写入逻辑

### 硬约束重申
- **DELETE-CANDIDATE仅记录，不执行删除**：本次审计未发现符合删除标准的表
- **DEPRECATE表保留历史数据**：xhs_*三张表保留schema，不DROP
- **所有修改需向后兼容迁移**：新增字段用ALTER TABLE ADD COLUMN，不破坏历史数据
- **生产数据库最高保护级别**：任何表结构变更需用户明确授权
