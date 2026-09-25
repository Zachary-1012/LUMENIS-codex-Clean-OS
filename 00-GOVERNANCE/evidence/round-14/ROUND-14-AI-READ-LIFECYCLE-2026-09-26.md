# ROUND 14 — AI read lifecycle

## Bounded Task Card

- Base: fresh local/remote main `7d67d2d8e05c3542d4dda555bf57cf65204dfa83`.
- Publication base advanced to `89af8a2bbda9d69cd974d57a0d545a6752c33d7a`
  through the backend controller's separate Gateway/governance commits. These
  did not change the four allowed App paths; root fetched and reconciled again.
- Owner: existing AI-02 and AI-03 Flutter view models and their tests.
- Observed defect: each screen disposes its owned view model on departure;
  pending reads still assigned results and notified it afterward. Overlapping
  reads could also let an older result replace a newer result.
- One GPT-6 Luna executes this Batch only. Root reviews and verifies the result.
- Allowed: those two view models, focused tests and this evidence. Layout,
  features, repositories, execution proof, Permission, Evidence and providers
  remain with their existing owners. No dependencies or alternate lifecycle owner.
- Reuse the just-verified ACC-01/03 disposal and request-generation pattern.
- Screen layouts and interaction specifications are unchanged; this repair
  does not promote their blocked execution/trace design or acceptance status.
- Protected: all unrelated backend candidates, production DB/session material,
  Windows/Codex model configuration and the backend controller's index/CURRENT
  publication window. No provider calls or product startup are authorized here.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

- REAL USER JOB: inspect existing task/analysis status and return to prepare a
  local task when data is unavailable, including leaving while a read is pending.
- ENTRY: existing AI-01/02/03 shell routes.
- REAL INPUT: actual canonical read responses from the empty isolated preview;
  an actual local task draft. No seeded task, permission grant or fake analysis.
- END-TO-END PATH: enter task/analysis page -> pending or actual blocked read ->
  leave -> return to the composer -> retain a local draft.
- USER-VISIBLE RESULT: an operable current page with honest unavailable state;
  late replies cannot change the newer view. Local drafting is not AI execution.
- FAILURE/RECOVERY: delayed success/failure after departure is ignored; obsolete
  replies cannot replace a newer refresh; server errors keep their existing copy.
- EVIDENCE: red/green controlled request tests plus actual browser navigation.
- ACCEPTANCE ASSERTION: scoped lifecycle correction only. Real authorized task
  execution and citations remain unaccepted; this is not a Round exit.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

Official Flutter ChangeNotifier lifecycle documentation accessed 2026-09-26:
https://api.flutter.dev/flutter/foundation/ChangeNotifier/dispose.html
and its linked source:
https://github.com/flutter/flutter/blob/main/packages/flutter/lib/src/foundation/change_notifier.dart
The GitHub renderer could not be fetched; the installed source was inspected
directly instead. SDK 3.47.5 / Dart 3.13.4, Flutter revision
`6a19cca56475dbfba1478ee68d7bd0c2ef891da1`, maintained Flutter project, BSD-3-Clause.
ADAPT existing repository request invalidation to the SDK lifecycle contract.
No new library, third-party asset, external effect or architectural owner.

## GLOBAL UNIVERSE / DATA MATURITY IMPACT

No scope or data change. Random entity sample count is zero in the empty preview.
Global Commercial Coverage, Global Brand Coverage and Guangzhou Taikoo Hui
Reference Coverage are NOT VERIFIED by this Batch.
LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO.

## COMMERCIAL OVERLAY IMPACT

No task submission, analysis generation, report export or credential flow added.
Authorization, complete native surfaces and business E2E remain open.
RELEASED=NO; OPERATING=NO; COMMERCIAL_READY=NO. No Round PASS.

## Verification

Luna first added eight controlled-request regressions; all eight failed on the
old implementation (test command exit 1). Failures reproduced late notifications
after disposal, an old HTTP 403 replacing a newer result, and editing/selection
after disposal. The same two test files passed 19/19 after the minimal guards
were added (exit 0). Root reviewed all four changed files. Generation checks
also protect re-entrant refresh before a request is dispatched.

Root's scoped analyzer reported no issues (exit 0). The final Web build passed
in 97.8 seconds (exit 0), with `main.dart.js` SHA256
`DCAF10FC40B74F8060D2F68CE6F476DB5F1DFF320BAA357BF0906C08A84A1939`.

Actual Chrome checks used the canonical preview on loopback 53764 and its empty
disposable DB. The browser received real AI-02/03 reads; HTTP 200 did not enable
their unbound/unauthorized execution. A temporary 5/10-second network latency
setting applied only to the agent-created test tab exercised rapid page changes.
The longer latency exceeded the client timeout: AI-01 displayed a connection
error; after removing the delay, its existing Retry restored the composer.
Network evidence includes expected canceled requests, not a clean-network claim.
The old real 87-byte task TXT was then opened through the actual file picker,
restoring exactly the entered text and displaying the unsubmitted-draft notice.
The browser delay was cleared afterward. No AI task or business write ran.
Controlled tests, rather than release-mode screenshots alone, prove the precise
late-completion and out-of-order cases. Browser automation selector deadlines
were not counted as successful interactions; final visible states were checked.

Artifacts `ai-read-lifecycle-build.log`, `ai-read-lifecycle-browser.json` and
`ai-read-lifecycle-restored.png` are outside Git in the frontend task's existing
review directory. Protected product DB SHA256 remained
`A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`.
Root's combined account/navigation/shell/launch/AI-01/02/03/appearance regression
passed 106/106 (exit 0), logged in `ai-read-lifecycle-tests.log`. The final
repository static gates must pass on the published snapshot. The containing
commit also co-publishes the CURRENT status; fresh
local/origin/live main comparison is required after push. Hosted CI and full
business/native E2E remain unverified.
