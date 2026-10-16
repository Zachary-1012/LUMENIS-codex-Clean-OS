# BMP-01 — 品牌市场总览

screen_id: BMP-01
status: REVIEWED_FOR_SCOPE_BLOCKED_SLICE
revision: 2
owner_domain: BMP
binding_ids: [BACKEND-GAP-018]
product_owner_approval: APPROVED_OVERALL_EXPERIENCE_CONSTITUTION_30_36
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: NON_AUTHORITATIVE_EXPLORATION_ONLY
reviewer: Codex delegated BMP-01 specification review
reviewed_at: 2026-09-20
approval_reference: Product Owner instruction in current task; implementation copy update against origin/main b4608331eacb868ff13ef74e770aa54c309ebef3

## 1. User problem and product invariant

- Role and authorized context: A brand or market operator working in BMP. A trusted actor and an authorized BrandFocus are required before showing brand-level truth. The current screen endpoint returns neither.
- User task and completion signal: Inspect the selected brand's market signals and trace each visible signal to canonical Evidence. Completion requires an authorized selected brand, brand-scoped metrics/records, and traceable source lineage. This task is currently blocked.
- Owner and invariant: BMP owns brand/market-first data and workflows. Shared Evidence retains its original origin and scope. CTH SubjectContext is not a substitute for BMP BrandFocus.
- Out of scope for this slice: Selecting or inferring a brand, mapping note authors to brands, displaying product-wide ZBMP aggregates as brand metrics, using CTH records/events, creating reports/campaigns, and claiming the Golden Page is complete.
- Implementable part: An honest scope/access guard, retryable read state, and distinct responsive BMP composition. Brand analytics remain hidden until source, actor, Permission, brand scope, and Evidence lineage are verified.

## 2. Route, entry, exit and return

- App entry: BMP-01 is mounted in the canonical App Shell and is reachable from desktop, compact and mobile navigation. The page remains a source-backed read slice, not an accepted or released screen.
- Required context: Verified actor and selected, authorized BMP brand/market context. The route cannot grant authorization. Current response contains no such context.
- Current Product Core call: GET /api/experience/screen/BMP-01, implemented by experience_runtime.screen_viewmodel. There are no query parameters, cancellation, pagination, or idempotency concerns for this read. The existing Flutter client LumenisCoreClient.screen('BMP-01') is the transport.
- Exit/deep links: Shell navigation and restoration among the five Golden Pages are implemented. Direct BMP-01 destinations or deep links to BMP-02/BMP-05, reports or plans have not been verified; do not invent them.
- Trace/return: No Evidence trace route or return-state contract is currently bound. Refresh preserves the page, and the Shell restores its active Golden Page; object-level return state remains unavailable.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source / callable | Definition, units, window | Freshness / missing behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Screen identity and bound state | Experience API adapter | GET /api/experience/screen/BMP-01; response screen, bound, source | API envelope; no metric | Missing/mismatched envelope becomes contract error | BACKEND-GAP-018 | experience_runtime.py screen_viewmodel; experience_screens.py _envelope |
| P0 | Product/domain identity | BMP canonical adapter | truth.product_id, truth.domain_id | Must be exactly ZBMP / zbmp | Wrong/missing owner identity fails closed | BACKEND-GAP-018 | experience_screens.py _build_bmp01; api_dual_domain.py get_zbmp_product_snapshot |
| P0 | Authorized actor and selected BrandFocus | SYSTEM identity/Permission + BMP scope owner | No verified callable or response field | Required to show brand data | UNKNOWN → block all analytics | BACKEND-GAP-018 | Registry row actor_scope; no field in current screen payload or _build_bmp01 |
| P0 | Read authorization result | SYSTEM Permission | No screen-specific PermissionGate decision in screen_viewmodel; global app _basic_auth applies only when configured | Required for a trusted App read | UNKNOWN → show access/scope guard; do not display returned business data | BACKEND-GAP-018 | experience_runtime.py screen_viewmodel; app.py _basic_auth; permission.py PermissionGate is canonical owner but is not called by this route |
| P0 | Canonical-to-Evidence lineage | BMP Canonical Data + Shared Evidence | Snapshot preserves evidence_ref and provenance on canonical rows; no verified BMP-01 Evidence lookup/validation call | Per-record origin/scope/freshness required | UNKNOWN → do not expose risk records or evidence IDs | BACKEND-GAP-018 | api_dual_domain.py _safe_zbmp_record; experience_screens.py _build_bmp01 |
| P1 | Canonical record total, sentiment/risk/engagement distributions, 14-day trend | BMP | truth.canonical_count; section metric/chart payload from get_zbmp_product_snapshot() | Whole ZBMP canonical dataset; trend uses captured dates over the last 14 days | Current endpoint is unscoped by brand; do not render as selected-brand truth | BACKEND-GAP-018 | api_dual_domain.py get_zbmp_product_snapshot; experience_screens.py _build_bmp01 |
| P1 | Risk records | BMP canonical rows | sections[type=risks].items[]: title, description, risk level/score, evidence reference | Up to five risk-matched records from the whole ZBMP snapshot | Brand attribution and Evidence lineage are unverified; keep hidden | BACKEND-GAP-018 | experience_screens.py _build_bmp01; existing ZBMP isolation test |
| P1 | Events, risk index, brand health | BMP event/metric owners | No canonical event contract; risk index and health score have no ZBMP metric owner | Not defined | Explicitly unavailable; never derive or show fixture values | BACKEND-GAP-018 | experience_screens.py _build_bmp01 blocked list and not-collected sections |
| P1 | Refresh | Experience App → same read endpoint | LumenisCoreClient.screen('BMP-01') | Safe GET; no write, external effect, or Evidence emission | Distinguish offline, HTTP denial, contract error and retry | BACKEND-GAP-018 | app/lib/core/lumenis_core_client.dart; route above |

