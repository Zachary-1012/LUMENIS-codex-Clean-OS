# ZBC Phase 11 - Module Inventory & Function-Level Verification Report

> **Repository**: `D:\Taikoo-monitor-new` | **Branch**: `feat/zbc-full-upgrade-v1` | **HEAD**: `5e0ccd0`
> **Audit Date**: 2026-09-06 12:55 | **Scope**: All production `.py` files (excluding tests/.venv/node_modules/__pycache__/.trae-cn/99-ARCHIVE)

## 1. Executive Summary

| Metric | Value |
|--------|-------|
| Total modules scanned | **504** |
| Total functions | 4106 |
| Total classes | 375 |
| Total API routes | 589 |
| Stub functions | 6 |
| Modules with test coverage | 170 (33%) |

### Status Distribution

| Status | Count | % | Description |
|--------|-------|---|-------------|
| VERIFIED | 139 | 27% | Has implementation + referenced + tested/runnable |
| PARTIAL | 262 | 51% | Has implementation but incomplete (missing tests/exception handling/stubs) |
| BLOCKED | 0 | 0% | Cannot run / parse errors / no implementation |
| DEPRECATED | 10 | 1% | Marked legacy / has replacement / no new development |
| DELETE-CANDIDATE | 93 | 18% | Confirmed no runtime/API/migration dependency (marked only, not deleted) |

### Classification Distribution

| Classification | Count |
|----------------|-------|
| CORE | 108 |
| SCRATCH | 84 |
| INFRASTRUCTURE | 66 |
| COLLECTOR | 66 |
| UTILITY | 52 |
| AI | 27 |
| RESEARCH | 21 |
| DATA | 19 |
| OPERATIONS | 17 |
| API | 15 |
| REPORT | 15 |
| EVIDENCE | 8 |
| RISK | 6 |

## 2. Critical Deep-Dive: `app.py` Giant Monolith

`app.py` is a **5886-line** monolithic file containing the entire Flask application.

| Metric | Value |
|--------|-------|
| Lines | 5886 |
| Functions | 262 |
| Classes | 2 |
| API Routes | 188 |
| Route handler functions | 188 |
| Routes without try/except | **59** |
| Functions without return | **16** |

**Status: PARTIAL** — Reasons:

- 59 route handlers lack try/except
- 16 functions lack explicit return
- Monolithic 5886-line single file (violates SRP)
- 136 imports indicates excessive coupling
- Mixed concerns: routing + DB + business logic + auth in one file

> The route handlers without try/except represent unhandled exception risk. The monolithic structure makes targeted testing and incremental refactoring difficult.

## 3. Module Verification by Priority Group

Modules verified in strict priority order per task specification.

### 1. Collector (66 modules)

Status: VERIFIED=13, PARTIAL=53

