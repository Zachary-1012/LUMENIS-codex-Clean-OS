# ROUND 14 — Local appearance and return continuity — 2026-09-27

Status: bounded implementation tested on an isolated main candidate; final
publication review in progress. No Round, business workflow,
native surface, or release acceptance is asserted. Resolve publication from
fresh Git refs; this file is not a substitute for them.

## Task Cards and current truth

The frontend continuation began at `76f8c473`; a fresh fetch then confirmed
`79f46a7ab8aa49a7de2d733528a8e920be8d9696`, then
`00960ff9d1b0f48c380b408bdfff329eee49ade2` on local/main and origin/main.
The App and detailed screen specifications were initially clean. Existing
backend/governance candidates remain protected. No database, provider route,
Cookie, process-wide user setting, or backend API is changed by these Cards.

| Card | Existing owner and bounded change | Source/test state |
| --- | --- | --- |
| R14-SYS05-LOCAL | SYS-05 resolves its existing device-local appearance scope before mounting the remote settings branch; keep the no-scope fallback | Implemented; 35 related tests passed; scoped analyzer passed; independent source review found no regression |
| R08/14-SCOPE-RECOVERY | Existing shell context picker recovers from an unreadable formerly confirmed focus through its existing clear-context operation | Implemented; 16 scoped tests passed, exit 0; reviewed repeated failure, late-response and new-confirmation recovery |
| R08-CONTEXT-ATOMIC-CONFIRM | Existing Core client validates requested scope before accepting its envelope/headers; rejected select/clear must preserve the previous confirmed scope | Implemented; 8 scoped transport tests passed, exit 0; root reviewed the two-line source change |
| R14-SH02-RETURN | Existing SH-02 Space/List detail return restores browsing position and invoking-item focus | Implemented; 11 scoped tests passed within the final combined run, exit 0; source review completed; live binding remains unverified |

These are repairs to reviewed local presentation and recovery behavior. They
do not enable unbound data, grant permission, expand collection controls, or
create an alternate screen renderer. Existing API calls remain canonical.

## Existing design gate

All three specification changes clarify existing implementation/recovery;
none changes visual direction, creates a feature, or accepts a blocked API.

| Screen | Current approved boundary | Experience Constitution mapping | Specification delta |
| --- | --- | --- | --- |
| SYS-05 | DESIGN_READY; runtime PENDING | §6 device-local appearance; §§17–18 settings and honest state; §§31–36 | Replace the obsolete always-read description with local-scope-first behavior; preserve every unrelated paragraph |
| ACC-02 / shared picker | DESIGN_READY for confirmed selection; existing shell CTH/BMP picker | §9 context; §18 failure states; §34(2) real shell recovery; §36 | Specify recovery through the existing clear endpoint, no cached authorization or silent collection |
| SH-02 | presentation DESIGN_READY; business BLOCKED | §12 Evidence; §§20–21 responsive focus; §32 Trace / Return; §36 | Record verification of already-required position, query and invoking-focus return; retain business block |

## Why, impact, risk and recovery

- A local appearance route previously read remote settings it never displayed.
  SYS-05 now mounts that read-only branch only without the local scope. The
  local controller, preference format, palette, draft and shell ownership stay
  unchanged. A test also covers disposal while a fallback read is pending.
- The scope recovery is limited to a previously server-confirmed focus. An
  unreadable focus must not become an implicit GLOBAL or a permission grant;
  only the existing server-confirmed clear response may change selection.
- SH-02 return continuity is local presentation state over the same verified
  visible rows. Missing rows must not be reconstructed or invented to recover
  focus. The business Evidence/Permission binding remains blocked.
- Rollback is a scoped reversal of these presentation edits after preserving
  any newer changes; no data migration or production-data repair is involved.

## Verification ledger

- SYS-05 first added test run failed because the existing test host omitted
  the real App localization delegate. That test harness was corrected rather
  than skipping an assertion. Subsequent run: `sys02_to_sys08_test.dart`,
  `sys05_appearance_test.dart`, and `lumenis_appearance_integration_test.dart`:
  **35/35, exit 0**. The two SYS-05 edited Dart files analyzed with **no issues,
  exit 0** using the existing ASCII junction to the same canonical sources.
- The independent Luna review covered only the SYS-05 source/test diff and
  found no lifecycle or contract regression. It is not independent runtime
  evidence. The remaining Cards were independently inspected by root against their
  final scoped diffs; this is not independent runtime evidence.
