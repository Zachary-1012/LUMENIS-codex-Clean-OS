# 09 — Communication Graph (跨库通信图)

> Verification: PARTIAL — Communication channels identified from source code; runtime connectivity NOT_VERIFIED

## 1. Communication Channel Inventory

### 1.1 API Communication
| Channel | Provider | Consumer | Protocol | Endpoint | Contract | Status |
|---|---|---|---|---|---|---|
| ZBC Web API | ZBC | SICI (via adapter) | HTTP/REST | :8200/api/* | zbc-evidence-adapter.js (read-only) | NOT_VERIFIED (runtime) |
| DCC AI Bridge | DCC | DCC frontend | HTTP/REST | 127.0.0.1:8787/api/* | server.js route table | ACTIVE (code) |
| DCC Audit API | DCC | DCC frontend | HTTP/REST | /api/audit/* | server.js | ACTIVE (code) |
| GitHub API | GitHub | All repos | HTTPS REST | api.github.com | github.js, github-audit.js, ci_cd.py | ACTIVE |
| LLM Providers | DashScope/OpenAI/DeepSeek/Ollama | ZBC | HTTPS REST | various | ark_llm.py, local_ai_client.py, ai_gateway_v570.py | ACTIVE (code) |
| WeChat/WeCom API | WeChat | ZBC | HTTPS REST | various | wechat_notifier.py | ACTIVE (code) |
| Chrome CDP | Chrome | ZBC | WebSocket | localhost:9222 | cdp_helper.py | ACTIVE (code) |
| Cloudflare Tunnel | Cloudflare | ZBC | HTTPS | — | tunnel_guardian.py | ACTIVE (code) |

### 1.2 Event Communication
| Channel | Provider | Consumer | Mechanism | Contract | Status |
|---|---|---|---|---|---|
| Shadow Learning Lifecycle | DCC | DCC | In-memory state machine | shadow-learning.js | ACTIVE (code) |
| Learning Case Events | DCC | DCC | In-memory | learning-store.js | ACTIVE (code) |
| Collection Events | ZBC | ZBC | In-process callbacks | collector.py, collector_automation.py | ACTIVE (code) |
| AI Analysis Events | ZBC | ZBC | In-process | ai_analyzer.py | ACTIVE (code) |
| **Cross-repo events** | — | — | **NONE IDENTIFIED** | — | **GAP** |

**Finding**: No cross-repository event bus or message queue. All inter-repo communication is via HTTP API or file-based contracts.

### 1.3 Callback Communication
| Channel | Provider | Consumer | Mechanism | Status |
|---|---|---|---|---|
| DCC Task Callback | DCC AI Bridge | DCC frontend | HTTP response (sync) | ACTIVE |
| ZBC Collection Callback | Collector | app.py | In-process function call | ACTIVE |
| **Cross-repo callbacks** | — | — | **NONE IDENTIFIED** | **GAP** |

### 1.4 File Contract Communication
| Channel | Provider | Consumer | Format | Location | Status |
|---|---|---|---|---|---|
| Research Records | AIDRH | All | JSONL | data/research/records.jsonl | ACTIVE |
| Capability Registry | AIDRH | All | Markdown | CAPABILITY-REGISTRY.md | ACTIVE |
| Baseline Rules | AIDRH | All | Markdown | GLOBAL-CROSS-REPOSITORY-BASELINE.md | ACTIVE (immutable) |
| Supplement Protocols | DCC | DCC | JSON | protocols/registry.json | ACTIVE |
| Effective Rules | DCC/SICI | DCC/SICI | JSON (in-memory) | data/baseline.json, data/rules/ | ACTIVE |
| Design Tokens | (shared) | SICI, DCC | CSS | ZBIP_DESIGN_TOKENS.css | ACTIVE (identical SHA) |
| ZBC Evidence | ZBC | SICI | JSON (via API) | zbc-evidence-adapter.js | NOT_VERIFIED |
| Learning Data | DCC | AIDRH | JSON (adapter) | ddc_research_adapter.py | ACTIVE (code) |

### 1.5 Database Contract Communication
| Channel | Provider | Consumer | Mechanism | Status |
|---|---|---|---|---|
| ZBC SQLite | ZBC | ZBC only | Direct file access | ACTIVE (isolated) |
| **Cross-repo DB access** | — | — | **NONE** (correct isolation) | PASS |

### 1.6 GitHub Operation Communication
| Channel | Provider | Consumer | Mechanism | Status |
|---|---|---|---|---|
| CI/CD Pipelines | GitHub Actions | All repos | .github/workflows/ | ACTIVE |
| Auto-push Scripts | Local | SICI | PowerShell (auto_push.ps1) | ACTIVE (potential risk) |
| Repository Audit | GitHub API | DCC | github-audit.js + /api/audit/* | ACTIVE |
| Code Search | GitHub API | All | search_code (MCP) | ACTIVE |

### 1.7 Runtime Bridge Communication
| Channel | Provider | Consumer | Mechanism | Status |
|---|---|---|---|---|
| Zachary Runtime API | SICI | SICI | In-browser JS API | ACTIVE |
| DCC Local AI Bridge | DCC | DCC frontend | HTTP 127.0.0.1:8787 | ACTIVE |
| ZBC Local AI Client | ZBC | Ollama/LMStudio | HTTP localhost | ACTIVE (code) |
| **Cross-repo runtime bridge** | — | — | **NONE IDENTIFIED** | **GAP** |

### 1.8 Persistence Bridge Communication
| Channel | Provider | Consumer | Mechanism | Status |
|---|---|---|---|---|
| SICI Persistence Bridge | SICI | (server) | zachary-ai-persistence.js | CONTRACT ONLY (no server impl) |
| DCC JSON Persistence | DCC | DCC | fs.writeFile | ACTIVE |
| AIDRH JSONL Ledger | AIDRH | AIDRH | append-only file | ACTIVE |
| ZBC SQLite | ZBC | ZBC | sqlite3 | ACTIVE |

### 1.9 Capability Adapter Communication
| Channel | Provider | Consumer | Mechanism | Status |
|---|---|---|---|---|
| ZBC Evidence Adapter | ZBC | SICI | zbc-evidence-adapter.js (read-only) | ACTIVE (code) |
| DDC Research Adapter | DCC | AIDRH | ddc_research_adapter.py | ACTIVE (code) |
| LLM Provider Adapter | Multiple | ZBC | ai_gateway_v570.py (multi-provider) | ACTIVE (code) |
| Platform Adapter | Multiple | ZBC | platform_adapters/ | ACTIVE (directory) |

### 1.10 Evidence Flow Communication
```
ZBC Production (notes/events/ai_filter_log)
    │
    ▼ read-only
SICI zbc-evidence-adapter.js
    │
    ▼
SICI Zachary AI Core (evidence-first analysis)
    │
    ▼ (persistence bridge - contract only)
    (no server implementation)

DCC Shadow Learning (Research→Candidate→Shadow→Evidence→Review→Verify→Promotion)
    │
    ▼
DCC Evidence Bundle (evidence-bundle.js)
    │
    ▼ (manual promotion)
AIDRH Research Records (JSONL append-only)
    │
    ▼
AIDRH Capability Registry (CAP-2026-XXX)
    │
    ▼ (governance)
All repos (GLOBAL-CROSS-REPOSITORY-BASELINE.md)
```

### 1.11 Learning Flow Communication
```
ZBC: data_feedback_loop.py → ai_learning_engine.py → updated patterns (in DB)
    │
    ▼ (no cross-repo learning export)

SICI: research-learning.js → localStorage (browser-only)
    │
    ▼ (no cross-repo learning export)

DCC: learning-store.js → shadow-learning.js → evidence-bundle.js → (manual)
    │
    ▼ ddc_research_adapter.py
AIDRH: research records → capability registry → (governance to all repos)
    │
    ▼ (no automated feedback to ZBC/SICI)
```

## 2. Communication Gap Analysis

| Gap | Description | Impact | Severity |
|---|---|---|---|
| No cross-repo event bus | Repos cannot notify each other of state changes | Manual coordination required | MEDIUM |
| SICI persistence bridge no server | zachary-ai-persistence.js has no server endpoint | Learning data lost on browser clear | HIGH |
| No automated learning feedback | AIDRH research doesn't automatically feed back to ZBC/SICI | Learning is manual | MEDIUM |
| ZBC evidence API not documented | SICI adapter references ZBC API but no OpenAPI/schema | Contract is implicit | MEDIUM |
| No cross-repo callback mechanism | Async operations cannot notify other repos | Polling required | LOW |
| DCC in-memory state | Learning/snapshot/change-plan state lost on restart | No persistence | HIGH |

## 3. Communication Security Assessment

| Channel | Encryption | Auth | Rate Limit | Status |
|---|---|---|---|---|
| ZBC Web API | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED |
| DCC AI Bridge | No (localhost only) | None (127.0.0.1) | No | ACCEPTABLE (localhost) |
| GitHub API | TLS | Token/PAT | GitHub default | ACTIVE |
| LLM Providers | TLS | API Key | Provider default | ACTIVE |
| Chrome CDP | No (localhost) | None | No | ACCEPTABLE (localhost) |
| WeChat API | TLS | WebHook Key | Provider default | ACTIVE |
| Cross-repo file contracts | N/A | N/A | N/A | N/A |

**Verification**: PARTIAL — Communication channels identified from source code. Runtime connectivity, authentication, and encryption for ZBC Web API are NOT_VERIFIED. DCC localhost binding (127.0.0.1) is confirmed in config.js.