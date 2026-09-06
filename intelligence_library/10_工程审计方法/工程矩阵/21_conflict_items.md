# 21 — 冲突项 (Conflict Items)

> Per instruction: 矛盾时状态设为 CONFLICT，不得自行选择，需 Human Gate.  
> Verification: PASS (all conflicts identified from source code analysis, no AI resolution)

## 1. CONFLICT-001: ZBC Database Schema vs Model Registry Mismatch

| Property | Value |
|---|---|
| **Severity** | HIGH |
| **Repos** | ZBC |
| **Files** | database.py (15 CREATE TABLE), models.py (22 MODEL_REGISTRY entries) |
| **Conflict** | 7 tables in models.py are not in database.py CREATE TABLE statements |
| **Missing Tables** | weekly_events, web_topics, web_events, brand_industry_monitor, collection_counters, system_config, (comments — need to verify) |
| **Possible Resolutions** | A) Tables created by migrations 009/010; B) Tables created dynamically in app code; C) Tables are legacy and no longer exist; D) Model registry is ahead of schema |
| **Why CONFLICT** | Cannot determine actual production DB state without querying. Code analysis alone is insufficient. |
| **Impact** | Runtime errors if code accesses non-existent tables. Data loss if tables are dropped but code still references. |
| **Human Gate Required** | YES — Query production SQLite .tables and compare with models.py MODEL_REGISTRY |
| **Status** | CONFLICT |

## 2. CONFLICT-002: Multiple Capability Registries (Second Authority Risk)

| Property | Value |
|---|---|
| **Severity** | HIGH |
| **Repos** | ZBC, SICI, DCC, AIDRH |
| **Files** | ZBC function_registry.py + function_map.json; SICI capability-registry.js; DCC /api/capabilities; AIDRH CAPABILITY-REGISTRY.md |
| **Conflict** | 4 separate capability registration mechanisms. BASE-013 prohibits "制造第二权威". Multiple registries create potential for conflicting capability definitions. |
| **Possible Resolutions** | A) AIDRH as canonical registry, all others become local caches; B) Each repo owns its own capabilities, AIDRH only indexes; C) Unified API in AIDRH, all repos register via API |
| **Why CONFLICT** | Ownership principle (BASE-005) says one authoritative owner, but current state has 4. Cannot unilaterally decide consolidation approach. |
| **Impact** | Capability definition drift, inconsistent discovery, potential conflicts in cross-repo usage. |
| **Human Gate Required** | YES — Decide canonical registry owner and consolidation approach |
| **Status** | CONFLICT |

## 3. CONFLICT-003: Effective Rules Duplication (SICI Frontend vs DCC Server)

| Property | Value |
|---|---|
| **Severity** | MEDIUM |
| **Repos** | SICI, DCC |
| **Files** | SICI js/effective-rules.js (12455B, frontend); DCC server/effective-rules.js (8543B, server) |
| **Conflict** | Same 4-layer priority model implemented twice in different languages/runtimes. Logic may diverge over time. No shared contract or test suite. |
| **Possible Resolutions** | A) DCC server as authoritative, SICI calls API; B) Shared JSON rules file, both implementations read same data; C) Keep both but add contract testing |
| **Why CONFLICT** | BASE-016 (L3禁止跨库复制) suggests no code copying, but BASE-015 (L2经Contract可复用) allows via contract. Current state is code duplication without formal contract. |
| **Impact** | Rule resolution inconsistency between mobile and desktop. Silent divergence as each evolves independently. |
| **Human Gate Required** | YES — Decide consolidation approach (API vs shared JSON vs dual with tests) |
| **Status** | CONFLICT |

## 4. CONFLICT-004: Design Token Divergence (ZBC vs SICI/DCC)

