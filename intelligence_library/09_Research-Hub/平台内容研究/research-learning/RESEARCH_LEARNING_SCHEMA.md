# SICI Research Learning Schema

> Incremental implementation under the existing three-repository baseline. This is a learning data contract, not a replacement for the DCC-owned three-repository matrix.

## Purpose

Provide a durable, auditable record for research, experiments, Shadow Learning, verification, and promotion candidates.

## Record types

- `research_case` — external/internal research finding.
- `experiment` — a concrete hypothesis and implementation trial.
- `shadow_run` — non-authoritative evaluation against an existing behavior or baseline.
- `evidence` — observable execution/test result.
- `review` — human/AI assessment of evidence.
- `promotion_candidate` — a proposal to turn a verified pattern into a reusable skill/rule/automation.

## Required provenance

Every record must include:

- stable `id`
- `record_type`
- `created_at`
- `source`
- `repository`
- `commit_sha` when code is involved
- `status`
- `owner`
- `summary`

Evidence-backed records should also include `test_ref`, `evidence_ref`, or an explicit `verification_status` explaining why runtime evidence is unavailable.

## Promotion states

`observed → researched → shadowed → verified → reviewed → reusable`

A model assertion alone cannot move a record to `verified` or `reusable`.

## Privacy/security

Do not store GitHub tokens, passwords, cookies, private user content, or other credentials in the learning database. Store references/metadata instead.

## Three-repository rule

Cross-repository learning is portable knowledge, not ownership transfer. A finding from one repository must be adapted and re-verified in the destination repository before promotion there.
