# ROUND 14 — Honest unavailable browser entry and task return

Batch: `R14-BROWSER-ENTRY-TRUTH`, 2026-09-27. Integration base:
`3ccc8307c3cfea8e2f4a2d983590350451e65905`. Scope is the existing Flutter host
navigation owner and the reviewed ACC-03 DESIGN_READY recovery contract.
SYS-06 remains DESIGN_EXPLORATION and is not mounted as an operable viewport.

## Defect and accepted change

The previous route always told users that browsing required Desktop, including
when reached on desktop. No target had an operable SYS-06 page. The host now says
that browsing is unavailable and lets users return to their original task.
Entering this one unavailable destination pushes the existing route; returning
pops it. Normal workspace navigation is unchanged. Direct links without an
origin return to the workspace root. Unknown routes keep their separate message.
The explanation and Return scroll at narrow height and enlarged text.

Three language dictionaries and their generated copy were updated together.
Shell markers now communicate unavailable information instead of desktop support.
No Browser API, permission, Actor/session, Evidence or engine effect is added.

## Task Card / ownership

- Entry dependency: ACC-03 host navigation is DESIGN_READY; the bounded review
  is appended to that contract. It does not promote SYS-06.
- Allowed: router, route registry, shell markers, copy, router tests, ACC-03 and
  SYS-06 contract reconciliation, this evidence and CURRENT publication.
- Forbidden: backend, production DB, identity bootstrap, browser engine, model
  configuration, personal XHS, unsupported viewport mounting, unrelated dirty work.
- Delegation: GPT-6 Luna implemented only the three router/registry/test paths;
  main controller reviewed the diff, corrected one test's route observation and
  performed integration, tests, live acceptance and publication. Other candidates
  in the shared worktree were not accepted or staged.

## Verification of the frozen candidate

- `flutter test --no-pub test/navigation/lumenis_router_test.dart`: 15 passed,
  exit 0.
- `flutter test --no-pub test/navigation test/shell test/l10n test/features/system/sys05_appearance_test.dart`:
  56 passed, exit 0.
- `dart analyze --fatal-infos`: no issues, exit 0.
- `flutter build web --no-pub --release --no-web-resources-cdn --no-wasm-dry-run`:
  release build exit 0, 76.7 seconds, in the isolated runtime archive.
- Six existing gates passed: AI-native constitution, exclusive Experience,
  strict anti-template, screen blueprints, single product and takeover governance.
- Final actual Chromium Web acceptance: 8 assertions, exit 0, zero page errors
  and zero Browser API requests. The served JavaScript matched the built bytes.

Earlier failing runs are not PASS. The final navigation test reads the displayed
route's GoRouterState: go_router 18.0.1 deliberately leaves the underlying
RouteMatchList URI at SYS-05 during imperative push. All visible-page, exact-input,
focus, non-mounting and narrow-text assertions remain. No global URL option was
changed. A live driver initially clicked a horizontally clipped mobile choice;
the final driver scrolls the real choice row and verifies its checked state
before typing. No product state or storage was injected for this flow.

The 206 App lib/web/assets/manifest files in the runtime archive match canonical
content after CRLF normalization. Ten exact candidate hashes, normalized Git
blobs, build/screenshot hashes and commands are recorded in the sibling JSON.
Backend runtime is the existing loopback-only disposable profile at
`15a994bbf172a783b9b8dd2bf8a8d43359829fec`, not the current Browser backend.
This is appropriate for the local navigation-only job and proves no backend
browser integration. No production DB, scheduler or social identity was used.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

- REAL USER JOB: inspect an unavailable destination and resume appearance editing
  without losing an in-progress local input.
- ENTRY: actual SYS-05 page and existing shell navigation.
- REAL INPUT: type the deliberately unapplied local color text `A1F`.
- END-TO-END PATH: choose custom color → type input → existing Internal Browser
  entry → truthful unavailable message → Return → exact original input. Repeat
  with the browser Back control, at 1440 px and 390 px. A direct SYS-06 link at
  320 × 360 px also returns to the existing workspace root.
- USER-VISIBLE RESULT: the same task and exact uncommitted input; no color
  application, browser capability or permission success is fabricated.
- FAILURE/RECOVERY: unsupported entry, unknown route and no-origin direct link
  retain honest distinct states. Widget acceptance covers 320 px/200% text and
  preserved input focus. Browser checks exercise rendered controls and real text.
- EVIDENCE: final 56-test regression, 8 live assertions and inspectable screenshots
  under `C:/Users/28049/AppData/Local/Temp/lumenis-browser-entry-20260927`.
- ACCEPTANCE ASSERTION: bounded Web recovery is LIVE_VERIFIED; user sign-off,
  native Windows/macOS/Linux/Android/iOS and full SYS-06 work are NOT VERIFIED.
  This batch is not Round 14 PASS or all-frontend completion.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

Accessed 2026-09-27: official
[go_router Navigation topic](https://pub.dev/documentation/go_router/latest/topics/Navigation-topic.html),
version 18.0.1, and the installed matching package source (BSD-3-Clause, Flutter
team maintained). ADAPT its existing push/pop state-preservation behavior for
this host boundary. Preserve normal go-based navigation and the default URL
reflection option. No dependency upgrade, copied visual design or second owner.
The bounded independent Luna read-only review confirmed the local implementation
of imperative match URI and GoRouterState before final acceptance.

## GLOBAL UNIVERSE / DATA MATURITY IMPACT

GLOBAL/ALL and focus semantics are unchanged. Global Commercial Coverage =
NO / NOT VERIFIED; Global Brand Coverage = NO / NOT VERIFIED; Guangzhou Taikoo
Hui Reference Coverage = NOT REVERIFIED by this batch. RANDOM ENTITY DATA
ACCEPTANCE sample count = 0: this local appearance/navigation job consumes no
entity corpus and makes no entity-data claim. It does not close any coverage gap.
`LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`.

## COMMERCIAL OVERLAY IMPACT / remaining work

Full SYS-06 still needs approved screen promotion, real product Actor entry,
authorized target/revision/frame binding, failure recovery and user work E2E.
Backend transport credentials are not a product Actor. No global account wall
is introduced. Four-surface business continuity remains a separate acceptance.
`ROUND_14=REWORK`, `USER_VERIFIED=NO`, `RELEASED=NO`, `OPERATING=NO`,
`COMMERCIAL_READY=NO`. Hosted CI remains the separately recorded quota blocker;
local gates do not claim hosted execution. Rollback is a scoped revert of this
batch through mainline; no data migration is involved.
