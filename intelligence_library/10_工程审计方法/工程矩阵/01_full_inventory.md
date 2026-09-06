# 01 — 四库完整Inventory (Full Repository Inventory)

> Audit SHA baseline: ZBC=`bd6ed8d`, SICI=`c1b42bb`, DCC=`b0de3c5`, AIDRH=`930c646`  
> Generated: 2026-09-02 | Verification: PASS (direct GitHub API traversal)

---

## 1. Z-Brand-Core (ZBC) — 品牌舆情监测生产系统

### 1.1 Repository Metadata
- **Owner**: Zachary-1012
- **Default Branch**: main
- **HEAD SHA**: `bd6ed8d0bc50735c164455ea1a576ae7fc8e8897`
- **Branches** (6): main, feat/keyboard-shortcuts-modal, feat/zb-runtime-preflight, research/context-intelligence-20260901, research/zachary-ai-context-convergence-20260901, ui/staging-foundation
- **Version**: v5.8.9 (from VERSION file)
- **Language**: Python 3 (Flask), with JS/HTML/CSS frontend, PowerShell/BAT scripts
- **Database**: SQLite (data/monitor.db), env-overridable via ZBC_DB_PATH
- **Runtime Port**: 8200 (TAIKOO_PORT)
- **Total root entries**: ~190 (files + dirs)

### 1.2 Directory Structure
```
Z-Brand-Core/
├── .github/                    # CI/CD workflows
├── config/                     # industry_platforms.json, proxy_nodes.example.json
├── collector_guard/            # 采集守护进程
├── collector_v2/               # V2采集器
├── data/                       # JSON数据文件 + _zbmp_docs/
├── deployment/                 # 部署配置
├── docker/                     # Docker相关
├── docs/                       # 文档
├── migrations/                 # SQL迁移 (009, 010)
├── platform_adapters/          # 平台适配器
├── proxy_pool/                 # 代理池
├── ref_gpt_v2/                 # GPT参考实现
├── report_export/              # 报告导出
├── scripts/                    # 脚本
├── static/                     # 静态资源
├── templates/                  # HTML模板
├── tests/                      # 测试 (~55 test files + _archive/, frames/, shots/)
├── tools/                      # 工具
├── v4_upgrade/                 # V4升级
├── app.py                      # 主应用 (264KB, 巨型单体)
├── app_backup_v589.py          # 备份
├── database.py                 # 数据层 (63KB, 15 CREATE TABLE)
├── models.py                   # ORM模型 (22表注册)
├── config.py                   # 统一配置管理
├── requirements.txt            # Python依赖
├── .env.example                # 环境变量模板
├── system_config.json          # 系统配置
├── function_map.json           # 功能映射
├── function_registry.py        # 功能注册表
├── events_config.json          # 事件配置
├── brand_directory.json        # 品牌目录 (47KB)
├── brand_websites.json         # 品牌网站
├── case_library.json           # 案例库
├── pr_case_library.json        # PR案例库
├── pr_response_templates.json  # PR回复模板
├── reference_repos.json        # 参考仓库
└── [80+ Python modules]        # 各功能模块
```

### 1.3 Core Python Modules (by domain)

