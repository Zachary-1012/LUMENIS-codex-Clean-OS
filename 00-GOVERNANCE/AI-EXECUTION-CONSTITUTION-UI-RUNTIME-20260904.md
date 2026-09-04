# AI Execution Constitution · UI / UX / Runtime

Status: LOCKED / ACTIVE
Scope: ZBC × OSAI shared execution standard

## Objective
Natural-language product intent must become executable, testable contracts before implementation. AI must not freely reinterpret established product, UI, UX, data or runtime intent.

`Requirement → Design Contract → UX Contract → Data Contract → Runtime Contract → Render Contract → Code → Test → Runtime Verification → Visual Verification → Regression → Evidence`

If correctness cannot be demonstrated, the task is NOT DONE.

## Shell
Default shell: `Left Navigation → Main Workspace`.
A persistent right-side context surface is NOT default. Context/detail surfaces require an explicit feature contract.

## Ownership
- Production data: one canonical source of truth.
- Business calculations: one canonical function/formula.
- Runtime state: one authoritative owner.
- Visual region: one render authority and one DOM/layout owner.
- Components may not compete to mutate the same region.

## Design-language compilation
Qualitative design intent must be compiled into versioned tokens/contracts for typography, spacing, surface, glass, border, shadow, blur, density, motion, scale, opacity and layer behavior. No parallel visual rules when approved tokens/components exist.

## Dynamic cards
The AI Workspace may expose up to 20 dynamic cards. A single stack controller owns active index, position, scale, opacity, blur, z-order and interaction state. Cards do not independently control global stack behavior.

## Runtime truth
Source/document existence does not mean active capability. Observable lifecycle:
`REGISTERED → SYNCED → LOADED → READY → RUNNING → UPDATED → VERIFIED`.

## Data/UI rule
UI consumes canonical View Models and must not independently recompute canonical business metrics.
`Source → Evidence → Validate → Normalize → Canonical Data → Function → Metric → View Model → UI`.
`0`, `NULL/UNKNOWN`, `NOT_AVAILABLE`, `STALE`, `ERROR` are distinct states.

## Change boundary
Every AI task defines allowed files/components/routes/state and forbidden areas. Unrelated global or other-feature changes require explicit authorization.

## Root-cause repair
For overlap, clipping, disappearance, stale UI, incorrect values or visual drift, diagnose root cause before patching. Do not use `z-index`, `!important`, `position:absolute`, `overflow:hidden` or similar as a masking first-line fix.

`Root Cause → Evidence → Patch → Regression Test → Result`

## Unknown / stop
Unknown requirements, data sources, APIs, ownership or runtime state are marked `UNKNOWN`; the affected branch stops until resolved. Guessing is prohibited.

## Verification
`Requirement ✓ Design ✓ UX ✓ Data ✓ Runtime ✓ Interaction ✓ Visual ✓ Regression ✓ Evidence ✓`
Implementation alone is not completion.

## Traceability
`Research-ID → Decision-ID → Task-ID → Commit-SHA → Test-ID → Evidence → Result`.
Historical conclusions are preserved when revised; new evidence and reason for revision must remain traceable.

## Twin boundary
ZBC remains Production Truth: production code, data, runtime and release. OSAI remains Research & Intelligence: research, evidence, evaluation and implementation specifications. No uncontrolled cross-repository writes and no third core repository.

**Final rule:** `DESIGN INTENT = CODE = RUNTIME = DATA = UI = USER EXPERIENCE`.
Otherwise: `NOT DONE.`
