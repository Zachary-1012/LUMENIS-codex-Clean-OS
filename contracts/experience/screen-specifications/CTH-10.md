# CTH-10 — 报告与运营简报工作台

```yaml
screen_id: CTH-10
status: BLOCKED
revision: 2
owner_domain: CTH / Shared Capability Reporting
binding_ids:
  - BACKEND-GAP-017
product_owner_approval: M_BOUNDED_SOURCE_BRIEF_INCREMENT_2026_10_02
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_READY
design_ready_scope: SOURCE_BRIEF_START_STATUS_RESUME_JOB_READBACK_ONLY
artifact_disposition: BOUNDED_SOURCE_BRIEF_INCREMENT_FULL_SCREEN_BLOCKED
reviewer: M / Sol / 序境12
reviewed_at: 2026-10-02
approval_reference: M approved the bounded SourceBrief increment on 2026-10-02; period, weekly report, export and owned business quality remain BLOCKED; no ACCEPTED claim
```

## 1. User problem and product invariant

- **Role / context:** CTH operator in `GLOBAL / ALL` or an authorized focused CTH Subject.
- **User task:** choose a verified period, inspect a report/brief as a paged artifact, follow each conclusion to its source trail, and understand the methodology and action/outcome status before any export.
- **Completion signal for this bounded slice:** start a scoped source brief, inspect actual task state, then reopen the saved Job with its verified source list. This is not completion of a period/weekly business report.
- **Invariant:** a report is not a screenshot of a dashboard. The storyboard keeps narrative, methodology, source trail and action/outcome implications separate.
- **Current limitation:** the legacy `_build_cth10()` aggregate remains unsuitable as scoped report data. Existing SourceBrief task/job APIs provide a separate actor- and scope-checked incremental binding; period/weekly/export and owned business quality remain unclosed.

## 2. Route, entry and return

- **Entry:** nested CTH reporting workflow from the CTH work surface or a completed Case/Decision trace. Shared shell routing is outside this batch.
- **Required read binding:** legacy report payload still requires valid context plus `binding.actor_scope=verified`, matching `context_mode`, `domain=CTH`, `evidence_lineage=verified`, and report-level `scope_verified=true`. SourceBrief instead uses the exact task/job contract below, with server-issued principal, exact registered scope and verified source snapshot. Focus mode must echo `subject_id`.
- **Exit / Trace / Return:** select a report section or source locally; Return restores the storyboard page and selected source. No report write, export, file creation or share effect is enabled.

## 3. Verified data and callable bindings

| Priority | UI field / action | Source / callable | Definition and missing behavior | Binding |
| --- | --- | --- | --- | --- |
| P0 | Report catalog | Existing CTH/Shared Reporting owner | Requires `reports[]` with stable ID, period, state and scope; no cross-scope rows | `BACKEND-GAP-017`, currently unscoped |
| P0 | Brief storyboard / preview | Same report owner | Requires narrative blocks with definition/window and status; do not invent numbers or conclusions | Unknown until scoped report contract exists |
| P0 | Source trail | Shared Evidence owner | Each displayed reference must be trusted and related to the selected report | Current query has no actor/Subject/origin filtering |
| DRAFT | Generate weekly brief | `report:write` | No backend result contract in this batch | Disabled |
| EXPORT | Export PDF/Excel | `report:export` plus permission/effect/audit result | No real report export endpoint is bound | Disabled |

Source references are admitted by actual Canonical source identity, exact scope,
source snapshot integrity and matching `evidence_id` / `scope_evidence_ref` checked
by the existing reporting/Evidence owners. There is no fixed frontend EV-ID
allowlist. `canonical_ref` does not imply a valid `source_id`. Unknown, foreign,
malformed, hostile or unverified references remain withheld; replacing the old
fixture allowlist does not relax their rejection.

### 3.1 M-approved SourceBrief increment — 2026-10-02

The full screen remains `BLOCKED`. Only this increment is `DESIGN_READY`, approved
by M=序境12 under the sole Experience Constitution, for F implementation and W6
integration. These APIs already exist at source base `a85c35ee619ae75052f91b3b924e467bd8bc1622`;
source existence does not establish runtime or screen acceptance.

| Action | Exact existing API | Field/state and effect contract |
| --- | --- | --- |
| Generate source brief | `POST /api/experience/reports/source-brief/start` | JSON `limit` (1–100), optional `source_ids`, `business_question` (4–1500 characters), `image_source_ref`; server validates actor/scope and source IDs. A `revision` request is inherited parent input only and is outside this incremental UI action. HTTP 202 is task admission. |
| Inspect task | `GET /api/experience/reports/source-brief/tasks/<task_id>` | Envelope `task`; keep `task_id` and `job_id` distinct. `pending/running/succeeded/failed/interrupted` are actual execution states. |
| Resume interrupted task | `POST /api/experience/reports/source-brief/tasks/<task_id>/resume` | Body exactly `{}`; a new request revalidates current principal, exact scope, Permission and effect boundary before execution/commit. HTTP 202 remains admission. |
| Reopen saved result | `GET /api/experience/reports/source-brief/jobs/<job_id>` | Envelope `result`; canonical `daily_reports` readback rechecks actor, scope, source selection, Evidence and hashes. Never substitute an in-memory request or the legacy aggregate. |