| Domain | Files | Key Files |
|---|---|---|
| **Web/Application** | app.py, run_production.py, run_supervised.py | app.py (264KB monolith) |
| **Database** | database.py, models.py, database_migrations.py, populate_empty_tables.py | database.py (63KB), models.py (22 tables) |
| **Configuration** | config.py, settings_module.py, system_config.json, .env.example | config.py (unified env+JSON config) |
| **AI/Analysis** | ai_analyzer.py, ai_filter.py, ai_gateway_v570.py, ai_learning_engine.py, ark_llm.py, local_ai_client.py, ai_analyzer.py (33KB) | Multi-provider: DashScope/Qwen, OpenAI, DeepSeek, Ollama, LMStudio, Llama.cpp |
| **Collection** | collector.py, collector_automation.py, collector_auto_start.py, collector_v2_integration.py, xhs_cdp_collector.py, xhs_cookie_bridge.py, rednote_collector.cjs, bilibili_login_manager.py, weibo_login_manager.py, browser_discovery.py, cdp_helper.py | XHS via CDP, Bilibili/Weibo login, web discovery |
| **Brand/PR** | brand_knowledge_base.py, brand_report_generator.py, brand_stats_recompute.py, pr_case_engine.py, pr_case_integration.py, public_opinion_cases.py, swire_group.py, topic_campaign.py (61KB) | Brand directory 47KB JSON |
| **Events/Intelligence** | event_graph.py (25KB), intelligence.py, context_intelligence.py, subject_classifier.py, subject_rules.py, case_deep_analysis.py, web_topic_discovery.py, web_monitor.py | Event graph, subject classification, web discovery |
| **Reporting** | daily_report.py (25KB), export_report.py (35KB), report_engine.py, report_filter.py, weekly_events.py | Daily/weekly reports, Excel/Word export |
| **Security/Safety** | safety_boundary.py (18KB), security_scanner.py, runtime_preflight.py, data_boundary.py, risk_engine.py, auth_recovery_api.py, auth_recovery_center.py | Safety boundaries, security scanning, runtime preflight |
| **Monitoring** | monitoring.py (19KB), stability_monitor.py (18KB), system_health_api.py (19KB), system_watchdog.py, system_guardian.py, monitor_pipeline.py, evaluate_system_timing.py | Health APIs, watchdog, stability monitor |
| **Recovery** | auto_recovery.py (17KB), tunnel_guardian.py, ci_cd.py | Auto-recovery, Cloudflare tunnel guardian |
| **Cache/Network** | cache_manager.py, network_adaptive.py, memory_optimizer.py | Cache, network adaptation |
| **Evaluation** | evaluation_system.py (18KB), data_feedback_loop.py | Evaluation system, feedback loop |
| **Review/Workflow** | review_workflow.py, architecture_api.py, system_features_api.py | Review workflow, architecture API |
| **Notification** | wechat_notifier.py (36KB) | WeChat/WeCom/ServerChan/PushPlus notification |
| **Logging** | logger.py, check_logs.py | Structured logging |

### 1.4 Frontend Assets
- `templates/` — Jinja2 HTML templates
- `static/` — CSS, JS, images
- `zachary_robot_widget.html` — Zachary robot widget (10KB)
- `xhs_campaign_monitor.js`, `xhs_search.js`, `xhs_cookie_search.js` — XHS browser automation JS
- `inject_cookies.js` — Cookie injection script

### 1.5 Test Inventory (55+ files in tests/)
audit_probe_1-6.py, conftest.py, test_adapter_resilience.py, test_adaptive_engine.py, test_ai.py, test_api.py, test_api_smoke.py, test_auth_api.py, test_auto_recovery.py, test_bilibili.py, test_brand_library.py, test_browser_e2e.py, test_collect_pipeline.py, test_collect_state.py, test_collection_full.py, test_context_intelligence.py, test_css_balance.py, test_data_feedback.py, test_database.py, test_dev_exec_guard.py, test_douyin_adapter.py, test_e2e.py (17KB), test_event_curation.py, test_event_date.py, test_event_graph_relations.py, test_global_bil_read.py, test_guard_wiring.py, test_health_center.py, test_instagram_adapter.py, test_llm_gateway.py, test_llm_online.py, test_negative_event_api.py, test_proxy_pool.py, test_redline_units.py, test_rednote_policy.py, test_report_center_route.py, test_report_periods.py, test_risk_engine.py, test_runtime_preflight.py, test_safety_boundary.py, test_schedule_gate.py, test_scheduling.py, test_security_scan.py, test_sentiment_engine.py, test_subject_dual_dimension.py, test_subject_redline.py, test_system.py, test_title_fallback.py, test_topic_port.py, test_version_api.py, test_workspace_keys.py, v4_smoke.py, github_benchmark.py, healthcheck.py, run_all.py

### 1.6 Database Tables (22 registered in models.py)
notes, events, comments, note_comments, daily_reports, daily_digest, weekly_events, web_topics, web_events, web_mentions, brand_industry_monitor, collection_counters, collection_logs, collector_quality_log, ai_filter_log, event_insights, event_mentions, note_review_history, feedback_keywords, system_config, web_sources, web_runs

### 1.7 Dependencies (requirements.txt)
Flask>=2.0, Werkzeug>=2.0, pandas>=1.3, openpyxl>=3.0, xlsxwriter>=3.0, python-docx>=0.8.11, reportlab>=3.6, playwright>=1.30, selenium>=4.0, psutil>=5.9, requests>=2.28, httpx>=0.24, python-dotenv>=0.21, colorama>=0.4.6, tqdm>=4.64

---

## 2. SICI-Core — 移动开发控制台 / Zachary AI Runtime

