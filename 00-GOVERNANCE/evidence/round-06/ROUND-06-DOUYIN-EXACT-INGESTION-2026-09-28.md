# ROUND 06 — real Douyin ingestion into both product domains

Base: e61348f5. Reuses SYSTEM Collector, canonical Cookie vault, Permission,
Raw/Evidence/Canonical/native-field owners; no new database or login authority.

- Human DATA_IMPORT approval binds the exact platform/query/domain/entity.
  It is checked before collection and again before write. Testing bypass and
  public maintenance service authorization cannot activate this social path.
- Actual numeric create_time becomes UTC ISO publication time; native integer
  is preserved. Missing never uses capture time. Invalid numeric values fail.
- Actual uid is preserved when sec_uid is absent; it is not relabeled sec_uid.
- Completed request bodies are read on Playwright requestfinished, not headers.
  Official semantics: https://playwright.dev/python/docs/api/class-request
  (accessed 2026-09-28; installed Playwright 1.62.0; ADAPT existing owner).
- The live hang was separately localized to CDP attach on old heavy targets.
  Closing only two root-owned targets recovered the same connection. Explicit
  Douyin startup now opens about:blank; no unknown/personal target is closed.

## Real input and durable result

Disposable product clone first passed CTH Guangzhou Taikoo Hui 3 + BMP Nike 3.
Actual DB was backed up with SQLite backup before write; durable private copy
is under ignored data/backups/douyin-first-import-20260928. Two fresh-process
manual runs then exercised real authorized platform search and real persistence:

| Product state | First run | Immediate second run |
|---|---:|---:|
| CTH imported / updated | 3 / 0 | 0 / 3 |
| BMP imported / updated | 3 / 0 | 0 / 3 |
| Douyin Raw / Canonical / native | 6 / 6 / 6 | 6 / 6 / 6 |
| Signed Douyin observation Evidence | 2 | 2 |
| Total Canonical | 226 | 226 |

Both domains returned refresh_verified=true and VERIFIED exact scope. All six
saved rows have source author ID, actual publication time, URL and observed
engagement values; their scope Evidence signatures verify. CTH/BMP IDs stay
separate. Product DB schema remains 18, integrity OK and FK violations 0.
No Cookie, token, private profile or product database is committed.

## Verification and limits

54 focused isolated-seed regressions passed, exit 0, without thread leaks.
After the startup URL change, all 26 worker-routing regressions passed again.
One initial shared test invocation lacked explicit isolated seed and was refused
by the protected-DB sidecar gate; the corrected invocation used a disposable
v18 seed. The guard was not changed and product DB was not used as a test seed.
All seven staged Python files parse. Protected unrelated secondary_collection
working-tree candidate remains untouched; only the exact accepted patch is staged.

REAL DELIVERY CARD / 真实用户工作闭环验收: source-to-product persistence is live
verified for these six records. User-operated page/result/report, comments/replies,
creator depth and unauthenticated parity are not accepted. No whole-platform PASS.
GLOBAL UNIVERSE / DATA MATURITY IMPACT: Global Commercial/Brand NO, Guangzhou
PARTIAL, Full Universe NO. COMMERCIAL OVERLAY IMPACT: rights/release unchanged.
ROUND 06 REWORK; RELEASED / OPERATING / COMMERCIAL_READY remain NO.