- SH-02 scoped final run: **10/10, exit 0**, covering list offset, Space
  camera/focus, filtered-item fallback and 390 px query/return. An earlier
  test-only attempt failed compilation for a missing new fixture helper; it
  was corrected before the final run. No behavior-red baseline is claimed.
- Core context confirmation: the corrected red assertion reproduced a rejected
  focus response replacing the cached confirmed Subject. The initial red
  attempt had matching fixture/request input and was corrected. Final
  `lumenis_core_client_test.dart`: **8/8, exit 0**. Loopback HttpServer unit
  tests inspect cached selection and subsequent request headers after wrong
  Subject/domain/mode replies, rejected clear and successful GLOBAL clear.
  This is real local transport with fixture responses, not business E2E.
- Shell scoped final run: **16/16, exit 0**. The baseline exposed missing
  stale-focus recovery. Later test-only fixes replaced an inappropriate
  pumpAndSettle during indefinite loading with a bounded pump, and corrected
  an expected GLOBAL label to the required unavailable label; neither was a
  production behavior bypass. CTH/BMP clear, denied/pending clear, repeated
  failed reads, late dismissed reads and newly confirmed ACC-02 navigation
  are covered.
- Clean-main candidate verification uses a `git archive` of `00960ff9` plus
  exactly the reviewed App/spec/evidence paths. The protected shared working
  tree remains dirty. Its constitution gate failed because its protected
  `tests/test_report_audit.py` candidate lacks two missing-vs-zero regression
  anchors that remain in published main. That path was not edited, staged or
  replaced. The isolated candidate constitution and five other gates passed
  (all exit 0); this does not convert the dirty-working-copy FAIL into PASS.
- The first combined isolated Flutter run passed **92/92, exit 0**. Full App
  analysis then exited 1 on three added test-style lints. They were fixed
  without disabling rules; final post-fix verification is recorded below.
- The static gates are `verify_ai_native_constitution.py`,
  `verify_experience_authority_exclusive.py`,
  `verify_experience_anti_template.py --strict`,
  `verify_experience_screen_blueprints.py`, `verify_lumenis_single_product.py`,
  and `verify_codex_takeover_governance.py`. The two Git-aware validators read
  the real main Git metadata via process-local GIT_DIR/GIT_WORK_TREE; their
  HEAD co-publication result refers to base `00960ff9`. The integrating owner
  must check the new source/evidence/CURRENT commit again after publication.
- Current safe business Core preview: unavailable at inspection; neither
  `8201` nor the earlier `53764` preview was listening. The Runtime owner is
  preparing its isolated acceptance profile. No full production launcher or
  obsolete preview was started for this work.

### Final isolated candidate verification

After the three lint repairs and the focused List/Space transition test, the
combined suite passed **93/93, exit 0** on the final App source/test candidate.
It covers SYS02–SYS08, appearance persistence and App integration, shell,
navigation, Core transport, SH-02 and ACC-02. The targeted transition test
passed without any additional production change; the actual SH-02 container
is AnimatedSize, not an overlapping AnimatedSwitcher.

