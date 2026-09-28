# Round 04 — Global / Focus context API selection slice (2026-09-26)

## Current source and scope
- Base: `149be0a123b792cb746358ec9a7371fcea332900` on local/remote/live main before this Batch.
- Owner: existing Product Core `lumenis_app_api.py`, `subject_context.py`, canonical `subject_registry.py`, and existing actor-to-resource Permission.
- Adds `GET/PUT/DELETE /api/settings/context` matching the existing Flutter `lumenis.context.v1` selection contract. Default and clear return `GLOBAL_ALL`; Focus resolves one registered CTH Subject or BMP BrandFocus. BMP keeps the existing client `subject_id` envelope but authorizes the canonical `brand_focus_id`.
- Focus is a selection and never a Permission grant, Evidence, Canonical Data, or collector trigger. Missing/invalid/unauthorized focus fails explicitly. No UI, DB schema, collector, model configuration, or production data change.

## Verification
- Candidate source files were checked against the exact base Git blobs before review. Sol inspected the precise diff and removed a request-local `g` assignment that had no downstream consumer.
- Candidate `py_compile`: exit 0.
- Sol replayed `python -m pytest -q tests/test_settings_context_api.py tests/test_permission_exact_resource_scope.py tests/test_request_domain_context.py tests/test_subject_registry.py -k 'not hk_cookie_apply'` on the isolated exact candidate: exit 0, 51 passing test points, no background-thread leaks. Tests use disposable SQLite and stub only authenticated actor retrieval.
- `python scripts/audit_tools/verify_ai_native_constitution.py`: PASS on the clean candidate. The `hk_cookie_apply` case was excluded to preserve the Product Owner's personal XHS identity boundary; it is not a passing result for that case.

## Current status and remaining work
- This is `IMPLEMENTED + TARGETED_TESTED` for the selection API only. It does not establish a persistent global universe or prove that business data routes bind Focus and reauthorize every read.
- The inspected product DB snapshot was schema v13, while focus registry reading requires migrated v15+; no production migration was attempted. Global Commercial Coverage = NO / NOT VERIFIED; Global Brand Coverage = NO / NOT VERIFIED; Guangzhou Taikoo Hui Reference Coverage = PARTIAL / NOT REVERIFIED. `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`.
- Real user-work E2E, Global and Focus evidence-backed data, random CTH/BMP entities, clear-to-Global on all promised surfaces, continuous collection, and recovery remain open. ROUND 04 remains REWORK; COMMERCIAL_READY=NO. This Batch must not be cited as Round PASS or operating proof.

## 2026-09-28 — allow the no-focus selection without an account wall
- On base `f8927655ca550ccf43673eb2290bbe4b77d35856`, the selection-only `GET /api/settings/context` with no focus and `DELETE /api/settings/context` now return the static `GLOBAL_ALL` envelope without requiring an Actor. These operations expose no business data and perform no persistent or external effect.
- `FOCUS` `GET` and `PUT` still use `_context_selection_from_scope`, which requires a real Actor and exact subject/brand-focus read permission. Unauthenticated Focus remains `401 AUTH_REQUIRED`; data routes keep their existing independent authorization.
- Isolated Flask route probe: unauthenticated Global GET = 200, clear = 200, Focus GET = 401. `tests/test_settings_context_api.py` passed (6 tests, no daemon-thread leak); Python source compilation and `git diff --check` passed. No real-user browser E2E was run in this correction.
- This is a narrow access correction to the existing selection contract only. It does not change the Global data-coverage statuses above or close ROUND 04.
