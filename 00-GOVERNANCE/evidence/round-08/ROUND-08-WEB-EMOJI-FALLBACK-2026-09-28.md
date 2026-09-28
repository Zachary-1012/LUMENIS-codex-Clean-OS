# ROUND 08 — Web local glyph fallback

Status: `LOCAL_ONLY / IMPLEMENTED / SCOPED_TESTED / LOCAL_FILE_JOB_VERIFIED`.
Release Web build and sampled external-font-denied PC/phone workflow verified.
Mainline publication is coordinated with the primary controller; Round acceptance
and native-device/user acceptance remain open.

## Sol Task Card — R08-WEB-LOCAL-EMOJI

Entry base: `e61348f59c56e87e331b6f7b9ecb03c03e51507e` from fetched main.
Owner: existing Experience Theme, bundled fonts and asset manifest. These paths
were clean at entry; preserve every unrelated dirty path and the content team's
three-language/generated-copy work. No new font/theme owner or runtime is added.

Evidence: R14 focused draft actual browser showed composite emoji missing on an
early mobile capture, then visible after an external Noto Color Emoji request.
The UTF-8 file bytes were intact. This is a rendering dependency gap.

Allowed: `app/lib/core/lumenis_theme.dart`, `app/pubspec.yaml`, the unmodified
`app/assets/fonts/NotoColorEmoji.ttf` and its OFL notice, relevant font/theme tests.
Sol owns this evidence, the existing Constitution typography clarification and
CURRENT status. Forbidden: API/data/Permission/Collector, model/global settings,
existing CJK font replacement, unrelated UI layout, custom emoji substitution,
font subsetting/build tools, implicit cloud calls, silent removal of characters.

Final notice reconciliation adds the bundled font to the existing `main.dart`
LicenseRegistry list and records it in the canonical third-party register. This
one-line registration is included in the final R14 quiet-canvas six-file manifest,
analysis, 14 affected tests, release build and 12 actual browser assertions;
the earlier four-source-file emoji-only receipt remains a separate snapshot.

Presentation decision: append a bundled emoji font to the existing fallback list
on Web only. Preserve the existing SC/KR font order and native platform fallback.
This preserves user input; it does not add emoji decoration or a product feature.

## REAL DELIVERY CARD — 真实用户工作闭环验收

REAL USER JOB: open and revise multilingual local text containing composite emoji
when external font servers are unavailable, then save exact content.
ENTRY: existing AI-01 local file editing and expanded editor.
REAL INPUT: actual UTF-8 text file and keyboard edits; include ZWJ/skin-tone/flag.
END-TO-END PATH: reject external font requests -> open file -> display -> expand
and edit -> Return -> exact saved bytes -> reopen the downloaded file.
USER-VISIBLE RESULT: intact visible sample glyphs and exact downloadable draft.
FAILURE/RECOVERY: external font service denial must not remove text or block local
file actions. Unknown glyph coverage must not be reported as all-Unicode support.
EVIDENCE: source hashes, font metadata/license, analysis, affected tests, Web build,
actual browser network record and inspected PC/mobile captures. Native E2E stays
unaccepted; no native fallback change is intended by this slice.
ACCEPTANCE ASSERTION: the sampled emoji render from the bundled asset, with no
successful external font fetch, and the original Unicode text survives file return.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

Accessed 2026-09-28. Context7 resolved Flutter API docs but returned no matching
versioned query; exact installed Flutter 3.47.5 and official API are the fallback:
https://api.flutter.dev/flutter/painting/TextStyle/fontFamilyFallback.html .
The explicit fallback follows the primary font in order; preserve CJK typography.

ADAPT: official `googlefonts/noto-emoji`, commit
`e20cbc2bbec1926686be9f9bee7d1d2cfa1fea0e`, `2D/fonts/NotoColorEmoji.ttf`,
10,730,124 bytes, with `2D/fonts/LICENSE` (SIL OFL 1.1). Source:
https://github.com/googlefonts/noto-emoji/tree/e20cbc2bbec1926686be9f9bee7d1d2cfa1fea0e/2D/fonts .
Official README points to obsolete `gh-pages`/`fonts/LICENSE` paths; GitHub API
confirmed the actual current `2D/fonts` paths. Retain the unmodified upstream
font and license. This adds payload size; it removes the sampled glyphs' external
font dependency. Smaller COLRv1/font subsetting is DEFER pending separate format,
coverage and cross-surface evidence. No source/customer data leaves the device.
No hosted model, account, new package or paid service is required.

