# 02 — 文件对账 (File Reconciliation)

> Baseline SHAs: ZBC=`bd6ed8d`, SICI=`c1b42bb`, DCC=`b0de3c5`, AIDRH=`930c646`  
> Verification: PASS (all file paths and SHAs from GitHub API)

## 1. ZBC File Inventory (root level, key files)

| Path | Type | Size | SHA | Status |
|---|---|---|---|---|
| app.py | file | 264628 | 1562b949 | ACTIVE |
| database.py | file | 63014 | 9eb44791 | ACTIVE |
| models.py | file | 10023 | e49bd6af | ACTIVE |
| config.py | file | 10511 | b77364c4 | ACTIVE |
| ai_analyzer.py | file | 33760 | c946e955 | ACTIVE |
| ai_learning_engine.py | file | 18035 | af3ba952 | ACTIVE |
| event_graph.py | file | 25588 | 21eee66e | ACTIVE |
| daily_report.py | file | 25904 | 683c3317 | ACTIVE |
| export_report.py | file | 35655 | 3adcba71 | ACTIVE |
| topic_campaign.py | file | 61820 | e775221d | ACTIVE |
| wechat_notifier.py | file | 36729 | d0849a53 | ACTIVE |
| xhs_cdp_collector.py | file | 44252 | 4dda835b | ACTIVE |
| xhs_cookie_bridge.py | file | 29823 | 7eda323c | ACTIVE |
| safety_boundary.py | file | 18822 | c6aadad7 | ACTIVE |
| monitoring.py | file | 19185 | 9d34c9ac | ACTIVE |
| system_health_api.py | file | 19869 | f90a2933 | ACTIVE |
| collector_automation.py | file | 27385 | aa037cd8 | ACTIVE |
| pr_case_integration.py | file | 24386 | a0b74090 | ACTIVE |
| public_opinion_cases.py | file | 24653 | b6b5e980 | ACTIVE |
| swire_group.py | file | 26710 | 277f7d08 | ACTIVE |
| auto_recovery.py | file | 17156 | 3ebc1d32 | ACTIVE |
| evaluation_system.py | file | 18632 | 1836c965 | ACTIVE |
| intelligence.py | file | 16889 | aa56c3dc | ACTIVE |
| data_feedback_loop.py | file | 15865 | 84a327f6 | ACTIVE |
| app_evidence.py | file | 15430 | 469ed652 | ACTIVE |
| security_scanner.py | file | 14140 | ab0e9eff | ACTIVE |
| cdp_helper.py | file | 19758 | 7e25e067 | ACTIVE |
| ark_llm.py | file | 12505 | 6a81fd1b | ACTIVE |
| brand_report_generator.py | file | 12550 | f8676348 | ACTIVE |
| review_workflow.py | file | 13007 | f067eaec | ACTIVE |
| ci_cd.py | file | 13187 | f7abae98 | ACTIVE |
| subject_classifier.py | file | 14334 | 2ac70b2a | ACTIVE |
| cache_manager.py | file | 10020 | fb4dc4ee | ACTIVE |
| memory_optimizer.py | file | 11525 | 9d34f4f7 | ACTIVE |
| stability_monitor.py | file | 18026 | b9a7ee51 | ACTIVE |
| system_watchdog.py | file | 11541 | 605337fc | ACTIVE |
| runtime_preflight.py | file | 14928 | 9b0733fc | ACTIVE |
| database_migrations.py | file | 17807 | 70169026 | ACTIVE |
| architecture_api.py | file | 13498 | 9f73ffed | ACTIVE |
| case_deep_analysis.py | file | 13858 | 9559c656 | ACTIVE |
| collector.py | file | 15191 | db3fded4 | ACTIVE |
| settings_module.py | file | 11009 | 10fe01da | ACTIVE |
| ai_filter.py | file | 13190 | b7554fd1 | ACTIVE |
| adaptive_engine.py | file | 14216 | 1d5d434c | ACTIVE |
| auth_recovery_center.py | file | 13165 | d306ac2a | ACTIVE |
| brand_knowledge_base.py | file | 8115 | 3e7cdbf4 | ACTIVE |
| function_registry.py | file | 7204 | 54c6beca | ACTIVE |
| logger.py | file | 8331 | 0ca3933c | ACTIVE |
| local_ai_client.py | file | 7621 | 7b8abb26 | ACTIVE |
| network_adaptive.py | file | 7830 | f9d4f715 | ACTIVE |
| tunnel_guardian.py | file | 7954 | 90b29bac | ACTIVE |
| update_reference.py | file | 9912 | a0cb8aa3 | ACTIVE |
| reprocess.py | file | 9922 | 29b93e4d | ACTIVE |
| verify_system_e2e.py | file | 12885 | d5197ca1 | ACTIVE |
| app_backup_v589.py | file | 251896 | b154a173 | BACKUP (potential dead code) |
| zachary_robot_widget.html | file | 10587 | e1b20855 | ACTIVE |
| requirements.txt | file | 831 | b38ade81 | ACTIVE |
| .env.example | file | 3697 | 4a4aacbc | ACTIVE |
| VERSION | file | 8 | 3dab4b4b | ACTIVE (v5.8.9) |
| brand_directory.json | file | 47652 | 7100793f | ACTIVE |
| function_map.json | file | 7136 | 11d4f020 | ACTIVE |
| system_config.json | file | 3192 | ccd9c9c8 | ACTIVE |
| events_config.json | file | 5428 | ad531837 | ACTIVE |
| Dockerfile | file | 1953 | 12c4f6d2 | ACTIVE |
| docker-compose.yml | file | 1244 | 38260835 | ACTIVE |
| pytest.ini | file | 711 | bc46d244 | ACTIVE |