| Module | Class | Funcs | Classes | Routes | Importers | Test | Status | Key Issues |
|--------|-------|-------|---------|--------|-----------|------|--------|------------|
| `browser_runtime/adapters/xhs_collector_bridge.py` | COLLECTOR | 3 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `collector.py` | COLLECTOR | 18 | 0 | 0 | 10 | Y | **VERIFIED** | all verification checks pass |
| `collector_auto_start.py` | COLLECTOR | 9 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_automation.py` | COLLECTOR | 19 | 1 | 0 | 3 | Y | **VERIFIED** | all verification checks pass |
| `collector_guard/analyzer.py` | COLLECTOR | 1 | 2 | 0 | 5 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_guard/checkpoint.py` | COLLECTOR | 10 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_guard/dlq_replay.py` | COLLECTOR | 10 | 1 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `collector_guard/guard.py` | COLLECTOR | 7 | 2 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `collector_guard/metrics.py` | COLLECTOR | 8 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_guard/queue_worker.py` | COLLECTOR | 6 | 1 | 0 | 0 | Y | **PARTIAL** | gaps: not imported/no routes/no main (orphaned) |
| `collector_guard/rate_limiter.py` | COLLECTOR | 9 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_guard/resource_guard.py` | COLLECTOR | 4 | 1 | 0 | 4 | Y | **PARTIAL** | gaps: no try/except |
| `collector_guard/risk_engine.py` | COLLECTOR | 12 | 1 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `collector_guard/runtime_switch.py` | COLLECTOR | 11 | 1 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `collector_guard/schedule_adapter.py` | COLLECTOR | 6 | 0 | 0 | 2 | Y | **PARTIAL** | gaps: no try/except |
| `collector_guard/state.py` | COLLECTOR | 1 | 1 | 0 | 5 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_guard/task_queue.py` | COLLECTOR | 8 | 1 | 0 | 0 | Y | **PARTIAL** | gaps: not imported/no routes/no main (orphaned) |
| `collector_guard_integration.py` | COLLECTOR | 5 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `collector_v2/base.py` | COLLECTOR | 8 | 3 | 0 | 33 | - | **PARTIAL** | gaps: 1 stub function(s); no dedicated test; contains NotImp |
| `collector_v2/browser_session.py` | COLLECTOR | 10 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_v2/official_info_scraper.py` | COLLECTOR | 9 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_v2/pipeline/deduplicate.py` | COLLECTOR | 12 | 1 | 0 | 4 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `collector_v2/pipeline/normalize.py` | COLLECTOR | 9 | 1 | 0 | 4 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_v2/pipeline/persist.py` | COLLECTOR | 9 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_v2/pipeline/spam_filter.py` | COLLECTOR | 4 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `collector_v2/pipeline/subject_filter.py` | COLLECTOR | 9 | 1 | 0 | 3 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_v2/run_live_engine.py` | COLLECTOR | 3 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_v2/run_profile.py` | COLLECTOR | 2 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_v2/run_xhs_live.py` | COLLECTOR | 1 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no return statements; no dedicated test |
| `collector_v2/scheduler/collector_job.py` | COLLECTOR | 15 | 3 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_v2/session/browser_session.py` | COLLECTOR | 9 | 2 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_v2/weibo/collector.py` | COLLECTOR | 12 | 1 | 0 | 10 | Y | **VERIFIED** | all verification checks pass |
| `collector_v2/xhs/client.py` | COLLECTOR | 11 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_v2/xhs/collector.py` | COLLECTOR | 10 | 1 | 0 | 10 | Y | **VERIFIED** | all verification checks pass |
| `collector_v2/xhs/live_engine.py` | COLLECTOR | 2 | 0 | 0 | 5 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_v2/xhs/models.py` | COLLECTOR | 0 | 2 | 0 | 11 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_v2/xhs/parser.py` | COLLECTOR | 7 | 1 | 0 | 3 | - | **PARTIAL** | gaps: no dedicated test |
| `collector_v2_integration.py` | COLLECTOR | 9 | 0 | 3 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `platform_adapters/base.py` | COLLECTOR | 8 | 3 | 0 | 33 | - | **PARTIAL** | gaps: no try/except; no dedicated test; contains NotImplemen |
| `platform_adapters/bilibili.py` | COLLECTOR | 10 | 1 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `platform_adapters/config.py` | COLLECTOR | 1 | 0 | 0 | 23 | Y | **VERIFIED** | all verification checks pass |
| `platform_adapters/douyin.py` | COLLECTOR | 10 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `platform_adapters/evidence_exporter.py` | COLLECTOR | 9 | 0 | 0 | 0 | Y | **PARTIAL** | gaps: not imported/no routes/no main (orphaned) |
| `platform_adapters/facebook.py` | COLLECTOR | 10 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `platform_adapters/health_center.py` | COLLECTOR | 4 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `platform_adapters/instagram.py` | COLLECTOR | 11 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `platform_adapters/rednote_policy.py` | COLLECTOR | 4 | 1 | 0 | 0 | Y | **PARTIAL** | gaps: no try/except; not imported/no routes/no main (orphane |
| `platform_adapters/registry.py` | COLLECTOR | 4 | 0 | 0 | 12 | Y | **PARTIAL** | gaps: no try/except |
| `platform_adapters/safe_collection.py` | COLLECTOR | 16 | 2 | 0 | 1 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `platform_adapters/scheduling/decision.py` | COLLECTOR | 12 | 3 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `platform_adapters/scheduling/gate.py` | COLLECTOR | 3 | 0 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `platform_adapters/scheduling/planner.py` | COLLECTOR | 11 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `platform_adapters/scheduling/policy.py` | COLLECTOR | 6 | 1 | 0 | 5 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `platform_adapters/scheduling/state_map.py` | COLLECTOR | 8 | 1 | 0 | 0 | Y | **PARTIAL** | gaps: no try/except; not imported/no routes/no main (orphane |
| `platform_adapters/scheduling/store.py` | COLLECTOR | 6 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `platform_adapters/weibo.py` | COLLECTOR | 10 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `platform_adapters/x_platform.py` | COLLECTOR | 10 | 1 | 0 | 3 | - | **PARTIAL** | gaps: no dedicated test |
| `platform_adapters/xhs.py` | COLLECTOR | 5 | 1 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (103 lines, 5 funcs): no dedicated  |
| `platform_adapters/xhs_app_topic.py` | COLLECTOR | 8 | 1 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (248 lines, 8 funcs): no dedicated  |
| `platform_adapters/zhihu.py` | COLLECTOR | 10 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/collector_service.py` | COLLECTOR | 8 | 0 | 0 | 0 | Y | **PARTIAL** | gaps: not imported/no routes/no main (orphaned) |
| `xhs_cdp_collector.py` | COLLECTOR | 28 | 0 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `xhs_collection_optimizer.py` | COLLECTOR | 28 | 3 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `xhs_cookie_bridge.py` | COLLECTOR | 35 | 0 | 0 | 11 | Y | **VERIFIED** | all verification checks pass |
| `xhs_p0_orchestrator.py` | COLLECTOR | 12 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `xhs_runtime_state.py` | COLLECTOR | 10 | 7 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |

### 2. Risk / Public Opinion (6 modules)

Status: VERIFIED=4, PARTIAL=2

| Module | Class | Funcs | Classes | Routes | Importers | Test | Status | Key Issues |
|--------|-------|-------|---------|--------|-----------|------|--------|------------|
| `alert_engine.py` | RISK | 13 | 0 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `event_graph.py` | RISK | 32 | 3 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `pr_case_engine.py` | RISK | 14 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `pr_case_integration.py` | RISK | 6 | 0 | 3 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `public_opinion_cases.py` | RISK | 7 | 1 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `risk_engine.py` | RISK | 2 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |

### 3. AI (27 modules)

Status: VERIFIED=6, PARTIAL=21

| Module | Class | Funcs | Classes | Routes | Importers | Test | Status | Key Issues |
|--------|-------|-------|---------|--------|-----------|------|--------|------------|
| `ad_intelligence/analytics/analyzer.py` | AI | 6 | 5 | 0 | 5 | - | **PARTIAL** | gaps: 1 stub function(s); no try/except; no dedicated test |
| `ad_intelligence/base.py` | AI | 3 | 4 | 0 | 33 | - | **PARTIAL** | gaps: no dedicated test |
| `ad_intelligence/models/ctr_predictor.py` | AI | 7 | 2 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `ad_intelligence/models/feature_engineer.py` | AI | 9 | 2 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `ad_intelligence/permission_gate.py` | AI | 11 | 2 | 0 | 4 | Y | **VERIFIED** | all verification checks pass |
| `ad_intelligence/platform_registry.py` | AI | 5 | 5 | 0 | 2 | Y | **PARTIAL** | gaps: no try/except |
| `ad_intelligence/platforms/factory.py` | AI | 6 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `ad_intelligence/platforms/jiguang.py` | AI | 12 | 3 | 0 | 3 | - | **PARTIAL** | gaps: no dedicated test |
| `ad_intelligence/platforms/meta_ads.py` | AI | 6 | 3 | 0 | 2 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `ad_intelligence/platforms/ocean_engine.py` | AI | 7 | 3 | 0 | 2 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `ad_intelligence/platforms/x_ads.py` | AI | 6 | 3 | 0 | 2 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `ad_intelligence/strategy/generator.py` | AI | 4 | 6 | 0 | 1 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `ai_analyzer.py` | AI | 14 | 0 | 0 | 8 | Y | **VERIFIED** | all verification checks pass |
| `ai_api.py` | AI | 21 | 0 | 19 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `ai_channel.py` | AI | 26 | 2 | 0 | 4 | Y | **VERIFIED** | all verification checks pass |
| `ai_filter.py` | AI | 7 | 0 | 0 | 3 | - | **PARTIAL** | gaps: no dedicated test |
| `ai_governance.py` | AI | 19 | 2 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `ai_learning_engine.py` | AI | 17 | 2 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `ai_resource_packs.py` | AI | 13 | 0 | 0 | 5 | Y | **VERIFIED** | all verification checks pass |
| `ark_llm.py` | AI | 10 | 0 | 0 | 3 | Y | **VERIFIED** | all verification checks pass |
| `intelligence.py` | AI | 31 | 0 | 0 | 16 | Y | **VERIFIED** | all verification checks pass |
| `local_ai_client.py` | AI | 10 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `scripts/ai_budget.py` | AI | 6 | 0 | 0 | 3 | - | **PARTIAL** | gaps: no dedicated test |
| `scripts/ai_gateway.py` | AI | 3 | 0 | 0 | 0 | Y | **PARTIAL** | gaps: not imported/no routes/no main (orphaned) |
| `v4_upgrade/ai_hub/routes.py` | AI | 7 | 0 | 7 | 5 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `v4_upgrade/ai_hub/service.py` | AI | 9 | 0 | 0 | 3 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/ai_hub/shadow.py` | AI | 7 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (114 lines, 7 funcs): no dedicated  |

### 4. Evidence / Evaluation (8 modules)

Status: VERIFIED=4, PARTIAL=3, DELETE-CANDIDATE=1

| Module | Class | Funcs | Classes | Routes | Importers | Test | Status | Key Issues |
|--------|-------|-------|---------|--------|-----------|------|--------|------------|
| `canonical_metrics.py` | EVIDENCE | 12 | 0 | 0 | 11 | Y | **VERIFIED** | all verification checks pass |
| `data_quality_gate.py` | EVIDENCE | 15 | 1 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `evaluation/agent_benchmark_contract.py` | EVIDENCE | 2 | 1 | 0 | 1 | Y | **PARTIAL** | gaps: no return statements |
| `evaluation/collection_benchmark.py` | EVIDENCE | 3 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | orphaned small module: no dedicated test; not imported/no ro |
| `evaluation_system.py` | EVIDENCE | 15 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `evidence_api.py` | EVIDENCE | 5 | 0 | 4 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `evidence_store.py` | EVIDENCE | 9 | 0 | 0 | 5 | Y | **VERIFIED** | all verification checks pass |
| `scripts/evidence_export.py` | EVIDENCE | 9 | 0 | 0 | 0 | Y | **VERIFIED** | all verification checks pass |

### 5. Report (15 modules)

Status: VERIFIED=7, PARTIAL=7, DELETE-CANDIDATE=1

| Module | Class | Funcs | Classes | Routes | Importers | Test | Status | Key Issues |
|--------|-------|-------|---------|--------|-----------|------|--------|------------|
| `brand_report_generator.py` | REPORT | 13 | 1 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `daily_report.py` | REPORT | 14 | 0 | 0 | 6 | Y | **VERIFIED** | all verification checks pass |
| `export_report.py` | REPORT | 19 | 0 | 7 | 1 | Y | **VERIFIED** | all verification checks pass |
| `report_api.py` | REPORT | 18 | 0 | 16 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `report_engine.py` | REPORT | 4 | 0 | 0 | 5 | Y | **VERIFIED** | all verification checks pass |
| `report_export/app_report_api_patch.py` | REPORT | 2 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | orphaned small module: no dedicated test; not imported/no ro |
| `report_export/report_engine.py` | REPORT | 12 | 0 | 0 | 5 | Y | **VERIFIED** | all verification checks pass |
| `report_filter.py` | REPORT | 6 | 0 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `scripts/export_report.py` | REPORT | 1 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `v4_upgrade/report_center/api.py` | REPORT | 4 | 0 | 3 | 1 | Y | **VERIFIED** | all verification checks pass |
| `v4_upgrade/report_center/cth_phrases.py` | REPORT | 4 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (167 lines, 4 funcs): no try/except |
| `v4_upgrade/report_center/report_generator.py` | REPORT | 18 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/report_center/standard_taxonomy.py` | REPORT | 13 | 8 | 0 | 4 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `v4_upgrade/report_center/word_pdf_export.py` | REPORT | 4 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/report_center/zbmp_phrases.py` | REPORT | 3 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (132 lines, 3 funcs): no dedicated  |

### 6. UI / API (15 modules)

Status: VERIFIED=1, PARTIAL=13, DELETE-CANDIDATE=1

| Module | Class | Funcs | Classes | Routes | Importers | Test | Status | Key Issues |
|--------|-------|-------|---------|--------|-----------|------|--------|------------|
| `...00-GOVERNANCE__path_backup__split_report_api.py` | API | 1 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | backup file, 0 importers |
| `app.py` | API | 262 | 2 | 188 | 4 | Y | **PARTIAL** | Giant monolith: 188 routes, 262 funcs, 59 routes without try |
| `architecture_api.py` | API | 22 | 0 | 22 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `auth_recovery_api.py` | API | 8 | 0 | 7 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `browser_runtime_api.py` | API | 3 | 0 | 2 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `browser_surface_api.py` | API | 31 | 0 | 27 | 1 | Y | **VERIFIED** | all verification checks pass |
| `collection_api.py` | API | 13 | 0 | 12 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `data_query_api.py` | API | 12 | 0 | 11 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `ic_routes.py` | API | 13 | 0 | 12 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `juguang_api.py` | API | 5 | 0 | 0 | 1 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `kos_routes.py` | API | 62 | 0 | 53 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `lumenis_agg_api.py` | API | 23 | 0 | 14 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `podcast_routes.py` | API | 14 | 0 | 9 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `system_features_api.py` | API | 16 | 0 | 16 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `system_health_api.py` | API | 18 | 0 | 3 | 2 | - | **PARTIAL** | gaps: no dedicated test |

### 7. Operations (17 modules)

Status: VERIFIED=6, PARTIAL=9, DELETE-CANDIDATE=2

| Module | Class | Funcs | Classes | Routes | Importers | Test | Status | Key Issues |
|--------|-------|-------|---------|--------|-----------|------|--------|------------|
| `account_keepalive/manager.py` | OPERATIONS | 9 | 4 | 0 | 4 | - | **PARTIAL** | gaps: no dedicated test |
| `auto_recovery.py` | OPERATIONS | 19 | 3 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `deployment/backup.py` | OPERATIONS | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | backup file, 0 importers |
| `deployment/deployment/µò░µì«σ║ôσñçΣ╗╜.py` | OPERATIONS | 5 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `deployment/deployment/σüÑσ║╖µúÇµƒÑ.py` | OPERATIONS | 8 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `deployment/health_check.py` | OPERATIONS | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 22 lines, 0 importers |
| `deployment/健康检查.py` | OPERATIONS | 8 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `deployment/数据库备份.py` | OPERATIONS | 5 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `monitor_pipeline.py` | OPERATIONS | 2 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `monitoring.py` | OPERATIONS | 19 | 5 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `runtime_bin.py` | OPERATIONS | 4 | 0 | 0 | 7 | Y | **PARTIAL** | gaps: no try/except |
| `runtime_guardian.py` | OPERATIONS | 72 | 12 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `runtime_preflight.py` | OPERATIONS | 14 | 0 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `scripts/runtime_switch_ops.py` | OPERATIONS | 1 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no return statements; no dedicated test |
| `stability_monitor.py` | OPERATIONS | 23 | 1 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `system_guardian.py` | OPERATIONS | 8 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `system_watchdog.py` | OPERATIONS | 6 | 1 | 0 | 0 | Y | **VERIFIED** | all verification checks pass |

### 8. Research / Knowledge (21 modules)

Status: VERIFIED=6, PARTIAL=11, DELETE-CANDIDATE=4

| Module | Class | Funcs | Classes | Routes | Importers | Test | Status | Key Issues |
|--------|-------|-------|---------|--------|-----------|------|--------|------------|
| `brand_knowledge_base.py` | RESEARCH | 11 | 1 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `collection_intelligence.py` | RESEARCH | 5 | 0 | 0 | 0 | Y | **PARTIAL** | gaps: no try/except; not imported/no routes/no main (orphane |
| `context_intelligence.py` | RESEARCH | 5 | 0 | 0 | 1 | Y | **PARTIAL** | gaps: no try/except |
| `learning_collector.py` | RESEARCH | 19 | 2 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `learning_persistence.py` | RESEARCH | 27 | 1 | 0 | 0 | Y | **PARTIAL** | gaps: not imported/no routes/no main (orphaned) |
| `podcast/intelligence/breakout.py` | RESEARCH | 1 | 1 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `podcast/intelligence/content_yield.py` | RESEARCH | 1 | 2 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `podcast/intelligence/episode_runtime.py` | RESEARCH | 3 | 2 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `podcast/intelligence/learning.py` | RESEARCH | 1 | 2 | 0 | 0 | - | **DELETE-CANDIDATE** | orphaned small module: no dedicated test; not imported/no ro |
| `podcast/intelligence/research_levels.py` | RESEARCH | 1 | 3 | 0 | 0 | - | **DELETE-CANDIDATE** | orphaned small module: no dedicated test; not imported/no ro |
| `podcast/intelligence/research_pipeline.py` | RESEARCH | 5 | 3 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (86 lines, 5 funcs): no try/except; |
| `podcast/intelligence/story_nodes.py` | RESEARCH | 1 | 2 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `podcast/intelligence/topic_score.py` | RESEARCH | 3 | 1 | 0 | 0 | - | **DELETE-CANDIDATE** | orphaned small module: no dedicated test; not imported/no ro |
| `podcast/intelligence/topic_scoring.py` | RESEARCH | 3 | 1 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `resource_library.py` | RESEARCH | 8 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (301 lines, 8 funcs): no dedicated  |
| `scripts/topic_cluster.py` | RESEARCH | 3 | 0 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `scripts/topic_words.py` | RESEARCH | 4 | 0 | 0 | 2 | Y | **PARTIAL** | gaps: no try/except |
| `topic_campaign.py` | RESEARCH | 45 | 0 | 16 | 2 | Y | **VERIFIED** | all verification checks pass |
| `topic_monitor_policy.py` | RESEARCH | 3 | 1 | 0 | 0 | - | **DELETE-CANDIDATE** | orphaned small module: no dedicated test; not imported/no ro |
| `topic_note_detail_backfill.py` | RESEARCH | 4 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `topic_snapshot.py` | RESEARCH | 4 | 1 | 0 | 1 | Y | **PARTIAL** | gaps: no try/except |

### 9. Core (108 modules)

Status: VERIFIED=29, PARTIAL=57, DEPRECATED=6, DELETE-CANDIDATE=16

| Module | Class | Funcs | Classes | Routes | Importers | Test | Status | Key Issues |
|--------|-------|-------|---------|--------|-----------|------|--------|------------|
| `..._path_backup/osai_engine_repository_registry.py` | CORE | 10 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `...VERNANCE/_path_backup/scripts_e2e_loop_check.py` | CORE | 2 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `..._backup/scripts_inventory_feature_crosscheck.py` | CORE | 3 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (140 lines, 3 funcs): no dedicated  |
| `...ackup/scripts_inventory_feature_final_verify.py` | CORE | 4 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (131 lines, 4 funcs): no dedicated  |
| `.../_path_backup/scripts_reconcile_capabilities.py` | CORE | 3 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `...OVERNANCE/_path_backup/scripts_shard_b_audit.py` | CORE | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 53 lines, 0 importers |
| `00-GOVERNANCE/_path_backup/tests__audit_system.py` | CORE | 2 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (145 lines, 2 funcs): no dedicated  |
| `...ERNANCE/_path_backup/tests__diag_cdp_subproc.py` | CORE | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 17 lines, 0 importers |
| `00-GOVERNANCE/_path_backup/tests__make_preview.py` | CORE | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 21 lines, 0 importers |
| `00-GOVERNANCE/_path_backup/tests__s07_scan.py` | CORE | 1 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | orphaned small module: no dedicated test; not imported/no ro |
| `...path_backup/tests_e2e_cross_core_convergence.py` | CORE | 1 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (182 lines, 1 funcs): no return sta |
| `...ANCE/_path_backup/tests_test_ai_channel_flag.py` | CORE | 32 | 5 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (194 lines, 32 funcs): no try/excep |
| `...OVERNANCE/_path_backup/tests_test_ai_degrade.py` | CORE | 7 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (56 lines, 7 funcs): no try/except; |
| `...ANCE/_path_backup/tests_test_compliance_gate.py` | CORE | 9 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (57 lines, 9 funcs): no try/except; |
| `...ERNANCE/_path_backup/tests_test_kol_analysis.py` | CORE | 8 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (93 lines, 8 funcs): no try/except; |
| `...NANCE/_path_backup/tests_test_report_special.py` | CORE | 8 | 2 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (61 lines, 8 funcs): no try/except; |
| `...NANCE/_path_backup/tests_test_resource_guard.py` | CORE | 11 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (83 lines, 11 funcs): no try/except |
| `...NCE/_path_backup/tests_test_schedule_adapter.py` | CORE | 12 | 1 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (95 lines, 12 funcs): no try/except |
| `.../_path_backup/tests_test_security_scanner_s2.py` | CORE | 5 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no try/except; no return statements; no dedicated test |
| `...NANCE/_path_backup/tests_test_topic_snapshot.py` | CORE | 6 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (71 lines, 6 funcs): no dedicated t |
| `00-GOVERNANCE/_path_backup/tests_test_v2_p0_2_3.py` | CORE | 19 | 3 | 0 | 0 | - | **PARTIAL** | gaps: no try/except; no return statements; no dedicated test |
| `...RNANCE/_path_backup/tests_test_v2_p0_modules.py` | CORE | 17 | 3 | 0 | 0 | - | **PARTIAL** | gaps: no try/except; no return statements; no dedicated test |
| `...ANCE/_path_backup/tests_test_v2_p0_remaining.py` | CORE | 18 | 8 | 0 | 0 | - | **PARTIAL** | gaps: no try/except; no return statements; no dedicated test |
| `...VERNANCE/_scan_output/build_feature_registry.py` | CORE | 5 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (420 lines, 5 funcs): no dedicated  |
| `00-GOVERNANCE/_scan_output/fast_scanner.py` | CORE | 2 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (219 lines, 2 funcs): no dedicated  |
| `00-GOVERNANCE/_scan_output/fix_canonical_data.py` | CORE | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 29 lines, 0 importers |
| `...OVERNANCE/_scan_output/fix_missing_os_import.py` | CORE | 0 | 0 | 0 | 0 | - | **PARTIAL** | script with top-level code only (no function structure), 66  |
| `00-GOVERNANCE/_scan_output/fix_osai_registry.py` | CORE | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 39 lines, 0 importers |
| `00-GOVERNANCE/_scan_output/hardcoded_scan_full.py` | CORE | 1 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | orphaned small module: no return statements; no dedicated te |
| `...ERNANCE/_scan_output/replace_hardcoded_paths.py` | CORE | 4 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (244 lines, 4 funcs): no dedicated  |
| `00-GOVERNANCE/_scan_output/shard_d_scanner.py` | CORE | 8 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `00-GOVERNANCE/_scan_output/update_subject_rules.py` | CORE | 0 | 0 | 0 | 0 | - | **PARTIAL** | script with top-level code only (no function structure), 65  |
| `adaptive_engine.py` | CORE | 14 | 3 | 0 | 3 | Y | **VERIFIED** | all verification checks pass |
| `agent_boundary.py` | CORE | 29 | 10 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `agent_runtime_adapter.py` | CORE | 12 | 1 | 0 | 0 | Y | **VERIFIED** | all verification checks pass |
| `app_evidence.py` | CORE | 20 | 0 | 8 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `app_refactor_blueprint.py` | CORE | 18 | 0 | 16 | 0 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `auth_recovery_center.py` | CORE | 15 | 4 | 0 | 3 | Y | **VERIFIED** | all verification checks pass |
| `bilibili_login_manager.py` | CORE | 8 | 1 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `brand_stats_recompute.py` | CORE | 3 | 0 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `canonical_data.py` | CORE | 23 | 1 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `case_ai_evaluate.py` | CORE | 5 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `case_deep_analysis.py` | CORE | 14 | 1 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `case_templates.py` | CORE | 4 | 0 | 0 | 2 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `cdp_helper.py` | CORE | 15 | 1 | 0 | 7 | Y | **VERIFIED** | all verification checks pass |
| `check_collection.py` | CORE | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 44 lines, 0 importers |
| `check_collection_detail.py` | CORE | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 53 lines, 0 importers |
| `check_db_dates.py` | CORE | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 38 lines, 0 importers |
| `check_empty_tables.py` | CORE | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 20 lines, 0 importers |
| `check_logs.py` | CORE | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 43 lines, 0 importers |
| `check_system.py` | CORE | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 41 lines, 0 importers |
| `check_warnings.py` | CORE | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 39 lines, 0 importers |
| `ci_cd.py` | CORE | 9 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `dev_exec_core.py` | CORE | 7 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `domain_isolation.py` | CORE | 6 | 1 | 0 | 0 | Y | **PARTIAL** | gaps: no try/except; not imported/no routes/no main (orphane |
| `emv.py` | CORE | 3 | 0 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `engineering_metrics.py` | CORE | 10 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `evaluate_system_timing.py` | CORE | 1 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (259 lines, 1 funcs): no dedicated  |
| `historical_data_importer.py` | CORE | 18 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `import_cookies.py` | CORE | 1 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (123 lines, 1 funcs): no dedicated  |
| `import_xhs_cookies.py` | CORE | 2 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (116 lines, 2 funcs): no dedicated  |
| `internal_browser.py` | CORE | 33 | 0 | 13 | 4 | Y | **VERIFIED** | all verification checks pass |
| `internal_browser_stream.py` | CORE | 19 | 2 | 2 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `kol_analysis.py` | CORE | 5 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `kos_attribution.py` | CORE | 3 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `kos_engine.py` | CORE | 31 | 0 | 0 | 6 | Y | **VERIFIED** | all verification checks pass |
| `kos_execution.py` | CORE | 6 | 0 | 0 | 4 | - | **PARTIAL** | gaps: no dedicated test |
| `kos_intel.py` | CORE | 10 | 0 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `kos_metrics.py` | CORE | 10 | 0 | 0 | 3 | - | **PARTIAL** | gaps: no dedicated test |
| `kos_ops.py` | CORE | 13 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `kos_paid.py` | CORE | 9 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `kos_professional.py` | CORE | 11 | 0 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `kos_report.py` | CORE | 5 | 0 | 0 | 1 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `kos_scenarios.py` | CORE | 5 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `lumenis_frontend.py` | CORE | 25 | 0 | 25 | 1 | Y | **VERIFIED** | all verification checks pass |
| `lumenis_skill_adapter.py` | CORE | 12 | 1 | 0 | 2 | Y | **DEPRECATED** | marked deprecated/legacy, importers=2 |
| `network_adaptive.py` | CORE | 10 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `openapi_spec.py` | CORE | 7 | 0 | 0 | 0 | Y | **PARTIAL** | gaps: no try/except; not imported/no routes/no main (orphane |
| `podcast_store.py` | CORE | 9 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `populate_empty_tables.py` | CORE | 5 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `production_evidence_contract.py` | CORE | 9 | 2 | 0 | 1 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `provider_registry.py` | CORE | 6 | 0 | 0 | 2 | Y | **DEPRECATED** | marked deprecated/legacy, importers=2 |
| `quick_check.py` | CORE | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 50 lines, 0 importers |
| `read_docx.py` | CORE | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 34 lines, 0 importers |
| `reprocess.py` | CORE | 8 | 0 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `resident_health.py` | CORE | 16 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `review_workflow.py` | CORE | 11 | 3 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (355 lines, 11 funcs): no dedicated |
| `run_production.py` | CORE | 1 | 0 | 0 | 0 | - | **DEPRECATED** | marked deprecated/legacy, importers=0 |
| `run_supervised.py` | CORE | 10 | 0 | 0 | 0 | - | **DEPRECATED** | marked deprecated/legacy, importers=0 |
| `security_scanner.py` | CORE | 12 | 1 | 0 | 4 | Y | **VERIFIED** | all verification checks pass |
| `skill_registry.py` | CORE | 15 | 5 | 0 | 2 | Y | **DEPRECATED** | marked deprecated/legacy, importers=2 |
| `start_tunnel.py` | CORE | 1 | 0 | 0 | 0 | - | **DEPRECATED** | marked deprecated/legacy, importers=0 |
| `subject_classifier.py` | CORE | 17 | 1 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `subject_context.py` | CORE | 17 | 4 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `subject_rules.py` | CORE | 15 | 0 | 0 | 18 | Y | **VERIFIED** | all verification checks pass |
| `swire_group.py` | CORE | 17 | 0 | 8 | 1 | Y | **VERIFIED** | all verification checks pass |
| `tunnel_guardian.py` | CORE | 9 | 1 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `ui_data_audit.py` | CORE | 6 | 2 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `update_reference.py` | CORE | 7 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `verify_system.py` | CORE | 0 | 0 | 0 | 0 | - | **PARTIAL** | script with top-level code only (no function structure), 73  |
| `verify_system_e2e.py` | CORE | 3 | 0 | 0 | 0 | - | **PARTIAL** | orphaned but substantial (332 lines, 3 funcs): no dedicated  |
| `video_intelligence.py` | CORE | 3 | 3 | 0 | 0 | Y | **PARTIAL** | gaps: not imported/no routes/no main (orphaned) |
| `web_monitor.py` | CORE | 9 | 0 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `web_monitor_v570.py` | CORE | 6 | 0 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `web_topic_discovery.py` | CORE | 5 | 0 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `wechat_notifier.py` | CORE | 45 | 9 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test; contains NotImplementedError |
| `weekly_events.py` | CORE | 5 | 0 | 0 | 1 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `weibo_login_manager.py` | CORE | 9 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |

### 10. Data (19 modules)

Status: VERIFIED=8, PARTIAL=5, DELETE-CANDIDATE=6

| Module | Class | Funcs | Classes | Routes | Importers | Test | Status | Key Issues |
|--------|-------|-------|---------|--------|-----------|------|--------|------------|
| `alembic/env.py` | DATA | 2 | 0 | 0 | 0 | - | **VERIFIED** | alembic environment config (invoked by alembic CLI) |
| `...d79_baseline_existing_54_tables_empty_stamp_.py` | DATA | 2 | 0 | 0 | 0 | - | **VERIFIED** | alembic migration version script |
| `config.py` | DATA | 17 | 1 | 0 | 23 | Y | **VERIFIED** | all verification checks pass |
| `data/check_db.py` | DATA | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 16 lines, 0 importers |
| `data/migrate_db.py` | DATA | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 32 lines, 0 importers |
| `data/parse_brands.py` | DATA | 0 | 0 | 0 | 0 | - | **PARTIAL** | script with top-level code only (no function structure), 85  |
| `data/test_persist.py` | DATA | 1 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | orphaned small module: no dedicated test; not imported/no ro |
| `data/verify_db.py` | DATA | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 27 lines, 0 importers |
| `data/verify_db2.py` | DATA | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 41 lines, 0 importers |
| `data/verify_final.py` | DATA | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 30 lines, 0 importers |
| `data_boundary.py` | DATA | 7 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `data_feedback_loop.py` | DATA | 12 | 1 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `database.py` | DATA | 60 | 0 | 0 | 34 | Y | **VERIFIED** | all verification checks pass |
| `database_migrations.py` | DATA | 19 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `models.py` | DATA | 6 | 23 | 0 | 11 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `proxy_pool/config.py` | DATA | 1 | 1 | 0 | 23 | Y | **VERIFIED** | all verification checks pass |
| `proxy_pool/models.py` | DATA | 3 | 1 | 0 | 11 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/auth/models.py` | DATA | 4 | 0 | 0 | 11 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/config.py` | DATA | 0 | 0 | 0 | 23 | Y | **PARTIAL** | script with top-level code only (no function structure), 91  |

### 11. Infrastructure (66 modules)

Status: VERIFIED=13, PARTIAL=50, DEPRECATED=2, DELETE-CANDIDATE=1

| Module | Class | Funcs | Classes | Routes | Importers | Test | Status | Key Issues |
|--------|-------|-------|---------|--------|-----------|------|--------|------------|
| `agent_security.py` | INFRASTRUCTURE | 5 | 0 | 0 | 1 | Y | **PARTIAL** | gaps: no try/except |
| `browser_discovery.py` | INFRASTRUCTURE | 9 | 0 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `browser_runtime/adapters/cdp_adapter.py` | INFRASTRUCTURE | 12 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `browser_runtime/adapters/playwright_adapter.py` | INFRASTRUCTURE | 13 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `browser_runtime/contract.py` | INFRASTRUCTURE | 16 | 7 | 0 | 4 | - | **PARTIAL** | gaps: no dedicated test |
| `browser_runtime/policy.py` | INFRASTRUCTURE | 6 | 3 | 0 | 5 | - | **PARTIAL** | gaps: no dedicated test |
| `browser_runtime/router.py` | INFRASTRUCTURE | 8 | 2 | 0 | 1 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `browser_surface.py` | INFRASTRUCTURE | 53 | 1 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `cache_manager.py` | INFRASTRUCTURE | 11 | 0 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `compliance_gate.py` | INFRASTRUCTURE | 7 | 1 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `contracts/lumenis_adapter.py` | INFRASTRUCTURE | 8 | 0 | 0 | 0 | Y | **PARTIAL** | gaps: not imported/no routes/no main (orphaned) |
| `core/repository_registry.py` | INFRASTRUCTURE | 20 | 0 | 0 | 11 | Y | **VERIFIED** | all verification checks pass |
| `function_registry.py` | INFRASTRUCTURE | 7 | 0 | 0 | 3 | Y | **VERIFIED** | all verification checks pass |
| `logger.py` | INFRASTRUCTURE | 20 | 0 | 0 | 0 | Y | **VERIFIED** | all verification checks pass |
| `memory_optimizer.py` | INFRASTRUCTURE | 14 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `permission_gate.py` | INFRASTRUCTURE | 36 | 8 | 0 | 4 | Y | **VERIFIED** | all verification checks pass |
| `proxy_pool/adapters.py` | INFRASTRUCTURE | 3 | 0 | 0 | 3 | - | **PARTIAL** | gaps: no dedicated test |
| `proxy_pool/health.py` | INFRASTRUCTURE | 2 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `proxy_pool/loader.py` | INFRASTRUCTURE | 1 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `proxy_pool/manager.py` | INFRASTRUCTURE | 15 | 2 | 0 | 4 | - | **PARTIAL** | gaps: no dedicated test |
| `repository_registry.py` | INFRASTRUCTURE | 20 | 1 | 0 | 11 | Y | **PARTIAL** | gaps: no try/except |
| `safety_boundary.py` | INFRASTRUCTURE | 18 | 3 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `schema_registry.py` | INFRASTRUCTURE | 5 | 0 | 0 | 0 | Y | **DEPRECATED** | marked deprecated/legacy, importers=0 |
| `security_boundary.py` | INFRASTRUCTURE | 46 | 7 | 0 | 0 | Y | **PARTIAL** | gaps: not imported/no routes/no main (orphaned) |
| `settings_module.py` | INFRASTRUCTURE | 10 | 0 | 8 | 1 | - | **DEPRECATED** | marked deprecated/legacy, importers=1 |
| `v4_upgrade/adapters/auth_recovery.py` | INFRASTRUCTURE | 18 | 0 | 0 | 0 | Y | **PARTIAL** | gaps: not imported/no routes/no main (orphaned) |
| `v4_upgrade/adapters/baidu_search.py` | INFRASTRUCTURE | 2 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/base.py` | INFRASTRUCTURE | 20 | 6 | 0 | 33 | - | **PARTIAL** | gaps: 1 stub function(s); no dedicated test |
| `v4_upgrade/adapters/base_backup_v589.py` | INFRASTRUCTURE | 9 | 4 | 0 | 0 | - | **DELETE-CANDIDATE** | backup file, 0 importers |
| `v4_upgrade/adapters/bilibili.py` | INFRASTRUCTURE | 10 | 1 | 0 | 2 | Y | **VERIFIED** | all verification checks pass |
| `v4_upgrade/adapters/bing_search.py` | INFRASTRUCTURE | 2 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/cookie_vault.py` | INFRASTRUCTURE | 8 | 0 | 0 | 9 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/dianping.py` | INFRASTRUCTURE | 2 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/doubao_search.py` | INFRASTRUCTURE | 4 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/douyin.py` | INFRASTRUCTURE | 16 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/dual_pool.py` | INFRASTRUCTURE | 26 | 7 | 0 | 0 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/facebook.py` | INFRASTRUCTURE | 9 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/google.py` | INFRASTRUCTURE | 7 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/human_browser.py` | INFRASTRUCTURE | 16 | 3 | 0 | 11 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/instagram.py` | INFRASTRUCTURE | 13 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/persist.py` | INFRASTRUCTURE | 11 | 0 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/registry.py` | INFRASTRUCTURE | 9 | 1 | 0 | 12 | Y | **VERIFIED** | all verification checks pass |
| `v4_upgrade/adapters/risk_controller.py` | INFRASTRUCTURE | 15 | 2 | 0 | 3 | Y | **VERIFIED** | all verification checks pass |
| `v4_upgrade/adapters/smzdm.py` | INFRASTRUCTURE | 2 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/sogou_search.py` | INFRASTRUCTURE | 14 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/sogou_wechat.py` | INFRASTRUCTURE | 2 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/weibo.py` | INFRASTRUCTURE | 10 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/x_platform.py` | INFRASTRUCTURE | 9 | 1 | 0 | 4 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/adapters/zhihu.py` | INFRASTRUCTURE | 13 | 1 | 0 | 2 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/auth/audit.py` | INFRASTRUCTURE | 3 | 0 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/auth/security.py` | INFRASTRUCTURE | 8 | 0 | 0 | 6 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/auth/service.py` | INFRASTRUCTURE | 19 | 0 | 0 | 3 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/auth/workspace.py` | INFRASTRUCTURE | 9 | 0 | 0 | 1 | Y | **VERIFIED** | all verification checks pass |
| `v4_upgrade/blueprint.py` | INFRASTRUCTURE | 29 | 0 | 27 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/collect/routes.py` | INFRASTRUCTURE | 2 | 0 | 1 | 5 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/console/routes.py` | INFRASTRUCTURE | 3 | 0 | 2 | 5 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/data_cleanup/fix_publish_date.py` | INFRASTRUCTURE | 6 | 0 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/global_bil.py` | INFRASTRUCTURE | 2 | 0 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/importer/analyzer.py` | INFRASTRUCTURE | 13 | 1 | 0 | 5 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/importer/parser.py` | INFRASTRUCTURE | 8 | 1 | 0 | 3 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/importer/service.py` | INFRASTRUCTURE | 4 | 0 | 2 | 3 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/settings/routes.py` | INFRASTRUCTURE | 15 | 0 | 14 | 5 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/unified_logger.py` | INFRASTRUCTURE | 15 | 1 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/version_center/git_manager.py` | INFRASTRUCTURE | 24 | 1 | 0 | 4 | - | **PARTIAL** | gaps: no dedicated test |
| `v4_upgrade/version_center/routes.py` | INFRASTRUCTURE | 9 | 0 | 9 | 5 | - | **PARTIAL** | gaps: no try/except; no dedicated test |
| `v4_upgrade/version_center/watcher.py` | INFRASTRUCTURE | 2 | 0 | 0 | 1 | - | **PARTIAL** | gaps: no dedicated test |

### 12. Utility (52 modules)

Status: VERIFIED=11, PARTIAL=31, DEPRECATED=2, DELETE-CANDIDATE=8

| Module | Class | Funcs | Classes | Routes | Importers | Test | Status | Key Issues |
|--------|-------|-------|---------|--------|-----------|------|--------|------------|
| `audit/get_schemas.py` | UTILITY | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 45 lines, 0 importers |
| `audit/scan_refs.py` | UTILITY | 4 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `audit/summarize_schemas.py` | UTILITY | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 35 lines, 0 importers |
| `audit/validate_output.py` | UTILITY | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 20 lines, 0 importers |
| `...ference/apple-ui-reference/raw/build_catalog.py` | UTILITY | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 42 lines, 0 importers |
| `docs/reference/apple-ui-reference/raw/build_db.py` | UTILITY | 1 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test; not imported/no routes/no |
| `...rence/ui-research/analysis-0901-gpt/ef_sheet.py` | UTILITY | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 21 lines, 0 importers |
| `...nce/ui-research/analysis-0901-gpt/make_sheet.py` | UTILITY | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 41 lines, 0 importers |
| `...ce/ui-research/analysis-0901-gpt/trans_sheet.py` | UTILITY | 0 | 0 | 0 | 0 | - | **DELETE-CANDIDATE** | ad-hoc script, top-level code only, 37 lines, 0 importers |
| `scripts/app_closure_audit.py` | UTILITY | 2 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/backup_db.py` | UTILITY | 4 | 0 | 0 | 0 | Y | **DELETE-CANDIDATE** | backup file, 0 importers |
| `scripts/batch_hardcoded_cleanup.py` | UTILITY | 7 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/brand_insight.py` | UTILITY | 7 | 0 | 0 | 1 | Y | **VERIFIED** | utility module: all checks pass |
| `scripts/campaign_plan.py` | UTILITY | 4 | 0 | 0 | 1 | Y | **VERIFIED** | utility module: all checks pass |
| `scripts/check_system.py` | UTILITY | 1 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no return statements; no dedicated test |
| `scripts/collect_now.py` | UTILITY | 1 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/daily_git_sync.py` | UTILITY | 3 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/dev_ai.py` | UTILITY | 3 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/dlq_ops.py` | UTILITY | 1 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no return statements; no dedicated test |
| `scripts/e2e_loop_check.py` | UTILITY | 2 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/github_upgrade_check.py` | UTILITY | 3 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/idea_generator.py` | UTILITY | 16 | 0 | 0 | 5 | Y | **VERIFIED** | utility module: all checks pass |
| `scripts/init_database_data.py` | UTILITY | 7 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no try/except; no dedicated test |
| `scripts/init_db.py` | UTILITY | 1 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no return statements; no dedicated test |
| `scripts/inventory/asset_scan.py` | UTILITY | 4 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test; not imported/no routes/no |
| `scripts/inventory/build_asset_registry.py` | UTILITY | 6 | 0 | 0 | 0 | - | **DEPRECATED** | marked deprecated/legacy, importers=0 |
| `scripts/inventory/feature_crosscheck.py` | UTILITY | 3 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test; not imported/no routes/no |
| `scripts/inventory/feature_final_verify.py` | UTILITY | 4 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test; not imported/no routes/no |
| `scripts/json_repair.py` | UTILITY | 11 | 0 | 0 | 1 | Y | **VERIFIED** | utility module: all checks pass |
| `scripts/lean_footprint.py` | UTILITY | 7 | 0 | 0 | 0 | Y | **VERIFIED** | utility module: all checks pass |
| `scripts/license_audit.py` | UTILITY | 2 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/localization_guard.py` | UTILITY | 2 | 0 | 0 | 1 | Y | **VERIFIED** | utility module: all checks pass |
| `scripts/marketing_calendar.py` | UTILITY | 13 | 0 | 0 | 5 | Y | **VERIFIED** | utility module: all checks pass |
| `scripts/observatory_feed.py` | UTILITY | 5 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/osai_module_graph_shardB.py` | UTILITY | 1 | 0 | 0 | 0 | - | **DEPRECATED** | marked deprecated/legacy, importers=0 |
| `scripts/perspective_adapter.py` | UTILITY | 4 | 0 | 0 | 0 | Y | **VERIFIED** | utility module: all checks pass |
| `scripts/pitch_export.py` | UTILITY | 5 | 0 | 0 | 1 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/pitch_parser.py` | UTILITY | 14 | 0 | 0 | 2 | Y | **VERIFIED** | utility module: all checks pass |
| `scripts/production_baseline_check.py` | UTILITY | 7 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/prompt_registry.py` | UTILITY | 3 | 0 | 0 | 1 | Y | **VERIFIED** | utility module: all checks pass |
| `scripts/quality_audit.py` | UTILITY | 2 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/run_core_regression.py` | UTILITY | 1 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/social_ops.py` | UTILITY | 4 | 0 | 0 | 1 | - | **PARTIAL** | utility module: no try/except; no dedicated test |
| `scripts/stability_fix.py` | UTILITY | 4 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/staging_setup.py` | UTILITY | 2 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/start_resident_browsers.py` | UTILITY | 8 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/sync_v4_owner_password.py` | UTILITY | 2 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/sync_xhs_cookie_from_cdp.py` | UTILITY | 3 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/video_script.py` | UTILITY | 5 | 0 | 0 | 1 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/visualization_quality_gate.py` | UTILITY | 2 | 0 | 0 | 1 | Y | **VERIFIED** | utility module: all checks pass |
| `scripts/warehouse_sync_monitor.py` | UTILITY | 3 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no dedicated test |
| `scripts/zell_trace.py` | UTILITY | 8 | 0 | 0 | 0 | - | **PARTIAL** | utility module: no try/except; no dedicated test |

## 4. SCRATCH / DEBUG Files (_prefix)

Total SCRATCH files: **84**

All `_`-prefixed files are classified as SCRATCH/DEBUG. Those with 0 importers are additionally marked DELETE-CANDIDATE.

| File | Lines | Status | Importers |
|------|-------|--------|-----------|
| `00-GOVERNANCE\_path_backup\_split_report_api.py` | 147 | DELETE-CANDIDATE | 0 |
| `00-GOVERNANCE\_t10_db_audit.py` | 34 | DELETE-CANDIDATE | 0 |
| `00-GOVERNANCE\_t10_evidence_test.py` | 14 | DELETE-CANDIDATE | 0 |
| `_apply_api_audit_fixes.py` | 139 | DELETE-CANDIDATE | 0 |
| `_apply_migration_10.py` | 66 | DELETE-CANDIDATE | 0 |
| `_audit_backups.py` | 80 | DELETE-CANDIDATE | 0 |
| `_audit_historical.py` | 177 | DELETE-CANDIDATE | 0 |
| `_db_audit.py` | 27 | DELETE-CANDIDATE | 0 |
| `_db_inspect.py` | 40 | DELETE-CANDIDATE | 0 |
| `_debug_x.py` | 94 | DELETE-CANDIDATE | 0 |
| `_debug_x_v2.py` | 76 | DELETE-CANDIDATE | 0 |
| `_debug_x_v3.py` | 130 | DELETE-CANDIDATE | 0 |
| `_debug_x_v4.py` | 45 | DELETE-CANDIDATE | 0 |
| `_douyin_detail_debug.py` | 46 | DELETE-CANDIDATE | 0 |
| `_douyin_render_walk.py` | 63 | DELETE-CANDIDATE | 0 |
| `_douyin_ssr_debug.py` | 75 | DELETE-CANDIDATE | 0 |
| `_douyin_struct.py` | 62 | DELETE-CANDIDATE | 0 |
| `_open_login_pages.py` | 30 | DELETE-CANDIDATE | 0 |
| `_parse_jiguang_cookie.py` | 145 | DELETE-CANDIDATE | 0 |
| `_parse_x_cookie.py` | 86 | DELETE-CANDIDATE | 0 |
| `_parse_x_cookie_v2.py` | 109 | DELETE-CANDIDATE | 0 |
| `_patch_ai_channel.py` | 176 | DELETE-CANDIDATE | 0 |
| `_phase13_adapt.py` | 222 | DELETE-CANDIDATE | 0 |
| `_shardC_add_csrf.py` | 85 | DELETE-CANDIDATE | 0 |
| `_shardC_add_escape.py` | 64 | DELETE-CANDIDATE | 0 |
| `_shardC_db_audit.py` | 44 | DELETE-CANDIDATE | 0 |
| `_shardC_enhance_overview.py` | 116 | DELETE-CANDIDATE | 0 |
| `_shardC_enhance_workspace.py` | 114 | DELETE-CANDIDATE | 0 |
| `_shardC_insert_security.py` | 53 | DELETE-CANDIDATE | 0 |
| `_shardC_patch_css.py` | 18 | DELETE-CANDIDATE | 0 |
| `_shardC_patch_css2.py` | 17 | DELETE-CANDIDATE | 0 |
| `_smoke_test_importer.py` | 50 | DELETE-CANDIDATE | 0 |
| `_split_report_api.py` | 147 | DELETE-CANDIDATE | 0 |
| `_t7_db_inspect.py` | 112 | DELETE-CANDIDATE | 0 |
| `_t7_db_inspect2.py` | 63 | DELETE-CANDIDATE | 0 |
| `_tmp_check_core.py` | 17 | DELETE-CANDIDATE | 0 |
| `_tmp_extract.py` | 26 | DELETE-CANDIDATE | 0 |
| `_verify_jiguang.py` | 27 | DELETE-CANDIDATE | 0 |
| `_verify_x.py` | 22 | DELETE-CANDIDATE | 0 |
| `_verify_x_adapter.py` | 20 | DELETE-CANDIDATE | 0 |
| `_verify_x_final.py` | 124 | DELETE-CANDIDATE | 0 |
| `_verify_x_live.py` | 120 | DELETE-CANDIDATE | 0 |
| `account_keepalive\__init__.py` | 11 | VERIFIED | 0 |
| `ad_intelligence\__init__.py` | 42 | VERIFIED | 0 |
| `ad_intelligence\analytics\__init__.py` | 12 | VERIFIED | 0 |
| `ad_intelligence\models\__init__.py` | 13 | VERIFIED | 0 |
| `ad_intelligence\platforms\__init__.py` | 20 | VERIFIED | 0 |
| `ad_intelligence\strategy\__init__.py` | 13 | VERIFIED | 0 |
| `audit\_batch2_smoke.py` | 127 | DELETE-CANDIDATE | 0 |
| `audit\_check_status.py` | 24 | DELETE-CANDIDATE | 0 |
| `audit\_count_tables.py` | 9 | DELETE-CANDIDATE | 0 |
| `audit\_filter_batch2.py` | 26 | DELETE-CANDIDATE | 0 |
| `audit\_filter_batch3.py` | 124 | DELETE-CANDIDATE | 0 |
| `audit\_fix_hardcoded_paths.py` | 27 | DELETE-CANDIDATE | 0 |
| `audit\_list_partial.py` | 14 | DELETE-CANDIDATE | 0 |
| `audit\_module_scanner.py` | 303 | DELETE-CANDIDATE | 0 |
| `audit\_verify_batch1.py` | 623 | DELETE-CANDIDATE | 0 |
| `browser_runtime\__init__.py` | 34 | VERIFIED | 0 |
| `browser_runtime\adapters\__init__.py` | 2 | VERIFIED | 0 |
| `collector_guard\__init__.py` | 32 | VERIFIED | 0 |
| `collector_v2\__init__.py` | 11 | VERIFIED | 0 |
| `collector_v2\pipeline\__init__.py` | 15 | VERIFIED | 0 |
| `collector_v2\scheduler\__init__.py` | 5 | VERIFIED | 0 |
| `collector_v2\session\__init__.py` | 4 | VERIFIED | 0 |
| `collector_v2\weibo\__init__.py` | 5 | VERIFIED | 0 |
| `collector_v2\xhs\__init__.py` | 6 | VERIFIED | 0 |
| `contracts\__init__.py` | 1 | VERIFIED | 0 |
| `core\__init__.py` | 45 | VERIFIED | 0 |
| `platform_adapters\__init__.py` | 31 | VERIFIED | 0 |
| `platform_adapters\scheduling\__init__.py` | 38 | VERIFIED | 0 |
| `proxy_pool\__init__.py` | 17 | VERIFIED | 0 |
| `scripts\_prod_dep_check.py` | 19 | DELETE-CANDIDATE | 0 |
| `scripts\_zbc_phase7_verify.py` | 48 | DELETE-CANDIDATE | 0 |
| `v4_upgrade\__init__.py` | 22 | VERIFIED | 0 |
| `v4_upgrade\adapters\__init__.py` | 15 | VERIFIED | 0 |
| `v4_upgrade\ai_hub\__init__.py` | 14 | VERIFIED | 0 |
| `v4_upgrade\auth\__init__.py` | 19 | VERIFIED | 0 |
| `v4_upgrade\collect\__init__.py` | 5 | VERIFIED | 0 |
| `v4_upgrade\console\__init__.py` | 5 | VERIFIED | 0 |
| `v4_upgrade\data_cleanup\__init__.py` | 5 | VERIFIED | 0 |
| `v4_upgrade\importer\__init__.py` | 7 | VERIFIED | 0 |
| `v4_upgrade\report_center\__init__.py` | 41 | VERIFIED | 0 |
| `v4_upgrade\settings\__init__.py` | 5 | VERIFIED | 0 |
| `v4_upgrade\version_center\__init__.py` | 13 | VERIFIED | 0 |

## 5. DELETE-CANDIDATE Inventory (Marked Only — NOT Deleted)

Total DELETE-CANDIDATE: **93**

> These modules have **zero runtime importers, no API routes, no migration dependencies, and no test references**. Safe candidates for removal after user confirmation. **No files have been deleted.**

| # | File | Lines | Funcs | Classification | Evidence |
|---|------|-------|-------|----------------|----------|
| 1 | `00-GOVERNANCE\_path_backup\00-GOVERNANCE__path_backup__split_report_api.py` | 146 | 1 | API | backup file, 0 importers |
| 2 | `00-GOVERNANCE\_path_backup\_split_report_api.py` | 147 | 1 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 3 | `00-GOVERNANCE\_path_backup\scripts_shard_b_audit.py` | 53 | 0 | CORE | ad-hoc script, top-level code only, 53 lines, 0 importers |
| 4 | `00-GOVERNANCE\_path_backup\tests__diag_cdp_subproc.py` | 17 | 0 | CORE | ad-hoc script, top-level code only, 17 lines, 0 importers |
| 5 | `00-GOVERNANCE\_path_backup\tests__make_preview.py` | 21 | 0 | CORE | ad-hoc script, top-level code only, 21 lines, 0 importers |
| 6 | `00-GOVERNANCE\_path_backup\tests__s07_scan.py` | 42 | 1 | CORE | orphaned small module: no dedicated test; not imported/no routes/no ma |
| 7 | `00-GOVERNANCE\_scan_output\fix_canonical_data.py` | 29 | 0 | CORE | ad-hoc script, top-level code only, 29 lines, 0 importers |
| 8 | `00-GOVERNANCE\_scan_output\fix_osai_registry.py` | 39 | 0 | CORE | ad-hoc script, top-level code only, 39 lines, 0 importers |
| 9 | `00-GOVERNANCE\_scan_output\hardcoded_scan_full.py` | 97 | 1 | CORE | orphaned small module: no return statements; no dedicated test; not im |
| 10 | `00-GOVERNANCE\_t10_db_audit.py` | 34 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 11 | `00-GOVERNANCE\_t10_evidence_test.py` | 14 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 12 | `_apply_api_audit_fixes.py` | 139 | 1 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 13 | `_apply_migration_10.py` | 66 | 1 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 14 | `_audit_backups.py` | 80 | 2 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 15 | `_audit_historical.py` | 177 | 1 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 16 | `_db_audit.py` | 27 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 17 | `_db_inspect.py` | 40 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 18 | `_debug_x.py` | 94 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 19 | `_debug_x_v2.py` | 76 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 20 | `_debug_x_v3.py` | 130 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 21 | `_debug_x_v4.py` | 45 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 22 | `_douyin_detail_debug.py` | 46 | 1 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 23 | `_douyin_render_walk.py` | 63 | 1 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 24 | `_douyin_ssr_debug.py` | 75 | 1 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 25 | `_douyin_struct.py` | 62 | 1 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 26 | `_open_login_pages.py` | 30 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 27 | `_parse_jiguang_cookie.py` | 145 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 28 | `_parse_x_cookie.py` | 86 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 29 | `_parse_x_cookie_v2.py` | 109 | 1 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 30 | `_patch_ai_channel.py` | 176 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 31 | `_phase13_adapt.py` | 222 | 4 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 32 | `_shardC_add_csrf.py` | 85 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 33 | `_shardC_add_escape.py` | 64 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 34 | `_shardC_db_audit.py` | 44 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 35 | `_shardC_enhance_overview.py` | 116 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 36 | `_shardC_enhance_workspace.py` | 114 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 37 | `_shardC_insert_security.py` | 53 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 38 | `_shardC_patch_css.py` | 18 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 39 | `_shardC_patch_css2.py` | 17 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 40 | `_smoke_test_importer.py` | 50 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 41 | `_split_report_api.py` | 147 | 1 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 42 | `_t7_db_inspect.py` | 112 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 43 | `_t7_db_inspect2.py` | 63 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 44 | `_tmp_check_core.py` | 17 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 45 | `_tmp_extract.py` | 26 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 46 | `_verify_jiguang.py` | 27 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 47 | `_verify_x.py` | 22 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 48 | `_verify_x_adapter.py` | 20 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 49 | `_verify_x_final.py` | 124 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 50 | `_verify_x_live.py` | 120 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 51 | `audit\_batch2_smoke.py` | 127 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 52 | `audit\_check_status.py` | 24 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 53 | `audit\_count_tables.py` | 9 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 54 | `audit\_filter_batch2.py` | 26 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 55 | `audit\_filter_batch3.py` | 124 | 1 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 56 | `audit\_fix_hardcoded_paths.py` | 27 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 57 | `audit\_list_partial.py` | 14 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 58 | `audit\_module_scanner.py` | 303 | 9 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 59 | `audit\_verify_batch1.py` | 623 | 14 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 60 | `audit\get_schemas.py` | 45 | 0 | UTILITY | ad-hoc script, top-level code only, 45 lines, 0 importers |
| 61 | `audit\summarize_schemas.py` | 35 | 0 | UTILITY | ad-hoc script, top-level code only, 35 lines, 0 importers |
| 62 | `audit\validate_output.py` | 20 | 0 | UTILITY | ad-hoc script, top-level code only, 20 lines, 0 importers |
| 63 | `check_collection.py` | 44 | 0 | CORE | ad-hoc script, top-level code only, 44 lines, 0 importers |
| 64 | `check_collection_detail.py` | 53 | 0 | CORE | ad-hoc script, top-level code only, 53 lines, 0 importers |
| 65 | `check_db_dates.py` | 38 | 0 | CORE | ad-hoc script, top-level code only, 38 lines, 0 importers |
| 66 | `check_empty_tables.py` | 20 | 0 | CORE | ad-hoc script, top-level code only, 20 lines, 0 importers |
| 67 | `check_logs.py` | 43 | 0 | CORE | ad-hoc script, top-level code only, 43 lines, 0 importers |
| 68 | `check_system.py` | 41 | 0 | CORE | ad-hoc script, top-level code only, 41 lines, 0 importers |
| 69 | `check_warnings.py` | 39 | 0 | CORE | ad-hoc script, top-level code only, 39 lines, 0 importers |
| 70 | `data\check_db.py` | 16 | 0 | DATA | ad-hoc script, top-level code only, 16 lines, 0 importers |
| 71 | `data\migrate_db.py` | 32 | 0 | DATA | ad-hoc script, top-level code only, 32 lines, 0 importers |
| 72 | `data\test_persist.py` | 39 | 1 | DATA | orphaned small module: no dedicated test; not imported/no routes/no ma |
| 73 | `data\verify_db.py` | 27 | 0 | DATA | ad-hoc script, top-level code only, 27 lines, 0 importers |
| 74 | `data\verify_db2.py` | 41 | 0 | DATA | ad-hoc script, top-level code only, 41 lines, 0 importers |
| 75 | `data\verify_final.py` | 30 | 0 | DATA | ad-hoc script, top-level code only, 30 lines, 0 importers |
| 76 | `deployment\backup.py` | 13 | 0 | OPERATIONS | backup file, 0 importers |
| 77 | `deployment\health_check.py` | 22 | 0 | OPERATIONS | ad-hoc script, top-level code only, 22 lines, 0 importers |
| 78 | `docs\reference\apple-ui-reference\raw\build_catalog.py` | 42 | 0 | UTILITY | ad-hoc script, top-level code only, 42 lines, 0 importers |
| 79 | `docs\reference\ui-research\analysis-0901-gpt\ef_sheet.py` | 21 | 0 | UTILITY | ad-hoc script, top-level code only, 21 lines, 0 importers |
| 80 | `docs\reference\ui-research\analysis-0901-gpt\make_sheet.py` | 41 | 0 | UTILITY | ad-hoc script, top-level code only, 41 lines, 0 importers |
| 81 | `docs\reference\ui-research\analysis-0901-gpt\trans_sheet.py` | 37 | 0 | UTILITY | ad-hoc script, top-level code only, 37 lines, 0 importers |
| 82 | `evaluation\collection_benchmark.py` | 42 | 3 | EVIDENCE | orphaned small module: no dedicated test; not imported/no routes/no ma |
| 83 | `podcast\intelligence\learning.py` | 31 | 1 | RESEARCH | orphaned small module: no dedicated test; not imported/no routes/no ma |
| 84 | `podcast\intelligence\research_levels.py` | 36 | 1 | RESEARCH | orphaned small module: no dedicated test; not imported/no routes/no ma |
| 85 | `podcast\intelligence\topic_score.py` | 56 | 3 | RESEARCH | orphaned small module: no dedicated test; not imported/no routes/no ma |
| 86 | `quick_check.py` | 50 | 0 | CORE | ad-hoc script, top-level code only, 50 lines, 0 importers |
| 87 | `read_docx.py` | 34 | 0 | CORE | ad-hoc script, top-level code only, 34 lines, 0 importers |
| 88 | `report_export\app_report_api_patch.py` | 17 | 2 | REPORT | orphaned small module: no dedicated test; not imported/no routes/no ma |
| 89 | `scripts\_prod_dep_check.py` | 19 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 90 | `scripts\_zbc_phase7_verify.py` | 48 | 0 | SCRATCH | SCRATCH/debug file (_prefix), 0 runtime importers |
| 91 | `scripts\backup_db.py` | 158 | 4 | UTILITY | backup file, 0 importers |
| 92 | `topic_monitor_policy.py` | 76 | 3 | RESEARCH | orphaned small module: no dedicated test; not imported/no routes/no ma |
| 93 | `v4_upgrade\adapters\base_backup_v589.py` | 130 | 9 | INFRASTRUCTURE | backup file, 0 importers |

## 6. BLOCKED Modules

Total BLOCKED: **0**

No BLOCKED modules detected. All production modules parse successfully and have at least minimal implementation.

## 7. DEPRECATED Modules

Total DEPRECATED: **10**

| File | Lines | Importers | Reason |
|------|-------|-----------|--------|
| `lumenis_skill_adapter.py` | 339 | 2 | marked deprecated/legacy, importers=2 |
| `provider_registry.py` | 100 | 2 | marked deprecated/legacy, importers=2 |
| `run_production.py` | 142 | 0 | marked deprecated/legacy, importers=0 |
| `run_supervised.py` | 298 | 0 | marked deprecated/legacy, importers=0 |
| `schema_registry.py` | 141 | 0 | marked deprecated/legacy, importers=0 |
| `scripts\inventory\build_asset_registry.py` | 357 | 0 | marked deprecated/legacy, importers=0 |
| `scripts\osai_module_graph_shardB.py` | 180 | 0 | marked deprecated/legacy, importers=0 |
| `settings_module.py` | 327 | 1 | marked deprecated/legacy, importers=1 |
| `skill_registry.py` | 321 | 2 | marked deprecated/legacy, importers=2 |
| `start_tunnel.py` | 92 | 0 | marked deprecated/legacy, importers=0 |

## 8. Key Findings & Critical Issues

### P0 Issues

1. **app.py monolith**: 5,886 lines / 262 functions / 188 routes in a single file. 59 route handlers without try/except represent unhandled exception risk.
2. **SCRATCH file proliferation**: 84 `_`-prefix debug/scratch files in repository root and subdirectories. The majority have 0 importers and are DELETE-CANDIDATEs.
3. **Orphaned substantial modules**: Multiple 100+ line modules have zero importers and no tests, suggesting abandoned development paths (e.g., monitoring.py, evidence_chain.py, platform_adapters/xhs.py).

### P1 Issues

4. **Test coverage gap**: Only 170/504 modules (33%) have matching test files.
5. **Stub functions**: 6 stub functions remain (NotImplementedError / pass-only), primarily in base adapter classes.
6. **Duplicate adapter layers**: Both `platform_adapters/` and `v4_upgrade/adapters/` exist with overlapping platform implementations (xhs, weibo, bilibili, douyin), indicating incomplete migration.

### P2 Issues

7. **collector_v2 integration**: The v2 pipeline (deduplicate/normalize/persist/spam_filter/subject_filter) exists but `collector_v2_integration.py` has 0 importers.
8. **Dual report engines**: `report_engine.py`, `report_export/report_engine.py`, and `v4_upgrade/report_center/report_generator.py` coexist with unclear ownership.
9. **AI provider fragmentation**: `ai_channel.py`, `ark_llm.py`, `local_ai_client.py`, `ai_api.py`, and `v4_upgrade/ai_hub/` represent 5+ AI access paths without a unified gateway.

## 9. Methodology

- **AST-based static analysis**: Every `.py` file parsed with Python `ast` to count functions, classes, routes, stubs, imports, try/except, returns.
- **Import graph resolution**: Built reverse-dependency graph to determine actual runtime importers.
- **Test coverage matching**: Cross-referenced `tests/` directory against module names and import statements.
- **Marker detection**: Scanned source for DEPRECATED, LEGACY, TODO, FIXME, NotImplementedError, `if __name__ == "__main__"`, top-level executable code.
- **Status determination**: Rules-based engine combining implementation presence, runtime references, test coverage, exception handling, and structural markers.
- **No source modification**: Read-only audit. No files were modified, moved, or deleted.

---
*Generated by ZBC Phase 11 Module Audit | 2026-09-06 12:55*