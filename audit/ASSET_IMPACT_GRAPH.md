# ZBC/LUMENIS 全库资产与影响图 (Asset Impact Graph)

> 生成时间: 2026-09-07 00:27:46
> 扫描器版本: 1.0.0
> 项目根目录: D:\Taikoo-monitor-new

## 1. 总览 (Summary)

| 指标 | 数量 |
|------|------|
| Python 源文件 | 969 |
| 函数定义 | 8339 |
| 类定义 | 1015 |
| API 路由 (注册) | 335 |
| 唯一 API Path | 310 |
| HTML 模板 | 55 |
| JS 文件 | 15 |
| 数据库表 | 73 |
| 测试文件 | 227 |
| 测试函数 | 2820 |
| Contract 文件 | 9 |
| Skill 注册文件 | 2 |
| CI Workflow | 1 |
| UI 页面 | 55 |

## 2. 按域分布 (Domain Distribution)

| 域 (Domain) | 产品 | 文件数 | 函数数 | 路由数 |
|-------------|------|--------|--------|--------|
| AI | AI Runtime | 154 | 1771 | 76 |
| CI | CI/CD & Deployment | 7 | 37 | 0 |
| COLLECTOR | Collector & Adapters | 27 | 205 | 0 |
| COOKIE | Cookie & Auth | 32 | 238 | 0 |
| CORE | Shared Core | 473 | 2765 | 68 |
| CTH | CorTech-TaikooHui | 100 | 879 | 20 |
| DCC | Data Canonical Chain | 22 | 309 | 8 |
| KOS | KOS Module | 20 | 333 | 53 |
| MIGRATION | Migration & Upgrade | 10 | 106 | 0 |
| NOTIFICATION | Notification & Alert | 4 | 103 | 4 |
| PODCAST | Podcast Module | 3 | 37 | 9 |
| REPORT | Report & Export | 17 | 168 | 7 |
| SYSTEM | Shared Core / System | 81 | 1175 | 73 |
| UI | UI & Frontend | 7 | 98 | 2 |
| ZBMP | Z-Brand Monitoring Platform | 12 | 115 | 15 |

## 3. 数据库表清单 (Database Tables)

| 表名 | 字段数 | 行数 | 索引数 |
|------|--------|------|--------|
| ai_call_logs | 28 | 83 | 5 |
| ai_filter_log | 9 | 864 | 2 |
| alert_configs | 5 | 13 | 1 |
| alert_records | 11 | 0 | 2 |
| app_evidence_records | 16 | 13 | 3 |
| auth_recovery_tasks | 15 | 0 | 2 |
| brand_knowledge | 11 | 0 | 4 |
| brand_propagation_entities | 9 | 0 | 1 |
| brand_propagation_events | 17 | 0 | 5 |
| canonical_data | 47 | 13 | 8 |
| case_deep_analysis | 22 | 0 | 5 |
| collection_logs | 7 | 477 | 0 |
| collector_quality_log | 9 | 7 | 1 |
| daily_digest | 15 | 9 | 2 |
| daily_reports | 34 | 30 | 1 |
| evaluation_records | 11 | 0 | 4 |
| event_graph_events | 12 | 0 | 4 |
| event_graph_relations | 7 | 0 | 4 |
| event_insights | 10 | 17 | 1 |
| event_mentions | 6 | 562 | 1 |
| events | 22 | 427 | 2 |
| feedback_keywords | 7 | 16 | 1 |
| historical_import_log | 20 | 0 | 3 |
| intelligence_assets | 16 | 711 | 1 |
| kos_executions | 15 | 481 | 2 |
| kos_operations | 6 | 230 | 1 |
| kos_paid_plans | 16 | 92 | 2 |
| kos_profiles | 58 | 1 | 1 |
| kos_rewards | 10 | 46 | 2 |
| metric_snapshots | 14 | 994 | 1 |
| note_comments | 11 | 141 | 2 |
| note_review_history | 11 | 8327 | 0 |
| notes | 69 | 963 | 9 |
| notification_config | 7 | 0 | 0 |
| notification_logs | 12 | 3 | 0 |
| podcast_ai_runs | 10 | 0 | 2 |
| podcast_entities | 21 | 0 | 4 |
| professional_accounts | 14 | 0 | 1 |
| professional_metrics | 14 | 0 | 1 |
| rule_version_registry | 12 | 1 | 3 |
| runtime_guardian_checkpoints | 9 | 1 | 2 |
| runtime_guardian_dlq | 17 | 0 | 3 |
| runtime_guardian_workers | 18 | 9 | 3 |
| schedule_decisions | 22 | 11513 | 1 |
| schema_version | 5 | 2 | 0 |
| skills_registry | 11 | 12 | 1 |
| swire_events | 12 | 10 | 2 |
| swire_notes | 14 | 0 | 2 |
| swire_projects | 13 | 8 | 1 |
| token_stat | 2 | 0 | 1 |
| topic_campaign_notes | 16 | 79 | 2 |
| topic_campaign_snapshots | 12 | 325 | 1 |
| topic_campaign_topics | 6 | 7 | 1 |
| topic_campaigns | 9 | 1 | 1 |
| user_nav_config | 5 | 0 | 1 |
| v4_audit_logs | 9 | 26 | 2 |
| v4_login_approvals | 11 | 0 | 1 |
| v4_login_attempts | 5 | 12 | 0 |
| v4_member_authorizations | 10 | 2 | 2 |
| v4_product_protection | 6 | 0 | 1 |
| v4_security_questions | 6 | 2 | 0 |
| v4_sessions | 7 | 64 | 2 |
| v4_totp_secrets | 6 | 1 | 1 |
| v4_users | 16 | 9 | 1 |
| v4_verification_codes | 15 | 0 | 2 |
| v4_workspace_grants | 7 | 52 | 1 |
| v4_workspace_keys | 13 | 261 | 1 |
| web_mentions | 24 | 89 | 3 |
| web_runs | 9 | 28 | 0 |
| web_sources | 9 | 1 | 1 |
| zbc_canonical_data | 13 | 4 | 5 |
| zbc_evidence | 15 | 6 | 4 |
| zbc_lifecycle_tracking | 15 | 8 | 4 |

