# ROUND 06 — XHS exact scope repair

Base: `1c8454ff47982d87fb4ef167db0ec5c7bcc11b69`. Existing SYSTEM Collector,
Raw, signed Evidence and Canonical owners only. No new migration or store.

## Changed behavior

`/api/rednote/collect` now resolves one registry query before browser work and
passes it into persistence. Primary `xhs_cookie_bridge.sync` also binds saved
observations. Keyword/legacy location flags cannot supply an exact source
identity. Raw observations remain available when scope cannot be verified;
failed scope persistence is surfaced. Unknown interaction metrics remain NULL.
Reusing a signed scope record requires unchanged source text. A verified name
mention is association evidence, never proof of tenancy or venue location.

## Real data disposition

All six preexisting UNASSIGNED rows were inspected from stored source text:

| Raw IDs | Decision | Exact reason |
|---|---|---|
| 268, 269 | VERIFIED CTH Subject `SUBJ-89269ecd7273fb3c4b6d3fbe` | Source explicitly mentions 广州太古汇; signed scope Evidence 422 |
| 270 | Remains UNASSIGNED / review required | A bar behind 太古汇 is not demonstrated to be inside the reference venue; no full registered source name. Review provenance in Evidence 422 |
| 227–229 | Remain UNASSIGNED / review required | Source explicitly concerns 深圳湾万象城, not the selected 罗湖深圳万象城. Review provenance in Evidence 423 |

No tenant/location assertions were created. No source body, capture/publication
time, or source count changed. `notes=270`, `canonical_data=270`, remaining
UNASSIGNED=4. Both scope Evidence rows have writer-authenticated signatures.
The second application reused Evidence 422/423 and the same Raw/Canonical IDs.
Integrity check = ok; foreign key violations = 0.

Canonical WAL-consistent backup before application:
`data/backups/pre-xhs-scope-apply-20261001.db` (private, not tracked).
First applied to a disposable clone; then bounded product application and
repeat/reopen verification returned exit 0. Signed Permission DATA_IMPORT
approval records cite the Product Owner's explicit six-row repair instruction.

## Current automated evidence

Normal `tests/conftest.py` remained enabled; an explicitly migrated, empty v18
OS-temp seed was used. 61 tests passed, no skips/failures, in:

- `test_xhs_exact_scope_binding.py`
- `test_xhs_lineage_persistence.py`
- `test_rednote_persistence_unknown_comments.py`
- `test_prelaunch_source_entity_mentions.py`
- `test_prelaunch_douyin_manual_import.py`
- `test_prelaunch_x_manual_import.py`
- `test_xhs_approved_local_worker_route.py`

The last suite replaces the earlier `--noconftest` run as current isolated
regression proof. It does not retrospectively turn that earlier run into a gate.

## Real delivery card / 真实用户工作闭环验收

Job: collect and reopen source data under the correct commercial Subject.
Real input: the six previously collected public observations above.
Path: canonical backup -> disposable proof -> signed scope review -> existing
Raw/Canonical binding -> repeat/reopen/integrity verification.
Visible result: exact sources may be consumed by the scoped Source Brief;
incorrect venue/ambiguous observations remain excluded from focused results.
Failure/recovery: missing signed Evidence never promotes scope; raw data is
retained; unchanged repeat is idempotent; changed sources require new review.
Acceptance: **bounded persisted-data repair verified**. New platform login/
collection and human repeated UI acceptance are **not verified by this batch**.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: no coverage promotion. Global Commercial
Coverage=NO; Global Brand Coverage=NO; Guangzhou Taikoo Hui Reference=PARTIAL.
COMMERCIAL OVERLAY IMPACT: RELEASED=NO, OPERATING=NO, COMMERCIAL_READY=NO.
CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: internal source-identity
defect fixed through existing owners; no new dependency was justified.
