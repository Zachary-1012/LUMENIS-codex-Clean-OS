# CTH-01 — Commercial Operations Overview

```yaml
screen_id: CTH-01
status: BLOCKED
revision: 2
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-005
  - BACKEND-GAP-006
  - BACKEND-GAP-007
product_owner_approval: APPROVED — user approved App architecture and Experience Constitution §§30–36 for implementation on 2026-09-20; this is not per-screen acceptance
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: NON_AUTHORITATIVE_EXPLORATION_ONLY
reviewer: Codex delegated CTH-01 source review
reviewed_at: 2026-09-20
approval_reference: Product Owner instruction approving App / UX §§30–36 and requiring business-language UI copy; source baseline origin/main b4608331eacb868ff13ef74e770aa54c309ebef3
```

## 1. User problem and product invariant

- **Role / authorized context:** CTH commercial operator. The screen reads only the Product Core's current Subject context from `GET /api/experience/runtime/identity`. It requires `domain == cth`, `subject.product == CTH`, and a non-empty `subject.subject_id`. It does not load the Subject registry or treat membership in a list as authorization.
- **User task:** understand current operating activity, inspect one returned event, and return to the same activity stream.
- **Completion signal for this slice:** source-backed Subject context and real CTH fields render; unavailable, empty, error, and unscoped data remain explicit.
- **Invariant:** CTH is Subject-first. The API's current Subject may label context, but the current contract does not bind an authenticated actor or a domain permission decision to that Subject. Do not label it “authorized” in the App.
- **Out of scope:** changing Subject, creating a Case/Decision/Plan, notifying a team, report creation/export, event detail navigation, source navigation, and unverified trend visualization.

## 2. Route, entry, exit and return

