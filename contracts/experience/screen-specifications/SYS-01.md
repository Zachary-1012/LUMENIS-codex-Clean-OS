# SYS-01 — Runtime health / RuntimeGuardian slice

```yaml
screen_id: SYS-01
status: APPROVED
revision: 2
owner_domain: SYSTEM / RuntimeGuardian
binding_ids:
  - BACKEND-GAP-036
product_owner_approval: APPROVED
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_READY
design_scope: READ_ONLY_RUNTIME_GUARDIAN_SLICE
artifact_disposition: NON_AUTHORITATIVE_EXPLORATION_ONLY
reviewer: Codex source review under Product Owner direction
reviewed_at: 2026-09-20
approval_reference: Product Owner instruction to implement the approved App / UX plan and Experience Constitution §§30–36
```

This specification approves the **read-only RuntimeGuardian health slice**. It does not claim the complete dependency topology or latency series in the SYS-01 blueprint is implemented.

## 1. User problem and product invariant

- Role and authorized context: SYSTEM operator, after the App's current authentication boundary permits the GET request. This page reports infrastructure state only; it does not select a CTH Subject or BMP Brand/Market context.
- User task: understand the RuntimeGuardian overall state, Worker and dead-letter queue counts, reaper/circuit-breaker indicators, and when the health snapshot was sampled.
- Completion signal: current health values and sample timestamp are displayed with their real availability state. This read-only slice has no operation action or state transition.
- Owner/invariant: SYSTEM owns runtime infrastructure. Runtime health is operational state and must never be presented as CTH/BMP business truth.
- Explicitly out of scope: restarting/reloading workers, retrying DLQ items, changing breaker state, latency charts, App→API→database→adapter health claims, and persisted Evidence artifacts.

## 2. Route, entry, exit and return

- Entry: App shell route to SYS-01. Shell/authentication remains the caller boundary.
- Read route: `GET /api/experience/screen/SYS-01`. `experience_runtime.screen_viewmodel()` resolves the propagated builder in `experience_screens.SCREEN_BUILDERS` and returns its JSON envelope.
- Source chain: `experience_screens._build_sys01()` → `runtime_guardian.legacy_health_check()` → `RuntimeGuardian.get_instance("legacy").health_check()`.
- Exit: return to the originating SYSTEM navigation state. There are no drilldown routes verified by this slice.
- Trace/Return: show `runtime_guardian.timestamp`, guardian name and runtime source. The current endpoint has no historical sample/detail route, so it cannot open a prior snapshot. Preserve only the shell's origin route and scroll/focus state.

## 3. Verified data and callable bindings

