# 06 — 功能对账 (Function Reconciliation)

> Verification: PARTIAL — Routes/APIs extracted from source; runtime behavior NOT_VERIFIED (no live execution)

## 1. ZBC Functional Capabilities

### 1.1 Web UI Routes (app.py — estimated 50+ routes)
| Route Group | Count | Purpose | Evidence |
|---|---|---|---|
| / (index) | 1 | Dashboard | app.py |
| /notes/* | ~10 | Note CRUD, review, detail | app.py, models.py |
| /events/* | ~8 | Event graph, detail, management | app.py, event_graph.py |
| /collect/* | ~6 | Collection control, status | app.py, collector.py |
| /report/* | ~8 | Daily/weekly reports, export | app.py, daily_report.py |
| /api/* | ~15 | JSON API endpoints | app.py |
| /admin/* | ~5 | Admin functions | app.py |
| /health/* | ~3 | Health checks | app.py, system_health_api.py |
| /brand/* | ~5 | Brand management | app.py, brand_knowledge_base.py |
| /pr/* | ~4 | PR case management | app.py, pr_case_integration.py |
| /settings/* | ~4 | System settings | app.py, settings_module.py |
| /ai/* | ~5 | AI analysis controls | app.py, ai_analyzer.py |
| /monitoring/* | ~4 | Monitoring dashboards | app.py, monitoring.py |
| /security/* | ~3 | Security dashboard | app.py, security_scanner.py |
| /recovery/* | ~3 | Recovery controls | app.py, auto_recovery.py |

**Note**: Exact route count NOT_VERIFIED — app.py is 264KB and was not fully parsed for route decorators. Estimated 50+ based on module count.

### 1.2 Core Business Functions
| Function | Owner Module | Input | Output | DB Access | Status |
|---|---|---|---|---|
| Content Collection | collector.py | keywords, platforms | notes, comments | R/W notes, comments, collection_logs | ACTIVE |
| XHS CDP Collection | xhs_cdp_collector.py | CDP endpoint, keywords | XHS notes | R/W notes | ACTIVE |
| AI Sentiment Analysis | ai_analyzer.py | note content | sentiment, risk, confidence | R notes, W ai_filter_log | ACTIVE |
| Event Clustering | event_graph.py | notes | events, relations | R/W events, event_mentions | ACTIVE |
| Daily Report Generation | daily_report.py | date range | report HTML/JSON | R notes, events, W daily_reports | ACTIVE |
| Report Export | export_report.py | report data | Excel/Word/PDF | R daily_reports | ACTIVE |
| PR Case Matching | pr_case_engine.py | event description | matched cases | R pr_case_library.json | ACTIVE |
| Brand Knowledge Query | brand_knowledge_base.py | brand name | brand profile | R brand_directory.json | ACTIVE |
| Subject Classification | subject_classifier.py | note content | subject tags | R notes, feedback_keywords | ACTIVE |
| Risk Assessment | risk_engine.py | event/note | risk score, level | R notes, events | ACTIVE |
| Safety Boundary Check | safety_boundary.py | content | pass/block, reason | — | ACTIVE |
| Auto Recovery | auto_recovery.py | failure signal | recovery action | R/W system_config | ACTIVE |
| WeChat Notification | wechat_notifier.py | message, channel | sent status | — | ACTIVE |
| System Health Check | system_health_api.py | — | health metrics | R monitoring data | ACTIVE |
| Data Feedback Loop | data_feedback_loop.py | user feedback | updated keywords | R/W feedback_keywords | ACTIVE |
| AI Learning | ai_learning_engine.py | feedback data | learned patterns | R/W notes, ai_filter_log | ACTIVE |
| Runtime Preflight | runtime_preflight.py | — | pass/fail report | R config, database | ACTIVE |
| Security Scan | security_scanner.py | code/files | findings | — | ACTIVE |
| Web Topic Discovery | web_topic_discovery.py | sources | topics, mentions | R/W web_topics, web_mentions | ACTIVE |
| Evaluation | evaluation_system.py | system data | quality score | R notes, events | ACTIVE |

## 2. SICI Functional Capabilities

| Function | Owner Module | Input | Output | Persistence | Status |
|---|---|---|---|---|---|
| PWA Bootstrap | app.js | — | initialized app | localStorage | ACTIVE |
| Zachary AI Runtime | zachary-ai-core.js | user query | AI response + evidence | localStorage | ACTIVE |
| Effective Rules Resolution | effective-rules.js | context, rules | resolved rule set | — | ACTIVE |
| Runtime Preflight | preflight.js | — | 10-check report | — | ACTIVE |
| Capability Discovery | capability-registry.js | query | capability list | — | ACTIVE |
| Tool Execution (gated) | zachary-tool-registry.js | tool name, args | result | — | ACTIVE (permission-gated) |
| ZBC Evidence Read | zbc-evidence-adapter.js | evidence query | ZBC evidence (read-only) | — | ACTIVE |
| Test Execution | tester.js | test definitions | pass/fail | — | ACTIVE |
| Code Execution | runner.js | code snippet | output | — | ACTIVE |
| GitHub Operations | github.js | repo, action | result | — | ACTIVE |
| Deployment | deploy.js | config | deploy status | — | ACTIVE |
| Research Learning UI | research-learning.js | — | learning dashboard | localStorage | ACTIVE |
| Three-Repo Verification | three-repository-verifier.js | repos | verification report | — | ACTIVE |
| Persistence Bridge | zachary-ai-persistence.js | state | server sync | localStorage → server | ACTIVE (contract only) |

## 3. DCC Functional Capabilities

| Function | Owner Module | Input | Output | Persistence | Status |
|---|---|---|---|---|---|
| HTTP API Server | server.js | HTTP requests | responses | in-memory | ACTIVE |
| AI Task Execution | server.js (/api/ai/task) | task description | AI result | in-memory | ACTIVE |
| Repository Audit | server.js (/api/audit/*) | repo, branch | audit data | in-memory | ACTIVE |
| Snapshot Management | snapshot.js | state | snapshot, lock | JSON files | ACTIVE |
| Change Plan Management | change-plan.js | plan data | plan status | JSON files | ACTIVE |
| Evidence Bundle | evidence-bundle.js | evidence data | validated bundle | JSON files | ACTIVE |
| Learning Case Store | learning-store.js | case data | CRUD operations | JSON files | ACTIVE |
| Shadow Learning | shadow-learning.js | candidate | lifecycle state | JSON files | ACTIVE |
| Effective Rules (server) | effective-rules.js | context | resolved rules | JSON files | ACTIVE |
| Supplement Protocol | supplement-protocol.js | protocol | active supplements | JSON files | ACTIVE |
| Startup Preflight | startup-preflight.js | — | integrity report | — | ACTIVE |
| Security Middleware | security.js | requests | filtered requests | — | ACTIVE |
| GitHub Audit UI | github-audit.js | repo URL | audit UI | — | ACTIVE |
| Task UI | task.js | — | task dashboard | — | ACTIVE |

## 4. AIDRH Functional Capabilities

| Function | Owner Module | Input | Output | Persistence | Status |
|---|---|---|---|---|---|
| Research ID Generation | tools/research_id.py | date | R-YYYY-NNNN | — | ACTIVE |
| Secret Scanning | tools/secret_scan.py | files/content | findings | — | ACTIVE |
| Runtime Preflight | tools/runtime_preflight.py | repo path | 7-check report | — | ACTIVE |
| DDC Research Adapter | src/adapters/ddc_research_adapter.py | DDC data | AIDRH format | — | ACTIVE |
| Research Record Management | data/research/records.jsonl | — | append-only ledger | JSONL | ACTIVE |
| Capability Registry | CAPABILITY-REGISTRY.md | — | 3 registered capabilities | Markdown | ACTIVE |
| Cross-Repo Baseline Governance | GLOBAL-CROSS-REPOSITORY-BASELINE.md | — | governance rules | Markdown | ACTIVE (immutable) |

## 5. Cross-Repo Function Mapping

| Business Capability | ZBC Implementation | SICI Implementation | DCC Implementation | AIDRH Implementation |
|---|---|---|---|---|
| AI Analysis | ai_analyzer.py (multi-provider LLM) | zachary-ai-core.js (runtime) | /api/ai/task (proxy) | — (research only) |
| Learning | ai_learning_engine.py | research-learning.js | learning-store.js + shadow-learning.js | research/ records |
| Evidence | app_evidence.py | zbc-evidence-adapter.js (read-only) | evidence-bundle.js | GLOBAL-CROSS-REPOSITORY-BASELINE.md |
| Rules Engine | safety_boundary.py (red lines) | effective-rules.js (4-layer) | effective-rules.js (4-layer) | PLATFORM_BASELINE.md |
| Preflight | runtime_preflight.py | preflight.js | startup-preflight.js | runtime_preflight.py |
| Capability Mgmt | function_registry.py | capability-registry.js | /api/capabilities | CAPABILITY-REGISTRY.md |
| Security | security_scanner.py + safety_boundary.py | — | security.js | secret_scan.py |
| Testing | tests/ (pytest, 55+) | tester.js | tests/ (node) | tests/ (pytest, 115) |
| GitHub Ops | ci_cd.py | github.js | github-audit.js | — |
| Monitoring | monitoring.py + 5 modules | — | — | — |
| Collection | collector.py + 8 modules | — | — | — |
| Reporting | daily_report.py + 4 modules | — | — | — |

## 6. Function Status Summary

| Status | Count | Notes |
|---|---|---|
| ACTIVE (verified in source) | ~80 | All functions found in source code |
| NOT_VERIFIED (runtime) | ALL | No live execution performed; runtime behavior unverified |
| DEPRECATED | 1 | app_backup_v589.py (backup, not imported) |
| CONFLICT | 0 | No direct function-level conflicts identified |

**Verification**: PARTIAL — Functions identified from source code structure and imports. Exact route counts in app.py are estimates (264KB file not fully parsed). Runtime behavior is NOT_VERIFIED across all repos.