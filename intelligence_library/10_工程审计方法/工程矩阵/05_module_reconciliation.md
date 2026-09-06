# 05 — 模块对账 (Module Reconciliation)

> Verification: PASS (module boundaries extracted from source file organization and imports)

## 1. ZBC Module Map

### 1.1 Core Application Layer
| Module | File | Responsibility | Dependencies | Status |
|---|---|---|---|---|
| Web Server | app.py | Flask routes, request handling, all UI endpoints | ALL modules | ACTIVE (monolith, 264KB) |
| Config | config.py | Unified env+JSON config management | os, json, dotenv | ACTIVE |
| Settings | settings_module.py | Runtime settings API | config, database | ACTIVE |
| Function Registry | function_registry.py | Feature flag/function registration | — | ACTIVE |

### 1.2 Data Layer
| Module | File | Responsibility | Dependencies | Status |
|---|---|---|---|---|
| Database | database.py | SQLite connection, schema init, CRUD helpers | sqlite3, config | ACTIVE |
| Models | models.py | ORM-like model classes, 22 table registry | database | ACTIVE |
| Migrations | database_migrations.py | Custom migration runner | database | ACTIVE |

### 1.3 AI/Analysis Layer
| Module | File | Responsibility | Dependencies | Status |
|---|---|---|---|---|
| AI Analyzer | ai_analyzer.py | LLM-based content analysis, sentiment, risk | ark_llm, local_ai_client, database | ACTIVE |
| AI Gateway | ai_gateway_v570.py | Multi-provider LLM routing | requests, config | ACTIVE |
| AI Learning | ai_learning_engine.py | Learning from feedback, pattern extraction | database, ai_analyzer | ACTIVE |
| AI Filter | ai_filter.py | Content filtering, quality scoring | ai_analyzer, database | ACTIVE |
| Ark LLM | ark_llm.py | DashScope/Qwen provider integration | requests | ACTIVE |
| Local AI | local_ai_client.py | Ollama/LMStudio/Llama.cpp client | requests, config | ACTIVE |
| Subject Classifier | subject_classifier.py | Dual-dimension subject classification | subject_rules, database | ACTIVE |
| Intelligence | intelligence.py | Event intelligence aggregation | event_graph, database | ACTIVE |
| Context Intelligence | context_intelligence.py | Context-aware analysis | intelligence, database | ACTIVE |

### 1.4 Collection Layer
| Module | File | Responsibility | Dependencies | Status |
|---|---|---|---|---|
| Collector | collector.py | Core collection orchestration | database, config, platform_adapters | ACTIVE |
| Collector Automation | collector_automation.py | Scheduled auto-collection | collector, scheduler | ACTIVE |
| XHS CDP Collector | xhs_cdp_collector.py | Xiaohongshu via Chrome DevTools Protocol | cdp_helper, browser_discovery | ACTIVE |
| XHS Cookie Bridge | xhs_cookie_bridge.py | Cookie injection for XHS | cdp_helper | ACTIVE |
| CDP Helper | cdp_helper.py | Chrome DevTools Protocol utilities | websocket, requests | ACTIVE |
| Browser Discovery | browser_discovery.py | Find running Chrome instances | psutil, subprocess | ACTIVE |
| Bilibili Login | bilibili_login_manager.py | Bilibili auth management | selenium, requests | ACTIVE |
| Weibo Login | weibo_login_manager.py | Weibo auth management | selenium, requests | ACTIVE |
| Web Monitor | web_monitor.py | Generic web source monitoring | requests, database | ACTIVE |
| Web Topic Discovery | web_topic_discovery.py | Topic discovery from web | web_monitor, ai_analyzer | ACTIVE |

### 1.5 Brand/PR Layer
| Module | File | Responsibility | Dependencies | Status |
|---|---|---|---|---|
| Brand Knowledge | brand_knowledge_base.py | Brand entity knowledge | brand_directory.json | ACTIVE |
| Brand Report | brand_report_generator.py | Brand-specific report generation | daily_report, database | ACTIVE |
| PR Case Engine | pr_case_engine.py | PR case matching and retrieval | pr_case_library.json | ACTIVE |
| PR Case Integration | pr_case_integration.py | PR case workflow integration | pr_case_engine, app | ACTIVE |
| Public Opinion Cases | public_opinion_cases.py | Case library management | database, case_library.json | ACTIVE |
| Swire Group | swire_group.py | Swire group-specific logic | brand_knowledge | ACTIVE |
| Topic Campaign | topic_campaign.py | Campaign tracking (61KB) | database, ai_analyzer | ACTIVE |

### 1.6 Event/Graph Layer
| Module | File | Responsibility | Dependencies | Status |
|---|---|---|---|---|
| Event Graph | event_graph.py | Event clustering, relation graph | database, ai_analyzer | ACTIVE |
| Case Deep Analysis | case_deep_analysis.py | Deep case analysis | ai_analyzer, database | ACTIVE |

