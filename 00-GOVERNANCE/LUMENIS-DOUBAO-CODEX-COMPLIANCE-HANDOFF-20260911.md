---
document: LUMENIS Doubao -> Codex Compliance Execution Handoff
status: EXECUTION_HANDOFF
date: 2026-09-11
repository: Zachary-1012/LUMENIS-codex-Clean-OS
base_main_sha_before_handoff: 31c68a942d639cd1c48fb6d37e025b9447504ef0
source_word: LUMENIS_Doubao_Codex_Compliance_Execution_Plan_2026-09-11.docx
authority: supplemental; current repo truth and AGENTS.md always take precedence
---

# READ FIRST — Codex / Doubao Handoff

This file is the Git-friendly canonical handoff compiled from the Word implementation plan plus the two user-approved supplemental directives. It is not a replacement for current repository truth.

Before execution, re-read current `README.md`, `AGENTS.md`, `00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md`, current source/runtime/test evidence, and applicable Heritage assets. If this document conflicts with current source, current verified runtime/test/data evidence, or `AGENTS.md`, follow current repository truth and record the drift explicitly.

## Required read order

1. `README.md`
2. `AGENTS.md`
3. `00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md`
4. Current Governance / Architecture / Runtime / Test / Evidence relevant to this task
5. This handoff file
6. Current worktree / branch / diff / runtime evidence before any change

## Base snapshot note

This handoff was prepared against `main@31c68a942d639cd1c48fb6d37e025b9447504ef0` before this documentation commit. Do not reset or force the repository back to that SHA. If HEAD has advanced, classify it as `DRIFT` and continue from current truth.

# 1. Objective

Keep LUMENIS / 序境 as the Production Core / Production Truth Owner. The goal is not to turn the product into a ChatGPT shell. The target is a controlled public ChatGPT Plugin/App distribution boundary that is minimal-permission, auditable, reversible, and isolated from internal Collector/Auth/Browser sessions.

Execution chain:

```text
Current Repo Truth
→ Doubao Capability Preflight
→ Current-Tree Audit
→ Compliance Gap Matrix
→ Minimal Additive Remediation
→ Test / Runtime / Security / Evidence
→ Bounded Repair Loop
→ Handoff Package
→ Codex Independent Re-Audit
→ Final Closure / Submission Readiness
```

Evidence levels:

- `VERIFIED`: directly confirmed from current repo/current runtime/current official source.
- `PROPOSED`: target design or remediation proposal, never presented as current implementation.
- `UNVERIFIED`: not proven yet; absence must not be inferred from search failure alone.
- `BLOCKED`: requires authorization, human credential/2FA, legal review, external approval, or another non-automatable dependency.

# 2. Current verified repository baseline

At preparation time:

- Canonical repository: `Zachary-1012/LUMENIS-codex-Clean-OS`.
- `main` base SHA before this documentation commit: `31c68a942d639cd1c48fb6d37e025b9447504ef0`.
- `AGENTS.md` is active and requires: audit before change, compatibility before refactor, side-path before cutover, verification before delivery.
- Current phase is Production Convergence / Production Acceptance toward RC and Production.
- Production Truth, Evidence, Canonical Data, Subject/Domain isolation, Security, Recovery, Test/E2E and rollback remain protected.
- Collector/account automation remains read-only and must stop on captcha/security/IP/platform risk; no bypass of platform controls.
- Secrets such as API key/token/cookie must not enter Git.
- Current public Privacy / public MCP/App behavior / submission artifact status must be independently re-audited locally before claims are made.

# 3. Public ChatGPT distribution target

```text
ChatGPT / Codex Plugin Directory
          ↓
MCP / App Adapter
          ↓
Tool Allowlist + Explicit Schemas
          ↓
Auth + Tenant/Subject/Domain Scope
          ↓
Policy + Provenance Gate
          ↓
Versioned Internal Contract
          ↓
Existing Evidence / Canonical / Metric / Report / Agent capabilities
```

Internal Collector / Browser / Auth Session / cookies / raw credentials are not public tools.

Suggested public capability directions are `PROPOSED` until real source audit confirms equivalent current implementations: evidence search, metric query, report retrieval/generation, case insight, action-plan generation, controlled internal case writes, and separately confirmed external write/open-world actions.

