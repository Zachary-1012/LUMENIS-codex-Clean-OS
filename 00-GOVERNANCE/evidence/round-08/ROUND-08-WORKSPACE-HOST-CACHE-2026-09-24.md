# ROUND 08 — canonical Web Workspace artifact host and cache policy

Sol decision: `PASS FOR BOUNDED SYSTEM RUNTIME BATCH / ROUND 08 EXIT NOT ACCEPTED`. The existing Flask Product Core now registers one bounded adapter for the generated Flutter Web Workspace artifact. This Batch does not accept the current frontend as a connected business workflow or release.

## Source and verification

- Base: fetched local and live `main` `d4a0fae885f93ff7611b194075187c415e437bdb`. Exact staged paths: `app.py` (three-line registration only), `lumenis/system/runtime/__init__.py`, `lumenis/system/runtime/workspace_host.py`, `tests/test_workspace_host.py`, this evidence, and CURRENT status. The other dirty `app.py` and backend changes remain unstaged.
- `/workspace` and extensionless deep links serve the generated `app/build/web/index.html`; existing root-relative Flutter assets are served only from that build directory. API/runtime namespaces are reserved. Missing builds return a structured 503, missing assets a 404, and traversal/directory requests cannot become HTML success.
- `index.html` is no-store; unhashed bootstrap/runtime assets use `max-age=0, must-revalidate`; content-hashed assets use one-year immutable caching. A mocked browser revalidation test checks unchanged ETag → 304 and changed bootstrap bytes → new 200/ETag. The frontend's source-owned bootstrap removes deprecated service-worker registration; SDK legacy cleanup remains in its separately published frontend Batch.
- Sol's isolated candidate tests passed 8/8 with shell profile disabled and no daemon-thread leak. The exact staged source is replayed against current clean `main` and checked before publication. No app startup, account, social browser, external service, or production database write is claimed.

## REAL DELIVERY CARD / 真实用户工作闭环验收

`REAL USER JOB`: open the Web Workspace from the product's canonical same-origin runtime and receive the current build after an update. `ENTRY`: `/workspace` or a screen deep link. `REAL INPUT`: a generated Flutter build artifact in a disposable test directory. `END-TO-END PATH`: Flask route → bounded build file resolution → cache/revalidation response. `USER-VISIBLE RESULT`: local frontend preview exists, but this exact Product Core host was not exercised in a real user session. `FAILURE/RECOVERY`: absent build returns 503, absent asset 404, stale unhashed asset revalidates. `EVIDENCE`: scoped test suite and staged source. `ACCEPTANCE ASSERTION`: adapter behavior passes as a bounded Batch; connected business E2E and ROUND 08 exit remain open.

`GLOBAL UNIVERSE / DATA MATURITY IMPACT`: no entity coverage added. Global Commercial Coverage=`NO`; Global Brand Coverage=`NO`; Guangzhou Taikoo Hui Reference Coverage=`PARTIAL / NOT REVERIFIED`; `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`. Random real-entity sample count is zero for this infrastructure Batch.

`COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO`. Actual Product Core startup, authorized API/Context/Permission binding, real user work, cross-surface acceptance and release remain open.

`CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION`: [Flutter Web FAQ](https://docs.flutter.dev/platform-integration/web/faq) and [RFC 9111 HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html), accessed 2026-09-24, support revalidation of non-hashed launch assets. [Flutter](https://github.com/flutter/flutter), maintained BSD-3 OSS at access, is the existing implementation (`ADAPT`); no new dependency or truth owner is introduced. Rollback is the mainline source commit; generated build artifacts stay replaceable.