### 1.7 Reporting Layer
| Module | File | Responsibility | Dependencies | Status |
|---|---|---|---|---|
| Daily Report | daily_report.py | Daily report generation | database, event_graph | ACTIVE |
| Export Report | export_report.py | Excel/Word/PDF export | pandas, openpyxl, python-docx | ACTIVE |
| Report Engine | report_engine.py | Report template engine | daily_report | ACTIVE |
| Report Filter | report_filter.py | Report data filtering | database | ACTIVE |
| Weekly Events | weekly_events.py | Weekly event digest | database, event_graph | ACTIVE |

### 1.8 Security/Safety Layer
| Module | File | Responsibility | Dependencies | Status |
|---|---|---|---|---|
| Safety Boundary | safety_boundary.py | Content safety boundaries, red lines | config, database | ACTIVE |
| Security Scanner | security_scanner.py | Code/secret scanning | — | ACTIVE |
| Runtime Preflight | runtime_preflight.py | Startup integrity checks | config, database | ACTIVE |
| Data Boundary | data_boundary.py | Data access boundaries | database | ACTIVE |
| Risk Engine | risk_engine.py | Risk scoring and assessment | ai_analyzer, database | ACTIVE |
| Auth Recovery | auth_recovery_api.py + auth_recovery_center.py | Authentication recovery flows | config, database | ACTIVE |

### 1.9 Monitoring/Ops Layer
| Module | File | Responsibility | Dependencies | Status |
|---|---|---|---|---|
| Monitoring | monitoring.py | System metrics collection | psutil, database | ACTIVE |
| Stability Monitor | stability_monitor.py | Stability anomaly detection | monitoring | ACTIVE |
| System Health | system_health_api.py | Health check endpoints | monitoring, config | ACTIVE |
| System Watchdog | system_watchdog.py | Process watchdog | psutil, subprocess | ACTIVE |
| System Guardian | system_guardian.py | System protection | watchdog, monitoring | ACTIVE |
| Auto Recovery | auto_recovery.py | Automatic failure recovery | watchdog, config | ACTIVE |
| Tunnel Guardian | tunnel_guardian.py | Cloudflare tunnel monitoring | subprocess | ACTIVE |
| CI/CD | ci_cd.py | CI/CD pipeline integration | subprocess, git | ACTIVE |

### 1.10 Infrastructure Layer
| Module | File | Responsibility | Dependencies | Status |
|---|---|---|---|---|
| Cache Manager | cache_manager.py | In-memory caching | — | ACTIVE |
| Network Adaptive | network_adaptive.py | Network condition adaptation | requests | ACTIVE |
| Memory Optimizer | memory_optimizer.py | Memory usage optimization | psutil | ACTIVE |
| Logger | logger.py | Structured logging | logging | ACTIVE |
| WeChat Notifier | wechat_notifier.py | WeChat/WeCom/PushPlus notifications | requests | ACTIVE |
| Evaluation System | evaluation_system.py | System quality evaluation | database, ai_analyzer | ACTIVE |
| Data Feedback | data_feedback_loop.py | Feedback-driven improvement | database, ai_learning | ACTIVE |

## 2. SICI Module Map

| Module | File | Responsibility | Dependencies | Status |
|---|---|---|---|---|
| App Bootstrap | js/app.js | PWA initialization, UI routing | all js modules | ACTIVE |
| Zachary AI Core | js/zachary-ai-core.js | Zachary AI runtime, evidence-first capability | storage, zachary-runtime-api | ACTIVE |
| Effective Rules | js/effective-rules.js | 4-layer rules resolution (Baseline>Supplement>Product>Capability) | — | ACTIVE |
| Preflight | js/preflight.js | 10-check runtime preflight | effective-rules | ACTIVE |
| Capability Registry | js/capability-registry.js | UMD capability registration/discovery | — | ACTIVE |
| Runtime API | js/zachary-runtime-api.js | Zachary runtime API surface | zachary-ai-core | ACTIVE |
| Persistence Bridge | js/zachary-ai-persistence.js | Server persistence contract | storage | ACTIVE |
| Tool Registry | js/zachary-tool-registry.js | Permission-gated tool registry | effective-rules | ACTIVE |
| ZBC Evidence Adapter | js/zbc-evidence-adapter.js | Read-only ZBC evidence access | zachary-ai-core | ACTIVE |
| Storage | js/storage.js | localStorage abstraction | — | ACTIVE |
| Test Runner | js/tester.js | In-browser test execution | — | ACTIVE |
| Code Runner | js/runner.js | Code execution sandbox | — | ACTIVE |
| GitHub | js/github.js | GitHub API integration | — | ACTIVE |
| Deploy | js/deploy.js | Deployment utilities | github | ACTIVE |
| Research Learning | js/research-learning.js | Research & learning UI | storage | ACTIVE |
| Three-Repo Verifier | js/three-repository-verifier.js | Cross-repo verification | github | ACTIVE |

## 3. DCC Module Map