For third-party data, public visibility does not itself prove authorization for automated collection or redistribution. Public ChatGPT distribution must fail closed when source rights/authorization cannot be demonstrated. Do not solve authorization problems by bypassing API restrictions, rate limits, access controls, captcha, login verification, or platform risk controls.

# 4. P0 / P1 closure priorities

## P0

1. Third-party source authorization/provenance boundary.
2. Published Privacy policy aligned with actual data flow.
3. Behavior-level audit of every exposed MCP/App tool and explicit tool annotations/hints.
4. Auth, minimum permission, tenant/subject/domain server-side scope enforcement.
5. Secrets and restricted credentials excluded from public tool input/output/log/Git.

## P1

1. Retention / deletion / export / user controls.
2. Confirmation, idempotency, Action Firewall / Effect Fence for write/open-world actions.
3. Submission artifact generated from actual source behavior, not guessed tool names.
4. Public distribution observability that is useful internally but does not leak internal identifiers/secrets in tool responses.

# 5. Doubao one-shot closed-loop protocol

Doubao must not downgrade this task into a document summary or code suggestion when it has real local execution capability.

Stages:

1. Capability preflight: verify terminal, local file write, Git, network, runtime and test capability actually available.
2. Current repo audit: record branch, HEAD, dirty state, remote and applicable AGENTS instruction chain.
3. Gap classification: `VERIFIED / GAP / UNVERIFIED / BLOCKED`.
4. Minimal safe implementation: prefer additive adapter/policy/test/evidence changes; do not rewrite Production Core without verified necessity.
5. Cheap gates first: parse, lint, schema, compile/syntax, focused unit/contract tests.
6. Runtime/security/E2E: execute real paths where environment allows.
7. Bounded self-repair: maximum 3 repair attempts per failure family; then stop expansion and record blocker/evidence.
8. Full regression + re-audit for affected P0 production paths.
9. Generate human-readable evidence and machine-readable `handoff_state.json`.
10. Final truthful state only: `READY_FOR_CODEX`, `PARTIAL`, or `BLOCKED`; never fake READY.

If Doubao lacks a required capability, it must preserve the current worktree, record the exact missing capability and blocker, and still produce the handoff state needed for Codex continuation.

# 6. Doubao Master One-Shot directive

```text
You are executing inside the current LUMENIS / 序境 repository. Do not rely on historical chat, old README, old commit conclusions, or this handoff as Production Truth.

FIRST:
- read current README.md
- read current AGENTS.md and any more-specific applicable AGENTS/override files
- read current Production Acceptance checklist
- record git status --short, branch, HEAD, latest commit, remotes
- detect worktree drift before changing anything

Then audit the real current tree for the ChatGPT public distribution task. Classify every relevant item as VERIFIED / GAP / UNVERIFIED / BLOCKED.

Do not delete or weaken Production Truth, Collector protections, Subject/Domain isolation, Security, Evidence, Runtime, Recovery, tests, or existing verified capabilities merely to make the new public layer easier.

Public ChatGPT tools must not expose internal Cookie/Token/password/MFA/browser session/raw credential/private trace. Third-party source rights must fail closed if not proven. Do not bypass platform/API/access/risk controls.

Implement only the minimal safe changes supported by current source and current architecture. Prefer adapters, allowlists, versioned contracts, feature flags, tests and evidence rather than duplicate cores or metric/report truth.

For every exposed MCP/App tool, trace the real handler and actual side effects. Tool annotations/hints must be explicit and behavior-matching; do not infer them from names.

Run real validation in ascending cost order: parse/schema/syntax/compile → unit/contract → integration/security → runtime/critical E2E → affected regression. Record real commands and exit codes. Never delete/skip tests, hide errors, broaden permissions or fabricate data/evidence to obtain PASS.

For one failure family, attempt repair at most 3 times. If still failing, record BLOCKED/NEEDS_EVIDENCE and stop broadening the refactor.

Git safety: no force push, no reset --hard, no clean -fd, no history rewrite, no overwrite of user uncommitted work. Do not merge main unless explicitly authorized. If making a branch/commit, record exact branch/SHA/push status and rollback.

Final delivery must include: audited; changed; why; files; DB changes; API/runtime changes; tests+exit codes; evidence; P0/P1 status; blockers/unverified; risks; branch/HEAD/dirty; commit/push status; rollback; next actions.

Generate/update handoff_state.json from real facts only so Codex can independently re-audit and continue.
```

