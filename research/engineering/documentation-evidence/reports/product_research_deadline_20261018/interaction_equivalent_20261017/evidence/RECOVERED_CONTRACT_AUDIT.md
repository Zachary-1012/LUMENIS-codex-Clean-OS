# Recovered demo contract audit

Date: 2026-10-17 (UTC). Initial scope: read-only audit of the recovered independent review demo, not the LUMENIS product or a deployment. No browser was opened by this audit worker. No product code, runtime, database, credentials or host configuration was changed. The supplied product governance documents were read only. The later explicitly delegated working-copy repair and test work is recorded separately in the addendum below; frozen recovered source remains unchanged.

## Findings first

The recovered demo has 39 distinct study entries (01–39). The five v5 Node test files remain import-compatible with the recovered source. This does not establish the complete 200+ requirement scope, integrated workflow continuity, browser accessibility, or product acceptance.

Highest-value repairs in the independent working copy:

1. Give the settings layer one complete, explicit preference model and one active modal/focus owner.
2. Retain per-study drafts and context when navigating the demo, with truthful session-only/persistent labels.
3. Invalidate stale async work on cancel, reopen, navigation, preference change and recovery-state changes.
4. Add DOM/event and new-module regression coverage without changing or weakening the original v5 assertions.

No P0 production defect is claimed because this is a disconnected, explicitly labelled LOCAL_ONLY demo. The P1/P2 priorities below concern the integrity of the review and its future adoption.

## Sources and evidence limits

All file references below are relative to `recovery_inspection_20261017/site_source_readback/dist/` unless prefixed otherwise. Source lines are unusually long in several recovered modules; the function and control names identify the exact location within the line.

Read governance:
- Product `AGENTS.md`: sole router/Experience authority; current source and real outcomes remain distinct from audit claims.
- Product `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md`: lines 259–284 (device appearance owner and preserve draft/selection/route/scroll), 502–508 (single recovery sheet, focus and originating task), 577–583 (explicit setting scope/effect), 619–632 (interruptible motion and reveal lifecycle), 678–682 (concise task-first presentation), 1038–1049 (mounted work under settings, visible return/close), 1393–1398 and 1415–1419 (incremental work and complete task continuity).

Evidence types:
- **Reproduced, pure Node**: imported local pure modules or mounted a single study in a minimal in-memory DOM stub. No browser, network, media playback or product runtime.
- **Source-confirmed**: direct code/control-flow or CSS evidence; browser repeat operation still required before claiming browser acceptance.
- Parent reported a real `node --test tests/*.test.mjs` baseline of **27/27** in `review_working/evidence/recovery-baseline-tests.log`. This report did not rerun or modify that baseline.

## P1: route changes discard the current work

**Source-confirmed.** `src/app.mjs:63,67,117`; representative owners `src/navigation-study.mjs:3–5`, `src/navigation.mjs:1–2`, `src/drawer-study.mjs:19–43`.

`mount()` always runs every cleanup, empties the stage/actions, and creates a fresh study. Drafts and state live inside each `create…` call. Only review notes and selected explicit local-save examples are persisted elsewhere. `navigation-study` protects switching its two internal tasks but does not protect the outer demo navigation.

Reproduction: open `#navigation`, edit the research draft and place a selection, choose another study through the global index, then return to `#navigation`. `initialNavigation()` supplies the original text; the edited text, selection, scroll and pending task state are gone. The source drawer and most other editors have the same outer-route boundary. The navigation study says “本页会话保存；刷新或离开整个demo前…”, which understates that merely choosing another study loses the session.

Repair: a route-owned session snapshot/mount contract or retained mounted task, preserving current fields, selection, scroll, selected object and local versions. Stop media/animation and remove stale callbacks on leave independently of preserving work. Do not relabel memory as server save; explicit reset/discard must remain distinct.

Regression: navigation study A → B → A exact draft/selection/scroll; cross-study A → another study → A; all scoped reset/permission semantics retained; no claim of full cross-product workflow closure.

## P1: a global shortcut opens a second modal over settings

**Source-confirmed.** `src/command-study.mjs:7–8`; `src/app.mjs:45–49`; unused policy `src/experience-policy.mjs:9,15,17`.

The command study installs a `window` keydown listener for Cmd/Ctrl+K. It only checks whether its own dialog is already open. It does not check for an existing settings or other modal, `defaultPrevented`, or the active modal's shortcut scope.

