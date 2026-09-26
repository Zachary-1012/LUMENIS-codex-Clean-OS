# AGENTS.md — 序境 / LUMENIS Production Execution Router

> Purpose: model-neutral routing, evidence, safety and completion rules for coding agents.  
> This file is not a second README, architecture book, handoff log, or proof of runtime state.

This root file is the **only repository execution router**. Product Architecture,
Experience Constitution, source-owner and screen contracts remain authoritative only
for their named domains; reports, taskbooks, PDFs, spreadsheets, screenshots,
wireframes and generated prompts are evidence or working artifacts, never competing
execution instructions.

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

Never use old chat, old commit messages, stale README text, static prototypes or handoff claims to override executable truth.

Documentation merged into `main` proves only that the rule/document exists. It does not prove the production capability is implemented, tested, live-verified or released.

For implementation decisions, apply this routing order without turning it into a
second product or design authority:

```text
Current source / runtime / DB / API / Permission / Evidence truth
→ this AGENTS.md execution router
→ AI-native product constitution principle layer
→ sole Product Architecture
→ sole Experience Constitution for user-visible work
→ Source Owner Index and approved Multi-Surface Decision
→ current detailed Screen Specification for the active screen
→ bounded Sol Task Card
→ taskbook/report/PDF/sketch as non-authoritative evidence only
```

### Mandatory Codex bootstrap

This root `AGENTS.md` is the first coding-agent instruction boundary. Before changing product code, Codex must resolve the current remote truth and then read the CURRENT governance path:

```text
AGENTS.md
→ 00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md
→ 00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md
→ 00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md
→ 00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md
→ 00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md
→ 00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md
→ 00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md
→ 00-GOVERNANCE/PRODUCT-POSITIONING-CURRENT.md
→ README.md
→ 00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md
→ 00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json
→ 00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md
→ exact current source / runtime / DB / API / Permission / Evidence / tests for the active slice
```

Hard rules:

- current HEAD comes from `git fetch origin` + `git rev-parse origin/main`, never from a document, screenshot, chat or pasted SHA;
- `00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md` is the mandatory principle layer for every coding-agent task; it adds no second product, architecture, design, data, Permission or release authority;
- the active cross-product contract is `lumenis-ggi-cross-product` **v1.1.0** with fingerprint `68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f`;
- the Markdown registry is a human-readable mirror; the JSON contract plus blocking validators are the machine gate;
- if CURRENT governance artifacts disagree, fail closed and reconcile them before cross-product work;
- dated handoffs, archived audits and legacy repositories are provenance only unless current executable evidence revalidates them;
- do not write to another repository merely because it is listed in the cross-repo registry; that repository must be explicitly in the active task scope.

### AI-native constitution execution chain — NON-BYPASS

Every coding-agent task must travel through this existing execution chain; the
constitution is a principle layer inside the chain, not a parallel authority:

```text
origin/main truth
→ AGENTS.md
→ AI-NATIVE-PRODUCT-CONSTITUTION.md
→ current Product / Architecture / Owner / Contract
→ bounded Task Card
→ current source and runtime truth
→ implementation
→ proportional automated tests
→ Integration / E2E when applicable
→ runtime / recovery evidence when applicable
→ blocking gates
→ commit
→ push
→ remote verify
```

Classify unresolved requirements honestly: `MACHINE_BLOCKING` failures block
delivery; live/environment evidence that is unavailable is `LIVE_NOT_VERIFIED`
or `BLOCKED`; product/commercial choices that belong to the Product Owner are
`HUMAN_DECISION_REQUIRED`. None of those states may be rewritten as PASS.

Non-bypass red lines:

- never delete, skip, weaken, quarantine or move a legitimate failing test to another tier solely to obtain green;
- never turn a blocking gate into advisory / informational or add `continue-on-error` solely to bypass a failure;
- never convert missing/unknown/uncollected data to zero, fabricate HTTP success, or use Mock/fixture/demo data as production acceptance;
- never bypass the current Permission, Evidence, Canonical owner, Effect Fence or approval boundary to complete a task;
- never use reset/clean/checkout/restore or broad staging to overwrite a protected dirty worktree; reconcile stale candidates against current `origin/main` in an isolated clean worktree/archive, then reapply only validated unique work;
- never expand product scope, add a new product/owner/architecture/design authority, or activate a new external effect without explicit Product Owner authorization;
- before a delivery commit, run `python scripts/audit_tools/verify_ai_native_constitution.py`; its failure is `MACHINE_BLOCKING`.

