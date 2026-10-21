# Recovered review repairs: adapter contracts

These modules are independent JavaScript review logic. Formal product integration must use the existing Owner/API and current app toolchain; no Flutter/native runtime has been compiled or accepted here. Rebuilding the view does not require copying this review shell.

## State and version boundaries
- `recoveryReduce(state,{type:'kind',id,kind})`: only registered recovery kinds; a changed kind advances the attempt token and suspends the item. `observe` must include the current source id and attempt, and cannot turn blocked/risk/cooldown into success. `dismiss` closes only the view; `defer` relinquishes active queue ownership. Adapter health is a supplied observation, not a real session check by this demo.
- `streamReduce` source `revision` is monotonically observed per block within a run. `seenRevision` is an additive optional field so earlier snapshots remain readable. Human text remains authoritative until explicit adopt. Reject does not reset the observed revision watermark; stale suggestions cannot return. New run creates a new scope.
- `endDrag(state,timeMs,pointerId=state.pointerId)`: optional third parameter preserves old two-argument callers. Pointer ownership is required when a view handles multiple pointers. Units remain CSS/logical px, milliseconds in, px/second velocity out. No server effect.

## Persistence adapter
- `writeLocal(Storage,key,value) -> {ok,reason?}` serializes once, writes once, then compares exact readback. There are no automatic retries. `ok:false` does not mean the write definitely had no effect; the UI retains its working state and reports unconfirmed persistence.
- `removeLocal(Storage,keys) -> {ok,results:[{key,ok}]}` reports partial removal. It touches only declared keys, never unrelated review notes or task versions.
- Canonical `lumenis-review-preferences` remains version 1 with additive `appearance` and `revealMotion`. Existing legacy keys are read only as fallbacks. Save is explicit; changing a control previews in current memory. Global reset clears the canonical and two legacy preference keys, verifies absence, and reports partial failure. Wallpaper file URLs are not persisted.
- `appearancePreferences(input)` permits a six-digit hex color, finite font size clamped 13–18, and a strict boolean for the localized frosted example. These are current review-safe ranges, not a product-wide typography decision.

## View lifecycle
- `createReviewSession(allowedRoutes)` returns cloned in-memory `read/write/clear` snapshots. Allowed route ids bound allocation; it is not a persistent document store. Current mounted session routes are navigation, local budget revision, chapters, topic planning, research learning, commands, aggregate feed, independent report, intelligent view, context selector, provenance adoption and typed presentation. Each stores only its own validated local presentation/draft state; persistence and permission boundaries differ by its explicit module contract. The revision route preserves the reviewed proposal, manual note, uncommitted numeric inputs, selection and scroll, including revoked authority. Each additional workflow needs its own state/permission/version contract before claiming continuity.
- `canOpenDialog(candidate,openDialogs)` prevents another open native dialog from losing modal ownership to a shortcut. Views still own native dialog close/cancel, focus restoration and accessible labels. Logic tests do not prove screen-reader or keyboard behavior in a browser.
- File intake uses a per-intent generation; new selection, empty selection, explicit reopen, cancel and dispose invalidate both late success and late failure. Notes/original text are not replaced by stale file callbacks. File read and storage remain local examples.
- Reveal cancellation now invalidates pending font-ready work. Its rendered trajectory and font/layout timing remain pending actual browser QA.

## Failure/verification boundary
`BROWSER_QA_ATTEMPT.md` records the failed preview connection. Current tests cover pure state and selected minimal-DOM adapters; no successful screenshots, real backend request, platform authentication, AI inference, media engine or native device validation is implied. Future binding should map intent/result/error/cancel to the original Owner's real idempotency, permission and receipt semantics rather than translating LOCAL_ONLY into success.