Commands (inside the isolated candidate's `app/`):

```text
flutter test --no-pub test/features/system/sys02_to_sys08_test.dart test/features/system/sys05_appearance_test.dart test/product/lumenis_appearance_integration_test.dart test/shell/lumenis_workspace_shell_test.dart test/navigation test/core/lumenis_core_client_test.dart test/features/shared/sh02 test/features/account/acc02 --reporter expanded
flutter analyze --no-pub
flutter build web --no-pub
```

Full App analysis passed with **no issues, exit 0**. Web release compilation passed
with **exit 0** (86.6 seconds), including the SDK Wasm compatibility dry run.
This is a Web package, not a browser/native runtime or business E2E result.
All six named static gates were rerun after the final App/test changes and
passed with exit 0. App source/test files were frozen before this final run.
The 12 exact candidate paths and SHA-256 hashes, patch and raw command logs
were handed to the mainline controller for one source/evidence/CURRENT
publication. No frontend-side commit, push or CI result is claimed here.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

- REAL USER JOB: change local appearance without an irrelevant server read;
  recover an unusable focus through the canonical clear action; inspect a
  material and return to its previous browsing position.
- ENTRY: existing SYS-05 route, shell context picker, and SH-02 browse/detail.
- REAL INPUT: actual user preference, last server-confirmed focus, and real
  authorized material respectively. Tests use isolated doubles and never
  substitute for production material or permission.
- END-TO-END PATH: existing UI → existing local preference or canonical
  context owner → confirmed result → return; SH-02 is read-only presentation.
- USER-VISIBLE RESULT: the same local appearance editor and work context;
  GLOBAL only after confirmed clear; stable material browse return.
- FAILURE/RECOVERY: local storage errors remain explicit; failed/denied clear
  does not claim GLOBAL; unavailable material stays unavailable.
- EVIDENCE: final code diff and automated results are source/test evidence.
  Current business Core, real actor, authorized data, native runtime and full
  user-job E2E are **LIVE_NOT_VERIFIED**. No historical screenshot is reused as
  current evidence.
- ACCEPTANCE ASSERTION: each Card must satisfy its bounded regression, and
  real page behavior must be verified before marking it live. ROUND 14 remains
  **REWORK**; these edits do not pass any predecessor or Round 15.

## GLOBAL UNIVERSE / DATA MATURITY IMPACT

Default GLOBAL/ALL and CTH Subject/BMP BrandFocus semantics remain intact.
Selection and clearing do not start collection. Global Commercial Coverage,
Global Brand Coverage remain **NO / NOT VERIFIED**; Guangzhou Taikoo Hui
Reference Coverage remains **PARTIAL / NOT REVERIFIED**. This Batch adds no
coverage. RANDOM ENTITY DATA ACCEPTANCE: live sample
count **0**, because the safe, actor-bound live environment is unavailable.
No fixture is counted as a sampled entity or mature coverage.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

Accessed 2026-09-27. Existing local SDK: Flutter 3.47.5 / Dart 3.13.4; no package
upgrade or new production dependency is introduced.

| Source | Version/license/maintenance | Decision and owner mapping |
| --- | --- | --- |
| [Flutter focus guidance](https://docs.flutter.dev/ui/interactivity/focus) | Current official documentation; installed Flutter source uses its existing BSD-3-Clause license | ADAPT managed State-owned focus nodes and return focus for SH-02; no new design/data owner |
| [Flutter State dependencies](https://api.flutter.dev/flutter/widgets/State/didChangeDependencies.html) | Current official API reference; installed SDK compatibility | ADAPT inherited appearance-scope routing within SYS-05; retain the existing remote fallback lifecycle |
| [motion-web](https://github.com/Zachary-1012/motion-web/commit/5f4e40f1253e11e28850d08dce28b9b7e4320115) | Live main checked at the linked commit; not archived, last push 2026-09-15; LICENSE is CC BY-NC 4.0, despite GitHub metadata reporting NOASSERTION | DEFER code/assets/workflow adoption; no justified motion addition to these recovery repairs; no dependency or copied material |

## Product requirement routing and COMMERCIAL OVERLAY IMPACT

The 2026-09-27 collection direction is owned by the existing Global contract:
manual user action by default, automatic collection only after explicit opt-in,
and no collection on focus selection/clear or page startup. Current SYS-02 and
CTH-03 specifications do not authorize new collection controls. The inspected
uncommitted backend projection has no accepted automatic-mode/opt-in binding;
the frontend must not manufacture that state.

The frontend binding checklist is manual action as the initial mode; AUTO
starts off and needs deliberate confirmation showing the actual source,
range and frequency before enabling, an honest unavailable/denied state,
and a clear disable/return path. Those states must come from the existing
Collector owner before controls become operable; this checklist is not a
new API contract or a promotion of SYS-02/CTH-03 to DESIGN_READY.

The read-only Evidence caller audit at `00960ff9` found no Flutter callers
for the newly hardened `/api/evidence/{stats,list,id,timeline}` family.
The existing content-Evidence and screen routes are different endpoints.
No caller rewrite is required; neither technical Basic authorization nor
fixture-backed screens prove the new server actor/Permission binding.

Professional original creation remains the existing Brief + Evidence →
strategy/script/storyboard/content/video → edit/review → export/use → evaluation
chain. These local recovery repairs do not supply or accept that professional
delivery chain. It stays with the existing Shared/BMP and backend owners.

COMMERCIAL READINESS GAP / BLOCKED FOR COMMERCIAL_READY. Source repair and
automated tests do not establish release, commercial readiness or user sign-off.
