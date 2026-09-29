# Exact content-source confirmation — existing Permission integration

Status: IMPLEMENTED / TESTED; REAL USER WORK E2E NOT VERIFIED.
Base accepted main: `2a603207136a87ef99947b613c4e8671500cebce`.

## Scope and result

Root selected the frozen Content candidate's existing Permission slice, not
the whole candidate. Five paths: `lumenis/system/security/permission.py`, its
`__init__.py`, `test_content_source_import_permission.py`,
`test_permission_scope_approval_binding.py`, `test_permission_exact_resource_scope.py`.

The server constructs the immutable file descriptor. Confirmation binds the
exact name, size, SHA-256, actor, domain and GLOBAL/Subject/BrandFocus scope.
It expires, can be cancelled and cannot be replayed for another file or actor.
Permission keeps the nonce/grant in its own bounded memory, never raw file
bytes. The exact import grant does not grant general COMMIT or DB-write powers.
Live scope and approval are rechecked; tests cannot authorize production import
by turning on a bypass flag. Existing authenticated scope checks and anonymous
loopback read policy were preserved exactly.

Root found a concrete cleanup defect: removing an expired restricted grant
could leave a still-live underlying approval available to another ordinary
DB-write caller. A failing regression reproduced it. Cleanup now revokes the
underlying approval before removing its restriction. The final test passed.

## Verification history and current result

- First neighboring run: 242 passed / 3 failed, exit 1. The same three failures
  occurred with unmodified HEAD Permission loaded in a disposable process.
- The existing Evidence API fixture lacked current signing/schema setup and
  changed signed rows directly with SQL. It now configures a public test-only
  HMAC key and canonical Evidence schema, and creates the NULL sample through
  the writer initially. All 67 original assertions were verified unchanged.
- The restricted-grant cleanup regression failed before the fix (one failed),
  then passed with capacity-recovery coverage. Earlier results were superseded.
- Final exact snapshot: **273 passed, exit 0**, across source-import permission,
  scope-approval binding, local-workspace read, exact resource scope, permission
  gate and dual-domain permission tests. File hashes matched before/after.
- Connection instrumentation recorded 419 SQLite opens, all in disposable
  temporary paths; zero production connections and zero thread leaks.
- Root inspected the source, fixture diff and exact final hashes; scoped diff
  check passed. No staging or Git operation was delegated to the worker.

Final SHA-256 values (in path order above):

```text
ea813130a1e20f17a2ed59ada6fe9684eb787bd22329263977489f1a143110e2
7e1f5fdf8bf56fa52aea03437dd0eb5883674497ffefdca874f582b6ec3f6299
7288914fb568bcbbe214b4f6fc7b0b847a6ef3ffded253d56b96cdeeb9b8cedc
f311412c00cb564e6f80ca3a9fcd8e78a6b5b27acb93602ca2645d2d479dcc74
de1cb85332d9a2f373bf0bbb730d8bbc1de0452d90f63392591230275eac2e52
```

## REAL DELIVERY CARD / 真实用户工作闭环验收

Job: import the user's chosen media into the intended work context after an
explicit, revocable confirmation. This Batch proves the Permission decision and
recovery states using explicitly labelled account fixtures. Actual API upload,
the Artifact handler's successful insert/approval consumption, local workspace
principal, edit/render/reopen and user review remain dependent work. No product
account provisioning, Cookie access, real approval, DB migration or runtime
restart occurred. J4/J5/J6 and ROUND 04 remain unaccepted.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: reuse current Permission
and the frozen reviewed Content candidate, with a demonstrated lifecycle repair;
no extra package or permission system. COMMERCIAL OVERLAY IMPACT: approval to
import a local file does not grant media reuse or distribution rights.
RELEASED / OPERATING / COMMERCIAL_READY remain NO.
