# 数据库 Schema 权威清单（DATABASE-SCHEMA-REGISTRY，P1-5 单一权威源）

> 由 schema_registry.py 只读反射实际库 + 全仓 CREATE 声明来源生成；请勿手改，用生成器重跑。本文件不改变任何建表逻辑与生产数据。

- 反射对象：data/monitor.db (mode=ro)
- 实际表数：**52**；有 CREATE 声明：51；登记遗留：1；无主未登记：**0** 
- 状态含义：DECLARED=全仓可定位建表声明；LEGACY_NO_DECL=历史遗留保留不删；MIGRATION_ISOLATED=迁移隔离预留；MISSING_SOURCE=必须处理的无主表。

| # | 表名 | 状态 | 列数 | 行数 | 索引数 | CREATE 声明来源（节选） | 备注 |
|---|------|------|------|------|--------|--------------------------|------|
| 1 | `ai_filter_log` | DECLARED | 9 | 827 | 2 | database.py, database_migrations.py | id, note_id, filter_stage, filter_result, filter_reason, noi |
| 2 | `app_evidence_records` | DECLARED | 16 | 0 | 3 | app_evidence.py | id, source, capture_mode, captured_at, topic, metric_name, m |
| 3 | `auth_recovery_tasks` | DECLARED | 15 | 16 | 2 | auth_recovery_center.py | id, platform, issue_type, status, title, description, qr_cod |
| 4 | `brand_industry_monitor` | DECLARED | 12 | 198 | 1 | scripts/init_db.py, web_topic_discovery.py | id, brand_name, brand_name_cn, industry, floor, shop_number, |
| 5 | `brand_knowledge` | DECLARED | 11 | 103 | 4 | brand_knowledge_base.py | id, category, title, content, source, url, tags, content_has |
| 6 | `case_deep_analysis` | DECLARED | 22 | 20 | 5 | case_deep_analysis.py | id, case_id, case_title, brand, agency, industry, year, case |
| 7 | `collection_counters` | DECLARED | 8 | 1 | 1 | scripts/init_db.py | id, date, daily_count, manual_count, auto_count, last_collec |
| 8 | `collection_logs` | DECLARED | 7 | 499 | 0 | database.py | id, keyword, notes_count, status, error_msg, started_at, fin |
| 9 | `collector_quality_log` | DECLARED | 9 | 7 | 1 | database.py, database_migrations.py, scripts/init_db.py | id, note_id, status, score, detail_status, comments_collecte |
| 10 | `comments` | DECLARED | 14 | 2 | 1 | scripts/init_db.py | id, note_id, comment_id, content, author_id, author_nickname |
| 11 | `daily_digest` | DECLARED | 15 | 7 | 2 | database.py, database_migrations.py | id, digest_date, total_found, effective_count, positive_coun |
| 12 | `daily_reports` | DECLARED | 29 | 33 | 1 | database.py, scripts/init_db.py | id, report_type, report_date, period_start, period_end, tota |
| 13 | `event_graph_events` | DECLARED | 12 | 16 | 4 | event_graph.py | id, event_id, event_type, title, event_time, source, descrip |
| 14 | `event_graph_relations` | DECLARED | 7 | 1 | 4 | event_graph.py | id, source_event_id, target_event_id, relation_type, evidenc |
| 15 | `event_insights` | DECLARED | 10 | 17 | 1 | database.py, database_migrations.py | id, event_id, ai_summary, risk_assessment, recommended_actio |
| 16 | `event_mentions` | DECLARED | 6 | 562 | 1 | database.py, database_migrations.py | id, event_id, source_type, source_id, match_score, created_a |
| 17 | `events` | DECLARED | 22 | 427 | 2 | database.py, database_migrations.py, scripts/init_db.py | id, event_key, title, summary, fact_status, impact, risk_rea |
| 18 | `feedback_keywords` | DECLARED | 7 | 16 | 1 | database.py, database_migrations.py | keyword, source, score, enabled, first_seen, last_seen, used |
| 19 | `industry_stats` | LEGACY_NO_DECL | 9 | 8 | 1 | — | LEGACY 历史遗留预聚合表（8 行旧数据）；现役 /api/brand-industry/* 实际查 brand_industry_monitor，web_monitor_v570 为旧文件；保留不删，待人工确认后清理 |
| 20 | `note_comments` | DECLARED | 11 | 141 | 2 | database.py, database_migrations.py, scripts/init_db.py | id, comment_id, note_id, content, author_id, author_nickname |
| 21 | `note_review_history` | DECLARED | 11 | 8327 | 0 | database.py, database_migrations.py | id, note_id, old_relevance, new_relevance, old_sentiment, ne |
| 22 | `notes` | DECLARED | 67 | 957 | 12 | database.py, scripts/init_db.py | id, note_id, title, content, url, cover, author_id, author_n |
| 23 | `notification_config` | DECLARED | 7 | 0 | 0 | wechat_notifier.py | id, channel_name, channel_type, config_json, enabled, create |
| 24 | `notification_logs` | DECLARED | 12 | 3 | 0 | wechat_notifier.py | id, notification_type, level, title, content, channel, statu |
| 25 | `review_logs` | DECLARED | 9 | 0 | 0 | review_workflow.py | id, ticket_id, note_id, action, operator, comment, old_statu |
| 26 | `review_samples` | DECLARED | 13 | 0 | 1 | review_workflow.py | id, note_id, title, content, original_sentiment, reviewed_se |
| 27 | `review_tickets` | DECLARED | 15 | 0 | 1 | review_workflow.py | id, ticket_id, note_id, review_type, status, priority, reaso |
| 28 | `schedule_decisions` | DECLARED | 22 | 424 | 1 | platform_adapters/scheduling/store.py | id, platform, account_id, task_id, started_at, finished_at,  |
| 29 | `schema_version` | DECLARED | 5 | 7 | 0 | database_migrations.py | id, version, description, applied_at, applied_by |
| 30 | `swire_events` | DECLARED | 12 | 10 | 2 | swire_group.py | id, project_key, brand, event_type, title, summary, source,  |
| 31 | `swire_notes` | DECLARED | 14 | 0 | 2 | swire_group.py | id, project_key, brand, note_id, title, author, likes, comme |
| 32 | `swire_projects` | DECLARED | 13 | 8 | 1 | swire_group.py | project_key, name, city, line, opened, intro, sort, kind, ke |
| 33 | `system_config` | DECLARED | 6 | 10 | 1 | scripts/init_db.py | id, config_key, config_value, description, created_at, updat |
| 34 | `token_stat` | DECLARED | 2 | 1 | 1 | ark_llm.py | day, used |
| 35 | `topic_campaign_notes` | DECLARED | 24 | 120 | 2 | topic_campaign.py | id, campaign_key, topic, note_id, title, content, author, pu |
| 36 | `topic_campaign_snapshots` | DECLARED | 12 | 325 | 1 | topic_campaign.py | id, campaign_key, topic, captured_at, browse_count, discussi |
| 37 | `topic_campaign_topics` | DECLARED | 6 | 7 | 1 | topic_campaign.py | id, campaign_key, topic, normalized_topic, enabled, created_ |
| 38 | `topic_campaigns` | DECLARED | 9 | 1 | 1 | topic_campaign.py | id, campaign_key, name, start_date, end_date, status, interv |
| 39 | `v4_ai_shadow` | DECLARED | 11 | 2 | 1 | v4_upgrade/ai_hub/shadow.py | id, created_at, module, kind, title, rationale, payload, sta |
| 40 | `v4_audit_logs` | DECLARED | 9 | 35 | 2 | v4_upgrade/auth/models.py | id, user_id, username, action, resource, resource_id, detail |
| 41 | `v4_login_attempts` | DECLARED | 5 | 26 | 0 | v4_upgrade/auth/models.py | id, username, ip, success, created_at |
| 42 | `v4_security_questions` | DECLARED | 6 | 2 | 0 | v4_upgrade/auth/models.py | id, question, answer_hash, is_active, created_by, created_at |
| 43 | `v4_sessions` | DECLARED | 7 | 45 | 2 | v4_upgrade/auth/models.py | id, user_id, token, ip, user_agent, expires_at, created_at |
| 44 | `v4_users` | DECLARED | 14 | 1 | 1 | v4_upgrade/auth/models.py | id, username, password_hash, role, display_name, email, stat |
| 45 | `v4_workspace_grants` | DECLARED | 7 | 18 | 1 | v4_upgrade/auth/workspace.py | id, user_id, workspace, key_id, session_token, expires_at, c |
| 46 | `v4_workspace_keys` | DECLARED | 10 | 90 | 1 | v4_upgrade/auth/workspace.py | id, workspace, label, key_prefix, key_hash, created_by, stat |
| 47 | `web_events` | DECLARED | 13 | 20 | 1 | scripts/init_db.py | id, title, description, source, url, published_at, discovere |
| 48 | `web_mentions` | DECLARED | 24 | 79 | 3 | database.py, database_migrations.py | id, source_id, source_platform, source_type, title, content, |
| 49 | `web_runs` | DECLARED | 9 | 28 | 0 | database.py, database_migrations.py | id, adapter, query, started_at, finished_at, fetched, accept |
| 50 | `web_sources` | DECLARED | 9 | 1 | 1 | database.py, database_migrations.py | id, source_key, source_name, adapter, enabled, last_run_at,  |
| 51 | `web_topics` | DECLARED | 11 | 96 | 2 | scripts/init_db.py, web_topic_discovery.py | id, topic, source, sentiment, relevance_score, mention_count |
| 52 | `weekly_events` | DECLARED | 17 | 30 | 1 | scripts/init_db.py | id, week_key, event_title, event_type, urgency, description, |

## 红线时间列核对（publish_datetime ≠ captured_at）
- `notes.publish_datetime`: 存在
- `notes.captured_at`: 存在
