# Demo 34: chapter route continuity

Date: 2026-10-17. Scope: the independent interaction review copy only. No product source, database, backend, deployment, app integration or offline bundle was changed by this bounded adapter change.

## Existing sources consulted read-only

Source root: `recovery_inspection_20261017/remote-main-readback/source/LUMENIS-codex-Clean-OS-main/` (existing remote-main readback, not a claim of a new remote fetch).

- `AGENTS.md`: existing-owner reuse, save/revise/reopen/recover, protected Permission and evidence boundaries; a route or contract alone is not completed product delivery. SHA-256: `f748d46d7a18c357d27576f44c345023601e452344f5da56f74106f52e850367`.
- `contracts/experience/screen-specifications/BMP-08.md`: existing Shared/C4 production ownership; compatibility BMP-08 route; one player; selected segment and known time survive Script/Audio view switching; source/rights, drafts and actual sound remain separate. SHA-256: `faf53e2e3cdf42083462af6f3e050009ae47bfaf2464df6db1914512fb2f2042`.
- `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md`: Return restores selection/scroll/context (including lines 813–820 and 1055); presentation state is not Permission or business truth (line 992). SHA-256: `ccc2e93e52bafde51e2b41e1c61003d6f67d436e27b72a06f8193566c15830fc`.
- `app/lib/features/bmp08/bmp08_view_model.dart`: refresh clears snapshot/action state; staging checks the current snapshot permission; disposal blocks later refresh outcomes. This remains product-owner code, not imported into the review adapter. SHA-256: `e2db834a8f1c635a408b77722cf16e99b4cc89c292138b17154428afa31ff516`.
- Review-only integration patterns: `src/review-session.mjs`, `src/navigation-study.mjs`, `tests/revision-route-adapter.test.mjs`; chapter domain remains `src/media-chapters.mjs`.

## Corrected existing gap

Previously leaving demo 34 disposed its in-memory source map. Returning recreated initial chapters. Switching the two fixtures also discarded their pending proposals.

`createChapters` now accepts optional injected `session`. Its `chapters` slot holds a versioned, per-known-fixture snapshot of chapters, selected chapter, revision, pending proposal and undo history, plus raw unsubmitted name/start input, text selection/direction, field scroll and body scroll. Source changes preserve each fixture independently. Returning never applies a pending proposal automatically. Cancel, Escape and undo continue to use the original reducer.

Restoration accepts only matching fixed fixture source metadata, valid sorted chapter sets with the expected IDs, selected IDs, bounded history, positive revision and matching proposal baseline/source/selection. UI selections are clamped. Invalid entries fall back to that fixture's initial state; exceptions during session read/write do not prevent mounting or media cleanup. Only the two known fixture entries are restored. No snapshot field is interpreted as authorization.

Exit pauses the native audio adapter, clears loop/load intent, removes listeners and src, unloads and revokes the object URL. Playback generations invalidate old asynchronous work. Return creates a fresh full-source player with no autoplay or loop. Runtime audio, URLs, listeners and permissions are not persisted. Native number inputs do not support selection ranges, so that browser exception is handled; supported text selection is restored.

This demo has no permission grant/revocation model. This work neither invents one nor claims to verify revoked product permissions. Whitelisting drops injected permission/runtime fields; the actual product must still check its live Permission owner. The existing revision-route permission-revocation test is separate evidence.

Persistence is only the current page's review session. Refresh or closing the page loses it. No backend or durable save claim is made. Audio playhead persistence across leaving the route is not claimed; the restored full player starts at zero, with the selected chapter preserved for explicit seeking.

## Verification and limits

`node --test tests/chapter-route-adapter.test.mjs`: 6/6 passed. Tests call the actual `createChapters` adapter with a minimal DOM/media double, exercising real registered callbacks and disposal rather than only reducer snapshots:

1. Two-fixture revision/proposal/selection/undo and raw-field/scroll/selection continuity.
2. Restored proposal cancellation and Escape without accidental adoption.
3. Pause, URL revocation, listener removal and isolation of a late rejected play promise after remount.
4. Explicit stop and hidden-page stop; no replay on return.
5. Invalid/stale snapshots and injected permission/runtime fields cannot crash or grant state.
6. Optional or throwing session does not obstruct media cleanup.

Full suite excluding the parent-owned generated offline artifact: 213/213 passed at the time of the run. Other workers were adding tests concurrently, so this is a dated local observation. The earlier full run was 185/186 with only the offline manifest hash assertion failing due to pending rebuild. The parent owns app session injection and offline rebuild/recheck.

These are Node contract tests, not browser rendering, audible playback, codec, device, native selection/scroll layout, touch, screen-reader, visual or product acceptance evidence. Real browser QA remains open. No new product ability or visual acceptance is asserted.
