# ROUND 14 — Wallpaper and local continuity — 2026-09-27

Base: `801adbf8cb0cd96312bd2bdc2b722cfc3fb53b39` (freshly fetched before work).
This is a bounded frontend implementation and local browser verification Batch.
**ROUND 14 remains REWORK; USER_VERIFIED, RELEASED and COMMERCIAL_READY are NO.**
The source, this evidence, validation receipt and CURRENT update travel in the
same mainline commit. Unrelated protected dirty paths are excluded.

## Task Cards, owners and disposition

| Card | Existing owner / bounded work | Disposition |
| --- | --- | --- |
| SYS05-PRESET-RESET | SYS-05 local appearance: bundle the two Product Owner photographs unchanged; existing wallpaper key and setter; serialize image changes/reset; explicit corrupt-store recovery | IMPLEMENTED / TESTED / bounded Web LIVE_VERIFIED |
| WALLPAPER-CONTRAST | Existing Theme/App: automatically solve the minimum light/dark scrim against the worst possible image region; cover body, secondary, primary-action and semantic status colors; avoid unreadable interpolated theme frames | IMPLEMENTED / TESTED / inspected on both real images, blur 0 and minimum panel opacity |
| AI01-LOCAL-CONTINUITY | AI-01 keeps local Open/Save/Copy and draft through loading, 401/403, offline/retry; removes stale remote snapshot | IMPLEMENTED / TESTED / local Web flow LIVE_VERIFIED; AI execution not accepted |
| RESPONSIVE-STATE | Existing Shell keeps same-screen/same-scope State across responsive reparenting; existing screen/context key still resets State on a real change | IMPLEMENTED / TESTED / desktop-to-phone Web draft preservation LIVE_VERIFIED |
| BMP02-LOCAL-RECOVERY | Existing BMP-02 full verified snapshot supplies role options, no-result filter clear and visible selection fallback | IMPLEMENTED / TESTED; business DESIGN_EXPLORATION/BLOCKED unchanged |
| ASYNC-READ-LIFETIME | Existing AI-01/BMP-01–11/SH-01 ViewModels ignore responses after disposal; generation guards where applicable | IMPLEMENTED / TESTED; no data, Permission or repository owner change |
| WEB-LOCAL-RENDERER | Existing Flutter bootstrap loads bundled CanvasKit; deployment guidance includes all build assets | IMPLEMENTED / TESTED / live browser with Google CDN blocked |

Bounded Luna workers stopped at their cards. Root inspected their diffs and
integrated independently verified repairs. No model routing, Windows user-level
environment, credentials, production DB or external provider configuration changed.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

- REAL USER JOB: choose a personal wallpaper, retain readable operations, continue
  editing a local task draft, and recover corrupt appearance preferences.
- ENTRY: actual `/workspace/SYS-05`, global appearance sheet and `/workspace/AI-01`.
- REAL INPUT: the two uploaded JPEGs, unchanged (182063 / 159638 bytes), and a
  deliberately typed multilingual 119-byte UTF-8 draft. The draft is a local file
  test input, not a business finding, provider result or Production Truth.
- END-TO-END PATH: preset selection → persisted original bytes → light/dark change
  at blur 0 and panel opacity 0.65 → close/reopen browser page → type/copy/download
  draft → change wallpaper → offline retry → real server 403 → reopen downloaded
  file → resize to 390 px → select preset on mobile → corrupt isolated local
  appearance keys → explicit reset → reopen → remove wallpaper.
- USER-VISIBLE RESULT: both images remain selectable and restore correctly;
  theme-dependent protection preserves readable UI while retaining image color;
  exact draft bytes survive file round trip and in-screen recovery/resize;
  reset clears only the two local appearance keys and returns to frosted mode.
- FAILURE/RECOVERY: real offline and permission errors remain visible and analysis
  stays disabled; local drafting remains available. Corrupt preferences are not
  silently deleted. Controller tests additionally cover pending image/pref writes,
  partial reset failure, retry, bad image and storage failure.
- EVIDENCE: [machine receipt](ROUND-14-WALLPAPER-AND-LOCAL-CONTINUITY-2026-09-27.json)
  records exact file hashes/Git blobs, commands, exits and browser assertions.
  Local raw logs/screenshots: `C:/Users/private-user-121dcc385158/AppData/Local/Temp/lumenis-frontend-verification-801adbf8`.