| Module | File | Responsibility | Dependencies | Status |
|---|---|---|---|---|
| HTTP Server | server/server.js | Express-like HTTP server, 40+ routes | all server modules | ACTIVE |
| Learning Store | server/learning-store.js | Learning cases/patterns/lesson CRUD | fs, config | ACTIVE |
| Shadow Learning | server/shadow-learning.js | Shadow learning lifecycle engine | learning-store, evidence-bundle | ACTIVE |
| Evidence Bundle | server/evidence-bundle.js | Evidence bundle creation/validation | fs, config | ACTIVE |
| Change Plan | server/change-plan.js | Change plan management | fs, config | ACTIVE |
| Effective Rules | server/effective-rules.js | 4-layer rules resolver (server-side) | fs, config | ACTIVE |
| Snapshot | server/snapshot.js | State snapshot & lock management | fs | ACTIVE |
| Startup Preflight | server/startup-preflight.js | Server startup integrity checks | config | ACTIVE |
| Supplement Protocol | server/supplement-protocol.js | Supplement protocol registry | fs, protocols/registry.json | ACTIVE |
| Security | server/security.js | CORS, body parser, security headers | — | ACTIVE |
| Config | server/config.js | Server configuration | — | ACTIVE |
| GitHub Audit | js/github-audit.js | Frontend GitHub audit UI | bridge | ACTIVE |
| Bridge | js/bridge.js | Frontend-backend API bridge | fetch | ACTIVE |
| Task | js/task.js | Task management UI | bridge | ACTIVE |
| Search | js/search.js | Search UI | bridge | ACTIVE |
| Theme | js/theme.js | UI theme management | — | ACTIVE |

## 4. AIDRH Module Map

| Module | File | Responsibility | Dependencies | Status |
|---|---|---|---|---|
| DDC Research Adapter | src/adapters/ddc_research_adapter.py | DDC research_learning compatibility | — | ACTIVE |
| Contracts | src/contracts/ | Contract definitions | — | ACTIVE (directory, files not fully read) |
| Shared | src/shared/ | Shared utilities | — | ACTIVE (directory, files not fully read) |
| Research ID | tools/research_id.py | R-YYYY-NNNN ID generation | — | ACTIVE |
| Secret Scan | tools/secret_scan.py | Secret scanning (R-2026-0007) | — | ACTIVE |
| Runtime Preflight | tools/runtime_preflight.py | 7-check repo integrity (R-2026-0008) | — | ACTIVE |

## 5. Cross-Repo Module Overlap Analysis

| Capability Domain | ZBC | SICI | DCC | AIDRH | Overlap Level |
|---|---|---|---|---|---|
| Effective Rules | — | effective-rules.js | effective-rules.js | — | HIGH (2 implementations, semantic alignment) |
| Runtime Preflight | runtime_preflight.py | preflight.js | startup-preflight.js | runtime_preflight.py | VERY HIGH (4 implementations) |
| Capability Registry | function_registry.py | capability-registry.js | — | CAPABILITY-REGISTRY.md | MEDIUM (different formats) |
| Learning | ai_learning_engine.py | research-learning.js | learning-store.js + shadow-learning.js | research/ + data/ | HIGH (4 implementations, different layers) |
| Evidence | app_evidence.py | zbc-evidence-adapter.js | evidence-bundle.js | GLOBAL-CROSS-REPOSITORY-BASELINE.md | HIGH (4 implementations) |
| Security Scan | security_scanner.py | — | security.js | secret_scan.py | MEDIUM (different scopes) |
| GitHub Integration | ci_cd.py | github.js | github-audit.js | — | MEDIUM |
| Test Runner | tests/ (pytest) | tester.js | tests/ (node) | tests/ (pytest) | LOW (different frameworks) |
| Config Management | config.py | storage.js | config.js | — | LOW |
| Monitoring | monitoring.py + 5 modules | — | — | — | ZBC-ONLY |
| Collection | collector.py + 8 modules | — | — | — | ZBC-ONLY |
| Reporting | daily_report.py + 4 modules | — | — | — | ZBC-ONLY |

## 6. Module Boundary Violations

| Violation | Repo | Detail | Severity |
|---|---|---|---|
| Monolith app.py | ZBC | 264KB single file containing routes, business logic, and data access | HIGH |
| app_backup_v589.py | ZBC | 251KB backup file in production repo, potential confusion | MEDIUM |
| Effective Rules duplication | SICI+DCC | Same 4-layer logic implemented twice (frontend + server) | MEDIUM |
| Preflight duplication | ZBC+SICI+DCC+AIDRH | Same concept implemented 4 times | MEDIUM |
| Learning logic fragmentation | All 4 | Learning implemented in 4 different ways across repos | HIGH |
| No shared contract library | All | Cross-repo contracts are documentation-only, no shared code | MEDIUM |

**Verification**: PASS — Module boundaries extracted from file organization and import analysis. Overlap levels based on semantic analysis of module names and documented responsibilities.