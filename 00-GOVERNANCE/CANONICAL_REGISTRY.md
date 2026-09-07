# 序境 / LUMENIS — Canonical Registry

> Status: Active · Production Truth Owner

## Purpose

This registry is the single structural reference for mapping production assets without changing runtime behavior.

## Product identity

| Layer | Standard name | Role |
|---|---|---|
| Product | **序境 / LUMENIS** | Production Core · Production Truth Owner |
| Product | **序境·商业运营 / LUMENIS Commerce Operations** | CTH · Commerce Operations Domain · Subject-first |
| Product | **序境·品牌市场 / LUMENIS Brand & Market** | BMP · Brand & Market Domain · Brand-first / Primary Focus |
| Shared Capability | **序境·内容创作 / LUMENIS Content & Creation** | Cross-product shared capability |

Korean product name: **서경 LUMENIS**. CTH Korean: **서경·커머스 운영**. BMP Korean: **서경·브랜드 & 마켓**. Existing repository/internal identifiers such as `ZBC`, `ZBMP`, and `CTH` may remain in code, API paths, database fields and migration history where compatibility requires them; user-facing naming follows this registry.

## Domain semantics

### CTH — Commerce Operations

**中文正式产品名：序境·商业运营**  
**English：LUMENIS Commerce Operations**  
**한국어：서경·커머스 운영**  
**领域：Commerce Operations Domain / 商业运营领域 / 커머스 운영 영역**

CTH is **subject-first and subject-selectable, not Taikoo Hui-fixed**. A selected legal business Subject establishes the working context for the existing CTH capabilities across its subordinate business units/sections, brands, categories, content, events, propagation, user feedback, sentiment, risks, analysis, decision information and reports.

CTH does not imply trading or transaction capability. Do not use `Commerce & Trading Hub`, `Trading`, `商业交易`, `商业情报`, `Taikoo Hui Intelligence`, or `太古汇智能` as current product terminology.

Guangzhou Taikoo Hui is one selectable `Subject Profile`, not the CTH product name or permanent product boundary.

### BMP — Brand & Market

**中文正式产品名：序境·品牌市场**  
**English：LUMENIS Brand & Market**  
**한국어：서경·브랜드 & 마켓**  
**领域：Brand & Market Domain / 品牌市场领域 / 브랜드 & 마켓 영역**

BMP remains **brand-first / primary-focus**, while retaining its existing multi-brand and cross-subject monitoring behavior. Selecting a brand sets the current primary monitoring focus; it does not make other brands, competitors, market signals, content, communication subjects, events, risks, consumer needs, benchmarking or multi-platform monitoring inaccessible.

Do not use `Z-Brand Monitoring Platform`, `Brand Intelligence`, or `品牌智能` as current user-facing product names. `BMP` remains a stable internal identifier for compatibility.

### Shared Capability — Content & Creation

**中文：序境·内容创作**  
**English：LUMENIS Content & Creation**  
**한국어：서경·콘텐츠 & 크리에이션**

Content & Creation is a shared capability, not a CTH-only or BMP-only product/module. CTH, BMP, Agent Groups and future LUMENIS products may consume it through explicit capability contracts. Naming changes must not alter existing content creation behavior, permissions, APIs or runtime flows.

### Agent Groups

Agent Groups are **Cross-Product Execution & Collaboration / 跨产品执行与协作层**, not a third product. They may call CTH, BMP, shared capabilities, AI and other authorized capabilities through the existing permission and contract boundaries.

## Product hierarchy

```text
LUMENIS / 序境
│
├── Commerce Operations Domain
│   └── 序境·商业运营 / LUMENIS Commerce Operations / CTH
│       └── Subject-first
│
├── Brand & Market Domain
│   └── 序境·品牌市场 / LUMENIS Brand & Market / BMP
│       └── Brand-first / Primary Focus
│
├── Shared Capability Layer
│   └── 序境·内容创作 / LUMENIS Content & Creation
│
└── Cross-Product Execution & Collaboration
    └── Agent Groups
```

## Twin boundary

| System | Canonical role | Owns | May request |
|---|---|---|---|
| 序境 / LUMENIS | Production Truth | production code/data/runtime/policy/reporting | research, models, recommendations |
| LUMENIS Intelligence / OSAI | Research & Intelligence | research/evidence/models/evaluation/contracts | LUMENIS implementation through Contract |

Neither system becomes the other's unrestricted writer.

## Canonical hierarchy

