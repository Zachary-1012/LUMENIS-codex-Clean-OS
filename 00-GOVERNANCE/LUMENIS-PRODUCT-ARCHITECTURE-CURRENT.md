# LUMENIS Product Architecture — CURRENT

> Status: **CANONICAL / SOLE PRODUCT ARCHITECTURE AUTHORITY**  
> Product: **序境 / LUMENIS**  
> Repository: **Zachary-1012/LUMENIS-codex-Clean-OS**  
> Mainline: **main**  
> Experience authority: `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md`

This document owns product/domain/runtime boundaries. It does not define visual style. The Experience Constitution is the only UI/UX/presentation authority.

## 1. Only One / All-in

LUMENIS is one product, not a collection of historical versions.

```text
ONE Product
ONE Repository
ONE main
ONE Product Architecture
ONE Production Truth
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
ONE Experience
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

## 5. App-only product direction

LUMENIS is an **application product**, not a public web product.

The canonical user Experience target is a single Flutter codebase for:

```text
Windows
macOS
Linux
Android
iOS
```

The existing Flask/Python implementation remains the Product Core / API / runtime during convergence. HTTP/JSON may remain an internal transport boundary; it is not a public Web Experience contract.

The legacy Jinja/static/Experience V2 browser presentation surfaces have been removed from `main`. Retained ViewModel/IA contracts under `contracts/experience/` are binding inputs for the canonical Flutter App only; they do not constitute a second Experience.

Removal rule:

```text
old surface
→ trace capability
→ bind capability to canonical ViewModel/API
→ implement in app
→ regression/E2E
→ delete old surface
```

Never delete a user capability merely to remove a web page.

## 6. AI / Skill / Agent

Target:

```text
Zhipu + Local AI
       │
       ├── deterministic rules / functions
       └── advisory / analysis
```

A Provider is ACTIVE only when real callers, health verification and tests prove it. Historical configuration is not runtime truth.

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
```

This is an ownership target, not permission to mass-move files. Every move requires owner/caller/read-write/runtime/test tracing.

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

UI/UX history, visual reference packs, old screenshots, Apple/GPT references and old design systems are not RESEARCH assets for current main. They are deleted so they cannot become competing design authority.

## 10. Completion gate

Convergence is complete only when:

```text
original baseline capability regressions = 0
later capability regressions = 0
unclassified old-repo capabilities = 0
parallel runtime owners = 0
parallel Experience implementations = 0
legacy UI/UX/reference packs = 0
clean clone = PASS
blocking CI = GREEN
critical E2E = PASS
LUMENIS production repositories = 1
```