## 4. API 路由清单 (按域)

### AI (76 routes)

| Method | Path | Function | File |
|--------|------|----------|------|
| GET | / | command_home | lumenis_frontend.py |
| GET | /<asset_id> | get_asset | intelligence_library_api.py |
| GET | /api/agents/status | agents_status | lumenis_agg_api.py |
| GET | /api/domain/brands | api_domain_brands | lumenis_frontend.py |
| GET | /api/domain/context | api_domain_context | lumenis_frontend.py |
| GET | /api/domain/overview | api_domain_overview | lumenis_frontend.py |
| GET | /api/domain/risk | api_domain_risk | lumenis_frontend.py |
| GET | /api/evaluation/status | evaluation_status | lumenis_agg_api.py |
| GET | /api/intelligence/evidence | api_intelligence_evidence | lumenis_frontend.py |
| GET | /api/intelligence/models | intelligence_models | lumenis_agg_api.py |
| POST | /api/kos/professional/disable | kos_professional_disable | lumenis_agg_api.py |
| POST | /api/kos/professional/enable | kos_professional_enable | lumenis_agg_api.py |
| POST | /api/kos/professional/import | kos_professional_import | lumenis_agg_api.py |
| GET | /api/kos/professional/status | kos_professional_status | lumenis_agg_api.py |
| GET | /api/operations/permissions | operations_permissions | lumenis_agg_api.py |
| GET | /api/production/reports | production_reports | lumenis_agg_api.py |
| GET | /api/research/pipeline | research_pipeline_view | lumenis_agg_api.py |
| POST | /api/research/start | research_start | lumenis_agg_api.py |
| GET | /api/research/status | research_status | lumenis_agg_api.py |
| GET | /api/skills/invocations | skill_invocations_history | lumenis_frontend.py |
| POST | /api/skills/invoke | skill_invoke | lumenis_frontend.py |
| GET | /api/skills/status | skill_status | lumenis_frontend.py |
| POST | /api/skills/sync | skill_sync | lumenis_frontend.py |
| GET | /api/system/repository | system_repository | lumenis_agg_api.py |
| GET | /api/system/runtime | system_runtime | lumenis_agg_api.py |
| GET | /cth/brands | cth_brands | lumenis_frontend.py |
| GET | /cth/events | cth_events | lumenis_frontend.py |
| GET | /cth/evidence | cth_evidence | lumenis_frontend.py |
| GET | /cth/industries | cth_industries | lumenis_frontend.py |
| GET | /cth/kos | cth_kos | lumenis_frontend.py |
| GET | /cth/launch | cth_launch | lumenis_frontend.py |
| GET | /cth/overview | cth_overview | lumenis_frontend.py |
| GET | /cth/realtime | cth_realtime | lumenis_frontend.py |
| GET | /cth/reports | cth_reports | lumenis_frontend.py |
| GET | /cth/risk | cth_risk | lumenis_frontend.py |
| GET | /cth/xiaohongshu | cth_xhs | lumenis_frontend.py |
| GET | /healthz | foundation_healthz | lumenis_frontend.py |
| GET | /intelligence | intelligence_workspace | lumenis_frontend.py |
| GET | /intelligence/agents | agent_center | lumenis_frontend.py |
| GET | /intelligence/evaluation | evaluation_center | lumenis_frontend.py |
| GET | /intelligence/evidence | evidence | lumenis_frontend.py |
| GET | /intelligence/models | models | lumenis_frontend.py |
| GET | /intelligence/skills | skill_hub | lumenis_frontend.py |
| GET | /operations | operations | lumenis_frontend.py |
| GET | /operations/permissions | permissions | lumenis_frontend.py |
| GET | /operations/repository | repository | lumenis_frontend.py |
| GET | /operations/runtime | runtime | lumenis_frontend.py |
| GET | /production | production_overview | lumenis_frontend.py |
| GET | /production/cases | cases | lumenis_frontend.py |
| GET | /production/monitoring | monitoring | lumenis_frontend.py |
| GET | /production/public-opinion | public_opinion | lumenis_frontend.py |
| GET | /production/reports | reports | lumenis_frontend.py |
| GET | /production/risk | risk | lumenis_frontend.py |
| GET | /research | research_workspace | lumenis_frontend.py |
| GET | /research/findings | findings | lumenis_frontend.py |
| GET | /search | search_assets | intelligence_library_api.py |
| GET | /stats | get_stats | intelligence_library_api.py |
| GET | /sub_libraries | list_sub_libraries | intelligence_library_api.py |
| GET | /system/ai | system_ai | lumenis_frontend.py |
| GET | /system/browser | system_browser | lumenis_frontend.py |
| GET | /system/collector | system_collector | lumenis_frontend.py |
| GET | /system/database | system_database | lumenis_frontend.py |
| GET | /system/evaluation | system_evaluation | lumenis_frontend.py |
| GET | /system/runtime | system_runtime | lumenis_frontend.py |
| GET | /system/security | system_security | lumenis_frontend.py |
| GET | /zbmp/brand | zbmp_brand | lumenis_frontend.py |
| GET | /zbmp/competition | zbmp_competition | lumenis_frontend.py |
| GET | /zbmp/content | zbmp_content | lumenis_frontend.py |
| GET | /zbmp/evaluation | zbmp_evaluation | lumenis_frontend.py |
| GET | /zbmp/intelligence | zbmp_intelligence | lumenis_frontend.py |
| GET | /zbmp/kos | zbmp_kos | lumenis_frontend.py |
| GET | /zbmp/launch | zbmp_launch | lumenis_frontend.py |
| GET | /zbmp/overview | zbmp_overview | lumenis_frontend.py |
| GET | /zbmp/podcast | zbmp_podcast | lumenis_frontend.py |
| GET | /zbmp/reports | zbmp_reports | lumenis_frontend.py |
| GET | /zbmp/risk | zbmp_risk | lumenis_frontend.py |

