# AGENTS.md — 序境 / LUMENIS Production Execution Router

> Purpose: compact model-neutral routing and safety rules for coding agents.
> This file is not a second README, architecture book, handoff log, or proof of runtime state.

## 1. Authority

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

Never use old chat, old README text, old commit messages, static prototypes or handoff claims to override current executable truth.

Documentation merged into `main` means the rule/plan exists; it does not mean the production capability is implemented.

## 2. Session start

Do not assume a local absolute path.

Start with only:

```text
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git rev-parse HEAD
git status
git fetch origin
git rev-parse origin/main
```

Confirm local repository identity. Preserve unknown/uncommitted work until classified. Never reset/discard it merely to obtain a clean tree.

### Single-mainline rule

`main` is the only long-lived development line and the only remote production-candidate truth.

A task branch may exist only as a short-lived isolation mechanism for one coherent change. Valid implementation, tests, governance and evidence must converge back into `main`; do not create a second long-lived production, integration, handoff or feature truth.

Before retiring an old branch, compare it with `main` by content and dependency ownership:

- `ahead_by = 0` → already absorbed; treat as retired.
- unique valid implementation/test/evidence → salvage or merge into `main` first.
- historical-only/superseded material → preserve only where it still has evidence value; do not re-promote it into active Production Truth.

Do not force-push `main`. Do not use branch names or old branch HEADs as proof that a capability is current.

## 3. Execution mode

Use model-neutral high-efficiency production execution:

```text
Progressive Disclosure
Minimal Context Loading
Source / Runtime Truth First
Reuse Before Rebuild
Batch Related Fixes
Proportional Testing
Persistent Execution
Explicit Completion Criteria
```

Do not begin by rediscovering or summarizing the entire repository.

Typical loop:

```text
ACTIVE GATE / TICKET
→ inspect exact owner / callers / contracts / tests
→ implement
→ scoped test
→ neighbour regression
→ runtime / E2E when required
→ evidence
→ coherent commit
→ merge/converge to main
→ update state/registry if required
→ next dependent gate
```

Do not stop after the first code edit if implementation, validation and repair are still executable.

## 4. Progressive document routing

Read only what the active change needs.

Always-use entrypoints:

- human/product orientation: `README.md`
- this router: `AGENTS.md`

Conditional canonical docs:

- human maintainability / feature closure / E2E / release: `00-GOVERNANCE/ENGINEERING-MAINTAINABILITY-AND-RELEASE-V1.md`
- Collector + Shared Capability closed loop: `00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md`
- third-party/open-source dependency/replacement work: `00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md`
- branch consolidation: `00-GOVERNANCE/SINGLE-MAINLINE-BRANCH-CONSOLIDATION-V1.md` when present
- point-in-time takeover evidence: `00-GOVERNANCE/handoff/` only when the current task actually depends on it
- historical evidence: `99-ARCHIVE/` only when migration/history is relevant

Task routing examples:

```text
DB/schema/migration → DB owner + affected contracts/tests + DB governance/playbook
Collector → Collector runtime/adapters + closed-loop canonical doc + relevant tests
Permission/write → Permission owner + action/approval contract + affected route/service/tests
Frontend/Experience → relevant current screen/runtime contract + backend binding + E2E
Startup/deployment → launcher/supervisor/health/config + relevant operations tests
Third-party change → actual manifests/imports + component register + license/release implications
Branch convergence → compare branch against main; salvage only unique valid implementation/test/evidence
Ordinary bug → affected source/caller/test only
```

Do not reread unchanged large documents in the same session.

## 5. Product ownership

LUMENIS has four product domains:

```text
CTH             Subject-first Commerce Operations
BMP             Brand / Market-first
Shared Capability
SYSTEM          Collector / Runtime / AI Gateway / DB / Security / Permission / Settings / Recovery / Observability
```

AI enhances the product; AI is not Production Truth.

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

## 6. No duplicate truth

Before creating a model/table/service/registry/runtime, dependency-trace the existing owner.

Prefer:

```text
reuse → adapt → bind → verify
```

Do not create a second:

- Evidence truth
- Canonical Data truth
- Metric engine/truth
- Permission system/truth
- Subject Context
- DB truth
- Runtime truth
- API truth
- Design System
- Collector runtime

