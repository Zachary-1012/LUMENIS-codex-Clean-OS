# LUMENIS Product Architecture — CURRENT

> Status: **CANONICAL / SOLE PRODUCT ARCHITECTURE AUTHORITY**  
> Product: **序境 / LUMENIS**  
> Repository: **Zachary-1012/LUMENIS-codex-Clean-OS**  
> Mainline: **main**  
> Experience authority: `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md`
> Approved surface decision: `00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md`

This document owns product/domain/runtime boundaries. It does not define visual style. The Experience Constitution is the only UI/UX/presentation authority.

The ROUND 01 audit, taskbook, missing register, sketches and generated delivery
artifacts are approved execution evidence, not Product Architecture. They cannot add
an owner, API, surface, workflow or product function, and they cannot authorize UI
implementation without the current Experience and screen-specification gates.

## 1. Only One / All-in

LUMENIS is one product, not a collection of historical versions.

```text
ONE Product
ONE Repository
ONE main
ONE Product Architecture
ONE Production Truth
ONE Product Core
ONE API / ViewModel Contract
ONE Canonical Data Layer
ONE Evidence Layer
ONE Permission Model
ONE Runtime
ONE Collector System
ONE Browser Runtime
ONE AI Gateway
ONE Agent Runtime
ONE Reporting System
ONE Evaluation System
ONE Learning System
ONE coherent Experience across approved surfaces
ONE Design Authority
```

Original baseline capability may not regress. Capabilities added later may not regress. Convergence means merging ownership and execution paths, not deleting capability.

## 2. Product domains

### CTH / 序境·商业运营 / LUMENIS Commerce Operations

**Subject-first.**

The user first selects an authorized commercial Subject, then organizes, observes, analyzes and acts on the Subject's business units, brands, categories, content, activities, communication, user feedback, public opinion, events, cases, risks, decisions, actions and reports.

CTH does not mean trading. Current product semantics must not use Commerce & Trading Hub, Trading, 商业交易, 商业情报 or 太古汇智能.

广州太古汇 is one selectable `Subject Profile`, not the CTH product boundary.

### BMP / 序境·品牌市场 / LUMENIS Brand & Market

**Brand-first / Primary Focus.**

Selecting a brand establishes the primary working focus while LUMENIS may continue monitoring competitors, markets, content, communication, creators, consumer demand, trends, events, risks and benchmarks.

Z-Brand Monitoring Platform and Brand Intelligence are historical names, not current product names. `BMP` remains a stable internal identifier.

### Shared Capability Layer

Shared capabilities include:

```text
Content & Creation
Evidence
Research
Evaluation
Learning Assets
Reporting / Export
AI Enhancement
```

Shared capability does not erase CTH/BMP domain ownership.

### SYSTEM

SYSTEM owns:

```text
Collector
Runtime
Scheduler
Browser / CDP
AI Gateway
Database
Security
Permission
Settings
Recovery
Observability
```

### Agent Groups

Agent Groups are the **Cross-Product Execution & Collaboration Layer**, not a third product and not an independent truth owner.

They may invoke CTH, BMP, Shared and SYSTEM capabilities through permissioned contracts.

## 3. Subject model

```text
Product
└─ Domain (CTH / BMP)
   └─ Selected Subject / Primary Focus
      ├─ Sub-Subject / Business Unit
      ├─ Industry / Category
      ├─ Content
      ├─ Event / Case
      ├─ Risk
      └─ Report / Decision
```

Selecting a Subject changes context, monitoring emphasis and downstream views. It must never rewrite Canonical Data, Evidence, historical events, confirmed outcomes or original ownership.

`SUBJECT_WORDS`, `SUBJECT_EXCLUDE_WORDS` and `subject_hit()` semantics are production-protected. Refactors require regression evidence.

## 4. Canonical chains

Production:

```text
External Data → Evidence → Canonical Data → Function → Metric
→ Truth Table → View Model → Experience / Report / Export
```

Business:

```text
Source → Evidence → Event → Case → Insight → Decision → Action
→ Outcome → Evaluation → Learning Asset
```

No migration may shorten either chain by replacing truth with UI state, AI output or compatibility data.

## 5. Multi-surface product direction

LUMENIS is **one commercial product with multiple approved Experience surfaces**:

```text
Public Website     product explanation, demo, trial/contact/help and workspace entry
Web Workspace      primary commercial workspace in the browser
Desktop App        Power User Client and local/advanced execution surface
Mobile Companion   notification, review, approval, status and light action
```

The existing Flask/Python implementation remains the one Product Core / API / runtime. Every operational surface shares Canonical Data, Evidence, Permission, SubjectContext/BrandFocus, state meanings, business workflows and API/ViewModel contracts. Surface-specific layout or deployment cannot become a second product truth.

The approved implementation route is an SEO-capable Public Website deployed separately from a Flutter Web Workspace. `app/` remains one Flutter codebase for Web, Windows, macOS, Linux, Android and iOS. The full product and capability boundary are recorded in `LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md`; that decision does not create a second architecture or design authority.

Historical browser/Jinja/static presentation surfaces have been removed from `main` and remain forbidden as implementation shortcuts. Retained ViewModel/IA contracts under `contracts/experience/` are binding inputs for all approved operational surfaces; they do not constitute a second Experience.

Removal rule:

```text
old surface
→ trace capability
→ bind capability to canonical ViewModel/API
→ implement in the approved surface without duplicating Product Core
→ regression/E2E
→ delete old surface
```

Never delete a user capability merely to remove a web page.

### Experience implementation boundary

Implement operational surfaces in four layers. These are code boundaries, not new business-truth owners:

```text
presentation  44 purpose-built screen compositions, semantic primitives,
              adaptive navigation, accessible rendering and local view state
application   domain use cases, typed state transitions, routing/deep links,
              authorized CTH SubjectContext and BMP BrandFocus
data           typed Product Core clients, request cancellation, pagination,
              bounded cache, freshness labels, retry/idempotency and decoding
platform/core  runtime connectivity; future post-beta account/session,
               secure credential storage, permission-aware
              affordances, connectivity, filesystem/export and device services
```

Do not implement one catch-all screen renderer driven by `sectionTypes`, a page-family skin with only swapped labels, or a global store that merges SubjectContext and BrandFocus. Reusable elements are limited to behavior contracts (focus, form validation, chart semantics, evidence citation, empty/error states, motion and density); each of the 44 screens owns its question, information hierarchy, composition and primary action. Route state may restore a user's working context but cannot grant authorization. Every server request rechecks the actor and product/domain scope. Public Website content may explain a capability but cannot execute or own its business workflow.

Generated or audit design artifacts remain `DESIGN_EXPLORATION`. A screen becomes
`DESIGN_READY` only through a current reviewed specification under
`contracts/experience/screen-specifications/` that resolves owner, binding,
Permission, Evidence, state, surface composition and executable acceptance. Direct
implementation from a PDF, screenshot, fixture, Figma frame or repeated wireframe is
forbidden.

Cache is a presentation aid only: show its capture time and stale state; never silently promote it to current truth. Retry is bounded and safe for the operation's idempotency contract. Offline mode allows inspection of explicitly cached material and drafting when safe; it cannot imply that a write, approval, publication or collection completed. Provider, platform and API errors remain distinguishable for recovery.

## 6. AI / Skill / Agent

Provider roles:

```text
Generative providers (including Zhipu and Local AI)
       ├── drafting / explanation / transformation
       └── advisory analysis

Jev typed decision provider candidate
       ├── routing / classification / scoring
       └── verification / evaluation with probabilities and confidence

LUMENIS-specific self-developed model candidate
       └── the same bounded typed jobs, evaluated against real LUMENIS work
```

A Provider is ACTIVE only when real callers, health verification and tests prove it. Historical configuration is not runtime truth.

Runtime and engineering roles are separate:

- `lumenis/system/ai_gateway/` is the single SYSTEM AI runtime owner. Ollama is the local provider direction behind that owner; `local_ai_client.py` and existing `/api/local-ai/*` routes are compatibility callers that must converge without changing behavior or creating another gateway.
- Jev is approved only as a typed decision/evaluation provider behind that gateway. It is not a free-text fallback, Permission/Evidence owner, final business decision maker or effect authorizer. Its implementation remains `ABSENT` until ROUND 07 proves typed contracts, pinned version, secret handling, cost/legal/privacy review, shadow evaluation, low-confidence behavior and complete trace metadata.
- The Product Owner also requires a LUMENIS-specific self-developed model candidate to reach a real, reviewable closed loop before prelaunch review. Keep it behind the same Gateway and evaluate it alongside Jev on the same authorized typed jobs, Evidence, Permission, language, confidence, outcome and rollback gates. Jev is a transitional comparison candidate: preserve both now, then retire the external path only after the self-developed candidate passes the matched real-work accuracy, calibration, latency, failure-state and rollback gates and the prelaunch review approves the change. Neither candidate may self-promote or replace Product Truth.
- The self-developed candidate may adopt publicly documented typed-question, rubric and calibration principles. It must use independently authorized data and evaluation labels; training on Jev API outputs or copying proprietary model material requires an explicit license and data-use review.
- Local Codex engineering may use an open-source model through separate workstation configuration. That model is not a product Gateway provider, does not replace Sol's product and release authority, and does not establish product-provider acceptance.
- `.opencode/opencode.json` configures OpenCode for repository development, audit, test and automation. OpenCode/Codex are engineering runtimes, not user-facing model providers, Product Core dependencies or Production Truth owners.
- Public Website, Flutter Web, Desktop and Mobile consume typed Product Core results and provider state. They do not hold provider keys, run OpenCode, choose hidden tool chains or own model routing.

The platform identity boundary is also explicit: media Cookie/session/browser authorization belongs to the SYSTEM collector/browser chain and stays separate from the future LUMENIS product account. Product account and password design is deferred until product closure reaches 100%, followed by a Product Owner redesign; this timing does not weaken server-side Permission, approval or effect-fence enforcement.

Production write chain:

```text
Task → Permission → Action Firewall → Effect Fence / Idempotency
→ Execute → Evidence → Evaluation → Trace
```

AI/Agent cannot bypass Permission or directly overwrite Production Truth.

## 7. Product independence

LUMENIS Production Core must run independently.

- LUMENIS does not depend on GGI production code or production databases.
- OSAI / LUMENIS Intelligence is not a startup, collection, analysis, reporting or core-runtime prerequisite.
- LUMENIS Command / 序枢 is a private R&D sidecar: Observe → Control → Verify.
- Cross-repository exchange is versioned, traceable Contract/Artifact only.
- Sidecar failure or deletion must not break LUMENIS.

## 8. Convergence target

```text
lumenis/
├─ domains/
│  ├─ cth/
│  └─ bmp/
├─ shared/
│  ├─ content/
│  ├─ evidence/
│  ├─ research/
│  ├─ evaluation/
│  ├─ learning/
│  └─ reporting/
├─ system/
│  ├─ collector/
│  ├─ runtime/
│  ├─ browser/
│  ├─ ai_gateway/
│  ├─ database/
│  ├─ security/
│  └─ observability/
└─ core/

app/
└─ Flutter LUMENIS Experience
   ├─ Web Workspace
   ├─ Desktop App
   └─ Mobile Companion

website/                     future approved source root; currently ABSENT
└─ Public Website only       no Product Truth / workflow owner
```

This is an ownership target, not permission to mass-move files. Every move requires owner/caller/read-write/runtime/test tracing.

For each vertical delivery slice, record the surface matrix over one Product Core contract: Web Workspace primary/available; Desktop enhanced/exclusive; Mobile view/notify/approve/light action; Public Website explanation/demo only. Layouts need not match, but business meaning and state semantics must. Start acceptance on actual available browser, desktop and mobile reference hosts; record unavailable device/runtime combinations as `UNVERIFIED`, and do not claim a surface or OS release until its build and runtime flows pass.

### Current runtime caller map

These paths are the current owners for production callers. A route or compatibility façade may preserve an established API name, but it may not own the underlying business, security, data or runtime truth.