- **Entry:** `Cth01Screen(client: ...)` after the product shell chooses the CTH workflow. This slice has no route or deep-link registration.
- **Context gate:** fetch runtime identity first. Fetch the CTH-01 ViewModel only for a returned CTH domain and non-empty current CTH Subject. Otherwise show a blocked-context state and do not fetch the screen aggregate.
- **Backend read:** `GET /api/experience/screen/CTH-01`; no parameters, pagination or cancellation contract.
- **Authentication:** when Basic auth is enabled, `app.py::_basic_auth` protects these routes; neither path is in the CTH anonymous read-only allowlist. The App launch surface now accepts credentials after a 401; `LumenisCoreClient` keeps them in memory and sends them only over HTTPS or loopback HTTP. A 401 clears the active session; a 403 stays a distinct access-denied state. This does not bind the authenticated actor to the current Subject or add a screen-level Permission decision.
- **Exit / Trace / Return:** selecting an event exposes its returned title, summary, time, severity and tags in an inline inspector. Internal event identifiers are not rendered. “Return to activity” clears the local selection. The event list remains mounted and unfiltered; the same Subject, order and scroll position remain.
- **No API-provided Subject:** show a blocked state; never substitute a listed Subject or the contract fixture.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source / callable | Definition, units, freshness and missing behavior | Binding / Evidence |
| --- | --- | --- | --- | --- | --- |
| P0 | Current business context | SYSTEM subject context via CTH read | `experience_runtime.runtime_identity()` → `subject.subject_id`, `subject.brand_key`, `subject.product`, `domain`; Subject from `subject_context.current_scope()` | Use returned `subject_id` only as a gate when domain is `cth` and product is `CTH`; do not display internal IDs or response-generation time as business freshness. Actor-to-Subject authorization is not returned. Missing / mismatch = BLOCKED. | Context source verified; actor-scope permission remains UNKNOWN. |
| P1 | Negative voice count | CTH DB read, through the CTH-01 aggregate | `experience_runtime._build_cth01()` → `database.get_stats().negative`; `database._verified_base()` applies verified-note and Subject filters | Integer record count; `ready` only when the source returns a value, `offline` when the source failed. API aggregate timestamp is not source freshness. | BACKEND-GAP-005 partial. No per-record citations in this field. |
| P1 | Footfall and member sales | CTH external-data dependency | CTH-01 KPI items `cth.footfall`, `cth.member_sales` | Backend returns `value: null`, `state: notcollected`, with POS / sales source reasons. Render as NOT_COLLECTED; never as zero. | BACKEND-GAP-005; external source unavailable. |
| P1 | Signal stream | CTH event read | `experience_runtime._build_cth01()` → `database.get_events(6)`; each item is filtered by `subject_rules.subject_hit`; active events sort first, but active and closed records may both be returned. ViewModel displays at most three. | Render only returned business fields: date/time, title, summary, risk level and tags. Hide event identifiers. Empty state only when returned section state is `empty`. Do not claim total/open-event count. | BACKEND-GAP-006 partial. Event references do not establish Evidence lineage. |
| P1 | Risk notes | CTH DB read | `_build_cth01()` → `database.get_high_risk_notes(6)` → `database._verified_base()`; ViewModel displays at most two | Render title, returned text, level and score only if numeric and returned. Missing score stays unavailable. Hide internal note identifiers. | CTH source verified; no Case/action permission binding. |
| P2 | Daily canonical summary values | Shared Reporting calculation over CTH-filtered source reads | `_build_cth01()` → `lumenis.shared.reporting.daily.generate_today_summary(today)`; uses `database.get_notes_by_date_range`, `database.get_events(20)`, `calculate_risk_index`, `calculate_brand_health_score` | If present, label risk index on its 0–100 scale; the legacy `brand_health_score` is shown as a current-Subject health score, also 0–100; risk count is medium + high notes and excludes critical notes. No trend or delta claim. Null summary = unavailable. | BACKEND-GAP-007 partial; deterministic computation, not an AI conclusion. |
| BLOCKED | 14-day signal chart | CTH DB read via runtime builder | `experience_runtime.days_labels_series(14)` → `database.get_stats_by_date_range` | The builder converts a per-day source exception into numeric zero and labels the section READY. Zero cannot be distinguished from missing data; omit this chart and show “趋势状态待后端区分缺数与零值”. | BLOCKED: source must expose per-day state/error explicitly. |
| BLOCKED | CTH-linked Evidence items | Shared Evidence store | `lumenis.shared.evidence.store.query_evidence(limit=2)`, called without product, Subject, origin-domain or source filter | The current aggregate includes recent unscoped records and a generic hard-coded lineage. Do not render record contents or attach these items to CTH. Show a blocked lineage explanation. | BLOCKED: canonical query must provide verified CTH Subject scope and real lineage. |
| BLOCKED | Brief, range, export, event navigation, plan and notify actions | CTH / Shared / SYSTEM action owners unresolved | Actions appear as ViewModel declarations only in `experience_runtime.py`; no CTH-01 App callback and no verified request contract for these actions | Show no enabled action control and cause no write, export, navigation, Permission decision or external effect. | Permission/effect and destination contracts UNKNOWN; high-risk notify must remain absent. |

All calls above are through the existing `LumenisCoreClient.runtimeIdentity()` and `LumenisCoreClient.screen('CTH-01')`. There is no new API. This implementation review used live `origin/main` at `b4608331eacb868ff13ef74e770aa54c309ebef3`.

## 4. State and recovery matrix

| State | Trigger / evidence | User-visible meaning | Available action | Recovery / acceptance |
| --- | --- | --- | --- | --- |
| Loading | Core identity / screen request pending | 正在加载经营主体与运营动态 | None | Skeleton/context label; announce loading. |
| Empty / no signal | Backend `events.state == empty` and items empty | 暂无运营动态；当前没有可展示的运营动态 | Refresh | Distinguish a confirmed empty result from offline/error; do not infer collection health. |
| Not collected | Footfall/sales KPI state `notcollected` | 对应指标显示“尚未采集” | None | Keep the source state distinct from an empty result; never render 0. |
| Fresh | UNKNOWN | No source-level freshness timestamp exists for these values | None | Do not use “实时”/“最新” claims or display API response generation time as data freshness. |
| Stale | UNKNOWN | No stale indicator is provided | None | Remains unverified. |
| Partial | One or more fields unavailable / blocked while others are returned | Some CTH fields are available; withheld fields are named | Refresh | Keep data status local to each section. |
| Offline | Backend section state `offline` or the Core request fails by connectivity | 暂时无法连接，请检查网络后重试 | Retry | Preserve loaded data only for this request; no offline cache in this slice. |
| Blocked / permission denied | Current Subject mismatch/missing, HTTP 401/403, or `bound != true` | 经营主体信息暂不可用 | Retry after access/context recovery | No screen aggregate call after a failed Subject gate; no fixture fallback. |
| Error | Invalid response shape, other HTTP error, or backend `ok != true` | 运营信息暂不可用，请稍后重试 | Retry | Generic safe copy; do not display tracebacks or server internals. |
| Local inspect / return | User selects then clears a returned event | Inspecting a signal; return keeps the same stream | Return to signals | No write or source link is implied; selected id stays in view state only. |

