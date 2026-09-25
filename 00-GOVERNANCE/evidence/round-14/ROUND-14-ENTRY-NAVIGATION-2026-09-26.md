# ROUND 14 — Existing entry and workspace navigation

## Bounded Task Card / design review

- Entry base: `e604e4e08cfe129200db4f82d611822c3f617889`; coordinated backend
  commits `e50540d0` and `68d38431` advanced the shared main while this slice ran.
- Owner: existing Flutter shell/router, ACC-01/02/03/04 repositories and view
  models. No new route registry, product feature, Permission or Context owner.
- Allowed implementation: ACC entry callbacks, ACC-02 pending/confirmation
  safety, ACC-01/03 async lifecycle, scoped tests and current screen specs.
- Protected: every unrelated dirty backend path; product DB and sidecars,
  credentials, media sessions, model/provider/global Windows configuration.
- Root review: existing screen-specific layouts are DESIGN_READY for this
  bounded navigation change; complete screens and native/mobile acceptance
  remain unaccepted. The supplied low-fidelity HTML helped identify missing
  callbacks but is not a layout or implementation authority.
- ACC-01 Continue opens the already existing ACC-03 launch map. ACC-02 is an
  optional scope chooser; successful confirmed continuation opens the same map.
  It is never an account wall or a mandatory Subject selection step.
- ACC-03 maps commerce, brand and assistant to CTH-01, BMP-01 and AI-01 through
  the existing shell and browser URL owner. Navigation neither confirms runtime
  health nor grants downstream permissions. It never submits the AI task.
- ACC-04 Return opens ACC-03, preserving its unavailable guard. No access
  request, context-switch recovery, grant, or retry of a business write is added.
- The shell reuses the client's last server-confirmed Context on navigation so
  the visible header does not retain the pre-selection scope.
- ACC-02 keeps Continue disabled for unconfirmed/mismatched domain or Subject,
  pending selection and confirmation error. Pending confirmation is serialized
  even if the user selects another row. A departed page cannot notify disposed
  listeners when its request completes.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

- REAL USER JOB: open the internal workspace, choose a work area, prepare a
  local task description, and return to the existing entry without a new account.
- ENTRY: `/workspace/ACC-01` and the shell's account/work-area entry.
- REAL INPUT: current canonical runtime GETs on an empty isolated database;
  the user's actual request to continue completing the frontend, entered as a
  local task draft. No fixture business records or fabricated permission grant.
- END-TO-END PATH: ACC-01 -> ACC-03 -> existing destination; AI-01 -> local task
  text -> actual TXT download; shell return -> entry. Separately inspect ACC-02
  unavailable scope and ACC-04 unbound recovery without promoting either.
- USER-VISIBLE RESULT: chosen work surface and retained local draft file, or
  the actual unavailable/denied state. A selected route alone is not a business
  result or a completed AI task.
- FAILURE/RECOVERY: rejected/pending scope cannot continue; read errors retain
  existing retry; unbound guard can return; delayed reads after leaving are inert.
- EVIDENCE / ACCEPTANCE ASSERTION: verification results are recorded below.
  Real authorized Subject selection remains required before ACC02-REAL-01 passes.

## Independent review and compute

One read-only Luna identified the same pending/duplicate confirmation risk and
the exact three domain roots. Root adopted those findings. Its suggestion to
return directly to CTH was refined to the existing launch map so entry preserves
GLOBAL/ALL and does not silently choose a domain or require a Subject.
Two bounded GPT-6 Luna implementation tasks cover ACC-02 and ACC-01/03 async
handling; root owns integration, tests, browser acceptance and publication.
Observed host limit is four total agents, with at most root plus two active
implementation workers here. External unpaid provider routing was not retried.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

Installed `go_router` is 18.0.1 (lockfile). Official package and navigation docs
accessed 2026-09-26:

- https://pub.dev/packages/go_router/versions/18.0.1
- https://pub.dev/documentation/go_router/latest/topics/Navigation-topic.html

