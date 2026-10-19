# F — report continuity and public workflow candidate

Date: 2026-10-02. Frontend build base:
`a85c35ee619ae75052f91b3b924e467bd8bc1622` plus the protected F changes.
The App increment remains an unpublished candidate for M acceptance and W6
integration/publication. Website's separate accepted increment is now published
in `9a51963dffe6e58ce8c986e0384b09d74ed66223`, verified at 01:37 UTC against
HEAD, freshly fetched origin/main and live refs/heads/main. This does not accept
full CTH-10, full frontend or product release.

## Current Task Card and scope

F owns `app/` and `website/`. M approved the public workflow candidate in
`website/DEVELOPMENT-BRIEF.md` and the bounded CTH-10 SourceBrief increment;
W6 recorded the latter in revision 2 of
`contracts/experience/screen-specifications/CTH-10.md`. Existing SourceBrief
services retain Permission, source/Evidence integrity and persistent Job truth.

REAL USER JOB: organize the current CTH scope's verified sources, know whether
the task is waiting, completed or interrupted, and return to the same saved brief.
ENTRY: CTH-10's separate source-brief action. REAL INPUT: existing canonical
sources in the selected GLOBAL_ALL/CTH focus; an existing task/Job reference for
recovery. No synthetic business data is submitted as live input.

END-TO-END PATH: fresh context → POST start → actual task status → separate Job
GET → saved source list → leave/reopen by reference. A 202 response never means
the brief is saved. Resume is an explicit action using the same task ID and a
fresh server authorization. Weekly/period reports and export remain unbound.

USER-VISIBLE RESULT: source titles, dates, provenance and links; saved/reopened
status; business analysis and human review are distinct. No business question
is sent while the owned analysis route is unbound. Existing typed analysis can
be read as a draft, separate from source facts. No new account or login wall.

FAILURE/RECOVERY: denied, unavailable, unknown/malformed result, pending/running,
interrupted and failed remain distinguishable. On context change or a newer
operation, old responses cannot overwrite the current view. Transient context
read failure hides prior result while preserving known task/Job references.
Every new read also clears the previous displayed artifact before revalidation;
task-level denial or malformed responses cannot leave it shown as current.
The user can copy a reference and reopen after navigation/reload; this UI has
no second persistent report/history store and does not claim automatic recall.

ACCEPTANCE ASSERTION: a visible saved result requires the verified Job readback,
matching exact CTH scope and source/Evidence identities; analysis availability
and HUMAN_PENDING are not promoted by successful persistence.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: no registry or collection coverage
change. Global Commercial Coverage, Global Brand Coverage and Guangzhou Taikoo
Hui Reference Coverage are not established by frontend tests. Random registry
acceptance and real input counts belong to the recorded live operation and
canonical data owners; fixtures below are not coverage evidence.

COMMERCIAL OVERLAY IMPACT: local interface closure is incremental. Period/
weekly/export, owned inference service, actual deployment and Product Owner
repeat operation remain separate outstanding gates. COMMERCIAL_READY is not
claimed.

## Coherent implementation

- CTH-10: source-only task entry, status refresh, explicit resume, verified Job
  reopen, source reading and separate analysis/review state; responsive reading
  composition and Chinese/English/Korean copy. Polling pauses while inactive
  and is disposed on leaving; no automatic resume/new write.
- CTH-10 legacy report paragraphs and quotes no longer share the 240-character
  label limit. Withheld malformed/sensitive blocks mark the result partial.
- BMP-09: temporary in-page request state says it is cleared by refresh/leave;
  it no longer claims a saved draft or generated report.
- Website: two existing business questions have three reversible reading
  stages, keyboard navigation and honest destinations. Its detailed browser
  evidence is in `website/DEVELOPMENT-BRIEF.md`.

## Automated evidence

The Windows PowerShell profile changes working directories, so all commands
used explicit `workdir` and `login:false`. No persistent shell configuration
was changed. Flutter 3.47.5 / Dart 3.13.4 used the existing SDK.

| Check | Result |
| --- | --- |
| `flutter test --no-pub test/features/cth/cth10` | **33 PASS**, exit 0, including task-revalidation failure/recovery and rendered failure state |
| `dart analyze --fatal-infos lib/features/cth/cth10 test/features/cth/cth10` | **No issues**, exit 0 |
| `flutter test --no-pub test/features/bmp09/bmp09_report_request_test.dart test/features/bmp_creation/bmp_creation_screen_test.dart` | **28 PASS**, exit 0 |
| Scoped Dart analysis of BMP-09 source/new tests and BMP creation tests | **No issues**, each exit 0 |
| SourceBrief CoreClient contract tests | **4 PASS**, exit 0 |
| Adjacent content-project CoreClient tests | **10 PASS**, exit 0 |
| Scoped Dart analysis of CoreClient and its new test | **No issues**, exit 0 |
| Website final preview `npm test` | Build + **12 PASS**, exit 0 |
| Website configured-destination contract branch | Build + **12 PASS**, exit 0; public fixtures only, then restored preview |
| AI-native constitution validator | **PASS**, exit 0 |
| Experience authority exclusivity | **PASS**, exit 0 |
| Experience anti-template `--strict` | **PASS**, exit 0 |
| Experience screen blueprints | **PASS**, exit 0 |
| F-only `git diff --check -- app website` | exit 0 |