- ACCEPTANCE ASSERTION: the above local user jobs pass the bounded automated and
  actual browser paths. This does not accept complete AI/BMP tasks or the Round.

## Verification and discovered failures

- Flutter 3.47.5 / Dart 3.13.4: **233 affected tests pass, exit 0**; full app
  `flutter analyze --no-pub` **exit 0**; release Web build with
  `--no-web-resources-cdn --no-wasm-dry-run` **exit 0**.
- Actual Chromium uses canonical Core source from an isolated base archive,
  disposable data and the safe no-scheduler workspace-context acceptance profile.
  Its generated Basic transport credential stays in memory; it is not an actor,
  product login or proof of business Permission. Protected routes still reject.
- Browser verifies the served `main.dart.js` hash against the current build,
  original JPEG hashes in local persistence, actual clipboard text, downloaded
  UTF-8 bytes and reopening that file. No intercepted business-success response,
  mock data, fixture response or external collection is used.
- Original live review exposed wallpaper contrast failures. Independent review
  found missing primary-button coverage and low-contrast theme-transition colors;
  both were repaired and tested across nine extreme color regions and all active
  text/accent/domain/status roles in light/dark palettes.
- Actual browser resizing exposed loss of the local draft. The Shell now keeps
  its screen host through layout changes. Regression also proves real screen and
  confirmed context changes create fresh screen State, preserving scope isolation.
- Early test-driver failures (Flutter real/fake async, off-screen widget taps,
  semantics focus transfer) were corrected without weakening byte/state assertions.
  Failed runs are not counted as current PASS.
- Constitution, Experience authority, strict anti-template, screen blueprints and
  single-product gates passed on the immutable candidate. The base commit's
  takeover gate reported its missing same-commit CURRENT update; this delivery
  includes CURRENT and the unchanged validator must pass on the new commit before
  publication. No gate is bypassed or made advisory.

## GLOBAL UNIVERSE / DATA MATURITY IMPACT

No collection or domain focus is triggered by these local operations. Global
Commercial Coverage = NO / NOT VERIFIED; Global Brand Coverage = NO / NOT
VERIFIED; Guangzhou Taikoo Hui Reference Coverage = NO / NOT VERIFIED.
RANDOM ENTITY DATA ACCEPTANCE sample count = 0: this local-only Batch has no
actor-bound entity sampling result. No generated or fixture entity is counted.
LUMENIS_INTERNAL_FULL_UNIVERSE_READY = NO.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

Accessed 2026-09-27; installed Flutter 3.47.5, BSD-3-Clause; maintained official
SDK/documentation. No package upgrade or new product/runtime dependency.

| Source | Decision and exact owner mapping |
| --- | --- |
| [ChangeNotifier.dispose](https://api.flutter.dev/flutter/foundation/ChangeNotifier/dispose.html) | ADAPT existing ViewModel lifecycle; ignore late callbacks and keep canonical repositories |
| [WidgetTester.runAsync](https://api.flutter.dev/flutter/flutter_test/WidgetTester/runAsync.html) | ADAPT test host for actual asset/prefs futures; preserve reset and exact-byte assertions |
| [Flutter Web initialization](https://docs.flutter.dev/platform-integration/web/initialization) | ADAPT documented loader configuration in the existing bootstrap to bundled CanvasKit; no alternate frontend |

The source-owner locator was used narrowly for wallpaper, AI-01 and BMP-02;
linked current rules were present, and historical-research candidate count was
zero in that bounded search (not a claim that no historical work exists).
Current screen contracts and the sole Experience Constitution govern the repair.

## COMMERCIAL OVERLAY IMPACT and remaining boundaries

No business data, Evidence, Permission, DB, AI execution or release authority is
added. The account/session binding gap remains for the appropriate existing owner.
Native Windows/macOS/Linux/Android/iOS picker/material/user-flow evidence remains
LIVE_NOT_VERIFIED. Browser profile reopening is not a native application restart.
The isolated Core's Basic challenge is not accepted as a pre-beta account entry
experience. This Batch is not full-product frontend completion, user sign-off,
production operation or commercial readiness. Preserve the ordered 15 checkpoints.
