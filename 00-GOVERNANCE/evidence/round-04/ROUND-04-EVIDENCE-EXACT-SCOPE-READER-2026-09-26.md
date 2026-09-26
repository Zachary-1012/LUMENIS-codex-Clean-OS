# ROUND 04 — exact-scope Evidence storage reader (2026-09-26)

## Batch truth

- Base: `d2cdd01382a8a0294f2fdad918fc3c87c5ff570f`; final local/online SHA is verified after publication. Only the existing Shared Evidence owner, its focused test, this evidence and CURRENT online status are in this Batch.
- `record_evidence` already persists CTH Subject, BMP BrandFocus or domain-global scope in canonical `app_evidence_records`. The legacy `query_evidence` remains broad and existing API routes have not yet been made actor/scope-safe. This Batch adds a separate, internal `query_scoped_evidence` storage read, with the same scope normalization as the writer. It is **not an authorization gate** and must not be exposed to product clients until the canonical Permission/Context contract is enforced at the API boundary.
- The reader requires exactly one Subject, BrandFocus or domain-global scope, rejects malformed/pending parameters, selects matching persisted `domain_id` and `product_id`, then compares the complete reserved `_lumenis_scope` metadata. Legacy unassigned, other focus, other domain and malformed JSON rows are excluded. Offset/limit are applied after this exact comparison; order is stable by creation time and ID. No database migration, table or new Evidence owner is introduced.

## Verification

- Clean current-HEAD archive under `%TEMP%`, explicit `Set-Location` and `PYTHONPATH` to prevent the shared dirty worktree being imported; process-scoped disposable `ZBC_DB_PATH` and `LUMENIS_TEST_SEED_DB`; cloud AI disabled.
- Initial two test invocations exited 1 before collection because named files were not part of this committed snapshot. These were command selection errors, **not PASS**. The corrected exact file set was `tests/test_evidence_scoped_write.py tests/test_evidence_store_schema.py tests/test_evidence_store.py tests/test_evidence_schema_owner.py tests/test_evidence_replay_api.py`: **69 passed, exit 0**, no daemon thread leak.
- New cases check CTH subject 1/2, CTH global, BMP BrandFocus/global and legacy separation; malformed stored JSON is skipped before pagination; invalid/missing scopes fail closed.
- Run constitution/static owner and staged diff checks against the exact candidate, then verify the committed HEAD/remote; production `data/monitor.db` must retain its pre-batch SHA-256 `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`, 1,458,176 bytes, with no sidecars.

## REAL DELIVERY CARD / 真实用户工作闭环验收

- REAL USER JOB: an authorized CTH/BMP worker opens only Evidence for the selected Subject/BrandFocus or legitimate global domain scope.
- ENTRY/REAL INPUT: isolated SQLite records written through the canonical Evidence writer, plus one legacy/unassigned and one malformed record. They are test input, not live user records.
- END-TO-END PATH: scoped write → persisted row → exact storage read = tested. Actor identity → Permission decision → scoped API/ViewModel → user-visible result → Return/recovery = **not wired/tested**.
- USER-VISIBLE RESULT: none from this Batch. Existing broad `/api/evidence/list`, `/api/evidence/<id>`, `/api/evidence/stats` and timeline routes require a separate Permission/API hardening Batch. Do not promote this storage reader as proof those routes are secure.
- FAILURE/RECOVERY: invalid read scope raises ValueError; malformed row is excluded. No external effect.
- ACCEPTANCE: bounded storage reader `TESTED`; ROUND 04 remains `REWORK`, real-user E2E `LIVE_NOT_VERIFIED`.

## GLOBAL UNIVERSE / DATA MATURITY, research and commercial impact

This Batch changes no source acquisition or population. Random real-entity sample count 0; Global Commercial Coverage `NO`, Global Brand Coverage `NO`, Guangzhou Taikoo Hui Reference Coverage `PARTIAL` from separate prior reference evidence; internal full-universe readiness `NO`. Global here means one **domain-specific persisted global scope**, not all entities or all data maturity.

The current Round 04 gap is exact scope read isolation. This Batch reuses the existing writer normalization, DB repository and storage owner; no external package or independent architecture is justified (`RESEARCH COMPLETE / NO JUSTIFIED UPGRADE`). The controlled evolution path still requires Permission, live actor/context binding, API return semantics, operational evidence and rollback. Commercial identity/onboarding, data rights, retention and human acceptance remain unverified.

## Online closure

Co-publish this evidence and CURRENT status with exact source/test blobs. After push, fetch and compare local HEAD, `origin/main`, live `refs/heads/main`, and both published paths. Hosted CI is a separate gate; a nonexecuted job gives `EXECUTION-LAYER UNVERIFIED`, not test PASS.