## 2. Canonical workspace and mainline

Current Windows workstation entrypoint:

```text
D:\\LUMENIS_REBUILD\\序\\序境
```

Expected repository:

```text
Zachary-1012/LUMENIS-codex-Clean-OS
```

`main` is the only writable development, integration and production-candidate branch.

Start every engineering session with:

```powershell
Set-Location D:\\LUMENIS_REBUILD\\序\\序境
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short --branch
git fetch origin
git rev-parse origin/main
```

Preserve unknown/uncommitted/unpushed work until classified. Never reset, clean or overwrite valid local work merely to make the tree look clean.

### Local-to-main truth gate

Always distinguish:

```text
local main HEAD
local working tree
local unpushed commits
origin/main
```

Do not claim local-only work exists on GitHub. If local valid work is ahead, preserve it, integrate the newest `origin/main` without destructive overwrite, run proportional regression, then commit/push coherently.

### Accepted Batch online-publication gate

For every Sol-accepted implementation Batch, close local work and online truth in
the same delivery cycle. Sol must inspect the exact staged files and diff,
record the Batch's tests, runtime/E2E evidence and unresolved limits, update the
owning Round evidence **and** this repository's CURRENT online status, then make
a coherent mainline commit and push it. Before calling the Batch delivered or
starting a dependent acceptance gate, fetch again and verify `HEAD`,
`origin/main`, live `refs/heads/main`, and the published status/evidence paths
refer to that accepted source. A progress-only commit never substitutes for
unpublished implementation. Conversely, a source commit without its online
status update is an incomplete handoff. The blocking governance validator
checks this co-publication on the current commit.

If a push or remote read fails, preserve the work and report its exact local
commit, `LOCAL_ONLY / NOT_PUBLISHED` state and blocker. Continue independent
safe work, but do not tell an online reader that the Batch or Round is delivered.
Never bulk-stage a dirty tree to satisfy this gate: classify and protect every
unrelated or unverified path, including credentials, Cookies and production DBs.

### Single-mainline hard rules

- do not create routine task/feature/codex/production/integration/handoff/research branches;
- do not open routine PRs as an intermediate development path;
- do not force-push `main`;
- historical side branches are read-only evidence only;
- if an old branch has unique valid work, compare it once, absorb only the unique valid implementation into `main`, then continue on `main`.
- before and after a delivery, run `git fetch origin --prune`, inspect `git branch --format="%(refname:short)"`, `git branch -r --format="%(refname:short)"`, and `git ls-remote --heads origin`; accepted inventory is exactly local `main`, `origin/main`, and live `refs/heads/main`;
- if any side branch exists, inspect its unique commits and paths, preserve valid capability on `main`, delete only verified redundant branches, and repeat the live check; cached refs alone are not branch-cleanup evidence.

## 3. Execution mode

Use:

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

Do not begin every task with a full-repository rediscovery. Load only the owners, callers, contracts, tests and runtime paths required by the active gate.

The fixed source classification and resume path is `00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md`. Use its owner row for normal work. A full-repository re-audit is permitted only for the structural triggers listed there; a local gap, stale historical note or runner failure is not a trigger.

### Fifteen-round closed-loop red line

All current product execution preserves the approved 15-round coverage and dependency
map in `LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md`: current truth; authority/Only-One;
database; identity/Permission/Evidence; runtime; collector/browser; AI/Agent/Shared
engines; cross-surface foundation; Golden Pages; CTH monitoring; CTH decision loop;
BMP market loop; BMP content/campaign loop; remaining ACC/AI/Shared/SYSTEM
Experience; then closed-loop internal beta/release. The rounds are fifteen acceptance
checkpoints, not fifteen mutually blocking implementation windows. Do not omit a
checkpoint or use a later implementation as proof that an unmet dependency passed.

