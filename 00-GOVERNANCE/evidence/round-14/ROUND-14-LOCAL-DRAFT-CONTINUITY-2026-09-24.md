# ROUND 14 — local draft continuity and wallpaper selection

Date: 2026-09-24. Integration base: `742e48e1197d4a5cb6608b8f7e749657e9818a63`.
Status: PASS for the bounded Chrome local-text job and tested wallpaper fix;
not AI execution, whole-screen or ROUND 14 acceptance.
Related foundation: ROUND 08 / existing SYS-05 appearance owner.

## Scope and ownership

The Product Owner authorized continuing all independent frontend work. AI-01
retains its existing controller/composer and blocked business submission. The
new file helper is a presentation-side adapter for user-selected, unsent text,
not a second canonical store, Evidence importer, AI runtime or Context owner.
SYS-05 retains its existing preference/image controller. No dependencies,
production DB, account/Cookie, provider, registry or workstation environment
configuration were changed. macOS's existing sandbox entitlements add only
user-selected file read/write, needed by the installed file-selector plugin.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

- REAL USER JOB: prepare a real task, save its wording locally, reopen it after
  reloading the workspace and continue editing without silently losing text.
- ENTRY: AI-01 existing task composer; Open text draft / Save text draft / Copy.
- REAL INPUT: the current frontend task wording entered in the actual Web UI.
- END-TO-END PATH: composer -> browser text download -> local file -> reload ->
  file picker -> validated UTF-8 -> same composer with caret and typing focus.
- USER-VISIBLE RESULT: restored unsent text; context must still be checked and
  no analysis, server submission, Evidence or completed work is claimed.
- FAILURE/RECOVERY: picker cancellation, invalid/oversized file and read/write
  failure preserve current text; different nonempty text requires confirmation;
  changes during confirmation are not overwritten. Native save cancellation
  reports no success. Browser status describes download handoff accurately.
- EVIDENCE: final scoped tests, analyzer, Web build and browser record below.
- ACCEPTANCE ASSERTION: compare downloaded bytes and restored text, then decline
  and accept replacement; verify focus allows continued typing. This is a local
  drafting job, not the AI execution-to-Evidence business job.

Native Android/iOS offer Open and Copy; installed file-selector does not support
their save dialog. Native Windows/macOS/Linux use the user's save destination.
Only Web runtime is included in this Batch's E2E; native runtime is unverified.

## Changes and verification

- TXT import is limited to 64 KiB and 4000 graphemes, uses strict UTF-8, accepts
  an initial BOM, and rejects non-text control bytes. No automatic draft storage.
- Buttons, replacement dialog, busy/error/result status and accessibility live
  announcements are translated in zh-CN/en/ko. Mobile controls wrap.
- Independent review found composer focus was not restored after open. Root
  fixed it, then reran regression including empty and replacement focus/caret.
- Selecting Wallpaper now opens the picker first. Cancellation keeps the prior
  backdrop; successful validated image selection uses the existing controller.
- 41/41 targeted AI-01, SYS-05, appearance integration and typography tests
  passed, exit 0, after the final focus change.
- Scoped Flutter analyze passed with no issues, exit 0. An earlier run from the
  Unicode path failed inside Dart's LSP JSON parser (exit 255); it was not PASS.
  The same source analyzed successfully through the existing `L:` mapping.
- The initial wallpaper widget test hung because its fake asynchronous storage
  timer was awaited without advancing the test clock. Root corrected the test
  clock, stopped that own run and reran all 41 tests; the stopped run is not PASS.
- Authority exclusivity, strict anti-template and screen-blueprint checks passed.
- Final Web build with local engine assets and source maps passed, exit 0.
  An earlier build overlapped the focus edit and was discarded as focus evidence;
  the final isolated build includes that edit. Build output is local-only.

### Browser result — real local files, no synthetic business response

Chrome at `http://127.0.0.1:53764/workspace/AI-01` completed the job:
typed the actual current frontend task -> clicked Save -> downloaded a 109-byte
UTF-8 file -> reloaded to an empty composer -> opened that downloaded file ->
restored exact text -> typed directly at its end -> confirmed replacement ->
restored original text and composer focus. A separate decline preserved the
modified text. The final build downloaded the restored text again as
`lumenis-task-draft-1790231422986.txt`; its bytes matched the original download.
Both SHA-256 values:
`8becf0a4c73eb3c8040cdca781a45de5a125fa270b962b408672e153d046cdf6`.
Final generated `main.dart.js` SHA-256:
`7a7e07deaf41632d74319b30f8c7e7ae6569a15aa082583cad4297824e5113a9`.

Chrome wallpaper checks: an invalid local file was rejected without changing
the selected frosted mode; the user's local reference JPG activated Wallpaper
only after validation; Remove restored Frosted and removed the preview image.
Cancellation is proven by the widget test, not browser automation (the chooser
tool cannot submit an empty selection). Real OS picker cancellation remains
outside this runtime evidence. No selected image was uploaded.