# 7. Handoff state contract

Use the repository's existing authoritative handoff location/naming if one exists. Do not create a competing handoff standard merely because this document suggests fields.

Minimum machine-readable state:

```json
{
  "generated_at": "...",
  "repository": "Zachary-1012/LUMENIS-codex-Clean-OS",
  "base_branch": "...",
  "base_sha": "...",
  "work_branch": "...",
  "head_sha": "...",
  "dirty": true,
  "objective": "ChatGPT public distribution compliance closure",
  "verified_facts": [],
  "changed_files": [{"path":"...","reason":"...","rollback":"..."}],
  "tests": [{"command":"...","exit_code":0,"status":"PASS","evidence_path":"..."}],
  "compliance_items": [{"id":"...","status":"VERIFIED|GAP|UNVERIFIED|BLOCKED","evidence":[]}],
  "syntax_errors_found": 0,
  "syntax_errors_fixed": 0,
  "json_errors_found": 0,
  "json_errors_fixed": 0,
  "schema_mismatches": [],
  "remaining_blocked": [],
  "validation_commands": [],
  "validation_results": [],
  "blockers": [],
  "unverified": [],
  "security_notes": [],
  "files_to_read_first": [],
  "recommended_next_actions": [],
  "rollback": []
}
```

# 8. Supplemental Directive A — execution launch rule

Read this handoff in full and treat the “Doubao Master One-Shot directive” as the main execution task. Do not only summarize the document, do not regenerate a new plan instead of executing, and do not omit tables, code blocks, JSON contracts or acceptance conditions. Before execution, verify current repository truth; after execution, generate the complete Codex handoff package.

If this handoff conflicts with current source, README, AGENTS, Production Truth, or current runtime evidence, current repository truth takes precedence and the conflict must be recorded as `DRIFT`.

# 9. Supplemental Directive B — syntax / JSON repair gate

In addition to the main task, enforce the following without changing task scope, architecture, business semantics or Production Truth:

1. Check all files added/modified/touched by this task for syntax, formatting, JSON/JSONL/config structure errors.
2. For every involved JSON file, perform real parsing/schema validation. Check missing/extra commas, unclosed braces/brackets, invalid quotes/escapes, duplicate keys where the parser/tooling can detect them, illegal comments, BOM/encoding issues, incorrect `null/true/false`, schema field/type/required mismatches, invalid paths/file names/version references.
3. JSON repair must follow the real existing Schema/Contract. Do not delete business fields, change data meaning, or fabricate defaults merely to make parsing pass.
4. Also validate affected Python, JS/TS, HTML/CSS, YAML, Markdown code blocks, Shell/PowerShell or other changed source/config formats using the repository's actual toolchain where available.
5. After repair, rerun JSON parse/schema validation, compile/syntax checks, and relevant unit/integration/smoke tests.
6. If the failure is a Contract mismatch rather than syntax, do not silently rewrite Production Contract. Mark `BLOCKED_CONTRACT_MISMATCH` and record file, field, actual value, expected contract/evidence, and proposed next action for Codex.
7. Automatic repair must remain `minimal safe change`. Do not opportunistically refactor UI, database, permissions or API business semantics.
8. Final handoff must include `syntax_errors_found`, `syntax_errors_fixed`, `json_errors_found`, `json_errors_fixed`, `schema_mismatches`, `remaining_blocked`, `validation_commands`, `validation_results`.

Hard acceptance:

```text
JSON_PARSE_ERRORS = 0
SYNTAX_ERRORS = 0
NEW_CONFIG_PARSE_FAILURES = 0
```

Do not claim completion when these are unmet, except for a real Contract conflict explicitly handed to Codex as blocked.

# 10. Codex takeover protocol

Codex must not trust the word “completed”. It must independently validate Git state, real diff, real files, actual MCP/App handlers and side effects, scope/permissions/secrets, source provenance, privacy state, test exit codes, runtime/E2E/evidence and P0/P1 gates.

## Codex Takeover directive