| Priority | UI field | Current owner | Exact source/ViewModel field or callable | Definition / units / window | Freshness and missing-data behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Overall status | SYSTEM RuntimeGuardian | `truth.overall`; runtime item `总体状态.state/detail` | RuntimeGuardian health classification (`healthy`, `degraded`, etc.) | `truth.overall == null` or status `offline` means unavailable; never map it to healthy | BACKEND-GAP-036 | `runtime_guardian.py::RuntimeGuardian.health_check`; `experience_screens.py::_build_sys01` |
| P0 | Registered Worker count | SYSTEM RuntimeGuardian | KPI id `sys01.workers_total`, from `health_check().workers.total` | Count of workers currently returned by `list_workers()` | Display integer only when state is `ready`; display 0 only when the source returned numeric 0 and state is ready; otherwise unavailable | BACKEND-GAP-036 | `experience_screens.py::_build_sys01`; `tests/test_experience_runtime.py::test_sys01_unavailable_health_counts_are_not_reported_as_zero` |
| P0 | Failed Worker count | SYSTEM RuntimeGuardian | KPI id `sys01.workers_failed`, from `health_check().workers.failed` | Count with `WorkerStatus.FAILED`; not the sum of failed and dead | Same null/ready distinction as above | BACKEND-GAP-036 | Same as above |
| P0 | DLQ count | SYSTEM RuntimeGuardian | KPI id `sys01.dlq`, from `health_check().dlq.total` | RuntimeGuardian DLQ aggregate total | Same null/ready distinction as above | BACKEND-GAP-036 | `_build_sys01`; `runtime_guardian.py::RuntimeGuardian.health_check` |
| P1 | Reaper | SYSTEM RuntimeGuardian | Runtime item `name=reaper`, `state`, `detail`; source `health_check().reaper_running` | Whether this guardian's reaper loop is running | Use only when the health snapshot is complete; if the endpoint normalized missing data to a default, show unavailable rather than false | BACKEND-GAP-036 | `_build_sys01`; `RuntimeGuardian.health_check` |
| P1 | Circuit breaker OPEN / registered counts | SYSTEM RuntimeGuardian | Runtime item `name=熔断器`, `detail=open=N · registered=N`; source `health_check().circuit_breakers` | `open` counts entries whose state is `open`; `registered` is the number of breaker entries returned. | Hide if snapshot is incomplete or the runtime item is offline. | BACKEND-GAP-036 | Current `_build_sys01` filters breaker entries by `state == "open"` and separately returns `len(breakers)` |
| P1 | Guardian identity | SYSTEM RuntimeGuardian | Runtime item `name=guardian`, `detail`; source `health_check().guardian_name` | RuntimeGuardian instance name | `—` or absent is unavailable | BACKEND-GAP-036 | Same source chain |
| P0 | Sample timestamp | SYSTEM RuntimeGuardian | Runtime item `name=时间戳`, `detail`; source `health_check().timestamp` | ISO timestamp returned by the health check, distinct from the screen envelope's `generated_at` | Missing/`—` means sample time unavailable; do not substitute client time | BACKEND-GAP-036 | `RuntimeGuardian.health_check`; `_build_sys01` |
| P0 | Runtime observation trace | SYSTEM RuntimeGuardian binding | `runtime_observation.state/captured_at/trace_id/boundary` | Read-only operational-provenance envelope derived from the same validated health snapshot | Missing or malformed source yields unavailable; never expose guardian name, path-shaped values or internal implementation details | BACKEND-GAP-036 | `_build_sys01`; `tests/test_experience_runtime.py`; SYS-01 Flutter snapshot/view-model/widget tests |

### Exact callable and effect

- `GET /api/experience/screen/SYS-01` has no request body, pagination, cancellation, idempotency key or write effect. The aggregate envelope includes `ok`, `screen`, `source`, `bound`, `sections`, `truth`, `binding` and `generated_at`.
- The current builder returns one `kpis` section containing the three count metrics and one `runtime` section containing overall, reaper, circuit-breaker, guardian and timestamp items.
- `app.py::_basic_auth` may require Basic/session authentication when auth is enabled. The GET route is not in the explicit CTH read-only GET allowlist. The route has no separate SYS-01 action permission check because the page defines no action.
- No Evidence record is emitted by this GET. RuntimeGuardian's timestamp and source name are operational provenance, not a persisted Shared Evidence artifact.
- `runtime_observation` is additive operational provenance only. Its deterministic `sys01rt-...` identifier does not become Canonical Data or Shared Evidence, and `boundary=read_only` authorizes no runtime effect.
- `viewmodel.latency: number[]` and the fixture's dependency uptime / response chart are not backed by this RuntimeGuardian callable. They are excluded and remain unimplemented.

## 4. State and recovery matrix

| State | Trigger/evidence | User-visible meaning | Available actions | Recovery/return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | GET pending | 正在读取系统运行状态 | Wait or leave page | No placeholders or zero counts | SYS01-READ-01 |
| Empty / no source data | Bound response with known zero Worker/DLQ count | The returned source count is exactly zero | Read details | Render zero only for a numeric value whose KPI state is `ready` | SYS01-READ-02 |
| Not collected | Metric is null/notcollected or field missing | Count shows “暂未提供”; unavailable status never appears as 0 | Read other available fields | Keep unavailable distinct from zero | SYS01-READ-03 |
| Fresh | Runtime source timestamp is present | Show the timestamp returned by RuntimeGuardian | Read current snapshot | Do not claim a freshness SLA that is not in the contract | SYS01-READ-04 |
| Stale | No stale threshold is defined | Staleness cannot be classified | Reload only through the normal screen refresh mechanism | Do not infer stale from device clock | SYS01-READ-05 |
| Partial | Some KPI values are ready while others are null/offline, or sample timestamp/overall is absent | Show valid counts and mark affected runtime indicators unavailable | Return or retry GET | Do not interpret normalized `false`, `open=0`, `—` defaults as source facts when the sample is incomplete | SYS01-READ-06 |
| Offline | Network/Socket failure | 系统服务暂不可用；暂时无法读取当前运行状态 | Retry GET | Clear old snapshot; never keep stale values under a live label | SYS01-READ-07 |
| Blocked / permission denied | HTTP 401 or 403 | 401: “需要登录”；403: “当前账号无法查看” | Return to shell authentication/access route; no operation action is offered | Keep 401 and 403 distinct | SYS01-AUTH-01 |
| Error | Non-2xx other than 401/403, malformed JSON, wrong screen id or runtime error | 运行状态暂不可用；系统暂时无法提供有效状态 | Retry GET | Show a bounded error state, no zero values | SYS01-READ-08 |
| Success / persisted | Not applicable: endpoint is read-only | Nothing is persisted by this screen | None | Do not show a success toast or imply a runtime mutation | SYS01-EFFECT-01 |

