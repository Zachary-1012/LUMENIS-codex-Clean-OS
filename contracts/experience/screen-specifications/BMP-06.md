# BMP-06 — 内容生产台

```yaml
screen_id: BMP-06
status: OWNER_REVIEW
revision: 1
owner_domain: BMP
binding_ids: [BACKEND-GAP-023]
product_owner_approval: APPROVED_OVERALL_EXPERIENCE_CONSTITUTION_30_36
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: SOURCE_BACKED_SCOPE_BLOCKED_IMPLEMENTATION
reviewer: Bounded ROUND-13 implementation worker
reviewed_at: 2026-09-22
approval_reference: ROUND-13-BMP-CREATION-UI
```

## 1. User problem and product invariant

- A brand operator needs to move an approved content idea through drafting, review and authorized release while retaining version and source context.
- BMP owns the brand/market workflow. A current BrandFocus or explicitly granted global range, actor read access, content lineage and action-specific approval are required before content is shown or released.
- Scope modes are explicit: an authorized `GLOBAL_ALL` response may show a global brand collection with verified lineage; `FOCUS` must match the selected BrandFocus. One mode is never presented as the other.
- Current backend gap `BACKEND-GAP-023` is unscoped and cannot supply a verified brand read. The implementation therefore renders only a scope guard until that contract exists.
- Out of scope: inferring a brand from a source record, showing product-wide content counts, directly publishing, or treating an AI draft as approved content.

## 2. Route, entry, exit and return

- Read callable: `LumenisCoreClient.screen('BMP-06')`, corresponding to `/api/experience/screen/BMP-06`.
- Required response envelope: `ok`, `screen`, `bound`, `source`, `focus_context`, `binding`, `truth`, and allowlisted `assets`.
- Display gate: `binding.scope_read_evidence_version` and `binding.evidence_lineage_version` must both be `v2`, `binding.read_access` must be `ALLOWED`, and `binding.scope_mode` must match the returned context. `FOCUS` requires the exact selected `brand_id`; `GLOBAL_ALL` requires a null `brand_id` plus `global_read=ALL_GRANTED`. Legacy self-reported scope/permission booleans are not accepted.
- Exit and restoration remain Shell-owned. The page does not invent content deep links or a local brand selector.
- Current backend response is not sufficient for a real delivery loop; no content is displayed as brand truth until the binding is verified.

## 3. Verified data and callable bindings

| Field/action | Owner | Current contract | Missing behavior | Binding |
| --- | --- | --- | --- | --- |
| Asset title, kind, state | BMP Content | `assets[].title`, `kind`, `state` | Hide records without verified brand scope and lineage | BACKEND-GAP-023 |
| Version/review status | BMP Content | `version`, `review_state`, `approval_state` | Keep review and release distinct | BACKEND-GAP-023 |
| Source relationship | Shared source/content owner | `evidence_ref` is required as a gate, never shown as an implementation identifier | Withhold asset if absent | BACKEND-GAP-023 |
| New content | BMP Content | `content:draft` action contract | Save a local content draft only; do not write | BACKEND-GAP-023 |
| Submit review | BMP Content | `content:submit` action contract | Save a local review-request draft only; do not submit | BACKEND-GAP-023 |
| Publish | BMP Content + effect fence | `content:publish`, high-risk confirmation | Save a local publishing-request draft only; no effect without the canonical executor and result | BACKEND-GAP-023 |

## 4. State and recovery matrix

| State | User-visible behavior | Recovery |
| --- | --- | --- |
| Loading | Keep the production task identity and announce loading | Wait or refresh |
| Not collected | Explain that no source-backed content is ready | Refresh; do not show zero assets |
| Scope blocked / denied | Explain that the selected brand cannot be confirmed | Return through Shell context or retry |
| Offline / error | Explain that content production is temporarily unavailable | Retry without stale business records |
| Ready | Show only verified assets; review and publish remain separate | Refresh |
| Action staged | Confirm a local request draft was saved; nothing was written or published | Wait for the canonical executor, approval and action result |

## 5. Purpose-built desktop composition

- Use an editorial production board with six distinct lifecycle swimlanes: brief, draft, review, approved, scheduled and released. A version inspector sits beside the board for the selected asset.
- The primary question is “what is the next authorized production step for this brand asset?” The page is not a KPI dashboard and does not reuse a generic card grid.
- A compact action rail exposes “save ... draft” controls with the matching approval state; each control visibly remains local and non-executing.
- At narrow widths the board becomes a single production queue followed by the selected version detail; it is not a shrunken desktop board.

## 6. Actions, authorization and effects

- `content:draft`: save a local draft of the request; no content is created.
- `content:submit`: save a local review-request draft; no review is submitted.
- `content:publish`: save a local publishing-request draft. Until the canonical server executor, Permission/effect fence and Evidence-bearing result exist, no publish effect is attempted or reported.

## 7. Accessibility and localization

- Keyboard order is heading, scope context, lifecycle queue, selected version, then action rail. Each lane has a meaningful label.
- Screen-reader copy describes brand content status and next business step, not implementation diagnostics.
- Table/queue content has a linear mobile equivalent and action state announcements.
- Integration key inventory: `screen.BMP-06`, `bmp06.subtitle`, `bmp06.lane.*`, `bmp06.asset.*`, `bmp06.action.*`, `bmp06.state.*`, `bmp06.recovery.*` for `zh-CN`, `en`, and `ko`.

## 8. Executable acceptance

- An unscoped backend payload renders the scope guard and none of its asset titles, states or counts.
- A verified BrandFocus payload renders the six-lane workflow and preserves distinct draft/review/approval/release states.
- Missing lineage removes only the affected asset; it never becomes an empty success or zero count.
- A denied publish action remains blocked; an enabled local-draft action shows a non-executed state and never claims a successful write or publish.
- Desktop, compact and mobile widths expose the same state semantics with the purpose-built compositions above.

Current decision: `IMPLEMENTED / BLOCKED_FOR_BRAND_SCOPE`; backend owner must provide actor-to-BrandFocus read and action result contracts before real-user E2E acceptance.