Sol may run bounded Luna Batches from multiple rounds concurrently in one product
war room when their actual entry dependencies are satisfied and their files,
canonical owners, migrations, tests and runtime resources do not conflict. The
Product Owner's parallelism target is ten **safe, active** Luna workers when
the host actually supports ten; ten is also the approved operating ceiling,
never permission to exceed a lower host limit. Keep a ready/active/blocked
Batch queue, fill available safe slots without serializing independent work,
and report the observed host capacity, actual active count, queued count and
the reason for any shortfall. Never claim ten workers are running when fewer
are, or invent a conflicting Batch solely to fill a slot. Sol owns the shared
worktree, integration order, conflict resolution and every PASS / REWORK / BLOCKED /
SPLIT / REORDER decision. Each Luna receives exactly one Batch and may not cross
into another Batch automatically. A completed Batch is only a report until Sol
reads its base/final state, diff, tests, runtime/E2E evidence and blockers. Publish
overall progress against all fifteen checkpoints as each closes; a separate Codex
window is not required. Before assigning a new Batch, resolve current `origin/main`,
local state, dependencies, protected work and overlapping active owners again.
Parallel implementation does not permit a dependent round to be accepted before
its predecessor exit gate; the Source Owner Index retains the ordered acceptance
sequence.

### Continuity after a Sol decision

The fifteen rounds are acceptance checkpoints, not one-attempt or session stop
points. `REWORK`, `SPLIT` and `REORDER` require Sol to re-resolve current
remote/local truth and select the next safe executable Batch; a Luna stopping at
its one-Batch boundary does not stop the active Round or the product program.
A localized `BLOCKED` owner pauses only that owner; continue independent work
whose entry gates are met. When a Round truly passes and the Product Owner has
authorized continuous delivery, publish its evidence and hand off or start the
next eligible Sol task before closing the prior task. If continuation cannot
be confirmed, report it as idle rather than claiming work is running. Stop
the overall program only on an explicit user pause or a genuine §22 blocker
that leaves no safe in-scope work; never weaken an exit gate to avoid a pause.

### REAL USER WORK E2E ACCEPTANCE — ROUND 02 through ROUND 15

`00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md` is the single content owner for the eight real-delivery questions, per-round constraints, `REAL DELIVERY CARD`, completion semantics, final seven statuses and the six Section 23 commercial-readiness gates. It is an execution/acceptance overlay, not a second Product Architecture or Experience authority, and it does not add a sixteenth round.

Every ROUND 02–15 task must define and pass at least one `REAL USER WORK E2E ACCEPTANCE` before Sol may return `PASS` or publish the next round as executable. The Round Charter, contributing Luna Task Cards and Sol report must route through the Overlay's `REAL USER JOB`, `ENTRY`, `REAL INPUT`, `END-TO-END PATH`, `USER-VISIBLE RESULT`, `FAILURE/RECOVERY`, `EVIDENCE` and `ACCEPTANCE ASSERTION` gates and include `真实用户工作闭环验收`, `REAL DELIVERY CARD` and `COMMERCIAL OVERLAY IMPACT`. Missing E2E evidence forces Sol to return `REWORK` or `BLOCKED`; code/HTTP success, fixtures, mocks, hard-coded examples, screenshots, builds, tests, CI or model output cannot pass alone.

`00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md` is the single subordinate contract for default `GLOBAL / ALL`, focus-only Subject/BrandFocus selection, honest uncollected states and data-maturity acceptance. It governs one internal full-universe edition over one Product/Core/Data/Evidence/Permission/API/Context/Experience stack; no acceptance dimension may become a separate product or release. Every related Round Charter and `REAL DELIVERY CARD` must add `GLOBAL UNIVERSE / DATA MATURITY IMPACT` and report `Global Commercial Coverage`, `Global Brand Coverage` and `Guangzhou Taikoo Hui Reference Coverage`. Guangzhou Taikoo Hui is the controlled depth-reference Subject, never the product default or a substitute for global coverage. Only all three `YES` permits `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=YES`; later-round functionality must be reported honestly and must not block unrelated work.