| Property | Value |
|---|---|
| **Severity** | LOW |
| **Repos** | ZBC, SICI, DCC |
| **Files** | ZBIP_DESIGN_TOKENS.css |
| **Conflict** | SICI and DCC have identical SHA (2210afc9), but ZBC has different SHA (137a6f0e). No canonical owner assigned. No versioning. |
| **Possible Resolutions** | A) AIDRH as canonical owner, all repos reference; B) ZBC intentionally divergent (different product), document as separate; C) Merge ZBC changes back to shared |
| **Why CONFLICT** | Cannot determine if ZBC divergence is intentional or accidental without comparing content. |
| **Impact** | UI inconsistency across Zachary AI platforms. |
| **Human Gate Required** | YES — Compare ZBC vs shared token content, decide if intentional |
| **Status** | CONFLICT |

## 5. CONFLICT-005: Runtime Preflight — 4 Implementations, No Standard

| Property | Value |
|---|---|
| **Severity** | MEDIUM |
| **Repos** | ZBC, SICI, DCC, AIDRH |
| **Files** | ZBC runtime_preflight.py (14928B); SICI preflight.js (9850B, 10 checks); DCC startup-preflight.js (5223B); AIDRH runtime_preflight.py (7 checks) |
| **Conflict** | Same concept (startup integrity verification) implemented 4 times with different check sets, different severity levels, no shared standard. AIDRH claims to be "adapted from DDC" but has different check count. |
| **Possible Resolutions** | A) AIDRH defines standard check set, all repos implement; B) DCC provides reference implementation, others adapt; C) Keep separate but document differences |
| **Why CONFLICT** | BASE-005 (Ownership) requires one owner, but no owner assigned for preflight standard. |
| **Impact** | Inconsistent startup verification. Some repos may miss critical checks. |
| **Human Gate Required** | YES — Define standard preflight check set and assign owner |
| **Status** | CONFLICT |

## 6. CONFLICT-006: Learning Logic Fragmentation (4 Different Approaches)

| Property | Value |
|---|---|
| **Severity** | HIGH |
| **Repos** | ZBC, SICI, DCC, AIDRH |
| **Files** | ZBC ai_learning_engine.py + data_feedback_loop.py; SICI research-learning.js; DCC learning-store.js + shadow-learning.js; AIDRH research records |
| **Conflict** | Learning implemented in 4 completely different ways: ZBC (feedback-driven pattern learning in DB), SICI (browser localStorage UI), DCC (in-memory lifecycle engine), AIDRH (append-only research ledger). No unified learning flow. No automated cross-repo learning. |
| **Possible Resolutions** | A) DCC owns learning engine, AIDRH owns research registry, ZBC provides data, SICI consumes; B) Each repo keeps its own learning, AIDRH only aggregates research; C) Build unified learning API in AIDRH |
| **Why CONFLICT** | BASE-010 (双向受控学习) requires bidirectional learning, but current state is 4 isolated systems. Cannot unilaterally design unified architecture. |
| **Impact** | Knowledge fragmentation. Learning in one repo doesn't benefit others. No evidence-based learning across repos. |
| **Human Gate Required** | YES — Design unified learning architecture with clear ownership |
| **Status** | CONFLICT |

## 7. CONFLICT-007: Evidence Flow — No Automated Cross-Repo Evidence

| Property | Value |
|---|---|
| **Severity** | HIGH |
| **Repos** | All |
| **Files** | ZBC app_evidence.py; SICI zbc-evidence-adapter.js (read-only); DCC evidence-bundle.js; AIDRH JSONL ledger |
| **Conflict** | BASE-007 (Evidence优先) requires all decisions evidence-based, but there is no automated evidence flow between repos. ZBC production evidence doesn't reach AIDRH ledger. AIDRH research doesn't feed back to ZBC. DCC evidence bundles don't automatically register in AIDRH. |
| **Possible Resolutions** | A) Build ZBC→AIDRH evidence API; B) Build AIDRH→ZBC research feedback API; C) DCC evidence bundles auto-register in AIDRH; D) All of the above in phased rollout |
| **Why CONFLICT** | Cannot design full evidence architecture without understanding performance requirements and data volumes. |
| **Impact** | Evidence is siloed. Governance decisions in AIDRH lack production evidence. Production in ZBC lacks research findings. |
| **Human Gate Required** | YES — Design evidence flow architecture and API contracts |
| **Status** | CONFLICT |