CoreClient sends `X-Domain-Id: CTH`, `X-Product-Id: CTH` and explicit
`X-Lumenis-Context-Mode: GLOBAL_ALL/FOCUS`; focused requests have the exact
`X-Subject-ID`, and GLOBAL requests have no Subject/BrandFocus selector. Headers
select context; they do not grant Permission. The Core resolves the sealed local
workspace principal or authenticated actor, canonical registry and module `reports`
read/write scope, then requires `REPORT_GENERATE` Permission/effect/audit before
task admission, execution and artifact commit.

On success, read `job_state`, `artifact_outcome`, `source_brief.records`,
`business_analysis.state`, `operator_review`, `evaluation` and `review_status`
independently. `job_state=completed` plus
`artifact_outcome=persisted_and_reopened_verified` proves the source brief was
saved/reopened at its `report_id/artifact_hash/source_count`; it does not prove
business analysis or quality approval. `review_status=HUMAN_PENDING` remains
pending. Current owned inference is not service-bound; do not label unavailable
analysis successful. No period or export is supplied by this increment, and
`publish_status=not_performed` never becomes publication.

## 3.2 Task continuity, language and recovery

- Keep the source brief task/result region distinct from the blocked period-report
  storyboard. Show submission, running, saved-source-result, interrupted, denied,
  unavailable and failed states in business language. Export/weekly controls stay
  blocked until their own contracts close.
- Capture domain/context/Subject and a request generation at submission. On focus
  change, Clear, navigation or retry, invalidate outstanding responses. A late
  result cannot overwrite the new scope or make an old result appear current.
- Reopen uses `job_id` through the actual GET API after returning/reloading. Keep
  useful error recovery and return to the prior task/source selection. An empty
  registry/source result stays honest; never fabricate report prose or zeros.
- Chinese, English and Korean must cover actions, pending/running/saved/interrupted/
  denied/unavailable/error copy and accessibility announcements. Raw provider,
  exception or private path details are not user copy.
- At 1440px, use the existing report/source composition with one clearly identified
  task result; at 390px, recompose into task/result then source trail. Keyboard,
  screen reader labels, focus recovery and overflow require actual checks at both
  widths; a passing widget fixture is not live user acceptance.

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
| Generate/reopen/resume source brief | Server actor/exact scope; `REPORT_GENERATE` and audit/effect checks for writes; verified Job readback | Enabled only within §3.1; task admission, source-result save and business quality remain distinct |

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
| CTH10-SB-001 | Valid scoped start returns actual task admission, then polls to a persisted result; no optimistic saved/analysis success | Pending → running → source result | Real Canonical inputs; 390 / 1440; zh/en/ko | Repository + widget + live E2E |
| CTH10-SB-002 | Interrupted task resumes through a fresh permission check; denied/revoked scope performs no forbidden write | Interrupted → resume or denied | Actual task/principal/scope | Integration + live recovery |
| CTH10-SB-003 | Reopen result after navigation/Core recovery verifies same Job/source/hash and keeps HUMAN_PENDING | Saved → reopened | Actual saved Job | Integration + live E2E |
| CTH10-SB-004 | Clear/focus change drops late result; foreign/unknown/hostile source identities are withheld | Any → GLOBAL/new focus | 390 / 1440; keyboard and screen reader | Widget + repository + live E2E |

## 8. Review decision and open dependencies

- **Decision:** full CTH-10 remains BLOCKED; §3.1–3.2 SourceBrief increment is M-approved DESIGN_READY, not IMPLEMENTED/ACCEPTED evidence. Period/weekly/export controls remain blocked.
- **Required before DESIGN_READY / ACCEPTED:** actor-to-Subject report read binding, filtered Evidence query, report/storyboard owner, report generation contract, export endpoint, Permission/effect/audit result and runtime/E2E evidence.
- **Current disposition:** the existing aggregate report/Evidence builder is not exposed as App data.

### 8.1 M acceptance of the source-only main flow — 2026-10-02

M reviewed the frozen fourteen App source/test files, 75 affected tests and actual
same-origin browser operation, and accepted this bounded flow: GLOBAL CTH source
brief creation, real task completion, 29 Canonical source records with the returned
Evidence references, saved Job/hash readback, leave/reload/reference reopen,
offline result hiding/reconnect, foreign Focus denial and Clear back to GLOBAL.
The owning evidence is `00-GOVERNANCE/evidence/round-06/APP-WORKFLOW-VERIFICATION-2026-10-02.md`.

The actual task is `rbrief_ab54bb81-8feb-467c-9c0f-2458821909f1`, Job/Report
`brief-fb2192a3e5784d18a68ed0186b49733b`, artifact SHA256
`59b5efb3a98623106b35883a533b1b4d9a73576a3f02a79af6df082e438acff6`.
Evaluation rows 131–133 record the material workflow, not business usefulness.
Analysis was not requested; human review remains pending. The fourteen source/test
hashes remain frozen; the six Website files were published separately.

W6 verified the four API callables and their scope/context helpers match current
main; the Task/Job modules and `lumenis_app_api.py` also match main. Source-only
execution does not enter the local, unaccepted owned-business adapter. Other
Collector, AI, Skill, Memory and business candidates are excluded from this
publication. Genuine interrupted-task resume and operating-system clipboard
transfer remain `LIVE_NOT_VERIFIED` / `NOT_VERIFIED`. Full CTH-10, owned analysis,
full C3, native surfaces, Product Owner repeat operation and release remain open.
