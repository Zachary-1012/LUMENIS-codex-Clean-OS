# LUMENIS Source Owner Index — CURRENT

> Status: **CURRENT EXECUTION INDEX / THREE-DELIVERY RED LINE**
>
> Updated: 2026-09-20
> Audit baseline: `1b78783f41628046f25b4a79f57985d18054b9a2` (provenance only; resolve the live `origin/main` before every change)

This file is the fixed repository navigation and delivery index for 序境 / LUMENIS. It classifies current source by owner and tells Codex where to look after the one-time source audit. It is not a second product architecture, Experience authority, progress ledger, or proof that a runtime capability works.

When this index conflicts with current executable source or runtime evidence, current source/runtime wins and this index must be repaired in the same coherent change.

## 1. Locked delivery sequence

Product work is delivered in exactly three ordered rounds. Do not split the product into a new architecture or intermingle unrelated rewrites.

| Round | Delivery | Scope | Exit gate |
| --- | --- | --- | --- |
| 1 | **App Experience** | Existing product functions expressed through distinct Flutter UI, layout, responsive PC/mobile composition, accessibility, state feedback and purposeful motion. Complete the App Shell, five Golden Pages, nested CTH-02, then the remaining approved screen workflows. | A real App can be operated against current Product Core contracts; every completed screen has its own specification, honest states, representative PC/mobile runtime evidence and no generic 44-screen template. |
| 2 | **Backend and capability recovery** | Trace existing callers to current owners; recover, adapt and bind valid capability; close API, Permission, Evidence, workflow and data gaps. Preserve Ollama, media Cookie collection and existing functions. Use OpenCode/Codex as engineering runtimes, not product-truth owners. | Each included workflow proves callable source → Permission → canonical read/write → real result → Evidence/trace → regression. No `UNKNOWN` or `BACKEND_GAP` is treated as a missing API until current source is checked. |
| 3 | **Closed-loop internal beta** | Run the complete product with real permitted data and current platform sessions; execute PC/mobile E2E, failure/recovery, security, packaging and release evidence. | The selected beta workflows pass user-entry → action → result → return/evaluation on supported devices. `TESTED`, `VERIFIED`, `RELEASED` and `OPERATING` remain separate claims. |

Round 1 may use existing Product Core reads and actions needed to make the current App real. If a missing backend behavior blocks a workflow, record the exact owner/caller/contract and hand it to Round 2; never invent mock success or a parallel API.

## 2. Product preservation contract

These are blocking rules for all three rounds:

1. Inspect the current owner, callers, contract, tests and runtime path before changing code. `UNKNOWN` and `BACKEND_GAP` are investigation states, not instructions to create an API.
2. Preserve existing product position, functions, business rules, data sources, object meanings and workflow outcomes. Work may strengthen or adapt an approved capability; it may not invent, expand or replace product scope.
3. Media platforms continue through the existing SYSTEM Cookie/session/browser collection chain. Do not add a platform-login step, a second collector or a new account model.
4. The LUMENIS product account is deferred until after internal beta. Pre-beta browsing and existing product use must not be blocked by a LUMENIS account wall. This decision does not remove server-side Permission, effect fences or platform-session safety.
5. Platform Cookie/session authorization and a future LUMENIS product account are separate identities. Never migrate, display, log or commit platform credentials as product-account data.
6. Apple contributes restraint, content priority and clear primary actions. ChatGPT contributes a single intent entry and progressive complexity. TRAE contributes the visible rhythm “task → execution → result”. These are Experience principles only; they do not authorize new search, chat, project, task or account features.
7. The frontend presents business intent, state, progress, result and recovery. Collection, routing, tool execution, model selection, Evidence creation and other processing remain in their current backend/runtime owners.
8. Each of the 44 screen blueprints keeps its own task, information hierarchy, composition and interaction path. PC and mobile share business truth but use purpose-built semantic recomposition; neither is a scaled copy of the other.
9. A local problem may change only its bounded owner/callers. It may not trigger a global auth, database, naming, architecture or design-system rewrite. Remove a path only after its unique behavior is preserved and accepted in the current owner.
10. Every change proves the requested improvement and preservation of affected behavior with proportional tests and, for user-visible workflows, real runtime/E2E evidence. A build, fixture, HTTP 200, screenshot or document alone is insufficient.

## 3. Fixed source lookup map

After bootstrap, locate work here. Root-level compatibility callers remain classified as callers until their behavior is safely absorbed; their location does not make them a second owner.