### CORE (68 routes)

| Method | Path | Function | File |
|--------|------|----------|------|
| GET | / | get_notes | app_refactor_blueprint.py |
| GET | / | get_events | app_refactor_blueprint.py |
| GET | / | get_settings | app_refactor_blueprint.py |
| POST | / | update_settings | app_refactor_blueprint.py |
| GET | /<event_id> | get_event_detail | app_refactor_blueprint.py |
| GET | /<note_id> | get_note_detail | app_refactor_blueprint.py |
| POST | /alert/<int:alert_id>/state | alert_transition | ic_routes.py |
| GET,POST | /alert/config | alert_config | ic_routes.py |
| POST | /alert/evaluate | alert_evaluate | ic_routes.py |
| GET | /alert/records | alert_records | ic_routes.py |
| POST | /analyze | analyze | app_refactor_blueprint.py |
| GET | /api/adaptive/can-collect | adaptive_can_collect | architecture_api.py |
| POST | /api/adaptive/report-result | adaptive_report_result | architecture_api.py |
| POST | /api/adaptive/reset | adaptive_reset | architecture_api.py |
| GET | /api/adaptive/status | adaptive_status | architecture_api.py |
| GET | /api/architecture/status | architecture_status | architecture_api.py |
| POST | /api/boundary/approve/<int:confirmation_id> | boundary_approve | architecture_api.py |
| POST | /api/boundary/file-integrity/baseline | boundary_file_integrity_baseline | architecture_api.py |
| GET | /api/boundary/file-integrity/check | boundary_file_integrity_check | architecture_api.py |
| GET | /api/boundary/pending-confirmations | boundary_pending_confirmations | architecture_api.py |
| POST | /api/boundary/reject/<int:confirmation_id> | boundary_reject | architecture_api.py |
| GET | /api/boundary/safety-level/<operation_type> | boundary_safety_level | architecture_api.py |
| GET | /api/boundary/stats | boundary_stats | architecture_api.py |
| GET | /api/feedback/analyze | feedback_analyze | architecture_api.py |
| GET | /api/feedback/history | feedback_history | architecture_api.py |
| GET | /api/feedback/pending | feedback_pending | architecture_api.py |
| POST | /api/feedback/run-cycle | feedback_run_cycle | architecture_api.py |
| GET | /api/feedback/stats | feedback_stats | architecture_api.py |
| GET | /api/feedback/suggestions | feedback_suggestions | architecture_api.py |
| GET | /api/health | health_check | app_refactor_blueprint.py |
| GET | /api/recovery/alerts | recovery_alerts | architecture_api.py |
| GET | /api/recovery/health-check | recovery_health_check | architecture_api.py |
| POST | /api/recovery/run-cycle | recovery_run_cycle | architecture_api.py |
| GET | /api/recovery/stats | recovery_stats | architecture_api.py |
| GET | /api/settings/config | get_config | settings_module.py |
| POST | /api/settings/config | update_config | settings_module.py |
| POST | /api/settings/developer/execute | developer_execute | settings_module.py |
| GET | /api/settings/developer/logs | developer_logs | settings_module.py |
| GET | /api/settings/domain | get_domain_config | settings_module.py |
| POST | /api/settings/domain | update_domain_config | settings_module.py |
| POST | /api/settings/domain/delete | delete_domain_config | settings_module.py |
| GET | /api/settings/system-info | system_info | settings_module.py |
| GET | /brands | zbmp_brands | api_dual_domain.py |
| GET | /browser-discovery | browser_discovery | app_refactor_blueprint.py |
| GET | /daily | get_daily_report | app_refactor_blueprint.py |
| GET | /domains | system_domains | api_dual_domain.py |
| GET | /emv | ic_emv | ic_routes.py |
| GET | /events | cth_events | api_dual_domain.py |
| GET | /export | export_report | app_refactor_blueprint.py |
| GET | /kos-scenario | kos_scenario | ic_routes.py |
| GET | /kos/interest-signal | kos_interest_signal | ic_routes.py |
| POST | /localization/check | localization_check | ic_routes.py |
| GET | /marketing/calendar | marketing_calendar | ic_routes.py |
| GET | /metrics | zbmp_metrics | api_dual_domain.py |
| GET | /overview | zbmp_overview | api_dual_domain.py |
| GET | /overview | cth_overview | api_dual_domain.py |
| GET | /providers | get_providers | app_refactor_blueprint.py |
| GET | /runtime-workers | system_runtime_workers | api_dual_domain.py |
| GET | /search | search_notes | app_refactor_blueprint.py |
| GET | /status | system_status | api_dual_domain.py |
| GET | /status | get_collection_status | app_refactor_blueprint.py |
| POST | /synthetic/scan | synthetic_scan | ic_routes.py |
| GET | /test/domain-context | test_domain_context | tests\test_request_domain_context.py |
| GET | /topics | get_web_topics | app_refactor_blueprint.py |
| POST | /trigger | trigger_collection | app_refactor_blueprint.py |
| POST | /vis/quality-check | vis_quality_check | ic_routes.py |
| GET | /vis/quality-gate | vis_quality_gate | ic_routes.py |
| GET | /xiaohongshu | cth_xiaohongshu | api_dual_domain.py |

