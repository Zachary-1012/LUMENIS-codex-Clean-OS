# SH-01 saved-work continuation — frontend F, 2026-10-02

## Bounded Task Card

- REAL USER JOB: import selected local media, edit a sequence, export a real
  editable result, leave, find/reopen it in the same business scope, then revise
  and export a new version while retaining the first version.
- ENTRY: existing SH-01 catalog -> media workbench. Direct GLOBAL entry asks
  for an explicit CTH/BMP use; the previous screen does not imply that use.
- REAL INPUT: W4 development-authored `scene-01.mp4` and `scene-02.mp4`, as pinned
  in `work/w4-creation-20261002/f-media-handoff/inventory-v1.json`. No external
  imagery, participant voice or music is involved. Canonical rights remain
  unknown/demo; this is an engineering media chain, not C4 creative acceptance.
- PATH: existing Source Import / exact-byte confirmation -> fresh reference
  inspection -> manual Timeline -> Artifact export -> media / ZIP -> same-scope
  saved-project listing or retained reference -> fresh source inspection -> edit.
- USER-VISIBLE RESULT: a playable export and editable saved version, with a
  discoverable reopening path. The current backend has no project-name field;
  `W4-F-SH01-Harbour-20261002-A` is an evidence label only.
- FAILURE/RECOVERY: malformed input, unavailable/denied/partial list, pagination,
  stale context, read failure retaining the current draft, and return/reopen.
- ACCEPTANCE ASSERTION: actual registered source and output IDs, submitted versus
  returned Timeline, playable measured movie, downloaded package, fresh reopen,
  parent-linked revision and preserved first version. Tests alone do not pass it.
- COMMERCIAL OVERLAY: no publication, rights approval, training admission,
  owned-AI result, whole-video/podcast/pitch outcome or commercial acceptance.
- GLOBAL UNIVERSE / DATA MATURITY: no registry coverage is inferred from two
  media inputs. Global commercial/brand and reference coverage are unchanged.

M approved this increment under existing SH-01 sections 10.3/10.5: true saved
listing in the existing version flow plus reference fallback, fresh scope reads,
three languages/mobile layers, and the existing leave guard. F owns App changes;
W6 owns contracts, formal write-slot coordination, runtime refresh and publication.

## Current source and implementation

SourceBrief was separately accepted and published at
`d73e807c0a786b24cab78c0a5b8d4e1e3962fc6f` before CoreClient gained its read-only
listing method. The accepted SourceBrief methods were not changed. W6 verified
the existing listing/detail Core routes equal main and observed a real GLOBAL
CTH list response. F did not create a new API, Artifact owner or persistent store.

The candidate implements:

- Real scoped `GET /api/experience/content-projects`, bounded opaque pagination,
  explicit incomplete/error states, and exact returned record timestamps. Current
  backend timestamps have no timezone; the UI does not invent one.
- A saved-work dialog that selects actual returned IDs, with manual reference
  fallback; exported work exposes its reusable reference.
- Reopen stages the candidate Timeline/version until all source checks succeed.
  A read failure retains the old draft, undo, source references and selection.
- Scope invalidation clears list output. Dialog notifications run after the frame,
  fixing a reproduced `markNeedsBuild during build` failure without changing the
  Permission or leave boundary.
- Chinese/English/Korean copy through the existing canonical delta/generator.

The original nine source/test fingerprints are recorded in
`work/frontend-2026-10-02/sh01-source-hashes.json`; the frozen v3 set adds the
Web player lifecycle owner, for ten files in `sh01-v3-source-hashes.json`.

## Automated evidence and current limits

SDK: Flutter 3.47.5 / Dart 3.13.4, existing workstation SDK. No dependency update.
Direct Dart analysis with fatal infos passed on CoreClient, SH-01, generated copy
and affected tests. The Constitution and all three Experience blocking validators
passed. `git diff --check` passed for the App and locale deltas.

The coherent scoped run initially had 101 passing tests and one failed locale
registry check: generated/delta key count was 778 while the registry still held
763. W6 owns its correction; this failure is retained in
`work/frontend-2026-10-02/sh01-final-tests.log` and is not rewritten as PASS.
W6 corrected the locale registry from 763 to 778 without altering the test.
Its three localization tests then passed (exit 0; `sh01-l10n-repair.log`).
Independent review found one further available-to-available scope transition
that did not refresh an already loaded dialog. The workbench now compares the
current scope fingerprint on widget updates and invalidates the dialog after
the frame. Its final 31 widget tests passed (exit 0;
`sh01-workbench-final.log`), including both loaded-dialog scope transitions.
Final analysis of those changed files passed with fatal infos (exit 0).