## 5. Purpose-built desktop composition

- **Primary question:** what operating changes and risks need attention for this business subject?
- **Hierarchy:** current business context → key operating measures and their honest availability → operating activity → daily key indicators and risk records → source-availability state.
- **Wide desktop (≥1100 logical px of feature content after Shell navigation):** the event stream occupies the main work surface. The selected event inspector, canonical scores and Evidence-lineage status occupy a distinct side region so signal timing remains visible during inspection.
- **Compact desktop/tablet (768–1099 logical px of feature content):** one event work surface; selected-event details appear in a reversible secondary panel below or beside it as space allows.
- **Primary interaction:** focus an event row; show only returned business fields; hide internal references; Return clears focus without changing stream order.
- **Keyboard:** event rows are keyboard-focusable; Enter/Space opens inline inspection, Escape returns to the stream. Focus style is visible.
- **Screen-specific identity:** a vertical time/signal ribbon is the organizing axis. It is not a brand relationship graph, four-card KPI dashboard, or generic section renderer.

## 6. Purpose-built mobile composition

- **Active task:** inspect one business activity item and return to the same activity list.
- **Layout:** ≤767 logical px uses a single vertical task surface. Available metrics are concise rows; NOT_COLLECTED measures are grouped under source availability. Events form a chronological list with one inline focused detail; the risk/summary and blocked Evidence lineage follow the signal task.
- **Navigation / return:** no unverified screen route; Return clears the event focus and preserves list position and business context.
- **Touch:** event rows and retry/return controls have at least 48 logical px interactive height. No write-action sheet is shown while action contracts are blocked.
- **Interruption/offline:** retain no local business cache. If a request fails, show the recovery state and retry control. No pending write is represented.
- **Screen-specific identity:** mobile prioritizes one active signal and keeps source/scope gaps adjacent to it instead of shrinking the desktop side panel.

## 7. Actions, authorization and effects

| Action | Server owner / actor / scope | Permission operation | Effect | Evidence | UI behavior |
| --- | --- | --- | --- | --- | --- |
| Load current runtime identity | SYSTEM runtime route; actor is authenticated only when global Basic auth is configured; actor-to-Subject binding UNKNOWN | Global Basic auth gate when enabled; no route-level `PermissionGate` decision | Read only | Runtime API response; no CTH Evidence | The App sends configured Basic Auth through the shared Core client; do not infer authorization from Subject registry or identity context. |
| Load CTH-01 aggregate | CTH read builder and its DB/Shared Reporting/Evidence callers | Global Basic auth gate when enabled; no fine-grained CTH read operation returned | Read only | DB-derived fields; Evidence query is unscoped | Render only safe, source-mapped fields; isolate or suppress unscoped Evidence. |
| Inspect/return event | Local presentation state only | No server permission call | No persistent or external effect | Returned event fields only; no Evidence lineage established | Enabled as a reversible local selection. |
| Draft brief / select range / export / navigate event / draft plan / notify | Owner/action contract not proven | UNKNOWN (labels in JSON do not prove a server decision) | UNKNOWN; notify is external/high risk | UNKNOWN | No enabled controls or requests. |

## 8. Accessibility, motion and localization

