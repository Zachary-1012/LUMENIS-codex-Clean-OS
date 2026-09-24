# Frontend reference adaptation — 2026-09-24

Status: implementation candidate; this inventory is not whole-product acceptance.
Owner: existing Flutter Experience / SYS-05 settings / Public Website. Existing
44 route IDs preserve capability and deep links, not a fixed page-count target.

## Input coverage and method

The Product Owner supplied desktop creation screenshots, mobile optical/voice
screenshots, five MP4 files and five XHS links. Only the named local files were
read. No private message or notification in the screen recordings is product
content. Recordings and extracted images remain outside the Git repository.

The two newest clips were decoded sequentially with PyAV 18.1.0, a development
tool installed only in the task artifact directory, not a product dependency:

| File | Duration | Decoded frames | Dimensions | SHA-256 |
| --- | --- | --- | --- | --- |
| f17b987d8584bb13b649187a9f5652f3.mp4 | 37.733 s | 1,133 | 1280 × 704 | 3b65034ddf198b0d458df45861204abcb15babd5771e981b4afc46bd7e257bfd |
| 3e1067660c7223875e207df7661645e5.mp4 | 154.308 s | 4,477 | 448 × 960 | 5a24c4910b08e7432ea154be1d33e0c8aa8d777a5033565967844b09c01dcdd3 |

Every decoded frame has a timestamp and adjacent-frame change measurement.
The complete timeline was visually inspected using two-second storyboards;
one-second and abrupt-change frames were retained. Eight selected transition
ranges were additionally inspected at every decoded frame (192 frames total).
This is not a claim that all 5,610 frames were manually inspected one by one.
The earlier three MP4s have four sampled frames each; that earlier sampling
does not establish exhaustive frame coverage.

## Specific observation → product placement

| Reference / time | Observed interaction | LUMENIS placement and current boundary |
| --- | --- | --- |
| Fish desktop screenshots | Project rail, script segments, selected section, inspector, audio area | BMP-08 now has desktop three-pane script work and mobile task tabs. Local text edits are local drafts. Without real audio, the track stays explicitly empty. |
| Nextly mobile screenshots | Large focused question, soft optical depth, capsule choices, secondary disclosure | AI-01 task entry uses the existing intention owner; system/configuration language is reduced. Context and model availability remain inspectable. Submission cannot pretend a missing backend succeeded. |
| Monochrome voice screenshots | Environmental blur, centered task, contextual waveform controls | SYS-05 backdrop/mode controls and focused task presentation. Actual recording/playback still requires its existing audio capability; decorative waveforms are not audio evidence. |
| Earlier portfolio/gallery/Flip+Zoom clips | Free exploration, focused item, preserved return path, neighboring controls | SH-02 space/list modes use existing verified source records and preserve the camera on detail return. No invented source cards or links in an empty library. |
| New clip 1, 0–7 s | Point field compacts into an object, then opens into an orbital arrangement | Public Website workflow exploration: optional orbital layout, readable central focus, accessible linear alternative. This is labelled product explanation, not live business data. |
| New clip 1, 7–35 s | Circular arrangement straightens into a depth track; current object stays near a fixed focus while metadata remains stable | Public Website focus/return and SH-02 selected material hierarchy. Continuous scroll/depth effects belong to exploration, never to moving editable rows or risk values. |
| New clip 2, 2–34 s | Black presentation with project image expansions and alternating text/image depth | Public Website progressive chapters and focused explanation. This does not force a black operational workspace. |
| New clip 2, 36–39 s | Compact blue/black product presentation, restrained feature hierarchy | Hierarchy and short hover/reveal transitions; no copied feature claims. The short recording fragment does not establish the full source site's behavior. |
| New clip 2, 40–47 s | White mobile book collection, cover depth, fast collection transition | SH-02 item identity and collection/focus/return hierarchy; only actual source data may fill the collection. |
| New clip 2, 52–64 s | Warm white narrative, blue/orange optical object, staged explanation and dark closing section | Public Website optical material and chapter transitions. Third-party statistics and brand marks are not copied. |
| New clip 2, 68–94 s | Floating project field, centered selection, reversible right menu drawer | SH-02 navigable space and contextual detail; Public Website exploration uses an explicit return path and keyboard operation. |
| New clip 2, 98–124 s | Room background, translucent floating tools, focused prompt, nearby contextual responses | SYS-05 local wallpaper/system material; AI task focus and contextual controls. Weather/map/café results in the clip do not authorize new product features or fake results. |
| New clip 2, 144–154 s | Searchable visual index, landscape preview, focused object controls | Material discovery and preview/detail composition; LUMENIS is not turned into a template marketplace. |