The first independent build succeeded but was superseded during the late scope
repair: `app/build/media-reopen-preview` is WITHDRAWN and must not be served.
The new candidate uses `app/build/media-reopen-preview-v2`. The existing served
SourceBrief build remains untouched. The v2 JS release omits the optional Wasm
dry run; no Wasm surface is claimed or required by this candidate.

V2 build exited 0 using `flutter build web --release --no-web-resources-cdn
--no-pub --no-wasm-dry-run --output build/media-reopen-preview-v2`.
Its served-JS candidate hash is
`477efedd2cdeb5f8c0749a074a9d02f37dd90d9d34c3d94268275c17810af406`;
full build hashes are `work/frontend-2026-10-02/sh01-build-v2-hashes.json`.
The four blocking gates were rerun after the final scope repair and passed.

W6 selected v2 in a controlled restart and verified its actual HTTP asset hashes.
The following real browser chain then ran through the existing Product Core.
F has returned the formal write slot; subsequent preview repair checks reuse
these saved artifacts without another import or export.

## Real media continuation evidence

Both source imports first returned the required exact-byte confirmation, then
created `ART-8be9b0e5e0754f60` and `ART-32a50a39e63d4d34` with recorded Evidence.
The editor used real source intervals 1–9 and 1–13 seconds, placed at 0 and 8.
Its first 9:16 export is `ART-2c34889ece5a43aa` (Timeline v4; execution
`b82682e792fc454e`). The actual video played in the browser. The ZIP's timeline
matches the submitted and returned timeline; pinned FFprobe measured 20 seconds,
600 frames, 720×1280, H.264 at 30 fps, with no audio.

Leaving and reopening through the real CTH saved-work list restored that result
after fresh source inspection. Changing only the second source end to 12 seconds
produced `ART-187bb52b61444904` (Timeline v5; execution `a7bbc43463e84a1d`),
with parent `ART-2c34889ece5a43aa`. Its actual file is 19 seconds / 570 frames.
Reopening the first version restored its original 20 seconds and source end 13;
the previous version was preserved. BMP listing did not reveal the CTH results,
and entering the CTH reference under BMP returned HTTP 403 with
`CONTENT_PROJECT_CONTEXT_MISMATCH`. Returning to explicit CTH reopened v5.

Chrome's actual UI download saved `ART-187bb52b61444904.zip` to Downloads at
2026-10-02 11:16:34 +08:00: 44,511 bytes, SHA-256
`a1a88fe22c1ef8cbd67be2dfed01332153aeb2cac1f80ff864b4149162a23fa7`.
The physical downloaded file passed 35 package/timeline/media comparisons.
The automation download-event wait timed out despite this real file save.
The in-app browser returned the correct package bytes but did not provide a
verified file save: IAB save remains NOT VERIFIED, distinct from Chrome.

Evidence under `work/frontend-2026-10-02/`:

- `sh01-first-export.json`, `sh01-revision-export.json`: actual request/result.
- `sh01-first-reopen.json`, `sh01-scope-denied.json`: listing/detail/inspection
  and denied cross-scope result.
- `sh01-chrome-download-receipt.json`: actual filesystem download receipt.
- `sh01-output-verification/verify-sh01-fkef3s3h/comparison.json`: first ZIP,
  33 passed comparisons, exit 0.
- `sh01-output-verification/verify-sh01-ygzwerq8/comparison.json`: physical
  Chrome revision download, 35 passed comparisons, exit 0.

An earlier comparison rejected numerically identical JSON values (`10` and
`10.0`); that failed helper report remains preserved. The corrected helper
compares canonical numeric values and does not rewrite any product output.

## Preview interaction repair candidate

Real v2 operation exposed three bounded usability defects: preview loaded above
the desktop viewport, the mobile actions sheet remained over the preview, and
native HTML video interfered visually with the saved-work dialog. The candidate
reveals a freshly loaded preview after layout, closes only the requesting mobile
actions layer, and uses the existing saved-work loading text. Reduced motion
uses zero-duration reveal. Late or scope-mismatched responses remain rejected.

