# AI EXECUTION MASTER COMMAND V2

Status: ACTIVE
Authority: Canonical execution entrypoint for AI-assisted work
Scope: ZBC and linked OSAI work

## 1. Authority order
1. Safety / legal constraints
2. Product and canonical data truth
3. CANONICAL-AI-EXECUTION-BASELINE-V1
4. Domain contracts
5. Current task requirement
6. Research evidence
7. Implementation details

No parallel document may silently override a higher layer. Historical documents are RECORD or SUPERSEDED unless explicitly reactivated through a new decision.

## 2. Before changing anything
READ current baseline, authority map, relevant README/AGENTS, domain contracts, existing implementation, tests, and prior decisions. Search for reusable code before creating new code. Never guess when a required fact is unknown.

## 3. Requirement compilation
Convert natural-language requests into Requirement-ID, user goal, information hierarchy, UX behavior, visual intent, data/runtime/render requirements, dependencies, change boundary, lifecycle, and acceptance criteria. Register the requirement before implementation.

## 4. Product/UI shell
Default workspace: left navigation + central workspace. No permanent right context column by default. Prefer a fixed viewport with integrated information hierarchy. Do not create endless page scrolling. When content exceeds the current layer, use child page, focused workspace, sheet, dialog, popover, or bounded local-scroll region with explicit scroll ownership.

Homepage is an AI work cockpit, not a feature warehouse. Show only core/high-value/current information. Card count is variable; do not force a target number. Secondary/deep information belongs in the relevant feature page. Glass, motion, and effects are functional and restrained; information and usability outrank decoration.

## 5. Rendering ownership
Every rendered region must have one state owner, data owner, layout owner, renderer/DOM owner, and event owner. Never allow competing renderers to mutate the same region. Do not hide structural bugs with arbitrary z-index, !important, overflow, absolute positioning, or duplicate DOM.

## 6. Data/runtime truth
UI does not invent business truth. Canonical data flows through validation/normalization/domain functions/view models before presentation. New capability or data is not considered live merely because it exists in GitHub.

Required lifecycle states where applicable:
REGISTERED -> SYNCED -> LOADED -> READY -> RUNNING -> UPDATED -> VERIFIED -> DELIVERED -> MONITORED -> IMPROVED

## 7. Lifecycle traceability
Every meaningful change must be traceable:
Research-ID -> Decision-ID -> Requirement-ID -> Task-ID -> file/function/component -> Commit-SHA -> Test-ID -> Evidence -> Result.

Do not overwrite history. If new evidence invalidates a decision, mark the old decision superseded and record the revised decision and reason.

## 8. Verification gate
Implemented is not verified. Before delivery check requirement coverage, product intent, UI/UX, data accuracy, runtime behavior, rendering, interaction, visual integrity, regression, lifecycle state, and evidence. Any FAIL, UNKNOWN, or BLOCKED item prevents DELIVERY READY.

## 9. Change boundary
Declare allowed files/components/routes/state/runtime and forbidden areas before implementation. Cross-boundary changes require impact analysis and an explicit decision record.

## 10. Research adoption
Research Apple, open-source AI/ML, rendering, interaction, accessibility, and relevant technical cases for principles and mechanisms, not imitation. Classify findings as ADOPT, ADAPT, DEFER, or REJECT with evidence and rationale.

## 11. Rule hygiene
Do not add another permanent/maximum-priority instruction when an existing contract is sufficient. Prefer one canonical rule plus explicit domain contracts. Remove or mark duplicate/obsolete instructions instead of creating another layer. Status vocabulary: ACTIVE, DOMAIN, RECORD, SUPERSEDED.

## 12. Failure handling
When a bug appears, identify root cause, evidence, patch, and regression coverage. For UI coverage/overlap, inspect viewport, sizing, overflow, visibility, opacity, positioning, transforms, stacking context, mount/unmount, async rendering, ownership, and duplicate render paths. Fix the structure, not only the symptom.

## 13. Execution loop
READ -> AUDIT -> RECALL HISTORY -> RESEARCH -> CONTRACT -> BOUNDARY -> PLAN -> IMPLEMENT -> TEST -> RUN -> VERIFY -> VISUAL VERIFY -> DATA VERIFY -> RUNTIME VERIFY -> REGRESSION -> LIFECYCLE TRACE -> EVIDENCE -> COMMIT -> REPORT -> NEXT.

Do not skip stages silently. If a stage is not applicable, record N/A and why.

## 14. Completion report
Report: objective, baseline, research, decisions, files/functions changed, runtime/data/UI effects, tests, visual verification, regression, lifecycle trace, evidence, commit, requirement coverage, remaining risks, and status.

Status must be one of PASS / FAIL / PARTIAL / BLOCKED. Never claim completion from code existence or a static page alone.

## 15. Core principle
Do not optimize for more rules. Optimize for fewer conflicting rules, explicit ownership, bounded changes, deterministic rendering, canonical data, lifecycle visibility, and machine-verifiable delivery.