### App language mapping

| Returned value | App display | Boundary |
| --- | --- | --- |
| `truth.overall`: healthy/ok, degraded, unhealthy/error, missing | 正常、部分异常、异常、暂不可用 | Never infer health from absent fields. |
| Worker total / failed count | 后台进程总数 / 异常后台进程 | These are registered runtime worker records, not business-task counts. |
| DLQ total | 失败队列记录总数 | Show a number only when the current source returns a ready integer. |
| Reaper state | 过期任务回收服务：运行中、已停止或暂不可用 | Do not expose the internal service name. |
| Circuit-breaker counts | 已触发的调用保护 / 已配置的调用保护 | Keep open and registered counts distinct; missing counts display 暂不可用. |
| Runtime guardian instance name | 运行服务状态：已识别 | Do not display internal instance names. |
| Health sample timestamp | 状态检查时间; absent value displays 暂不可用 | Use only the timestamp returned by the health source; do not substitute device time. |

## 5. Purpose-built desktop composition

- Primary question: is the system operating normally, and which counts or protections explain its current state?
- At ≥1100 logical px of feature content after Shell navigation, use a vertical operational spine: overall state and source sample at the top; Worker/DLQ counts in the central inspection plane; reaper and circuit-breaker entry count in a narrow guardrail rail. Keep timestamp and guardian identity in the source rail.
- At 768–1099 logical px of feature content, keep the overall state pinned above the count surface; move guardrail details into a reversible inspector so the primary status remains visible.
- Use status text plus shape/label; never rely on color alone. A number is not colored as healthy unless its source state is ready.
- This composition follows operational dependency and failure inspection. It does not use the product KPI dashboard or prototype line chart.

## 6. Purpose-built mobile composition

- At ≤767 px, use a single fault-priority column: overall health first, then failed background processes and failed-queue records, then total background processes, then reaper/protection details and sample time.
- Unknown/offline indicators remain beside each metric, not collapsed into a generic empty page.
- Keep SYSTEM identity visible while scrolling. No destructive or recovery control is shown.
- Use touch-sized refresh/back controls only when supplied by the existing shell. Return to the same originating navigation location.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read/write/external effect | Idempotency / reversal | Evidence emitted | Confirmation and failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Load SYS-01 health | SYSTEM RuntimeGuardian; request governed by existing app authentication | GET; no SYS-01 operation permission is invoked | Read only | Safe to reload | None; timestamp is runtime telemetry provenance | 401 authentication, 403 access denial, offline and server errors have distinct states |
| Restart/reload/retry | Not implemented in this slice | UNKNOWN/not used | Would mutate runtime/DLQ state | No route or reversal contract verified | UNKNOWN | No corresponding control is rendered |

## 8. Accessibility, motion and localization