The Web player observes whether its enclosing route is current. A modal route
pauses and hides the same HTML element and disables its pointer handling;
returning restores visibility without autoplay, replacing its source, or losing
its playback position. V2 evidence above proves the unchanged data chain;
the actual v3 repair checks are recorded below. A mounted
and generation check also rejects late platform-view creation after disposal
or source replacement, before allocating an object URL. This race protection
was source-reviewed; a forced native-view timing race was not browser-reproduced.

The coherent v3 affected suite passed 107 tests (`sh01-v3-coherent-tests.log`).
After the final analyzer-only callback naming fix, all 35 workbench tests passed
again against the frozen source (`sh01-v3-frozen-workbench-tests.log`, exit 0).
Fatal-infos analysis passed for the workbench/test and Web preview owners.
Four blocking governance checks passed (`sh01-v3-gates.json`). Earlier failed
preview test attempts remain recorded: duplicate loading-label assertions,
incorrect test viewport bounds, and premature route-animation assertions were
resolved without weakening the user-visible result checks.

The independent v3 Web release build passed (exit 0, `sh01-v3-build.log`), with
all ten frozen source/test hashes unchanged before and after compilation.
`app/build/media-reopen-preview-v3/main.dart.js` is 4,765,448 bytes, SHA-256
`f22411a8ad604cc9bdb2dc1ebc34083f90640f546e557024fe2ec974e23b8a80`.
Full asset hashes are recorded in `sh01-v3-build-hashes.json`. W6 selected v3;
F independently read its actual HTTP JS hash and healthy/database-ok response
at 2026-10-02 03:55:19 UTC (`sh01-v3-actual-runtime.json`).

Actual v3 IAB checks reused saved v5 with no new import or export:

- At 390×844, preview closed the actions sheet and placed the 230px player
  wholly within y=173–403; `sh01-v3-mobile-preview.jpg`.
- Playback was running (`paused=false`, time 0.00856) immediately before opening
  the saved-work dialog. Covered state became paused, hidden and pointer-events
  none at 0.2008 seconds. Closing restored the same source URL and exact 0.2008
  position with `paused=true`; `sh01-v3-mobile-modal-lifecycle.json`.
- `sh01-v3-mobile-saved-list.jpg` shows the stable dialog without video bleed.
- At 1440×900, the footer preview action moved the player from y=-169 to
  y=106.88–406.88; duration remained 19 seconds and no media error occurred.
  `sh01-v3-desktop-reveal.json` and `sh01-v3-desktop-preview.jpg` retain evidence.
- Actual Chinese, English and Korean saved-work dialogs returned the same scoped
  real versions, translated labels and recovery controls; `sh01-v3-list-en.json`
  and `sh01-v3-list-ko.json`. Captured browser error log was empty.

Locale switching exposed one remaining Web-specific accessibility defect: the
already-created native player's aria-label retained its original language.
V4 updates the localized label in `didChangeDependencies`; all other nine
frozen files retain their v3 hashes. `sh01-v4-source-hashes.json` records the exact set.
Fatal-infos analysis, 38 affected workbench/localization tests and all four
blocking governance checks passed after this change. The initial analysis text
did not include an exit marker; `sh01-v4-analysis-confirmed.log` now records a
fresh fatal-infos analysis with no issues and explicit `EXIT_CODE=0`.

V4 built successfully (exit 0, `sh01-v4-build.log`) without changing its ten-file
source manifest. The final JS candidate is 4,765,553 bytes, SHA-256
`59e209e917eaa7276029787b7ddc51c502ef57a67a602d9025701f01bb47febd`.
The immutable directory is `app/build/media-reopen-preview-v4`; v2/v3 remain
available for rollback. Full fingerprints are `sh01-v4-build-hashes.json`.

W6 selected v4 through the existing runtime owner. F independently read the
actual `/workspace/main.dart.js` with HTTP 200 and the exact frozen hash/size;
`/healthz` also returned HTTP 200, healthy and database ok. The record includes
both URLs, statuses and capture time (2026-10-02 04:26:22 UTC) in
`sh01-v4-actual-runtime-confirmed.json`.

