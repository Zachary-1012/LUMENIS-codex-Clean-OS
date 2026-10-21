# Remaining local state contracts

Verified 2026-10-17 UTC. Scope: the independent review package's risk review,
version tree and audio-chapter state modules. This is pure Node state-contract
verification, not browser, real product/backend, or audio-listening acceptance.
Product source was read only. No product code, database, runtime, services,
deployment, frozen recovery copy or existing v5 tests were changed.

## Result

- Added `tests/remaining-state-contracts.test.mjs`: 21 task-shaped tests.
- Before repair: 19 passed, 2 failed. Original failure output is preserved in
  `remaining-state-contracts-before.log`.
- After repair: 21 passed, 0 failed. Output:
  `remaining-state-contracts-after.log`.
- Only `src/version-tree.mjs` needed changes. `risk-review.mjs` and
  `media-chapters.mjs` remained unchanged. No defect was reproduced in their
  tested paths; this is not a blanket defect-free guarantee.
- The non-offline full suite passed 175/175, including concurrently completed
  work elsewhere in this independent package. Output:
  `remaining-state-contracts-full-excluding-offline.log`.
- The integration owner rebuilt the offline artifacts and recorded 178/178 in
  `current-regression.log`. This audit did not write offline artifacts.

## Two reproduced defects and bounded repairs

### 1. A saved branch kept the wrong draft base

Reproduction: save `local-v1`, edit and explicitly save a branch `local-v2`,
then edit that branch and choose ordinary save. The original reducer marked
the branch draft clean but retained `base=local-v1`. The next save therefore
silently wrote `local-v3` under `local-v1` and replaced the main head, losing the
actual saved parent relationship.

Repair: branch creation now sets `base` to the new branch's ID while leaving
`head` unchanged. A following ordinary save correctly fails the existing
base/head conflict gate and retains the draft. Explicitly saving another branch
creates a child of the saved branch. Explicit old-content adoption can still
create a new draft on the current head; no old version is rewritten.

### 2. Validated restored IDs could collide on the next append

Reproduction: `validateVersionTree` accepts a structurally valid one-version tree
whose version is `local-v2`. The original append formula also generated
`local-v2`, duplicating its identity and making the newly generated tree fail
its own readback validation. The same formula was used by save, branch and the
explicit concurrent-version simulation.

Repair: one private helper chooses the first unused local ID starting at
`versions.length + 1`. All three append paths use it. Normal sequential IDs
remain unchanged; valid noncontiguous restored IDs remain accepted. No storage
schema, public export or event shape changed.

## Exact read-only authority and owner references

Reference root:
`recovery_inspection_20261017/remote-main-readback/source/LUMENIS-codex-Clean-OS-main/`.
These clauses constrain the local demonstration; they do not establish that it
implements, calls or replaces the product owner.

- `AGENTS.md` §11, lines 1287–1305: consequential writes pass actual
  Permission/approval/effect boundaries; denied/pending actions create no
  forbidden effects and must not fake success. §13, lines 1364–1385 separates
  UI entry and fixtures from real user-visible completion. §14,
  lines 1422–1450 distinguishes isolated regressions from actual product E2E.
- `00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md`, lines 52–53:
  C4 owns media/Timeline/project state; C5 owns Reporting/SavedWork/Artifact
  source continuity, conflict/revision, save/reopen/recovery. Lines 547–551
  require idempotent repeat, preserved revision parent, byte/source-version
  recovery, retained old results and affected-only correction.
- `contracts/experience/screen-specifications/BMP-10.md` §§2–5:
  real read scope and lineage are required, local response drafts do not send,
  publish or change a risk record, and severity is not invented. Lines 77–82
  explicitly separate source, judgment and outcome, bind scope/Evidence/decision
  version, and retain history after source withdrawal without claiming response.
- `contracts/experience/screen-specifications/SH-04.md`, lines 35–44:
  unchanged retry retains request identity; reopen matches the exact
  Artifact/digest/version; revision preserves parent and source scopes. Lines
  83–85 and 110 require a new immutable child with its parent still selectable.
