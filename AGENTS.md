# AGENTS.md — 序境 / LUMENIS Production Execution Router

> Purpose: model-neutral routing, evidence, safety and completion rules for coding agents.  
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

Never use old chat, old commit messages, stale README text, static prototypes or handoff claims to override executable truth.

Documentation merged into `main` proves only that the rule/document exists. It does not prove the production capability is implemented, tested, live-verified or released.

### Mandatory Codex bootstrap

This root `AGENTS.md` is the first coding-agent instruction boundary. Before changing product code, Codex must resolve the current remote truth and then read the CURRENT governance path:

```text
AGENTS.md
→ 00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md
→ 00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md
→ 00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md
→ 00-GOVERNANCE/PRODUCT-POSITIONING-CURRENT.md
→ README.md
→ 00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md
→ 00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json
→ 00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md
→ exact current source / runtime / DB / API / Permission / Evidence / tests for the active slice
```

Hard rules:

- current HEAD comes from `git fetch origin` + `git rev-parse origin/main`, never from a document, screenshot, chat or pasted SHA;
- the active cross-product contract is `lumenis-ggi-cross-product` **v1.1.0** with fingerprint `68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f`;
- the Markdown registry is a human-readable mirror; the JSON contract plus blocking validators are the machine gate;
- if CURRENT governance artifacts disagree, fail closed and reconcile them before cross-product work;
- dated handoffs, archived audits and legacy repositories are provenance only unless current executable evidence revalidates them;
- do not write to another repository merely because it is listed in the cross-repo registry; that repository must be explicitly in the active task scope.

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

### Three-delivery product red line

All current product execution follows exactly this order:

```text
1. App Experience — UI / layout / responsive PC-mobile composition / UX motion
2. Backend and capability recovery — current owners / Ollama / media Cookie chain / workflow binding
3. Closed-loop internal beta — real data / E2E / recovery / release evidence
```

Preserve product position, functions, rules, data sources and workflow meanings. Apple, ChatGPT and TRAE are Experience-principle references only and never authorize new product features. OpenCode/Codex are engineering runtimes; Ollama is a SYSTEM AI runtime provider. Media-platform Cookie/session authorization remains separate from the future LUMENIS product account. The LUMENIS account is deferred until after internal beta; pre-beta App access must not be blocked by an account wall, while server Permission and effect fences remain enforced.

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

### App-only Experience direction

The final user-facing LUMENIS product is one cross-platform Flutter application for Windows, macOS, Linux, Android and iOS.

The Flutter application under `app/` is the sole user-facing LUMENIS Experience. Flask routes serve Product Core/API/ViewModel contracts and must not become a parallel web frontend. Before removing any remaining user-visible capability, trace its business purpose, ViewModel, permission, state, Evidence and acceptance evidence into the canonical App/API path.

All UI/UX/visual/presentation decisions remain subordinate to the sole authority:

`00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md`

Historical UI/UX documents, screenshots, copied Apple/GPT reference packs and old design systems are forbidden development inputs. The only permitted external-reference input is the bounded abstract principle mapping recorded in the current Experience Constitution; it cannot add features, copy layouts or become a second design authority.

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

## 23. Current App-only product surface

The canonical user-facing application is `app/` (Flutter); binding experience contracts live under `contracts/experience/`. `experience_runtime.py` provides the API/ViewModel boundary and `lumenis_app_api.py` provides JSON APIs.

A launch shell, route, or contract does not establish that an end-to-end product workflow is complete. App screens must bind real Product Core/API, Canonical Data, Evidence, Permission, and Evaluation behavior before they can be described as complete.
