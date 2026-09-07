# 序境 / LUMENIS — Canonical Registry

> Status: Active · Production Truth Owner

## Purpose

This registry is the single structural reference for mapping production assets without changing runtime behavior.

## Product identity

| Layer | Standard name | Role |
|---|---|---|
| Product | **序境 / LUMENIS** | Production Core · Production Truth Owner |
| Domain | **CTH — Commerce & Trading Hub** | 主体驱动的商业与交易情报域 |
| Domain | **ZBMP — Brand Monitoring Platform** | 多主体品牌监测与品牌情报域 |

Korean product name: **서경 LUMENIS**. Existing repository/internal identifiers such as `ZBC`, `ZBMP`, and `CTH` may remain in code, API paths, database fields and migration history where compatibility requires them; user-facing naming follows this registry.

## Domain semantics

### CTH — Commerce & Trading Hub

**中文标准名：商业与交易枢纽**  
**한국어：커머스 & 트레이딩 허브**

CTH is **subject-selectable, not Taikoo Hui-fixed**. Guangzhou Taikoo Hui is one selectable business subject, not the permanent product boundary.

The selected subject establishes the current business context. CTH capabilities follow the selected `subject_id / scope`, including monitoring, subject rules, subordinate business units/sections, categories, events, risks, analysis, decision information and reports.

Changing the selected subject changes the working context and focus; it must never overwrite, migrate, reinterpret or contaminate historical canonical facts.

### ZBMP — Brand Monitoring Platform

**中文标准名：品牌监测平台**  
**한국어：브랜드 모니터링 플랫폼**

ZBMP retains its original multi-brand monitoring capability. Brands and other eligible subjects can remain in routine monitoring; selecting a subject establishes the **primary monitoring focus**, not an exclusive platform boundary.

The platform must continue to support other monitored brands/subjects, competitors, content, communication subjects, events, risk, consumer needs, benchmarking, multi-platform monitoring and related intelligence workflows.

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

CTH and ZBMP may share infrastructure and contracts, but their domain semantics remain explicit. `product_id`, `subject_id`, `scope`, source identity and evidence lineage must remain traceable through collection, analysis, risk, reporting and UI.

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

1. Public product: **序境 / LUMENIS**.
2. Korean public product: **서경 LUMENIS**.
3. Production role: **Production Core · Production Truth Owner**.
4. CTH: **Commerce & Trading Hub / 商业与交易枢纽 / 커머스 & 트레이딩 허브**.
5. ZBMP: **Brand Monitoring Platform / 品牌监测平台 / 브랜드 모니터링 플랫폼**.
6. The leading `Z-` is removed from the **public ZBMP product name**; `ZBMP` remains a stable internal identifier for compatibility and APIs.
7. Taikoo Hui is a selectable CTH subject, not the CTH product name or permanent scope.
8. No user-facing use of `Xujing`, `Xujing Core`, `서경` as a standalone substitute for LUMENIS, or `Z-Brand` as the public ZBMP name.

## Non-negotiables

1. No third core repository.
2. No AI/Agent direct write to production truth.
3. No module outside the registry.
4. No production rule bypass for UI, research, automation, or language.
5. No deletion without evidence of non-use and regression safety.
6. Subject selection must never rewrite canonical historical facts.
7. CTH must remain subject-selectable; ZBMP must remain multi-subject with primary-focus selection.