Reproduction: enter `#commands`, open global Settings, then press Cmd/Ctrl+K. The handler calls the command dialog's `showModal()` despite `#reviewSettings.open`. A second native modal becomes active. `previous` is captured from the settings dialog, so Return now follows a stacked-modal chain rather than one active task layer.

`experience-policy.mjs` describes “One modal owns focus; underlying task shortcuts are suspended”, but no recovered module imports or calls that policy. Its existence is not runtime enforcement.

Repair: shared modal ownership/open/close/focus utility or an explicit active-dialog guard in every global task shortcut. Preserve native dialog focus confinement and safe Escape. A setting change must not invoke the underlying task's keyboard actions.

Regression: Settings open + Cmd/Ctrl+K stays in Settings; Escape closes exactly the top permitted layer; source drawer remains open underneath until its own close; focus returns to a connected, enabled opener/fallback.

## P1: a stale file read overwrites a deliberately reopened version; late failures touch disposed DOM

**Reproduced, pure Node with a minimal in-memory DOM stub.** `src/more-studies.mjs:16`, `intake()`.

The async success path checks `generation` after `await f.text()`. “取消读取” and dispose increment it, but “重开本地版本” does not. The `catch` branch does not check generation/disposal before updating `#intakeState`.

Observed reproduction A:
1. Start a deferred `new.txt` read.
2. Invoke “重开本地版本”; visible source becomes `SAVED CONTENT`.
3. Resolve the older pending read; visible source becomes `NEW CONTENT`, silently replacing the explicitly reopened version.

Observed reproduction B:
1. Start a deferred read.
2. Dispose/navigate away, so the stage no longer contains intake nodes.
3. Reject the read promise.
4. The catch branch raises `Cannot set properties of null (setting 'textContent')`.

Repair: every new intent that replaces the displayed input/version increments the generation, including reopen; both success and failure check generation and mounted ownership. Capture owned nodes, and ensure cancelled status no longer remains “正在本地读取…”.

Regression: late success and late failure after cancel, reopen, second input and dispose; user edits after explicit reopen cannot be overwritten by the previous read.

## P1: recovery can accept health from before a new blocked state

**Reproduced, pure Node.** `src/recovery-study.mjs:8`; `src/recovery.mjs:8–9`.

The “注入来源状态” select directly assigns `item.kind` without a reducer event, revision/attempt invalidation or status transition. The subsequent observation only checks active source, attempt and waiting/verifying status; it does not check that the kind/health observation matches the current recovery generation.

Exact reproduction: `AUTH_REQUIRED` → open → begin (attempt 1) → change kind to `BLOCKED` as the current UI does → observe `{attempt:1, health:'verified'}`. Observed result is `{kind:'BLOCKED',status:'recovered',attempt:1}`, active source cleared, and “适配器已核验；仅原任务可继续”.

Repair: represent state observations in the coordinator, invalidate pre-change attempts/health, and require a current permitted recovery/readback contract. Do not simply hide blocked states or label login as their remedy. A genuine fresh health recovery may be accepted only under the explicit new state/readback generation.

Regression: waiting → BLOCKED/IP_RISK/COOLDOWN followed by old verified observation cannot recover; independent queue item unchanged; dismiss/defer remain different; a new valid generation can recover.

## P1: an older suggestion replaces a newer pending suggestion

**Reproduced, pure Node.** `src/contracts.mjs:14–15`; UI caller `src/studies.mjs:28–29`.

`streamReduce()` compares an incoming revision only with `old.revision`. When the user has edited a block, suggestions do not advance `old.revision`; therefore a v3 pending suggestion may be replaced by v2.

Exact sequence: block v1 → manual edit → source suggestion v3 → delayed source suggestion v2. Observed block retains manual text, but `suggestion` becomes `{text:'stale',revision:2}`. The latest pending source suggestion was lost.

Repair: track the accepted/source high-water revision separately from the manual draft, or compare against both current revision and pending suggestion revision. Reject duplicate/older suggestions while preserving manual content and explicit adopt/reject.

Regression: v3 then v2; duplicate v3; reject v3 then delayed v2; adopted suggestion version; run/scope/cancel/revoke fencing.

## P2: settings are visually centralized but their save/reset scope is fragmented

**Source-confirmed.** `src/app.mjs:35–38,57–58,97,110,114`; `src/studies.mjs:33`; `index.html:3`.