### 2.1 Repository Metadata
- **Owner**: Zachary-1012
- **Default Branch**: main
- **HEAD SHA**: `c1b42bb6f7e286875d8a209018a89b69d8435b4f`
- **Branches** (2): main, security/runtime-preflight-hardening
- **Language**: JavaScript (PWA - Progressive Web App), HTML, CSS
- **Runtime**: Static hosting (GitHub Pages compatible, .nojekyll present)
- **Total root entries**: 18

### 2.2 Directory Structure
```
SICI-Core/
├── .github/            # CI workflows
├── css/                # Stylesheets
├── docs/               # Documentation
├── js/                 # 16 JavaScript modules
├── shadow_run/         # Shadow run reports & tests
├── tests/              # Test files
├── upgrade_modules/    # Upgrade modules
├── index.html          # Entry point (1KB)
├── manifest.json       # PWA manifest
├── sw.js               # Service Worker
├── PLATFORM_README.md  # Platform README (9.5KB)
├── README.md           # README (3.2KB)
├── ZBIP_DESIGN_TOKENS.css  # Design tokens (identical SHA across repos)
├── ZBIP_UNIFIED_README.md  # Unified README
├── auto_push.ps1       # Auto-push script
└── 一键推送学习资料.bat    # Batch script
```

### 2.3 JavaScript Modules (js/)
| File | Size | Purpose |
|---|---|---|
| app.js | 30KB | Main application bootstrap |
| zachary-ai-core.js | 11KB | Zachary AI core runtime (evidence-first capability) |
| effective-rules.js | 12KB | 4-layer rules engine (Baseline 100 > Supplements 95 > Product 90 > Capability 80) |
| preflight.js | 9.8KB | Runtime preflight (10 checks, hard-block + soft-warn) |
| capability-registry.js | 6.2KB | UMD capability registry (list/get/getByOwner/getDependencies) |
| deploy.js | 6.2KB | Deployment utilities |
| tester.js | 11KB | Test runner |
| runner.js | 7.3KB | Code runner |
| github.js | 5.7KB | GitHub integration |
| research-learning.js | 2.7KB | Research & learning |
| storage.js | 2.8KB | LocalStorage persistence |
| zachary-runtime-api.js | 3.3KB | Zachary runtime API |
| zachary-ai-persistence.js | 1.5KB | AI persistence bridge |
| zachary-tool-registry.js | 1.3KB | Tool registry (permission-gated) |
| zbc-evidence-adapter.js | 1.5KB | Read-only ZBC evidence adapter |
| three-repository-verifier.js | 0.8KB | Three-repo verification |

### 2.4 PWA Manifest
- Name: "Zachary — 移动开发控制台"
- Display: standalone, portrait
- Start URL: ./index.html
- Icons: inline SVG (192x192, 512x512)

### 2.5 Shadow Run (shadow_run/)
- SHADOW_RUN_REPORT.md — Shadow run report
- test_pyresilience.py — Python resilience test
- test_yyds_logger.py — Logger test
- xiaohongshu_bakeoff_report.md — XHS bakeoff report

### 2.6 Registered Capabilities (capability-registry.js)
5 exposed capabilities: EffectiveRules, Preflight, MobileUI, TestRunner, CI-Verify  
1 dependency: DCC-CI-VERIFY (reusable-verify.yml@448ba21)

---

## 3. Development-Command-Console (DCC) — AI软件工程命令控制台

### 3.1 Repository Metadata
- **Owner**: Zachary-1012
- **Default Branch**: main
- **HEAD SHA**: `b0de3c55e90d52c57a076e96a3d0e140f7ee1cb1`
- **Branches** (2): main, security/runtime-preflight-hardening
- **Version**: 0.5.0 (package.json)
- **Language**: Node.js (server) + JavaScript (frontend)
- **Runtime**: Node >=18, HTTP server on port 8787, host 127.0.0.1
- **Total root entries**: 18

### 3.2 Directory Structure
```
Development-Command-Console/
├── .devcontainer/     # Dev container config
├── .github/           # CI workflows
├── css/               # Stylesheets (tokens.css, components.css)
├── data/              # JSON data (baseline.json, rules/)
├── docs/              # Documentation
├── js/                # 6 frontend JS modules
├── protocols/         # Protocol registry (registry.json)
├── server/            # 11 Node.js server modules
├── tests/             # Test files
├── tools/             # Tools
├── index.html         # Frontend entry (17.9KB)
├── package.json       # NPM config (v0.5.0, no runtime deps)
├── PLATFORM_README.md # Platform README (11.8KB)
├── README.md          # README (20.9KB)
├── ZBIP_DESIGN_TOKENS.css  # Design tokens (identical SHA: 2210afc9)
└── ZBIP_UNIFIED_README.md  # Unified README
```

