# 05 — NEXT CODEX PROMPT (paste-ready)

You are the Production Code Owner for LUMENIS / 序境. Doubao completed a read-only ChatGPT
public-distribution compliance audit and left PROPOSED contracts. Do not trust this summary as
truth — re-verify against the live tree, then implement. Follow root AGENTS.md first.

## Step 0 — re-verify (do not skip)
```
git status --short
git branch --show-current
git rev-parse HEAD        # audit was at ab67612367c172ced2dff62b44e98de86469d1e6 on main; if different, mark drift
```
Read: README.md, AGENTS.md, 00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md,
then this folder: 00..05 + handoff_state.json + proposed/.

## Step 1 — branch (no work on main without protection)
Create `integration/chatgpt-plugin-compliance-doubao-v1` (or follow current governed branch).
No force-push, no main merge, no push without explicit user authorization.

## Step 2 — close P0 in this order (tickets)
- CPLG-01 Source provenance registry: implement `proposed/source_provenance_contract.proposed.json` adapting existing provenance; default-deny; unit test.
- CPLG-02 Public MCP adapter (isolated module): register ONLY proposed tools; explicit hints; JSON-Schema input validation; reuse `account/` for server-side tenant->subject->scope; call only `contracts/` versioned internals. Read/compute tools first.
- CPLG-03 Per-tool annotation/behavior consistency test + cross-tenant fail-close + response-minimization tests.
- CPLG-04 Secrets/Restricted-Data gate in the public output path; re-run secret scan; add contract tests.
- CPLG-05 Privacy/Terms/Data-Policy/Support routes wired to the DRAFT (routes real; legal text stays TODO(LEGAL)); a route is VERIFIED only when reachable.
- CPLG-06 Write effect fence (intent + idempotency key + resolved-param confirmation + audit) for the two private writes; keep send_or_publish_external DISABLED.
- CPLG-07 Finalize chatgpt_app_submission only after CPLG-02/03 pass: exactly 5 positive + 3 negative, real tools, outputSchema or explicit warning; demo account + verified developer are HUMAN blockers.

## Step 3 — test ladder (record command + exit code; never skip/delete/forge)
syntax/JSON -> secret scan -> unit -> MCP contract/integration -> auth isolation -> provenance policy
-> runtime/health/idempotency -> (if env allows) MCP Inspector / ChatGPT dev mode -> regression.

## Hard stops
- Never expose collector/browser/CDP/cookie/session/raw-DB; never let the model recompute metrics; never build a second truth.
- Legal / third-party rights / demo account / 2FA / verified developer stay BLOCKED — no technical workaround.
- Same failure family 3x -> stop, mark BLOCKED/NEEDS_EVIDENCE; do not paper over with refactors.
- Output only READY_FOR_CODEX / PARTIAL / BLOCKED.
