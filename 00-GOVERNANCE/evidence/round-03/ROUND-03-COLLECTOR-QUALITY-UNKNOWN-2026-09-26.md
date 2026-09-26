# ROUND 03 — Collector quality missing-count truth

Sol decision: PASS FOR BOUNDED DATABASE BATCH / ROUND EXIT NOT ACCEPTED. The existing database.save_collector_quality writer now inserts SQL NULL when comments_collected is omitted, None or blank, and retains a measured zero. This uses the existing canonical DatabaseRepository and collector_quality_log; no table, migration or second data owner was added.

## Exact scope and verification

- Base: fetched main and origin/main at be15d5927bb70a157af51bef6e1f60d7e446c8db. Exact source/test paths: database.py and tests/test_database_collector_quality_missing.py. Sol replayed the Luna patch on a clean archive of that main; the shared dirty database.py and tests were never overwritten or broadly staged.
- The current schema declares collector_quality_log.comments_collected INTEGER DEFAULT 0 without NOT NULL. The writer explicitly supplies NULL for unknown values, so the schema default does not replace it. A disposable database test checks omitted, None, blank, measured zero, numeric input and rejected invalid text. Sol ran this test with neighboring canonical database regressions: 25 selected tests passed, exit 0, no background-thread leak. Compilation, database authority and AI-native constitution gates passed.
- The protected data/monitor.db was not opened or migrated. SHA-256 remained A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45. No XHS module, Cookie, session, profile or browser runtime was used.
- Source review found app.py and live_engine.py quality-log callers can still supply a fabricated zero before this writer receives the value. This Batch cannot recover a missing count that an upstream caller erased; those paths remain open.

## REAL DELIVERY CARD / 真实用户工作闭环验收

REAL USER JOB: see whether comment collection quality was actually measured. ENTRY: canonical collector-quality write. REAL INPUT: synthetic missing/blank and observed numeric values in an isolated database. END-TO-END PATH: caller quality dict -> canonical writer -> collector_quality_log readback. USER-VISIBLE RESULT: none through a running product ViewModel or page. FAILURE/RECOVERY: invalid numeric text raises before a row is written; source callers must retain unknown state for a later retry/observation. EVIDENCE: 25 selected database tests and blocking static gates. ACCEPTANCE ASSERTION: this database-owner Batch passes only; approved live source -> Evidence -> Canonical -> user-visible quality decision E2E remains unverified. ROUND 03 stays REWORK.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: no new source/entity coverage. Global Commercial Coverage=NO; Global Brand Coverage=NO; Guangzhou Taikoo Hui Reference Coverage=PARTIAL / NOT REVERIFIED; LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO. Random canonical entity sample count is zero for this isolated persistence Batch.

COMMERCIAL OVERLAY IMPACT: COMMERCIAL_READY=NO. A database readback is not a completed commercial monitoring task.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: SQLite's official CREATE TABLE documentation (accessed 2026-09-26; https://www.sqlite.org/lang_createtable.html) explains that explicit column values and defaults have different effects; its NULL documentation (https://www.sqlite.org/nulls.html) treats NULL distinctly from numeric values. Decision ADAPT: use explicit NULL in the existing writer for unobserved counts. No new dependency was adopted. Targeted tests and normal mainline revert provide validation and rollback; live promotion still needs source and user-result checks.

NEXT DEPENDENCY: remove remaining missing-to-zero conversions in current app and live quality-log callers, preserving international XHS identity protection, then prove the real user-work E2E.
