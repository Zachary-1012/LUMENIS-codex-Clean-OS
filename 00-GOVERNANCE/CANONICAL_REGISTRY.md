# 寰意 / OEVIRA — Canonical Registry

> Status: Current naming and compatibility reference; subordinate to Product Architecture.

## Purpose

This registry preserves formal names and compatibility identifiers. AGENTS.md is
the sole execution router; Product Architecture owns the blueprint; Source Owner
Index owns source lookup. This document neither owns Production Truth nor defines
an additional execution schedule.

## Product identity

Current public brand (PO authorized 2026-10-18): **寰意 / OEVIRA**. English positioning: **An Open Space for Thought and Creation.** Product domain: **oevira.com** (brand/domain reference; DNS, HTTPS and deployment are not established by this source change). Korean uses **OEVIRA** with the existing Korean domain descriptions; no new phonetic transliteration is adopted. Former main-product display names 序境 / LUMENIS / 서경 remain historical or compatibility references, not a second product. Other repositories’ brands and the v1.1.0 exchange contract/fingerprint are unchanged; its LUMENIS identifier continues to name the same technical Production Core.

| Layer | Standard name | Role |
|---|---|---|
| Product | **寰意 / OEVIRA** | Production Core · Production Truth Owner |
| Product | **寰意·商业运营 / OEVIRA Commerce Operations** | CTH · Commerce Operations Domain · Subject-first |
| Product | **寰意·品牌市场 / OEVIRA Brand & Market** | BMP · Brand & Market Domain · Brand-first / Primary Focus |
| Shared Capability | **寰意·内容创作 / OEVIRA Content & Creation** | Cross-product shared capability |

Korean product name: **OEVIRA**. CTH Korean: **OEVIRA·커머스 운영**. BMP Korean: **OEVIRA·브랜드 & 마켓**. Existing repository/internal identifiers such as `ZBC`, `ZBMP`, and `CTH` may remain in code, API paths, database fields and migration history where compatibility requires them; user-facing naming follows this registry.

## Ecosystem identity and four-repository contract

The formal ecosystem naming and Truth Ownership are locked as follows:

| Product | Canonical Repository | Stable technical alias | Canonical role | Truth Owner |
|---|---|---|---|---|
| **寰意 / OEVIRA** | `Zachary-1012/LUMENIS-codex-Clean-OS` | LUMENIS / historical `ZBC` where compatibility requires | Production Core | **Production Truth** |
| **序蕴 / LUMENIS Intelligence** | `Zachary-1012/Zachary-OS-AI` | OSAI / `Zachary-OS-AI` | Shared Intelligence Capability | **Shared Intelligence Assets** |
| **序衍 / LUMENIS Growth** | `Zachary-1012/global-growth-intelligence` | GGI / `global-growth-intelligence` | Independent Research & Growth Product | **Research / Growth Truth** |
| **序枢 / LUMENIS Command** | `Zachary-1012/lumenis-command` | COMMAND / `lumenis-command` | R&D Control Sidecar | **Engineering Evidence** |

Machine contract: `lumenis-ggi-cross-product` v`1.1.0`, status `ACTIVE`, effective `2026-09-17`, fingerprint `68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f`.

Stable technical aliases, repository names, package names, environment variables, API namespaces, DB keys and historical links are not destructively renamed solely for branding. Formal names above govern README, governance, product-facing naming and new human-readable documentation.

## Domain semantics

### CTH — Commerce Operations

**中文正式产品名：寰意·商业运营**\
**English：OEVIRA Commerce Operations**\
**한국어：OEVIRA·커머스 운영**\
**领域：Commerce Operations Domain / 商业运营领域 / 커머스 운영 영역**

CTH is **subject-first and subject-selectable, not Taikoo Hui-fixed**. A selected legal business Subject establishes the working context for the existing CTH capabilities across its subordinate business units/sections, brands, categories, content, events, propagation, user feedback, sentiment, risks, analysis, decision information and reports.

CTH does not imply trading or transaction capability. Do not use `Commerce & Trading Hub`, `Trading`, `商业交易`, `商业情报`, `Taikoo Hui Intelligence`, or `太古汇智能` as current product terminology.

