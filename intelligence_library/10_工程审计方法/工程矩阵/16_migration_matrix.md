# 16 — Migration Matrix (迁移矩阵)

> Verification: PARTIAL — Migration files identified; migration execution history NOT_VERIFIED

## 1. Database Migrations (ZBC Only)

### 1.1 Migration Files
| Migration ID | File | Size | SHA | Purpose | Status |
|---|---|---|---|---|---|
| 009 | migrations/009_global_bil_staging.sql | 8307B | 3264938a | Global BIL staging tables | NOT_VERIFIED (not fully read) |
| 010 | migrations/010_notes_subject_content_type.sql | 857B | 506bcf4e | Add subject_content_type to notes | NOT_VERIFIED (not fully read) |

### 1.2 Migration Framework
| Property | Value | Assessment |
|---|---|---|
| Framework | Custom (database_migrations.py) | Non-standard, no Alembic |
| Migration tracking | NOT_VERIFIED | No migration tracking table identified |
| Idempotency | CREATE TABLE IF NOT EXISTS | Safe for creates, but ALTER TABLE may not be idempotent |
| Rollback | No down migrations | Cannot roll back |
| Ordering | Numeric prefix (009, 010) | Gaps suggest earlier migrations were inline in database.py |
| Execution | database_migrations.py (17807B) | Custom runner, NOT_VERIFIED |

### 1.3 Schema Migration Risk
| Risk | Assessment | Severity |
|---|---|---|
| 7 tables in models.py not in CREATE TABLE | May be created by migrations 009/010 or dynamically | HIGH |
| No migration tracking | Cannot determine which migrations have been applied | HIGH |
| No down migrations | Cannot roll back failed migrations | MEDIUM |
| ALTER TABLE on large notes table | notes has 70+ columns, ALTER may be slow | MEDIUM |
| Migration 009 not fully read | 8307B suggests multiple table creates, may include missing 7 tables | MEDIUM |

## 2. Code Migration Paths

### 2.1 ZBC Version Migration
| From | To | Evidence | Risk |
|---|---|---|---|
| v4 | v5 | v4_upgrade/ directory, v4_smoke.py | NOT_VERIFIED |
| v5.8.9 | current | app_backup_v589.py (backup before upgrade) | Backup exists, but upgrade path NOT_VERIFIED |
| collector v1 | collector v2 | collector_v2/ directory, collector_v2_integration.py | Dual-running, NOT_VERIFIED |
| ref_gpt v1 | ref_gpt v2 | ref_gpt_v2/ directory | NOT_VERIFIED |

### 2.2 Cross-Repo Migration Paths
| Migration | Source | Target | Mechanism | Status |
|---|---|---|---|---|
| Learning data | DCC | AIDRH | ddc_research_adapter.py (format conversion) | ACTIVE (code) |
| Evidence | ZBC | SICI | zbc-evidence-adapter.js (read-only API) | ACTIVE (code) |
| Research findings | AIDRH | All | Documentation reference | MANUAL (no automated) |
| Capability registration | Any | AIDRH | CAPABILITY-REGISTRY.md (manual) | MANUAL |
| Design tokens | (shared) | SICI, DCC | File copy (identical SHA) | MANUAL |
| **ZBC → AIDRH evidence** | ZBC | AIDRH | **NOT IMPLEMENTED** | GAP |
| **AIDRH → ZBC research** | AIDRH | ZBC | **NOT IMPLEMENTED** | GAP |
| **SICI → DCC persistence** | SICI | DCC | **CONTRACT ONLY** (zachary-ai-persistence.js) | GAP |

## 3. Consolidation Migration Plan

### Phase 1: Foundation (Low Risk)
| Step | Action | Source | Target | Risk | Dependencies |
|---|---|---|---|---|---|
| 1.1 | Assign Design Tokens owner to AIDRH | SICI, DCC, ZBC | AIDRH | LOW | None |
| 1.2 | Standardize Runtime Preflight spec in AIDRH | ZBC, SICI, DCC | AIDRH | LOW | None |
| 1.3 | Enable GitHub push protection on all repos | — | All | LOW | None |
| 1.4 | Remove app_backup_v589.py from ZBC | ZBC | (git history) | LOW | Verify not imported |
| 1.5 | Add missing deps to ZBC requirements.txt | ZBC | ZBC | LOW | websocket-client, schedule |

