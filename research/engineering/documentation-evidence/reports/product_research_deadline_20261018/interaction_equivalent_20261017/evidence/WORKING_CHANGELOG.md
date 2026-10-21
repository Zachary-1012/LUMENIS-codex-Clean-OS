# Independent review working revision 2026-10-17

Frozen recovery inputs remain unchanged. This is new development based on the recovered v12 demo and v5 tests, not a byte-for-byte restoration of the lost later implementation. Product source and Site are unchanged.

## Verified local baseline
- v5 original Node tests against recovered v12 source: 27/27 passed.
- Current regression set after recovery/stream/persistence/session repairs: 62/62 passed, including file-intake and appearance adapter tests using a minimal in-memory DOM.
- `app.mjs`, `navigation-study.mjs`, `command-study.mjs` syntax checked.
- Official cloud-browser QA was attempted but the independent local preview was unreachable; details in BROWSER_QA_ATTEMPT.md. No browser, touch hardware, accessibility-reader, visual or native-platform acceptance passed in this revision.

## New changes
1. `recovery.mjs` accepts a typed `kind` transition. Source-state changes invalidate old attempt observations and suspend the task. Restricted kinds also reject successful observations defensively. Demo selector uses the reducer rather than mutation.
2. `contracts.mjs` retains highest seen proposal revision across human edits and rejected proposals. Late older/duplicate suggestions cannot replace newer suggestions or reappear after rejection.
3. `local-persistence.mjs` verifies exact storage readback; failure is reported without destroying current editing state. Review notes and parameter-save UI now use it. Reset verifies removal and honestly reports partial failure.
4. Reveal preference joins the canonical parameter save, with migration read from the legacy key. Selecting a reveal option previews it; explicit unified save persists it. Reveal clear events invalidate pending font-ready work. The latter adapter change is syntax checked; real rendering awaits batch QA.
5. Appearance uses a bounded schema and injected preference state. Changing local appearance does not remount the active task. Wallpaper remains a local object URL, deliberately excluded from durable preferences.
6. `review-session.mjs` provides an injected, bounded, cloned in-memory route snapshot and one-modal guard. Navigation demo stores text/selection/scroll when leaving its route. Command shortcut cannot open a second modal over settings. Pure contracts passed; focus restoration and browser route behavior await batch QA.

## Still open, not hidden by current pass count
- Other demos do not yet have per-object route snapshots. Navigation preservation cannot imply whole-product continuity.
- Appearance now uses injected get/set state and joins canonical explicit save/reset. Legacy appearance keys are migration-only, reset verifies their removal. Pure bounds/schema and storage failure tests pass; Six minimal-DOM appearance adapter checks pass; actual browser behavior remains pending.
- All additional audit findings remain tracked in RECOVERED_CONTRACT_AUDIT.md until backed by a fix and a new reproducible test.
- File intake late success/failure after reopen, cancellation, replacement and disposal is repaired and covered by nine adapter tests; actual browser file picker/read timing remains pending.
- Real backend binding, all 200+ distinct useful contracts, product-native ports and complete product workflow acceptance remain unfinished.

## Work order and expansion gate
Existing planned capabilities and recovery contracts take priority. New proposals require research before coding: a concrete user pain point, original Owner, expected time/cost saving, measurement method, and net benefit after added user steps, configuration and maintenance cost. The 44-screen inventory is not a ceiling, but neither new screens nor effects count as value on their own. Missing video references remain unreviewed; no claim that their contents have been absorbed.

## After 12:43 freeze, working revision 2
- Pointer release now checks owning pointer; a second pointer cannot steal the active drag or release it. Added a backward-compatible optional pointer id to endDrag, tested. Pointer capture/browser touch remains pending.
- Settings header is sticky so its return control is intended to remain visible; actual narrow-screen/large-text rendering remains pending, not visually accepted.
- Added ten outcome tests for recovered confirmation, civil scheduling, and optimistic version merge contracts. These demonstrate only stated local boundaries, not remote persistence or real scheduling.
- Budget-revision route now retains local state, pending proposal, manual text, numeric-input drafts, selection and scroll through an injected route session. Three mounted-adapter tests cover restoration, explicit adoption and retained revocation. Other editors still require per-workflow continuity rather than a blanket claim.

