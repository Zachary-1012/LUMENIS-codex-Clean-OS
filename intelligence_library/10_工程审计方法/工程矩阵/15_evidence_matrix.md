# 15 — Evidence Matrix (证据矩阵)

> Verification: PARTIAL — Evidence flows identified from source code; evidence integrity NOT_VERIFIED (no cryptographic verification)

## 1. Evidence Source Inventory

| Evidence ID | Source Repo | Source File | Evidence Type | Owner | Sensitivity | Retention |
|---|---|---|---|---|---|---|
| EV-ZBC-001 | ZBC | notes table | Production content (notes) | ZBC | PII (author info) | Permanent |
| EV-ZBC-002 | ZBC | events table | Event clustering results | ZBC | Business | Permanent |
| EV-ZBC-003 | ZBC | ai_filter_log table | AI filtering decisions | ZBC | Operational | Permanent |
| EV-ZBC-004 | ZBC | collection_logs table | Collection operations | ZBC | Operational | Permanent |
| EV-ZBC-005 | ZBC | collector_quality_log table | Collection quality scores | ZBC | Operational | Permanent |
| EV-ZBC-006 | ZBC | note_review_history table | Review decisions | ZBC | Operational | Permanent |
| EV-ZBC-007 | ZBC | feedback_keywords table | User feedback | ZBC | Business | Permanent |
| EV-ZBC-008 | ZBC | app_evidence.py | Evidence generation logic | ZBC | Code | Permanent |
| EV-ZBC-009 | ZBC | evaluation_system.py | System quality metrics | ZBC | Operational | Permanent |
| EV-SICI-001 | SICI | zachary-ai-core.js | AI runtime evidence-first logic | SICI | Code | Permanent |
| EV-SICI-002 | SICI | zbc-evidence-adapter.js | Read-only ZBC evidence access | SICI | Code | Permanent |
| EV-SICI-003 | SICI | localStorage | Browser-side evidence cache | SICI | User data | Session |
| EV-DCC-001 | DCC | evidence-bundle.js | Evidence bundle creation/validation | DCC | Code | Permanent |
| EV-DCC-002 | DCC | learning-store.js | Learning cases/patterns/lessons | DCC | Operational | In-memory (lost on restart) |
| EV-DCC-003 | DCC | shadow-learning.js | Shadow learning lifecycle evidence | DCC | Operational | In-memory |
| EV-DCC-004 | DCC | data/baseline.json | Baseline rules evidence | DCC | Governance | Permanent (file) |
| EV-AIDRH-001 | AIDRH | data/research/records.jsonl | Research records (append-only) | AIDRH | Governance | Permanent (append-only) |
| EV-AIDRH-002 | AIDRH | GLOBAL-CROSS-REPOSITORY-BASELINE.md | Immutable baseline | AIDRH | Governance | Permanent (immutable) |
| EV-AIDRH-003 | AIDRH | CAPABILITY-REGISTRY.md | Capability registration evidence | AIDRH | Governance | Permanent |
| EV-AIDRH-004 | AIDRH | SHADOW-LEARNING-PROTOCOL.md | Shadow learning protocol | AIDRH | Governance | Permanent |
| EV-AIDRH-005 | AIDRH | AI-COLLABORATION-PROTOCOL.md | AI collaboration rules | AIDRH | Governance | Permanent |

## 2. Evidence Flow Mapping

### 2.1 Production Evidence Flow (ZBC → SICI)
```
ZBC notes/events/ai_filter_log (SQLite)
    │
    ▼ HTTP GET (read-only)
SICI zbc-evidence-adapter.js
    │
    ▼
SICI zachary-ai-core.js (evidence-first analysis)
    │
    ▼ localStorage
SICI browser cache (session only)
```
**Contract**: zbc-evidence-adapter.js (read-only, no write)  
**Risk**: No API schema, no auth, no encryption in transit verified  
**Status**: NOT_VERIFIED (runtime connectivity not tested)

### 2.2 Learning Evidence Flow (DCC → AIDRH)
```
DCC learning-store.js (in-memory cases/patterns/lessons)
    │
    ▼ shadow-learning.js lifecycle
DCC evidence-bundle.js (validated bundle)
    │
    ▼ manual promotion (no automated flow)
AIDRH data/research/records.jsonl (append-only ledger)
    │
    ▼
AIDRH CAPABILITY-REGISTRY.md (registered capability)
    │
    ▼ governance reference
All repos (GLOBAL-CROSS-REPOSITORY-BASELINE.md)
```
**Contract**: ddc_research_adapter.py (format conversion)  
**Risk**: DCC learning state is in-memory only, lost on restart; promotion is manual  
**Status**: PARTIAL (code exists, automated flow not implemented)