### Phase 2: Contract Alignment (Medium Risk)
| Step | Action | Source | Target | Risk | Dependencies |
|---|---|---|---|---|---|
| 2.1 | Define OpenAPI schema for ZBC evidence API | ZBC | AIDRH (contract) | MEDIUM | ZBC API inventory |
| 2.2 | Align Effective Rules to DCC server reference | SICI | DCC (spec) | MEDIUM | Phase 1 |
| 2.3 | Implement SICI persistence bridge to DCC | SICI | DCC | MEDIUM | DCC persistence API |
| 2.4 | Persist DCC learning state to JSON files | DCC | DCC | MEDIUM | None |
| 2.5 | Register all capabilities in AIDRH registry | All | AIDRH | LOW | Phase 1 |

### Phase 3: Evidence & Learning Integration (High Risk)
| Step | Action | Source | Target | Risk | Dependencies |
|---|---|---|---|---|---|
| 3.1 | Implement IETF AAT evidence standard in AIDRH | AIDRH | AIDRH | MEDIUM | Phase 2 |
| 3.2 | Build ZBC → AIDRH evidence API | ZBC | AIDRH | HIGH | Phase 2.1 |
| 3.3 | Build AIDRH → ZBC research feedback API | AIDRH | ZBC | HIGH | Phase 3.1 |
| 3.4 | Implement hash chaining for evidence ledger | AIDRH | AIDRH | MEDIUM | Phase 3.1 |
| 3.5 | Add evidence retention policy | All | All | MEDIUM | Phase 3.1 |

### Phase 4: Full Consolidation (Highest Risk)
| Step | Action | Risk | Dependencies |
|---|---|---|---|
| 4.1 | Resolve ZBC database schema/model mismatch (7 tables) | HIGH | Phase 1 |
| 4.2 | Implement cross-repo event bus | HIGH | Phase 2 |
| 4.3 | Unified capability registry API (AIDRH) | MEDIUM | Phase 2.5 |
| 4.4 | Contract testing suite for all cross-repo APIs | MEDIUM | Phase 2 |
| 4.5 | E2E verification of all cross-repo flows | HIGH | All prior phases |

## 4. Migration Risk Register

| Risk ID | Description | Probability | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| MIG-001 | ZBC 7 missing tables may not exist in production DB | HIGH | HIGH | Verify production DB schema before consolidation | OPEN |
| MIG-002 | DCC in-memory learning state loss on restart | CERTAIN | MEDIUM | Persist to JSON files in Phase 2 | OPEN |
| MIG-003 | SICI persistence bridge has no server | CERTAIN | MEDIUM | Implement DCC endpoint in Phase 2 | OPEN |
| MIG-004 | ZBC app.py monolith refactoring risk | HIGH | HIGH | Do NOT refactor in this consolidation; wrap with API | OPEN |
| MIG-005 | Effective Rules divergence between SICI and DCC | MEDIUM | MEDIUM | Align to shared JSON spec in Phase 2 | OPEN |
| MIG-006 | No migration tracking in ZBC | HIGH | MEDIUM | Add migration tracking table | OPEN |
| MIG-007 | Cross-repo API breaking changes | MEDIUM | HIGH | Version all APIs, use contract testing | OPEN |
| MIG-008 | Evidence ledger cryptographic migration | MEDIUM | MEDIUM | Backfill hashes for existing records | OPEN |

## 5. Migration Rollback Plan

| Phase | Rollback Trigger | Rollback Action | Data Loss Risk |
|---|---|---|---|
| Phase 1 | Any failure | Revert commits | None (additive only) |
| Phase 2 | API contract break | Revert to previous contract version | Low (new endpoints only) |
| Phase 3 | Evidence corruption | Restore from git history (AIDRH) / SQLite backup (ZBC) | Medium (evidence gap) |
| Phase 4 | E2E failure | Freeze consolidation, maintain current state | Low (parallel running) |

**Verification**: PARTIAL — Migration files identified from repository. Migration execution history NOT_VERIFIED (no migration tracking table found). Consolidation plan is proposed, requires Human Gate approval before execution.