The browser download-event observer timed out, including in Chrome, so no
observer PASS is claimed. Actual Chrome Downloads file name, bytes and reopen
were independently verified. IAB download-to-disk was not established. Its
page served an older build until the task-owned isolated preview process was
restarted with the published canonical cache policy. Temporary cache/worker
bypass was restored to false, and ordinary IAB reload then showed the new local
draft controls. No shared production process was restarted. The preview uses
an empty disposable DB and shows unavailable Context / disabled analysis.

Local evidence: `draft-roundtrip-final.png`, `draft-roundtrip-final-ax.txt`,
downloaded text copies and tool transcript. The local user-input file is not
committed as product data. Native file dialogs remain unverified.

Local machine logs remain outside source under the current frontend task's
`lumenis-design-review` artifacts: `draft-appearance-tests-final.log`,
`draft-appearance-analyze-final.log`, `draft-appearance-web-build-mapped.log`.
No generated build or user's text/image files are committed.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

Official sources accessed 2026-09-24:

| Source / version / license | Decision and mapping |
| --- | --- |
| https://pub.dev/packages/file_selector — installed 1.1.0, BSD-3-Clause, Flutter-maintained | ADAPT existing plugin for user-selected TXT; preserve platform capability matrix and narrow macOS entitlement. No new package. |
| https://pub.dev/packages/cross_file — installed 0.3.5+5, BSD-3-Clause, Flutter-maintained | ADAPT existing XFile exact-text save. Web Blob/download is a browser handoff, not observable durable save. |
| https://pub.dev/packages/shared_preferences — installed 2.5.5, BSD-3-Clause, Flutter-maintained | REJECT for important task draft persistence: documentation does not guarantee durable writes. Existing appearance preferences retain their current owner. |

Model routing: Root integrated and validated; one GPT-6 Luna bounded SYS-05
implementation and two read-only Luna owner/review tasks. Host limit: four total
slots, not ten. External Zhipu routing was not retried under the known unpaid
provider constraint; no model/provider/default configuration was changed.

## Remaining dependencies and commercial impact

AI execution, trusted actor/Subject/Brand context and execution-scoped Trace are
still blocked at their existing owners. CTH-10/SH-04 cannot be connected to the
dirty scoped-report candidate as if it were an accepted download contract.
SYS-06 remains DESIGN_EXPLORATION until actor-to-browser-session access and
safe projection are accepted; a native-only route gate does not close that gap.
These findings were returned to the main product controller; protected backend
work was not overwritten or staged with this frontend change.

COMMERCIAL OVERLAY IMPACT: local task continuity improves; no launch gate is
promoted. Native file dialogs/material effects and full AI/report workflows
remain unaccepted. ROUND 03 remains REWORK; ROUND 08/14 have no exit PASS.
GLOBAL UNIVERSE / DATA MATURITY IMPACT: no canonical business records are read
or created by this local-text feature. RANDOM ENTITY DATA ACCEPTANCE sample
count zero for this slice; no entity population or coverage inferred.
Global Commercial Coverage = NO / NOT VERIFIED; Global Brand Coverage = NO /
NOT VERIFIED; Guangzhou Taikoo Hui Reference Coverage = unchanged / NOT VERIFIED
by this slice. LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO.
RELEASED=NO; OPERATING=NO; COMMERCIAL_READY=NO.

Online publication applies only after this exact source/spec/evidence/CURRENT
commit is pushed and HEAD, origin/main and live main are reverified.

## Publication refresh and supplied wireframe — 2026-09-26

Fresh fetch still resolved `742e48e1197d4a5cb6608b8f7e749657e9818a63`.
The four changed product source files retain their verified SHA-256 values;
the 41 scoped tests were rerun successfully, exit 0 (`draft-appearance-publication-tests.log`).
The browser result above remains the dated 2026-09-24 run, not a claim of a new
full-product E2E on September 26.

The Product Owner supplied `LUMENIS_Low_Fidelity_Flow_20260925.html` as an
uncertain reference. File SHA-256:
`43365ec988d694132d6f69642a1e308ef78875b97b85c61ff2faedc6910880dd`.
Root confirmed 13 groups, 107 boards and no missing internal anchor target.
There are no scripts or external links. Its stated base is the same `742e48e1`
plus the local draft/appearance changes, not a competing product baseline.
The inspected AI-01, SYS-05, SYS-06, CTH-10 and SH-04 entries retain current
draft-only, local-appearance, unavailable-route and read-only/export boundaries.
ADAPT as a flow/state inspection aid under the existing screen specifications;
not DESIGN_READY, implementation proof, a 44-screen quota, or acceptance of all
107 conditional states. No HTML-generated layout is copied into the product.

Independent read-only review confirmed all 44 indexed source paths exist and
all 44 recorded SHA-256 prefixes match the current working-tree files. After
normalizing CRLF/LF, 43 match the base commit; AI-01 contains this Batch's real
local change. Raw Git-blob versus Windows-file line-ending differences are not
additional uncommitted implementations. The separate SYS-05 editor is outside
that screen-file index.

ACC-01/02/03 also match the reference: the shell omits their optional onward
navigation callbacks. ACC-02 can confirm Subject through selectContext, but
that does not prove its subsequent navigation. These are existing integration
gaps for the account/navigation owners, not new features authorized by HTML.
Review coverage is the index plus the named samples, not every board or state.