Every related round also runs `RANDOM ENTITY DATA ACCEPTANCE` against the canonical registry with a recorded rotating/stratified seed and non-reference commercial, brand and cross-region samples. Covered/mature samples may not return silent blank, all-zero, missing→0, placeholder or invented content; a real defect forces `REWORK`/`BLOCKED`. If the canonical sample population does not yet exist, record sample count zero and the owning gap rather than fabricating data. ROUND 15 expands cumulative inspection and is never the first random check.

Every ROUND Charter, relevant Luna Task Card and Sol acceptance also includes `CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION`. Research the current business, engineering and page gap against directly relevant official sources, industry cases, papers or standards, maintained high-quality GitHub projects and applicable UI/UX flows. Record URL, accessed date, version or commit, license, maintenance status, commercial/security boundary, `ADOPT / ADAPT / DEFER / REJECT` decision and the exact mapping back to canonical LUMENIS owners, Evidence, Permission, workflow and Experience. External material is principle-only and cannot become a second product/design authority or Production Truth. Any improvement must be versioned and pass applicable real E2E/page/effect evaluation, regression, observability and rollback gates. If research finds no justified in-scope upgrade, record `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE` with evidence rather than inventing work.

When a round involves a page, deliver and run the actual operable page on every target surface promised by that round under the sole Experience Constitution and a Sol-approved `DESIGN_READY` specification. Commercial-readiness gaps are recorded as `COMMERCIAL READINESS GAP / BLOCKED FOR COMMERCIAL_READY`; they set `COMMERCIAL_READY=NO` but do not stop unrelated in-scope engineering work.

The Product Owner accepted the ROUND 01 source audit, missing-capability register,
multi-surface direction and 15-round mapping on 2026-09-21 as the execution baseline.
That approval closes the planning gate only. It does not accept an implementation,
screen, provider, migration or release claim. Implementation may proceed through the
parallel war-room rule above; every round still closes only through its own Sol
acceptance checkpoint and current remote/local evidence.

Preserve product position, functions, rules, data sources and workflow meanings. Apple, ChatGPT and TRAE are Experience-principle references only and never authorize new product features. OpenCode/Codex are engineering runtimes; Ollama and the approved Jev candidate are providers behind the one SYSTEM AI Gateway. Jev is limited to typed decision/evaluation tasks and cannot own Permission, Evidence, Production Truth or effects. Media-platform Cookie/session authorization remains separate from the future LUMENIS product account. The LUMENIS account is deferred until after internal beta; pre-beta product access must not be blocked by an account wall, while server Permission and effect fences remain enforced.

Business work is selected in this order: Product Positioning → Industry Business
Logic → Real User Jobs → Deliverable Outcomes → Experience → Data/Runtime
Requirements → source implementation. Audit current owners before adding work;
an absent module is a gap to map into an existing Round, not automatic authority
for a new product surface or feature. External competitors and the named design
research sites are non-exclusive inspiration, never product authority or a limit
on relevant current Web/GitHub research. Users see tasks, content, results and
available actions; internal agents, tools and research axes remain behind the
canonical product boundary.

Default loop:

```text
ACTIVE GATE / TICKET
→ inspect exact source owner / caller / contract / tests
→ verify existing capability before adding dependencies
→ reuse / adapt / bind
→ implement on main
→ scoped test
→ affected regression
→ runtime / E2E when required
→ evidence
→ coherent commit
→ push origin main when safe
→ main CI when required
→ next dependent gate
```

## 4. Product ownership

```text
CTH             Subject-first Commerce Operations
BMP             Brand / Market-first
Shared Capability
SYSTEM          Collector / Runtime / Scheduler / AI Gateway / DB / Security / Permission / Settings / Recovery / Observability
```

This product definition is locked. Repository cleanup must preserve the four domains, their owners, business workflows and shared services. A legacy-looking folder or identifier is not evidence that the capability is obsolete. Before removing a path, map its implementation and contracts to the current owner; retain the newer owner or migrate any unique behavior first. This repository is the only code-change target for 序境. The three companion products remain represented by the cross-repository registry as ecosystem specifications and ownership boundaries.

The user-facing product abbreviation is **BMP**. Existing account and storage interfaces still carry `product_id=ZBMP` and `domain_id=zbmp` as compatibility identifiers; App labels and screen copy must resolve them to BMP. An identifier migration must preserve authorization and stored history across the account, database, API adapter and acceptance-test owners.