The social search-result scrolling between these clips shows thumbnails, not
complete interactions. Thumbnail-only works remain observation-only until their
full behavior is available. All referenced styles have a named placement; this
table does not assert every final composition has passed user review.

## Five XHS links

Anonymous access to the five supplied short links redirected to login. The
Product Owner authorized using the approved Hong Kong collection identity.
Current configured allowlist exists, but the named/default HK Cookie file and
HK profile location were unavailable during inspection. Collection therefore
remains AUTH_UNAVAILABLE for these five full notes. The Mainland personal
account was not accessed. Do not mark these notes as read or substitute their
titles for source observation. This gap does not stop local-reference UI work.

## Reuse, versions and license boundary

| Component | Version resolved | License checked in installed source | Use |
| --- | --- | --- | --- |
| Flutter Material / InteractiveViewer | Flutter 3.47.5 | Flutter SDK license | Theme, accessible widgets, source-space pan/zoom; no second renderer |
| file_selector | 1.1.0 | BSD-3-Clause | User-initiated local wallpaper file selection |
| shared_preferences | 2.5.5 | BSD-3-Clause | SYS-05 device preferences only; no business database |
| flutter_acrylic | 1.1.4 | MIT | Windows system material adapter |
| macos_window_utils | 1.9.1 | MIT | Awaited macOS material calls and native host compatibility |