- “保存当前偏好” writes only `{version,parameters,motion,effects}` to `lumenis-review-preferences`.
- Result reveal is saved immediately under a second key by its own change handler.
- Appearance color/font/frosting uses a third key `review-appearance` and its own save button. It is available only while the appearance study is mounted.
- Global “恢复默认” resets motion/physics/effects/reveal but never the saved or current appearance preferences.
- “恢复外观默认” only changes the current preview and controls; without a further save, remount restores the previous saved appearance.
- `defaultPreferences` has density/input/effects axes but remains unbound to the actual settings/runtime.

Reproduction: save a non-default appearance; choose global restore; leave and reopen the appearance study. The saved non-default appearance reappears. Alter reveal choice without “保存当前偏好”; it persists on reload, unlike the main motion choice. These are different commit semantics under a unified-settings promise.

Repair: one explicit versioned preference schema and durable-save/reset semantics, with safe migration of existing keys. Keep reveal's value independent from other motion preferences while using the same save contract. State precisely what “restore” and “save” affect. If some effects are contextual, identify their context rather than pretending all settings apply globally.

Regression: preview-only vs saved values, reload, migration, independent reveal choice, complete reset, denied/unavailable storage, return preserves draft/selection/scroll, uploaded wallpaper remains local and excluded from exports.

## P2: reveal cancellation does not invalidate pending readiness

**Source-confirmed async control flow; browser acceptance not performed.** `src/app.mjs:96,100,102–103`.

`clear()` resets drawing/start only. It does not increment `token`. While “保存审核版本” awaits `document.fonts.ready`, pointer interaction, resize/scroll/visibility events and `review-motion-change` only call `clear()`. Once the promise resolves, the pre-event generation still matches and the effect can arm after the supposed cancellation. The preference check occurs before the await, so changing global motion to off while reveal follows motion can still be followed by the old effect.

Repair: separate clearing paint from invalidating an armed/pending reveal; lifecycle and user-interruption events must invalidate readiness, then recheck current preference, generation, visibility and owned nodes after readiness. Font/layout/asset readiness must be bounded and failure must leave readable content.

Regression: deferred font readiness followed by input, skip, resize, scroll, reduce/off change, hidden page, navigation or new save; no stale reveal starts; reopening old saved version never replays.

## P2: settings close action scrolls out of view

**Source-confirmed CSS.** `src/style.css:9`; `index.html:3`; Experience lines 1044–1049.

The whole `#reviewSettings` scrolls (`max-height:90dvh;overflow:auto`), while `.settings-head` is ordinary non-sticky flex content. When scrolling parameters and contextual options, the title/“返回工作” button scroll away. Escape remains available to keyboard users, but the explicitly required visible close/return is absent for touch while deep in settings.

Repair: fixed/sticky title/close region with a separate scrolling body. Keep safe-area and 200% text behavior. Do not collapse necessary controls or reduce scope to solve overflow.

Regression: narrow viewport/large text/long contextual settings; close remains visible without scrolling to top; dialog body remains scrollable and focus-visible.

## P2: current study/menu state and focus need lifecycle coverage

**Source-confirmed gaps, not claimed browser failures.** `src/menu-study.mjs:4,6–7`; `src/command-study.mjs:4`; `src/app.mjs:47`; `src/relations-study.mjs:4–5`; `src/word-study.mjs:6`.

- Several close handlers call `opener?.focus()` without checking whether the element is connected/enabled or providing a logical fallback. The newer physical drawer already has a safer pattern at `src/drawer-study.mjs:144–150`.
- The custom object menu closes on Tab, outside pointer and Escape but has no focusout/resize/scroll ownership path. Each menuitem is a native tabbable button; keyboard/menu focus and native Tab movement require explicit tests rather than a source assertion.
- Relation selection starts an animation and only cancels on filter/revoke/dispose. It does not subscribe to motion preference changes; turning reduce/off on mid-animation will not immediately cancel that existing effect.
- Word-edit adoption starts an untracked `Element.animate()`; onDispose and preference changes do not cancel it.
- Physical drag `src/app.mjs:77–79` accepts a new pointerdown while one is active and pointerup lacks `e.pointerId === pointer`, despite `moveDrag` rejecting a mismatched pointer. Multi-pointer cancel/release remains untested.

Repair/tests: reuse safe focus restoration, one active overlay, explicit menu navigation/Tab behavior, tracked animations cancelled on lifecycle/preference change, and active-pointer ownership. Preserve accessible equivalents; do not remove the interactions to make the checks pass.

## Default simplicity without scope reduction