Guangzhou Taikoo Hui is one selectable `Subject Profile`, not the CTH product name or permanent product boundary.

### BMP — Brand & Market

**中文正式产品名：寰意·品牌市场**\
**English：OEVIRA Brand & Market**\
**한국어：OEVIRA·브랜드 & 마켓**\
**领域：Brand & Market Domain / 品牌市场领域 / 브랜드 & 마켓 영역**

BMP remains **brand-first / primary-focus**, while retaining its existing multi-brand and cross-subject monitoring behavior. Selecting a brand sets the current primary monitoring focus; it does not make other brands, competitors, market signals, content, communication subjects, events, risks, consumer needs, benchmarking or multi-platform monitoring inaccessible.

Do not use `Z-Brand Monitoring Platform`, `Brand Intelligence`, or `品牌智能` as current user-facing product names. `BMP` remains a stable internal identifier for compatibility.

### Shared Capability — Content & Creation

**中文：寰意·内容创作**\
**English：OEVIRA Content & Creation**\
**한국어：OEVIRA·콘텐츠 & 크리에이션**

Content & Creation is a shared capability, not a CTH-only or BMP-only product/module. CTH, BMP, Agent Groups and future OEVIRA products may consume it through explicit capability contracts. Naming changes must not alter existing content creation behavior, permissions, APIs or runtime flows.

### Agent Groups

Agent Groups are **Cross-Product Execution & Collaboration / 跨产品执行与协作层**, not a third product. They may call CTH, BMP, shared capabilities, AI and other authorized capabilities through the existing permission and contract boundaries.

## Product hierarchy

```text
OEVIRA / 寰意
│
├── Commerce Operations Domain
│   └── 寰意·商业运营 / OEVIRA Commerce Operations / CTH
│       └── Subject-first
│
├── Brand & Market Domain
│   └── 寰意·品牌市场 / OEVIRA Brand & Market / BMP
│       └── Brand-first / Primary Focus
│
├── Shared Capability Layer
│   └── 寰意·内容创作 / OEVIRA Content & Creation
│
└── Cross-Product Execution & Collaboration
    └── Agent Groups
```

## Four-product boundary

| Product | Canonical role | Owns | May exchange |
|---|---|---|---|
| 寰意 / OEVIRA | Production Core | Production Truth, production code/data/runtime/policy/reporting | versioned Contract / Artifact / Evidence Reference |
| 序蕴 / LUMENIS Intelligence | Shared Intelligence Capability | Shared Intelligence Assets, validated reusable intelligence capabilities | versioned Contract / Artifact / validated learning candidate |
| 序衍 / LUMENIS Growth | Independent Research & Growth Product | Research / Growth Truth | versioned Contract / Artifact / Evidence Reference |
| 序枢 / LUMENIS Command | R&D Control Sidecar | Engineering Evidence | repository/test/CI/release/runtime verification evidence |

No product receives unrestricted write authority over another product. No shared production database is permitted. No cross-product runtime hard dependency is permitted. AI or Research output may not automatically overwrite OEVIRA Production Truth. Cross-product sharing is restricted to explicit, versioned and traceable Contract / Artifact boundaries.

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

Collection is controlled by the current Global data contract and the existing
SYSTEM Collector/Scheduler. Use task-semantic terms, exact entity/time scope,
platform rotation, bounded pacing and durable refresh. The historical twice-daily
schedule is not a current product-wide limit. Existing per-job safety controls
remain in their owner; this naming register grants no automatic collection or
platform authorization.

Every collection task must pass Preflight → Policy → Identity → Session → Risk → Validate → Normalize → Filter → Evidence.

Risk state: `STOP → COOLDOWN → HUMAN_REVIEW`.

No account rotation, cookie rotation, IP rotation, frequency escalation, or other action may be used to evade platform safety controls.

## UI rules

The sole Experience Constitution owns four-surface composition, navigation,
hand-painted identity, functional glyphs, motion, language and accessibility.
The naming hierarchy above is not a fixed layout or a competing design system.

## Data contract

