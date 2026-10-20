# 11 incremental native presentation: local continuity revision

Date: 2026-10-17. Source: current Experience 1388–1396 (typed incremental presentation, old-run isolation, user priority, draft/save distinction) and full plan G116 line347. Requirement meaning is recorded separately in FRONTEND_AIGC_SCOPE_CORRECTION.md. This module is a partial frontend intelligent-presentation contract; it is neither an AIGC content-production tool nor proof of full frontend AIGC.

## Code/adapter boundary

`contracts.mjs`: `initialStream`, `streamReduce`, `validStreamSnapshot`, `STREAM_LIMITS` are view-independent. Retained input API uses `type/run/id/revision/kind/text`; optional scope mismatch fails closed. This is the existing local review schema, not an invented production Task/run/attempt schema. A product adapter must bind real actor/scope/input-version/Task/attempt/checkpoint and original Owner source references before routing events. There is no model or network transport here.

`stream-study.mjs`: native textarea/button DOM adapter, mounted at existing11. State survives same-session route changes; there is no persistent/server save. No new entry is counted. Artificial new blocks/corrections/errors/disconnect/complete/revoke are in unified review settings. Normal work keeps pause reading, resume reading, cancel receive, checked new-round confirmation and block editing/adopt/reject/undo. Returning to a route renders its current local snapshot; this is not a server resume receipt.

## Actual behavior

- Incremental append preserves existing editor nodes, focus, selection and scrolling. No forced scroll-to-bottom. Plain text never executes HTML.
- Edited block receives later correction as an explicit candidate. Another human edit invalidates that adoption; source seenRevision prevents rejected old candidates returning. Adopt carries the supported kind; direct undo restores prior human text while retaining monotonic source revision. Later edit/source revision invalidates undo instead of rolling back intervening work.
- Pause reading defers incoming block display, not transport/Task execution. Resume reading does not change offline state. Disconnect and terminal completion are different; offline receipt requires explicit local reconnect fixture, terminal/cancelled state rejects late blocks. Already-readable text remains locally editable after cancel/complete.
- Restart is explicit confirmation, bound to actual visible inputs and state; edits/Escape cancel it. Restart never restores denied permission. Revoke immediately clears visible text, even while reading updates are paused, and persists denial on route return.
- Disposal disables old callbacks and removes settings. Route memory retains local text/selection/scroll but never claims formal save. Invalid input stays in its field rather than being silently truncated or overwritten by unrelated updates; native text capacity is20k UTF16 units per block.
- Bounds:128blocks,20000UTF16 units per block,524288units for visible+pending candidate text,128-unit safe IDs. Prototype names, non-safe/negative revisions and malformed local snapshots rejected. One bounded prior adoption per block may additionally be retained for undo. Parameters are local review resource limits, not imposed as a product content ceiling.

## Evidence and remaining gaps

`tests/stream-safety.test.mjs` and `tests/stream-adapter.test.mjs` cover new regressions; existing contracts/recovery stream tests remain. Full suite log is `current-regression.log`, rebuilt offline same source. Node/minimal DOM proves logic and DOM contract only; no browser/native screen-reader/touch/frame-time acceptance. The view currently uses actual text blocks; `comparison` is only a registered contract kind here, not a full data-table rendering claim. Production typed data/provenance/units, Gateway C2 proposal quality, transport/checkpoint, durable SavedWork/Artifact receipt, all-screen adaptation, trilingual UI and visual quality remain OPEN.