### CTH (20 routes)

| Method | Path | Function | File |
|--------|------|----------|------|
| POST | /api/collector-v2/collect | collector_v2_collect | collector_v2_integration.py |
| GET | /api/collector-v2/scheduler/status | collector_v2_scheduler_status | collector_v2_integration.py |
| GET | /api/collector-v2/status | collector_v2_status | collector_v2_integration.py |
| GET | /api/collector/status | collector_status | collector_status_api.py |
| POST | /api/topic-campaign/backfill-detail | topic_backfill_detail | topic_campaign.py |
| POST | /api/topic-campaign/campaign-save | tc_campaign_save | topic_campaign.py |
| POST | /api/topic-campaign/campaign-toggle | tc_campaign_toggle | topic_campaign.py |
| GET | /api/topic-campaign/campaigns | tc_campaign_list | topic_campaign.py |
| GET | /api/topic-campaign/export | topic_export | topic_campaign.py |
| POST | /api/topic-campaign/half-open-probe | topic_half_open_probe | topic_campaign.py |
| GET | /api/topic-campaign/note/<note_id> | topic_note_detail | topic_campaign.py |
| GET | /api/topic-campaign/notes | topic_notes | topic_campaign.py |
| POST | /api/topic-campaign/recover | topic_recover | topic_campaign.py |
| POST | /api/topic-campaign/run | topic_run | topic_campaign.py |
| GET | /api/topic-campaign/runtime-state | topic_runtime_state | topic_campaign.py |
| GET | /api/topic-campaign/stats | topic_stats | topic_campaign.py |
| GET | /api/topic-campaign/status | topic_status | topic_campaign.py |
| GET | /api/topic-campaign/timeline | topic_timeline | topic_campaign.py |
| GET | /api/topic-campaign/topics | topic_list | topic_campaign.py |
| GET | /topic-campaign | topic_campaign_page | topic_campaign.py |

