# ROUND 06 — approved Douyin worker and real search capture

Base 04021331. Existing SYSTEM Collector delegates to its current Douyin adapter.
No new collector, browser engine, account owner or database. Explicit DOUYIN_READONLY
worker uses the actual system default Chrome on loopback 9225 and a dedicated
private profile. Registered process/profile/bind/port must match before reuse.
Unknown local endpoints and CN/HK account ports cannot be reused for this worker.
Default resident launch does not silently activate Douyin. User-supplied Cookie
attachment was imported through the existing ignored local vault with private ACL;
no Cookie, token, profile or credential is committed.

The real official search response contains data[].aweme_info plus non-video cards.
Existing item parsing handled it. The old search reported successful empty when no
verified response had arrived. It now requires a successful explicit empty response
for NO_NEW_DATA; otherwise reports failure. Using ordinary browser pages without
navigator/runtime patching produced actual SYSTEM search SUCCESS with 3 Guangzhou
Taikoo Hui records in 20.26s. Title, author, publication date, URL and four metrics
were returned. This single comparison supports the ordinary-page route; it does
not prove every network/timing failure is resolved. Search author ID now passes
through to SYSTEM items. Missing metrics remain NULL and observed zero remains 0.

Verification: agent focused 43 tests exit 0; root rechecked the three new worker,
response-shape and capture test files in the combined candidate: 26 tests exit 0,
no background-thread leaks. All six changed Python files parse successfully.

REAL DELIVERY CARD / 真实用户工作闭环验收: real read-only search through the actual
SYSTEM adapter succeeded. Subsequent isolated exact-scope persistence returned
IMPORT_FAILED; its Raw import blocker is being fixed separately. No product DB
write or completed user-visible workflow is claimed in this batch. Permission,
Canonical/native field persistence, business result and UI E2E still need proof.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: ADAPT actual official response
and ordinary authenticated browser behavior, preserve source-native fields; no new
dependency and no challenge bypass. COMMERCIAL OVERLAY IMPACT: rights and launch
not promoted. GLOBAL UNIVERSE / DATA MATURITY IMPACT: Global Commercial/Brand NO,
Guangzhou PARTIAL; ROUND 06 REWORK; Full Universe/RELEASED/OPERATING/COMMERCIAL_READY NO.
