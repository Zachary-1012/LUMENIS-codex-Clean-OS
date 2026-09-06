# 07 — Symbol/Function对账 (Symbol & Function Reconciliation)

> Verification: PARTIAL — Symbols extracted from read source files; full symbol inventory NOT_VERIFIED (app.py 264KB not fully parsed)

## 1. ZBC Key Symbols (from read files)

### 1.1 database.py — Key Functions/Classes
| Symbol | Type | Signature (estimated) | Purpose |
|---|---|---|---|
| get_db | function | get_db() -> sqlite3.Connection | Get database connection |
| init_db | function | init_db() -> None | Initialize schema (15 CREATE TABLE) |
| query_db | function | query_db(query, args=(), one=False) -> list/dict | Query helper |
| execute_db | function | execute_db(query, args=()) -> int | Execute write, return lastrowid |
| close_db | function | close_db(e=None) -> None | Close connection |
| Note | class | Note(note_id, title, content, ...) | Note model (70+ fields) |
| Event | class | Event(event_key, title, ...) | Event model |
| DailyReport | class | DailyReport(report_date, ...) | Report model |

### 1.2 models.py — MODEL_REGISTRY (22 entries)
```python
MODEL_REGISTRY = {
    "notes": Note, "events": Event, "comments": Comment,
    "note_comments": NoteComment, "daily_reports": DailyReport,
    "daily_digest": DailyDigest, "weekly_events": WeeklyEvent,
    "web_topics": WebTopic, "web_events": WebEvent,
    "web_mentions": WebMention, "brand_industry_monitor": BrandIndustryMonitor,
    "collection_counters": CollectionCounter, "collection_logs": CollectionLog,
    "collector_quality_log": CollectorQualityLog, "ai_filter_log": AIFilterLog,
    "event_insights": EventInsight, "event_mentions": EventMention,
    "note_review_history": NoteReviewHistory, "feedback_keywords": FeedbackKeyword,
    "system_config": SystemConfig, "web_sources": WebSource, "web_runs": WebRun
}
```

### 1.3 config.py — Key Symbols
| Symbol | Type | Purpose |
|---|---|---|
| ConfigManager | class | Unified config (env + JSON) |
| get_config | function | Get global config instance |
| TAIKOO_PORT | const | 8200 |
| ZBC_DB_PATH | const | data/monitor.db |

### 1.4 ai_analyzer.py — Key Symbols (estimated)
| Symbol | Type | Purpose |
|---|---|---|
| analyze_note | function | AI analysis of single note |
| batch_analyze | function | Batch analysis |
| get_sentiment | function | Sentiment scoring |
| get_risk_level | function | Risk assessment |
| AIAnalyzer | class | Main analyzer class |

### 1.5 event_graph.py — Key Symbols (estimated)
| Symbol | Type | Purpose |
|---|---|---|
| build_event_graph | function | Build event relation graph |
| cluster_notes | function | Cluster notes into events |
| EventGraph | class | Graph data structure |
| find_related_events | function | Event relation query |

### 1.6 app.py — Symbols NOT_VERIFIED
app.py is 264KB. Full function/class inventory requires complete file parsing. Estimated 100+ route handlers and helper functions.

**Status**: NOT_VERIFIED — complete symbol inventory for app.py not obtained.

## 2. SICI Key Symbols

### 2.1 zachary-ai-core.js
| Symbol | Type | Purpose |
|---|---|---|
| ZacharyAICore | class/object | Main AI runtime |
| analyzeWithEvidence | function | Evidence-first analysis |
| getCapabilities | function | List AI capabilities |
| processQuery | function | Process user query |

### 2.2 effective-rules.js
| Symbol | Type | Purpose |
|---|---|---|
| resolveEffectiveRules | function | 4-layer resolution (Baseline 100 > Supplement 95 > Product 90 > Capability 80) |
| RULE_PRIORITY | const | Priority levels |
| EffectiveRulesEngine | class | Rules engine |

### 2.3 preflight.js
| Symbol | Type | Purpose |
|---|---|---|
| runPreflight | function | Execute 10 checks |
| PREFLIGHT_CHECKS | const | Check definitions |
| PreflightResult | class | Result object |

### 2.4 capability-registry.js
| Symbol | Type | Purpose |
|---|---|---|
| registerCapability | function | Register capability |
| getCapability | function | Get by ID |
| listCapabilities | function | List all |
| getCapabilitiesByOwner | function | Filter by owner |
| getCapabilityDependencies | function | Get deps |
| CAPABILITY_REGISTRY | const | Internal registry |

### 2.5 zbc-evidence-adapter.js
| Symbol | Type | Purpose |
|---|---|---|
| ZBCEvidenceAdapter | class | Read-only ZBC evidence access |
| getEvidence | function | Fetch evidence |
| searchEvidence | function | Search evidence |

