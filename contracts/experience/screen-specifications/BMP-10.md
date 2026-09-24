# BMP-10 — 品牌风险响应

```yaml
screen_id: BMP-10
status: OWNER_REVIEW
revision: 1
owner_domain: BMP
binding_ids: [BACKEND-GAP-027]
product_owner_approval: APPROVED_OVERALL_EXPERIENCE_CONSTITUTION_30_36
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: SOURCE_BACKED_SCOPE_BLOCKED_IMPLEMENTATION
reviewer: Bounded ROUND-13 implementation worker
reviewed_at: 2026-09-22
approval_reference: ROUND-13-BMP-CREATION-UI
```

## 1. User problem and product invariant

- A brand operator needs to see which brand-risk incidents need attention, how severity/spread/recency affect triage, and what response step is next.
- BMP BrandFocus risk is not interchangeable with CTH Subject events. The current builder reuses CTH rows, so those rows must not be relabeled as BMP risk.
- `BACKEND-GAP-027` blocks display until a canonical BrandFocus or global risk source and lineage are returned.
- Scope modes are explicit: globally scoped `GLOBAL_ALL` incidents are allowed only with the complete global grant and source lineage; `FOCUS` incidents must match the selected BrandFocus, and CTH Subject rows remain invalid in either mode.

## 2. Route and bindings

- Read callable: `LumenisCoreClient.screen('BMP-10')` / `/api/experience/screen/BMP-10`.
- Display gate: `binding.scope_read_evidence_version` and `binding.evidence_lineage_version` must both be `v2`, `binding.read_access` must be `ALLOWED`, and `binding.scope_mode` must match the returned context. `FOCUS` requires the exact selected `brand_id`; `GLOBAL_ALL` requires a null `brand_id` plus `global_read=ALL_GRANTED`. Legacy self-reported scope/permission booleans are not accepted.
- Expected fields: `risks[].title`, `severity`, `spread`, `recency`, `status`, `brand_id`, `evidence_ref`, and `events[]` with response timeline fields.
- `creator:hold` saves a local high-risk hold-request draft. `response:draft` saves a local response proposal and does not send or publish it.
- CTH Subject event rows are invalid for this screen even when their shape looks similar.

## 3. State and recovery

- Loading retains the risk-response identity.
- Not collected says no BrandFocus risk record is ready; it does not say risk is zero.
- Unscoped/CTH-sourced rows are withheld with a plain brand-range explanation.
- Offline/error supports retry with no stale risk action state.
- Hold/draft actions remain blocked or explicitly local until the matching executor, approval and Evidence-bearing result exists.

## 4. Purpose-built composition

- Desktop uses an incident field: severity queue on the left, spread/recency detail in the center, and a response timeline on the right.
- Mobile uses a triage queue first, then the selected incident timeline and response controls. It is not a generic dashboard or alert-card grid.
- The primary question is “what needs a brand response now, and what has already happened?”

## 5. Actions, authorization and effects

- `creator:hold` saves a local high-risk hold draft; until the canonical server executor, Permission/effect fence and Evidence-bearing result exist, it cannot pause a partnership.
- `response:draft` saves a local response draft; it cannot send, publish or change a risk record.
- No CTH fallback, automatic severity change or external communication is allowed.

## 6. Accessibility and localization

- Risk queue labels include severity, spread and recency; timeline events are announced in chronological order.
- Mobile preserves the selected incident heading while moving from queue to timeline.
- Integration key inventory: `screen.BMP-10`, `bmp10.subtitle`, `bmp10.severity.*`, `bmp10.spread.*`, `bmp10.recency.*`, `bmp10.timeline.*`, `bmp10.action.*`, `bmp10.recovery.*` for `zh-CN`, `en`, and `ko`.

## 7. Executable acceptance

- CTH Subject events are never rendered as BMP BrandFocus risks.
- Missing BrandFocus or source lineage withholds the incident and does not produce a healthy/zero state.
- A high-risk hold cannot succeed from a local click; a local draft is not sent, published or treated as a hold result.
- Severity queue and response timeline remain distinct at desktop and mobile widths.

Current decision: `IMPLEMENTED / BLOCKED_FOR_BRANDFOCUS_RISK`; BMP risk owner must supply a canonical BrandFocus source before real-user E2E acceptance.
