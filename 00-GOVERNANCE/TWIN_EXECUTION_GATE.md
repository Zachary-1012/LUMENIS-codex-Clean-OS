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

## UI gate

Web, App and Mini Program are presentation surfaces over the same canonical capability model. Do not create separate business logic trees for each surface.

Use the shared Design Language: restrained typography, small line icons, clear hierarchy, responsive layout, accessible states and data-first visualization. No oversized logo/icon or poster-like module dominates a page.

## Change rule

Zero Sequence is the governing change-control rule. Changes to product identity, twin-repository boundary, production-truth ownership, security rules or canonical naming require explicit authorization before execution.

## Evidence

Every production change must leave a traceable record of scope, owner, reason, test result and commit.

Status: ACTIVE