`index.html:3` renders the full index, review note/votes and context rail at once. `app.mjs:54` renders all studies with no grouping/search; the 16-word motion study has all diagnostic action buttons visible. These are understandable review tools, but do not yet demonstrate a default task-first operational layout or full cross-flow work.

Recommended change in the standalone review shell: task content and primary actions first; searchable/grouped full index; diagnostics, physics tuning, adoption evidence and review controls progressively disclosed. The complete index, every workflow and every requirement mapping remain reachable. Ordinary users must not need to operate a physics parameter panel to perform a task. Critical state/source/permission limitations remain visible and cannot be folded away.

## v5 compatibility and coverage audit

- All relative module imports in the recovered `src/*.mjs` resolve to recovered local files.
- Original v5 tests import only `contracts.mjs`, `direct-input.mjs` and `physics.mjs`; the two artifact suites inspect source/HTML text and local asset presence.
- The original artifact suite checks local-only network/code execution exclusions, the original eight entries, reveal source markers, local voices and bounded text input. Those are useful regressions, not live focus/cancellation/browser evidence.
- The tests do not directly import the 18 subsequently recovered model/policy modules: recovery, version-conflict, command-palette, action-gate, audio-signal, schedule, context-selection, navigation, relations, word-edit, object-menu, media-chapters, batch-review, version-tree, risk-review, propagation-review, physical-drawer and experience-policy.
- The recovered source contains 39 distinct study IDs numbered 01–39. This is the number of demo entry points, not the number of accepted requirements.
- The v5 `requirements/behavior-map.json` explicitly says `INITIAL_SEMANTIC_MAPPING_NOT_EXHAUSTIVE`, with **76** entries. Its `source-extraction.json` has **1,801** extracted blocks from three sources and explicitly disclaims complete semantic reading or completed requirements. Neither count establishes the current complete 200+ requirement inventory.
- Preserve v5 originals as unchanged baseline tests. Add explicit per-contract and integration/lifecycle suites; avoid testing only for new source strings or increasing counts without outcome assertions.

## Suggested repair/verification sequence

1. Freeze baseline source/test receipts and complete requirement inventory provenance; never rename 39 entries or 27 passing tests as “full acceptance”.
2. Implement one settings/dialog lifecycle and route-session ownership in the independent demo only.
3. Repair input/reveal/recovery/suggestion generations; run pure contract regressions and minimal DOM event tests.
4. Add complete preference migration/save/reset and visible settings return, then motion/menu/pointer cleanup tests.
5. Produce source-level and Node-test evidence. Browser, keyboard, touch, screen-reader, 200% text, native and product integration remain explicitly NOT_VERIFIED until separately authorized and performed.

## Addendum: scoped working-copy repair and adapter verification

After the audit, the parent assigned this worker the intake repair in the independent `review_working` copy and tests for the parent's new unified appearance adapter. These do not modify the frozen source or product. The original findings above retain their baseline file/line references.

This worker changed only production-like demo code in `review_working/src/more-studies.mjs`, restricted to `intake()`:
- Read success and failure are fenced by mounted ownership and input generation.
- Reopen, clear selection, cancel, replacement input and dispose invalidate previous reads.
- Current original and notes survive stale callbacks, cancelled reads, missing/corrupt reopen data and read errors.
- Cancel clears the pending status. Reopen validates stored fields before replacing visible content.
- Persistence remains an explicit user action. No read/reopen/late callback automatically writes storage.

Added test artifacts:
- `review_working/tests/intake-race.test.mjs`: 9 passing mounted-adapter tests with minimal DOM/storage stubs.
- `review_working/tests/appearance-adapter.test.mjs`: 6 passing tests for the parent's unified adapter. Tests verify host get/set, preview state, preset/control synchronization, reset-event refresh, preservation of draft/selection/scroll, local-only wallpaper lifecycle and absence of direct storage reads/writes. This worker did not edit `studies.mjs`.

Verified commands/results on 2026-10-17:
- `node --test tests/intake-race.test.mjs tests/appearance-adapter.test.mjs`: **15/15 PASS**. Log: `review_working/evidence/intake-appearance-adapter-tests.log`.
- `node --test tests/*.test.mjs`: **62/62 PASS** at this working-copy snapshot, including the original v5 assertions and the parent's concurrent pure-model tests. Log: `review_working/evidence/recovered-working-tests-after-adapters.log`.

The 62 passing tests are Node/minimal-DOM evidence only. They do not prove real browser focus, layout, native media/wallpaper decoding, touch, assistive technology, native-platform acceptance, integrated product behavior or full 200+ requirement closure.
