# 19 — Supplement Matrix (补充矩阵)

> Supplements are INCREMENTAL only. They add capabilities/rules below Baseline priority (95 < 100). They never override baseline.  
> Verification: PASS (supplements extracted from DCC protocols/registry.json and effective-rules.js)

## 1. Supplement Definition

Per DCC `protocols/registry.json` (SHA: 062813d3, 3375 bytes) and `server/supplement-protocol.js`

### 1.1 Active Supplement Protocols
| Supplement ID | Name | Owner | Priority | Type | Status | Source |
|---|---|---|---|---|---|---|
| SUP-DCC-001 | Effective Rules Supplement | DCC | 95 | Rule Set | ACTIVE | data/rules/product-rules.json |
| SUP-DCC-002 | Capability Constraints Supplement | DCC | 95 | Permission Gate | ACTIVE | data/rules/capability-constraints.json |
| SUP-AIDRH-001 | Research ID Generator | AIDRH | 90 | Capability | ACTIVE (reusable) | CAP-2026-0001 |
| SUP-AIDRH-002 | Shadow Lifecycle Protocol | AIDRH | 90 | Capability | ACTIVE (reusable) | CAP-2026-0002 |
| SUP-AIDRH-003 | DDC Research Adapter | AIDRH | 90 | Capability | ACTIVE (reusable) | CAP-2026-0003 |
| SUP-SICI-001 | ZBC Evidence Adapter | SICI | 90 | Integration | ACTIVE | zbc-evidence-adapter.js |
| SUP-SICI-002 | Permission-Gated Tool Registry | SICI | 90 | Security | ACTIVE | zachary-tool-registry.js |
| SUP-ZBC-001 | Local AI Client | ZBC | 90 | Capability | ACTIVE | local_ai_client.py |
| SUP-ZBC-002 | Web Topic Discovery | ZBC | 90 | Capability | ACTIVE | web_topic_discovery.py |

## 2. Supplement Priority Model

```
Priority 100: Baseline (IMMUTABLE, cannot be overridden)
     │
Priority 95:  Supplements (incremental, add-only)
     │         - DCC product rules
     │         - DCC capability constraints
     │
Priority 90:  Product-specific (repo-level)
     │         - ZBC features
     │         - SICI features
     │         - DCC features
     │
Priority 80:  Capability-level (individual features)
```

**Rule**: Higher priority wins. Baseline (100) always wins over supplements (95). Supplements always win over product (90) and capability (80).

**Verification**: This 4-layer model is implemented in both SICI `effective-rules.js` and DCC `server/effective-rules.js`.

## 3. Supplement Compliance Check

| Supplement | Incremental Only? | Doesn't Override Baseline? | Has Contract? | Has Owner? | Status |
|---|---|---|---|---|---|
| SUP-DCC-001 (Effective Rules) | Yes | Yes (priority 95) | Yes (product-rules.json) | DCC | PASS |
| SUP-DCC-002 (Capability Constraints) | Yes | Yes (priority 95) | Yes (constraints.json) | DCC | PASS |
| SUP-AIDRH-001 (Research ID) | Yes | Yes (priority 90) | Yes (CAP-2026-0001) | AIDRH | PASS |
| SUP-AIDRH-002 (Shadow Lifecycle) | Yes | Yes (priority 90) | Yes (CAP-2026-0002) | AIDRH | PASS |
| SUP-AIDRH-003 (DDC Adapter) | Yes | Yes (priority 90) | Yes (CAP-2026-0003) | AIDRH | PASS |
| SUP-SICI-001 (ZBC Evidence) | Yes (read-only) | Yes | PARTIAL (no OpenAPI) | SICI | PARTIAL |
| SUP-SICI-002 (Tool Registry) | Yes | Yes | Yes (permission gates) | SICI | PASS |
| SUP-ZBC-001 (Local AI) | Yes | Yes | No | ZBC | PARTIAL |
| SUP-ZBC-002 (Web Discovery) | Yes | Yes | No | ZBC | PARTIAL |

## 4. Supplement Risk Assessment

| Risk | Supplement | Severity | Mitigation |
|---|---|---|---|
| Supplement silently overrides baseline | None identified | — | Priority model prevents (95 < 100) |
| Supplement creates second authority | Multiple capability registries | MEDIUM | Consolidate to AIDRH canonical registry |
| Supplement without contract | ZBC local AI, web discovery | LOW | Add contracts for cross-repo use |
| Supplement accumulation | 9 active supplements | LOW | Regular review and pruning |
| Supplement versioning | Most unversioned | MEDIUM | Add version to all supplements |

## 5. Supplement vs Baseline Conflict Check

| Baseline | Supplement | Conflict? | Resolution |
|---|---|---|---|
| BASE-001 (Zachary独立身份) | SUP-SICI-001 (ZBC Evidence) | No — read-only, doesn't merge identity | PASS |
| BASE-002 (ZBC独立边界) | SUP-SICI-001 (ZBC Evidence) | No — read-only adapter, doesn't modify ZBC | PASS |
| BASE-005 (Ownership) | Multiple capability registries | Potential — 4 registries = multiple authorities | CONFLICT (see Conflict Items) |
| BASE-007 (Evidence优先) | All supplements | No — all supplements should be evidence-based | PASS |
| BASE-011 (Supplement增量) | All supplements | No — priority model enforces increment-only | PASS |
| BASE-013 (禁止第二权威) | Multiple registries | Yes — 4 capability registries | CONFLICT |
| BASE-016 (L3禁止复制) | Effective Rules duplication | Potential — same logic in SICI+DCC | PARTIAL (same spec, separate impl) |
| BASE-021 (禁止硬编码Secret) | All supplements | No — no secrets in supplements | PASS |

## 6. Supplement Governance

| Governance Step | Implemented? | Evidence |
|---|---|---|
| Supplement registration | PARTIAL | DCC protocols/registry.json, AIDRH CAPABILITY-REGISTRY.md |
| Supplement versioning | PARTIAL | AIDRH CAP IDs, DCC unversioned |
| Supplement approval workflow | PARTIAL | DCC shadow-learning Review stage |
| Supplement audit trail | No | No log of supplement changes |
| Supplement expiration | No | No TTL on supplements |
| Supplement conflict detection | PARTIAL | effective-rules.js priority resolution |
| Supplement rollback | No | No rollback mechanism |

## 7. Recommended Supplement Additions (Post-Consolidation)

| Proposed Supplement | Owner | Priority | Purpose | Prerequisite |
|---|---|---|---|---|
| Cross-repo Event Bus | DCC | 95 | Event-driven communication | Phase 3 consolidation |
| Unified Evidence API | AIDRH | 95 | IETF AAT-compatible evidence ledger | Phase 3 consolidation |
| Contract Testing Suite | AIDRH | 95 | Automated contract verification | Phase 2 consolidation |
| ZBC Evidence API Schema | ZBC | 90 | OpenAPI for ZBC evidence | Phase 2 consolidation |
| SICI Persistence Endpoint | DCC | 90 | Server for SICI persistence bridge | Phase 2 consolidation |

**Verification**: PASS — Supplements extracted from DCC protocol registry, AIDRH capability registry, and source code. Priority model verified in effective-rules.js implementations. No supplement overrides baseline (all priority ≤ 95 < 100).