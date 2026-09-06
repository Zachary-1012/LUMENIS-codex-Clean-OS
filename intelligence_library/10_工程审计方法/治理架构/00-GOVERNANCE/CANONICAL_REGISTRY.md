# 序境 Canonical Registry

> Status: Active · Governed by Zero Sequence

## Purpose

This registry is the single structural reference for mapping production assets without changing runtime behavior.

## Twin boundary

| System | Canonical role | Owns | May request |
|---|---|---|---|
| 序境-Core | Production Truth | production code/data/runtime/policy/reporting | research, models, recommendations |
| 序境-Intelligence | Research & Intelligence | research/evidence/models/evaluation/contracts | Core implementation through Contract |

Neither system becomes the other's unrestricted writer.

## Canonical hierarchy

`Product → Subsystem → Module → Page → Function → Data → API → Runtime → File → Symbol`

Cross-cutting governance: `Policy / Permission / Safety / Evidence / Audit`.

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

`Question → Research → Evidence → Recommendation → Contract → Core Implementation`

External research is reference material only. Adopt/adapt/reject decisions must be evidence-backed and must not copy protected code or unauthorized assets.

## Naming

Public product: `序境 / Xujing / 서경`.

Production core: `序境-Core / Xujing Core`.

Brand philosophy: `芥子纳须弥`.

`Zachary` is legacy repository/identity terminology, not the public product name.

## Non-negotiables

1. No third core repository.
2. No AI/Agent direct write to production truth.
3. No module outside the registry.
4. No production rule bypass for UI, research, automation, or language.
5. No deletion without evidence of non-use and regression safety.