`Product → Domain → Subject → Sub-Subject / Section → Module → Page → Function → Data → API → Runtime → File → Symbol`

Cross-cutting governance: `Policy / Permission / Safety / Evidence / Audit`.

## Subject rules

`Product → Domain → Selected Subject → Scope` is explicit state. Never use an implicit global subject/brand state to redefine production truth.

CTH and BMP may share infrastructure and contracts, but their domain semantics remain explicit. `product_id`, `subject_id`, `scope`, source identity and evidence lineage must remain traceable through collection, analysis, risk, reporting and UI.

## Core domains

| ID | Domain | Primary responsibility |
|---|---|---|
| OBS | Observation | sources, collection, normalization, monitoring |
| INS | Insight | analysis, trends, brands, competitors, risk |
| ACT | Action | KOS, Campaign, tasks, controlled execution |
| RPT | Reporting | daily/weekly/monthly/special reports and exports |
| SYS | System | accounts, sources, AI, settings, permissions, health |

## Runtime rules

Collection is policy-controlled. Automatic collection has two daily windows (00:00 and 12:00) and may be enabled/disabled; the entry remains hidden from ordinary navigation. Other collection is manual and capped at 30 minutes per run. Authorized accounts and official APIs may enter through an explicit adapter/policy boundary.

Every collection task must pass Preflight → Policy → Identity → Session → Risk → Validate → Normalize → Filter → Evidence.

Risk state: `STOP → COOLDOWN → HUMAN_REVIEW`.

No account rotation, cookie rotation, IP rotation, frequency escalation, or other action may be used to evade platform safety controls.

## UI rules

Navigation follows the hierarchy above. No module may invent an independent navigation tree, token system, icon registry, or interaction grammar.

Design baseline: restrained density, small line icons, information-first layout, drill-down from visualization to data/evidence, no oversized logo/icon/typography, and CJK/English layouts that preserve hierarchy.

## Data contract

`Source → Collection → Raw → Normalize → Analyze → Evidence → Insight → Report`

Any displayed metric must have a traceable data origin. Any consequential AI result must retain sufficient model/prompt/input/output/confidence/final-result/human-correction metadata according to sensitivity policy.

## Change gate

`Plan → Contract → Implementation → Test → Evidence → Audit → Release`

Destructive rename/migration/delete requires dependency scan and regression verification. Unverified historical assets are not deleted.

## Research handoff

`Question → Research → Evidence → Recommendation → Contract → LUMENIS Implementation`

External research is reference material only. Adopt/adapt/reject decisions must be evidence-backed and must not copy protected code or unauthorized assets.

## Naming rules

1. Public parent product: **序境 / LUMENIS**.
2. Korean parent product: **서경 LUMENIS**.
3. Production role: **Production Core · Production Truth Owner**.
4. CTH public product: **序境·商业运营 / LUMENIS Commerce Operations / 서경·커머스 운영**.
5. BMP public product: **序境·品牌市场 / LUMENIS Brand & Market / 서경·브랜드 & 마켓**.
6. Shared content capability: **序境·内容创作 / LUMENIS Content & Creation / 서경·콘텐츠 & 크리에이션**.
7. `CTH`, `BMP`, and `ZBC` remain stable internal identifiers where compatibility requires them.
8. Taikoo Hui is a selectable CTH Subject Profile, not the CTH product name or permanent scope.
9. Do not use `Xujing`, `Xujing Core`, `서경` as a standalone substitute for LUMENIS, `ZBMP`, `Z-Brand Monitoring Platform`, `Brand Intelligence`, `品牌智能`, `Commerce & Trading Hub`, `Trading`, `商业交易`, `商业情报`, `Taikoo Hui Intelligence`, or `太古汇智能` as current user-facing product names.
10. Do not use Center / 中心 / System / 系统 as product naming substitutes.

## Non-negotiables

1. No third core repository.
2. No AI/Agent direct write to production truth.
3. No module outside the registry.
4. No production rule bypass for UI, research, automation, or language.
5. No deletion without evidence of non-use and regression safety.
6. Subject selection must never rewrite canonical historical facts.
7. CTH must remain subject-selectable; BMP must remain multi-subject with primary-focus selection.
8. Product naming and domain metadata changes must not alter existing functional ownership, APIs, DB schema, permissions, collectors, or runtime behavior.
9. Cross-repository product semantics must be synchronized through versioned, traceable contract/artifact references; no shared production database or unrestricted writer.