### DCC (8 routes)

| Method | Path | Function | File |
|--------|------|----------|------|
| GET | /api/app_evidence/<int:record_id> | api_evidence_get | app_evidence.py |
| DELETE | /api/app_evidence/<int:record_id> | api_evidence_delete | app_evidence.py |
| POST | /api/app_evidence/<int:record_id>/confirm | api_evidence_confirm | app_evidence.py |
| POST | /api/app_evidence/<int:record_id>/reject | api_evidence_reject | app_evidence.py |
| POST | /api/app_evidence/<int:record_id>/shadow | api_evidence_shadow | app_evidence.py |
| GET | /api/app_evidence/list | api_evidence_list | app_evidence.py |
| GET | /api/app_evidence/stats | api_evidence_stats | app_evidence.py |
| POST | /api/app_evidence/upload | api_evidence_upload | app_evidence.py |

### KOS (53 routes)

| Method | Path | Function | File |
|--------|------|----------|------|
| GET | /account | api_kos_account | kos_routes.py |
| GET | /ad-candidates | api_ad_candidates | kos_routes.py |
| GET | /attribution | api_attribution | kos_routes.py |
| GET | /brand | api_kos_brand | kos_routes.py |
| POST | /campaign | api_kos_campaign | kos_routes.py |
| GET | /channel-roi | api_kos_channel_roi | kos_routes.py |
| POST | /collect | api_kos_collect | kos_routes.py |
| GET | /comments | api_comments | kos_routes.py |
| GET | /competitor-benchmark | api_competitor_benchmark | kos_routes.py |
| GET | /content-dna | api_content_dna | kos_routes.py |
| GET,POST | /cooperation | api_kos_cooperation | kos_routes.py |
| POST | /cooperation/confirm | api_kos_cooperation_confirm | kos_routes.py |
| POST | /cooperation/execute | api_kos_cooperation_execute | kos_routes.py |
| GET | /cost | api_kos_cost | kos_routes.py |
| GET | /detail | api_detail | kos_routes.py |
| POST | /email/invitation | api_kos_email_invitation | kos_routes.py |
| POST | /email/send | api_kos_email_send | kos_routes.py |
| POST | /execution | api_kos_execution_create | kos_routes.py |
| POST | /execution/<execution_id>/transition | api_kos_execution_transition | kos_routes.py |
| GET | /executions | api_kos_executions | kos_routes.py |
| GET | /funnel | api_kos_funnel | kos_routes.py |
| GET | /intent-analysis | api_intent_analysis | kos_routes.py |
| GET | /koc-tier | api_kos_koc_tier | kos_routes.py |
| GET,POST | /kos-identity | api_kos_identity | kos_routes.py |
| GET,POST | /lead | api_kos_lead | kos_routes.py |
| GET | /list | api_list | kos_routes.py |
| POST | /manual | api_kos_manual | kos_routes.py |
| POST | /operation | api_kos_record_operation | kos_routes.py |
| GET | /operations | api_kos_operations | kos_routes.py |
| POST | /outreach | api_outreach | kos_routes.py |
| GET | /overview | api_overview | kos_routes.py |
| GET | /ownership | api_kos_ownership | kos_routes.py |
| POST | /ownership/confirm | api_kos_ownership_confirm | kos_routes.py |
| GET | /ownership/overrides | api_kos_ownership_overrides | kos_routes.py |
| POST | /paid/execute | api_kos_paid_execute | kos_routes.py |
| POST | /paid/plan | api_kos_paid_plan | kos_routes.py |
| GET | /paid/plans | api_kos_paid_plans | kos_routes.py |
| POST | /paid/result | api_kos_paid_result | kos_routes.py |
| POST | /professional/disable | api_professional_disable | kos_routes.py |
| POST | /professional/enable | api_professional_enable | kos_routes.py |
| POST | /professional/import | api_professional_import | kos_routes.py |
| GET | /professional/metrics | api_professional_metrics | kos_routes.py |
| GET | /professional/status | api_professional_status | kos_routes.py |
| GET | /profile | api_kos_profile | kos_routes.py |
| POST | /refresh | api_refresh | kos_routes.py |
| POST | /reply/generate | api_reply_generate | kos_routes.py |
| POST | /report/generate | api_report_generate | kos_routes.py |
| GET | /report/view | api_report_view | kos_routes.py |
| GET | /reward | api_reward | kos_routes.py |
| POST | /reward/execute | api_kos_reward_execute | kos_routes.py |
| POST | /reward/issue | api_kos_reward_issue | kos_routes.py |
| GET | /rewards | api_kos_rewards | kos_routes.py |
| GET | /tier | api_kos_tier | kos_routes.py |