User-facing App text and accessibility labels use product and business language, not implementation or governance terminology. Preserve distinct business states (such as no records, not collected, unavailable and access restricted); never merge them into a misleading empty state or fabricate zero values.

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

### Continuous capability evolution contract

Collection, browser acquisition, creation, AI, agents, reporting, evaluation, learning and every CTH/BMP/Shared/SYSTEM workflow are versioned capabilities, not frozen modules. During the 15-round build and after release, improve a capability when real Evidence, outcome feedback or evaluation identifies a bounded gap. Reuse its canonical owner and preserve the Product Architecture, workflow meaning, Permission, Evidence lineage and state semantics; never create an alternate owner in order to learn faster.

Controlled evolution path:

```text
Evidence + Canonical Input
→ Versioned Execution
→ Real Result
→ User / Outcome Feedback
→ Evaluation
→ Versioned Learning Asset / Model / Skill / Configuration
→ Shadow or Targeted Validation
→ Permission / Approval Gate
→ Promoted Capability Version
→ Observability + Rollback
```

Learning is derivative. It may recommend, evaluate and promote a tested version through the canonical owner, but it must never silently rewrite source Evidence, Canonical Truth, permissions, approvals or external effects. Every user invocation must produce the real requested result or an explicit unavailable/error/blocked state; fixtures, empty output, HTTP 200, provider registration and unverified AI text are not completion.

### Multi-surface Experience direction

LUMENIS is one product with four approved surfaces: Public Website, Web Workspace, Desktop App and Mobile Companion. `00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md` records their approved roles and delivery route; it is subordinate to the sole Product Architecture and Experience Constitution.

The Flutter application under `app/` is the shared implementation for Web Workspace, Windows/macOS/Linux Desktop and Android/iOS Mobile. The committed `website/` foundation is restricted to the Public Website; its presence is not proof of configured commercial entry or release acceptance. Flask routes remain the one Product Core/API/ViewModel boundary; neither surface may create parallel business logic, data, Permission, Evidence or runtime truth. Historical `templates/`, `static/` and `experience_v2/` must not be restored. Before removing any remaining user-visible capability, trace its business purpose, ViewModel, permission, state, Evidence and acceptance evidence into the canonical Product Core and approved surfaces.

All UI/UX/visual/presentation decisions remain subordinate to the sole authority:

`00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md`

Historical UI/UX documents, screenshots, copied Apple/GPT reference packs and old design systems are forbidden development inputs. The only permitted external-reference input is the bounded abstract principle mapping recorded in the current Experience Constitution; it cannot add features, copy layouts or become a second design authority.

The approved audit PDF, its 44 sketches and any later AI/Figma/wireframe output are
`DESIGN_EXPLORATION` unless the applicable `<SCREEN-ID>.md` has been reviewed and
promoted to `DESIGN_READY` under the Experience Constitution. They may illustrate
questions and surface deltas, but they may not be copied directly into code, used to
authorize a shared renderer, or treated as acceptance evidence. If an implementation
copies a PDF/sketch or generic repeated frame without the current screen-specific gate,
Sol returns `REWORK`.

## 5. No duplicate truth

Before creating a new model/table/service/registry/runtime, dependency-trace the existing owner.

Prefer:

```text
reuse → adapt → bind → verify
```

Do not create a second:

- Evidence truth
- Canonical Data truth
- Metric truth
- Permission truth
- Subject Context
- DB truth
- Runtime truth
- API truth
- Design System
- Collector runtime

A missing adapter does not justify a parallel platform.

## 6. Current source truth

Resolve the current remote `main` commit at the start of each task. Do not use a historical SHA, audit, handoff, chat, or README as the current checkout or capability baseline.

Verify each capability claim against the source, contracts, routes, runtime behavior, scoped acceptance evidence, and exact current commit. If any of these disagree, current executable source and runtime evidence take precedence; record unknown behavior as unverified.

## 7. Codex local development tools

The following may be used by Codex when installed on the workstation:

```text
Git CLI
Playwright MCP
Filesystem MCP
ripgrep / rg
fd
jq
sqlite3 CLI
curl
```