| Concern | Canonical authority or owner | Current callers/contracts/tests to inspect |
| --- | --- | --- |
| Agent execution | `AGENTS.md`; `00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md`; this index | `scripts/audit_tools/verify_codex_takeover_governance.py`; `.github/workflows/platform-verify.yml` |
| Product/domain architecture | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`; `00-GOVERNANCE/PRODUCT-POSITIONING-CURRENT.md` | Exact CTH/BMP caller and contract for the active slice; do not infer ownership from a filename |
| Experience authority | `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md` | `contracts/experience/screen-specifications/<SCREEN-ID>.md`; Experience validators |
| Flutter App | `app/lib/product/`, `app/lib/shell/`, `app/lib/features/` | `app/lib/core/`; matching `app/test/`; `app/README.md` |
| Screen truth binding | `contracts/experience/lumenis_app_binding_registry.json`; `contracts/experience/screens/<SCREEN-ID>/` | `actions/`, `permissions/`, `evidence/`, `states/`, `viewmodels/`; current API owner and tests |
| Product Core composition/API | `app.py`; `lumenis_app_api.py`; current registered routes | `experience_runtime.py`; `experience_screens.py`; exact route/service/repository tests |
| CTH/BMP business callers | Current root/domain modules such as `subject_context.py`, `subject_registry.py`, `api_dual_domain.py`, campaign/brand/event/case/risk modules | Trace each caller to its actual data, Permission, Evidence and test owner before moving or renaming it |
| Shared Evidence | `lumenis/shared/evidence/` | Evidence APIs, migrations, lineage and affected domain tests |
| Shared Database | `lumenis/shared/database/` | `data/monitor.db` contract, migrations and isolated persistence tests |
| Schema/migrations | Shared Database migration owner; existing `migrations/`/Alembic paths | Schema callers, rollback/compatibility and isolated migration tests; never mutate the protected runtime DB merely to classify a file |
| Shared Evaluation/Learning/Reporting | `lumenis/shared/evaluation/`; `lumenis/shared/learning/`; `lumenis/shared/reporting/` | Current root callers and domain regression tests |
| Shared skills/agent execution | `lumenis/shared/agents/skills/` | `account/api.py`; `agent_runtime/`; `agent_capability/`; `agent_smart_tool/`; `ai_api.py`; `ai_task_engine.py` |
| SYSTEM Permission/effects | `lumenis/system/security/` | Active API/action callers; permission, denial, approval and effect-fence tests |
| SYSTEM AI runtime | `lumenis/system/ai_gateway/` | `local_ai_client.py`; `lumenis/ai_hub/`; `ai_api.py`; `ai_task_engine.py`; `content_generation.py`; `system_features_api.py`; `experience_runtime.py`; AI tests |
| SYSTEM collection | `lumenis/system/collector/` | Platform adapters, guard, runtime, scheduler and collection/Evidence tests |
| SYSTEM browser/session | `lumenis/system/browser/runtime/` | `xhs_cookie_bridge.py`; `xhs_p0_orchestrator.py`; `xhs_cdp_collector.py`; Cookie/path/HK-policy/lineage tests |
| Engineering AI | `.opencode/opencode.json` for OpenCode; Codex user/runtime configuration outside product source | Engineering audit/test/automation only; never count it as a LUMENIS user model, API owner or Production Truth |
| Startup/runtime | `scripts/start_production.ps1`; `app.py`; `run_supervised.py` | `/healthz`; required initialization; critical API/App runtime evidence |
| Operations/deployment | Existing `scripts/`, `deployment/` and environment manifests | Use only the launcher/deployment artifact named by the active acceptance gate; scripts do not become product owners |
| Tests and release evidence | `tests/`; `app/test/`; `tests/CI_TEST_TIERS.md` | `.github/workflows/`; exact release/production acceptance artifact for the current commit |
| Historical/provenance material | Dated handoff/audit/archive and `intelligence_library/` | Read only when the active owner trace needs provenance; never use it as current runtime truth |
| Third-party code/assets | Registered dependency manifests, `vendor/` when present, and `THIRD-PARTY-COMPONENT-REGISTER.md` | License, version, adapter boundary and replacement direction; never absorb it into LUMENIS ownership silently |

`scripts/audit_tools/scan_all.py`, `scan_local_repos.py` and `local_feature_diff.py` are legacy/one-time discovery tools. They scan outside the active slice or contain historical path assumptions, so they are not normal bootstrap commands and their output is not CURRENT capability evidence.

### File placement rule

New production code goes into the canonical owner above. New Flutter code goes into the owning `app/lib/features/<owner>/<screen>` slice, with stable cross-feature primitives promoted only after proven reuse. New Experience contracts go into the existing `contracts/experience/` family. Do not add a new top-level frontend, collector, AI gateway, database, permission system, evidence store or design authority.

## 4. Fixed per-task inspection route

Do not repeat a full-repository audit for normal work. Use this route:

```text
live origin/main
→ this index row
→ active screen/workflow specification or contract
→ exact canonical owner
→ direct callers
→ direct tests
→ required runtime/E2E evidence
→ update the same row/specification if ownership changed
```

For a screen task, the fixed route is:

```text
Experience Constitution
→ contracts/experience/screen-specifications/<ID>.md
→ contracts/experience/screens/<ID>/ + binding registry
→ app/lib/features/<owner>/<ID>
→ app/test/<matching owner>/<ID>
→ current Product Core route/owner/tests
```

A repository-wide re-audit is allowed only when one of these triggers occurs:

- a canonical owner in this index is missing or has split into competing implementations;
- a change adds a top-level product surface, database, runtime, collector, AI gateway, Permission or Evidence owner;
- current source and this index disagree about a business owner or read/write path;
- a blocking Only-One, Experience or takeover validator detects structural drift;
- the product owner explicitly changes product architecture or requests a new full audit.

Routine commits, runner/DNS failures, stale historical documents and a single `UNKNOWN` binding are not full-audit triggers.

## 5. Source-audit disposition at the baseline

| Area | Source-backed finding | Status for execution |
| --- | --- | --- |
| Flutter Experience | `app/` is the only user-facing product. Five top-level Golden Page slices and nested CTH-02 exist; 44 screen IDs exist, while only six reviewed screen specifications exist. Current UI contains responsive compositions but limited motion/accessibility/runtime coverage. | **PARTIAL / ROUND 1**. Existing source is preserved; remaining screens and real interaction acceptance are not claimed complete. |
| Product account | The current launch flow contains Basic/Auth + `/v4/auth/login` and can gate the App. | **CONFLICT TO RESOLVE IN ROUND 1** against the approved pre-beta no-account-wall boundary. Preserve backend Permission; do not touch media Cookie sessions. |
| OpenCode | `.opencode/opencode.json` configures a bounded engineering runtime and explicitly restricts secrets/network/task behavior. Flutter and Product Core do not call OpenCode as a user feature. | **ENGINEERING CONFIG PRESENT**. Preserve and use for development/audit where available; do not report it as an implemented product capability. |
| Ollama | Local Ollama is represented by `lumenis/system/ai_gateway/`, provider discovery/fallback, `local_ai_client.py`, backend callers and AI-01 provider state. The canonical registry promotes it to `ACTIVE` only after probe; an older provider matrix currently claims `ACTIVE` and must not override runtime. | **IMPLEMENTED SOURCE / LIVE UNVERIFIED IN THIS AUDIT**. Round 2 reconciles the duplicate client/status wording and validates the configured model, real caller behavior, fallback and Evidence. |
| Media Cookie collection | SYSTEM collector/browser owners, XHS/RedNote bridges, HK-policy checks, Cookie path and lineage tests exist. Secrets are runtime-only and excluded from Git. | **IMPLEMENTED SOURCE / LIVE SESSION UNVERIFIED IN THIS AUDIT**. Preserve existing Cookie flow and verify only through authorized runtime acceptance. |
| Backend gaps | The registry contains 54 fail-closed binding rows, and current backend capability is distributed across canonical and compatibility callers. Source audit also found duplicate `/api/ai/tasks` declarations, a canonical AI Gateway plus `local_ai_client.py`, and compatibility Skill/Cookie callers that must be reconciled. | **SOURCE CHECK REQUIRED PER ROW**. Preserve unique behavior and converge on existing owners; do not manufacture 54 APIs or a third execution path. |
| Legacy-looking root callers | Root modules still carry active compatibility/caller behavior. | **CLASSIFIED, NOT DELETION-READY**. Move/delete only after call graph, behavior, data and tests converge on the canonical owner. |

This disposition freezes where work starts; it does not freeze code. Each delivered slice updates its own specification, evidence and affected index row so future work resumes from the fixed path rather than rediscovering the repository.
