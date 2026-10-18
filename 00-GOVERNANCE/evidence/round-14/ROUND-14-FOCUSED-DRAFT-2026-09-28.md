# ROUND 14 — Focused local draft editing

Status: `IMPLEMENTED / TESTED / bounded Web local-file job LIVE_VERIFIED`;
ROUND 14 remains REWORK. Native platforms and Product Owner acceptance remain open.

## Sol Task Card — R14-AI01-FOCUSED-DRAFT

Task entry base: `8d6e510309747607a2ce8e3253a02ce5119c05d9`.
Final isolated verification base: `291056e0487a556dfb8e412fda30a5f6e30a560f`.
Owner: existing Flutter AI-01 local draft/controller and existing file actions.
Specification: AI-01, Focused draft editing and Return, 2026-09-28.

Allowed implementation paths: `app/lib/features/ai01/ai01_screen.dart`,
the three `contracts/experience/i18n/{zh-CN,en,ko}.delta.json` canonical copy files,
their existing `copy-registry.json` key-count metadata,
generated `app/lib/l10n/lumenis_copy.g.dart`, and focused AI-01 tests under
`app/test/features/ai01/`. Generate via the existing copy tool; the localization
consumer is unchanged. Sol owns the specification, this evidence and CURRENT.
Forbidden: backend, Collector, Permission, DB, runtime/ports, global configuration,
draft file/actions owner changes, new dependencies, implicit persistence, API writes.
Preserve all unrelated dirty paths. One Luna executes this Batch, then stops for
Sol review; no staging, commits, push or next Batch by the worker.

Implement an explicitly entered modal editor over the same draft controller,
with keyboard-inset handling, localized Return, Escape/Back, reduced motion,
wallpaper-safe readable material and preserved source composer/file state.
Do not duplicate the file actions in the focused layer.

## REAL DELIVERY CARD — 真实用户工作闭环验收

REAL USER JOB: refine a task draft on a phone-sized view and retrieve exact text.
ENTRY: AI-01 local Open and expanded editing.
REAL INPUT: user-selected UTF-8 text file, then actual keyboard input.
END-TO-END PATH: Open -> expanded editor -> edit -> Return -> Save -> reopen.
USER-VISIBLE RESULT: exact updated text returned to the composer and file.
FAILURE/RECOVERY: remote denial/offline does not erase local input; Close/Escape/
Back preserve text; existing cancelled/malformed/replacement safeguards remain.
EVIDENCE: proportional current-source tests, actual browser file round-trip and
source/build hashes; native mobile E2E remains separate.
ACCEPTANCE ASSERTION: exact text and selection survive Return, no business write,
and no claim that local draft completion proves an AI execution or Round exit.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

ADAPT the content-first/reversible-disclosure principles already recorded in
Constitution §23; REUSE installed Flutter 3.47.5 Dialog/Focus/TextField APIs,
BSD-3-Clause. No new renderer, dependency or external asset is justified.
OpenCode/Zhipu was already unavailable for insufficient balance in the immediately
preceding Batch; no repeated provider call or configuration mutation is needed.

## GLOBAL UNIVERSE / DATA MATURITY IMPACT

No data/scope/coverage change. No random entity sample is appropriate to local
text editing. Global Commercial Coverage, Global Brand Coverage and Guangzhou
Taikoo Hui Reference Coverage are not accepted by this Batch.
LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO.

## COMMERCIAL OVERLAY IMPACT

Local draft delivery only. Real authorized AI execution, native device E2E,
USER_VERIFIED, RELEASED, OPERATING and COMMERCIAL_READY remain unaccepted.
Rollback is an exact bounded source inverse with no data migration.

## Sol implementation and review

Sol performed the screen and canonical-copy edit after reordering the original
worker to tests only. The bounded Luna worker returned three new regression tests;
Sol inspected the exact diff and replayed the integrated affected suite. A separate
read-only guard found no remaining concrete blocker in this slice.

The expanded editor shares the original controller, has its own disposable focus
node, and returns final text/selection to the original composer. The composer has
a stable screen-owned GlobalKey: crossing the 1100 px layout boundary otherwise
recreated its file-action State and could discard a pending file result. The new
1440 -> 390 -> 1440 regression preserves the same State while the modal is open.
The source file/actions owner, business submission, API and persistence are unchanged.