Rules:

- these are development/inspection/acceptance tools, not automatically LUMENIS production dependencies;
- Filesystem MCP must be scoped to the active repository/workspace, not entire disks unless explicitly required;
- Playwright MCP may validate UI/E2E/runtime, but it does not replace the repository's own Playwright/browser runtime contracts;
- CLI inspection must be read-only against protected production data unless the active task explicitly requires and safely authorizes a write.

## 8. Zero-auth acquisition capability program

Canonical acceptance matrix:

```text
00-GOVERNANCE/CODEX-ZERO-AUTH-CAPABILITY-ACCEPTANCE-V1.md
```

Remote source already provides these foundations through manifests/source:

```text
requests
httpx
aiohttp
BeautifulSoup4
lxml
Playwright
SQLite
APScheduler
tenacity
```

Dependency declarations and runtime availability are separate claims. For each adapter dependency, verify the current manifest, import and call path, installation in the target runtime, restart state after source changes, and scoped runtime acceptance at the active commit. A manifest entry or import alone does not prove implementation. Dated audit statements are provenance only; do not present them as current runtime status.

Do not lie by upgrading it to remote `IMPLEMENTED` before the repository manifest actually contains it.

### Approved zero-auth adapters

Target adapters:

```text
PublicHttpAdapter
RSSAdapter
AtomAdapter
SitemapAdapter
BrowserAdapter
```

All adapters must converge to existing LUMENIS truth:

```text
External Source
→ Acquisition Adapter
→ Evidence
→ Canonical Data / Canonical Content
→ Function / Research
→ Metric / Truth Table
→ View Model
→ UI / Report / Export
```

Forbidden shortcuts:

```text
RSS → AI directly
Web page → UI directly
Browser result → parallel DB truth
Sitemap → new independent content store
```

### Adapter completion gate

For every adapter, prove as applicable:

```text
source fixture / real public source
→ fetch/parse
→ provenance
→ Evidence
→ canonicalization
→ idempotence / source identity semantics
→ failure isolation
→ API binding
→ UI binding where user-visible
→ targeted tests
→ runtime/E2E
```

No API key/OAuth/cloud dependency may be added to this zero-auth program without a separate architecture and legal/commercial decision.

## 9. Data truth and DB safety

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

Forbidden:

```text
missing → 0
UNKNOWN → healthy
API failure → business success
excluded test → PASS
```

Tests/staging must use explicit isolated/disposable DBs and prove the protected production DB is unchanged when persistence is touched.

`data/monitor.db` selected by `ZBC_DB_PATH` is the sole business/Canonical Production Truth database. A separately owned SYSTEM operational store such as the durable task queue may remain only when its path and schema owner are explicit, it contains no CTH/BMP business truth or Evidence, it opens through `lumenis/shared/database` repository/connection abstractions, and its durability/replay/recovery is covered by tests. Do not add another per-module SQLite file silently; consolidating an existing store requires a data-preserving migration.

Do not delete, rewrite, migrate or repair real production data without required evidence and approval.

## 10. Evidence and lineage

Evidence is provenance-bearing source truth and must not be overwritten by analysis output.

When touching XHS/RedNote or any new acquisition path:

- production XHS/RedNote acquisition may use only the approved Hong Kong / international
  allowlisted identity, Cookie/session and browser profile;
- the locally signed-in Mainland China XHS/RedNote profile is the Product Owner's
  personal work account, not a collection asset: never read, export, import, inject,
  refresh, probe, automate, test, recover, rotate to, or otherwise touch that identity;
- legacy Mainland-cookie helpers, ports, profiles and tests may be inspected as source
  only. They must remain outside every startup, scheduler, collector, browser, recovery,
  E2E and release path unless the Product Owner explicitly changes this rule;
- resolve other platform capability from existing secret-safe configuration and
  registered owners before asking the Product Owner for credentials. Never print or
  commit a secret; report unavailable/blocked honestly when a real integration cannot
  authenticate;
- primary ingestion must not be broken by a non-critical Evidence side-write failure unless the canonical contract explicitly changes;
- preserve source identity, source URL, capture time, provider, domain/product context and trace metadata where available;
- do not collapse distinct source provenance merely because normalized content text matches;
- AI analysis and human correction/final decision must remain distinguishable;
- historical records must not be silently rewritten by new rules.

