# BMP-07 — 活动工作台

```yaml
screen_id: BMP-07
status: OWNER_REVIEW
revision: 1
owner_domain: BMP
binding_ids: [BACKEND-GAP-024]
product_owner_approval: APPROVED_OVERALL_EXPERIENCE_CONSTITUTION_30_36
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: SOURCE_BACKED_SCOPE_BLOCKED_IMPLEMENTATION
reviewer: Bounded ROUND-13 implementation worker
reviewed_at: 2026-09-22
approval_reference: ROUND-13-BMP-CREATION-UI
```

## 1. User problem and product invariant

- A brand operator needs to connect an activity objective to audience, channel milestones and observed outcomes without confusing a plan with a result.
- BMP owns the brand/market activity. A verified BrandFocus or explicitly granted global range and canonical activity source are required; topic quota or cooldown is process context, not campaign truth.
- Scope modes are explicit: an authorized `GLOBAL_ALL` campaign collection is valid when globally scoped and sourced; `FOCUS` is limited to the selected BrandFocus. The page does not force a brand selection before a granted global read.
- `BACKEND-GAP-024` currently exposes no verified per-campaign BrandFocus activity list. The page must not invent campaigns or ROI.

## 2. Route and bindings

- Read callable: `LumenisCoreClient.screen('BMP-07')` / `/api/experience/screen/BMP-07`.
- Display gate: `binding.scope_read_evidence_version` and `binding.evidence_lineage_version` must both be `v2`, `binding.read_access` must be `ALLOWED`, and `binding.scope_mode` must match the returned context. `FOCUS` requires the exact selected `brand_id`; `GLOBAL_ALL` requires a null `brand_id` plus `global_read=ALL_GRANTED`. Legacy self-reported scope/permission booleans are not accepted.
- Expected fields: `campaigns[].goal`, `stage`, `kpis`, `timeline`, `outcome`, plus verified brand/source context.
- `campaign:write` saves a local campaign-content request draft; `campaign:close` saves a local close-request draft and must not imply a close result.
- No activity deep link, campaign selector or outcome calculation is invented locally.

## 3. State and recovery

- Loading preserves the selected brand context.
- Not collected says no campaign result is available; missing activity is not zero activity.
- Unscoped or denied data shows a brand-range guard and hides goals, timeline, ROI and channel totals.
- Offline/error offers retry and clears transient business data.
- Staged actions say “local request draft saved”; they never say launched, closed or measured.

## 4. Purpose-built composition

- Desktop composition is an objective strip followed by a five-step lifecycle: planned, budgeted, launched, observed and measured. A milestone timeline, channel mix and outcome plan-vs-actual section remain separate regions.
- The primary question is “what was planned, what actually happened, and what can be measured?” Planned and actual values never share one undifferentiated status.
- Mobile becomes a guided lifecycle with one milestone at a time, then a separate outcome section and channel details. It is not a dashboard card grid.

## 5. Actions, authorization and effects

- `campaign:write` saves a local request draft for authorized content activity; no campaign write is sent or persisted.
- `campaign:close` saves a local campaign-close draft. Until the canonical server executor, Permission/effect fence and Evidence-bearing result exist, no close effect is attempted or reported.
- Quota/cooldown can be shown only as a process notice and cannot be relabeled as ROI, reach or outcome.

## 6. Accessibility and localization

- Lifecycle steps are announced in order with planned/actual distinctions in each label.
- Timeline milestones have a linear list equivalent; color is not the only stage signal.
- Integration key inventory: `screen.BMP-07`, `bmp07.subtitle`, `bmp07.lifecycle.*`, `bmp07.milestone.*`, `bmp07.channel.*`, `bmp07.outcome.*`, `bmp07.action.*`, `bmp07.recovery.*` for `zh-CN`, `en`, and `ko`.

## 7. Executable acceptance

- A topic quota response alone cannot render a campaign, ROI or measured outcome.
- A verified campaign keeps planned, launched, observed and measured states distinct.
- BrandFocus leakage from another campaign is rejected by the view-model allowlist.
- Close/write actions remain blocked or save an explicitly local draft when exact approval/result fields are absent; no close or write success is shown.
- Desktop, compact and mobile widths preserve lifecycle and outcome semantics.

Current decision: `IMPLEMENTED / BLOCKED_FOR_CAMPAIGN_SCOPE`; the BMP owner must bind canonical activity results before real-user E2E acceptance.