### NOTIFICATION (4 routes)

| Method | Path | Function | File |
|--------|------|----------|------|
| GET | /api/badge/counts | badge_counts | badge_api.py |
| POST | /api/badge/mark-all-read | badge_mark_all_read | badge_api.py |
| POST | /api/badge/mark-read/<notif_id> | badge_mark_read | badge_api.py |
| GET | /api/badge/notifications | badge_notifications | badge_api.py |

### PODCAST (9 routes)

| Method | Path | Function | File |
|--------|------|----------|------|
| POST | /breakout | api_breakout | podcast_routes.py |
| POST | /content-yield | api_content_yield | podcast_routes.py |
| GET | /entities | api_entities | podcast_routes.py |
| GET | /entity | api_get_entity | podcast_routes.py |
| POST | /entity | api_create_entity | podcast_routes.py |
| GET | /overview | api_overview | podcast_routes.py |
| POST | /runtime/validate | api_runtime_validate | podcast_routes.py |
| POST | /story-nodes | api_story_nodes | podcast_routes.py |
| POST | /topic-score | api_topic_score | podcast_routes.py |

### REPORT (7 routes)

| Method | Path | Function | File |
|--------|------|----------|------|
| GET | /api/export/excel | export_excel | export_report.py |
| GET | /api/export/file/<path:filename> | export_file | export_report.py |
| POST,GET | /api/export/generate | export_generate | export_report.py |
| GET | /api/export/list | export_list | export_report.py |
| GET | /api/export/preview | export_preview | export_report.py |
| GET | /api/export/report | export_unified | export_report.py |
| GET | /api/export/word | export_word | export_report.py |

### SYSTEM (73 routes)

