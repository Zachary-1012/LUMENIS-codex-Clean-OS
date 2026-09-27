# ROUND 14 — Mobile workspace refinement — 2026-09-27

Integration base: `790303a6a130c7079118410baa1db3fbcf1aaf04` after fresh fetch. The frontend started at
`b20b658`; intervening Browser commits did not change these frontend paths.
**This bounded local Web Batch is verified; ROUND 14 remains REWORK.**
USER_VERIFIED, RELEASED, OPERATING and COMMERCIAL_READY are not claimed.

## Bounded Task Cards and source owners

| Card | Existing owner and adopted change | Scope |
| --- | --- | --- |
| PHONE-NAVIGATION | Shell: compact page/context header, workflow chooser, five domain entries, tools menu, fixed close | Same routes, context, Permission and State owner |
| MOBILE-AI-COMPOSER | AI-01: one writing surface, concise context reason, local draft controls adjacent to text, visible keyboard focus | Submission remains disabled without the existing prerequisites |
| MOBILE-APPEARANCE | SYS-05: rectangular photo presets, choose → preview → adjust, separated typography/density/motion | Existing preference controller and original photo bytes |
| ADAPTIVE-APPEARANCE-RETURN | Existing SYS-05 entry: right-side inspector on wide windows; phone sheet keeps originating page visible; title/close remain fixed during scrolling | Close/Escape returns to unchanged draft; no navigation replacement |
| ACC04-READ-LIFECYCLE | ACC-04 ViewModel ignores disposed/stale responses and refresh after disposal | Six scoped tests; no authorization semantics changed |

Three bounded Luna workers supplied candidates or independent checks. Root
reviewed each diff, integrated repairs and performed acceptance. Unknown dirty
backend files, production DB, credentials, Cookie/session stores, model routing
and Windows environment were excluded. No new architecture or product dependency.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

- REAL USER JOB: retain a local draft while changing workspace appearance,
  navigate work on a phone and return from settings without losing that draft.
- ENTRY: actual AI-01, SYS-05, phone page/tools sheets and global appearance entry.
- REAL INPUT: the two previously bundled original user photographs and a typed
  119-byte multilingual draft, reopened from its actual downloaded file.
- END-TO-END PATH: preset selection → minimum opacity/zero blur → light/dark →
  page reopen → write/copy/download → wide right-side appearance panel → close →
  offline/real 403 retry → reopen draft → resize to 390 px → page chooser → same
  page → tools/close → phone appearance → scroll → fixed close by touch → exact
  draft copy → SYS-05 through real navigation → preset → touch text-size control
  → 320 px large type → dark mode → corrupt local preferences → explicit reset
  → reopen → remove wallpaper.
- USER-VISIBLE RESULT: compact phone navigation leaves more room for work;
  repeated AI panels are removed; appearance can be adjusted while the originating
  task is visible, with an explicit stable close action. Original wallpaper bytes
  and exact draft bytes survive the checked paths.
- FAILURE/RECOVERY: real offline and denied reads remain errors; local draft
  actions remain usable. Corrupt local appearance requires explicit reset. No
  intercepted business success, fabricated entity, fixture response or AI output.
- EVIDENCE: [ROUND-14-MOBILE-WORKSPACE-REFINEMENT-2026-09-27.json](ROUND-14-MOBILE-WORKSPACE-REFINEMENT-2026-09-27.json), exact source SHA-256/Git blobs, commands,
  exits, 16 actual browser assertions and screenshot hashes.
- ACCEPTANCE ASSERTION: bounded local user jobs passed. This does not accept AI
  execution, domain workflows, product-account onboarding or the whole frontend.

## Verification and limits

- Flutter 3.47.5 / Dart 3.13.4: **125 affected tests, full app analysis and release
  Web build exit 0** at the recorded source. The six unchanged governance gates
  also exit 0; the new commit's co-publication gate must pass before push.
- Real Chromium checks the served build hash, local renderer with Google CDN
  blocked, original JPEG hashes, actual clipboard/download/reopen bytes, real
  HTTP 403 and offline recovery, narrow layout and visible close target. No page
  errors. A Flutter semantics proxy can show an empty DOM value despite a visible
  retained draft; mobile validation therefore checks the actual Copy result's
  exact bytes. Touch coordinates validate the fixed close control.
- Added regression covers 320 px, 200% text, safe insets, language callbacks,
  directory open/return and current-page draft preservation. Test-driver repairs
  used the new menu path, scrolled off-screen chips and synchronized virtual
  viewport metrics. Failed/older runs are not included as current PASS.
- Independent screenshot review found missing explicit close in navigation/tools
  sheets; fixed close was added and reverified. The final visual pass covers
  the desktop inspector, phone writing surface, phone settings layer before/after
  scrolling, tools/navigation and enlarged type. Impeccable detection returned
  no findings; it does not replace this runtime review.
- Core runs from an isolated published archive with disposable data and no
  scheduler. Its generated Basic transport credential stays in process memory,
  is not a product Actor, and does not prove business authorization. Later Browser
  backend commits are not exercised by this frontend-only acceptance profile.
- Native Windows/macOS/Linux/Android/iOS and real-device performance/assistive
  technology remain LIVE_NOT_VERIFIED; viewport testing is not native acceptance.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

The new user video was source-hash checked and sampled over its 47.367 seconds,
with 20 keyframes and transition comparisons. It depicts phone navigation and
settings. ADAPT grouped destinations, clear current state, persistent return and
readable controls through the existing Shell/SYS-05 owners. It contains no proof
of a desktop implementation; its account details, branding, OS settings and
unrelated product features are excluded. Raw reference frames stay local.

Official sources accessed 2026-09-27; installed Flutter remains unchanged,
BSD-3-Clause, maintained official project, no new commercial integration:

- [Flutter adaptive guidance](https://docs.flutter.dev/ui/adaptive-responsive/general):
  ADAPT window-specific compositions over retained State.
- [NavigationBar](https://api.flutter.dev/flutter/material/NavigationBar-class.html):
  ADAPT existing accessible destination control, restrained indicator/density.
- [Flutter license](https://github.com/flutter/flutter/blob/stable/LICENSE):
  existing framework reuse, no copied reference-app assets or additional package.

## GLOBAL UNIVERSE / DATA MATURITY IMPACT

These local operations do not collect or mutate entity truth. Global Commercial
Coverage, Global Brand Coverage and Guangzhou Taikoo Hui Reference Coverage =
NO / NOT VERIFIED by this Batch. RANDOM ENTITY DATA ACCEPTANCE sample count 0:
no actor-bound entity sampling result is available here. Full-universe readiness
remains NO; no placeholder or generated value is counted.

## COMMERCIAL OVERLAY IMPACT / publication

The existing 15 checkpoints and canonical owners remain. This bounded source,
receipt and CURRENT update co-publish on main. Browser SYS-06 remains an independent
DESIGN_EXPLORATION/API-contract gap, not a shipped viewport. Protected local
candidates remain unaccepted. Production release and the user's visual approval
are still outstanding.