Initial failures were repaired rather than excluded: the long-text regression
reproduced the truncation; a Dart state field shadowed the task parser; one new
offline test paired different task/readback IDs; and a reference-button test
needed to scroll the actual control into view. A final regression reproduced a
previous artifact remaining visible after a denied/malformed task refresh; the
new operation now hides that artifact while retaining its recovery references.
The regressions prove denial, malformed response and same-Job recovery. A
failed read now also shows an unconfirmed task label instead of continuing to
say that readback is in progress.
All original assertions remain.

`flutter analyze` hit the SDK's non-ASCII-path LSP framing defect. Direct
`dart analyze` was used successfully against the same files instead of altering
SDK code, moving the canonical repository, or weakening checks.

## Research and adoption

Accessed 2026-10-02, current official sources; no new dependency or copied
third-party asset/code, hence no new distribution notice requirement:

- [Flutter ephemeral state](https://docs.flutter.dev/data-and-backend/state-mgmt/ephemeral-vs-app):
  ADAPT — describe BMP request preparation as page-local state.
- [Flutter Text](https://api.flutter.dev/flutter/widgets/Text-class.html) and
  [maintained widget tests](https://github.com/flutter/flutter/blob/master/packages/flutter/test/widgets/text_test.dart):
  ADAPT — preserve verified paragraphs and let the existing reader wrap them.
- [Dart invocation diagnostic](https://dart.dev/tools/diagnostics/invocation_of_non_function_expression):
  ADAPT — distinguish task state data from its parsing function.
- [Flutter lifecycle observation](https://api.flutter.dev/flutter/widgets/WidgetsBindingObserver/didChangeAppLifecycleState.html):
  ADAPT — bound read-only polling to the active page lifecycle.
- [Flutter asynchronous snapshot contract](https://api.flutter.dev/flutter/widgets/FutureBuilder-class.html):
  ADAPT principle only — old asynchronous data can survive a new request;
  explicitly hide the previous artifact until access and readback are verified
  again in the existing ViewModel. No new state-management dependency.
- [Flutter issue 192079](https://github.com/flutter/flutter/issues/192079),
  [191309](https://github.com/flutter/flutter/issues/191309), and
  [fix 191377](https://github.com/flutter/flutter/pull/191377):
  ADAPT development invocation only — direct Dart analysis for the observed
  Unicode-path tooling failure. This is not product runtime evidence.

## Live and integration evidence

Website operation and M's bounded local engineering acceptance are recorded in
its brief. SourceBrief Web release build completed, exit 0, with bundled
CanvasKit and a successful Wasm dry run. Command (from `app/`):
`flutter build web --release --no-web-resources-cdn --no-pub --output build/source-brief-preview`.
The first candidate `main.dart.js` SHA256
`fd05f651735499acdd27a8c693c64fcf26f97262ac3b0a20f9efbf5a34b20f7f`
was withdrawn before deployment after the task-revalidation regression.
The replacement build completed in 201.9 seconds with exit 0 and bundled
CanvasKit. W6 must use this replacement `main.dart.js` SHA256 only:
`a0de16ecc518a24cac810c4dd87f7b8cb53450d45831ee5fdd20b3bb6b760b6f`.

W6 switched the existing canonical 8201 Core to this candidate through its
existing process-scoped workspace-host seam, retaining `app/build/web`. Its
reported loaded source was `4a318776` plus the coordinated owner candidates,
not a claim that every running candidate was already on main. F operated that
same-origin page and observed the separate SourceBrief entry. F did not restart
Core, change persistent environment, publish main or directly access the DB.

### Real browser operation — 2026-10-02

Input was the existing GLOBAL_ALL CTH canonical source set. No business question,
model invocation, fixture, fabricated report or direct database write was used.
One create action made this real saved artifact through the existing service:

- Task: `rbrief_ab54bb81-8feb-467c-9c0f-2458821909f1`.
- Job and Report: `brief-fb2192a3e5784d18a68ed0186b49733b`.
- Artifact SHA256: `59b5efb3a98623106b35883a533b1b4d9a73576a3f02a79af6df082e438acff6`.
- Readback: 29 records, `persisted_and_reopened_verified`, analysis
  `not_requested`, review `HUMAN_PENDING`.
- Source Evidence references, in returned order: 422, 422, 418, 417, 407, 401,
  399, 398, 166, 162, 139, 171, 147, 375, 188, 138, 149, 163, 167, 121, 148,
  173, 120, 108, 134, 191, 187, 168, 137. Repeated references are preserved;
  29 records are not represented as 29 distinct Evidence objects.
- Evaluation row/ID pairs: 131 / `1ab2cd9692725f48c095bf2774f631259ec010e91a455853f999eb5dbeebec6f`,
  132 / `ccc276e9f0ccb33212c34761edbe5666aa48394cf80ddecfde1a00ca269cf767`,
  133 / `ff3709419499b06cd07d166115eab876fe0043ecc69000c137a825668b4d79ee`.

| Actual user operation | Observed result |
| --- | --- |
| Enter CTH-10 → separate SourceBrief → create | Start 202, task GET 200, separate Job GET 200; saved result and real source titles displayed |
| Expand VivoCity source | Original URL, recorded time and Evidence reference 418 readable; unavailable publication time remains unconfirmed |
| Return to reports, enter again, type saved Job reference | Same Job, artifact hash and complete record array read back |
| Browser reload, enter again, type reference | Same saved result reopened |
| Temporarily take this browser tab offline, open reference | Error visible, saved result absent, exact reference retained |
| Restore tab network, open reference | Same Job/hash and 29 records returned |
| Select actual VivoCity focus | Previous GLOBAL result cleared |
| Attempt GLOBAL Job from VivoCity focus | Actual Job GET 403, honest scope error, no prior result shown |
| Restore GLOBAL, open existing task reference | Same saved result returned through task and Job reads |
| Chinese → English → Korean → Chinese | Saved result and task/review states remained readable |
| 1440 and 390 px browser widths | Operable responsive reader inspected; this does not establish native device acceptance |

The tab's network/cache/viewport overrides were restored. Context was restored
to GLOBAL and language to Chinese. Final browser warning/error log was empty.
The deliberately tested offline/403 responses were expected recovery cases.

Evidence artifacts under `work/frontend-2026-10-02/`:
`source-brief-live-evidence.json`, `source-brief-final-desktop-1440.jpg`,
`source-brief-mobile-390.jpg`, `source-brief-offline-390.jpg`.
The JSON is a scoped extraction from actual UI network responses, not a DB dump.

### Remaining acceptance limits

- Interrupted-task resume: same-ID unit/widget behavior passes; no genuine live
  interrupted task was manufactured. W6 was asked for an existing safe,
  source-only GLOBAL task if available. `LIVE_NOT_VERIFIED` for this path.
- Copy button: the product displayed its completion toast, but Browser Use's
  separate virtual clipboard stayed empty and could not perform paste. Actual
  system clipboard transfer is `NOT_VERIFIED`; manual reference reopen passed.
- The legacy weekly/period report index, export, owned analysis, installed
  native surfaces and Product Owner repeat operation remain separate gates.
  Global/reference coverage and full frontend/commercial readiness are not
  promoted by this one successful source brief.

### Adjacent BMP-09 live honesty check

The refreshed 8201 runtime rendered the new temporary-request copy in BMP-09.
The actual GLOBAL brand evaluation remained unavailable; clicking its request
action showed the current scope/report-authorization restriction and never
claimed a saved draft or generated report. Screenshot:
`work/frontend-2026-10-02/bmp09-real-unavailable.jpg`. This verifies the real
unavailable path and wording only. The eligible temporary-request path remains
covered by the scoped tests; a full brand evaluation/report job is not accepted.

### M bounded final acceptance — 2026-10-02

M (thread `private-source-id-sha256-c255b5e6a0750867a584692fa6107a7d4df9f561ec97e6faeac199516b522186`) accepted the source-only
SourceBrief main flow: real canonical sources, saved artifact, reference reopen,
offline recovery and scope-switch isolation. The 14 Dart source/test files remain
frozen for W6's exact App + CURRENT co-publication. This note records M's decision;
it is not by itself evidence that the App candidate has been published.

The accepted result has 29 source records with traceable Evidence, with business
analysis `not_requested` and review `HUMAN_PENDING`. Its evaluation records describe
the materials workflow, not commercial outcomes. W6's read-only check found all
15 existing SourceBrief production tasks already succeeded; a genuine interrupted
task was unavailable, so resume remains `LIVE_NOT_VERIFIED`. Actual system clipboard
transfer remains `NOT_VERIFIED`. No acceptance of whole CTH-10, AI analysis, C3,
the four installed surfaces, Product Owner repeat operation or release is implied.
