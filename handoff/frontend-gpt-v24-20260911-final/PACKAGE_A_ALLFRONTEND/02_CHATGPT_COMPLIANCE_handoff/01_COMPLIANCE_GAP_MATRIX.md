# 01 — Compliance Gap Matrix

Status vocabulary: **VERIFIED** (evidence in tree) · **GAP** (missing, buildable) ·
**UNVERIFIED** (cannot prove yet) · **BLOCKED** (needs human/legal/credential/right).
Because no public MCP/plugin exists yet, rules about exposed tools are GAP (nothing to
violate, but the distribution requirement is unmet) — never mark them VERIFIED-by-absence.

## A. Work packages WP0-WP9
| ID | Work package | Status | Evidence / note |
|---|---|---|---|
| WP0 | Execution preflight | VERIFIED | `00_VERIFIED_REPO_STATE.md`; drift vs Word snapshot explained |
| WP1 | Source provenance & authorization | GAP | Internal provenance exists (`08-AUDIT/_source_provenance_scan.py`, `canonical_data.provenance`); no **public** source allowlist/rights registry. Draft: `proposed/source_provenance_contract.proposed.json`. Third-party rights = BLOCKED |
| WP2 | Privacy / Terms / Support | GAP | 0 files / 0 routes. Engineering DRAFT (legal review pending): `proposed/privacy_terms_data_support.DRAFT.md`. Published URL = BLOCKED on `TODO(LEGAL)` |
| WP3 | Public MCP boundary | GAP | 0 public MCP; internal `agent_capability`/`agent_smart_tool` only. Tool contract draft: `proposed/public_mcp_tools.proposed.json`; arch: `proposed/public_distribution_layer_arch.proposed.md`. Implementation = Codex |
| WP4 | Auth / permission / tenant | GAP | Internal `account/` primitives exist; plugin OAuth + server-side tenant->subject->scope re-validation not built. Demo/2FA = BLOCKED |
| WP5 | Secrets & restricted data | VERIFIED (owned scope) / GAP (public IO) | Secret scan of owned frontend = 0 hits over 367 text files; `.env.example` OPENAI key empty. Public-tool response minimization only specified, not enforced in code |
| WP6 | Write safety | GAP | Internal `ToolRiskLevel` exists; public Action Firewall / confirmation / idempotency / effect fence not built. Rules in arch draft |
| WP7 | Retention / delete / export | GAP | Governance mentions per-table retention; no public user export/delete. Schedule must be derived from REAL tables by Codex (do not invent) |
| WP8 | Tests / eval / submission | PARTIAL | Deterministic gates PASS (`03_TEST_EVIDENCE.md`); MCP contract/integration/inspector cannot run (no server); submission skeleton BLOCKED on real tools + demo account |
| WP9 | Handoff to Codex | VERIFIED | This bundle |

## B. OpenAI public-distribution rules A-K (Stage 2)
| Rule | Status | Evidence / required action |
|---|---|---|
| A tool names/descriptions match behavior | GAP | Naming rules captured in `public_mcp_tools.proposed.json`; verb-first, unique, non-manipulative |
| B explicit readOnly/openWorld/destructive hints | GAP | 0 annotations in tree; MCP pessimistic defaults; set per real handler, justify each at submit |
| C minimal inputs / no full chat history | GAP | Input schemas must be task-narrow; never reconstruct chat log; no raw GPS |
| D minimal auth scopes | GAP | Server-side scope in `account/`; design per-tool least privilege |
| E third-party authorization & ToS | BLOCKED | Public-visible != licensed; no unofficial connectors / scraping / rate-limit bypass; Collector stays internal |
| F published privacy policy (categories/purposes/recipients/retention/controls) | GAP -> publication BLOCKED | Draft present; needs `TODO(LEGAL)` + reachable public URL |
| G restricted data out of tool IO | GAP | PCI/PHI/gov-ID/credentials/MFA/cookies/tokens banned from public IO; add contract tests when tools built |
| H response minimization | GAP | Strip session/trace/request IDs, internal timestamps/log metadata unless strictly required |
| I write/open-world/destructive explicit+confirmed+idempotent+audited | GAP | Confirmation shows resolved params; exfiltration (send/post/upload) = write w/ preview; default read-first |
| J no subscription checkout in plugin | GAP (observe at build) | Only existing-entitlement sign-in; no plans/upgrade/checkout; commerce = physical goods only per OpenAI |
| K submission package / 5 positive + 3 negative / demo account | BLOCKED | Skeleton only (`proposed/chatgpt_app_submission.skeleton.json`); finalize only after real tools |

## C. Acceptance gates G0-G10
| Gate | Status | Note |
|---|---|---|
| G0 Repo Truth | VERIFIED | git + diff, no overwrite |
| G1 Public Boundary | GAP | Arch draft guarantees no collector/browser/cookie/raw-DB exposure; VERIFY after Codex builds adapter |
| G2 Provenance | GAP | fail-close default-deny registry proposed |
| G3 Privacy | BLOCKED | needs legal + published URL |
| G4 Tool Safety | GAP | hints/confirmation/idempotency after build |
| G5 Auth/Scope | GAP | cross-tenant/subject fail-close tests required |
| G6 Secrets | VERIFIED owned / GAP public | scan clean; add public-IO contract tests |
| G7 Runtime | UNVERIFIED | no public MCP runtime yet; cannot run health/flow |
| G8 Regression | VERIFIED (no production change) | tracked backend untouched; frontend validate 34/34 |
| G9 Submission | BLOCKED | real tools + 5/3 + demo account |
| G10 Handoff | VERIFIED | this bundle |

## P0 / P1 split
- **P0 (before any public submission):** WP1-WP5, WP8, WP9 and rules A-K except I/J; gates G1-G6, G9.
- **P1 (before RC, can follow read-first launch):** WP6 write safety hardening, WP7 retention/delete/export UX, rule I, rule J audit.