## 8. CONFLICT-008: SICI Persistence Bridge — Contract Without Implementation

| Property | Value |
|---|---|
| **Severity** | MEDIUM |
| **Repos** | SICI, DCC |
| **Files** | SICI js/zachary-ai-persistence.js (1504B, contract only) |
| **Conflict** | Persistence bridge defines interface for server-side persistence, but no server endpoint exists in DCC or any repo. Zachary AI state is localStorage-only. |
| **Possible Resolutions** | A) Implement DCC server endpoint for persistence; B) Implement in AIDRH; C) Remove contract and accept localStorage-only; D) Build new persistence service |
| **Why CONFLICT** | Cannot decide where to implement server without understanding deployment topology (DCC is localhost-only, may not be suitable for mobile persistence). |
| **Impact** | Zachary AI state lost on browser clear. No cross-device sync. Learning not persisted. |
| **Human Gate Required** | YES — Decide persistence service owner and deployment model |
| **Status** | CONFLICT |

## 9. CONFLICT-009: DCC Learning State In-Memory — Data Loss on Restart

| Property | Value |
|---|---|
| **Severity** | HIGH |
| **Repos** | DCC |
| **Files** | server/learning-store.js (25690B), server/shadow-learning.js (20303B) |
| **Conflict** | Learning cases, patterns, lessons, and shadow learning state are in-memory only. Despite having file-based persistence for baseline.json and rules/, learning data is not persisted. This contradicts the evidence-first principle (BASE-007) and historical evidence protection (BASE-009). |
| **Possible Resolutions** | A) Persist learning to JSON files like baseline.json; B) Persist to AIDRH ledger via API; C) Use SQLite; D) Accept in-memory for dev tool, document limitation |
| **Why CONFLICT** | DCC is a dev tool (localhost), but learning data should be durable per governance principles. Cannot decide persistence approach without performance requirements. |
| **Impact** | All learning progress lost on server restart. No audit trail for learning decisions. Shadow learning promotions lost. |
| **Human Gate Required** | YES — Decide persistence approach for DCC learning state |
| **Status** | CONFLICT |

## 10. CONFLICT-010: No Cross-Repo Event Bus — Architecture Gap

| Property | Value |
|---|---|
| **Severity** | MEDIUM |
| **Repos** | All |
| **Conflict** | No event-driven communication between repos. All integration is via polling or manual file copying. This creates stale data and missed state changes. However, adding an event bus is a significant architectural change. |
| **Possible Resolutions** | A) Webhook-based event notification; B) Shared event log in AIDRH; C) Polling with defined intervals; D) GitHub Actions as event bus |
| **Why CONFLICT** | Cannot decide event bus architecture without understanding real-time requirements and deployment topology. |
| **Impact** | Stale evidence, missed learning opportunities, manual coordination overhead. |
| **Human Gate Required** | YES — Decide if event bus is needed and what technology |
| **Status** | CONFLICT |

## 11. Conflict Summary

| ID | Severity | Domain | Human Gate | Status |
|---|---|---|---|---|
| CONFLICT-001 | HIGH | Database | YES | CONFLICT |
| CONFLICT-002 | HIGH | Governance | YES | CONFLICT |
| CONFLICT-003 | MEDIUM | Rules Engine | YES | CONFLICT |
| CONFLICT-004 | LOW | Design | YES | CONFLICT |
| CONFLICT-005 | MEDIUM | DevOps | YES | CONFLICT |
| CONFLICT-006 | HIGH | Learning | YES | CONFLICT |
| CONFLICT-007 | HIGH | Evidence | YES | CONFLICT |
| CONFLICT-008 | MEDIUM | Persistence | YES | CONFLICT |
| CONFLICT-009 | HIGH | Data Durability | YES | CONFLICT |
| CONFLICT-010 | MEDIUM | Architecture | YES | CONFLICT |

**Total Conflicts**: 10 (4 HIGH, 4 MEDIUM, 2 LOW)  
**All require Human Gate** — no conflicts resolved by AI per instruction.

**Verification**: PASS — All conflicts identified from source code analysis. No AI resolution attempted. All marked CONFLICT per instruction.