| Method | Path | Function | File |
|--------|------|----------|------|
| GET | / | index | tests\_v4_live.py |
| GET | /api/ai/evaluations | ai_evaluations | system_ai_data_api.py |
| GET | /api/ai/logs | ai_logs | system_ai_data_api.py |
| GET | /api/ai/owasp | ai_owasp | system_ai_data_api.py |
| POST | /api/collector/start-cdp | collector_start_cdp | system_features_api.py |
| POST | /api/collector/stop-cdp | collector_stop_cdp | system_features_api.py |
| GET | /api/evaluation/analysis | evaluation_analysis | system_features_api.py |
| GET | /api/evaluation/badcases | evaluation_badcases | system_features_api.py |
| GET | /api/evaluation/collection | evaluation_collection | system_features_api.py |
| GET | /api/evaluation/golden-cases | evaluation_golden_cases | system_features_api.py |
| GET | /api/evaluation/run | evaluation_run | system_features_api.py |
| GET | /api/evaluation/stability | evaluation_stability | system_features_api.py |
| POST | /api/local-ai/analyze | local_ai_analyze | system_features_api.py |
| POST | /api/local-ai/chat | local_ai_chat | system_features_api.py |
| GET | /api/local-ai/status | local_ai_status | system_features_api.py |
| POST | /api/security/baseline | security_create_baseline | system_features_api.py |
| GET | /api/security/dangerous-code | security_dangerous_code | system_features_api.py |
| GET | /api/security/integrity | security_check_integrity | system_features_api.py |
| GET | /api/security/scan | security_scan | system_features_api.py |
| GET | /api/security/sensitive-info | security_sensitive_info | system_features_api.py |
| GET | /api/system/health/detailed | system_health | system_health_api.py |
| GET | /api/system/health/module/<module_name> | system_health_module | system_health_api.py |
| GET | /api/system/health/summary | system_health_summary | system_health_api.py |
| GET | /api/v4/api-keys | compat_api_keys_list | account\compat.py |
| POST | /api/v4/api-keys/generate | compat_api_keys_generate | account\compat.py |
| POST | /api/v4/api-keys/revoke | compat_api_keys_revoke | account\compat.py |
| GET | /approvals | api_list_approvals | account\api.py |
| POST | /approvals/<int:approval_id>/approve | api_approve_login | account\api.py |
| POST | /approvals/<int:approval_id>/reject | api_reject_login | account\api.py |
| GET | /audit | api_audit_logs | account\api.py |
| GET | /audit/stats | api_audit_stats | account\api.py |
| POST | /change-password | api_change_password | account\api.py |
| GET | /devices | api_list_devices | account\api.py |
| POST | /devices/<int:session_id>/revoke | api_revoke_device | account\api.py |
| GET | /health | health | auth_recovery_api.py |
| GET | /members | api_list_members | account\api.py |
| POST | /members | api_create_member | account\api.py |
| PUT | /members/<int:user_id> | api_update_member | account\api.py |
| DELETE | /members/<int:user_id> | api_remove_member | account\api.py |
| GET | /members/<int:user_id>/authorizations | api_get_member_auths | account\api.py |
| PUT | /members/<int:user_id>/authorizations | api_set_member_auths | account\api.py |
| GET | /nav | api_get_nav | account\api.py |
| PUT | /nav | api_save_nav | account\api.py |
| POST | /nav/reset | api_reset_nav | account\api.py |
| GET | /profile | api_get_profile | account\api.py |
| PUT | /profile | api_update_profile | account\api.py |
| GET | /protection | api_get_protection | account\api.py |
| PUT | /protection | api_set_protection | account\api.py |
| GET | /quota | api_quota | account\api.py |
| GET | /recovery | api_recovery_options | account\api.py |
| GET | /skills | api_list_skills | account\api.py |
| POST | /skills | api_add_skill | account\api.py |
| PUT | /skills/<skill_id>/config | api_configure_skill | account\api.py |
| POST | /skills/<skill_id>/disable | api_disable_skill | account\api.py |
| POST | /skills/<skill_id>/enable | api_enable_skill | account\api.py |
| GET | /summary | get_summary | auth_recovery_api.py |
| GET | /tasks | list_tasks | auth_recovery_api.py |
| POST | /tasks | create_task | auth_recovery_api.py |
| POST | /tasks/<int:task_id>/complete | complete_task | auth_recovery_api.py |
| POST | /tasks/<int:task_id>/fail | fail_task | auth_recovery_api.py |
| POST | /tasks/<int:task_id>/start | start_task | auth_recovery_api.py |
| POST | /totp/confirm | api_totp_confirm | account\api.py |
| POST | /totp/reset | api_totp_reset | account\api.py |
| POST | /totp/setup | api_totp_setup | account\api.py |
| GET | /totp/status | api_totp_status | account\api.py |
| POST | /totp/verify | api_totp_verify | account\api.py |
| GET | /verification/pending | api_pending_codes | account\api.py |
| POST | /verification/request | api_request_verification | account\api.py |
| POST | /verification/resend | api_resend_code | account\api.py |
| POST | /verification/verify | api_verify_code | account\api.py |
| GET | /workspace-keys | api_list_workspace_keys | account\api.py |
| POST | /workspace-keys | api_create_workspace_key | account\api.py |
| DELETE | /workspace-keys/<int:key_id> | api_revoke_workspace_key | account\api.py |

### UI (2 routes)

| Method | Path | Function | File |
|--------|------|----------|------|
| GET,POST | /<function_name> | api_viz_function | viz_api.py |
| GET | /registry | api_viz_registry | viz_api.py |

### ZBMP (15 routes)

| Method | Path | Function | File |
|--------|------|----------|------|
| GET | /api/pr-cases | api_pr_cases_list | pr_case_integration.py |
| GET | /api/pr-cases/<case_id> | api_pr_case_detail | pr_case_integration.py |
| POST | /api/pr-cases/match | api_pr_cases_match | pr_case_integration.py |
| GET | /api/pr-response-templates | api_pr_response_templates | pr_case_integration.py |
| GET | /api/pr/act-principle | get_act_principle | pr_case_integration.py |
| GET | /api/pr/cases/<int:case_id> | get_pr_case_detail | pr_case_integration.py |
| GET | /api/pr/triggers | get_special_report_triggers | pr_case_integration.py |
| POST | /api/swire/brand-collect | swire_brand_collect | swire_group.py |
| GET | /api/swire/brand-detail | swire_brand_detail | swire_group.py |
| POST | /api/swire/brand-remove | swire_brand_remove | swire_group.py |
| POST | /api/swire/brand-save | swire_brand_save | swire_group.py |
| POST | /api/swire/event | swire_event_add | swire_group.py |
| GET | /api/swire/events | swire_events | swire_group.py |
| GET | /api/swire/notes | swire_notes | swire_group.py |
| GET | /api/swire/overview | swire_overview | swire_group.py |