- **Keyboard / focus:** Tab to event rows; Enter/Space selects; Escape returns; show the same Subject and selection in focus order.
- **Semantics:** label event title, date/time, severity text and selection state; hide internal event references. Severity is not color-only. Announce loading, blocked and request errors through a live-region status label.
- **Evidence and charts:** no chart is drawn while its per-day error state is ambiguous. Evidence rows are not shown until Subject lineage is verified; state explanation is screen-reader accessible.
- **Reduced motion:** no authored transition motion in this slice; state changes are immediate.
- **Localization:** current App strings are Chinese. Do not claim English/Korean coverage; returned Subject/event text is data and is not rewritten by locale.

## 9. Executable acceptance

| Acceptance ID | User action / expected result | State/error path | Platform/input | Layer / evidence |
| --- | --- | --- | --- | --- |
| CTH01-W-001 | Load returned CTH current Subject; request `screen('CTH-01')` once; render negative count and real signal fields from API | Verify only backend current Subject is used | Widget; desktop width 1440 | Widget test with contract-shaped test response; production E2E still required. |
| CTH01-W-002 | Return runtime identity with no Subject, non-CTH product or non-CTH domain | Show BLOCKED and do not request screen aggregate | Widget; desktop and mobile | Widget test asserting no screen call. |
| CTH01-W-003 | Render footfall/sales with `value=null,state=notcollected` | Show “尚未采集”, never zero or a raw backend reason | Widget; desktop and mobile | Widget test. Existing API test `tests/test_experience_runtime.py::test_cth01_external_metrics_are_not_collected`. |
| CTH01-W-004 | Select an event, inspect exact returned data, Return | Keep Subject and list position; no fabricated Evidence navigation | Widget; keyboard/touch | Widget test; live route/deep-link remains out of scope. |
| CTH01-W-005 | Return mixed/unverified Evidence records | Do not show records as Subject-linked; show blocked lineage state | Widget | Widget test with source-backed unscoped response. |
| CTH01-W-006 | Return API 401/403, bound=false, malformed JSON or empty event list | Distinguish blocked, error and empty; retry is user-driven | Widget; desktop and mobile | Widget tests; real auth integration/E2E required. |
| CTH01-W-007 | Resize from 1440 to 1024 to 390 logical px | Parallel desktop → compact inspector → single-task mobile composition; no overflow | Widget; pointer, keyboard and touch | Widget layout tests; actual device/runtime E2E remains required. |

## 10. Review decision and open questions

- **Decision:** BLOCKED for full Golden Page acceptance. A partial source-backed read-only implementation may render verified current-Subject metrics, signal fields and deterministic daily values with the limits above.
- **Reviewer:** Codex implementation review against `origin/main` `b4608331eacb868ff13ef74e770aa54c309ebef3`; user-visible state copy avoids architecture and endpoint diagnostics.
- **Open source dependencies:** (1) bind authenticated actor to current CTH Subject and a server-side CTH read decision; (2) add Subject-scoped Evidence query/lineage to this read contract; (3) return per-day trend error/state rather than zero-filling; (4) return a true active-event total or keep count omitted; (5) define action owners, requests, permission results, effects and Trace/Return.
- **Changes required before full acceptance:** resolve those dependencies through existing owners, preserve current database/report/Evidence behavior, add API/integration coverage, and prove real Core auth plus desktop/mobile E2E.
- **Acceptance evidence after implementation:** focused Flutter widget tests, existing Python CTH-01 runtime tests, actual Flutter build/runtime at PC/mobile widths, auth/access-denial acceptance, current-source trace, Evidence scope verification and CTH signal Trace/Return. Flutter 3.47.5 and Dart 3.13.4 are available in the workstation user toolchain.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 查看商业运营活动并检视单个事件。
- **屏幕专属呈现：** Subject/context、运营脉冲、事件流和选中详情组合
- **来源、范围与版本连续性：** 保留scope、时间窗、event ID和来源锚点；下游继承相同范围
- **四端差异：** Web/Desktop流和详情并读；Mobile按脉冲→事件；官网不显示私有运营
- **失败与恢复：** 无权限、空、未采集和错误分开；切主体清除旧数据
- **补充验收：** 事件返回同一位置；不从时间顺序推因果。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。保留序境二维手绘水彩/版画色彩语言与有功能含义的线性控件；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，只借鉴手绘平面笔触与色彩，不复制参考人物、不用3D质感。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
