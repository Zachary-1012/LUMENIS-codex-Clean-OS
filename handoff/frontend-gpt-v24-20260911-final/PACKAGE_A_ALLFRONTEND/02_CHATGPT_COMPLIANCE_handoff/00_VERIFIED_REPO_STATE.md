# 00 — Verified Repository State (read-only audit)

All facts below were re-verified against the live local tree at audit time
(not taken from chat memory). Re-run the git commands before acting.

## Git truth
| Item | Value |
|---|---|
| branch | `main` |
| HEAD | `ab67612367c172ced2dff62b44e98de86469d1e6` — "docs: add Doubao to Codex pre-production handoff markdown" |
| origin | `https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS.git` |
| `git status -sb` | `## main...origin/main` + `?? experience_v2/` (frontend, untracked) |
| tracked production diff | **none** (no tracked backend file modified by this work) |
| Word snapshot base | `31c68a942d639cd1c48fb6d37e025b9447504ef0` (brand-logo manifest, 2026-09-10) — DRIFT explained, **not** rolled back |
| branch created / commit / push | **none** — no authorization; `PUSH=NOT_PERFORMED` |

## Product baseline (current truth)
- `README.md`: CURRENT PHASE = **PRODUCTION CONVERGENCE**; six acceptance gates; Production Core / Production Truth Owner.
- `AGENTS.md` V3.1 Active: audit-before-change; Collector read-only red line; data minimization; secrets/git/test rules.
- `00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md` exists.

## Runtime / module entrypoints (real paths)
- Main Flask application: **`app.py`** (root). Feature blueprints in root `*_api.py`, e.g.
  `evidence_api.py`, `collection_api.py`, `data_query_api.py`, `ai_api.py`,
  `browser_runtime_api.py`, `browser_surface_api.py`, `content_generation.py`, `ic_routes.py`.
- Internal Collector governance (must stay internal): `collector_guard/`
  (`guard.py`, `rate_limiter.py`, `risk_engine.py`, `runtime_guardian.py`, `resource_guard.py`, ...), `collector_v2/`, `browser_runtime/`.
- Existing auth/permission primitives (internal, reusable): `account/`
  (`authorization.py`, `security.py`, `totp.py`, `verification.py`, `workspace_keys.py`, `audit.py`, `models.py`).
- Versioned internal contracts the public layer should call: `contracts/`
  (`global/`, `kos/`, `lumenis_adapter.py`, `CROSS_REPO_CONTRACT_BOUNDARY.md`).
- Internal tool/risk registry (NOT a public MCP server):
  `agent_capability/router.py` (`class ToolRiskLevel` LOW/MEDIUM/HIGH/CRITICAL at line 35; `list_tools()` line 348),
  `agent_smart_tool/base.py` (`list_tools()` line 580). Tests: `tests/agent_capability/`, `tests/agent_smart_tool/`.
- Internal data-provenance primitive: `08-AUDIT/_source_provenance_scan.py`,
  `tests/test_source_provenance.py`, `canonical_data.provenance` column (`00-GOVERNANCE/schema_registry_t4.csv:75`).

## Decisive "what does NOT exist" results (whole-tree, `experience_v2/` excluded)
| Probe (whole backend tree) | Result |
|---|---|
| MCP annotations `readOnlyHint/openWorldHint/destructiveHint/idempotentHint` | **0 matches** |
| MCP `inputSchema/outputSchema` | **0 matches** |
| Public MCP server (`FastMCP`, `mcp.server`, JSON-RPC `tools/list`,`tools/call`) | **0** (the `list_tools/call_tool` hits are the internal agent registry above) |
| files named privacy/terms/mcp/plugin/chatgpt/submission/support/data-policy | **0** |
| Flask routes `/privacy /terms /data-policy /support` | **0** |
| `chatgpt-app-submission.json` | **0** |
| "openai" matches | LLM **provider** config only (`.env.example` empty key; `ai_provider_matrix_shardB.csv` = DISABLED; `tests/test_v2_p0_modules.py::test_openai_disabled`) — NOT a ChatGPT plugin |

> Absence is recorded as GAP/UNVERIFIED for *distribution readiness* — it is not a runtime defect in the current internal product.
