# Research reader and learning review contract

## Scope and provenance

This is new independent review-prototype work under `review_working`. It is **not recovery of missing studies 40–68**, a product implementation, a new business owner, or a product rule publication. No product source, DB, runtime, model, collector, network, permission or external service was modified or invoked. Only these three files belong to this work:

- `src/research-learning.mjs`
- `tests/research-learning.test.mjs`
- `evidence/RESEARCH_LEARNING_CONTRACT.md`

Read-only source baseline: repository `Zachary-1012/LUMENIS-codex-Clean-OS`, archive commit `4dab98ed6357133da9307de846180ed4f7bba5f5`. The supplied archive provenance records verification at `2026-10-17T12:11:01.139443+00:00`, ZIP SHA-256 `3d603c1889521c5ea5e6eedc69c17ab69d564a33bffe6a559524397f4db80f18`. This work used that current-main readback, not Git history, older studies, old task dispatch, or a fresh network claim.

## Frozen-main authorities and source (not the modified product worktree)

Paths below are relative to that read-only source baseline. Subsequent current-working-tree checks and a concrete BMP-08 correction are in CURRENT_OWNER_RECONCILIATION.md; do not apply these archive line numbers or builder observations to the modified product tree.

1. `AGENTS.md`: existing C4/Shared media and podcast, C5 Research/Evidence/versioned deliverables, C2 Learning/Evaluation, C6 Core/runtime, F presentation responsibilities; AI output never Canonical fact; no alternate truth/permission stores; source/test/runtime/acceptance claims remain distinct. The repository's product bootstrap/publish route is not executed for this isolated local prototype.
2. `00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md`, §14 P12–P13 (lines 502–503): seven reasoning levels, source drawer preserving reading position, candidate evidence, at least two validations, counterexample veto, no mixed platform denominators, unverified conclusions clearly marked, AI suggestions never automatically facts.
3. `contracts/experience/screen-specifications/BMP-08.md`: independent podcast production belongs to Shared/C4-W4, BMP is a compatibility/business-context entry. Existing read is `/api/experience/screen/BMP-08`; `BACKEND-GAP-025`, exact scope and lineage gates remain. Script/render draft actions do not execute generation.
4. `contracts/experience/screen-specifications/SH-05.md`: Shared Capability learning/version shelf, current scope-guarded read-only screen; promotion/repair/retire/rollback require existing Evaluation/approval/audit/rollback owner. Missing backend scope does not permit a fake binding or shrink the eventual capability.
5. `00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md`: C4 podcast production; C5 research/citations/versioned save-reopen; C2 controlled Learning promotion and rollback; C6 composition/authentication; F presentation. No independent owner created here.
6. `podcast/intelligence/research_levels.py`: exact `fact`, `observation`, `pattern`, `hypothesis`, `validation`, `transfer`, `dont_copy`; statuses observed/derived/ai_suggested/human_verified/unverified.
7. `podcast/intelligence/learning.py`: evidence-ID/count-only legacy helper returns `PROMOTED` after count threshold, and `REJECTED` after positive contradiction count. This is insufficient evidence of independent validations, human confirmation, source validity or real product promotion.
8. `podcast/intelligence/research_pipeline.py`: non-unverified claims require evidence IDs; eligible statuses exclude AI suggestions. `evidence_gate` is downstream consideration, not factual admission or product promotion.
9. `podcast/contracts/research-case-v1.schema.json`: case/source/status/observed timestamp schema; no verified independent-validation/promotion transaction schema. `podcast/research/research-reader-v1.json` supplies the seven levels and evidence drawer reading model.
10. `lumenis/shared/learning/content_assets.py:268–280`: actual `promote_pattern` fails closed with `CANONICAL_PROMOTION_GATE_NOT_CONNECTED`. `tests/test_content_learning_assets.py` explicitly verifies candidates cannot self-promote and persisted self-reported ADOPT is rejected. `tests/test_shared_learning_operations.py` distinguishes derived operation learning from production truth. These tests were inspected, not executed against the product.
11. Actual call path inspected: Flutter `bmp08_repository.dart` and `sh05_repository.dart` -> Core screen route; `experience_runtime.py:757–791` route dispatcher -> `experience_screens.py:_build_bmp08` and `_build_sh05`. Builders return legacy podcast entities/global learning history. They do not establish the typed, scoped, evidence-versioned reader/promotion contract. `sh05_snapshot.dart` requires scope/read authorization and versioned asset semantics. Existing source is not a live runtime readback.

### Source fingerprints

| Source | SHA-256 |
|---|---|
| podcast/intelligence/learning.py | 89bda65d9f5fabb2505c315d3a937990d4c9b87f527f3cdaf72a8a4d68c93c04 |
| podcast/intelligence/research_levels.py | fdd96cad2b15712e2751af487718ab3e331b6d1c0b55b0aafd8f7bb43db8c290 |
| podcast/intelligence/research_pipeline.py | 5eafc630d9eb3e4d84bd7650f5bb8a95870e24f9c0b6d2aebb08e24155d38118 |
| podcast/contracts/research-case-v1.schema.json | eb60f51d633084b28c048940cbdb299d30ad1b799cfef48332dd925a398915a4 |