If local code contains a newer lineage convergence commit than remote `main`, preserve and reconcile it before new work; do not reimplement it from old remote code.

## 11. Permission and external effects

Consequential writes must pass the real permission/approval/effect boundary.

Denied or pending actions must not create forbidden side effects.

Do not fake write success to unblock UI.

For publisher-like behavior:

```text
Permission
→ Approval
→ Effect Fence
→ legitimate integration
→ Audit / Evidence
```

Logged-in social collection remains read-only unless a separately approved Publisher capability exists.

## 12. Collector / Shared Capability closed loop

Canonical owner:

```text
00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md
```

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

- Collector is SYSTEM-owned;
- CTH/BMP/Shared may request collection but do not own parallel runtimes;
- Upload / Import / API / Collector converge into the same Source/Evidence/Canonical/Provenance truth;
- `MetricSnapshot` is append-only;
- future T+ performance stays pending/scheduled until real time/data exists;
- AI may propose PatternCandidate/PromotionProposal but may not autonomously execute `Pattern → ADOPT`;
- Application Trace is required for Research → Creation → Evaluation closure;
- Fact Wall must fail honestly when factual Evidence/Brief support is absent;
- `RELEASED != OPERATING`.

## 13. Experience / user-visible completion

A page, route or test existing is not completion.

For an important user-operable feature prove, as applicable:

```text
UI Entry
→ User Action
→ API / Service
→ Permission
→ Canonical Read/Write
→ Real Result
→ Evidence / Trace
→ Honest Error State
→ Automated Test
→ E2E
```

No fake values, fake 200s, `undefined`, `NaN`, `[object Object]`, or silent missing→0 transformations in production acceptance.

Do not treat prototype-only screens as production-bound screens.

### Experience authority routing

For any user-visible Experience/UI task, the **sole design authority** is:

```text
00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
```

No nested router, archived screen, or prototype document may define a second design authority.

The product owner accepted §§30–36, including all 44 screen-specific UX blueprints, on 2026-09-20. App implementation proceeds through reviewed screen specifications under `contracts/experience/screen-specifications/` and source-backed vertical slices; this approval is not evidence that a screen or workflow is implemented or accepted. Each specification must pass §36's owner, binding, entry/return, field-priority, state, desktop/mobile, permission/effect, accessibility and executable-acceptance gates. The 54-row binding registry is a data/permission/Evidence truth ledger only; it is not a layout system. Any `UNKNOWN` owner, callable, permission or lineage blocks the dependent behavior. Legacy `sectionTypes` must not drive a generic renderer or swapped-title page template. Reusable components may share accessible behavior and design tokens, while each screen keeps its own task, hierarchy, composition and interaction path.

Screen design states are distinct from implementation states:

```text
DESIGN_EXPLORATION → DESIGN_READY → IMPLEMENTED → ACCEPTED
```

Only a Sol-reviewed detailed screen specification may establish `DESIGN_READY`.
PDFs, screenshots, prototypes, Figma frames and fixtures cannot self-promote.

Before claiming Experience work complete, run all three blocking checks:

```text
python scripts/audit_tools/verify_experience_authority_exclusive.py
python scripts/audit_tools/verify_experience_anti_template.py --strict
python scripts/audit_tools/verify_experience_screen_blueprints.py
```

Do not reintroduce deleted historical design/handoff/reference material into the current main tree.

## 14. Testing policy

Default progression:

```text
fast/static
→ targeted unit
→ affected integration
→ neighbour regression
→ representative/domain E2E
→ full regression at convergence/release points
```

Do not burn quota by running thousands of unrelated tests after every leaf edit.

Widen testing when shared primitives, persistence, permission, Evidence, Canonical contracts or runtime infrastructure change.

Never delete, skip or weaken a legitimate test merely to obtain PASS.

Test-tier truth is defined in:

```text
tests/CI_TEST_TIERS.md
```

Interpretation:

```text
Tier A/B green = clean repository/hermetic contract evidence
Tier C green   = environment/live acceptance evidence
Tier A/B green alone != PRODUCTION_READY
```