`Source → Evidence → Canonical Data/Content → Research/Analysis → Insight → Report`

Preserve the original material and source identity before derived analysis.
Capture/normalization steps remain within the existing Collector/Importer owners.

Any displayed metric must have a traceable data origin. Any consequential AI result must retain sufficient model/prompt/input/output/confidence/final-result/human-correction metadata according to sensitivity policy.

## Change gate

`Plan → Contract → Implementation → Test → Evidence → Audit → Release`

Destructive rename/migration/delete requires dependency scan and regression verification. Unverified historical assets are not deleted.

## Research handoff

`Question → Research → Evidence → Recommendation → Contract → LUMENIS Implementation`

External research is reference material only. Adopt/adapt/reject decisions must be evidence-backed and must not copy protected code or unauthorized assets.

## Naming rules

1. Public parent product: **寰意 / OEVIRA**.
2. Korean parent product: **OEVIRA**.
3. Production role: **Production Core · Production Truth Owner**.
4. Ecosystem products: **序蕴 / LUMENIS Intelligence**, **序衍 / LUMENIS Growth**, **序枢 / LUMENIS Command**.
5. Stable aliases `OSAI`, `GGI`, `COMMAND`, `ZBC`, `CTH`, `BMP` remain where compatibility requires them; they are not substitutes for current formal product naming in new human-readable governance/product surfaces.
6. CTH public product: **寰意·商业运营 / OEVIRA Commerce Operations / OEVIRA·커머스 운영**.
7. BMP public product: **寰意·品牌市场 / OEVIRA Brand & Market / OEVIRA·브랜드 & 마켓**.
8. Shared content capability: **寰意·内容创作 / OEVIRA Content & Creation / OEVIRA·콘텐츠 & 크리에이션**.
9. Taikoo Hui is a selectable CTH Subject Profile, not the CTH product name or permanent scope.
10. Do not use `Xujing`, `Xujing Core`, `서경` as a standalone substitute for OEVIRA, `ZBMP`, `Z-Brand Monitoring Platform`, `Brand Intelligence`, `品牌智能`, `Commerce & Trading Hub`, `Trading`, `商业交易`, `商业情报`, `Taikoo Hui Intelligence`, or `太古汇智能` as current user-facing product names.
11. Do not use Center / 中心 / System / 系统 as product naming substitutes.

## Non-negotiables

1. The four canonical products remain independently owned and independently runnable; capability sharing does not merge Truth Ownership.
2. No AI/Agent direct write to production truth.
3. No module outside the registry.
4. No production rule bypass for UI, research, automation, or language.
5. No deletion without evidence of non-use and regression safety.
6. Subject selection must never rewrite canonical historical facts.
7. CTH must remain subject-selectable; BMP must remain multi-subject with primary-focus selection.
8. Product naming and domain metadata changes must not alter existing functional ownership, APIs, DB schema, permissions, collectors, or runtime behavior.
9. Cross-repository product semantics must be synchronized through versioned, traceable contract/artifact references; no shared production database or unrestricted writer.
10. No cross-product runtime hard dependency. AI/Research output cannot automatically overwrite OEVIRA Production Truth.

## 2026-10-18 当前内部采用与外仓身份的区别

上述四仓名称/角色是交换与来源身份。PO已批准将GGI全部有用能力源级吸收进寰意既有Owner；“独立产品”不构成拒绝该内部采用的限制，不能据此另建GGI子模块、账号、数据库或启动依赖。寰意新增界面使用研究、资料、方案、行动、结果与学习等当前业务语义，不使用GGI旧品牌作为新的产品入口。兼容ID、来源commit及历史链接不机械改名。

唯一Architecture §7控制产品范围；[本地采用附件](LUMENIS-SOURCE-ADOPTION-V1.json)记录72文件/51API/33能力及权利；不改交换1.1.0/原指纹。安全flags仍用于跨运行时交换，源级采用须经现有Owner重写、验证、测试和本地release，绝不复制生产库、共享秘密或自动升级Production Truth。外仓本次只读，未同步修改；内部实施IN_PROGRESS，四端NOT_VERIFIED。