### 3.3 Server Modules (server/)
| File | Size | Purpose |
|---|---|---|
| server.js | 31KB | Main HTTP server, 40+ API endpoints |
| learning-store.js | 25KB | Learning case/pattern/lesson store |
| shadow-learning.js | 20KB | Shadow learning lifecycle (Research→Candidate→Shadow→Evidence→Review→Verify→Promotion) |
| evidence-bundle.js | 16KB | Evidence bundle creation/validation |
| change-plan.js | 12KB | Change plan management |
| effective-rules.js | 8.5KB | 4-layer effective rules resolver |
| startup-preflight.js | 5.2KB | Startup integrity preflight |
| supplement-protocol.js | 5.9KB | Supplement protocol manager |
| snapshot.js | 10KB | Snapshot & lock management |
| security.js | 5KB | Security middleware (CORS, body parser, headers) |
| config.js | 1.4KB | Server configuration |

### 3.4 Frontend JS (js/)
bridge.js, github-audit.js (14.9KB), search.js, task.js, theme.js

### 3.5 API Endpoints (server.js)
**Health/Status**: GET /health, GET /api/status, GET /api/ai/ping, GET /api/ai/capabilities  
**Task**: POST /api/ai/task  
**Audit**: GET /api/audit/repository, /api/audit/branches, /api/audit/commits, /api/audit/commit, /api/audit/workflows  
**Snapshot**: GET/POST /api/snapshot, GET /api/snapshot/:id, POST /api/snapshot/lock, GET /api/snapshot/lock/:id, POST /api/snapshot/lock/:id/verify  
**Change Plan**: GET/POST /api/change-plan, GET /api/change-plan/:id, POST /api/change-plan/:id/status, /update, /validate  
**Evidence**: GET/POST /api/evidence-bundle, GET /api/evidence-bundle/:id, POST /api/evidence-bundle/:id/validate  
**Learning**: GET/POST /api/learning/cases, GET /api/learning/cases/:id, GET /api/learning/patterns, GET /api/learning/lessons  
**Shadow Learning**: GET /api/shadow-learning, POST /api/shadow-learning/analyze, GET /api/shadow-learning/:id, POST /api/shadow-learning/:id/status, /promote  
**Effective Rules**: GET /api/effective-rules, /all, /type/:type  
**Supplements**: GET /api/supplements, /active, /:id  
**Capabilities**: GET /api/capabilities, /:id

### 3.6 Permission Model
READ=ALLOW, TASK=ALLOW, AUDIT=ALLOW, TEST=CONTROLLED, WRITE=DENY, DEPLOY=DENY

### 3.7 Data Files
- data/baseline.json — ZB-PROD-2026-08-31-04, 5 global rules, 4 product definitions
- data/rules/product-rules.json — 10 DCC product rules
- data/rules/capability-constraints.json — 13 capabilities, 12 permission gates
- protocols/registry.json — 2 active supplement protocols

---

## 4. AI-Development-Research-Hub (AIDRH) — 研发中枢

### 4.1 Repository Metadata
- **Owner**: Zachary-1012
- **Default Branch**: main
- **HEAD SHA**: `930c6468dcbfc424d5fc65559a27e55fed11bf6e`
- **Branches** (18): main, ci/r7-secret-scan-fix, research/content-benchmark-expansion (+001~013), security/runtime-preflight-hardening, zachary-ai-consolidation-01
- **Language**: Python (tools/src) + Markdown (research/protocols/architecture)
- **Role**: Shared research & development hub, no production control
- **Total root entries**: 25

### 4.2 Directory Structure
```
AI-Development-Research-Hub/
├── .github/           # CI workflows
├── architecture/      # Architecture docs
├── benchmarks/        # Benchmark data
├── cases/             # Case studies
├── data/              # Data files (learning/, research records)
├── design-system/     # Design system
├── docs/              # Documentation
├── logs/              # Operation logs
├── protocols/         # Protocol definitions
├── research/          # Research documents (R-2026-0001~0008)
├── src/               # Python source (adapters/, contracts/, shared/)
├── tests/             # Tests (115 passing)
├── tools/             # Python tools (research_id.py, secret_scan.py, runtime_preflight.py)
├── AI-COLLABORATION-PROTOCOL.md
├── CAPABILITY-REGISTRY.md
├── CASE-LIBRARY.md
├── GLOBAL-CROSS-REPOSITORY-BASELINE.md  # Immutable cross-repo baseline (5.3KB)
├── PLATFORM_BASELINE.md
├── README.md
├── RESEARCH-LEARNING-SCHEMA.md
├── SHADOW-LEARNING-PROTOCOL.md
├── THREE-REPOSITORY-VALIDATION.md
└── ZBIP_UNIFIED_README.md
```