## Conflict resolution and UNBOUND boundary

The old count helper's `PROMOTED` return and the 0.70 confidence predicate in `ResearchFinding.promotable` are not copied as product authority. No confidence threshold can bypass missing evidence or independent evaluation. The current Shared fail-closed gate and current P13/SH-05 constraints require honest separation.

The local state can reach only `candidate`, `ready_for_human_review`, `review_confirmed` or `rejected`. Every evaluation returns `localOnly: true`, `binding: UNBOUND`, `productPromotion: UNBOUND`, and `canonicalFact: false`. A fact-level label describes supplied research classification; this module never certifies Canonical truth. Editing cannot upgrade evidence status. A supplied AI-suggested/derived/unverified finding cannot be created as fact.

These require real existing owners and are deliberately not invented:

- authenticated actor/workspace/domain/SourceUse/Permission and evidence admission;
- objective proof of independence, sample lineage, trusted source groups and verifier identity;
- source freshness policy, expiration/withdrawal authority and real immutable versions;
- actual Evaluation approval, promoted lifecycle mapping, rollback transaction and audit;
- server persistence, request-id/effect fencing, source digest/integrity verification;
- metric definitions, time/population/denominator comparability and any legitimate cross-platform normalization.

The local fixtures' sourceGroup, independenceKey and independenceBasis are **human-authored illustrative assertions, not authenticated independent evidence**. Two arbitrary IDs never suffice even locally. UI must label them “人工示例独立验证记录” or equivalent and never report genuine product validation/promotion success. Serialization is plain JSON, not cryptographically signed evidence or a server save receipt.

## API and shapes

- `createResearchState({id, statement, level='hypothesis', status='unverified', evidenceRefs=[]})`
- `evaluateLearning(state, {now, evidence})`
- `reduceResearch(state, action, {now, evidence})`
- `saveResearch(state)` returns local JSON bytes as a string; caller owns any local storage/download.
- `reopenResearch(json, {now,evidence})` returns `{state,evaluation}`; structural validation, fresh context evaluation, and clears saved confirmation.
- `compareMetricScopes(a,b)` returns comparability reasons only, never aggregates or substitutes a denominator.

`state = {schema:'research-learning-review-v1', revision, draft:{finding:{id,statement,level,status,evidenceRefs},candidateVersion,validations}, history, reader:{anchor,drawerEvidenceId}, confirmation}`.

Evidence reference: `{id,version}`. Current externally supplied review context entry: `{id,version,state:'active'|'withdrawn'|'unknown',locator,sourceGroup,validUntil}`. `now` and non-null `validUntil` are explicit timezone-bearing date-time strings. A missing locator/source group/expiry remains incomplete; expiry at `now` is expired. This expiry requirement is conservative local review behavior, not a newly invented product TTL.

Validation: `{id,outcome:'pass'|'counterexample'|'inconclusive',independenceKey,independenceBasis,candidateVersion,evidenceRefs}`. Missing independence metadata never counts. Passing records must have current candidate version, matching active evidence versions, non-expired sources, distinct independence keys and non-overlapping source groups. Counting is deliberately conservative; this is not a statistical independence estimator.

Every action requires exact `expectedRevision`:

- `edit-finding`: full `finding`, same ID/status; increments candidate version, invalidates confirmation and old validation eligibility.
- `add-validation`: full `validation`; rejects duplicate ID and stale candidate version; preserves append-only records.
- `confirm-review`: `humanConfirmed:true, reviewer`; reevaluates current context and records only local human review.
- `revoke-review`: clears local confirmation.
- `undo`: restores previous finding, increments candidate version, clears confirmation; never erases validation/counterexample records.
- `set-anchor`: `anchor`; `open-evidence`: referenced `evidenceId`; `close-evidence`. Drawer operations preserve reader anchor and do not change research content.

Counterexamples veto even when stale, withdrawn or expired, including after edits/undo. Resolution is left to the product owner, so this prototype provides no “ignore counterexample” route. Reopen preserves content/reader/history but requires a fresh human review. Any changed evidence context invalidates the local confirmation basis. Revision is monotonic for reducer operations; JSON loading is not trusted as a product version authority.

Metric comparison requires all eight exact fields: platform, metric, definitionVersion, unit, denominator, population, windowStart, windowEnd. Missing/null/common UNKNOWN sentinels stay unknown, never zero. Different platforms cannot compare, even if metric names and numbers match. Compatible labels do not prove representative sampling, causal effect or a valid aggregate.

## Validation and limits

Run: `node --test review_working/tests/research-learning.test.mjs`.

Result: 12 isolated pure-logic test groups passed, no skips/failures (2026-10-17). Covered seven levels, no AI-to-fact mutation, 0/1/2 validation gates, duplicate/correlated source rejection, missing evidence, counterexample veto, withdrawn/expired/version-changed evidence, stale revisions, immutability, undo with append-only evidence, drawer reading position, save/reopen distrust, malformed saves, cross-platform and denominator mismatch, and strict explicit context.

No real product test runner, DB, API, model, network or runtime was called. No product/server save, promotion, source admission, independence verification, UI integration, four-surface E2E or lost-study recovery is proven. UI integration and browser acceptance belong to the parent review task and are not counted by these module tests.
