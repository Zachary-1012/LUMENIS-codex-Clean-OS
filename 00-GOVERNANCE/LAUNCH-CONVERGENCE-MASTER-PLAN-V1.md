# LUMENIS Launch Convergence Master Plan v1.0

Status: SUBORDINATE ROUND 15 LAUNCH GATE / NOT THE TASK-SEQUENCE AUTHORITY
Scope: Current Windows production-development workstation and `main`
Primary objective: Move LUMENIS from Production Convergence into Launch Convergence with minimum rework, minimum Codex quota waste, and maximum launch velocity.

Execution authority remains root `AGENTS.md` with the engineering source responsibility and complete retained acceptance coverage in
`LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md`. This plan applies only inside the active
C6 integration scope and retained ROUND 15 requirements; it may not bypass a real dependency, start a Luna Batch, or act as a second Product/Experience authority.

---

## 1. Phase transition

Historical launch lifecycle (current stage comes from CURRENT):

```text
LAUNCH CONVERGENCE
```

The launch lifecycle inside its approved round is:

```text
START
→ VISIBLE
→ USABLE
→ FIX LAUNCH BLOCKERS
→ LAUNCH
```

Production Convergence work is not reopened unless current executable evidence proves that a production blocker has regressed.

The goal is no longer to make the repository progressively cleaner. The goal is to make LUMENIS visible, operable, evidenced, stable, and launchable.

---

## 2. Verified remote baseline

The canonical remote repository is:

```text
Zachary-1012/LUMENIS-codex-Clean-OS
```

The only writable development, integration, and production-candidate branch is:

```text
main
```

At the time this historical plan was created, the then-verified remote `main` HEAD was:

```text
1f73070d20ee9183ef244f8da2163fe2edb38869
```

That commit contains the previously validated production-convergence implementation and the single-mainline governance update.

The corresponding `Verify LUMENIS` workflow run #123 completed successfully. Blocking compile, CI-manifest validation, and clean-checkout hermetic pytest all completed successfully.

These are provenance only. They do not establish the current remote HEAD, CI,
Windows working tree or runtime state; every round/task resolves those live.

---

## 3. Current facts that still require local evidence

The next executor must verify only the local facts that cannot be proven from GitHub:

```text
D:\LUMENIS_REBUILD\序\序境 local HEAD
working tree state
unpushed commits
local-vs-origin/main relationship
current runtime/process state
current /healthz result
current browser-visible product state
```

This is a short Reality Check, not a repository audit.

Do not spend quota rediscovering architecture, historical branches, old paths, prior audits, or already-verified CI work.

---

## 4. Launch priority rule

Every task must first answer:

```text
DOES THIS DIRECTLY INCREASE THE PROBABILITY OF LAUNCH?
```

If YES, execute it.

If NO, defer it unless it prevents safe launch.

### Launch-critical examples

- application cannot start;
- health endpoint fails;
- frontend cannot load;
- critical API fails;
- canonical data cannot flow to a user-visible result;
- permission blocks required legitimate operation;
- runtime crashes or becomes unstable;
- critical user action does not complete;
- evidence/provenance is missing for a production result;
- security, recovery, rollback, or deployment has a blocking defect.

### Deferred examples

- architecture beautification;
- repository reorganization;
- broad refactoring without a launch blocker;
- documentation polishing unrelated to launch;
- new design-system exploration;
- historical branch archaeology;
- old-path archaeology;
- noncritical UI micro-polish;
- speculative platform research;
- expanding test count for its own sake.

---

## 5. Codex quota and efficiency policy

Codex quota is a production resource and must be spent on launch progress.

Target allocation:

```text
~5%   Reality Check / exact-state confirmation
~70%  Startup, user-visible operation, real-data flow, and blocker repair
~15%  Targeted regression and acceptance evidence
~10%  Release / deployment / rollback qualification
```

This is a directional budget, not a stopwatch requirement.

### Hard anti-waste rules

- Do not perform a full-repository audit unless a concrete launch blocker cannot be resolved without it.
- Do not reread unchanged large governance documents in the same session.
- Do not rerun already-green CI merely to reconfirm history.
- Do not rerun the full 4000+ regression after every leaf change.
- Do not generate duplicate handoff documents.
- Do not recreate branch strategy work.
- Do not create a new architecture, design system, Evidence owner, Metric owner, Permission owner, DB owner, or Runtime owner.
- Do not create new task/feature/codex/production/integration/handoff/research branches.
- Do not open routine PRs as an intermediate engineering path.
- Do not stop at analysis when implementation and verification are safely executable.

### Escalation threshold

If Codex spends meaningful execution time without moving one of these states forward:

```text
STARTED
VISIBLE
USABLE
BLOCKER_CLOSED
LAUNCH_READY
```

then the task direction must be re-evaluated immediately.

---

## 6. Exact execution order

### Gate L0 — Reality Check

Start only from:

```text
D:\LUMENIS_REBUILD\序\序境
```

Verify repository identity and local state:

```powershell
Set-Location D:\LUMENIS_REBUILD\序\序境
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git rev-parse HEAD
git status
git fetch origin
git rev-parse origin/main
```