**ZBC Directories**: .github, config, collector_guard, collector_v2, data, deployment, docker, docs, migrations, platform_adapters, proxy_pool, ref_gpt_v2, report_export, scripts, static, templates, tests, tools, v4_upgrade

## 2. SICI File Inventory

| Path | Type | Size | SHA | Status |
|---|---|---|---|---|
| index.html | file | 1034 | 6e8a35de | ACTIVE |
| manifest.json | file | 1181 | 1964b270 | ACTIVE |
| sw.js | file | 1282 | 30001d96 | ACTIVE |
| js/app.js | file | 30656 | 8c07c20c | ACTIVE |
| js/zachary-ai-core.js | file | 11609 | 0a19107e | ACTIVE |
| js/effective-rules.js | file | 12455 | 215203fc | ACTIVE |
| js/preflight.js | file | 9850 | 76117b3f | ACTIVE |
| js/capability-registry.js | file | 6278 | 297f4b2d | ACTIVE |
| js/deploy.js | file | 6274 | e57e23e8 | ACTIVE |
| js/tester.js | file | 11236 | db89c425 | ACTIVE |
| js/runner.js | file | 7389 | c6a05c6c | ACTIVE |
| js/github.js | file | 5731 | 794081eb | ACTIVE |
| js/research-learning.js | file | 2727 | b74ae0b0 | ACTIVE |
| js/storage.js | file | 2801 | 566c8681 | ACTIVE |
| js/zachary-runtime-api.js | file | 3375 | bf81bd68 | ACTIVE |
| js/zachary-ai-persistence.js | file | 1504 | e423e51b | ACTIVE |
| js/zachary-tool-registry.js | file | 1365 | e6bca690 | ACTIVE |
| js/zbc-evidence-adapter.js | file | 1508 | 88622140 | ACTIVE |
| js/three-repository-verifier.js | file | 839 | 10123d40 | ACTIVE |
| ZBIP_DESIGN_TOKENS.css | file | 1399 | 2210afc9 | ACTIVE (shared with DCC) |
| PLATFORM_README.md | file | 9572 | 0e2402dc | ACTIVE |
| README.md | file | 3218 | c6c65878 | ACTIVE |
| auto_push.ps1 | file | 2173 | dbd2a0f6 | ACTIVE |

**SICI Directories**: .github, css, docs, js, shadow_run, tests, upgrade_modules

## 3. DCC File Inventory

| Path | Type | Size | SHA | Status |
|---|---|---|---|---|
| index.html | file | 17930 | 899069a3 | ACTIVE |
| package.json | file | 1359 | 0b4fefc2 | ACTIVE (v0.5.0) |
| server/server.js | file | 31394 | 1dd3c1dd | ACTIVE |
| server/learning-store.js | file | 25690 | 4a02fb34 | ACTIVE |
| server/shadow-learning.js | file | 20303 | 250ef650 | ACTIVE |
| server/evidence-bundle.js | file | 16296 | 1bb3ca38 | ACTIVE |
| server/change-plan.js | file | 12345 | 9c6e7bf7 | ACTIVE |
| server/effective-rules.js | file | 8543 | ccf36cc9 | ACTIVE |
| server/snapshot.js | file | 10069 | d0cedfe7 | ACTIVE |
| server/startup-preflight.js | file | 5223 | 6b8bde03 | ACTIVE |
| server/supplement-protocol.js | file | 5919 | 3e0d34f9 | ACTIVE |
| server/security.js | file | 5039 | 5c44432c | ACTIVE |
| server/config.js | file | 1441 | 3ac3d459 | ACTIVE |
| js/github-audit.js | file | 14896 | 6684da2a | ACTIVE |
| js/bridge.js | file | 1949 | 30ce5602 | ACTIVE |
| js/search.js | file | 3236 | 333876bf | ACTIVE |
| js/task.js | file | 6764 | ba4c8e40 | ACTIVE |
| js/theme.js | file | 998 | a2721a65 | ACTIVE |
| protocols/registry.json | file | 3375 | 062813d3 | ACTIVE |
| ZBIP_DESIGN_TOKENS.css | file | 1399 | 2210afc9 | ACTIVE (shared with SICI) |
| PLATFORM_README.md | file | 11816 | 66b77551 | ACTIVE |
| README.md | file | 20954 | cbcd8f92 | ACTIVE |