| Caller family | Canonical owner | Behavior that migration must preserve |
| --- | --- | --- |
| `account/api.py`, `agent_runtime/`, `agent_capability/router.py`, `agent_smart_tool/base.py`, `ai_api.py`, `ai_task_engine.py` | `lumenis/shared/agents/skills/{registry,package_runtime,execution}.py` | Skill discovery, source preview/validation, permission checks, execution state transitions, effect fencing and execution Evidence. |
| `subject_registry.py`, `experience_screens.py`, `lumenis/shared/evidence/api.py`, agent callers | `lumenis/system/security/{permission,action_firewall,effect_fence}.py` | Domain-aware Operation/Risk decisions, system scope, approval state, fail-closed behavior and audited side-effect boundaries. |
| `app.py`, `agent_runtime/observation.py` | `lumenis/system/ai_gateway/{channel,providers,core}.py` | Provider health, fallback order, retry/error classification, circuit breaking and token accounting. |
| `browser_runtime_api.py` and browser callers | `lumenis/system/browser/runtime/{contract,policy,router}.py` | Existing status/probe route contracts, authorization context and safe browser state transitions. |
| `data_query_api.py`, collector scheduling/operations | `lumenis/system/collector/guard/` | Resource limits, queue/DLQ replay, schedule state, recovery gating and runtime switches. |
| `compliance_gate.py`, `engineering_metrics.py`, `experience_runtime.py`, `topic_campaign.py`, `xhs_cookie_bridge.py` | `lumenis/system/collector/adapters/` | Platform registry, source-specific collection policy, schedule decisions, rate/safety limits and normalized records. |
| `kos_routes.py`, `scripts/collect_now.py` | `lumenis/system/collector/runtime/xhs/` and `runtime/pipeline/` | Live collection, deduplication, existing `subject_hit()` semantics, persistence, comments, quality fields and platform-blocked/verification-required states. |
| `collector_automation.py`, collector Evidence writers, `runtime_preflight.py` | `lumenis/shared/evidence/{chain,store,api,production_contract}.py` | Stable identifiers/hashes, primary database path, source/domain/Subject lineage, replay behavior and explicit write-failure evidence. |
| `experience_screens._build_bmp02` | `web_discovery.get_brand_directory()` with `data/brand_directory.json` | Preserve the curated 194-brand / 13-category retail directory and honest source/update metadata; external benchmarking stays unavailable until sourced. |
| `experience_runtime.py`, `experience_screens.py`, `risk_engine.py`, `content_generation.py` | `lumenis/shared/reporting/` | CTH operational/risk report semantics remain separate from BMP brand/market report semantics; export remains permission-gated. |
| `system_features_api.py`, `experience_screens._build_bmp09`, `architecture_api.py`, evaluation/learning callers | `lumenis/shared/{evaluation,learning}/` | Unknown is not PASS, records retain lineage, learning stays reviewable and never writes Production Truth automatically. |
| Business / Canonical Production Truth | `lumenis/shared/database/` | `data/monitor.db` selected through the single compatibility override `ZBC_DB_PATH` remains the only CTH/BMP/Shared business-truth database; all business schema/version ownership stays in the Shared Database migrations. |
| SYSTEM durable task queue | `lumenis/system/collector/guard/task_queue.py` through `DatabaseRepository` | Existing `data/task_queue.db` holds only operational queue/lease state, never Canonical Data, Evidence or business outcomes. Preserve its durable records and replay semantics; any future move requires an explicit, tested data migration. No new module-local SQLite sidecar is allowed without an architecture entry, recovery/retention owner and acceptance evidence. |

The production import gate parses Python import nodes and rejects exact retired owners. It excludes tests, audit prose and comments from the production dependency decision, while the relevant test suite remains responsible for proving each migrated behavior.

## 9. Convergence disposition

Every current or historical capability receives exactly one status:

```text
KEEP      current owner is already canonical
MERGE     multiple implementations become one owner
RESTORE   valid capability is absent or functionally regressed
MIGRATE   capability survives but moves to canonical ownership/app Experience
DELETE    duplicate/obsolete code after capability parity is proven
RESEARCH  non-runtime knowledge asset only
```

UI/UX history, visual reference packs, old screenshots, copied Apple/GPT references and old design systems are not RESEARCH assets for current main. They are deleted so they cannot become competing design authority. Only the bounded abstract principles named in the current Experience Constitution may inform implementation; they do not authorize copied surfaces or new product functions.

## 10. Completion gate

Convergence is complete only when:

```text
original baseline capability regressions = 0
later capability regressions = 0
unclassified old-repo capabilities = 0
parallel runtime owners = 0
parallel Experience implementations = 0
surface-specific business truth owners = 0
legacy UI/UX/reference packs = 0
clean clone = PASS
blocking CI = GREEN
critical E2E = PASS
LUMENIS production repositories = 1
```