## 15. CI truthfulness

CI checks must remain semantically classified as `BLOCKING`, `ADVISORY` or `INFORMATIONAL`.

Syntax errors, missing required test execution, critical DB/data-integrity failures, permission failures, required E2E failures and P0 security failures must not be hidden by `continue-on-error` or swallowed exceptions.

A green workflow is insufficient if blocking work did not actually execute.

## 16. Startup / runtime

Canonical Windows command:

```powershell
Set-Location D:\\LUMENIS_REBUILD\\序\\序境
powershell -ExecutionPolicy Bypass -File scripts\\start_production.ps1
```

Expected core health endpoint:

```text
http://127.0.0.1:8201/healthz
```

Startup acceptance:

```text
dependencies
→ configuration
→ launcher
→ application boot
→ supervisor stability
→ port bind
→ health
→ required runtime initialization
→ critical API / Experience
```

External browser/login/source health must be reported separately from core application health.

## 17. Third-party / OSS

Canonical register:

```text
00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md
```

Before adding a third party:

1. inspect current manifests/import/runtime usage;
2. prove a real capability gap;
3. verify license from authoritative project/package sources;
4. record attribution/notice obligations;
5. keep the dependency behind a bounded adapter where practical;
6. record replacement direction.

Preferred shape:

```text
LUMENIS Contract → Adapter → Third-party implementation
```

Unknown licensing is a release blocker.

## 18. License boundary

Repository-level source licensing is defined by root `LICENSE`.

Third-party dependencies and vendored components retain their own licenses. Never rewrite or imply ownership of third-party licenses.

If the repository license changes, treat it as a legal/governance change, not a routine code refactor.

## 19. Security boundaries

Never expose or commit:

- credentials/API keys;
- cookies/session material;
- browser/CDP secrets;
- real production DB files;
- system/developer prompts or private reasoning;
- privileged hidden tool details;
- unauthorized external-effect credentials.

Public adapters such as ChatGPT/MCP must use allowlisted/versioned internal contracts, authentication where applicable, Subject Context, domain, permission and provenance/policy boundaries. Do not expose raw DB/Collector session internals.

## 20. Git discipline

- `main` is the only writable development, integration and production-candidate branch;
- preserve unknown/uncommitted local work before synchronizing;
- use coherent-purpose commits;
- do not force-push `main`;
- do not commit production DB, secrets, cookies, sessions, caches or generated junk;
- do not claim an unpushed/local commit exists remotely;
- after remote documentation changes, a local branch that was previously ahead must `fetch` and reconcile the new remote commits before pushing.

## 21. Completion semantics

```text
IMPLEMENTED = code exists
TESTED      = scoped automated tests pass
VERIFIED    = runtime/E2E evidence proves behavior
RELEASED    = required production/security/recovery/rollback gates pass
OPERATING   = real operation produces required live/scheduled evidence
```

Use `LIVE_VERIFIED` only for actual live/runtime verification. CI, static source review and dependency installation do not qualify.

## 22. Legitimate stop conditions

Stop for user input only when required by a real blocker such as:

- required credential/source inaccessible;
- destructive production-data action needs explicit approval;
- unresolved migration conflict creates material data risk;
- legal/security decision cannot safely be inferred;
- high-risk external effect requires human approval;
- production hosting/domain/paid resource requires authorization.

Large code volume, many files, long tests or context size are not themselves blockers.

## 23. Current multi-surface product state

The approved experience surfaces are Public Website, Web Workspace, Desktop App and Mobile Companion. Do not freeze their implementation status in this router: inspect the current `origin/main`, protected local `app/` and `website/` work, active routes, builds and real runtime evidence separately. Local-only source must not be reported as absent, while a page file or build must not be reported as an accepted product surface. Binding contracts live under `contracts/experience/`; `experience_runtime.py` provides the API/ViewModel boundary and `lumenis_app_api.py` provides JSON APIs.

A launch shell, route, contract, generated Web target or provider registration does not establish an end-to-end product workflow. Operational surfaces must bind real Product Core/API, Canonical Data, Evidence, Permission and Evaluation behavior before they can be described as complete.