- `lumenis/shared/reporting/saved_work.py`, lines 728–749: the actual owner
  checks request ID and input hash for replay, rejects a mismatched previous
  Artifact with `WORK_REVISION_CONFLICT`, checks the prior draft digest, and
  records immutable parent Artifact/digest and incremented version.
- `contracts/experience/screen-specifications/BMP-08.md`, lines 3–11:
  Shared/C4 owns independent podcast production and retained versions/recovery.
  The Script/Audio refinement, lines 66–76, distinguishes transcript and actual
  sound and preserves selected segment/time. The acceptance/addendum, lines
  91–103, requires reversible edits and one workspace player, with explicit
  “改稿不改音频” semantics.
- `podcast/intelligence/episode_runtime.py`, lines 127–137 validates finite
  source bounds and positive duration; lines 451–462 emits chapter boundaries
  from actual output segments. This local fixture's integer sample indexing
  is not that product API's time representation.
- `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md` §38,
  lines 1343–1350 binds actions to source/result version and Permission with
  stale-action rejection and parent/rollback preservation. Lines 1391–1398
  require deduplication, preservation of user edits, distinct preview/save/
  execute states, revocation behavior and interrupted-work recovery.

## Covered behavior

- Risk: reason before preview, explicit record, repeated record, edit/decision/
  cancel invalidation, withdrawal after preview, immutable impacted history,
  revocation blocking old and fresh confirmation, hidden retained history and
  selected-item/draft isolation. Severity stays null and outcomes remain
  `NOT_OBSERVED`.
- Versions: immutable history and reason; repeat-save; non-destructive
  inspection; explicit old-content adoption; concurrent-head conflict;
  explicit branching and branch continuation; validated recovery with
  noncontiguous IDs; rejection of damaged ancestry, duplicate IDs, missing
  references and oversized payloads; detached validated copies.
- Chapters: exact half-open sample ranges and unchanged audio samples;
  first/last-sample and rounded endpoint bounds; invalid source units and
  markers; metadata-only reordering; apply/undo session invalidation;
  cancel/no-op/repeated apply; undo against a pending revision; source switch
  fencing previous proposals, sessions and undo history; independent
  revision/source identity/source version guards; invalid replacement and
  media-error recovery; stale loop range and session rejection.

## Interface compatibility and unverified boundaries

All existing module exports, reducer events and state fields remain compatible.
The corrected branch `base` value is serialized by the existing host; the
validator already accepts the new branch ID as a valid base. The helper is
private and introduces no new import or dependency. The offline build must be
regenerated after changes, as the integration owner did.

The local tree deliberately supports branches; the inspected SavedWork backend
uses sequential, current-parent revisions and server request/digest checks.
This repair does not add backend branching or imply API compatibility for
local IDs. A production adapter must use the real owner contract.

Risk's `allowed` flag is a fixture, not server Permission or a scoped binding
receipt. The version/chapter reducers have no actor/permission API; their
real revocation and privacy behavior needs the authorized host/owner adapter.
No backend save, export, real risk event/decision, server idempotency, source
authorization or persisted audio result is established by these tests.

Browser focus, keyboard/touch operation, screen readers, actual localStorage
failure/reopen in the tree host, route continuity, actual media decoding and
single-player audition, and Flutter/native acceptance were not tested here.
The chapter sample-rate/count limits are fixture limits, not product limits.

## Reproduction commands

```sh
node --test tests/remaining-state-contracts.test.mjs
node --check src/version-tree.mjs
node --check src/risk-review.mjs
node --check src/media-chapters.mjs
node --test $(find tests -maxdepth 1 -name '*.test.mjs' ! -name 'offline-bundle.test.mjs' -print | sort)
```

Integration owner only: rebuild via `python3 tools/build_offline.py`, then run
`node --test tests/*.test.mjs` against the regenerated offline artifacts.
