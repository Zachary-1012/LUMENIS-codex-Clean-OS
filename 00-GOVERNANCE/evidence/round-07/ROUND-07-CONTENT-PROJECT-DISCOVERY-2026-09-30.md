# ROUND 07 — scope-safe saved-project discovery

Base: `a307b8b8117b17db9c9e072166048fc453c98144`.
Status: TESTED source/API; running-Core list update and visible E2E pending;
J4/J5/J6 unaccepted.

## REAL DELIVERY CARD / 真实用户工作闭环验收

Users need to find and reopen saved work without copying an internal Artifact
identifier. The existing Artifact owner now provides `list_content_projects`;
GET `/api/experience/content-projects` applies the same exact Context and
Permission boundary as opening a project. The API returns verified minimal
metadata and a continuation cursor. The independent frontend task binds these
rows to its existing reopen operation.

This is a read-only path through the existing repository/table. It does not
initialize schema, create another library, transfer account ownership to the
open local workspace, or infer source rights. Account actors and the server's
local workspace principal retain separate exact ownership checks.

## Boundaries and recovery

- Every returned project passes the existing archive/hash/context verification.
- Foreign scopes/accounts do not expose project IDs, names or result counts.
- Keyset ordering is stable on creation time and Artifact ID; opaque cursors are
  bound to caller/scope and held in bounded process memory.
- One page scans at most 100 candidates and at most the existing single-package
  byte ceiling. `scan_incomplete` with continuation does not claim an empty list.
- Missing or corrupted packages return `integrity_incomplete` without leaking
  unverified metadata. A fresh listing can rediscover a restored package.
- Restart/eviction invalidates a cursor explicitly; refreshing from the start
  rediscovers durable projects. Cursors themselves are not durable user work.
- Workspace closure, hostile request origin and foreign forwarding remain
  denied. Reopening the workspace restores authorized reads without an account.

The worker's first combined run exited 1 because adjacent storage tests lacked
FFprobe configuration; nine listing tests passed within that failed invocation.
It is not final acceptance. Root's final frozen five-file integration group
passed **96 tests in 100.33 seconds, exit 0**. The enclosing snapshot check also
exited zero with all ten watched source/test hashes unchanged and no background
thread leak. It used the verified binaries and an explicit disposable DB seed.
API verification includes a
real WAV import/export and new-client discovery/reopen, not only synthetic list
rows. The separate live-media report records actual user input and process
restart; the new list endpoint still needs the controlled running-Core update.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: no change.
COMMERCIAL OVERLAY IMPACT: discoverability advances; creative quality, final
visible E2E, all J packages, release and operating remain unaccepted.
CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: reuse the accepted Artifact
integrity/context verifier and existing Flask boundary; no new dependency.
