# ROUND 04 — exact Subject and BrandFocus Permission decision

Sol decision: `PASS FOR BOUNDED PERMISSION OWNER BATCH / ROUND 04 EXIT NOT ACCEPTED`. The SYSTEM Permission owner can now decide an authenticated actor's exact CTH Subject or BMP BrandFocus scope. This source API is a prerequisite for separate route bindings; a context header or domain grant alone remains insufficient.

## Exact source and verification

- Base: fetched `main` `6396fac263cee9ee4157ff37c8ff972af5759abf`. Isolated candidate patch SHA-256 `47E1C84312931E923C2414D6727F6F347846374F2BBE58D201726AAD51460743`. Exact staged paths: `lumenis/system/security/permission.py`, `lumenis/system/security/__init__.py`, `tests/test_permission_exact_resource_scope.py`; broader dirty Permission/Context work remains unstaged.
- The checker loads active role and grants from existing account owners, validates CTH `subject_id` or BMP `brand_focus_id` against the existing registry, and requires explicit `data_scope` for non-owner/non-admin actors. `GLOBAL / ALL` requires an explicit global grant. Unknown actor, malformed scope, missing resource, unavailable owner, and unsupported nonempty time-window grants deny. It returns the decision and an existing PermissionGate audit identifier without creating a second Permission owner.
- Sol replayed the exact staged patch on a clean current-main archive and passed 148/148 exact-scope, PermissionGate, dual-domain and Subject Registry tests, exit 0, with no daemon-thread leak. The baseline neighboring suite passed in the worker's isolated archive; the current-snapshot static/governance checks are recorded at publication. No real account, production DB or external effect was used.
- The existing `PermissionGate._write_audit` keeps memory audit with optional file persistence; this Batch does not prove durable audit persistence. A missing audit identifier or checker exception denies, but file-write failure handling remains governed by that existing owner and is an explicit later release check.

## REAL DELIVERY CARD / 真实用户工作闭环验收

`REAL USER JOB`: let a permitted operator focus a specific commercial Subject or brand without exposing another entity's work. `ENTRY`: future Product Core route using the canonical checker. `REAL INPUT`: disposable actor/grant/registry fixtures across CTH and BMP. `END-TO-END PATH`: account role/grant → exact registry identity → Permission decision → audit result. `USER-VISIBLE RESULT`: none verified; production context routes are not yet bound. `FAILURE/RECOVERY`: denied or unavailable decisions return without granting a scope; later route tests must show the user's blocked/retry state. `EVIDENCE`: 148 clean replay tests and the exact staged source. `ACCEPTANCE ASSERTION`: Permission owner API passes as a bounded Batch; ROUND 04 and real user-work E2E remain open.

`GLOBAL UNIVERSE / DATA MATURITY IMPACT`: focus selection remains a view choice and never grants Permission or changes background collection. Global Commercial Coverage=`NO`; Global Brand Coverage=`NO`; Guangzhou Taikoo Hui Reference Coverage=`PARTIAL / NOT REVERIFIED`; `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`. Random real-entity sample count is zero for this Permission-only Batch.

`COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO`. Route-level enforcement, durable audit behavior, real authorized/denied user sessions and cross-surface recovery are unaccepted.

`CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION`: [OWASP Authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), accessed 2026-09-24, recommends deny-by-default and per-request resource checks (`ADAPT` within SYSTEM Permission). [PyCasbin](https://github.com/apache/casbin-pycasbin), Apache-2.0 OSS reviewed 2026-09-24, is `DEFER`: adding another policy runtime now would split the canonical owner without evidence of a need. No dependency was added. Rollback is the mainline source commit; grants and registry data are untouched.
