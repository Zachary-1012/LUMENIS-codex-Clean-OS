# ROUND 03 — XHS caller missing comment-count truth

Sol decision: PASS FOR BOUNDED SOURCE BATCH / ROUND EXIT NOT ACCEPTED. Two existing collector callers no longer invent zero when a source omits the comment-collection count. They pass the raw absent or observed value into the already-owned database.insert_note nullable metric boundary. No alternate data owner, helper, table, collector runtime or browser behavior was added.

## Exact scope and verification

- Base: fetched local main and origin/main at 7a60e0aa6cb0ad98c42c8776978c2ce2a5277a0b. Exact source paths: collector_automation.py and lumenis/system/collector/runtime/xhs/live_engine.py. A wider Luna candidate duplicated a metric normalizer in each caller; Sol rejected that candidate and replayed only two direct pass-through expressions on a clean main archive. The shared dirty worktree was not reset, overwritten or broadly staged.
- A source-only AST check verified both expressions pass the source field with no zero default. The existing canonical database comment-count and database tests passed 8/8 on a fingerprint-matched disposable database copy; compile checks and the AI-native constitution gate passed. No XHS module was imported and no collector, profile, Cookie, CDP port or session was touched. The protected data/monitor.db SHA-256 remained A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45.
- The existing database.insert_note normalizer keeps an absent or blank count NULL, preserves prior measured values on update, and retains explicit zero. The separate save_collector_quality quality-log call still converts a missing count to zero; this Batch does not claim that downstream quality audit fixed.

## REAL DELIVERY CARD / 真实用户工作闭环验收

REAL USER JOB: distinguish an uncollected comment count from a measured zero in a commercial monitoring record. ENTRY: existing approved international XHS collector source paths. REAL INPUT: static source-only and disposable database test data, not a live social account. END-TO-END PATH: source count field -> caller record -> canonical insert_note contract. USER-VISIBLE RESULT: no running UI result was verified. FAILURE/RECOVERY: missing count stays unknown at the source-to-DB boundary; invalid actual source values remain subject to the existing DB write error path. EVIDENCE: AST, 8/8 database tests, compile and constitution gates. ACCEPTANCE ASSERTION: the preparatory caller Batch passes; live approved-identity source -> Evidence -> Canonical -> ViewModel -> user result remains unverified, so ROUND 03 stays REWORK.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: no new entity or source coverage. Global Commercial Coverage=NO; Global Brand Coverage=NO; Guangzhou Taikoo Hui Reference Coverage=PARTIAL / NOT REVERIFIED; LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO. Random canonical entity sample count zero for this source-only Batch.

COMMERCIAL OVERLAY IMPACT: COMMERCIAL_READY=NO. No user-visible work, random entity acceptance or production comment-count audit was run.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: SQLite's official CREATE TABLE and NULL handling documentation (accessed 2026-09-26; https://www.sqlite.org/lang_createtable.html and https://www.sqlite.org/nulls.html) distinguishes absent/NULL values from recorded numeric zero. Decision ADAPT: preserve that distinction through the existing canonical database owner. No external dependency, new model or collection capability was adopted. Rollback is a normal mainline revert; live validation still requires the approved international identity and current Permission/Evidence gates.

NEXT DEPENDENCY: source-only audit and correction of the remaining quality-log and app-level missing-count conversions under their current owners, followed by real approved-identity E2E only when safe and authorized.