## 3. DCC Key Symbols

### 3.1 server.js — API Route Handlers
| Symbol | Type | Purpose |
|---|---|---|
| createServer | function | Create HTTP server |
| handleRequest | function | Request router |
| routes | object | Route table (40+ entries) |
| PORT | const | 8787 |
| HOST | const | 127.0.0.1 |

### 3.2 learning-store.js
| Symbol | Type | Purpose |
|---|---|---|
| LearningStore | class | CRUD for cases/patterns/lessons |
| createCase | function | Create learning case |
| getCase | function | Get case by ID |
| listCases | function | List cases |
| createPattern | function | Create pattern |
| createLesson | function | Create lesson |

### 3.3 shadow-learning.js
| Symbol | Type | Purpose |
|---|---|---|
| ShadowLearningEngine | class | Lifecycle engine |
| analyzeCandidate | function | Research→Candidate |
| runShadow | function | Candidate→Shadow |
| promoteToEvidence | function | Shadow→Evidence |
| SHADOW_STATES | const | Lifecycle states |

### 3.4 evidence-bundle.js
| Symbol | Type | Purpose |
|---|---|---|
| EvidenceBundle | class | Bundle creation/validation |
| createBundle | function | Create from evidence |
| validateBundle | function | Validate completeness |
| EVIDENCE_REQUIRED_FIELDS | const | Required fields |

### 3.5 effective-rules.js (server)
| Symbol | Type | Purpose |
|---|---|---|
| resolveRules | function | Server-side 4-layer resolution |
| loadRules | function | Load from JSON files |
| EffectiveRulesResolver | class | Resolver class |

### 3.6 snapshot.js
| Symbol | Type | Purpose |
|---|---|---|
| createSnapshot | function | Capture state |
| lockSnapshot | function | Lock for change |
| verifyLock | function | Verify lock integrity |
| SnapshotManager | class | Manager class |

## 4. AIDRH Key Symbols

### 4.1 tools/research_id.py
| Symbol | Type | Purpose |
|---|---|---|
| generate_research_id | function | R-YYYY-NNNN format |
| ResearchIDGenerator | class | ID generator |

### 4.2 tools/secret_scan.py
| Symbol | Type | Purpose |
|---|---|---|
| scan_secrets | function | Scan for secrets |
| SecretScanner | class | Scanner class |
| SENSITIVE_KEY_PATTERNS | const | Patterns to detect |

### 4.3 tools/runtime_preflight.py
| Symbol | Type | Purpose |
|---|---|---|
| run_preflight | function | 7-check repository integrity |
| PREFLIGHT_CHECKS | const | 7 check definitions |

### 4.4 src/adapters/ddc_research_adapter.py
| Symbol | Type | Purpose |
|---|---|---|
| DDCResearchAdapter | class | DDC compatibility adapter |
| convert_research_format | function | DDC→AIDRH format |

## 5. Cross-Repo Symbol Alignment

| Concept | ZBC Symbol | SICI Symbol | DCC Symbol | AIDRH Symbol | Alignment |
|---|---|---|---|---|---|
| Rules Engine | safety_boundary.check | resolveEffectiveRules | resolveRules | PLATFORM_BASELINE | SEMANTIC (different impl) |
| Preflight | runtime_preflight.run | runPreflight | startup-preflight | run_preflight | SEMANTIC (4 impls) |
| Capability Registry | function_registry | CAPABILITY_REGISTRY | /api/capabilities | CAPABILITY-REGISTRY.md | SEMANTIC (different formats) |
| Evidence | app_evidence | ZBCEvidenceAdapter | EvidenceBundle | GLOBAL-CROSS-REPOSITORY-BASELINE | SEMANTIC (different layers) |
| Learning | ai_learning_engine | research-learning | LearningStore | research records | SEMANTIC (different layers) |
| Snapshot | — | — | SnapshotManager | — | DCC-ONLY |
| Shadow Learning | — | — | ShadowLearningEngine | SHADOW-LEARNING-PROTOCOL | COMPLEMENTARY |
| Secret Scan | security_scanner | — | — | SecretScanner | SEMANTIC (different scope) |

## 6. Symbol Inventory Completeness

| Repo | Total Symbols (est.) | Verified | Not Verified | Completeness |
|---|---|---|---|---|
| ZBC | 300+ (app.py alone ~150) | ~80 | ~220 | ~27% |
| SICI | ~80 | ~50 | ~30 | ~63% |
| DCC | ~100 | ~60 | ~40 | ~60% |
| AIDRH | ~40 | ~25 | ~15 | ~63% |

**Overall Symbol Gate**: NOT_VERIFIED — ZBC app.py (264KB) requires full parsing for complete symbol inventory. This is the largest gap.

**Recommendation**: Use `python -c "import ast; ..."` to extract all function/class definitions from app.py in a follow-up audit pass.