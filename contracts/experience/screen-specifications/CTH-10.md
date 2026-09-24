# CTH-10 — 报告与运营简报工作台

```yaml
screen_id: CTH-10
status: BLOCKED
revision: 1
owner_domain: CTH / Shared Capability Reporting
binding_ids:
  - BACKEND-GAP-017
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
artifact_disposition: BOUNDED_BLOCKED_STATE_IMPLEMENTATION_ONLY
reviewer: Codex bounded ROUND-11 Luna batch
reviewed_at: 2026-09-22
approval_reference: Product Owner approval of App / Experience Constitution §§30–36; this is not CTH-10 acceptance
```

## 1. User problem and product invariant

- **Role / context:** CTH operator in `GLOBAL / ALL` or an authorized focused CTH Subject.
- **User task:** choose a verified period, inspect a report/brief as a paged artifact, follow each conclusion to its source trail, and understand the methodology and action/outcome status before any export.
- **Completion signal for this bounded slice:** render only a scoped report payload with a verified source list. A report row or an HTTP 200 is not enough.
- **Invariant:** a report is not a screenshot of a dashboard. The storyboard keeps narrative, methodology, source trail and action/outcome implications separate.
- **Current limitation:** `_build_cth10()` reads the latest daily report and an unscoped Evidence query. The current response cannot be sent to the App as a scoped report.

## 2. Route, entry and return

- **Entry:** nested CTH reporting workflow from the CTH work surface or a completed Case/Decision trace. Shared shell routing is outside this batch.
- **Required read binding:** valid context plus `binding.actor_scope=verified`, matching `context_mode`, `domain=CTH`, `evidence_lineage=verified`, and report-level `scope_verified=true`. Focus mode must echo `subject_id`.
- **Exit / Trace / Return:** select a report section or source locally; Return restores the storyboard page and selected source. No report write, export, file creation or share effect is enabled.

## 3. Verified data and callable bindings

| Priority | UI field / action | Source / callable | Definition and missing behavior | Binding |
| --- | --- | --- | --- | --- |
| P0 | Report catalog | Existing CTH/Shared Reporting owner | Requires `reports[]` with stable ID, period, state and scope; no cross-scope rows | `BACKEND-GAP-017`, currently unscoped |
| P0 | Brief storyboard / preview | Same report owner | Requires narrative blocks with definition/window and status; do not invent numbers or conclusions | Unknown until scoped report contract exists |
| P0 | Source trail | Shared Evidence owner | Each displayed reference must be trusted and related to the selected report | Current query has no actor/Subject/origin filtering |
| DRAFT | Generate weekly brief | `report:write` | No backend result contract in this batch | Disabled |
| EXPORT | Export PDF/Excel | `report:export` plus permission/effect/audit result | No real report export endpoint is bound | Disabled |

For this bounded renderer, report source IDs are displayed only when the response marks them trusted and they are in the explicit CTH report allowlist (`EV-7701`, `EV-7710`). Unknown references are withheld.

## 4. State and recovery matrix

| State | Trigger | User-visible meaning | Available action | Acceptance |
| --- | --- | --- | --- | --- |
| Loading | Context/report read pending | 正在读取报告与运营简报 | None | CTH10-W-001 |
| Empty | Bound report catalog is empty | 当前范围内暂无报告。 | Refresh | CTH10-W-002 |
| Not collected | No scoped report/storyboard | 报告资料尚未接入，暂不能生成运营简报。 | Refresh | CTH10-W-003 |
| Partial | Report exists but source trail is incomplete | 报告可见范围有限，未核验来源不会显示。 | Inspect safe blocks; retry | CTH10-W-004 |
| Blocked | Scope/lineage/export binding missing; 401/403 | 当前范围暂不能查看报告资料。 | Retry; return | CTH10-W-005 |
| Offline / Error | Transport or malformed response | 暂时无法读取报告资料，请稍后重试。 | Retry | CTH10-W-006 |
| Ready | Bound catalog + storyboard + trusted references | Show outline, page preview, source trail and action/outcome status | Local selection only | CTH10-W-007 |

## 5. Purpose-built composition

- **Desktop/Web:** report storyboard outline on the left, one paged artifact preview in the center, and a source/methodology rail on the right. The primary object is the report artifact, not a KPI wall.
- **Mobile:** report list first, then one-page preview and a bottom source trail. Period/window and scope remain visible in the header.
- **Accessibility:** page/section/source order is explicit; source references include title and observed fact; loading and blocked states are live regions; keyboard can move from outline to preview to source rail.

## 6. Actions, authorization and effects

| Action | Required proof | UI behavior |
| --- | --- | --- |
| Select period/section/source | Bound read response | Local selection only |
| Generate brief | Exact `report:write` Permission, Effect Fence, idempotent result and report Evidence | Disabled; no optimistic draft or success |
| Export PDF/Excel | Exact `report:export` Permission, effect/audit result and real file response | Disabled; no fake download |

## 7. Executable acceptance

| Acceptance ID | Action / expected result | State path | Platform/input | Test layer |
| --- | --- | --- | --- | --- |
| CTH10-W-001 | Pending read hides report rows and announces loading | Loading | All widths | Widget |
| CTH10-W-002 | Bound empty catalog is empty and does not use the fixture | Empty | Desktop/mobile | Widget |
| CTH10-W-003 | Missing report/storyboard is not-collected and Generate stays disabled | Not collected | All widths | Widget |
| CTH10-W-004 | Unknown source IDs and hostile fields never render | Partial / hostile input | All widths | Widget |
| CTH10-W-005 | Missing scope/lineage blocks report data; Generate and Export are disabled | Blocked | Desktop/mobile | Widget + repository |
| CTH10-W-006 | 401/403/offline/malformed response hides server detail and offers retry | Error | Desktop/mobile | Widget |
| CTH10-W-007 | Storyboard/preview/source rail recompose at desktop, tablet and mobile widths; Trace/Return preserves selection | Ready | 1440 / 900 / 390 logical px | Widget |

## 8. Review decision and open dependencies

- **Decision:** BLOCKED for full CTH-10 acceptance. The bounded implementation is a scoped read-only report artifact surface with disabled write/export controls.
- **Required before DESIGN_READY / ACCEPTED:** actor-to-Subject report read binding, filtered Evidence query, report/storyboard owner, report generation contract, export endpoint, Permission/effect/audit result and runtime/E2E evidence.
- **Current disposition:** the existing aggregate report/Evidence builder is not exposed as App data.