### 4.3 Source Code (src/)
- `src/adapters/` — ddc_research_adapter.py (DDC research_learning compatibility adapter)
- `src/contracts/` — Contract definitions
- `src/shared/` — Shared utilities

### 4.4 Tools (tools/)
- research_id.py — Research ID generator (R-YYYY-NNNN)
- secret_scan.py — Secret scanner (R-2026-0007, flags sensitive keys with non-empty non-REDACTED values)
- runtime_preflight.py — 7-check repository integrity preflight (R-2026-0008, adapted from DDC)

### 4.5 Registered Capabilities (CAPABILITY-REGISTRY.md)
| ID | Name | Status | Research ID |
|---|---|---|---|
| CAP-2026-0001 | research-id-generator | reusable | R-2026-0001 |
| CAP-2026-0002 | shadow-lifecycle | reusable | R-2026-0001 |
| CAP-2026-0003 | ddc-research-adapter | reusable | R-2026-0001 |

### 4.6 Research Records (R-2026-0001 ~ R-2026-0008)
- R-2026-0001: Foundation (research ID, shadow lifecycle)
- R-2026-0006: Credential Sanitization / security-first superset boundary (108 tests)
- R-2026-0007: Secret scan false positive fix (tools/secret_scan.py)
- R-2026-0008: Runtime preflight adapted from DDC (tools/runtime_preflight.py)

### 4.7 Key Governance Documents
- **GLOBAL-CROSS-REPOSITORY-BASELINE.md**: Before/Change/After Gate, Three-Way Verification, Capability Delta, Shadow Learning Gate, Global Feedback Loop
- **AI-COLLABORATION-PROTOCOL.md**: AI collaboration rules
- **SHADOW-LEARNING-PROTOCOL.md**: Shadow learning lifecycle
- **RESEARCH-LEARNING-SCHEMA.md**: Research & learning data schema
- **THREE-REPOSITORY-VALIDATION.md**: Three-repo validation matrix
- **PLATFORM_BASELINE.md**: Platform baseline

---

## 5. Cross-Repository Shared Artifacts

### 5.1 Identical Files (same SHA across repos)
| File | SHA | Repos |
|---|---|---|
| ZBIP_DESIGN_TOKENS.css | `2210afc983ea7f97f75b1bc031d785b185abcb81` | SICI, DCC |
| (ZBC has different SHA: `137a6f0e`) | | ZBC |

### 5.2 Similar-Named Files (potential duplication)
- ZBIP_UNIFIED_README.md — exists in all 4 repos (different SHAs, different sizes)
- PLATFORM_README.md — exists in ZBC, SICI, DCC
- effective-rules.js — SICI (frontend) and DCC (server) — semantic alignment, different implementations
- preflight.js / startup-preflight.js — SICI and DCC — semantic alignment
- runtime_preflight.py — ZBC and AIDRH (adapted from DDC)

### 5.3 Cross-Repo References
- SICI zbc-evidence-adapter.js → ZBC (read-only evidence)
- SICI capability-registry depends on DCC-CI-VERIFY
- DCC github-audit.js → reads any GitHub repo (including ZBC, SICI, AIDRH)
- AIDRH ddc_research_adapter.py → DDC research_learning compatibility
- AIDRH GLOBAL-CROSS-REPOSITORY-BASELINE → governs all 4 repos

---

## 6. Inventory Summary Statistics

| Metric | ZBC | SICI | DCC | AIDRH | Total |
|---|---|---|---|---|---|
| Branches | 6 | 2 | 2 | 18 | 28 |
| Root entries | ~190 | 18 | 18 | 25 | ~251 |
| Primary language | Python | JS(PWA) | Node.js | Python+MD | — |
| Database tables | 22 | 0 (localStorage) | 0 (JSON files) | 0 (JSONL) | 22 |
| API endpoints | ~50+ (Flask) | 0 (static) | 40+ | 0 | ~90+ |
| Test files | 55+ | ~10 | ~10 | ~15 | ~90 |
| Config files | 5+ | 1 | 4 | 3 | ~13 |
| CI workflows | present | present | present | present | 4 |

**Verification Status**: PASS — All inventory data obtained via direct GitHub API (get_file_contents, list_branches, list_commits). No AI speculation used for file existence or SHA values.