Primary sources checked 2026-09-24: [Flutter ThemeData](https://api.flutter.dev/flutter/material/ThemeData-class.html),
[file_selector](https://pub.dev/packages/file_selector/versions/1.1.0),
[shared_preferences](https://pub.dev/packages/shared_preferences/versions/2.5.5),
[flutter_acrylic](https://pub.dev/packages/flutter_acrylic/versions/1.1.4),
[macos_window_utils](https://pub.dev/packages/macos_window_utils/versions/1.9.1),
[PyAV](https://github.com/PyAV-Org/PyAV).
Decision: ADAPT through current owners. Matching source code for the pictured
Fish/Nextly interfaces is unverified; no purported matching repository or
model license is treated as a UI source license.

## Acceptance still required

Current-snapshot Dart/static checks, affected widget regression, actual browser
appearance changes/reload/draft preservation, responsive visual inspection,
and native Windows material/build evidence are tracked separately. No macOS,
Android or iOS runtime is available on this Windows host. Business workflow
E2E, all fifteen ordered checkpoints, Product Owner review and release approval
remain separate. COMMERCIAL_READY=NO.

This is the initial gate inventory. The bounded checks completed later in this
delivery cycle are recorded below; untested platform/business gates remain open.

## Additional GPT/Codex typography recording

Input: `20260924-0428-28.8331232.mp4`, 1906 × 1018, 36.0 seconds,
1,156 decoded frames; SHA-256
`0227d772ab1d13d4c9a115a315e2622c41b89a779df5ca78955a861ac72bef2f`.
Thirteen three-second storyboard frames were inspected, including original-size
frames at 0, 18 and 36 seconds. This was a focused typography/settings review,
not a claim of manually inspecting every frame. The source shows an appearance
settings page with theme thumbnails, aligned label/control rows, font options,
reduced motion and a 14 px UI base-size preference.

ADAPT: restrained heading/body/caption hierarchy; comfortable CJK body leading;
readable navigation and secondary copy; a local base-font control and typography
preview under the existing SYS-05 owner. Preserve OS accessibility scaling and
local draft state. Do not copy unrelated account settings, the code comparison
example, branded theme names or private sidebar content into the product.
The recording and extracted frames remain outside Git.

## Bounded frontend integration review — 2026-09-24

Base before publication: fetched local `main`, `origin/main` and live remote
`refs/heads/main` matched `9e8331ddeb3500a758b20638127fbc8afb2aec1a`.
The containing commit is the source/status checkpoint; resolve its SHA live.
The implementation scope is Flutter presentation, its Web/native adapters,
local appearance, trilingual copy and Public Website presentation. Previously
local route/repository/view-model candidates are included so the frontend source
is coherent online. Their inclusion is not business-workflow acceptance.
Backend candidates, credentials, production data, CI workflow changes and
workstation configuration remain outside this commit.

### REAL DELIVERY CARD / 真实用户工作闭环验收

- REAL USER JOB: make an active workspace comfortable to read and personal to
  the device without losing the work being edited.
- ENTRY: the actual `/workspace/AI-01` shell appearance button.
- REAL INPUT: a typed, unsent business-question draft and a Product Owner-supplied
  local JPEG used temporarily as a wallpaper. It is not a business record or
  bundled product asset.
- END-TO-END PATH: shell -> SYS-05 -> local preference owner -> rendered theme,
  typography and image -> local persistence -> browser reload -> restore ->
  remove wallpaper -> return to the same workspace.
- USER-VISIBLE RESULT: the current browser rendered pure black, frosted and a
  chosen blurred wallpaper; the local font base changed 14 -> 15 -> 18 -> 14 px;
  keyboard slider changes worked. The typed draft survived theme, font and
  reduced-motion changes and modal dismissal. Wallpaper, font size and reduced
  motion restored after reload; wallpaper removal returned to frosted mode.
  Reloading the page deliberately clears the unsaved AI draft, as its copy says.
- FAILURE/RECOVERY: Web disables native desktop material and explains wallpaper
  as the available alternative. Invalid images, local persistence failures and
  native failures have distinct tested states. API context was unavailable and
  AI submission stayed disabled; no analysis result was invented.
- EVIDENCE: root-operated in-app browser tab 7 on the isolated local preview,
  screenshots and accessibility observations in the task transcript; source
  and logs under the task's `lumenis-design-review/frontend-runtime/` artifact
  directory. Preview used a disposable migrated DB with no seeded business
  records. The guarded AI page is not a real AI business-job E2E.
- ACCEPTANCE ASSERTION: the bounded Web appearance job is exercised. Native
  visual effects, platform-wide screen-reader behavior and business workflows
  retain their own unclosed gates. This is not a ROUND 08 exit decision.

### Typography and state regressions found during verification

The browser exposed three concrete defects which were corrected: remote font
fallback left CJK glyphs missing; encoded-image `ImageDescriptor.width` was not
supported on Web; changing reduced motion changed the transition subtree and
remounted the editor. The corrected implementation bundles licensed Noto fonts,
validates image dimensions through the SDK codec callback, and retains the same
transition subtree while setting zero motion. Initial failed checks are retained
in local artifacts; only the subsequent passing checks support this candidate.

The actual 390 x 844 browser viewport rendered the workspace and scrollable
appearance editor at the maximum 18 px preference without visible overflow.
Chinese, English and Korean rendering was inspected and the document language
changed to `zh-CN`, `en` and `ko` respectively. Native phone runtime remains
unverified. Arbitrary wallpapers/opacity settings are not universally certified
for contrast; semantic dark/light palette tests cover the specified solid
surface roles, including raised surfaces.

### Asset freshness

The actual browser initially showed an older cached build. The source-owned
Flutter bootstrap now omits deprecated service-worker registration, following
the installed Flutter 3.47.5 loader contract. Keep the SDK-generated worker
cleanup stub at the original deployed worker path for existing clients; it
unregisters only itself. No broad browser storage/registration deletion is
authorized or implemented. Official sources checked 2026-09-24:
[Flutter initialization](https://docs.flutter.dev/platform-integration/web/initialization)
and [Web FAQ](https://docs.flutter.dev/platform-integration/web/faq).

The canonical Flask Workspace host's non-hashed asset revalidation and `app.py`
host registration are separately owned, still local backend candidates at this
frontend base. The product controller has that explicit dependency. This source
publication alone does not make a clean-main Flask Workspace runnable. Temporary
cache/SW bypass on the review tab is verification setup, not the product fix.

### Remaining gates

- Backend `/api/settings/context` authorization/binding, trusted scope and
  actor-bound Evidence/AI execution remain under their current owners. Empty or
  blocked CTH/BMP/Shared pages are not business acceptance.
- Windows compilation is distinct from rendered native blur; macOS, Linux,
  Android and iOS runtime were not exercised in this review.
- Website examples remain explicitly fictional; unconfigured commercial entry
  links stay disabled. No public deployment or new commercial service was made.
- Five full XHS notes still have the authenticated-access gap above. Their
  titles were not substituted for content and the Mainland account was untouched.
- COMMERCIAL OVERLAY IMPACT: frontend readability and local preference recovery
  improve; `COMMERCIAL_READY=NO`, `RELEASED=NO`, `OPERATING=NO`.
- GLOBAL UNIVERSE / DATA MATURITY IMPACT: appearance does not change coverage.
  Global Commercial Coverage = `NO / NOT VERIFIED`; Global Brand Coverage =
  `NO / NOT VERIFIED`; Guangzhou Taikoo Hui Reference Coverage retains the
  existing `PARTIAL` checkpoint and is not re-verified by this UI review.
  `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable to local appearance; preview
  business sample count is zero. No generated entity data was introduced.
- CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: ADAPT references to
  existing Theme/SYS-05/AI-01/BMP-08/SH-02/Website owners; defer unavailable source
  notes and unverified native effects. No new Product Core or design authority.

### Final source checks and observed limits

| Check | Actual result | Scope / artifact |
| --- | --- | --- |
| `dart analyze lib test` | EXIT 0, no issues | `analyze-current-snapshot-final.log`; after final source/test edits |
| Full Flutter suite | EXIT 0, 314/314 | `all-widget-tests-final.log`; before final modal/slider semantics correction |
| Final affected regression | EXIT 0, 16/16 | `appearance-correction-pass.log`; SYS-05 persistence, trilingual slider labels/values/actions, keyboard size changes, palette/contrast, live modal dark theme, draft retention and mobile size |
| Web build | EXIT 0 | `web-build-current-snapshot.log`; Flutter 3.47.5, local Web engine assets, custom bootstrap |
| Windows build | EXIT 0 | `windows-build-current-snapshot.log`; same checkout via verified `L:` alias, preview Core URL 127.0.0.1:53764; compilation only |
| Experience authority / strict anti-template / blueprint-source validators | EXIT 0 each | Canonical authority, 191 Dart files, historical 44 route IDs and 54 binding rows; counts are contract coverage, not accepted screens |
| CURRENT governance validator | EXIT 0 | Contract v1.1.0 and source/status co-publication rule; rerun on published commit |
| Website tests/build | EXIT 0, 9/9 tests | Existing website scope; trilingual actual-browser review; no public deployment |
| Final modal Web inspection | PASS for bounded visual job | Near-opaque surface removed distracting underlay text; pure-black change updated the open modal; semantic tree contains named sliders with px/percent values |
| Ordinary browser refresh after final build | PASS | New typography and named sliders remained visible after normal reload; temporary cache/SW bypass was reset to false and mobile viewport override reset |

Protected production DB SHA-256 stayed
`a3eb3ef45ef877bbf93b303245248da1160bbd561473a83af71b2a326a4a0b45`.
No production persistence, account/cookie, Windows user-level model setting,
external publishing or new provider charge was performed by this frontend slice.
Failures in intermediate test construction were corrected and retained as
non-passing artifacts; they are not included in the passing totals above.

Root decision: accept publication of the bounded frontend integration candidate
and the specified Web appearance result. Broader business, native visual and
ROUND 08/09/14/15 exit acceptance remain open. Product Owner aesthetic review is
pending on the real preview. Deployment and full commercial readiness are not
implied by this source publication.