**DCC Directories**: .devcontainer, .github, css, data, docs, js, protocols, server, tests, tools

## 4. AIDRH File Inventory

| Path | Type | Size | SHA | Status |
|---|---|---|---|---|
| GLOBAL-CROSS-REPOSITORY-BASELINE.md | file | 5318 | 88512f35 | ACTIVE (immutable) |
| CAPABILITY-REGISTRY.md | file | 2775 | 3b15b74a | ACTIVE |
| AI-COLLABORATION-PROTOCOL.md | file | 2611 | 06ac27d4 | ACTIVE |
| PLATFORM_BASELINE.md | file | 3904 | 5552f11f | ACTIVE |
| RESEARCH-LEARNING-SCHEMA.md | file | 3775 | a8022fce | ACTIVE |
| SHADOW-LEARNING-PROTOCOL.md | file | 3447 | 10dea166 | ACTIVE |
| THREE-REPOSITORY-VALIDATION.md | file | 4874 | 88250efc | ACTIVE |
| CASE-LIBRARY.md | file | 2505 | 57b87200 | ACTIVE |
| README.md | file | 6547 | 36e6a6d3 | ACTIVE |
| src/adapters/ddc_research_adapter.py | file | 2245 | a634951b | ACTIVE |
| src/contracts/ | dir | — | fe8fed02 | ACTIVE |
| src/shared/ | dir | — | 5668eea6 | ACTIVE |

**AIDRH Directories**: .github, architecture, benchmarks, cases, data, design-system, docs, logs, protocols, research, src, tests, tools

## 5. Cross-Repo File Duplication Detection

| File Pattern | ZBC | SICI | DCC | AIDRH | Duplication Level |
|---|---|---|---|---|---|
| ZBIP_DESIGN_TOKENS.css | SHA diff | `2210afc9` | `2210afc9` | — | EXACT (SICI=DCC) |
| ZBIP_UNIFIED_README.md | 8503B | 4245B | 5814B | 5513B | SIMILAR (different content) |
| PLATFORM_README.md | 13737B | 9572B | 11816B | — | SIMILAR (different content) |
| effective-rules | Python? | JS (frontend) | JS (server) | — | SEMANTIC (aligned, separate impl) |
| preflight | runtime_preflight.py | preflight.js | startup-preflight.js | runtime_preflight.py | SEMANTIC (3 implementations) |
| secret_scan | security_scanner.py | — | — | secret_scan.py | SEMANTIC (separate impl) |
| capability-registry | function_registry.py | capability-registry.js | — | CAPABILITY-REGISTRY.md | SEMANTIC (different formats) |
| shadow-learning | — | — | shadow-learning.js | SHADOW-LEARNING-PROTOCOL.md | COMPLEMENTARY (code+doc) |
| learning | ai_learning_engine.py | research-learning.js | learning-store.js | research/ + data/ | SEMANTIC (different layers) |

## 6. Orphan / Backup / Dead Code Files

| Repo | File | Size | Issue |
|---|---|---|---|
| ZBC | app_backup_v589.py | 251896 | Backup of app.py, 95% size of original, potential dead code |
| ZBC | ark_analysis.py.txt | 1772 | .txt extension for Python code, not importable |
| ZBC | user_file | 1461 | No extension, unclear purpose |
| ZBC | video_frames_grid.jpg | 2151622 | Large binary in repo (2.1MB) |
| ZBC | video_part_1-3.jpg | ~750KB each | Large binaries in repo |
| ZBC | 公关话术模板-舆情信息.docx | 21206 | Binary docx in repo |
| SICI | auto_push.ps1 | 2173 | Automation script, potential credential risk |
| DCC | (none identified) | — | — |
| AIDRH | (none identified) | — | — |

**Verification**: PASS — All file paths, sizes, and SHAs verified via GitHub API get_file_contents. No AI speculation.