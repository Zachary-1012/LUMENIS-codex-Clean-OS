# ROUND 04 — local Content workspace principal

Base: `80c2ab040e596676e49c22e47f737f35e009b668`.
Status: bounded implementation; not Round 04 or J4/J5/J6 acceptance.

## REAL DELIVERY CARD / 真实用户工作闭环验收

The Product Owner deferred product account design until closure. A local user
must therefore be able to select a Content business context without a fabricated
account or a login wall. This slice introduces the server-issued
`local_workspace` principal, `principal_ref=workspace:local`, `actor_id=None`.
It admits only `content` read/write scope requests for CTH/BMP GLOBAL or an
active, exact registered focus. It creates no account, table or parallel owner.

The existing Permission owner rechecks explicit open-workspace configuration,
loopback Host/Origin/remote address and absence of forwarded, authentication,
session or forged identity headers. Client JSON is never an authority object.
Closing the workspace or changing transport invalidates subsequent admission.
The prior local read policy and authenticated integer-actor path retain their
semantics; the legacy serializer is unchanged.

Scope admission does not authorize DB writes, exports, COMMIT, approvals or
external effects. Source confirmation, Artifact principal ownership and API/UI
binding still require their own existing-owner integration. This slice alone
does not constitute a real imported or rendered user result.

## Verification

Frozen Git blobs inspected by root:

- `permission.py`: `1662a692a896cffe357a7a77230abdc99a066561`
- `security/__init__.py`: `d0108347b35bae4c3a60e758a4e57476a8a1a56b`
- `test_local_workspace_principal.py`: `3fe8e1a5758face528905c84546ed1b4027c2cce`

Current-snapshot AST (3 files), exact diff check and blocking Constitution passed.
The worker's initial run did not preserve its final tool exit status and is not
counted as PASS. Root resolved that specific evidence gap on the same frozen
files: **189 passed in 9.78s, exit 0**, no background thread leak. Files:
`test_local_workspace_principal`, `test_local_workspace_read_permission`,
`test_permission_exact_resource_scope`, `test_permission_scope_approval_binding`,
`test_permission_gate`. An explicit external disposable SQLite seed was used;
the production database was not selected for testing.

## Impact and recovery

Recovery checks cover workspace closure, changed transport, invalid focus and
scope admission failing to confer write effects. Full App operation and process
restart acceptance remain LIVE_NOT_VERIFIED for this slice.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: no data or coverage claim changes.
COMMERCIAL OVERLAY IMPACT: source rights, release and commercial readiness remain
unaccepted. Current scope/Evidence/effect boundaries remain active.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: this closes a documented
local account-wall mismatch using the current Permission owner and existing
Flask request boundary; no dependency, new provider or external integration.

Rollback is a source revert of this isolated slice before dependent consumers,
not deletion or rewriting of production data. No runtime switch or account was
changed by this Batch.