### Current-source relation correction
Read current main CTH-04.md Intelligent UI supplement, line 142: “缺证据不画边”. The recovered relation fixture drew an unsupported inference as a dashed edge. `relations.mjs` now separates unsupported candidates from drawable edges, requires valid endpoints and a nonblank supplied source, clears both lists on revocation, and reports omitted candidates visibly. Four pure regression tests pass. The motion lifecycle tests were adjusted to select the supported fixture repeatedly rather than depend on the now-forbidden unsupported edge. Historical 12-failure reproduction logs refer to the pre-correction test fixture revision, not byte-identical final tests.

## Offline artifact correction after 12:50 freeze
The recovered offline.html was an embedded v12 build and did not automatically follow source repairs. It is now preserved as historical/offline-v12-recovered.html. tools/build_offline.py creates a NEW current offline.html from the reachable static module graph, with module-scoped bindings and strict export checks. Its 43 reachable modules, asset and final artifact hashes are recorded. Three build tests compare current hashes, native ESM exports and initialized logic modules; browser execution is still pending. Six additional batch parser/recovery tests passed without changing batch logic. Current full suite: 103/103.

## Original demo69 integrated with new language dependency
Exact recovered candidate core/view/tests were imported after hash checks, then the view gained a bidi-control warning and control-visible inspection copy. New content-language module implements full declared Unicode/fidelity diagnostics rather than a stub. Original core/test bytes remain exact; modified view provenance is explicit. The historical requirement remains real Web resumable upload, while this bounded local workbench remains UNBOUND. Current index has40 entries, not69; missing40–68 remain missing. Whole suite178/178 passed after offline rebuild, including21 remaining-state tests and version-tree fixes reported separately.

## 13:13 ongoing working revision: useful podcast workflow and settings consistency
- Added NEW source-backed topic planning demo70 (not a recovered lost40–68 module). Actual route owner `podcast/intelligence/topic_scoring.py` differs from retained legacy `topic_score.py`; the live route imports the former. Missing observations remain null, human guest gates stay separate from independent owned-audio/script creation. Simulated suggestion comparisons are explicitly labelled and never invoke models. Local saving/readback, reopen confirmation/cancel, route draft preservation and unknown/failed outcomes are demonstrated; actual production handoff remains UNBOUND.
- Demo34 now receives the shared review session; per-fixture revisions, pending edits, history, field drafts, selection and scroll survive route changes. Playback resources are released on leave and playback never resumes automatically. Six mounted-adapter tests cover this; no browser acceptance claim.
- Found a real settings inconsistency: demo69 chunk preference lived only inside its view, so global Save could not retain it. New bounded `file-preferences.mjs` injects it into canonical version1 preferences. Save/readback and Reset now cover it; resetting changes only the next file, not a prepared manifest. A mounted test verifies reset/cleanup and a pure test rejects coercion/unsupported values.
- Added reproducible inventory/delta generator `tools/index_evidence.py`; inventory counts are distinct from full semantic coverage. Synthetic local runtime measurements are recorded separately in CONTRACT_BENCHMARK.json, not promoted to browser FPS or mobile performance acceptance.

## 13:20 integrated working revision
- Demo71 adds current P13 research classification, evidence side-read with retained anchor/scroll, explicitly synthetic validation records, local human review, counterexample veto, source expiry/withdrawal and reopen revalidation. The actual Shared Owner's promotion gate remains unconnected; no UI success message claims product promotion. Four mounted-adapter checks complement twelve pure contract tests.
- Demo25 command panel now shares the in-memory route session. Six mounted-adapter tests cover retained draft/selection/scroll/result, no automatic reopened modal, modal exclusion, focus-return choices, empty search, prevented shortcuts, disposal and stale callbacks. These are DOM contracts, not actual browser focus acceptance.
- The long review index gains a keyboard direct-to-work button that does not mutate the hash or reload the task, plus semantic aria-current. Two pure tests cover modal ownership and current-route semantics; visible focus/reader testing remains open.
- Demo70 refuses to claim saving while a visible signal input was rejected by validation. An adapter regression preserves the old state and requires correction before save.
- Current integrated run: 247 tests passed, zero failures/skips. Inventory42 entries is distinct from source requirement or interaction coverage. Offline bundle52 reachable modules built and tested; current full visual/backend/native acceptance remains pending.