The canonical query filters canonical_data by both product_id = ZBMP and domain_id = zbmp. A brand_key is emitted only if the stored row has brand_key_verified; current tests prove an unverified row yields no brand grouping. The snapshot has no selected-brand filter. This is product-slice evidence, not a selected-brand contract.

## 4. State and recovery matrix

| State | Trigger/evidence | User-visible meaning | Available actions | Recovery/return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Initial request or refresh in progress | 正在加载品牌市场信息 | None; announce busy | Keep page identity; do not flash data from another scope | BMP01-W-01 |
| Empty / no source data | Endpoint says NOT_COLLECTED | 暂时没有品牌市场数据 | Retry | Keep all metrics unavailable | BMP01-W-02 |
| Not collected | truth.data_state=NOT_COLLECTED | 品牌表现、竞品动态与市场变化会在数据可用后呈现 | Retry | Do not display missing metrics as zero | BMP01-W-02 |
| Fresh | Endpoint contract returned successfully | 暂无可展示的关注品牌信息 | Retry | Continue to scope blocker until actor/brand binding exists | BMP01-W-03 |
| Stale | Capture time exists but freshness has no verified selected-brand rule | Brand freshness is not shown | Retry | Do not surface timestamp as selected-brand freshness | BMP01-W-04 |
| Partial | Some product-wide metrics/records exist but scope or Evidence lineage is absent | 当前没有已确认的关注品牌，因此暂不展示品牌表现或竞品数据 | Retry | Hide the unscoped payload; preserve explicit blocker | BMP01-W-05 |
| Offline | Core client reports socket/unavailable failure | 暂时无法连接，请检查网络连接后重试 | Retry | Retain no stale business data | BMP01-W-06 |
| Blocked / access denied | Missing BrandFocus; HTTP 401/403; wrong product/domain; or missing lineage | 当前账号暂时无法查看此内容 | Retry; Shell may later provide its real account/context recovery route | Do not grant access or show metrics; restore route state only through Shell | BMP01-W-07 |
| Error | Other HTTP, JSON, or response-contract failure | 品牌市场信息暂不可用，请稍后重试 | Retry | Show stable Chinese recovery copy, never raw payload/error | BMP01-W-08 |
| Success / persisted | Read-only response; nothing is written | No successful selected-brand state exists under current contract | None | A future success state requires tested owner, actor/scope, Permission and Evidence | BMP01-W-09 |