Three canonical locale deltas add four semantic keys each; the existing generator
produces the runtime copy. Registry counts are 665 per locale. The localization
consumer is unchanged. The editor retains reduced motion and opaque resolved-theme
material, with no new visual asset, dependency or continuous animation.

## Current-snapshot verification

The adjacent `.receipt.json` records all eight exact candidate hashes, the release
Web digest and the local job's assertions. Verification used an isolated archive:
206 app files matched published base plus this candidate (CRLF normalized only for
the archive comparison). Other protected dirty work was not copied into the build.

- `dart analyze --fatal-infos`: exit 0, no issues.
- `flutter test --no-pub --concurrency=1 --reporter expanded test/features/ai01
  test/l10n test/shell/lumenis_workspace_shell_test.dart
  test/navigation/lumenis_router_test.dart`: exit 0, 75 tests passed.
- `flutter build web --no-pub --release --no-web-resources-cdn
  --no-wasm-dry-run`: exit 0.
- Constitution, Experience authority, strict anti-template structure, blueprint
  bindings and Only-One architecture gates: exit 0. The takeover/co-publication
  validator is also required against the staged candidate and delivered commit.

The worker's first targeted test run failed because `pumpAndSettle` waited forever
while an intentionally unresolved remote read showed a loading animation. It was
replaced only at that transition by a finite frame wait; all content, recovery and
Return assertions remained. The corrected targeted run passed 14 tests, followed
by Sol's 75-test suite. The failed run is not PASS evidence.

Actual Chromium at 1440 and 390 px used real file chooser/upload/download behavior:
selected multilingual UTF-8 file -> expand -> keyboard edit -> Return -> exact Copy
-> Escape/Return -> cancel another file's replacement -> Save -> byte comparison
-> reload -> reopen the downloaded file. Both widths passed seven assertions each,
including equality of the served `main.dart.js` and the verified build. No request
was mocked; no API write or page error was observed. Real product authorization
remained unavailable on this isolated backend and was not bypassed.

The 200% text and keyboard-inset checks are widget evidence, not native-device E2E.
PC/mobile captures were visually inspected. The first mobile capture briefly showed
missing composite emoji glyphs. A separate 10-second capture rendered the glyph;
network evidence showed Flutter's external Noto Color Emoji fallback returning 200.
Exact Unicode text was preserved throughout. This identifies a pre-existing font
loading/offline coverage gap; it does not establish offline glyph readiness. No
font configuration or dependency was changed to disguise that limitation.

Local evidence directory:
`C:/Users/private-user-121dcc385158/AppData/Local/Temp/lumenis-focused-draft-20260928`.
Owned preview: `http://127.0.0.1:55826/workspace/AI-01`.
The backend stayed on isolated base `15a994bbf172a783b9b8dd2bf8a8d43359829fec`;
this is not full-current-backend acceptance. Formal runtime 53764, production DB,
Collector, Permission and workstation model settings were untouched.

## Acceptance boundary

Sol accepts this bounded local-text editing/delivery job. Full AI work, production
Actor/context, native E2E, offline emoji coverage, full frontend, ROUND 14 exit,
USER_VERIFIED, RELEASED, OPERATING and COMMERCIAL_READY remain unaccepted.
Online delivery applies after exact source/evidence/CURRENT co-publication and
live remote-ref verification. Hosted CI must be queried at the delivered SHA;
absence of a run is not a pass.

Pre-publication gate observation: the takeover validator initially failed because
another runtime archive under `data/private/runtime/prelaunch-baseline-8d6e510309747607a2ce8e3253a02ce5119c05d9`
contained a second machine-contract file. The archive owner was notified; this
Batch did not move/delete that runtime or weaken the validator. Publication must
wait for the owner to reconcile the physical duplicate and for the same validator
to return exit 0. This failed run is not acceptance evidence.
The archive owner corrected the deployment location; this Batch then reran the
unchanged takeover validator and observed exit 0 before staging. All six named
governance checks therefore passed on the reconciled candidate snapshot.
