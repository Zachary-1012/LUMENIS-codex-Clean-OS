# Content source import — existing Skill execution integration

Status: TESTED SOURCE / PRODUCT USER E2E NOT YET VERIFIED.
J4/J5/J6 and ROUND 07 remain unaccepted.

## Bounded implementation

The frozen Content candidate's existing Skill execution owner now accepts a
server-created immutable import descriptor and an opaque request context.
Client payloads cannot set either object or select a different effect target.
The descriptor must match the enabled Shared content skill, actor, CTH/BMP
domain and WRITE action. The existing Permission check runs again immediately
before the handler, after Action Firewall and Effect Fence admission.

Denied/revoked/replaced descriptors never call the import handler. Their
Permission audit remains; rejected/failed source imports do not write successful
Artifact/Evidence/Skill trace records. Successful imports continue through the
existing result, Evidence and trace owners; the owning Artifact handler must
still consume the exact approval after insertion. This Batch does not add that
handler or claim a real persisted import has occurred.

Root additionally excluded both server-only fields before dataclass traversal,
so even an opaque non-copyable request context cannot be copied or serialized.
The import-time Skill-table initialization was moved into the existing trace
write path; importing the module does not initialize account/trace persistence.

## Verification

Root ran these three files together on the integrated local source using an
explicit disposable seed (not the active product DB):

- `tests/test_content_source_execution.py`
- `tests/test_skill_execution_result_state.py`
- `tests/test_account_skill_execution_scope.py`

All 70 tests passed, exit 0, with no thread leak, and were rerun successfully
after Permission base `984df36f` (including grant cleanup) was published. Cases include revocation after
the fence, changed descriptors, actor/domain mismatch, pending/failed handlers,
expired approval, unsupported handler and server-context serialization. Source
and test AST parsing, scoped diff check and Constitution gate passed. Fixtures
explicitly emulate account reads and Artifact handler output; these are not
real-user or real-account acceptance.

## REAL DELIVERY CARD / 真实用户工作闭环验收

Job: import the exact chosen file into the selected business context and recover
cleanly if confirmation expires or is withdrawn. This increment connects the
existing execution boundaries; the main source/project API, Artifact storage,
local open-workspace principal and real upload/edit/export/reopen flow remain
separate dependent integration work. No external upload, publishing, account
creation, Cookie use, production DB migration or runtime restart occurred.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: adapt the existing reviewed
Content candidate and canonical execution owner; no additional framework.
COMMERCIAL OVERLAY IMPACT: source rights remain independent of import permission.
Global coverage / RELEASED / OPERATING / COMMERCIAL_READY remain NO.