Required decisions:

```text
LOCAL_EQUAL
LOCAL_AHEAD_VALID
REMOTE_AHEAD
DIVERGED_NEEDS_SEMANTIC_CONVERGENCE
UNKNOWN
```

Protect valid local work. Never use `git reset --hard`, destructive `git clean`, blind overwrite, or re-clone-overwrite as a shortcut.

Exit L0 as soon as the local state is safely classified and synchronized or intentionally preserved.

Do not expand L0 into repository archaeology.

---

### Gate L1 — Start

Use the existing launcher. Do not create a second launcher.

```powershell
Set-Location D:\LUMENIS_REBUILD\序\序境
powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
```

The current launcher is designed to:

- resolve the repository root from its own location;
- use the existing `.venv` Python runtime;
- check required production dependencies;
- supervise the Flask application on port 8201;
- reuse or clean stale 8201 processes deterministically;
- verify `/healthz`;
- ensure the resident browser processes for 9222/9223 where available.

Expected core health target:

```text
http://127.0.0.1:8201/healthz
```

L1 passes only when the application is genuinely running and core health succeeds.

If startup fails, repair only the concrete startup blocker before doing anything else.

---

### Gate L2 — Visible

Open the real product in a browser:

```text
http://127.0.0.1:8201/
```

Verify:

- page renders;
- critical assets load;
- navigation renders;
- no blocking frontend exception;
- no fake-success screen hiding backend failure;
- primary domain entry points are reachable.

L2 is about human-visible product reality, not test output.

If the browser cannot show the real application, that is the priority blocker.

---

### Gate L3 — Usable

Validate real user-operable flows across the four domains.

For each critical capability, use this acceptance chain where applicable:

```text
UI Entry
→ User Action
→ API / Service
→ Permission
→ Canonical Read/Write
→ Real Result
→ Evidence / Trace
→ Honest Error State
→ Targeted Test
→ E2E
```

#### CTH — Commerce Operations

Validate at least one real representative path through subject/context-driven operations, including the user-visible path from source/evidence into operational insight/action where currently implemented.

#### BMP — Brand & Market

Validate at least one real representative brand/market path through content/creator/metric/analysis/evaluation where currently implemented.

#### Shared Capability

Validate Evidence, Research, Learning Asset, Content Studio, Evaluation, and AI Enhancement only through currently implemented production paths. Do not invent missing product behavior.

#### SYSTEM

Validate the minimum launch-critical control plane: Runtime, Database, Permission, Security, Scheduler where required, AI Gateway where required, Recovery, and Observability necessary for launch.

The objective is not to prove every future capability. The objective is to prove the current launch-critical product is actually usable.

---

### Gate L4 — Real data and truth integrity

For every accepted user-visible result, preserve the production chain:

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

Never use the following shortcuts to claim usability:

- mock data presented as production data;
- placeholder values presented as measured values;
- missing or unknown converted to zero;
- API failure converted to business success;
- fabricated Evidence;
- fabricated AI facts;
- fake HTTP 200 success;
- UI-only completion without backend truth.

AI remains an enhancement capability and does not own Production Truth.

---

### Gate L5 — Fix launch blockers only

When a failure is found, classify it:

```text
P0 — prevents startup, core data integrity, security, or launch-critical user flow
P1 — materially prevents a required domain workflow or stable operation
P2 — important but does not block launch
P3 — polish / optimization / future improvement
```

Execution order:

```text
P0
→ P1
→ launch qualification
→ P2/P3 backlog
```

Do not expand a local bug into a broad refactor unless the current dependency graph proves the broader change is necessary.

Prefer:

```text
reuse
→ adapt
→ bind
→ verify
```

---

### Gate L6 — Proportional testing

Testing exists to protect launch progress.

Default progression:

```text
fast/static
→ targeted unit
→ affected integration
→ neighbour regression
→ representative/domain E2E
```

Widen testing only when the changed surface justifies it.

A full regression is required at the actual Release Candidate convergence point, not after every small repair.

Never obtain green by deleting, weakening, broadly skipping, or silently excluding legitimate tests.

Already-verified remote CI evidence should not be rerun merely because a new session started.

---

### Gate L7 — Stability, Security, Recovery, Rollback

Before launch, verify only the production-critical requirements:

#### Stability

- supervisor/runtime remains stable;
- required processes do not multiply uncontrollably;
- health remains truthful;
- critical API/UI path remains available.

#### Database

- one canonical production DB-path owner;
- tests remain isolated/disposable;
- no silent fallback to duplicate/stale DB paths;
- no destructive migration without explicit safety evidence.

#### Permission

Consequential actions must follow the current real permission/approval/effect contract. Denied or pending actions must not create forbidden side effects.

#### Security

No committed credentials, live cookies, sessions, private keys, production DB material, system prompts, or private reasoning.

#### Recovery

Prove that the required runtime can recover from the representative failure modes relevant to launch.

#### Rollback

Ensure there is a credible rollback path for the release candidate before public launch.

---

### Gate L8 — Launch Candidate

Launch readiness is evaluated using precise semantics:

```text
IMPLEMENTED = code exists
TESTED      = scoped automated tests pass
VERIFIED    = runtime/E2E evidence proves behavior
RELEASED    = required production/security/recovery/rollback gates pass
OPERATING   = real operation produces required live/scheduled evidence
```

`RELEASE_READY = YES` requires evidence for the actual blocking gates.

A green CI workflow alone is insufficient.

A running process alone is insufficient.

A browser-rendered page alone is insufficient.

Launch readiness requires a real user-operable path, truthful data flow, and required operational safeguards.

---

### Gate L9 — Deployment and public launch

After the local production candidate is launch-ready:

1. identify the existing supported deployment path from current source/configuration;
2. reuse existing deployment assets before creating new infrastructure;
3. provision only the minimum missing external resources required for launch;
4. deploy the exact validated production candidate;
5. verify public health, public UI, critical API, and one representative end-to-end user flow;
6. verify security boundaries in the deployed environment;
7. record rollback evidence;
8. declare `RELEASED` only after the public candidate passes the required gates.

Do not invent a public URL if none has been deployed and verified.

Do not treat local success as public deployment success.

---

## 7. Canonical product boundaries during Launch Convergence

LUMENIS has four product domains:

```text
CTH             Subject-first Commerce Operations
BMP             Brand / Market-first
Shared Capability
SYSTEM          Collector / Runtime / AI Gateway / DB / Security / Permission / Settings / Recovery / Observability
```

These boundaries are frozen for Launch Convergence unless a verified P0/P1 defect proves a contract change is necessary.

Do not use launch pressure as justification to create a second truth system.

Maintain one owner for each of the following:

- Evidence truth;
- Canonical Data truth;
- Metric truth;
- Permission truth;
- Subject Context;
- Runtime truth;
- API truth;
- Design System;
- Collector runtime;
- canonical production DB path.

---

## 8. Collector and external-platform boundary

Collector remains SYSTEM-owned and read-only for logged-in social collection flows.

Required status semantics must remain distinguishable where currently implemented:

```text
SUCCESS
EMPTY
BLOCKED
SESSION_EXPIRED
RATE_LIMITED
ERROR
OFFLINE
```

External browser/login/platform availability must be reported separately from core application health.

A platform login problem must not be reported as core LUMENIS runtime failure unless it actually prevents the required launch-critical user path.

---

## 9. Stop conditions for Codex

Codex should continue execution through implementation and verification without repeatedly asking for confirmation unless a real external blocker exists.

Legitimate stop/escalation conditions include:

- required credential or protected source is unavailable;
- a paid external resource must be purchased or approved;
- a destructive production-data action requires explicit approval;
- an unresolved migration materially risks real data;
- a legal/security decision cannot be made from current authorized policy;
- a high-risk external effect requires human authorization;
- a critical ambiguity would risk losing valid local work.

The following are not reasons to stop:

- a routine fix needs a targeted test;
- a current implementation needs binding to an existing API;
- a visible browser bug can be safely repaired;
- a launch-blocking local runtime bug can be diagnosed from available evidence;
- a coherent main commit can be produced and pushed safely.

---

## 10. Required execution report

Do not produce a long narrative report after every step.

Maintain the minimum launch-state report:

```text
REMOTE_MAIN_HEAD:
LOCAL_HEAD:
LOCAL_MAIN_STATUS:
WORKTREE_STATUS:

STARTUP:
HEALTH:
PRODUCT_VISIBLE:
PRODUCT_USABLE:

CTH_CRITICAL_PATH:
BMP_CRITICAL_PATH:
SHARED_CRITICAL_PATH:
SYSTEM_CRITICAL_PATH:

DATA_TRUTH:
PERMISSION:
SECURITY:
RECOVERY:
ROLLBACK:

TARGETED_TESTS:
FULL_REGRESSION:
MAIN_CI:

DEPLOYMENT:
PUBLIC_URL:

CURRENT_BLOCKERS:
RELEASE_READY:
RELEASED:
OPERATING:
```

Use `NOT VERIFIED` whenever evidence does not exist. Never guess PASS.

---

## 11. Direction-correction rule

If execution drifts into any of the following without a proven launch dependency:

- repository cleanup;
- architecture redesign;
- governance expansion;
- broad documentation work;
- design-system redesign;
- historical recovery work;
- branch workflow work;
- speculative new capabilities;
- large unrelated test runs;

stop that activity and return to the nearest incomplete Launch Convergence gate:

```text
START
→ VISIBLE
→ USABLE
→ FIX BLOCKERS
→ LAUNCH
```

The governing question remains:

> Can a user open LUMENIS, complete a real required task, receive a truthful result, and can that exact candidate be safely launched?

If not, work on the blocker that most directly closes that gap.

---

## 12. Definition of success

Launch Convergence succeeds when the product has moved from engineering assets to an evidenced operating candidate:

```text
real code
+ real runtime
+ real browser-visible product
+ real user action
+ real API/service behavior
+ real canonical data
+ real Evidence/trace
+ truthful error states
+ proportionate automated protection
+ security/recovery/rollback evidence
+ verified deployment
= launch
```

The repository is a means to the product. Repository neatness is not the product.
