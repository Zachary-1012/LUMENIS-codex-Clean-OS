# 11 — Contract Matrix (契约矩阵)

> Verification: PARTIAL — Contracts identified from source code; formal contract definitions NOT_VERIFIED for most channels

## 1. API Contracts

| Contract ID | Provider | Consumer | Endpoint | Method | Input | Output | Version | Status |
|---|---|---|---|---|---|---|---|---|
| API-ZBC-001 | ZBC | SICI | /api/evidence/* | GET | evidence query | JSON evidence | unversioned | NOT_VERIFIED (no OpenAPI) |
| API-ZBC-002 | ZBC | ZBC UI | /api/notes/* | GET/POST | note data | JSON | unversioned | ACTIVE (code) |
| API-ZBC-003 | ZBC | ZBC UI | /api/events/* | GET | event query | JSON | unversioned | ACTIVE (code) |
| API-ZBC-004 | ZBC | ZBC UI | /api/collect/* | POST | collect config | status | unversioned | ACTIVE (code) |
| API-ZBC-005 | ZBC | ZBC UI | /api/report/* | GET | date range | report JSON | unversioned | ACTIVE (code) |
| API-ZBC-006 | ZBC | ZBC UI | /api/health/* | GET | — | health metrics | unversioned | ACTIVE (code) |
| API-DCC-001 | DCC | DCC UI | /api/ai/task | POST | task description | AI result | v0.5.0 | ACTIVE (code) |
| API-DCC-002 | DCC | DCC UI | /api/audit/repository | GET | owner, repo | repo data | v0.5.0 | ACTIVE (code) |
| API-DCC-003 | DCC | DCC UI | /api/audit/commits | GET | owner, repo, branch | commits | v0.5.0 | ACTIVE (code) |
| API-DCC-004 | DCC | DCC UI | /api/snapshot | GET/POST | snapshot data | snapshot | v0.5.0 | ACTIVE (code) |
| API-DCC-005 | DCC | DCC UI | /api/change-plan | GET/POST | plan data | plan | v0.5.0 | ACTIVE (code) |
| API-DCC-006 | DCC | DCC UI | /api/evidence-bundle | GET/POST | evidence | bundle | v0.5.0 | ACTIVE (code) |
| API-DCC-007 | DCC | DCC UI | /api/learning/cases | GET/POST | case data | cases | v0.5.0 | ACTIVE (code) |
| API-DCC-008 | DCC | DCC UI | /api/shadow-learning/* | GET/POST | candidate | lifecycle state | v0.5.0 | ACTIVE (code) |
| API-DCC-009 | DCC | DCC UI | /api/effective-rules | GET | context | resolved rules | v0.5.0 | ACTIVE (code) |
| API-DCC-010 | DCC | DCC UI | /api/capabilities | GET | — | capability list | v0.5.0 | ACTIVE (code) |
| API-DCC-011 | DCC | DCC UI | /health | GET | — | health status | v0.5.0 | ACTIVE (code) |

## 2. File Contracts

| Contract ID | Provider | Consumer | File | Format | Schema | Version | Status |
|---|---|---|---|---|---|---|---|
| FILE-AIDRH-001 | AIDRH | All | GLOBAL-CROSS-REPOSITORY-BASELINE.md | Markdown | unstructured | immutable | ACTIVE |
| FILE-AIDRH-002 | AIDRH | All | CAPABILITY-REGISTRY.md | Markdown | semi-structured | v1 | ACTIVE |
| FILE-AIDRH-003 | AIDRH | All | data/research/records.jsonl | JSONL | R-YYYY-NNNN | v1 | ACTIVE |
| FILE-AIDRH-004 | AIDRH | All | AI-COLLABORATION-PROTOCOL.md | Markdown | unstructured | v1 | ACTIVE |
| FILE-AIDRH-005 | AIDRH | All | SHADOW-LEARNING-PROTOCOL.md | Markdown | unstructured | v1 | ACTIVE |
| FILE-DCC-001 | DCC | DCC | data/baseline.json | JSON | ZB-PROD-YYYY-MM-DD-NN | v1 | ACTIVE |
| FILE-DCC-002 | DCC | DCC | data/rules/product-rules.json | JSON | rule array | v1 | ACTIVE |
| FILE-DCC-003 | DCC | DCC | data/rules/capability-constraints.json | JSON | capability + permission gate | v1 | ACTIVE |
| FILE-DCC-004 | DCC | DCC | protocols/registry.json | JSON | protocol registry | v1 | ACTIVE |
| FILE-SICI-001 | SICI | SICI | manifest.json | JSON | PWA manifest | v1 | ACTIVE |
| FILE-ZBC-001 | ZBC | ZBC | system_config.json | JSON | key-value | unversioned | ACTIVE |
| FILE-ZBC-002 | ZBC | ZBC | function_map.json | JSON | function mapping | unversioned | ACTIVE |
| FILE-ZBC-003 | ZBC | ZBC | brand_directory.json | JSON | brand entities | unversioned | ACTIVE |
| FILE-SHARED-001 | (shared) | SICI, DCC | ZBIP_DESIGN_TOKENS.css | CSS | CSS variables | unversioned | ACTIVE (identical SHA) |

## 3. Database Contracts

| Contract ID | Provider | Consumer | Table/Collection | Access Mode | Schema | Status |
|---|---|---|---|---|---|---|
| DB-ZBC-001 | ZBC | ZBC | notes (22 tables total) | R/W | models.py | ACTIVE |
| DB-ZBC-002 | ZBC | SICI | (via API, not direct) | Read-only | zbc-evidence-adapter.js | ACTIVE (no direct DB access) |
| — | — | — | **No cross-repo direct DB access** | — | — | PASS (correct isolation) |

## 4. Event Contracts

| Contract ID | Provider | Consumer | Event Name | Payload | Mechanism | Status |
|---|---|---|---|---|---|---|
| — | — | — | **No cross-repo events identified** | — | — | GAP |
| EVT-DCC-001 | DCC | DCC | shadow-learning.state_change | {candidate_id, old_state, new_state} | in-memory | ACTIVE (internal only) |
| EVT-ZBC-001 | ZBC | ZBC | collection.complete | {keyword, count, status} | in-process | ACTIVE (internal only) |

## 5. Capability Contracts

| Contract ID | Capability | Provider | Consumer | Interface | Version | Status |
|---|---|---|---|---|---|---|
| CAP-AIDRH-001 | research-id-generator | AIDRH | All | tools/research_id.py | CAP-2026-0001 | ACTIVE |
| CAP-AIDRH-002 | shadow-lifecycle | AIDRH | DCC | SHADOW-LEARNING-PROTOCOL.md | CAP-2026-0002 | ACTIVE |
| CAP-AIDRH-003 | ddc-research-adapter | AIDRH | DCC | src/adapters/ddc_research_adapter.py | CAP-2026-0003 | ACTIVE |
| CAP-SICI-001 | EffectiveRules | SICI | SICI | js/effective-rules.js | unversioned | ACTIVE |
| CAP-SICI-002 | Preflight | SICI | SICI | js/preflight.js | unversioned | ACTIVE |
| CAP-SICI-003 | MobileUI | SICI | SICI | PWA | unversioned | ACTIVE |
| CAP-SICI-004 | TestRunner | SICI | SICI | js/tester.js | unversioned | ACTIVE |
| CAP-SICI-005 | CI-Verify | DCC | SICI | reusable-verify.yml | @448ba21 | ACTIVE |
| CAP-DCC-001 | EffectiveRules (server) | DCC | DCC | server/effective-rules.js | v0.5.0 | ACTIVE |
| CAP-DCC-002 | ShadowLearning | DCC | DCC | server/shadow-learning.js | v0.5.0 | ACTIVE |
| CAP-DCC-003 | EvidenceBundle | DCC | DCC | server/evidence-bundle.js | v0.5.0 | ACTIVE |
| CAP-DCC-004 | Snapshot | DCC | DCC | server/snapshot.js | v0.5.0 | ACTIVE |
| CAP-DCC-005 | RepositoryAudit | DCC | DCC | /api/audit/* | v0.5.0 | ACTIVE |

## 6. Cross-Repo Contract Gap Analysis

| Gap | Description | Impact | Severity |
|---|---|---|---|
| No OpenAPI/Swagger for ZBC API | ZBC has 50+ routes but no API schema | SICI adapter contract is implicit | HIGH |
| No formal contract for ZBC evidence API | zbc-evidence-adapter.js assumes API structure | Breaking changes in ZBC will break SICI | HIGH |
| No versioning on most contracts | Most contracts are unversioned | No backward compatibility guarantee | MEDIUM |
| No contract for SICI persistence bridge | zachary-ai-persistence.js has no server endpoint | Contract is one-sided | MEDIUM |
| No cross-repo event contract | No event bus defined | Async communication impossible | MEDIUM |
| Design token contract unversioned | ZBIP_DESIGN_TOKENS.css has no version | Divergence already occurred (ZBC) | LOW |
| No contract test suite | No automated contract verification | Contracts can break silently | HIGH |

## 7. Contract Compliance Checklist

| Contract | Provider Implements | Consumer Implements | Version Match | Test Coverage | Status |
|---|---|---|---|---|---|
| ZBC Evidence API | NOT_VERIFIED | zbc-evidence-adapter.js | unversioned | NOT_VERIFIED | NOT_VERIFIED |
| DCC AI Bridge | server.js | js/bridge.js | v0.5.0 | NOT_VERIFIED | PARTIAL |
| DCC Audit API | server.js | js/github-audit.js | v0.5.0 | NOT_VERIFIED | PARTIAL |
| AIDRH Research Records | records.jsonl | (manual consumption) | v1 | NOT_VERIFIED | PARTIAL |
| AIDRH Baseline | GLOBAL-CROSS-REPOSITORY-BASELINE.md | All repos (reference) | immutable | NOT_VERIFIED | PARTIAL |
| Effective Rules (SICI↔DCC) | 2 implementations | 2 implementations | unversioned | NOT_VERIFIED | CONFLICT (separate impls) |
| Design Tokens | (shared file) | SICI, DCC, ZBC | unversioned | NOT_VERIFIED | CONFLICT (ZBC divergent) |

**Verification**: PARTIAL — Contracts identified from source code and file analysis. Formal contract definitions (OpenAPI, JSON Schema) are absent for most channels. Runtime contract compliance NOT_VERIFIED.