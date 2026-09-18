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
→ README.md
→ 00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md
→ 00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json
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
D:\\LUMENIS_REBUILD
```

Expected repository:

```text
Zachary-1012/LUMENIS-codex-Clean-OS
```

`main` is the only writable development, integration and production-candidate branch.

Start every engineering session with:

```powershell
Set-Location D:\\LUMENIS_REBUILD
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

## 6. Point-in-time source audit (non-authoritative for current HEAD)

The 2026-09-16 source audit was performed against pre-documentation-update remote `main` SHA:

```text
147e3bd331b22236930ae29112a67c613a148f67
```

See:

```text
08-AUDIT/SOURCE-LEVEL-REPOSITORY-AUDIT-20260916.md
```

This SHA is retained only as audit provenance. **Codex must never use it as a checkout target, current baseline, or reason to reset/downgrade `main`.** Current truth must always be resolved from `origin/main` at session start.

Key facts verified at that audit point:

- production launcher is `scripts/start_production.ps1`;
- core application target is port `8201` with `/healthz`;
- Resident Browser infrastructure uses the existing 9222/9223 dual-identity model;
- `app.py` is the Flask application entry and registers existing runtime/API blueprints;
- Experience V2 is mounted through `experience_runtime.py` at `/experience/` and `/api/experience/*`;
- current source explicitly listed `CTH-01` and `AI-01` as bound Experience screens; prototype existence is not backend-binding proof;
- `evidence_chain.py` owned the audited `zbc_evidence` / `zbc_canonical_data` lineage model;
- `xhs_cookie_bridge.py` contained the audited XHS/RedNote collection safety/runtime logic;
- `content_generation.py` contained the audited research → generation → Evidence → Evaluation → human-feedback flow;
- root Node tooling was Playwright-oriented and was not a React/Next/Vite production application manifest;
- clean CI and Production/Live acceptance are separate tiers.

If current source differs, current source wins over this point-in-time list.

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

The earlier audit baseline did not contain `feedparser` in `requirements.txt`. The current canonical manifest now contains `feedparser>=6.0.11`, and the production adapter imports it through the Atom adapter. Treat the dated audit statement below as historical only; current status must be read from the manifest and runtime evidence:

```text
MANIFEST_PRESENT / LOCAL_VERIFIED / RUNTIME_ADAPTER_RESTART_REQUIRED_AFTER_SOURCE_CHANGES
```

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
Set-Location D:\\LUMENIS_REBUILD
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
