# 序境 / LUMENIS — Codex Takeover CURRENT

> Status: **CURRENT EXECUTION ENTRYPOINT / NO-REDISCOVERY**  
> Updated: 2026-09-20
> CI status: resolve from GitHub checks for the exact current origin/main; no historical SHA is a current acceptance result.
> **Never treat this document's commit, any pasted SHA, or any historical handoff SHA as the current HEAD. Codex must fetch and resolve `origin/main` at session start.**

This file records the current Codex execution path and authority order. It does **not** upgrade source evidence into LIVE / RELEASED / OPERATING claims.

## 1. Mandatory Codex bootstrap and authority

Root `AGENTS.md` is the first coding-agent instruction boundary. After reading it and before changing product code, use this order:

1. `AGENTS.md`
2. this file: `00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md`
3. `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`
4. `00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md`
5. `README.md`
6. `00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md`
7. `00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json`
8. `00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md`
9. `00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md`
10. the exact current Source / Route / API / DB / Permission / Evidence / Runtime / Tests for the active slice

When evidence conflicts:

```text
Current Production Source
> Runtime Reality
> Current DB / API / Permission / Evidence Contracts
> Tests / E2E / Production Acceptance
> Current Canonical Governance
> README
> Historical Handoff / Legacy Evidence
> Chat History
```

Current executable source/runtime truth always outranks this handoff. Historical handoffs, chat history and screenshots never override executable truth.

The root README, this CURRENT handoff, the human-readable cross-repo registry and the machine contract must not define conflicting current protocol identities. A mismatch is a governance failure to repair before cross-product changes continue.

### Experience authority

If the active task touches any user-visible Experience/UI, read the sole design authority:

```text
00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
```

Then inspect the current Source / ViewModel / State / Action / Permission / Evidence / Runtime owners for the active slice.

The product owner approved the overall App architecture and Experience Constitution §§30–36 on 2026-09-20; source-backed App implementation is active under `app/`. Continue the five distinct Golden Page vertical slices and the nested CTH-02 selection-only directory without asking for overall-plan approval again. Before implementing another screen, complete and review its specification with current source/API, canonical owner, actor scope, Permission, Evidence lineage, purpose-built PC/mobile composition, states and executable acceptance. Overall-plan approval is not per-screen acceptance. `contracts/experience/lumenis_app_binding_registry.json` records data/actor/permission/Evidence bindings; it is not a UI template, and legacy `sectionTypes` do not determine layout.

Historical browser presentation material was removed from `main`; retained App contracts are canonical under `contracts/experience/`.

Required design gates:

```text
python scripts/audit_tools/verify_experience_authority_exclusive.py
python scripts/audit_tools/verify_experience_anti_template.py --strict
```

## 2. Remote evidence lock

Repository and branch:

```text
repository = Zachary-1012/LUMENIS-codex-Clean-OS
branch     = main
current HEAD = READ WITH git fetch + git rev-parse origin/main
```

Mandatory start commands on the canonical workstation:

```powershell
Set-Location D:\LUMENIS_REBUILD\序\序境
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short --branch
git fetch origin
git rev-parse origin/main
```

Always distinguish:

```text
local working tree
local main HEAD
local unpushed commits
origin/main
last runner-backed green baseline
current-head CI
live workstation runtime
```

Do not collapse these into a single "current" claim.

Current remote and checks are always resolved dynamically from origin/main. This document does not embed old SHAs or historical green runs as current evidence. If GitHub has no check result for the fetched HEAD, record that current status as unavailable.

## 3. Current cross-product protocol — v1.1

Active contract:

```text
contract_id = lumenis-ggi-cross-product
version     = 1.1.0
fingerprint = 68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f
```

Current formal ecosystem identities:

```text
序境 / LUMENIS              = Production Core / Production Truth
序蕴 / LUMENIS Intelligence = Shared Intelligence Assets
序衍 / LUMENIS Growth       = Research / Growth Truth
序枢 / LUMENIS Command      = Engineering Evidence / R&D control sidecar
```

The machine contract in `00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json` is the blocking protocol artifact. `00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md` is its human-readable authority map. They must remain aligned.

Stable technical aliases/repository/package/API/DB identifiers are compatibility identities and must not be renamed merely for branding.

Do not mutate another repository merely because it appears in this registry. Cross-repository writes require that repository to be explicitly in the active task scope.

## 4. Canonical product model — already present, do not rebuild

Canonical production chain:

```text
External Data
→ Evidence
→ Canonical Data
→ Function
→ Metric
→ Truth Table
→ View Model
→ Visualization
→ UI / Report / Export
```

Canonical business chain:

```text
Source
→ Evidence
→ Event
→ Case
→ Insight
→ Decision
→ Action
→ Outcome
→ Evaluation
→ Learning Asset
```

These chains already exist in `README.md` and `AGENTS.md`. Do not create a second architecture or parallel truth to restate them.

Current four-domain ownership remains. The canonical definition is `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`:

```text
CTH               Subject-first Commerce Operations
BMP               Brand/Market-first
Shared Capability Content & Creation / Evidence / Research / Evaluation / Learning / AI Enhancement
SYSTEM            Collector / Runtime / Scheduler / AI Gateway / DB / Security / Permission / Settings / Recovery / Observability
```

### App-only target

The final LUMENIS Experience is a single Flutter application for Windows, macOS, Linux, Android and iOS. The legacy browser/Jinja/static presentation surface has been removed from `main`. No new public web product surface, parallel frontend or legacy visual reference path may be introduced. Retained contracts under `contracts/experience/` are binding inputs for Flutter surfaces.

## 5. Current source/runtime facts — source-audited, not live-certified by this handoff

The latest source audit identifies these existing owners/contracts:

```text
scripts/start_production.ps1              canonical Windows launcher
app.py                                    Flask Product Core entry
run_supervised.py                         process/health supervision
8201 /healthz                             core health target
9222 / 9223                               existing Resident Browser logical identities
experience_runtime.py                     transitional Experience migration binding
CTH-01 / AI-01                            explicit bound-screen claims in audited source
lumenis/shared/reporting/                  Shared Reporting canonical owner
lumenis/shared/evidence/                   Shared Evidence canonical owner
lumenis/shared/evaluation/                 Shared Evaluation canonical owner
lumenis/shared/learning/                   Shared Learning canonical owner
xhs_cookie_bridge.py                      XHS/RedNote controlled collector runtime
content_generation.py                     research → generation → Evidence → Evaluation → human feedback
```

Audited dependency foundations include Flask/Waitress, APScheduler, requests/httpx/aiohttp, BeautifulSoup/lxml, Playwright, SQLite, tenacity and Alembic. `package.json` is Playwright/tooling-oriented; it is not proof of a React/Next/Vite production frontend.

P1 Reporting, P2 Evidence and P3 Evaluation/Learning are converged under Shared Capability owners above. Retired root owners are forbidden by `scripts/audit_tools/verify_lumenis_single_product.py`. Shared Learning must never write AI-generated research directly into canonical external-event tables; learning remains a reviewed input to later decisions, not Production Truth.

Do not replace these with screenshot-derived or generic stack assumptions. If current source differs from a point-in-time audit, current source wins.

### Fixed source owners and current tool/runtime disposition

Use `00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md` for the fixed folder classification and per-task lookup route. Normal work follows the active owner row and its direct callers/contracts/tests; it does not repeat a repository-wide audit.

Current source establishes these boundaries:

- `.opencode/opencode.json` is a bounded **engineering** runtime configuration for development, audit, test and automation. OpenCode is not a Flutter feature, model provider, API owner or Production Truth owner.
- `lumenis/system/ai_gateway/` is the canonical SYSTEM AI runtime owner. Ollama is a local provider behind that gateway; `local_ai_client.py` and `/api/local-ai/*` are current compatibility callers to reconcile, not a reason to create a second gateway. A configured provider is not `ACTIVE` until its daemon, model, real caller, fallback and Evidence pass runtime acceptance.
- `lumenis/system/collector/` and `lumenis/system/browser/runtime/` are the canonical collector/browser owners. `xhs_cookie_bridge.py` remains an active compatibility caller for the existing XHS/RedNote Cookie chain until migrated with behavior parity.
- Product Core currently contains an App account gate. The approved delivery boundary defers the LUMENIS product account until after internal beta. Round 1 must remove that global pre-beta blocker while keeping server Permission/effect fences and platform Cookie/session safety intact.

## 6. Screenshot architecture intake — disposition

The three user-provided screenshots were reviewed against the repository. The reliably readable architecture principles that match repository truth are represented by the canonical chains, truth hierarchy, main/local/origin separation and completion semantics.

Two screenshots were too low-resolution for exact line-by-line extraction. Their unreadable package names, versions, commands or implementation claims were **not imported as truth**. Current code, contracts and acceptance evidence remain authoritative.

Rule for later higher-resolution re-ingestion:

```text
Screenshot statement
→ locate current owner/source/manifest/test
→ VERIFIED / ALREADY_COVERED / CANDIDATE / CONFLICT / UNVERIFIED
→ update existing canonical file when possible
→ create a new owner only when no valid owner exists
```

## 7. Current acceptance semantics

Use only these meanings:

```text
IMPLEMENTED = code exists
TESTED      = scoped automated tests pass
VERIFIED    = runtime/E2E evidence proves behavior
RELEASED    = required production/security/recovery/rollback gates pass
OPERATING   = real operation produces required live/scheduled evidence
```

This handoff does not claim live workstation health, release or operation.

```text
8201 live workstation health = NOT VERIFIED by this handoff
Playwright live acceptance   = NOT VERIFIED by this handoff
RELEASED                     = NO NEW CLAIM
OPERATING                    = NO NEW CLAIM
```

Check CI and runtime evidence for the exact current HEAD before making a release or operation claim.

## 8. Codex resume protocol

After the bootstrap and local/remote reconciliation:

```text
preserve unknown/uncommitted/unpushed valid work
→ compare local HEAD vs origin/main
→ read GitHub checks for the fetched origin/main commit
→ do not repeat already-merged gate/contract/brand/handoff repairs
→ inspect exact active owner/caller/contract/tests
→ reuse/adapt/bind before rebuild
→ scoped tests
→ affected regression
→ runtime/E2E when required
→ evidence
→ coherent mainline commit/push
→ current main CI when runner is executing normally
→ next unresolved production-acceptance gate
```

Never reset/clean valid local work merely to match remote. Never treat local-only code as GitHub-complete.

### Three-delivery red line

Execute and report product delivery in this order only:

```text
Round 1  App Experience: UI + layout + PC/mobile semantic recomposition + UX motion
Round 2  Backend/recovery: existing capability + API/Permission/Evidence + Ollama/Cookie binding
Round 3  Closed-loop internal beta: real workflow E2E + recovery + release evidence
```

Apple, ChatGPT and TRAE inform only restraint, content hierarchy, progressive complexity and visible task/execution/result feedback. They do not add or replace features. OpenCode/Codex stay in the engineering layer. Product functions and business semantics must survive all three rounds.

## 9. Non-regression boundaries

Do not create a second Evidence, Canonical Data, Metric, Permission, DB, Runtime, API, Design System or Collector truth.

Do not make 序蕴、序衍、序枢 hard runtime dependencies of 序境. Do not share production databases across products. Do not allow AI/research artifacts to overwrite LUMENIS Production Truth automatically.

Do not weaken CI, delete legitimate tests, broaden quarantine or use `continue-on-error` to manufacture green status. Repository-deterministic product failures remain blocking. Runner/DNS/package-registry failures are execution-layer failures and must be reported as `EXECUTION-LAYER UNVERIFIED`, never rewritten as product PASS or product FAIL.

## 10. Historical documents

Dated takeover/handoff files before this `CURRENT` entry remain historical evidence only. They may explain provenance but must not be used as a current HEAD, current CI, current protocol or current completion claim without re-verification.

## 11. Blocking consistency guard

The LUMENIS Product Gate is the single blocking repository workflow for cross-product contract + takeover governance. Do not create a second workflow for the same assertions.

It must run:

```text
python scripts/audit_tools/verify_lumenis_ggi_contract.py \
  00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json

python scripts/audit_tools/verify_codex_takeover_governance.py

python scripts/audit_tools/verify_lumenis_single_product.py
python scripts/audit_tools/verify_experience_authority_exclusive.py
python scripts/audit_tools/verify_experience_anti_template.py
```

The Experience checks are App-only. Historical browser implementation has been removed from `main`; retained contracts under `contracts/experience/` may inform Flutter binding but never act as a second Experience authority.

The second check prevents regression of the CURRENT takeover path, v1.1 protocol identity, root agent routing and human/machine contract alignment. A runner-level 0-step failure means the check did not execute; it is not a passing or failing repository assertion.
## Historical remote cutover checkpoint

Commit `3ba304f5d752dabcdc40531ce176f189527c29af` is the historical checkpoint at which the App-only surface cutover was recorded. It is not evidence of the current remote HEAD or branch inventory. Before any takeover, release or cleanup claim, fetch `origin` and verify local `main`, remote-tracking `origin/main`, and live `git ls-remote --heads origin`; only a live result containing `refs/heads/main` is current evidence. See the branch-cleanup gate in `AGENTS.md` §2 and `README.md` §7.
