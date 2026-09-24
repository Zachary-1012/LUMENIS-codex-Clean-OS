# BMP-09 — 品牌评估

```yaml
screen_id: BMP-09
status: OWNER_REVIEW
revision: 1
owner_domain: BMP
binding_ids: [BACKEND-GAP-026]
product_owner_approval: APPROVED_OVERALL_EXPERIENCE_CONSTITUTION_30_36
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: SOURCE_BACKED_SCOPE_BLOCKED_IMPLEMENTATION
reviewer: Bounded ROUND-13 implementation worker
reviewed_at: 2026-09-22
approval_reference: ROUND-13-BMP-CREATION-UI
```

## 1. User problem and product invariant

- A brand operator needs to understand movement by evaluation dimension, confidence and source coverage using actual observed results.
- Evaluation is derivative: it cannot rewrite the recorded result, replace its source or become a new truth store. Subjective generated text is not an evaluation result.
- `BACKEND-GAP-026` currently returns unfiltered evaluation records and drops source references; the page remains blocked until exact BrandFocus or global range and result lineage are available.
- Scope modes are explicit: authorized `GLOBAL_ALL` evaluation aggregates may be shown with global result lineage; `FOCUS` dimensions must match the selected BrandFocus. Focus data is never relabeled as global.

## 2. Route and bindings

- Read callable: `LumenisCoreClient.screen('BMP-09')` / `/api/experience/screen/BMP-09`.
- Display gate: `binding.scope_read_evidence_version` and `binding.evidence_lineage_version` must both be `v2`, `binding.read_access` must be `ALLOWED`, and `binding.scope_mode` must match the returned context. `FOCUS` requires the exact selected `brand_id`; `GLOBAL_ALL` requires a null `brand_id` plus `global_read=ALL_GRANTED`. Legacy self-reported scope/permission booleans are not accepted.
- Expected fields: `dimensions[].name`, `score`, `movement`, `confidence`, `evidence_coverage`, `source`, `brand_id`, `evidence_ref`, and `reports[]`.
- A report control uses `report:write` only to save a local report-request draft; it remains non-executing until the canonical owner returns a result.
- Only `actual_result` or `verified_result` sources are accepted by the view-model.

## 3. State and recovery

- Loading, not collected, offline and access-denied states are distinct.
- Unscoped or lineage-incomplete dimensions are hidden rather than shown with zero or a generated score.
- Ready shows score, movement, confidence and coverage together; reports remain separate from dimensions.
- Report request blocked/local-draft states never claim a report was generated or written.

## 4. Purpose-built composition

- Desktop uses a score matrix beside a report shelf, preceded by a BrandFocus line and an actual-result qualifier.
- Mobile uses a vertical dimension list followed by report history; each dimension keeps movement, confidence and coverage next to its score.
- This is a scorecard/evidence-coverage workflow, not a generic trend dashboard or repeated metric-card renderer.

## 5. Actions, authorization and effects

- `report:write` saves a local evaluation-report draft only when exact read/action permission is present. Until the canonical server executor, Permission/effect fence and Evidence-bearing result exist, no report is generated or written.
- No score recalculation, source correction or learning promotion is performed by the screen.

## 6. Accessibility and localization

- Each score row announces dimension, score, movement, confidence and source coverage in one linear label.
- Mobile list is the non-visual equivalent of the desktop matrix; no chart-only meaning.
- Integration key inventory: `screen.BMP-09`, `bmp09.subtitle`, `bmp09.scorecard.*`, `bmp09.report.*`, `bmp09.movement.*`, `bmp09.confidence.*`, `bmp09.coverage.*`, `bmp09.recovery.*` for `zh-CN`, `en`, and `ko`.

## 7. Executable acceptance

- A subjective or AI-only score is rejected by the source allowlist.
- A record without selected BrandFocus or source lineage is not displayed.
- A missing score remains unavailable rather than zero.
- Report request is blocked or explicitly local-only without a write result; no generated/written success is shown.
- Wide and narrow layouts preserve actual-result-only semantics.

Current decision: `IMPLEMENTED / BLOCKED_FOR_EVALUATION_SCOPE`; canonical evaluation owner must restore source references and brand filtering before real-user E2E acceptance.
