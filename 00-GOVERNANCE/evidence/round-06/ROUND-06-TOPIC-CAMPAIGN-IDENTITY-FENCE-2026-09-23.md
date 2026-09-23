# ROUND 06 — legacy topic campaign identity fence

Status: **PASS FOR BOUNDED SAFETY BATCH / ROUND 06 SPLIT, NOT ACCEPTED**
Observed: 2026-09-23 (Asia/Shanghai). Source base: `d621a9cc0854d184179f59f68c4d050a85976f5c`.

## Scope and decision

The legacy `topic_campaign.py` collection, health, recovery and detail-backfill paths could default to the personal Mainland XHS browser on port 9222 or an old profile. The source owner map assigns this caller to ROUND 06. This Batch fences that caller before browser, profile, Cookie, CDP or collector subprocess access. Its policy check accepts only the explicit `XHS_RETINAUT` / `intl` route at `http://127.0.0.1:9223`; automatic runs also require `REDNOTE_AUTO_RUN=true`. The legacy worker and backfill still target the Mainland site, so even the approved HK configuration returns `CANONICAL_COLLECTOR_BINDING_REQUIRED`. No campaign collection is represented as successful.

Manual run, scheduler startup/loop, direct worker, runtime health, recover, half-open probe, backfill and APP-topic entry paths now fail closed. The status API reports the blocked or unavailable runtime state instead of circuit-derived apparent health. Existing read-only campaign records remain readable. App registration still initializes its existing campaign storage; this Batch does not accept that storage or connect it to a new owner.

Sol inspected the exact two-path patch and rejected an earlier broad endpoint rule and an unrelated regex change. The final patch SHA-256 was `69776CF4C72716B7977C7BCE9EAF8DA1F8BEC03305A03C2DA7BA49716AFCAF45`. It applied cleanly to the current index and working tree; only `topic_campaign.py` and `tests/test_topic_campaign_identity_fence.py` were staged.

## Verification

Sol replayed the final patch in a clean `d621a9cc` Git archive under an OS temporary directory. That archive contained no `data/monitor.db`. With `ZBC_DB_PATH` directed at a disposable path, `LUMENIS_TEST_SEED_DB` cleared, and no browser/network/collector invocation, 9 fence and source-only tests passed; the neighboring canonical RedNote policy suite passed 5 tests. `py_compile` passed and the test runner reported no background-thread leak. Tests covered missing and hostile endpoints, exact HK config remaining unavailable to the old worker, policy auto-run gate, no forbidden side effects, route status truth, half-open serialization and no scheduler launch on missing endpoint. The disposable DB path was not created.

The protected `data/monitor.db` remained 1,458,176 bytes, UTC mtime `2026-09-21T20:03:21.3668965Z`, SHA-256 `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45`; WAL/SHM sidecars were absent. No protected SQLite connection, Mainland XHS account, Cookie, session, profile, CDP endpoint or platform request was used.

## Real delivery and next owner work

**REAL DELIVERY CARD / 真实用户工作闭环验收:** A CTH operator cannot use this legacy topic campaign to collect a new real result yet. The truthful user-visible state is blocked or unavailable; no Source → Evidence → Canonical Data → action/outcome E2E is claimed. The next independent SYSTEM Collector/Browser Batch must bind campaign and detail collection to the canonical authorized HK route, prove source identity, Evidence, Permission, scheduling, failure/recovery and a real user result, then run authorized runtime acceptance without touching the personal Mainland identity. ROUND 06 remains `SPLIT / REWORK`; ROUND 03 and the fifteen-checkpoint order are unchanged.

**GLOBAL UNIVERSE / DATA MATURITY IMPACT:** This fence adds no commercial or brand coverage. Global Commercial Coverage and Global Brand Coverage remain `NO / NOT VERIFIED`; Guangzhou Taikoo Hui reference coverage remains `PARTIAL`; `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`.

**COMMERCIAL OVERLAY IMPACT:** Source rights, retention, approved session governance and live operation are still open; `COMMERCIAL_READY=NO`. No new dependency, account, paid service or production-data migration was introduced.