```text
You are taking over the current LUMENIS / 序境 local worktree. Do not rely on historical chat and do not treat the Doubao handoff summary as Production Truth.

1) Read the current applicable AGENTS instruction chain before modifications.
2) Record current git status --short, branch, HEAD, latest commit and remotes. If handoff SHA differs, record DRIFT rather than resetting.
3) Read current README, Production Acceptance checklist, this handoff, handoff_state.json and all actual evidence/change manifests produced by Doubao.
4) Independently inspect changed_files and real diff.
5) Independently trace every exposed MCP/App tool to its real handler/side effects and verify explicit readOnly/destructive/open-world annotations against behavior.
6) Verify provenance/public allowlist fail-close behavior, auth/tenant/subject/domain server-side scope, and that credentials/auth secrets cannot enter public tool IO/log/Git.
7) Verify privacy/terms/data-policy/support claims against actual implemented/published state; an unverified URL is not VERIFIED.
8) Rerun P0 validation/tests yourself, including syntax/JSON gates. Preserve real commands and exit codes.
9) Close P0 GAP/BLOCKED/UNVERIFIED before P1. Do not bypass third-party restrictions, access controls, 2FA, legal review or authorization dependencies.
10) For a failure family, stop broadening the refactor after 3 failed repair attempts and record BLOCKED/NEEDS_EVIDENCE.
11) No reset --hard, clean -fd, force push, user-work overwrite, hidden permission expansion, deleted tests or fabricated PASS.
12) Final output must follow current AGENTS delivery format and state exact branch/HEAD/dirty, commit/push status, rollback and next action.

Only use READY when current evidence supports every required gate. Otherwise state PARTIAL or BLOCKED truthfully.
```

# 11. Definition of Done

- `G0 Repo Truth`: branch/HEAD/dirty/remote recorded; drift explained; no user-work overwrite.
- `G1 Public Boundary`: no public exposure of collector/browser/session/cookie/raw secrets; no raw DB-as-tool shortcut.
- `G2 Provenance`: every public source has a provable rights/authorization status; unknown fails closed.
- `G3 Privacy`: published privacy state is real and aligned with actual data flow; review status explicit.
- `G4 Tool Safety`: exposed tool annotations match behavior; write/open-world actions have confirmation/idempotency/audit where applicable.
- `G5 Auth/Scope`: cross-tenant/subject/domain paths fail closed and scope is server-side enforced.
- `G6 Secrets`: secret scan/contract evidence shows restricted credentials are excluded from Git/public tool IO.
- `G7 Runtime`: real MCP/App health, core success flow and failure flow verified where environment permits.
- `G8 Regression`: affected LUMENIS P0 production paths remain intact; internal Collector protection is not weakened.
- `G9 Submission`: submission artifact, if generated, is derived from actual source behavior and current review requirements; missing output schema is reported rather than invented.
- `G10 Handoff`: machine-readable and human-readable evidence is sufficient for independent Codex re-audit.
- Syntax gate: `JSON_PARSE_ERRORS=0`, `SYNTAX_ERRORS=0`, `NEW_CONFIG_PARSE_FAILURES=0`, excluding explicitly documented real Contract blockers.

Final state meanings:

- `NOT READY`: any required P0 gate is open or critical truth remains unverified.
- `READY FOR CODEX`: Doubao phase is truthfully closed and remaining items are transparently handed off; this does not mean public submission is complete.
- `SUBMISSION READY`: current public MCP/App, privacy, authorization, tests and submission artifacts have passed the then-current rules and real verification.
- `PRODUCTION READY`: repository's current six Production Acceptance Gates plus required public distribution gates all pass with real runtime/E2E/recovery evidence.

# 12. Non-negotiable safety / scope rules

- No production database deletion/overwrite or historical fact rewriting for test success.
- No duplicate Production Truth or duplicate metric/report calculation core.
- No secrets in Git, logs, test fixtures, front-end or tool responses.
- No weakening Collector/auth/platform risk protections to satisfy public Plugin goals.
- No legal conclusion fabricated by an agent; unresolved authorization/legal review remains blocked.
- No claim that internal isolation itself legalizes an unauthorized source.
- No claim that file existence means capability completion.
- No claim that tests exist means tests passed.
- No claim that tests passed means runtime verified.
- Prefer `BLOCKED` over false `READY`.

# 13. Final takeover rule

Codex must independently verify current Git state, actual diff, real files, MCP/App behavior, permissions/secrets, runtime/E2E/evidence, syntax/JSON validation and P0/P1 gates before declaring any completion state. Current repository truth and current evidence remain authoritative over this handoff.