## 5. Purpose-built desktop composition

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-01)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- Primary question: Which authorized brand's market signals am I viewing, and can each signal be traced?
- Hierarchy: A compact brand panel occupies the left side and names the current viewing context in business language. A broad right-side market field is reserved for brand performance, competitor movement and market change. Until an authorized brand and scoped records exist, it presents a clear empty state without exposing implementation or permission diagnostics and without drawing fabricated signals.
- Primary interaction: Refresh the existing BMP-01 read endpoint; show its result as contract status only. It must not unlock the canvas.
- Secondary interaction and keyboard: Tab order is heading → context rail → scope guard → refresh. Enter/Space activates refresh; focus returns to the refresh control after completion.
- Density/resize: Use LayoutBuilder; at workspace width ≥ 960 px use the two-region desk with content constrained to a readable maximum. Below that width, switch to the single active scope task. No hardware-type checks.
- Screen-specific composition: BMP is organized around BrandFocus and a market/evidence relationship. It never uses CTH Subject navigation or a generic KPI dashboard template.

## 6. Purpose-built mobile composition

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-01)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- Single active task: Explain that brand-market information is not available yet and let the user refresh it.
- Navigation/back: Shell owns route/back behavior; page does not invent alternate brand destinations. Keep a compact BMP · 品牌市场 identity in view.
- Touch: Refresh uses a minimum 48 px target. The focus guard precedes the recovery control in screen-reader order.
- Recomposition: Replace the PC side rail/canvas with one vertical brand context and market-information state. Do not shrink the PC split layout or show a miniature dashboard.
- Offline/interruption: Retry the same GET; display no cached business data because none is scoped to a verified brand.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read/write/effect | Idempotency / reversal | Evidence emitted | Confirmation and failure |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh BMP-01 source contract | Experience API adapter; actor and brand scope currently unknown | No screen-specific PermissionGate decision verified; HTTP Basic may guard route when enabled | GET only; no write or external effect | Safe repeat; no reversal needed | None emitted by the read | Keep blocked after response; separate offline, access denial, contract error and service error |
| Select/switch brand | No verified BMP owner/callable in this screen contract | UNKNOWN | Not implemented | N/A | N/A | Disabled/absent until canonical BrandFocus owner, actor authorization and permission are verified |
| Draft report/plan; navigate to creator analysis | Existing design actions have UNKNOWN target/scope/evidence and are not bound to a callable | report:write / plan:write claims are not verified here | Do not execute or present as active actions | N/A | N/A | Omit from this slice; no local-only success behavior |

## 8. Accessibility, motion and localization

- Keyboard: Preserve visible focus; Tab/Shift+Tab through the guard then refresh; Enter/Space retries. Do not trap focus during loading.
- Screen reader: Announce the current brand-market availability in plain Chinese, followed by the refresh control and its result with polite live-region semantics. Do not announce implementation gates or internal identifiers.
- Chart/table equivalents: No chart/table is shown in the blocked slice. If those fields become eligible later, provide a data table and cited source equivalent.
- Motion: No decorative motion. Respect reduced motion; state change may use no animation.
- Localization: Chinese first, short labels; no status encoded by color alone; wrap long errors without horizontal scrolling.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State/error path | Platform/input | Test layer | Current evidence/reference |
| --- | --- | --- | --- | --- | --- |
| BMP01-W-01 | Open BMP-01; page calls only GET /api/experience/screen/BMP-01; loading is announced | Loading → scope blocked | Flutter widget / keyboard and touch | Widget | LumenisCoreClient.screen; new local widget test |
| BMP01-W-02 | Return uncollected snapshot; show not-collected status and no zero-valued metric | Not collected | Widget | Widget + existing backend unit | tests/test_bmp_truth_isolation.py::test_zbmp_missing_canonical_table_is_not_collected |
| BMP01-W-03 | Return correct bound ZBMP/zbmp payload with unscoped metrics/risk records; show scope guard and render none of those payload values | Successful API read, unauthorized scope | Wide PC and narrow mobile | Widget | tests/test_bmp_truth_isolation.py::test_zbmp_api_and_experience_use_same_snapshot; new local widget test |
| BMP01-W-04 | Return only a latest capture timestamp without BrandFocus; do not call it selected-brand freshness | Partial/stale | PC and mobile | Widget | Current _build_bmp01 contract; new local widget test |
| BMP01-W-05 | Return an unverified author/brand-like record; do not display or associate it | Partial/blocked | Widget | Widget + backend unit | test_zbmp_snapshot_filters_cth_and_does_not_infer_brands; new local widget test |
| BMP01-W-06 | Core unavailable; show offline recovery and a working retry | Offline | Widget | Widget | Core exception contract; new local widget test |
| BMP01-W-07 | HTTP 401/403 or wrong product/domain; show access/scope guard and no business payload | Access denied / scope blocked | Widget | Widget + API integration | app.py::_basic_auth, _build_bmp01; backend enforcement still needs dedicated acceptance |
| BMP01-W-08 | Other transport/schema failure; show recoverable error without raw body | Error | Widget | Widget | Core exception contract; new local widget test |
| BMP01-W-09 | Verify no write, report, plan, event synthesis, CTH fallback or Evidence claim occurs | All current states | Repository + API integration | Widget / existing Python unit | tests/test_bmp_truth_isolation.py; no write route invoked |
| BMP01-W-10 | Verify user-visible loading, empty, blocked and failure states contain business wording only and expose no implementation identifiers or data-pipeline diagnostics | All user-visible states | PC and mobile | Widget | app/test/features/bmp01/bmp01_screen_test.dart |

