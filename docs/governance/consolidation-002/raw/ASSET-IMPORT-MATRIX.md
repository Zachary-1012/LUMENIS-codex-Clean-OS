# 资产静态依赖矩阵（机器生成，只读扫描）

- 扫描本地 Python 文件：**400**（已排除 venv/node_modules/浏览器profile/data/backups 等）
- 从 `app.py` 静态可达模块：**84**
- AST 解析失败：**0**

列含义：reach=app运行时静态可达；in=被几个本地模块依赖；main=含独立入口；test=测试

| 文件 | 行数 | reach | in | main | 依赖的本地模块 |
|---|--:|:--:|--:|:--:|---|
| `tests/__init__.py` | 2 | — | 0 |  |  |
| `tests/_adapter_live.py` | 26 | — | 0 |  | baidu_search, bing_search, dianping, doubao_search, douyin, smzdm, sogou_wechat, zhihu |
| `tests/_append_log.py` | 63 | — | 0 |  |  |
| `tests/_append_log10.py` | 39 | — | 0 |  |  |
| `tests/_append_log11.py` | 33 | — | 0 |  |  |
| `tests/_append_log6.py` | 35 | — | 0 |  |  |
| `tests/_append_log7.py` | 35 | — | 0 |  |  |
| `tests/_append_log8.py` | 31 | — | 0 |  |  |
| `tests/_append_log9.py` | 46 | — | 0 |  |  |
| `tests/_archive_blueprint.py` | 30 | — | 0 |  |  |
| `tests/_audit_data.py` | 23 | — | 0 |  |  |
| `tests/_audit_misc.py` | 31 | — | 0 |  | v4_upgrade, registry, risk_controller |
| `tests/_audit_system.py` | 145 | — | 0 |  |  |
| `tests/_audit_time2.py` | 23 | — | 0 |  |  |
| `tests/_audit_time_anomaly.py` | 37 | — | 0 |  |  |
| `tests/_backfill_pubdt.py` | 31 | — | 0 |  |  |
| `tests/_cdp_check.py` | 41 | — | 0 |  |  |
| `tests/_cdp_check2.py` | 47 | — | 0 |  |  |
| `tests/_cdp_check3.py` | 36 | — | 0 |  |  |
| `tests/_cdp_detach_start.py` | 14 | — | 0 |  | cdp_helper |
| `tests/_cdp_keepalive.py` | 26 | — | 0 |  | cdp_helper |
| `tests/_cdp_probe.py` | 29 | — | 0 |  |  |
| `tests/_cdp_proxy.py` | 25 | — | 0 |  |  |
| `tests/_check_9222_login.py` | 32 | — | 0 |  |  |
| `tests/_check_ai.py` | 25 | — | 0 |  | intelligence |
| `tests/_chk_cdp.py` | 12 | — | 0 |  |  |
| `tests/_chk_empty.py` | 11 | — | 0 |  |  |
| `tests/_clean_brand_test.py` | 13 | — | 0 |  |  |
| `tests/_collect_check.py` | 31 | — | 0 |  |  |
| `tests/_collect_probe.py` | 35 | — | 0 |  |  |
| `tests/_desk_load.py` | 29 | — | 0 |  |  |
| `tests/_diag_black.py` | 26 | — | 0 |  |  |
| `tests/_diag_black2.py` | 21 | — | 0 |  |  |
| `tests/_diag_black3.py` | 21 | — | 0 |  |  |
| `tests/_diag_black4.py` | 15 | — | 0 |  |  |
| `tests/_diag_black5.py` | 26 | — | 0 |  |  |
| `tests/_diag_black6.py` | 22 | — | 0 |  |  |
| `tests/_diag_cdp_subproc.py` | 17 | — | 0 |  |  |
| `tests/_diag_icon.py` | 25 | — | 0 |  |  |
| `tests/_diag_icon2.py` | 24 | — | 0 |  |  |
| `tests/_diag_inline.py` | 24 | — | 0 |  |  |
| `tests/_diag_mobile.py` | 44 | — | 0 |  |  |
| `tests/_diag_mobile2.py` | 29 | — | 0 |  |  |
| `tests/_diag_rule.py` | 20 | — | 0 |  |  |
| `tests/_diag_switch.py` | 20 | — | 0 |  |  |
| `tests/_dirty_detail.py` | 19 | — | 0 |  |  |
| `tests/_dup_schedule.py` | 31 | — | 0 |  |  |
| `tests/_empty_title.py` | 11 | — | 0 |  |  |
| `tests/_extract_docx.py` | 28 | — | 0 |  |  |
| `tests/_extract_frames.py` | 23 | — | 0 |  |  |
| `tests/_extract_js.py` | 10 | — | 0 |  |  |
| `tests/_extract_zbmp.py` | 40 | — | 0 |  |  |
| `tests/_fix_empty_titles.py` | 26 | — | 0 |  |  |
| `tests/_fix_state_order.py` | 43 | — | 0 |  |  |
| `tests/_fix_testpath.py` | 39 | — | 0 |  |  |
| `tests/_fix_title_fallback.py` | 26 | — | 0 |  |  |
| `tests/_health_collect.py` | 28 | — | 0 |  |  |
| `tests/_healthcheck.py` | 59 | — | 0 |  | subject_rules |
| `tests/_importer_live.py` | 57 | — | 0 |  | v4_upgrade |
| `tests/_init_schedule_table.py` | 31 | — | 0 |  | platform_adapters |
| `tests/_inspect_tables.py` | 19 | — | 0 |  |  |
| `tests/_live_collect.py` | 33 | — | 0 |  | xhs_cookie_bridge |
| `tests/_mobile_probe.py` | 47 | — | 0 |  |  |
| `tests/_mount_check.py` | 29 | — | 0 |  |  |
| `tests/_notes_schema.py` | 15 | — | 0 |  |  |
| `tests/_patch_ai_xhs.py` | 53 | — | 0 |  |  |
| `tests/_patch_app.py` | 49 | — | 0 |  |  |
| `tests/_patch_app_feedback.py` | 28 | — | 0 |  |  |
| `tests/_patch_automation.py` | 29 | — | 0 |  |  |
| `tests/_patch_automation_noproxy.py` | 21 | — | 0 |  |  |
| `tests/_patch_cdp_autostart.py` | 40 | — | 0 |  |  |
| `tests/_patch_collect_state.py` | 39 | — | 0 |  |  |
| `tests/_patch_collector.py` | 37 | — | 0 |  |  |
| `tests/_patch_collector_cdp.py` | 176 | — | 0 |  |  |
| `tests/_patch_collector_pycdp.py` | 48 | — | 0 |  |  |
| `tests/_patch_collector_tune.py` | 139 | — | 0 |  |  |
| `tests/_patch_database_pubdt.py` | 34 | — | 0 |  |  |
| `tests/_patch_gitsafety.py` | 25 | — | 0 |  |  |
| `tests/_patch_guard_wiring.py` | 50 | — | 0 |  |  |
| `tests/_patch_logs.py` | 58 | — | 0 |  |  |
| `tests/_patch_norm_title.py` | 40 | — | 0 |  |  |
| `tests/_patch_port.py` | 29 | — | 0 |  |  |
| `tests/_patch_proxy_wiring.py` | 73 | — | 0 |  |  |
| `tests/_patch_state_func.py` | 59 | — | 0 |  |  |
| `tests/_patch_title_fallback.py` | 32 | — | 0 |  |  |
| `tests/_patch_version_nav.py` | 38 | — | 0 |  |  |
| `tests/_persist_rednote.py` | 54 | — | 0 |  | database |
| `tests/_probe9222.py` | 43 | — | 0 |  |  |
| `tests/_probe_cdp_nav.py` | 40 | — | 0 |  |  |
| `tests/_probe_db2.py` | 35 | — | 0 |  |  |
| `tests/_probe_explore_url.py` | 46 | — | 0 |  |  |
| `tests/_proxy_api_check.py` | 26 | — | 0 |  |  |
| `tests/_proxy_realcheck.py` | 30 | — | 0 |  | proxy_pool, config, loader |
| `tests/_read_docx.py` | 22 | — | 0 |  |  |
| `tests/_readiness_audit.py` | 73 | — | 0 |  | subject_rules |
| `tests/_repo.py` | 13 | — | 0 |  |  |
| `tests/_restart_9222.py` | 55 | — | 0 |  |  |
| `tests/_run_core.py` | 23 | — | 0 |  |  |
| `tests/_run_core2.py` | 17 | — | 0 |  |  |
| `tests/_run_core_tests.py` | 40 | — | 0 |  |  |
| `tests/_run_one_collect.py` | 41 | — | 0 |  |  |
| `tests/_shot_before.py` | 40 | — | 0 |  |  |
| `tests/_start_browser.py` | 26 | — | 0 |  |  |
| `tests/_start_cdp.py` | 24 | — | 0 |  | cdp_helper |
| `tests/_swire_scan.py` | 45 | — | 0 |  |  |
| `tests/_test_auth_api.py` | 40 | — | 0 |  |  |
| `tests/_test_cdp_collect.py` | 24 | — | 0 |  | collector |
| `tests/_test_collector_guard.py` | 74 | — | 0 |  | collector_guard |
| `tests/_test_guard_wiring.py` | 45 | — | 0 |  | guard, state |
| `tests/_test_proxy_pool.py` | 101 | — | 0 |  | config, manager, models |
| `tests/_test_risk_engine.py` | 68 | — | 0 |  | risk_engine, state |
| `tests/_test_vc_api.py` | 48 | — | 0 |  |  |
| `tests/_test_version_api.py` | 39 | — | 0 |  |  |
| `tests/_test_version_center.py` | 47 | — | 0 |  | git_manager |
| `tests/_topic_run.py` | 32 | — | 0 |  |  |
| `tests/_topic_run2.py` | 29 | — | 0 |  |  |
| `tests/_ui_final.py` | 40 | — | 0 |  |  |
| `tests/_ui_mon.py` | 18 | — | 0 |  |  |
| `tests/_ui_mset.py` | 18 | — | 0 |  |  |
| `tests/_ui_pub_mobile.py` | 26 | — | 0 |  |  |
| `tests/_ui_q.py` | 18 | — | 0 |  |  |
| `tests/_ui_shot.py` | 48 | — | 0 |  |  |
| `tests/_ui_shot2.py` | 45 | — | 0 |  |  |
| `tests/_ui_shot3.py` | 43 | — | 0 |  |  |
| `tests/_v4_live.py` | 24 | — | 0 | ⚑ | v4_upgrade |
| `tests/_v4dbg.py` | 17 | — | 0 |  | v4_upgrade |
| `tests/_verify4.py` | 27 | — | 0 |  |  |
| `tests/_verify4b.py` | 30 | — | 0 |  |  |
| `tests/_verify_8201.py` | 43 | — | 0 |  |  |
| `tests/_verify_e2e.py` | 47 | — | 0 |  |  |
| `tests/_watch_1605.py` | 27 | — | 0 |  |  |
| `tests/_watch_auto.py` | 24 | — | 0 |  |  |
| `tests/_xhs_probe.py` | 46 | — | 0 |  |  |
| `tests/audit_probe_1.py` | 73 | — | 0 |  |  |
| `tests/audit_probe_2.py` | 31 | — | 0 |  |  |
| `tests/audit_probe_3.py` | 53 | — | 0 |  |  |
| `tests/audit_probe_4.py` | 54 | — | 0 |  |  |
| `tests/audit_probe_5.py` | 82 | — | 0 |  |  |
| `tests/audit_probe_6.py` | 48 | — | 0 |  |  |
| `tests/backfill_detail_cdp.py` | 83 | — | 0 |  |  |
| `tests/conftest.py` | 46 | — | 0 |  | app, database |
| `tests/github_benchmark.py` | 45 | — | 0 |  |  |
| `tests/healthcheck.py` | 59 | — | 0 |  | subject_rules |
| `tests/test_adaptive_engine.py` | 55 | — | 0 |  | adaptive_engine |
| `tests/test_ai.py` | 119 | — | 0 |  | ai_analyzer, ark_llm, intelligence, subject_rules |
| `tests/test_api.py` | 120 | — | 0 |  |  |
| `tests/test_api_smoke.py` | 53 | — | 0 |  | app, models, security |
| `tests/test_auth_api.py` | 40 | — | 0 |  |  |
| `tests/test_auto_recovery.py` | 32 | — | 0 |  | auto_recovery |
| `tests/test_bilibili.py` | 22 | — | 0 |  | bilibili_login_manager |
| `tests/test_brand_library.py` | 62 | — | 0 |  | swire_group |
| `tests/test_browser_e2e.py` | 114 | — | 0 |  | collector_automation |
| `tests/test_collect_pipeline.py` | 53 | — | 0 |  | v4_upgrade, collector_service, persist, registry |
| `tests/test_collect_state.py` | 30 | — | 0 |  | collector |
| `tests/test_collection_full.py` | 117 | — | 0 |  | xhs_cookie_bridge |
| `tests/test_data_feedback.py` | 53 | — | 0 |  | data_feedback_loop |
| `tests/test_database.py` | 90 | — | 0 |  |  |
| `tests/test_douyin_adapter.py` | 20 | — | 0 |  | douyin |
| `tests/test_e2e.py` | 526 | — | 0 | ⚑ | config, database_migrations, logger |
| `tests/test_event_curation.py` | 48 | — | 0 |  | database |
| `tests/test_event_date.py` | 46 | — | 0 |  | database |
| `tests/test_guard_wiring.py` | 45 | — | 0 |  | guard, state |
| `tests/test_health_center.py` | 76 | — | 0 |  | platform_adapters, health_center, state_map |
| `tests/test_instagram_adapter.py` | 32 | — | 0 |  | registry |
| `tests/test_llm_gateway.py` | 57 | — | 0 | ⚑ | intelligence |
| `tests/test_llm_online.py` | 47 | — | 0 |  | intelligence |
| `tests/test_negative_event_api.py` | 65 | — | 0 |  | database, subject_rules |
| `tests/test_proxy_pool.py` | 104 | — | 0 |  | proxy_pool, config, loader, manager, models |
| `tests/test_report_periods.py` | 18 | — | 0 |  | export_report |
| `tests/test_risk_engine.py` | 68 | — | 0 |  | risk_engine, state |
| `tests/test_safety_boundary.py` | 77 | — | 0 |  | safety_boundary |
| `tests/test_scheduling.py` | 177 | — | 0 |  | platform_adapters, state_map |
| `tests/test_security_scan.py` | 59 | — | 0 |  | security_scanner |
| `tests/test_sentiment_engine.py` | 42 | — | 0 |  | ai_analyzer |
| `tests/test_subject_redline.py` | 39 | — | 0 |  | subject_rules |
| `tests/test_system.py` | 48 | — | 0 |  | ai_analyzer, database, subject_rules |
| `tests/test_title_fallback.py` | 34 | — | 0 |  | database |
| `tests/test_topic_port.py` | 73 | — | 0 |  | database, topic_campaign |
| `tests/test_version_api.py` | 39 | — | 0 |  |  |
| `tests/v4_smoke.py` | 158 | — | 0 |  | v4_upgrade, registry, fix_publish_date, analyzer |
| `_reanalyze.py` | 43 | — | 0 |  | ai_analyzer |
| `adaptive_engine.py` | 382 | ✅ | 2 |  |  |
| `ai_analyzer.py` | 659 | ✅ | 13 |  | subject_rules |
| `ai_filter.py` | 363 | ✅ | 2 | ⚑ | ai_analyzer, database, intelligence |
| `ai_gateway_v570.py` | 208 | ✅ | 2 |  | ai_analyzer |
| `ai_learning_engine.py` | 449 | ✅ | 1 | ⚑ | ark_llm |
| `app.py` | 5074 | ✅ | 3 | ⚑ | ai_analyzer, ai_filter, ai_gateway_v570, ai_learning_engine, app_evidence, architecture_api, ark_llm, auth_recovery_api, bilibili_login_manager, brand_knowledge |
| `app_evidence.py` | 381 | ✅ | 1 |  |  |
| `app_refactor_blueprint.py` | 289 | — | 0 | ⚑ |  |
| `architecture_api.py` | 409 | ✅ | 1 |  | adaptive_engine, auto_recovery, data_feedback_loop, safety_boundary |
| `ark_llm.py` | 362 | ✅ | 4 | ⚑ |  |
| `auth_recovery_api.py` | 129 | ✅ | 1 |  | auth_recovery_center, topic_campaign |
| `auth_recovery_center.py` | 332 | ✅ | 1 |  |  |
| `auto_recovery.py` | 473 | ✅ | 2 |  |  |
| `bilibili_login_manager.py` | 193 | ✅ | 2 | ⚑ |  |
| `brand_knowledge_base.py` | 206 | ✅ | 1 |  |  |
| `brand_report_generator.py` | 310 | ✅ | 1 |  |  |
| `brand_stats_recompute.py` | 124 | ✅ | 1 | ⚑ |  |
| `browser_discovery.py` | 32 | ✅ | 1 |  |  |
| `cache_manager.py` | 305 | ✅ | 2 |  |  |
| `case_deep_analysis.py` | 307 | ✅ | 1 |  |  |
| `cdp_helper.py` | 519 | ✅ | 8 | ⚑ |  |
| `check_collection.py` | 44 | — | 0 |  |  |
| `check_collection_detail.py` | 53 | — | 0 |  |  |
| `check_db_dates.py` | 38 | — | 0 |  |  |
| `check_empty_tables.py` | 20 | — | 0 |  |  |
| `check_logs.py` | 43 | — | 0 |  |  |
| `check_system.py` | 41 | — | 0 |  |  |
| `check_warnings.py` | 39 | — | 0 |  |  |
| `ci_cd.py` | 461 | — | 0 | ⚑ |  |
| `collector.py` | 320 | ✅ | 9 |  | collector_automation, guard |
| `collector_auto_start.py` | 184 | ✅ | 1 |  |  |
| `collector_automation.py` | 565 | ✅ | 3 | ⚑ | collector, database, subject_rules, xhs_cookie_bridge |
| `collector_guard/__init__.py` | 32 | — | 1 |  |  |
| `collector_guard/analyzer.py` | 111 | ✅ | 1 |  | state |
| `collector_guard/checkpoint.py` | 84 | ✅ | 1 |  |  |
| `collector_guard/guard.py` | 135 | ✅ | 3 |  | analyzer, checkpoint, metrics, rate_limiter, state |
| `collector_guard/metrics.py` | 61 | ✅ | 1 |  |  |
| `collector_guard/rate_limiter.py` | 111 | ✅ | 1 |  | state |
| `collector_guard/risk_engine.py` | 125 | — | 2 |  | state |
| `collector_guard/state.py` | 45 | ✅ | 8 |  |  |
| `collector_v2/__init__.py` | 11 | — | 0 |  |  |
| `collector_v2/base.py` | 112 | — | 3 |  |  |
| `collector_v2/browser_session.py` | 165 | — | 0 |  |  |
| `collector_v2/official_info_scraper.py` | 578 | ✅ | 1 | ⚑ |  |
| `collector_v2/pipeline/__init__.py` | 15 | — | 0 |  |  |
| `collector_v2/pipeline/deduplicate.py` | 173 | — | 3 |  |  |
| `collector_v2/pipeline/normalize.py` | 211 | — | 3 |  |  |
| `collector_v2/pipeline/persist.py` | 202 | — | 1 |  |  |
| `collector_v2/pipeline/spam_filter.py` | 129 | — | 1 |  |  |
| `collector_v2/pipeline/subject_filter.py` | 148 | — | 2 |  |  |
| `collector_v2/run_live_engine.py` | 28 | — | 0 | ⚑ | ai_analyzer, live_engine |
| `collector_v2/run_xhs_live.py` | 14 | — | 0 | ⚑ | deduplicate, normalize, collector |
| `collector_v2/scheduler/__init__.py` | 5 | — | 0 |  |  |
| `collector_v2/scheduler/collector_job.py` | 246 | — | 1 |  |  |
| `collector_v2/session/__init__.py` | 4 | — | 0 |  |  |
| `collector_v2/session/browser_session.py` | 101 | — | 0 |  |  |
| `collector_v2/weibo/__init__.py` | 5 | — | 0 |  | collector |
| `collector_v2/weibo/collector.py` | 262 | — | 0 |  | base |
| `collector_v2/xhs/__init__.py` | 6 | — | 0 |  | collector |
| `collector_v2/xhs/client.py` | 219 | — | 1 |  |  |
| `collector_v2/xhs/collector.py` | 234 | — | 2 |  | base, client |
| `collector_v2/xhs/live_engine.py` | 75 | — | 2 |  | deduplicate, normalize, subject_filter, models, database |
| `collector_v2/xhs/models.py` | 28 | — | 2 |  | base |
| `collector_v2/xhs/parser.py` | 206 | — | 0 |  | models |
| `collector_v2_integration.py` | 240 | — | 0 |  | deduplicate, normalize, persist, spam_filter, subject_filter, collector_job, collector |
| `config.py` | 351 | ✅ | 2 | ⚑ |  |
| `daily_report.py` | 657 | ✅ | 4 | ⚑ | ai_analyzer, database, intelligence, xhs_cookie_bridge |
| `data_feedback_loop.py` | 380 | ✅ | 2 |  |  |
| `database.py` | 960 | ✅ | 27 |  | subject_rules |
| `database_migrations.py` | 518 | — | 1 | ⚑ |  |
| `deployment/backup.py` | 13 | — | 0 |  | database |
| `deployment/deployment/µò░µì«σ║ôσñçΣ╗╜.py` | 153 | — | 0 | ⚑ | database |
| `deployment/deployment/σüÑσ║╖µúÇµƒÑ.py` | 180 | — | 0 | ⚑ | database, intelligence |
| `deployment/health_check.py` | 22 | — | 0 |  |  |
| `deployment/健康检查.py` | 180 | — | 0 | ⚑ | database, intelligence |
| `deployment/数据库备份.py` | 153 | — | 0 | ⚑ | database |
| `docs/reference/apple-ui-reference/raw/build_catalog.py` | 42 | — | 0 |  |  |
| `docs/reference/apple-ui-reference/raw/build_db.py` | 267 | — | 0 |  |  |
| `evaluate_system_timing.py` | 259 | — | 0 |  |  |
| `evaluation_system.py` | 460 | ✅ | 2 |  |  |
| `event_graph.py` | 520 | ✅ | 1 |  |  |
| `export_report.py` | 732 | ✅ | 2 |  | subject_rules |
| `function_registry.py` | 122 | ✅ | 2 |  |  |
| `import_cookies.py` | 149 | — | 0 |  |  |
| `import_xhs_cookies.py` | 116 | — | 0 |  |  |
| `intelligence.py` | 200 | ✅ | 11 |  |  |
| `local_ai_client.py` | 232 | ✅ | 2 |  |  |
| `logger.py` | 319 | — | 1 | ⚑ |  |
| `memory_optimizer.py` | 333 | ✅ | 2 | ⚑ |  |
| `models.py` | 319 | ✅ | 2 | ⚑ |  |
| `monitor_pipeline.py` | 29 | — | 0 | ⚑ | ai_analyzer, collector, database |
| `monitoring.py` | 590 | — | 0 | ⚑ |  |
| `network_adaptive.py` | 212 | ✅ | 2 |  |  |
| `platform_adapters/__init__.py` | 25 | ✅ | 9 |  |  |
| `platform_adapters/base.py` | 103 | — | 4 |  |  |
| `platform_adapters/config.py` | 52 | ✅ | 3 |  |  |
| `platform_adapters/douyin.py` | 57 | — | 0 |  | base, registry |
| `platform_adapters/health_center.py` | 204 | ✅ | 2 |  | database, platform_adapters, config, state_map, xhs_cookie_bridge |
| `platform_adapters/registry.py` | 35 | — | 3 |  | base, config |
| `platform_adapters/scheduling/__init__.py` | 37 | — | 0 |  |  |
| `platform_adapters/scheduling/decision.py` | 247 | — | 1 |  | platform_adapters, policy, state_map |
| `platform_adapters/scheduling/planner.py` | 123 | — | 0 |  | platform_adapters, decision, policy, state_map, store |
| `platform_adapters/scheduling/policy.py` | 92 | — | 2 |  |  |
| `platform_adapters/scheduling/state_map.py` | 170 | ✅ | 5 |  |  |
| `platform_adapters/scheduling/store.py` | 110 | — | 1 |  |  |
| `platform_adapters/xhs.py` | 103 | — | 0 |  | collector, base, config, registry |
| `platform_adapters/xhs_app_topic.py` | 248 | — | 0 |  | base, registry |
| `populate_empty_tables.py` | 294 | — | 0 | ⚑ |  |
| `pr_case_engine.py` | 286 | ✅ | 1 | ⚑ |  |
| `pr_case_integration.py` | 579 | ✅ | 1 |  |  |
| `proxy_pool/__init__.py` | 17 | ✅ | 3 |  | models |
| `proxy_pool/adapters.py` | 29 | — | 0 |  | manager |
| `proxy_pool/config.py` | 36 | ✅ | 6 |  |  |
| `proxy_pool/health.py` | 24 | ✅ | 1 |  |  |
| `proxy_pool/loader.py` | 42 | ✅ | 3 |  | config, manager, models |
| `proxy_pool/manager.py` | 159 | ✅ | 4 |  | config, health, models |
| `proxy_pool/models.py` | 50 | ✅ | 4 |  |  |
| `public_opinion_cases.py` | 522 | ✅ | 1 | ⚑ |  |
| `quick_check.py` | 50 | — | 0 |  |  |
| `read_docx.py` | 34 | — | 0 |  |  |
| `report_engine.py` | 91 | ✅ | 2 |  | ai_analyzer, ai_filter, daily_report, database |
| `report_export/app_report_api_patch.py` | 17 | — | 0 |  | report_engine |
| `report_export/report_engine.py` | 370 | ✅ | 2 |  |  |
| `report_filter.py` | 209 | ✅ | 1 | ⚑ |  |
| `reprocess.py` | 158 | ✅ | 2 | ⚑ | ai_analyzer, database, intelligence, web_monitor |
| `review_workflow.py` | 355 | — | 0 |  |  |
| `risk_engine.py` | 15 | — | 0 |  | daily_report, subject_rules |
| `run_production.py` | 136 | — | 0 | ⚑ | app, cdp_helper, memory_optimizer, stability_monitor |
| `run_supervised.py` | 195 | — | 0 | ⚑ |  |
| `safety_boundary.py` | 435 | ✅ | 2 |  |  |
| `scripts/backup_db.py` | 118 | — | 0 | ⚑ |  |
| `scripts/check_system.py` | 160 | — | 0 | ⚑ |  |
| `scripts/collect_now.py` | 94 | — | 0 | ⚑ | collector, live_engine |
| `scripts/daily_git_sync.py` | 131 | — | 0 | ⚑ | subject_rules, git_manager |
| `scripts/export_report.py` | 133 | — | 0 | ⚑ | daily_report, report_engine |
| `scripts/github_upgrade_check.py` | 121 | — | 0 | ⚑ |  |
| `scripts/init_database_data.py` | 412 | — | 0 | ⚑ |  |
| `scripts/init_db.py` | 347 | — | 0 | ⚑ |  |
| `scripts/inventory/asset_scan.py` | 225 | — | 0 |  |  |
| `scripts/license_audit.py` | 62 | — | 0 | ⚑ |  |
| `scripts/run_core_regression.py` | 53 | — | 0 | ⚑ |  |
| `scripts/stability_fix.py` | 273 | — | 0 | ⚑ |  |
| `scripts/staging_setup.py` | 52 | — | 0 | ⚑ |  |
| `scripts/sync_xhs_cookie_from_cdp.py` | 115 | — | 0 | ⚑ |  |
| `security_scanner.py` | 367 | ✅ | 3 |  |  |
| `settings_module.py` | 321 | ✅ | 1 |  |  |
| `stability_monitor.py` | 446 | ✅ | 2 | ⚑ | xhs_cookie_bridge |
| `start_tunnel.py` | 86 | — | 0 |  |  |
| `subject_classifier.py` | 371 | ✅ | 1 |  |  |
| `subject_rules.py` | 98 | ✅ | 15 |  |  |
| `swire_group.py` | 448 | ✅ | 2 |  | database |
| `system_features_api.py` | 220 | ✅ | 1 |  | collector_auto_start, evaluation_system, local_ai_client, security_scanner |
| `system_guardian.py` | 227 | — | 0 |  |  |
| `system_health_api.py` | 541 | ✅ | 1 |  |  |
| `system_watchdog.py` | 278 | — | 0 | ⚑ |  |
| `topic_campaign.py` | 1224 | ✅ | 3 |  | cdp_helper, database, platform_adapters, subject_rules, xhs_runtime_state |
| `topic_monitor_policy.py` | 76 | — | 0 |  |  |
| `topic_note_detail_backfill.py` | 273 | — | 0 | ⚑ |  |
| `tunnel_guardian.py` | 251 | — | 0 | ⚑ |  |
| `update_reference.py` | 236 | — | 0 | ⚑ |  |
| `v4_upgrade/__init__.py` | 22 | ✅ | 15 |  | config |
| `v4_upgrade/adapters/__init__.py` | 15 | — | 0 |  |  |
| `v4_upgrade/adapters/auth_recovery.py` | 438 | ✅ | 2 |  | human_browser, risk_controller |
| `v4_upgrade/adapters/baidu_search.py` | 52 | — | 2 |  | base |
| `v4_upgrade/adapters/base.py` | 130 | — | 13 |  | config |
| `v4_upgrade/adapters/bing_search.py` | 41 | — | 2 |  | base |
| `v4_upgrade/adapters/collector_service.py` | 197 | — | 2 |  | v4_upgrade, persist, registry, risk_controller |
| `v4_upgrade/adapters/cookie_vault.py` | 265 | — | 2 |  |  |
| `v4_upgrade/adapters/dianping.py` | 45 | — | 2 |  | base |
| `v4_upgrade/adapters/doubao_search.py` | 87 | — | 2 |  | base |
| `v4_upgrade/adapters/douyin.py` | 291 | — | 3 |  | base, cookie_vault, human_browser |
| `v4_upgrade/adapters/google.py` | 225 | — | 1 |  | base, human_browser |
| `v4_upgrade/adapters/human_browser.py` | 331 | ✅ | 4 |  | cdp_helper |
| `v4_upgrade/adapters/instagram.py` | 234 | — | 1 |  | base, cookie_vault, human_browser |
| `v4_upgrade/adapters/persist.py` | 218 | — | 2 |  | base, config |
| `v4_upgrade/adapters/registry.py` | 113 | — | 6 |  | baidu_search, base, bing_search, dianping, doubao_search, douyin, google, instagram, smzdm, sogou_search, sogou_wechat, zhihu |
| `v4_upgrade/adapters/risk_controller.py` | 246 | ✅ | 4 |  | config |
| `v4_upgrade/adapters/smzdm.py` | 35 | — | 2 |  | base |
| `v4_upgrade/adapters/sogou_search.py` | 346 | — | 1 |  | base |
| `v4_upgrade/adapters/sogou_wechat.py` | 43 | — | 2 |  | base |
| `v4_upgrade/adapters/zhihu.py` | 51 | — | 2 |  | base |
| `v4_upgrade/ai_hub/__init__.py` | 14 | — | 0 |  |  |
| `v4_upgrade/ai_hub/routes.py` | 73 | — | 0 |  | v4_upgrade, service, shadow |
| `v4_upgrade/ai_hub/service.py` | 245 | — | 1 |  | ai_gateway_v570, database, function_registry, intelligence, config |
| `v4_upgrade/ai_hub/shadow.py` | 114 | — | 1 |  | config |
| `v4_upgrade/auth/__init__.py` | 19 | — | 0 |  | models |
| `v4_upgrade/auth/audit.py` | 91 | — | 0 |  | models |
| `v4_upgrade/auth/models.py` | 122 | ✅ | 5 |  | security, config |
| `v4_upgrade/auth/security.py` | 140 | ✅ | 4 |  | models, config |
| `v4_upgrade/auth/service.py` | 330 | ✅ | 1 |  | models, security, config |
| `v4_upgrade/blueprint.py` | 336 | — | 0 |  | v4_upgrade, auth_recovery, collector_service, registry, risk_controller, config |
| `v4_upgrade/collect/__init__.py` | 5 | — | 0 |  |  |
| `v4_upgrade/collect/routes.py` | 29 | — | 0 |  | v4_upgrade |
| `v4_upgrade/config.py` | 80 | ✅ | 12 |  |  |
| `v4_upgrade/console/__init__.py` | 5 | — | 0 |  |  |
| `v4_upgrade/console/routes.py` | 29 | — | 0 |  | v4_upgrade |
| `v4_upgrade/data_cleanup/__init__.py` | 5 | — | 0 |  |  |
| `v4_upgrade/data_cleanup/fix_publish_date.py` | 209 | — | 1 | ⚑ | config |
| `v4_upgrade/importer/__init__.py` | 7 | — | 0 |  |  |
| `v4_upgrade/importer/analyzer.py` | 219 | — | 2 |  | ark_llm, parser |
| `v4_upgrade/importer/parser.py` | 184 | — | 2 |  | config |
| `v4_upgrade/importer/service.py` | 164 | — | 0 |  | v4_upgrade, config, analyzer, parser |
| `v4_upgrade/settings/__init__.py` | 5 | — | 0 |  |  |
| `v4_upgrade/settings/routes.py` | 229 | — | 0 |  | v4_upgrade, models, security |
| `v4_upgrade/version_center/__init__.py` | 13 | — | 0 |  |  |
| `v4_upgrade/version_center/git_manager.py` | 415 | — | 4 |  |  |
| `v4_upgrade/version_center/routes.py` | 100 | — | 0 |  | v4_upgrade, git_manager |
| `v4_upgrade/version_center/watcher.py` | 43 | — | 0 |  | git_manager |
| `verify_system.py` | 73 | — | 0 |  |  |
| `verify_system_e2e.py` | 332 | — | 0 |  |  |
| `web_monitor.py` | 72 | ✅ | 1 |  |  |
| `web_monitor_v570.py` | 183 | ✅ | 1 |  | database |
| `web_topic_discovery.py` | 187 | — | 0 | ⚑ |  |
| `wechat_notifier.py` | 985 | — | 0 | ⚑ |  |
| `weekly_events.py` | 31 | ✅ | 1 |  |  |
| `weibo_login_manager.py` | 303 | ✅ | 1 | ⚑ |  |
| `xhs_cdp_collector.py` | 273 | — | 0 | ⚑ | cdp_helper |
| `xhs_cookie_bridge.py` | 564 | ✅ | 7 |  | ai_analyzer, cache_manager, database, network_adaptive, platform_adapters, reprocess |
| `xhs_runtime_state.py` | 255 | ✅ | 1 |  |  |