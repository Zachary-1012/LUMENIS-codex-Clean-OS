# ROUND 04 — XHS live side-write database path

Sol decision: `PASS FOR BOUNDED BATCH / ROUND 04 EXIT NOT ACCEPTED`. This Batch binds the existing XHS live Evidence and Canonical side-writes to the Shared Database owner's call-time `main_db_path()`. It does not start collection, validate an account, or accept a real user workflow.

## Exact source and verification

- Base: fetched `main` `b4ea810dc6979e6df7df8884ca924131caf67e15`, also the live `refs/heads/main` before staging. The isolated Luna patch SHA-256 is `1A1BE72F5472FDFE79946EC9DB4A6CD66EE21C9F0FF8C6586631A7D42522CE81`. Accepted source paths: `lumenis/system/collector/runtime/xhs/live_engine.py` and `tests/test_xhs_live_db_path.py`; unrelated dirty work remains unstaged.
- Primary note insertion already resolves the database through the repository at call time. EvidenceChain, Canonical table initialization and Canonical connection had read stale import-time `database.DB_PATH`. The patch resolves the Shared owner path at each side-write invocation, preserving the existing nonfatal side-write and source identity behavior.
- Sol independently replayed the exact patch on a clean `HEAD` archive and disposable database. `py_compile` exited 0. `python -m pytest -q -c pytest.ini tests/test_xhs_live_db_path.py tests/test_shared_database_owner.py tests/test_evidence_chain.py` passed 62/62, exit 0. The mock-only new test switches `ZBC_DB_PATH` after import and asserts Evidence and Canonical use the new path; it does not import or run the browser/collector runtime.
- The protected `data/monitor.db` remained 1,458,176 bytes with SHA-256 `A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45` at prepublication verification. No production database or personal Mainland XHS account, Cookie, session, profile or CDP endpoint was opened or changed.

## REAL DELIVERY CARD / 真实用户工作闭环验收

`REAL USER JOB`: retain an authorized source note's Evidence and Canonical record in the selected business database. `ENTRY`: existing SYSTEM Collector live note persistence caller. `REAL INPUT`: a mock note and a call-time isolated database selection. `END-TO-END PATH`: note → primary repository write → Shared Evidence and Canonical side-write path; only path selection is tested. `USER-VISIBLE RESULT`: no real App result or reopened record verified. `FAILURE/RECOVERY`: side-writes remain nonfatal and do not claim success on exception. `EVIDENCE`: clean staged replay, 62/62 focused and neighbor tests, static compile and protected DB fingerprint. `ACCEPTANCE ASSERTION`: caller-path parity passes as a bounded Batch; real user-work E2E is absent, so ROUND 04 remains unaccepted.

`GLOBAL UNIVERSE / DATA MATURITY IMPACT`: no new business entity coverage. Global Commercial Coverage=`NO`; Global Brand Coverage=`NO`; Guangzhou Taikoo Hui Reference Coverage=`PARTIAL / NOT REVERIFIED`; `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`. Random entity sample count is zero for this path-binding Batch.

`COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO`; authorized live acquisition, correct subject mapping, real Evidence/Canonical persistence, user-visible outcome and failure recovery remain open.

`CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION`: [W3C PROV-DM](https://www.w3.org/TR/prov-dm/) (accessed 2026-09-24) supports retaining source-to-derived lineage; decision `ADAPT` through the existing Evidence owner, no new dependency. [OpenLineage](https://github.com/OpenLineage/OpenLineage) (accessed 2026-09-24, Apache-2.0) is `DEFER` because this fix is an existing local owner binding. The patch is reversible through mainline history; real source evaluation remains outstanding.

`NEXT DEPENDENCY`: authorized source input through Evidence and Canonical to a user-visible report, with exact Permission and subject scope, then real user-work E2E.
