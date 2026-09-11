# LUMENIS Motion Guidelines (self-built runtime, no Anime.js / no lib)

Machine registry: `MOTION_REGISTRY.json` (M01–M15, each with timing band, semantic_reason, reduced_motion). Runtime: `10_prototype/assets/motion.js` (WAAPI + self-written; interruptible).

## Timing bands
Micro 80–180ms · Component 180–280ms · Layout 260–420ms · Workspace 320–520ms · Special ≤650ms. Standard easing `cubic-bezier(.2,.7,.2,1)`; entrances `cubic-bezier(.2,0,0,1)`.

## Canonical motions
| ID | Motion | Semantic reason |
|---|---|---|
| M01 | AppShellReveal | establish workspace once on entry |
| M02 | NavActiveTravel | show where the user moved in IA |
| M03 | ContextChange | signal subject/context switch (view, not data) |
| M04 | Card→WorkspaceMorph | expand a card into its workbench |
| M05 | Capability→Task | AI capability resolves into an accepted task |
| M06 | TaskStageProgress | show real pipeline stage progress |
| M07 | ArtifactReveal | present produced artifact (artifact-first) |
| M08 | EvidencePreview→Rail | move evidence from inline to reference rail |
| M09 | Drawer / BottomSheet | surface secondary panel without leaving page |
| M10 | SegmentedTravel | segmented/tab content transition |
| M11 | CalendarSelection | date range selection feedback |
| M12 | UploadPipeline | real upload stage + segmented progress |
| M13 | SuccessResolution | confirm completed action |
| M14 | Error / Recovery | surface failure + recovery path |
| M15 | ComposerState | AI nine-state transitions |

## Rules (hard)
1. Every played motion carries a `semantic_reason`; `motion.play()` rejects and warns if missing — no decoration-only animation.
2. Stagger at most 5 groups (0/40/80/120/160ms); long lists enter as one block.
3. Every sequence is interruptible and cancels cleanly (`interrupt()` cancels WAAPI).
4. `prefers-reduced-motion: reduce` jumps every motion to its final state instantly; count-up writes the final value; reveals appear immediately. Screenshots are captured under reduced-motion for deterministic final values.
5. One primary motion per view-region; gradient/aurora at most one per screen; never animate an indeterminate loop to imply work that is not happening (no fake "thinking").
6. Motion ≤10% of the experience; data/evidence/report surfaces stay calm and opaque.

## AI nine-state motion (M15)
BOOT→INTENT_HOME→COMPOSING→TASK_ACCEPTED→EXECUTING→ARTIFACT_READY→APPROVAL→ACTION→EVALUATION. State transitions reflect real backend state; EXECUTING steps map to real tool calls; if the backend is not bound, the UI shows the correct non-ready state instead of pretending.

## Research lineage (clean-room, principles only)
Showreel Before/Trigger/Continuity/After model and Anime scene model were studied as principles and re-implemented originally. Sources and what was/was not reused are in `13_research/`; no third-party runtime or asset ships in the product.