API integration remains an existing Python acceptance layer, not replaced by Flutter fixtures. Runtime/E2E for an authorized selected brand is BLOCKED until Product Core returns a verified actor, BrandFocus, per-screen read Permission decision and Shared Evidence lineage. The current implementation must be recorded as IMPLEMENTED / BLOCKED_FOR_BRAND_SCOPE; it is not a completed Golden Page.

## 10. Review decision and open questions

- Decision: PASS_FOR_SCOPE_BLOCKED_SLICE; all source-dependent brand analytics and writes remain BLOCKED.
- Reviewer and date: Codex delegated BMP-01 specification review, 2026-09-20.
- Product direction: Product Owner approved the App/UX architecture and Experience Constitution §§30–36 on 2026-09-20. This screen spec applies that accepted direction to the verified current owner only.
- Open questions and next action:
  1. SYSTEM: provide a server-verified actor and a canonical Permission decision for this screen read. The App Shell and in-memory Basic Auth transport exist; the screen route still has no local PermissionGate call or actor-to-BrandFocus authorization.
  2. BMP owner: define how a user selects an authorized brand/market and how the selected BrandFocus is carried to Product Core. Do not infer from author/source fields.
  3. BMP canonical owner: scope the ZBMP snapshot by verified brand_key and define KPI units/windows before the App displays it as brand truth.
  4. Shared Evidence owner: validate each evidence_ref against canonical Evidence and return stable lineage for the selected brand.
  5. BMP owner: define canonical brand events and any health/risk evaluation outputs before adding those panels.
  6. App Shell routing and restoration are already present. After SYSTEM/BMP supply the trusted context contract, bind that context and verify it through authenticated runtime acceptance.
- Changes required before brand analytics implementation: resolve the four remaining actor/scope, canonical metrics, Evidence lineage, and brand-event owner contracts above; update this spec and binding row from source evidence; add API/permission/Evidence integration cases; then bind data without adding parallel APIs.
- Acceptance evidence after this slice: scoped Flutter widget tests pass; root slice owner runs backend/API regression and live runtime/E2E when the actual authorized context becomes callable.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 回答授权品牌的市场信号与值得关注的趋势。
- **屏幕专属呈现：** 市场脉冲、趋势候选和证据抽屉；给时间窗、样本与来源覆盖
- **来源、范围与版本连续性：** 品牌/global scope、Evidence、采集时间和指标版本随同一Brief进入方案
- **四端差异：** Web/Desktop信号与来源并读；Mobile先优先信号再证据；官网只讲已验证能力
- **失败与恢复：** 未授权、样本不足、撤源时隐藏结论，unknown不补零
- **补充验收：** 从信号回源并继承资料；推荐不能直接成为决策。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