A missing adapter does not justify a parallel platform.

## 7. Data truth and DB safety

Never conflate:

```text
0
NULL
UNKNOWN
NOT_AVAILABLE
NOT_COLLECTED
STALE
OFFLINE
ERROR
BLOCKED
PENDING / SCHEDULED
```

Forbidden: `missing → 0`, `UNKNOWN → healthy`, API failure → business success.

Tests/staging must use explicit isolated/disposable DBs and prove the protected production DB is unchanged when the task touches persistence.

Do not delete, rewrite, migrate or repair real production data without the required safety evidence/approval.

## 8. Permission and external effects

Consequential writes must use the real permission/approval/effect boundary. Denied or pending actions must not create forbidden side effects.

Representative policy states should remain distinguishable, including denied, pending approval, granted and permanent deny where the current contract supports them.

Do not fake write success to unblock UI.

## 9. Collector / Shared Capability closed-loop hard rules

Canonical owner: `00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md`.

Required direction:

```text
SYSTEM Collector
→ Source / Evidence
→ Canonical Content
→ Research
→ Learning Asset
→ Content Studio
→ Application Trace
→ Collector Tracking
→ Evaluation
→ Learning Version Update
```

Hard constraints:

- Collector is SYSTEM-owned; CTH/BMP/Shared may request collection but do not own parallel runtimes.
- Upload / Import / API / Collector converge into the same Source/Evidence/Canonical/Provenance truth.
- `MetricSnapshot` is append-only; do not overwrite prior observations.
- future T+ performance stays pending/scheduled until real time/data exists.
- AI may propose PatternCandidate/PromotionProposal but may not autonomously execute `Pattern → ADOPT`.
- Application Trace is required for Research → Creation → Evaluation closure.
- Fact Wall must fail honestly when factual Evidence/Brief support is absent.
- logged-in social Collector behavior is read-only.
- future Publisher is a separate capability with Permission → Approval → Effect Fence → legitimate integration → Audit/Evidence.
- `RELEASED != OPERATING`.

First real acceptance dataset remains the configured 60-episode 凉子访谈录 cohort. Do not hardcode its 20/20/20 split into universal research logic.

## 10. Continuous production DAG

Follow the currently approved dependency order unless current source proves a gate is already satisfied or a dependency has changed:

```text
G0  Repository Truth Convergence
G1  DB / Safety Foundation
G2  Source + Evidence Unification
G3  Collector Runtime
G4  Canonical Content Intelligence
G5  Research Engine
G6  Learning Asset Engine
G7  Write / Permission / Approval Closure
G8  Content Studio Production Binding
G9  Application Trace
G10 Performance Collector
G11 Evaluation → Pattern Validation
G12 Learning Version Update
G13 Shared + SYSTEM UI Binding
G14 凉子访谈录 60期真实 Acceptance Dataset
G15 Full Regression / Security / Recovery / E2E
G16 Release Gates
```

Do not redo a gate only because an old handoff says it exists. Verify the relevant current source/runtime/test evidence and continue.

## 11. Human engineering quality

When touching production code, leave it easier for another engineer to understand without changing behavior gratuitously.

Use `00-GOVERNANCE/ENGINEERING-MAINTAINABILITY-AND-RELEASE-V1.md` for naming, ownership, dependency direction, error semantics, configuration, feature closure and release rules.

Do not mass-rename/move code by filename. Before restructuring, identify caller, owner, data read/write, runtime path and tests.

Do not add ambiguous production names such as `new_final`, `utils2`, `temp_fix`, `copy`, or `misc`.

Do not delete dead/duplicate-looking code until imports, registries, dynamic loading, routes, scripts, tests and runtime paths prove it unused.

## 12. User-visible feature completion

A page, route or test existing is not completion.

For important user-operable features, prove as applicable:

```text
UI Entry
→ User Action
→ API / Service
→ Permission
→ Canonical Read/Write
→ Real Result
→ Evidence / Trace
→ Honest Error State
→ Test
→ E2E
```

Use the Feature Acceptance Matrix contract in the engineering standard.

No fake values, fake 200s, `undefined`, `NaN`, `[object Object]`, or silent missing→0 transformations in production acceptance.

## 13. Testing policy

Default progression:

```text
fast/static
→ targeted unit
→ affected integration
→ neighbour regression
→ representative/domain E2E
→ full regression at convergence/release points
```

Do not run thousands of unrelated tests after every leaf edit.

Widen testing when shared primitives, persistence, permission, domain contracts or runtime infrastructure change.

Never delete, skip or weaken a legitimate test simply to obtain PASS. Classify failures before changing production code.

## 14. CI truthfulness

CI checks must be semantically classified as `BLOCKING`, `ADVISORY` or `INFORMATIONAL`.

Syntax errors, required test infrastructure missing/not executing, critical DB/data-integrity failures, critical permission failures, critical E2E failures and P0 security failures must not be hidden by `continue-on-error` or swallowed exceptions.

A green workflow is not sufficient if blocking work did not actually execute successfully.

Environment/Production-Live tests may be separated from secret-free clean-checkout CI only when their dependency is explicit. `excluded != PASS`.

## 15. Startup / runtime

Use the existing production launcher/supervisor path unless current evidence proves it must change. Do not create a second launcher as a shortcut.

Do not hardcode a developer-specific local repository path in new code.

Startup acceptance requires more than a live process:

```text
dependencies
→ config
→ app boot
→ supervisor/runtime
→ port
→ health
→ required runtime initialization
→ critical API/Experience
```

Report external browser/login/source dependencies separately from core application health.

## 16. Third-party / OSS

Before adding a third party, inspect actual current dependencies and prove a real capability gap.

Canonical register: `00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md`.

Prefer:

```text
LUMENIS Contract → Adapter → Third-party implementation
```

Third parties do not become LUMENIS Production Truth owners. Track license/attribution, current usage, integration boundary and replacement plan.

OpenTelemetry, Langfuse OSS and Temporal are evaluation candidates only unless current source/manifests prove adoption. Do not install them merely because they are named in governance.

## 17. AI/security boundaries

Never expose or commit:

- system/developer prompts or private reasoning
- credentials/API keys
- cookies/session material
- browser/CDP secrets
- real production DB files
- privileged hidden tool details

Public adapters such as ChatGPT/MCP must use allowlisted/versioned internal contracts, authentication, Subject Context, domain, permission and provenance/policy boundaries. Do not expose raw DB/Collector session internals.

## 18. Git discipline

- `main` is the only long-lived development line.
- short-lived task branches must converge back into `main` when their valid work is complete.
- do not leave a parallel implementation only on a branch.
- preserve unknown local work before convergence.
- use coherent-purpose commits.
- do not force-push `main`.
- do not commit production DB, secrets, cookies, sessions, caches or generated junk.
- do not claim an unpushed/local commit exists remotely.
- before retiring a branch, prove either `ahead_by = 0` or that its unique valid work has been absorbed into `main`.

## 19. Completion semantics

Use states precisely:

```text
IMPLEMENTED = code exists
TESTED      = scoped automated tests pass
VERIFIED    = runtime/E2E evidence proves behavior
RELEASED    = required production/security/recovery/rollback gates pass
OPERATING   = real operation produces required live/scheduled evidence
```

`PRODUCTION_READY = YES` only when all blocking production gates are evidenced. Otherwise report `NO` with real blockers.

Continue through implementation → validation → repair while work is safely executable. Do not stop merely to ask for approval between routine engineering steps.

## 20. Legitimate stop conditions

Stop for user input only when required by a real blocker such as:

- required credential/source is inaccessible;
- destructive production-data action needs explicit approval;
- unresolved migration conflict creates material data risk;
- legal/security decision cannot safely be inferred;
- high-risk external effect requires real human approval.

Large code volume, long tests, context size or many files are not themselves blockers.

## 21. Final reporting

Keep progress compact. Final reports should state evidence, not essays:

```text
Branch / Start HEAD / Final HEAD
Implemented / commits
Canonical DB/config
Tests actually run
Startup / health
Domain + critical E2E
Permission / Evidence / Trace
CI
Security / Recovery / Rollback
Third-party changes
Branch convergence status
Remaining blockers
RELEASED = YES/NO
OPERATING = YES/NO
PRODUCTION_READY = YES/NO
```

Do not use documentation completion, API 200s, test counts or commit counts as substitutes for real product closure.
