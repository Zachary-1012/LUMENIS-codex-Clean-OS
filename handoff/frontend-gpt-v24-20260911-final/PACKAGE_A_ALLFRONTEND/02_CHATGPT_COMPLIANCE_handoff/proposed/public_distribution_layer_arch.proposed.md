# Public Distribution Layer — proposed architecture (Codex implements)

Goal: keep LUMENIS Production Core / Truth ownership; add a thin, auditable
**Public ChatGPT/MCP Compliance Layer** that only calls versioned internal contracts.

```
ChatGPT / MCP client
   -> public transport (OAuth 2.1 + PKCE; per-tool least scope)         [TODO(CODEX) stack choice]
   -> public_mcp/ adapter  (NEW, isolated blueprint/module)
        * tool registry: ONLY the tools in public_mcp_tools.proposed.json
        * explicit annotations (readOnly/openWorld/destructive/idempotent)
        * input validation (JSON Schema, additionalProperties=false)
        * server-side authz: user -> workspace/tenant -> subject -> domain -> scope
          (NEVER trust client-supplied subject_id; reuse account/authorization.py)
        * source allowlist gate (source_provenance_contract; default-deny)
        * write effect fence: explicit intent + idempotency key + resolved-param confirmation + audit
        * output minimizer: project only allowed fields; strip internal metadata
   -> contracts/lumenis_adapter.py + versioned internal read/compute/write contracts
   -> Production Core (evidence / canonical / metric / case / report)  [unchanged owner]

NEVER reachable from public layer: collector_v2, collector_guard, browser_runtime/CDP,
cookies/session, raw DB connection, model-side metric recompute.
```

## Rollout order (matches tool phases)
1. Read/compute tools (`search_evidence`, `query_metrics`, `get_case_insights`, stateless `generate_report`).
2. Private additive/bounded writes with effect fence (`create_action_plan`, `update_internal_case`).
3. `send_or_publish_external` stays DISABLED at launch; later gate needs product + legal sign-off.

## Reuse, do not rebuild
- Risk vocabulary: map internal `agent_capability/router.py::ToolRiskLevel` (LOW/MEDIUM/HIGH/CRITICAL) to MCP hints; do not create a second risk model.
- Auth primitives: `account/` (authorization, security, totp, workspace_keys, audit).
- Provenance: extend `08-AUDIT/_source_provenance_scan.py` concepts / `canonical_data.provenance`, do not fork a parallel truth.

## Tests Codex must add (P0)
- annotation/behavior consistency test (fail if a public tool lacks all three hints or claims readOnly while its handler writes).
- cross-tenant / cross-subject isolation (must fail-close).
- provenance default-deny (INTERNAL_RESTRICTED / BLOCKED_EXTERNAL cannot trigger public fetch).
- response minimization contract test (no trace/request/session id, no restricted data).
- write idempotency + confirmation/effect-fence test.
