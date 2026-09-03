# 序境双子库 · Twin Execution Gate

## Purpose

This document defines the minimum gate for cross-repository work between Xujing-Core and Xujing-Intelligence.

## Boundary

- Core owns production truth, production data, collectors, runtime, reports, release and operational safety.
- Intelligence owns research, AI/Agent research, knowledge, evaluation, evidence and implementation specifications.
- Neither repository becomes the other's uncontrolled writer.
- No third core repository is created.

## Required mapping

Every new or changed capability must map to:

`Product → Subsystem → Module → Page → Function → API/Command → Data → Runtime → Policy → Evidence → Audit`

A capability without an owner, permission, runtime, policy or evidence path is not release-ready.

## Cross-repository flow

`Research → Evidence → Contract → Implementation Specification → Core Implementation → Test → Evidence → Audit → Release`

## Collector safety gate

Automatic collection is limited to the approved schedule: 00:00 and 12:00 daily, two runs per day, with an explicit enable/disable control. Other collection remains manual, with a 30-minute session limit. Legitimate account/API adapters are allowed only through an explicit policy boundary.

Any risk signal requires `STOP → COOLDOWN → HUMAN REVIEW`.

No new module may silently start a collector, create a new collection schedule, bypass an adapter/policy, or alter account/session safety controls.

### Authorized exception — TopicCampaign independent quota (2026-09-03, owner sign-off)

By explicit owner authorization (2026-09-03), the TopicCampaign module (topic_campaign.py) maintains an independent collection schedule as an approved exception to the daily 2-run limit above: fixed hours [9, 11, 13, 15, 17, 19] (6 runs/day, staggered 5-10 min), daily cap of 8 runs including manual, counted on its own counter and NOT consuming the main public-opinion quota. This exception applies only to TopicCampaign; the main public-opinion collector remains governed by the ShadowPlanner gate (dynamic decision, GAP-05 sign-off 2026-09-02). Any future change to this exception requires re-authorization by the owner.

## UI gate

Web, App and Mini Program are presentation surfaces over the same canonical capability model. Do not create separate business logic trees for each surface.

Use the shared Design Language: restrained typography, small line icons, clear hierarchy, responsive layout, accessible states and data-first visualization. No oversized logo/icon or poster-like module dominates a page.

## Agent orchestration decision（编排模式判据，2026-09-04, from P0 research Round 3）

Current production orchestration = **Supervisor / hub-and-spoke** (ShadowPlanner gate), which matches the 2026 industry consensus for deterministic workflows with 3-8 agents (70% of production use-cases).

Do NOT upgrade to Hierarchical (tree) orchestration unless at least one trigger fires:
1. coordinated agent count exceeds 6 (hierarchical avoids polluting the top-level supervisor state when same-domain workers need shared context);
2. clearly separated heterogeneous domains appear (e.g. public-opinion / marketing / compliance / engineering) each requiring its own specialized tools and reasoning, where per-domain sub-supervisors provide isolation (Microsoft: the key benefit of hierarchy is isolation);
3. workflow steps become genuinely dependent on prior step results across domains.

Until a trigger fires, keep the Supervisor pattern; adding hierarchy prematurely adds orchestration-logic complexity with no measured benefit. Any upgrade requires owner sign-off + Release Gate + regression.

Source: P0-AGENT-ORG Research Map T1 (OSAI), E2/E3 (MetaCTO/QubitTool/Microsoft Learn orchestration guidance 2026).

## Change rule

Zero Sequence is the governing change-control rule. Changes to product identity, twin-repository boundary, production-truth ownership, security rules or canonical naming require explicit authorization before execution.

## Evidence

Every production change must leave a traceable record of scope, owner, reason, test result and commit.

Status: ACTIVE