- Keyboard focus proceeds from overall state to counts, guardrails, guardian identity and timestamp; all text remains selectable.
- Announce overall state and read failure through semantic labels/live region. Each unavailable count says “暂未提供/当前不可用”, not just a dash or color.
- Counts and breaker-entry count are textual; no chart is needed for this slice.
- Motion is limited to state transitions and can be disabled for reduced-motion preference.
- Chinese/English labels wrap at narrow widths and 200% text size. Do not claim Korean localization until verified.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State/error path | Platform/input | Test layer | Current evidence/reference |
| --- | --- | --- | --- | --- | --- |
| SYS01-READ-01 | Read real SYS-01 envelope and map typed fields only | Loading / ready | All supported widths | Widget + source binding | `experience_runtime.screen_viewmodel`; `_build_sys01` |
| SYS01-READ-02 | A real integer zero remains visible as zero when its state is ready | Empty / zero | All widths | Widget | `tests/test_experience_runtime.py::test_sys01_status_is_not_a_numeric_kpi` |
| SYS01-READ-03 | Null/offline metrics render unavailable and never zero | Not collected / partial | All widths | Widget + API | `test_sys01_unavailable_health_counts_are_not_reported_as_zero` |
| SYS01-READ-04 | Show RuntimeGuardian source sample timestamp without substituting client time | Fresh / time absent | Desktop and phone | Widget | `RuntimeGuardian.health_check().timestamp` |
| SYS01-READ-05 | Do not add latency values or a chart without an owner callable | Unsupported latency | All widths | Snapshot/widget | ViewModel's latency declaration has no verified source |
| SYS01-READ-06 | Incomplete health response masks normalized fallback status/counts | Partial response | All widths | Snapshot/widget | `_build_sys01` normalizes missing data; frontend must fail closed |
| SYS01-READ-07 | Network error clears snapshot and exposes retry | Offline | Phone/desktop | ViewModel/widget | LumenisCoreClient socket exception contract |
| SYS01-AUTH-01 | 401 and 403 show different access states | Authentication / permission denied | All widths | ViewModel/widget | `app.py::_basic_auth` response contract |
| SYS01-READ-08 | Bad shape, wrong screen, and server error do not render health values | Error | All widths | Snapshot/widget | screen envelope validation |
| SYS01-TRACE-01 | A valid live health snapshot displays observation state, capture time, trace ID and read-only boundary; malformed or absent provenance remains unavailable | Ready / partial / error | Desktop and phone | API + snapshot + widget + live desktop | `_build_sys01`; SYS-01 focused tests; ROUND 02 evidence bundle |
| SYS01-RESP-01 | Desktop shows topology + inspector; mobile orders by failure priority | 1440/1024/390 logical px | Pointer/keyboard/touch | Widget + visual review | Constitution §§20, 31 and SYS-01 §36 |

## 10. Review decision and open questions

- Decision: `APPROVED` for this read-only RuntimeGuardian slice. The full SYS-01 dependency topology and latency series remain unimplemented and must not be represented by this page as complete.
- Product owner approval: inherited from the explicit approval of the overall App / UX plan and Experience Constitution §§30–36 on 2026-09-20; this implementation adds no product or recovery action.
- Confirmed binding: BACKEND-GAP-036 maps to `runtime_guardian.legacy_health_check()` through the current SYS-01 screen builder. The old `UNKNOWN`/`CODEX_VERIFY` statements are stale for this read aggregate.
- Remaining source limitations: `latency` has no verified callable; when health is missing, the builder normalizes some guardrail fields to strings such as `running=unknown` and `状态不可用`, without presence flags. The client must mark that group unavailable when the overall sample/timestamp is absent. The breaker detail format is `open=N · registered=N`; the two counts must remain distinct.
- No user approval is needed for read-only display. Do not add restart, retry, DLQ mutation, or breaker controls without an existing owner route and server-side permission contract.
- Acceptance required after implementation: local Flutter widget tests plus the existing isolated SYS-01 backend tests; runtime HTTP verification remains dependent on the current Core session/auth setup.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 读RuntimeGuardian状态和Worker/DLQ保护指标。
- **屏幕专属呈现：** health snapshot按整体→队列→防护解释，采样时间在场
- **来源、范围与版本连续性：** 同一guardian/source/timestamp；业务指标不得混入
- **四端差异：** Web/Desktop状态脊柱；Mobile故障优先；官网不承诺内部健康
- **失败与恢复：** offline/degraded/partial分开；无操作绑定不显示重启
- **补充验收：** 真实采样值和时间一致；旧快照不充当前状态。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。保留序境二维手绘水彩/版画色彩语言与有功能含义的线性控件；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，只借鉴手绘平面笔触与色彩，不复制参考人物、不用3D质感。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
