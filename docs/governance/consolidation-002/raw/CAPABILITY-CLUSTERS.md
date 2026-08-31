# 同能力多实现聚类（机器初筛，供唯一 Owner 判定）

## AI/大模型（13）
- `adaptive_engine.py`
- `ai_analyzer.py`
- `ai_filter.py`
- `ai_gateway_v570.py`
- `ai_learning_engine.py`
- `ark_llm.py`
- `intelligence.py`
- `local_ai_client.py`
- `tests/_patch_ai_xhs.py`
- `tests/github_benchmark.py`
- `tests/test_adaptive_engine.py`
- `tests/test_llm_gateway.py`
- `tests/test_llm_online.py`

## 证据/评审流（2）
- `app_evidence.py`
- `review_workflow.py`

## 恢复/守护/稳定（17）
- `auth_recovery_api.py`
- `auth_recovery_center.py`
- `auto_recovery.py`
- `collector_guard/guard.py`
- `safety_boundary.py`
- `scripts/stability_fix.py`
- `stability_monitor.py`
- `system_guardian.py`
- `system_watchdog.py`
- `tests/_patch_gitsafety.py`
- `tests/_patch_guard_wiring.py`
- `tests/_test_guard_wiring.py`
- `tests/test_auto_recovery.py`
- `tests/test_guard_wiring.py`
- `tests/test_safety_boundary.py`
- `tunnel_guardian.py`
- `v4_upgrade/adapters/auth_recovery.py`

## Cookie/登录（10）
- `bilibili_login_manager.py`
- `import_cookies.py`
- `import_xhs_cookies.py`
- `scripts/sync_xhs_cookie_from_cdp.py`
- `tests/_check_9222_login.py`
- `tests/_test_auth_api.py`
- `tests/test_auth_api.py`
- `v4_upgrade/adapters/cookie_vault.py`
- `weibo_login_manager.py`
- `xhs_cookie_bridge.py`

## 品牌/案例/知识（10）
- `brand_knowledge_base.py`
- `brand_stats_recompute.py`
- `case_deep_analysis.py`
- `pr_case_engine.py`
- `pr_case_integration.py`
- `public_opinion_cases.py`
- `swire_group.py`
- `tests/_clean_brand_test.py`
- `tests/_swire_scan.py`
- `tests/test_brand_library.py`

## 报告/导出（10）
- `brand_report_generator.py`
- `daily_report.py`
- `export_report.py`
- `report_engine.py`
- `report_export/app_report_api_patch.py`
- `report_export/report_engine.py`
- `report_filter.py`
- `scripts/export_report.py`
- `tests/test_report_periods.py`
- `weekly_events.py`

## 网络/代理/隧道（10）
- `browser_discovery.py`
- `network_adaptive.py`
- `start_tunnel.py`
- `tests/_cdp_proxy.py`
- `tests/_patch_automation_noproxy.py`
- `tests/_patch_proxy_wiring.py`
- `tests/_proxy_api_check.py`
- `tests/_proxy_realcheck.py`
- `tests/_test_proxy_pool.py`
- `tests/test_proxy_pool.py`

## 缓存/内存（2）
- `cache_manager.py`
- `memory_optimizer.py`

## 采集器（32）
- `check_collection.py`
- `check_collection_detail.py`
- `collector.py`
- `collector_auto_start.py`
- `collector_automation.py`
- `collector_v2/scheduler/collector_job.py`
- `collector_v2/weibo/collector.py`
- `collector_v2/xhs/collector.py`
- `collector_v2_integration.py`
- `monitor_pipeline.py`
- `scripts/collect_now.py`
- `tests/_collect_check.py`
- `tests/_collect_probe.py`
- `tests/_health_collect.py`
- `tests/_live_collect.py`
- `tests/_patch_collect_state.py`
- `tests/_patch_collector.py`
- `tests/_patch_collector_cdp.py`
- `tests/_patch_collector_pycdp.py`
- `tests/_patch_collector_tune.py`
- `tests/_persist_rednote.py`
- `tests/_run_one_collect.py`
- `tests/_test_cdp_collect.py`
- `tests/_test_collector_guard.py`
- `tests/test_collect_pipeline.py`
- `tests/test_collect_state.py`
- `tests/test_collection_full.py`
- `v4_upgrade/adapters/collector_service.py`
- `web_monitor.py`
- `web_monitor_v570.py`
- `web_topic_discovery.py`
- `xhs_cdp_collector.py`

## 评测/验证（16）
- `check_db_dates.py`
- `check_empty_tables.py`
- `check_logs.py`
- `check_system.py`
- `check_warnings.py`
- `ci_cd.py`
- `evaluate_system_timing.py`
- `evaluation_system.py`
- `scripts/check_system.py`
- `tests/_check_ai.py`
- `tests/_verify4.py`
- `tests/_verify4b.py`
- `tests/_verify_8201.py`
- `tests/_verify_e2e.py`
- `verify_system.py`
- `verify_system_e2e.py`

## 配置/设置（5）
- `config.py`
- `platform_adapters/config.py`
- `proxy_pool/config.py`
- `settings_module.py`
- `v4_upgrade/config.py`

## 数据库/迁移（7）
- `database.py`
- `database_migrations.py`
- `populate_empty_tables.py`
- `reprocess.py`
- `scripts/init_database_data.py`
- `tests/_patch_database_pubdt.py`
- `tests/test_database.py`

## 事件（4）
- `event_graph.py`
- `tests/test_event_curation.py`
- `tests/test_event_date.py`
- `tests/test_negative_event_api.py`

## 风险（5）
- `collector_guard/risk_engine.py`
- `risk_engine.py`
- `tests/_test_risk_engine.py`
- `tests/test_risk_engine.py`
- `v4_upgrade/adapters/risk_controller.py`

## 主体/分类（4）
- `collector_v2/pipeline/subject_filter.py`
- `subject_classifier.py`
- `subject_rules.py`
- `tests/test_subject_redline.py`

## 通知（1）
- `wechat_notifier.py`

## 平台适配（4）
- `proxy_pool/adapters.py`
- `tests/_adapter_live.py`
- `tests/test_douyin_adapter.py`
- `tests/test_instagram_adapter.py`
