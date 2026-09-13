# LUMENIS — Current Codex Blockers (2026-09-13)

> Point-in-time handoff only. Re-verify current `origin/main`, local working tree and runtime before acting.
> Current source/runtime/tests outrank this file. Do not turn this handoff into a mandatory full-read step for unrelated tasks.

## Already converged — do not rediscover

The active repository-convergence work has already established:

- clean-checkout hermetic CI separated from Production/Live/Environment suites;
- `excluded from clean CI != PASS`;
- compile and hermetic pytest are real blocking gates;
- production/live/browser/protected-data suites remain Production Acceptance requirements;
- tracked credential-path diagnostic now passes (`leak_count = 0`); the prior `naming-profile.json` / historical `secret_scan_result.txt` hits were verified classification false positives and fixed narrowly;
- `codex/production-convergence` valid DB isolation / Permission / Experience runtime implementation and tests have been selectively absorbed;
- remaining old implementation/handoff/research branch ancestry has been folded into the single convergence history without restoring stale trees;
- README is bilingual Chinese/English and `main` is defined as the only long-lived development line;
- AGENTS is a compact model-neutral execution router;
- third-party/open-source inventory/replacement boundaries are canonicalized.

Branch-convergence authority:

- `00-GOVERNANCE/SINGLE-MAINLINE-BRANCH-CONSOLIDATION-V1.md`

CI-tier authority:

- `tests/CI_TEST_TIERS.md`
- `tests/ci_environment_tests.txt`
- `tests/ci_quarantined_nodeids.txt`
- `tests/select_ci_tests.py`

## Latest completed high-signal hermetic run

Run #100 selected **248 hermetic test files** and executed to 100%.

Infrastructure truth:

```text
Development/test dependencies = PASS
Python compile = PASS
CI tier manifest validation = PASS
Tracked credential-path diagnostic = PASS (6212 tracked / 0 leaks)
Hermetic pytest = FAIL (deterministic product/contract failures remain)
Thread leak = NONE
Boundary advisory = 19 (INFO 11 / MEDIUM 8 / HIGH 0)
Asset inventory = 984 Python files / 617 routes / 68 DB tables / 275 test files
```

Do not hide the remaining deterministic failures by moving them into Environment/Live tiers.

## P0 — Canonical DB identity / module identity cluster

### 1. Import-time DB path ownership remains outside the new call-time resolver

Current evidence:

- canonical resolver now exists in `db_paths.py`;
- `database.py` and several production writers were converged to call-time resolution;
- `account/models.py` still captures `DB_PATH` at module import time;
- `skill_execution_chain.query_executions()` uses `account.models.get_db()`;
- module reload / temporary `ZBC_DB_PATH` changes can therefore read/write a different DB identity than the active test/runtime contract.

Observed deterministic symptoms include:

- `tests/test_experience_runtime.py::test_ai01_traceability_not_fabricated` → traceability is calculated from samples that should not exist in the isolated test DB;
- `tests/test_ai_task_engine.py::TestDBMigration::test_tables_exist` → expected `ai_task` table absent;
- `tests/test_ai_task_engine.py::TestDBMigration::test_evidence_hash_columns_exist` → evidence hash columns absent;
- `tests/test_subject_dual_dimension.py` → expected isolated schema/count differs from observed DB state;
- `tests/test_topic_snapshot.py` → expected snapshot rows written to isolated DB are absent;
- `tests/test_negative_event_api.py::test_event_mentions_linked_notes` may belong to the same fixture/DB-identity cluster and must be rechecked after canonical DB identity is fixed.

Required direction:

```text
all active persistence consumers
→ one canonical call-time DB-path contract
→ isolated test DB remains isolated across reload/import order
→ production DB unchanged
```

Do **not** create another DB resolver. Extend/use current `db_paths.py` ownership.

### 2. Python reload/type identity drift

`tests/test_permission_gate.py::TestOperationRegistry::test_operation_spec_fields` currently fails because an enum value created by a reloaded `permission_gate` module is not `isinstance`-identical to the test's previously imported `PermissionLevel` class.

Fix the public/serialized contract or module ownership so reload order cannot invalidate type checks. Do not suppress the test merely to get green CI.

## P1 — Semantic memory / asset admission

Current hermetic failures:

- `tests/agent_memory/test_memory_integration.py::TestMemoryFullChain::test_semantic_context_injection`
- `tests/agent_memory/test_memory_integration.py::TestLearningLoopFullChain::test_six_layer_memory_interop`
- `tests/agent_memory/test_semantic_memory.py` search/get/context/stats cases

These surfaced after semantic-asset admission work was recovered from the production-convergence branch. Determine whether fixture seeding, asset visibility/admission state, or current semantic-memory ownership is wrong. Do not restore an obsolete parallel memory truth.

## P1 — `ad_intelligence.models` ownership gap

Six tests in `tests/test_ad_intelligence.py` import:

```text
ad_intelligence.models.ctr_predictor.CTRPredictor
ad_intelligence.models.feature_engineer.AdFeatureEngineer
```

Current package has no `ad_intelligence.models` implementation, and repository search found no equivalent `CTRPredictor` / `AdFeatureEngineer` implementation.

Decision must come from current product ownership:

- if this is a still-required capability, implement it under the existing ad-intelligence contract with real tests;
- if the model layer was intentionally removed/superseded, update the stale tests/contract with evidence.

Do not create a parallel model stack solely because a test import name exists.

## P1 — AI/provider contract cluster

### Model / thinking metadata

`tests/test_ai_channel_flag.py` currently reports:

- requested model override not preserved (`glm-5.2` expected, metadata model is `None`);
- `has_thinking` missing for several GLM variants.

Resolve against current AI Gateway/provider metadata contract.

### Auth failure fallback semantics

`tests/test_ai_channel_multiprovider.py::TestRouteWithFallback::test_auth_error_no_fallback` expects a provider 401/auth failure to stop fallback, while current routing attempts the next provider.

Current AI provider policy supports multi-provider fallback generally, but auth/fatal-error semantics must be made explicit at the routing owner. Do not change behavior only to satisfy one assertion without reconciling the canonical policy.

## P1 — IC API auth/permission contract

`tests/test_ic_contracts_p1.py` has three smoke routes returning `401` where the test expects `200`:

- EMV API
- localization API
- KOS interest API

Resolve against current authentication/permission truth. Do not disable auth globally to obtain green tests.

## P1 — Secondary-platform state semantics

`tests/test_secondary_platforms_main.py` currently reports:

- Bilibili detail not implemented: actual `SESSION_EXPIRED`, expected `COLLECT_ERROR`;
- Weibo comments not implemented: actual `SESSION_EXPIRED`, expected `COLLECT_ERROR`.

Resolve the canonical collection-state semantics at the adapter owner. Missing implementation and expired authentication are distinct states and must not be conflated.

## Advisory architecture debt

Latest boundary advisory reports:

```text
B1 ZBC direct OSAI import                0
B2 OSAI direct ZBC DB                    1
B3 OSAI direct production-table writes   0
B4 app startup depends on OSAI            0
B5 cross-repo interaction contract       10
B6 Skill/Agent Permission Gate            8
B7 PENDING/CONCEPT production refs        0
B8 credential security                    0
TOTAL                                     19
HIGH                                      0
```

This remains advisory while deterministic product gates are repaired, but it must be reconciled before Production Acceptance where applicable.

## Recommended next execution order

```text
P0 canonical DB identity / import-time path consumers
→ rerun DBISO + Experience + subject/topic/AI-task focused tests
→ P0 reload/type identity contract
→ semantic-memory/admission cluster
→ AI/provider contract cluster
→ ad_intelligence ownership decision
→ IC auth/permission contract
→ secondary-platform state semantics
→ hermetic CI full rerun
→ Production/Live environment acceptance
→ canonical DB/config final full regression on local runtime
→ production startup / health / core runtime
→ domain + closed-loop Critical E2E
→ G0→G16 continuation
```

## Rules for the next executor

- Work from current `main`; do not use an old side branch as a development authority.
- Do not redo branch archaeology; the single-mainline convergence document records the completed history convergence.
- Do not reclassify deterministic failures as Environment/Live tests merely to make CI green.
- Do not rerun full repository discovery before working.
- Read only the owner/source/tests needed for the active blocker.
- Prefer `reuse → adapt → bind → verify`.
- Extend current canonical DB/Permission/Evidence/Runtime owners; do not create second truths.
- After deterministic CI is green, return to the real local Production/Live gates rather than continuing CI cleanup indefinitely.
- Clean GitHub CI alone never proves `PRODUCTION_READY = YES`.
