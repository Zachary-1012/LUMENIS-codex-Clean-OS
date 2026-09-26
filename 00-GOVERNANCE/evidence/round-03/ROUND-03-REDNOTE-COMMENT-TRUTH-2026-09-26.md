# ROUND 03 — RedNote comment truth at the collector caller

- Base: `9788507840998d44fcb9c63b001bba6cbed1ced1`, fetched from `origin/main` on 2026-09-26.
- Owner: existing RedNote collector caller → `app.py::persist_rednote_data` → canonical `database.py` writer. No new owner, schema, or runtime.
- Change: a failed detail read now passes `NULL` for post comments, loaded comment count and collector-quality count. Successful detail reads keep the number of loaded `.comment-item` records, including observed zero. The broad `.count` selector is not semantically identified as post comments, so it can no longer populate `notes.comments`. The existing database writer retains a previous measured value when the new value is `NULL`; measured zero can update it.
- Sol rework: the first candidate still treated the last generic `.count` as comments. Sol rejected it; only the revised patch was replayed on an independent exact-base archive.
- Verification at the revised current snapshot: Node producer tests 4 passed; Python persistence/disposable-DB and neighboring database tests 4 passed; CJS syntax, Python compile, and `verify_ai_native_constitution.py` PASS. The disposable DB proved unknown insert `NULL`, unknown update retained measured `12/7`, and observed zero updated to `0/0`. No production DB was opened for SQLite.
- External principle check: SQLite's expression contract treats `NULL` as distinct from numeric zero; a `NULL` comparison in a `CASE WHEN` is untrue, matching the existing retention rule. [SQLite expression reference](https://www.sqlite.org/lang_expr.html), accessed 2026-09-26. Decision: ADAPT within the existing owner; no new library or runtime justified.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

- REAL USER JOB: a CTH or BMP operator inspects a collected note and can trust that an unavailable comment total is not shown as zero.
- ENTRY / REAL INPUT: an authorized Hong Kong or international RedNote collection, with an actual detail success or failure. No identity was exercised in this Batch.
- END-TO-END PATH: real source → Collector → Evidence → Canonical note and quality record → ViewModel → user-visible state. Only the producer/caller/disposable persistence slice was verified.
- USER-VISIBLE RESULT / FAILURE/RECOVERY: not live-verified; real collection, Evidence lineage, ViewModel and user recovery still require proof.
- EVIDENCE / ACCEPTANCE ASSERTION: source tests and disposable DB above are `TESTED`, not real user E2E. `ROUND 03=REWORK`; no Round PASS.

## COMMERCIAL OVERLAY IMPACT

`COMMERCIAL_READY=NO`. A truthful stored comment state improves one input; full delivery, continuous running and human acceptance remain open.

## GLOBAL UNIVERSE / DATA MATURITY IMPACT

This Batch adds no entity or source coverage. Global Commercial Coverage `NO`; Global Brand Coverage `NO`; Guangzhou Taikoo Hui reference `PARTIAL / NOT REVERIFIED`; `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

Research complete / no justified dependency upgrade. The next bounded capability issue is `detail_fetched_at` fallback to current time on failed detail, which needs its own provenance fix. This Batch did not run the collector or touch any account, Cookie, session, browser profile, production DB or external effect.