## GLOBAL UNIVERSE / DATA MATURITY IMPACT

No business data or canonical registry change. Random entity sampling is not
applicable to glyph rendering. Global Commercial Coverage, Global Brand Coverage,
Guangzhou Taikoo Hui Reference Coverage and internal full-universe readiness are
not accepted by this Batch.

## COMMERCIAL OVERLAY IMPACT

This slice cannot accept the full frontend, native devices, Round 08 or release.
USER_VERIFIED/RELEASED/OPERATING/COMMERCIAL_READY remain NO. Rollback removes only
the explicit Web fallback and new assets/manifest entry, with no data migration.

## Current candidate and verification

Luna modified only the Theme fallback and pubspec entries, then stopped; Sol owns
the unmodified upstream asset, license, Constitution clarification and verification.
The font's actual name metadata is `Noto Color Emoji`, version
`2.057;GOOG;noto-emoji:20260911:fc4ca365e7c20e78278ae702aa20434bfe704c8f`.
Its SFNT tables include CBDT/CBLC and GSUB. SHA256:
`15671215ab769fdc7162a045d56fd7d7e477c51b04e6b3c761d914d8fdd6cc44`.
OFL notice SHA256:
`6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2`.
The bundled SDK's older 2017 / version 1.39 test font was rejected because its
age does not justify assuming current composite-sequence coverage.

The isolated archive matched 208 app source/asset files against published base
`4ef4a0382cf51c69f0bb6ea3d5ca4538350b0353` plus this candidate. Exact five-file
hashes, font metadata and logs are retained in
`C:/Users/28049/AppData/Local/Temp/lumenis-web-emoji-20260928`.

- `dart analyze --fatal-infos`: exit 0, no issues.
- Serial existing Theme, AI-01, SYS-05 appearance and appearance-integration
  suite: exit 0, 57 tests passed. These run on the VM and do not prove the Web-only
  font branch, actual glyph rendering or a native-device E2E.
- Constitution and sole-Experience-authority checks: exit 0.
- Release Web build: exit 0, 215.1 seconds; bundled CanvasKit, no resource CDN.
- External-font-denied browser job: exit 0, ten checks across 1440 and 390 widths.
  The real selected UTF-8 file was opened, edited in the focused layer, returned,
  saved with exact bytes, and reopened from the actual browser download. Both
  served JavaScript hashes equaled the built artifact. No API writes/page errors.
- Four local emoji font responses were HTTP 200; no external emoji font request
  occurred. Other CJK fallback requests were attempted and denied, so this is
  not a claim of zero external font attempts or all-Unicode/offline coverage.
- Sol visually inspected both captures: sampled skin-tone/ZWJ/family/flag/plant/
  arrow glyphs were visible. Source/log/build/capture hashes and exact checks are
  retained in the adjacent `.receipt.json`.

Earlier resource blocker: the workstation reported about 257 MiB physical memory and
1.4 GiB virtual-memory headroom; analysis startup slowed substantially. The
primary coordinator prioritized ongoing real collection and instructed this
slice to start no further build. The already-running serial tests finished,
then this task released Flutter resources. No unrelated process/model was
stopped, no workstation setting changed, and no test/gate was weakened.

## Resource recovery and publication boundary

The primary controller subsequently granted one serial Flutter window. The
existing 57 tests were not repeated because their source was unchanged. The
release build and actual browser job then completed. Old preview 55826 was no
longer listening and Windows refused its rebind; this was a local port failure,
not a product business failure. The same isolated backend archive was started
with its safe Workspace/context acceptance profile on available loopback 52526,
using a new explicit Temp data directory. No scheduler/Collector was started.
Formal 53764, production DB and workstation/model settings were not changed.

The isolated backend is still base `15a994bbf172a783b9b8dd2bf8a8d43359829fec`;
its unavailable business states remain honest. This acceptance concerns actual
local text work and rendered glyphs, not current production backend/Actor E2E.
The content team's independent `web` dependency candidate is outside this font
diff. Source, this evidence, receipt and CURRENT must be co-published through the
controller's shared-index integration window; local verification is not release.