Actual v4 browser verification reopened saved v5 through the catalog, explicit
CTH use and saved-work list, then previewed its 19-second movie. On that same
native player, Chinese -> Korean -> English -> Chinese changed the aria-label
to `预览成片`, `결과 미리 보기`, `Preview export`, then `预览成片`, while the
same source URL, position, paused state and 19-second duration were preserved.
`sh01-v4-native-locale.json` records the actual DOM observations. Playing the
movie and opening the saved-work dialog changed it from playing to paused,
hidden and non-interactive at 0.207195 seconds; closing the dialog restored the
same source and exact position, visible and paused, with no media error.
`sh01-v4-modal-lifecycle.json` and `sh01-v4-desktop-preview.jpg` retain this
evidence. Captured browser errors were empty. No new import or export ran.
The product was restored to Chinese and temporary browser viewport overrides
were reset. The latest product, SourceBrief and website tabs remain available.

Independent read-only review matched all ten source/test hashes and all three
immutable build hashes/byte counts, and confirmed the pinned test/gate results.
The v3 107-test run is reused for the nine unchanged files; v4's actual native
DOM checks and 38 affected tests cover the final localized Web-player change.
These are bounded engineering results, not full-product acceptance.

Native installed platform acceptance, complete C4 creative/rights acceptance,
M acceptance, publication and Product Owner repeat operation remain separate.

## Acceptance ledger

| Requirement | Current evidence | State |
| --- | --- | --- |
| Explicit business use from GLOBAL | Actual CTH/BMP entry; widget coverage | VERIFIED for this media job |
| Real import and exact-byte approval | Two source artifacts and recorded Evidence | VERIFIED |
| Editable export and parent-linked revision | v4/v5 response, timeline/package equality, measured movies | VERIFIED |
| Saved list, fresh inspection, old version retained | Actual leave/reopen and original interval readback | VERIFIED |
| Cross-scope rejection | BMP list exclusion and explicit 403 | VERIFIED |
| Physical engineering-package download | Chrome file, SHA and 35 comparisons | VERIFIED in Chrome; IAB save NOT VERIFIED |
| Preview reveal and modal visibility | Actual v3 phone/desktop geometry, pause/hide/return and screenshots | VERIFIED for Web browser sizes |
| Native player language refresh | Actual v4 same-player Chinese/Korean/English/Chinese DOM and modal return | VERIFIED for Web |
| Three languages, 320 px and 200% text | Scoped widget suite | TESTED; installed native devices NOT VERIFIED |
| Complete C4 video/podcast/pitch outcome | This job contains only a procedural media editing result | NOT CLAIMED |
| Publication / Product Owner review / release | W6/M gates and human repeat remain | PENDING |

## Focused current research

Read on 2026-10-02; ADAPT existing lifecycle handling, no added dependency:

- [Flutter mounted](https://api.flutter.dev/flutter/widgets/BuildContext/mounted.html):
  check lifetime before applying asynchronous UI results.
- [ChangeNotifier disposal](https://api.flutter.dev/flutter/foundation/ChangeNotifier/dispose.html):
  owned controller disposal and rejection of late responses.
- [Post-frame callbacks](https://api.flutter.dev/flutter/scheduler/SchedulerBinding/addPostFrameCallback.html):
  defer dialog notification out of the current build phase; the exact failing
  quarantine reproduction passed after this bounded repair.
- [Official file_selector package](https://pub.dev/packages/file_selector):
  reuse the declared Flutter plugin and exact chosen bytes. Its platform support
  table does not establish installed-native runtime acceptance. BSD-3-Clause;
  existing dependency only, no upgrade or redistribution change in this batch.
- [Flutter ensureVisible](https://api.flutter.dev/flutter/widgets/Scrollable/ensureVisible.html):
  reveal the existing preview after its layout, with reduced-motion handling.
- [HTML platform views](https://api.flutter.dev/flutter/widgets/HtmlElementView-class.html)
  and [current modal route](https://api.flutter.dev/flutter/widgets/ModalRoute/isCurrentOf.html):
  adapt native media visibility and input handling while Flutter modal routes
  are active; keep the existing media element and object URL lifecycle.
- [Locked cross_file 0.3.5+5](https://pub.dev/packages/cross_file/versions/0.3.5%2B5):
  inspected its installed Web save helper and observed the actual download
  anchor. No premature URL revocation was present. Chrome's saved file verified
  the current path; no download-library replacement was justified.

External references describe implementation behavior, not product truth or a
new design authority. Observable failure, fresh scope checks and the old saved
version provide recovery; W6 retains the previous immutable preview build.