### 2.3 Research Evidence Flow (AIDRH → All)
```
AIDRH research records (JSONL)
    │
    ▼ manual reference
All repos (documentation references)
    │
    ▼
No automated consumption by ZBC/SICI/DCC
```
**Contract**: GLOBAL-CROSS-REPOSITORY-BASELINE.md (governance)  
**Risk**: Research findings don't automatically feed back to production  
**Status**: PARTIAL (governance only, no automated integration)

### 2.4 Feedback Evidence Flow (ZBC Internal)
```
ZBC user feedback → feedback_keywords table
    │
    ▼
ZBC data_feedback_loop.py
    │
    ▼
ZBC ai_learning_engine.py → updated patterns (in DB)
    │
    ▼
ZBC ai_analyzer.py (uses learned patterns)
```
**Contract**: Internal (no cross-repo)  
**Status**: ACTIVE (production)

## 3. Evidence Integrity Assessment

| Criterion | ZBC | SICI | DCC | AIDRH | Industry Standard (IETF AAT) |
|---|---|---|---|---|---|
| Append-only | No (SQLite R/W) | No (localStorage) | No (JSON R/W) | Yes (JSONL) | Required |
| Cryptographic hash | No | No | No | No | Required (SHA-256) |
| Per-record signature | No | No | No | No | Required (HMAC/ECDSA) |
| Hash chaining | No | No | No | No | Required |
| Identity context | NOT_VERIFIED | No | No | No | Required |
| Timestamp | Yes (SQLite) | No | No | Yes (JSONL) | Required (UTC) |
| Full payload | Partial (ai_filter_log) | No | Partial (bundle) | Yes (research records) | Required |
| Evidence ID | note_id, event_id | No | bundle_id | R-YYYY-NNNN | Required |
| Tamper-evident | No | No | No | No (append-only, but no hash) | Required |
| External anchoring | No | No | No | No | Recommended |

## 4. Evidence Cross-Reference (source_repo/source_commit/source_file tracking)

| Evidence Item | source_repo | source_commit | source_file | source_owner | target_repo | contract_id |
|---|---|---|---|---|---|---|
| ZBC evidence read by SICI | ZBC | bd6ed8d | (API, not file) | ZBC | SICI | (no formal contract) |
| DCC learning → AIDRH | DCC | b0de3c5 | learning-store.js | DCC | AIDRH | ddc_research_adapter.py |
| AIDRH baseline → all | AIDRH | 930c646 | GLOBAL-CROSS-REPOSITORY-BASELINE.md | AIDRH | All | (immutable doc) |
| AIDRH capability registry → all | AIDRH | 930c646 | CAPABILITY-REGISTRY.md | AIDRH | All | CAP-2026-0001/002/003 |
| DCC CI-VERIFY → SICI | DCC | (workflow) | reusable-verify.yml | DCC | SICI | @448ba21 |
| Design tokens → SICI+DCC | (shared) | 2210afc9 | ZBIP_DESIGN_TOKENS.css | UNASSIGNED | SICI, DCC | (no contract) |

**Finding**: Most cross-repo evidence sharing lacks formal contract_id, promotion_id, and evidence_id tracking. Only AIDRH research records have structured IDs (R-YYYY-NNNN).

## 5. Evidence Protection Assessment

| Protection | ZBC | SICI | DCC | AIDRH | Status |
|---|---|---|---|---|---|
| Historical evidence protection | NOT_VERIFIED | No | No | Append-only | PARTIAL |
| Evidence deletion prevention | No (SQLite DELETE possible) | No (localStorage clear) | No (JSON file write) | Append-only (but file can be edited) | FAIL |
| Evidence access audit | NOT_VERIFIED | No | No | No | NOT_VERIFIED |
| Evidence backup | NOT_VERIFIED | No (browser) | No (in-memory) | Git (repo) | NOT_VERIFIED |
| Evidence retention policy | No (permanent) | Session | No (in-memory) | Permanent (git) | FAIL |

## 6. Evidence Gap Summary

| Gap | Severity | Affected Repos | Recommended Action |
|---|---|---|---|
| No cryptographic evidence integrity | HIGH | All | Implement IETF AAT standard (hash chaining + signatures) |
| DCC learning state in-memory | HIGH | DCC | Persist to JSON files or AIDRH ledger |
| No automated evidence flow ZBC→AIDRH | MEDIUM | ZBC, AIDRH | Build API for ZBC evidence to AIDRH ledger |
| No evidence retention policy | MEDIUM | ZBC, DCC | Define TTL and archival strategy |
| No formal evidence contracts | MEDIUM | All | Define contract_id for each cross-repo evidence flow |
| SICI evidence lost on browser clear | MEDIUM | SICI | Implement persistence bridge (currently contract only) |
| No evidence access auditing | MEDIUM | All | Add audit log for evidence access |

**Verification**: PARTIAL — Evidence flows identified from source code analysis. Evidence integrity (cryptographic verification, tamper-evidence) NOT_VERIFIED — no live testing performed. AIDRH JSONL append-only is confirmed by file format, but no hash verification exists.