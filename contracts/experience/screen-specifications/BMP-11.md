# BMP-11 — 品牌基准

```yaml
screen_id: BMP-11
status: OWNER_REVIEW
revision: 1
owner_domain: BMP
binding_ids: [BACKEND-GAP-028]
product_owner_approval: APPROVED_OVERALL_EXPERIENCE_CONSTITUTION_30_36
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: SOURCE_BACKED_SCOPE_BLOCKED_IMPLEMENTATION
reviewer: Bounded ROUND-13 implementation worker
reviewed_at: 2026-09-22
approval_reference: ROUND-13-BMP-CREATION-UI
```

## 1. User problem and product invariant

- A brand operator needs normalized comparisons with metric definitions visible beside values, while incomparable items remain explicitly withheld.
- The current benchmark uses configured/global terms rather than a selected BrandFocus and has no verified source-to-ranking chain. No rank or gap is invented locally.
- `GLOBAL_ALL` is allowed only when the returned binding explicitly grants the complete global range. Focus mode must match the selected brand ID exactly.
- The default page can therefore operate on an authorized global collection without requiring a prior brand selection; switching to `FOCUS` narrows the same workflow and never turns focused data into a global aggregate.

## 2. Route and bindings

- Read callable: `LumenisCoreClient.screen('BMP-11')` / `/api/experience/screen/BMP-11`.
- Display gate: `binding.scope_read_evidence_version` and `binding.evidence_lineage_version` must both be `v2`, `binding.read_access` must be `ALLOWED`, and `binding.scope_mode` must match the returned context. `FOCUS` requires the exact selected `brand_id`; `GLOBAL_ALL` requires a null `brand_id` plus `global_read=ALL_GRANTED`. Legacy self-reported scope/permission booleans are not accepted.
- Expected fields: `rows[].dimension`, `definition`, `self`, `competitors[]`, `comparable`, `brand_id`, `scope_mode`, `evidence_ref`; competitor rows require the same metric definition and their own recorded source.
- This screen has no write action. It cannot promote a competitor, alter canonical data or calculate a business ranking from incomplete rows.

## 3. State and recovery

- Loading, not collected, unavailable, access denied and offline remain distinct.
- A missing definition, source or comparability flag withholds the affected value.
- Comparable rows show values only when self and competitor definitions align.
- No comparable result shows a plain pending state, never zero or a synthetic rank.

## 4. Purpose-built composition

- Desktop is a horizontally scrollable normalized comparison grid with columns for dimension, current brand and competitors, followed by a metric-definition rail and source requirement strip.
- Mobile becomes a metric-by-metric comparison list: definition first, then current brand and competitors, with an explicit withheld state for incomparable rows.
- This is a definition-led comparison workflow, not a generic KPI dashboard or card grid.

## 5. Actions, authorization and effects

- No write/effect action is presented. Refresh repeats the read only.
- Any future ranking or benchmark export requires a new canonical callable and owner decision; it is not inferred by this page.

## 6. Accessibility and localization

- The desktop grid has a linear row/column reading order and mobile provides the equivalent metric list.
- Withheld values are announced with the reason; visual color is not the only comparability signal.
- Integration key inventory: `screen.BMP-11`, `bmp11.subtitle`, `bmp11.dimension.*`, `bmp11.definition.*`, `bmp11.comparison.*`, `bmp11.withheld.*`, `bmp11.recovery.*` for `zh-CN`, `en`, and `ko`.

## 7. Executable acceptance

- A global/configured term without exact BrandFocus or explicit `GLOBAL_ALL` grant is rejected.
- A competitor with a different metric definition or missing source is withheld.
- Missing values are never converted to zero and no rank is generated.
- Hostile rows from another brand are filtered before display.
- Desktop and mobile preserve the same definition/comparability semantics.

Current decision: `IMPLEMENTED / BLOCKED_FOR_BENCHMARK_SCOPE`; canonical benchmark owner must bind source-backed BrandFocus/global-all results before real-user E2E acceptance.