## 5. CI/CD Workflows

| Workflow | File |
|----------|------|
| Verify Z-Brand-Core | .github\workflows\platform-verify.yml |

## 6. Contracts (跨库契约)

| 文件 | 类型 | 域 |
|------|------|-----|
| contracts\CROSS_REPO_CONTRACT_BOUNDARY.md | md | CORE |
| contracts\lumenis_adapter.py | py | AI |
| contracts\__init__.py | py | CORE |
| contracts\global\HUMAN_CONTROL_GATE_v1.md | md | CORE |
| contracts\kos\COLLECTION_ACCURACY_GATE_v1.md | md | COLLECTOR |
| contracts\kos\KOS_ACCOUNT_ASSET_TEMPLATE_v1.md | md | SYSTEM |
| contracts\kos\KOS_ENTITY_OWNERSHIP_CONTRACT_v1.md | md | KOS |
| contracts\kos\KOS_RELEASE_BASELINE_v1.md | md | KOS |
| contracts\kos\KOS_UI_INTERACTION_HIERARCHY_v1.md | md | KOS |

## 7. 测试覆盖 (Test Coverage)

总测试函数: **2820**

| 测试文件 | 测试函数数 |
|----------|-----------|
| tests\test_skill_agent_boundary.py | 83 |
| tests\test_permission_gate.py | 80 |
| tests\test_runtime_guardian.py | 76 |
| tests\test_batch2_intel_security.py | 75 |
| tests\test_evaluation_system.py | 52 |
| tests\test_ai_evaluation.py | 46 |
| tests\test_report_audit.py | 46 |
| tests\test_evidence_chain.py | 44 |
| tests\test_viz_api.py | 43 |
| tests\test_ai_domain_context.py | 40 |
| tests\test_repository_registry.py | 37 |
| tests\test_permission_gate_app_integration.py | 36 |
| tests\test_sogou_adapters.py | 36 |
| tests\test_collector_audit.py | 35 |
| tests\test_dual_domain_e2e.py | 34 |
| tests\test_ad_intelligence_platforms.py | 32 |
| tests\test_browser_surface.py | 31 |
| tests\test_risk_dual_domain.py | 31 |
| tests\test_runtime_guardian_integration.py | 31 |
| tests\test_historical_data.py | 30 |
| tests\test_missing_values.py | 30 |
| tests\test_permission_dual_domain.py | 30 |
| tests\test_risk_audit.py | 30 |
| tests\test_batch3_rate_limiter.py | 29 |
| tests\test_wechat_notifier.py | 29 |
| tests\test_domain_context_switching.py | 28 |
| tests\test_p1_gap_closure.py | 28 |
| tests\test_api_audit.py | 27 |
| tests\test_collector_multi_platform.py | 27 |
| tests\test_kos_interest_graph.py | 26 |
| tests\test_kos_platform_rules.py | 26 |
| tests\test_report_dual_domain.py | 25 |
| tests\test_v2_p0_modules.py | 25 |
| tests\test_api_domain_contract.py | 24 |
| tests\test_batch3_cache_manager.py | 24 |
| tests\test_domain_context.py | 24 |
| tests\test_ip_risk_state_machine.py | 24 |
| tests\test_localization_guard.py | 24 |
| tests\test_source_provenance.py | 24 |
| tests\test_batch3_collect_state.py | 23 |
| tests\test_idea_sit_backing.py | 23 |
| tests\test_time_normalization.py | 23 |
| tests\test_browser_runtime_resident.py | 22 |
| tests\test_data_quality_subject_rejudge.py | 22 |
| tests\test_canonical_data_t4.py | 21 |
| tests\test_agent_security.py | 20 |
| tests\test_instagram_main_adapter.py | 20 |
| tests\test_learning_persistence.py | 20 |
| tests\test_collection_quality_gate.py | 19 |
| tests\test_performance_and_system.py | 19 |

---

*本文件由 scripts/audit_tools/asset_impact_scan.py 自动生成，请勿手动编辑。*
*完整机器可读索引见 audit/ASSET_IMPACT_GRAPH.json*