Flutter-maintained, BSD-3-Clause. ADAPT the already installed route owner and
`context.go` URL flow, retaining existing browser history; no new dependency or
imperative parallel navigation stack. Version-specific navigation-page fetch
was unavailable, so current official documentation was cross-checked against
the installed usage. No third-party assets, account integration or cost added.

## GLOBAL UNIVERSE / DATA MATURITY IMPACT

Default GLOBAL/ALL and optional focus remain unchanged. Navigation grants no
scope. RANDOM ENTITY DATA ACCEPTANCE: zero samples in the empty isolated
preview; no authorized registry population is fabricated to make selection pass.
Global Commercial Coverage: NOT VERIFIED. Global Brand Coverage: NOT VERIFIED.
Guangzhou Taikoo Hui Reference Coverage: NOT VERIFIED by this slice.
LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO.

## COMMERCIAL OVERLAY IMPACT

This is an entry/continuation slice. Actual guarded Subject selection, downstream
AI execution, report generation/export, SYS-06 session authorization, native
packaging and full user acceptance remain with their existing owners and gates.
No Round exit PASS. RELEASED=NO; OPERATING=NO; COMMERCIAL_READY=NO.

## Verification and online publication

Root verified the final product source on 2026-09-26:

| Check | Actual result |
| --- | --- |
| Flutter account, navigation, shell, launch, AI-01 and appearance regression | 87/87 passed; exit 0 |
| Scoped Flutter analyzer (account owners, shell and changed tests) | No issues; exit 0 |
| `flutter build web --no-pub --no-web-resources-cdn --source-maps` | Built Web in 135.2 seconds; exit 0 |
| Chrome entry job | ACC-01 Continue -> ACC-03 -> AI-01 -> enter real user task -> actual TXT download -> return through ACC-01/03 |
| Scope failure | Actual Context HTTP 401 retained as restricted; map remained operable; CTH-01 still denied business data; ACC-02 showed identity unconfirmed |
| Recovery | ACC-04 retained its unbound recovery state after recheck; Return opened ACC-03 without a grant or context switch |
| Narrow Web layout | 390 x 844 launch map, AI-01 input and return to ACC-01 checked; temporary viewport reset invoked afterward |
| Independent final review | Read-only Luna found no confirmed permission/navigation defect; root inspected the actual diff |
| Repository static gates | Experience authority, strict anti-template, blueprint/source contract and takeover governance: all exit 0 |

Browser E2E caught an optional Context permission error blocking the whole map,
then a misleading unnamed-global fallback. Both were corrected and retested.
An intermediate nullability mistake failed build/analyzer/tests; those failed
results were superseded only after correction by the successful final runs above.
Two shell invocations initially selected the wrong working directory and failed;
final commands explicitly set the app directory. The Unicode-path analyzer
transport failed separately; final analysis used a temporary ASCII junction to
the same canonical app, without changing source or workstation configuration.
Some browser locator actions timed out; actual page states and direct accessible
controls were used to verify the resulting navigation, not timeout assumptions.

The downloaded file `lumenis-task-draft-1790357797655.txt` is 87 bytes and exactly
matches the entered UTF-8 text. SHA256:
`2ACB5BDC94F7756A414BA81DA55CCDB7BE5CBAF776777CD2DC32FAA71127D0FE`.
Final `main.dart.js` SHA256:
`32E15DB00D7723925A667004CD246B331F5ADA123F5EDC00813F60D0BFE2CFF0`.
Screenshots, AX states and command logs remain outside Git in the frontend task's
`lumenis-design-review` artifact directory; no draft contents are published.

The loopback preview on port 53764 uses canonical blueprints and workspace host
with an empty disposable DB. It is not the full Product Core on port 8201 or a
production business workflow. No authenticated scope was invented. Actual
authorized ACC-02 selection, business/AI effects, native Desktop/Mobile and full
Round acceptance remain open. Product DB length stayed 1,458,176 bytes and its
SHA256 stayed `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`.

Only the exact reviewed source/spec/test/evidence/CURRENT paths are eligible for
this coherent commit. The containing commit must pass authority, anti-template,
screen-specification and takeover validation and be checked against fresh remote
refs after push; local command success is not GitHub-hosted CI or release proof.
