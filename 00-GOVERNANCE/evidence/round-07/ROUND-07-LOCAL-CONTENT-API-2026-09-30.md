# ROUND 07 — open local Content API integration

Base: `1e42b2565c95d496d658200dbafb040d7f74f39d`.
Status: TESTED SOURCE/API; live App and J4/J5/J6 remain unaccepted.

## REAL DELIVERY CARD / 真实用户工作闭环验收

The existing Experience API and Skill executor now carry the sealed local
principal to the accepted Permission and Artifact owners. Users select one media
file, review its exact confirmation, retry those same bytes, edit a timeline,
export, download/reopen the saved project and create a separate revision.
No account or general COMMIT grant is manufactured. Source checks still bind
actual observed bytes, filename, size and CTH/BMP context; change/cancel/expiry
cannot silently authorize another import.

Routes reused from the frozen Content candidate and adapted to current main:

- POST `/api/experience/content-sources` (bounded octet-stream, explicit WRITE).
- POST `/api/experience/content-source-confirmations/<id>` (confirm/cancel).
- GET `/api/experience/content-sources/<id>` (scope-checked read).
- POST `/api/experience/content-projects/export` (explicit EXPORT).
- GET `/api/experience/content-projects/<id>` plus `/package` and `/media`.

The global write guard delegates only the exact registered three POST handlers;
their existing Permission/Firewall/Effect Fence/Artifact chains perform the
resource-specific decisions. Path lookalikes remain blocked. Existing settings
context delegation is unchanged. Cross-origin browser writes are rejected;
native requests without Origin still need the server's local transport policy.

Execution serialization excludes the principal before deep-copy traversal;
handler entry rechecks the original descriptor/principal and live permission.
Media ownership and source rights remain separate; no publication is performed.

## Proportional verification and recovery

Root's final source/API/execution/inspection group: **35 passed in 25.33s, exit 0**.
It uses a disposable real SQLite store with `v4_users` removed, strict Permission,
real signed execution Evidence and actual FFmpeg/ffprobe. Tests cover file
confirmation/import, approval consumption, changed bytes, cancel/retry, hostile
origin/forwarded transport, oversize cleanup, real WAV export/package/media,
new-client reopen, separate revision preserving old bytes, cross-domain denial,
workspace closure/reopening, render failure and explicit retry.

Changed executor compatibility group: **78 passed in 4.49s, exit 0** (existing
content source execution, skill result states, account scope and new local
principal execution). No background-thread leaks. All tests selected an explicit
external disposable seed, never the active product DB. The earlier first API
test failure was a test's omitted `Timeline.from_dict(assets=...)` argument;
it was fixed and the whole group rerun to the successful result above.

AST, scoped diff check and Constitution are checked on final source. App process
restart and visible Web workflow are next; test-client operation does not prove
the currently running product has loaded the routes. Production data was not
modified by these checks. Restart persistence is separately proven by the
accepted Artifact evidence, not inferred from a second test client.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: no coverage change.
COMMERCIAL OVERLAY IMPACT: actual creative quality, rights, four surfaces,
release and operating acceptance remain pending.
CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: current Flask boundary and
existing accepted Content candidate reused; no new architecture or dependency.
