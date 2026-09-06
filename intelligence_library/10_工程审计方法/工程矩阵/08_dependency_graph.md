# 08 — Dependency Graph (依赖图)

> Verification: PASS (dependencies extracted from requirements.txt, package.json, imports, and module analysis)

## 1. External Dependencies

### 1.1 ZBC (requirements.txt)
| Package | Version Constraint | Purpose | Criticality |
|---|---|---|---|
| Flask | >=2.0 | Web framework | CRITICAL |
| Werkzeug | >=2.0 | WSGI utilities | CRITICAL |
| pandas | >=1.3 | Data processing | HIGH |
| openpyxl | >=3.0 | Excel read | HIGH |
| xlsxwriter | >=3.0 | Excel write | HIGH |
| python-docx | >=0.8.11 | Word export | MEDIUM |
| reportlab | >=3.6 | PDF export | MEDIUM |
| playwright | >=1.30 | Browser automation | HIGH |
| selenium | >=4.0 | Browser automation | HIGH |
| psutil | >=5.9 | System monitoring | HIGH |
| requests | >=2.28 | HTTP client | CRITICAL |
| httpx | >=0.24 | Async HTTP | MEDIUM |
| python-dotenv | >=0.21 | Env loading | HIGH |
| colorama | >=0.4.6 | Terminal colors | LOW |
| tqdm | >=4.64 | Progress bars | LOW |

**Additional implicit dependencies** (from imports, not in requirements.txt):
- sqlite3 (stdlib) — database
- json, os, sys, datetime, threading, subprocess (stdlib)
- websocket-client (for CDP) — NOT in requirements.txt! **MISSING**
- schedule (for collector automation) — NOT in requirements.txt! **MISSING**

### 1.2 DCC (package.json)
| Package | Version | Purpose | Criticality |
|---|---|---|---|
| (none runtime) | — | Zero runtime dependencies | — |
| (dev deps not listed) | — | — | — |

**Finding**: DCC has ZERO npm dependencies. All functionality built on Node.js stdlib (http, fs, path, url). This is intentional for security/auditability.

### 1.3 SICI
No package.json. Pure browser JavaScript. Dependencies:
- Browser APIs (localStorage, fetch, Service Worker)
- No external CDN libraries identified

### 1.4 AIDRH
No requirements.txt found. Python tools use stdlib only (json, os, re, sys, pathlib).

## 2. Internal Module Dependency Graph (ZBC)

```
app.py (monolith)
├── config.py
├── database.py
│   └── models.py
├── ai_analyzer.py
│   ├── ark_llm.py
│   ├── local_ai_client.py
│   └── ai_gateway_v570.py
├── ai_learning_engine.py
│   └── data_feedback_loop.py
├── ai_filter.py
├── collector.py
│   ├── xhs_cdp_collector.py
│   │   ├── cdp_helper.py
│   │   └── browser_discovery.py
│   ├── xhs_cookie_bridge.py
│   ├── bilibili_login_manager.py
│   ├── weibo_login_manager.py
│   └── collector_automation.py
├── event_graph.py
│   └── intelligence.py
│       └── context_intelligence.py
├── daily_report.py
│   ├── export_report.py
│   ├── report_engine.py
│   └── report_filter.py
├── brand_knowledge_base.py
│   ├── brand_report_generator.py
│   └── swire_group.py
├── pr_case_engine.py
│   └── pr_case_integration.py
├── public_opinion_cases.py
├── topic_campaign.py
├── subject_classifier.py
│   └── subject_rules.py
├── safety_boundary.py
├── security_scanner.py
├── runtime_preflight.py
├── risk_engine.py
├── monitoring.py
│   ├── stability_monitor.py
│   ├── system_health_api.py
│   ├── system_watchdog.py
│   └── system_guardian.py
├── auto_recovery.py
├── tunnel_guardian.py
├── ci_cd.py
├── cache_manager.py
├── network_adaptive.py
├── memory_optimizer.py
├── logger.py
├── wechat_notifier.py
├── evaluation_system.py
├── review_workflow.py
├── architecture_api.py
├── settings_module.py
├── function_registry.py
├── auth_recovery_api.py
└── auth_recovery_center.py
```

## 3. Internal Module Dependency Graph (SICI)

```
index.html
└── js/app.js
    ├── js/zachary-ai-core.js
    │   ├── js/zachary-runtime-api.js
    │   ├── js/zachary-ai-persistence.js
    │   │   └── js/storage.js
    │   ├── js/zbc-evidence-adapter.js
    │   └── js/zachary-tool-registry.js
    │       └── js/effective-rules.js
    ├── js/effective-rules.js
    ├── js/preflight.js
    │   └── js/effective-rules.js
    ├── js/capability-registry.js
    ├── js/tester.js
    ├── js/runner.js
    ├── js/github.js
    ├── js/deploy.js
    │   └── js/github.js
    ├── js/research-learning.js
    │   └── js/storage.js
    ├── js/three-repository-verifier.js
    │   └── js/github.js
    └── js/storage.js
```

