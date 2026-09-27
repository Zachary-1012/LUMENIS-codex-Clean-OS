# ROUND 06 — AI Browser synchronous Playwright thread affinity

Status: `SOURCE TESTED / ISOLATED REAL ENGINE VERIFIED / PRODUCT USER E2E NOT ACCEPTED`
Owner: existing SYSTEM Browser AI Browser runtime
Parent: `fd4e01622ebfff75903cb10b729049af2e5e2170`
Date: 2026-09-27

## Change and observed result

The existing AI Browser session now creates its synchronous Playwright connection
on one session worker thread and executes its status, observation, action,
screenshot and shutdown calls on that same thread. A repeated start does not
create a second context. The worker ends when the session closes. This closes
the cross-thread invocation defect found during the preceding real probe;
the existing Browser owner, action firewall, Permission API and verified isolated
default-browser engine remain the only paths.

On this Windows host, an isolated, disposable-DB probe called `start`, public
`https://www.bing.com/` navigation, `get_status`, `screenshot` and `close`
from separate request threads. It returned `navigate_result=PASS`, a page
title, a 4,580-byte screenshot and a legacy BrowserEvidenceStore ID. The
verified product browser process already existed, so the probe created and
closed only its fresh context and did not stop that process. No personal XHS
profile, account or browser session was used.

## Verification and limits

- 198 focused browser runtime, security, action verification, recovery,
  legacy Evidence and injection tests PASS, including cross-request-thread
  ownership and repeated-start regression; no background daemon thread leak.
- `py_compile`, Constitution Gate and Takeover Gate PASS at this source snapshot.
- The direct runtime probe used test actor identifiers in an isolated DB. Its
  legacy BrowserEvidenceStore ID is not canonical Evidence acceptance.
  Authenticated product HTTP, target/frame ownership, SYS-06 viewport/actions,
  real user review and cross-surface work remain `REWORK / LIVE_NOT_VERIFIED`.
  ROUND 06 and 14 are not accepted by this Batch.
