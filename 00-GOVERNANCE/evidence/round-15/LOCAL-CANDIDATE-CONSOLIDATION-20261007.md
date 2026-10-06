# LUMENIS local candidate consolidation — 2026-10-07

> Status: **LOCAL_ONLY / NOT_PUSHED**. This is the single local candidate, held for Product Owner approval before publication.
> Base: local = origin/main = live `main` `3be8298a3ae853b98fde90b2fda943a5c9462a58` (2026-10-07 04:07 +08).

## 1. Candidate contents

Five candidate regression suites were compared against current main, passed in full, and are the only unique valid work admitted:

| Test file | Origin | Local result |
|---|---|---|
| `tests/test_owned_ada_recipe.py` | `work/w2-owned-ai-20261002/matpool-ada-20261003/recovery-v2/source-v2/tests/` | pass |
| `tests/test_owned_ada_checkpoint_recovery.py` | same candidate pair; requires the recipe companion | pass |
| `tests/test_owned_training_checkpoint_producer.py` | `work/w2-owned-ai-20261002/matpool-ada-20261003/producer-v1/postimages/tests/` | pass |
| `tests/test_training_checkpoint_artifacts.py` | same producer tree | pass |
| `tests/test_xhs_cdp_native_truth.py` | `work/c1-w1-20261002/xhs-search-diagnostics-v1-final-postimages/tests/` | pass |

Together they run 138 tests with no thread leaks on the isolated test seed. The same five files also cover C1 XHS native-truth/checkpoint behavior and C2 ADA recipe/checkpoint producer/artifact behavior that current main tests do not duplicate by name or contract.

The candidate commit also carries: `.gitignore` protective entries, this record, and CURRENT item 79.

## 2. Local uncommitted item dispositions

| Item | Disposition |
|---|---|
| `lumenis/system/collector/data/schedule_state.json` | Runtime-written collector state. The single-writer path move already exists in main (`data/runtime/collector/schedule_state.json`); this tracked copy stops changing after the next authorized Core restart. Excluded from the candidate. |
| `config/ai-owned-training-runtime.json` | Private C2 runtime configuration. Never committed; now explicitly ignored. |
| `00-GOVERNANCE/evidence/round-06/C1-W1-DATA-COLLECTION-2026-10-02.md` | C1 local research receipt. Per the protected-boundary record it is not production Source/Evidence/Canonical admission; preserved locally and now ignored. |
| `work/` | Protected historical/provenance archive (25 roots). A bounded source scan found 6,530 candidate files identical to main, 3,098 differing and 1,127 main-absent; the differences are older snapshots of an evolving main or already-published batches. D43–D46 dispositions apply (D44: published, do not replay old postimages; D45: exact main match; D46: F evidence). No parallel active candidate remains; the tree is preserved on disk and now ignored. |
| F-owned Experience/screen edits in the shared worktree | Owned by F and preserved untouched; not part of M's candidate. |

## 3. Candidate-like material not admitted

| Item | Reason |
|---|---|
| `test_xhs_search_diagnostics.py` | Imports `_safe_acquisition_metadata`, absent from current main's XHS adapter; candidate-era C1 contract. |
| `test_source_credibility.py` | References `operational_brief._REVIEWED_PUBLIC_REFERENCES`, absent from current main; candidate-era C3+C5 contract. |
| `test_final_source_boundary.py` | Hardcodes the retired Cloud root `/workspace/LUMENIS-codex-Clean-OS`; Cloud-era test. |
| `test_approved_raw_public_import.py` | Still fails under a migrated seed with `EVIDENCE_WRITE_FAILED` against current main; candidate-era C1 intake contract. |
| `scripts/audit_tools/{local_feature_diff,scan_all,scan_local_repos}.py` | Retired from main by an approved convergence; not re-admitted. |
| F-owned `account/acc01..04` Dart screens in candidate snapshots | F-owned Experience work; outside M's candidate. |

## 4. Single candidate

The commit carrying this record, the five admitted test files, the `.gitignore` protections and CURRENT item 79 is the one and only local candidate. No parallel candidate tree is active. Publication requires explicit Product Owner approval; this record does not claim runtime, owned-model, user-E2E or release acceptance.