## 4. Internal Module Dependency Graph (DCC)

```
server/server.js
├── server/config.js
├── server/security.js
├── server/startup-preflight.js
├── server/effective-rules.js
├── server/supplement-protocol.js
│   └── protocols/registry.json
├── server/snapshot.js
├── server/change-plan.js
├── server/evidence-bundle.js
├── server/learning-store.js
└── server/shadow-learning.js
    ├── server/learning-store.js
    └── server/evidence-bundle.js

index.html
└── js/bridge.js
    ├── js/github-audit.js
    ├── js/task.js
    ├── js/search.js
    └── js/theme.js
```

## 5. Internal Module Dependency Graph (AIDRH)

```
tools/research_id.py (standalone)
tools/secret_scan.py (standalone)
tools/runtime_preflight.py (standalone)
src/adapters/ddc_research_adapter.py (standalone)
src/contracts/ (not fully read)
src/shared/ (not fully read)

GLOBAL-CROSS-REPOSITORY-BASELINE.md (governance, no code deps)
CAPABILITY-REGISTRY.md (registry, no code deps)
data/research/records.jsonl (data, no code deps)
```

## 6. Cross-Repository Dependency Graph

```
                    ┌─────────────────────┐
                    │   AIDRH (Governance) │
                    │  Research & Baseline │
                    └──────────┬──────────┘
                               │ governs (L1: Evidence/Research)
                               │ provides: CAP-2026-0001/002/003
                               ▼
┌──────────────┐      ┌─────────────────────┐      ┌──────────────┐
│  ZBC (Prod)  │◄─────│   SICI (Mobile AI)  │─────►│  DCC (Dev)   │
│  Brand Monitor│ read │  Zachary AI Runtime │      │  AI Bridge   │
└──────────────┘ only └─────────────────────┘      └──────────────┘
     ▲                    │           ▲                    │
     │                    │           │                    │
     │ evidence           │           │ CI-VERIFY          │ audit
     │                    │           │                    │
     └────────────────────┘           └────────────────────┘
```

### 6.1 Cross-Repo Dependency Details

| Consumer | Provider | Type | Contract | Level | Status |
|---|---|---|---|---|---|
| SICI | ZBC | Evidence (read-only) | zbc-evidence-adapter.js | L1 | ACTIVE |
| SICI | DCC | CI Verification | capability-registry dep: DCC-CI-VERIFY | L2 | ACTIVE |
| DCC | Any GitHub repo | Audit data | github-audit.js / /api/audit/* | L1 | ACTIVE |
| AIDRH | DCC | Research format | ddc_research_adapter.py | L1 | ACTIVE |
| All | AIDRH | Governance baseline | GLOBAL-CROSS-REPOSITORY-BASELINE.md | L1 | ACTIVE (immutable) |
| ZBC | AIDRH | Research findings | (not yet implemented) | L1 | PLANNED |
| DCC | ZBC | Production evidence | (not yet implemented) | L2 | PLANNED |

### 6.2 Shared Design Tokens
| Consumer | Provider | Artifact | SHA | Status |
|---|---|---|---|---|
| SICI | (shared) | ZBIP_DESIGN_TOKENS.css | 2210afc9 | IDENTICAL |
| DCC | (shared) | ZBIP_DESIGN_TOKENS.css | 2210afc9 | IDENTICAL |
| ZBC | (own version) | ZBIP_DESIGN_TOKENS.css | 137a6f0e | DIFFERENT |

**Finding**: ZBC has a divergent version of design tokens. No single source of truth identified.

## 7. Dependency Risk Assessment

| Risk | Repo | Severity | Detail |
|---|---|---|---|
| Missing deps in requirements.txt | ZBC | MEDIUM | websocket-client, schedule not listed |
| Monolithic app.py | ZBC | HIGH | 264KB, all modules depend on it |
| No dependency locking | ZBC | MEDIUM | No Pipfile/poetry/requirements.lock |
| Zero deps (security positive) | DCC | LOW | Intentional, but limits functionality |
| No shared contract library | All | MEDIUM | Cross-repo contracts are docs only |
| Design token divergence | ZBC vs SICI/DCC | LOW | ZBC has different SHA |
| Python version not pinned | ZBC | LOW | No python_requires in setup |

**Verification**: PASS — External dependencies from requirements.txt/package.json. Internal dependencies from import analysis. Cross-repo dependencies from source code references.