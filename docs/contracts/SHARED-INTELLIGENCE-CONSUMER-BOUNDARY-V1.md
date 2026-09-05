# Shared Intelligence Consumer Boundary V1

> Status: Active contract consumer boundary · 2026-09-05

## Purpose

序境 remains an independently runnable production product. Shared intelligence contribution to Zachary OS AI is optional and must never affect normal production operation.

## Independence guarantee

序境 must continue to collect, normalize, analyze, apply subject/business rules, calculate risk, generate reports and operate when OSAI is unavailable, degraded, upgrading, rejecting contributions, or offline.

OSAI must never become a synchronous dependency of the production critical path.

## Contribution flow

```text
Existing ZBC lifecycle
 → existing evidence / evaluation / human feedback
 → contribution candidate
 → local outbox
 → asynchronous contract export
 → OSAI validation
```

The existing production data pipeline and business rules remain authoritative.

## Hard boundaries

- Do not replace or bypass existing subject/business rules.
- Do not move production truth into OSAI.
- Do not share the production database.
- Do not add a required runtime dependency on OSAI.
- Do not place credentials, cookies, sessions or unrestricted sensitive records in contribution payloads.
- Do not let OSAI write ZBC production truth directly.
- Do not allow contribution retries to block collection, analysis, reporting or other primary operations.

## Failure isolation

```text
Contribution export
 ├── success → lineage/ACK recorded
 ├── timeout → bounded retry
 ├── unavailable → local queue / later retry
 └── rejected → local rejection record

Primary product operation → continues in every branch
```

## Returned intelligence

OSAI may return evaluation, skill, memory or learning candidates. ZBC treats them as advisory artifacts until they pass the existing ZBC contract, permission, regression and release gates.

## Adoption gate

`RECEIVE → VERIFY → EVALUATE → ADAPT → TEST → EVIDENCE → AUDIT → RELEASE`

No returned asset may silently change production rules or production truth.

## P0 implementation constraint

Implement the adapter/outbox boundary beside existing lifecycle points first. Do not rewrite the existing collection, subject filter, event aggregation, risk or reporting pipeline to introduce shared intelligence.

## Acceptance criteria

1. ZBC passes its existing regression tests with OSAI disabled.
2. Contribution export failure cannot fail the primary request/task.
3. Production database remains local to ZBC.
4. Sensitive payload minimization is enforced before export.
5. Contribution lineage is traceable.
6. Returned intelligence cannot bypass ZBC release gates.
