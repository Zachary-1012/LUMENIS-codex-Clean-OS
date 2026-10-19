# CTH-04 — 事件关系

```yaml
screen_id: CTH-04
status: BLOCKED
revision: 1
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-010
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: NON_AUTHORITATIVE_EXPLORATION_ONLY
reviewer: Codex delegated ROUND-10 bounded source review
reviewed_at: 2026-09-22
approval_reference: source baseline origin/main 5ba1aefc53a1babc293e990c23c62f841724c843; this is not per-screen acceptance
```

## 0. Authority basis and artifact disposition

- The governing experience row is the CTH-04 causal constellation paired with a time axis.
- The current source contract is `experience_screens._build_cth04()` and the shared `GET /api/experience/screen/CTH-04` envelope. The graph field is declared but the current builder returns curated events without verified relationship edges.
- Fixture/action JSON is a contract-gap record, not permission to invent graph edges or effectful actions. The implementation uses a timeline plus an explicit unavailable graph state until canonical edges exist.
- The composition is purpose-built: event timeline and relationship area remain synchronized in hierarchy; it is not a generic card list.
- Sol design decision: `BLOCKED`; no causal claim or Case navigation is accepted in this slice.

## 1. User problem and product invariant

- **User task:** understand the order of returned CTH events and inspect one event without mistaking chronology for causality.
- **Context:** use the same `settingsContext()` gate as CTH-03. `GLOBAL_ALL` is allowed only after a server `global_binding` (or current canonical equivalent) proves the global grant/scope, CTH product/domain, `scope_verified`, `read_allowed` and verified lineage. `FOCUS` is allowed only after `focus_binding.applied` plus exact Subject, CTH product/domain, `scope_verified`, `read_allowed` and verified lineage. Current backend responses without these fields are blocked.
- **Completion signal for this slice:** a returned event timeline can be selected and returned from locally; the relationship surface clearly says when graph edges are not returned.
- **Invariant:** an event row does not establish Evidence, a Case, causality, or actor authorization. `bound=true` is not authorization; unknown relationship and lineage data stays unknown.
- **Out of scope:** new event creation, linking a risk, navigation to a Case, opening Evidence, editing, notification, export and any other effect listed only in action metadata.

## 2. Route, entry, exit and return

- **Entry:** `Cth04Screen(client: ...)` from the existing CTH workspace; no new route/deep-link owner is added.
- **Read sequence:** `settingsContext()` → `screen('CTH-04')`. The current request is unparameterized. Focused data is rejected when the response does not prove an exact authorized focus binding; event rows additionally require explicit scope, read permission, verified Evidence lineage and a trace/evidence reference.
- **Verified response fields:** `events.items[title,date,time,desc,level,tags]`; the current `kpis` may report `cth04.graph` as `null/notcollected`. Internal event/evidence identifiers are dropped.
- **Exit / return:** selecting an event opens an inline inspection panel; `返回事件时间线` clears local selection and restores the timeline. No graph zoom, deep-link or Case position is persisted because no destination contract exists.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source/ViewModel field or callable | Definition / units / window | Freshness and missing-data behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Scope label | SYSTEM context read | `LumenisCoreClient.settingsContext()` | `GLOBAL_ALL` or applied focused CTH scope | Missing/mismatch blocks; IDs hidden | — | Current context contract |
| P1 | Event timeline | CTH read builder | `_build_cth04()` `events.items[title,date,time,desc,level,tags]` | Returned event fields; no total or causal score | Empty, not collected, offline and error remain distinct; rows without matching scope/lineage/trace are withheld | BACKEND-GAP-010 | Current source mapping; lineage pending |
| BLOCKED | Relationship constellation | CTH canonical event/Evidence relationship owner UNKNOWN | ViewModel `graph.nodes[]/edges[]`; current builder does not supply verified edges | No causal direction, case link or evidence anchor can be computed locally | Show graph unavailable; never derive edges from list order | BACKEND-GAP-010 | Current source says requested graph edges are not supplied |
| BLOCKED | Event → Evidence / Case trace | CTH/Evidence/Case owners unresolved | Action registry labels `to-case`, `link-risk`, but no verified App callback/request/result | UNKNOWN | No enabled action or raw identifier | BACKEND-GAP-010 | Permission/effect/Trace pending |

No new data owner is created. The App renders only the shared Core response, and no fixture is used as runtime fallback.

## 4. State and recovery matrix

| State | Trigger/evidence | User-visible meaning | Available actions | Recovery/return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Context/event request pending | 正在加载事件关系 | None | Announce; keep event details hidden | CTH04-W-001 |
| Empty / no events | `events.state=empty`, no items | 当前范围内暂无已返回事件 | Refresh | Keep graph unavailable separate from empty timeline | CTH04-W-002 |
| Not collected | Graph KPI/section is `notcollected` | 事件关系尚未返回 | None | Show timeline only; do not infer relations | CTH04-W-003 |
| Fresh / stale | No source timestamp/state contract | UNKNOWN | None | Do not label events live or stale | CTH04-W-004 |
| Partial | Timeline exists, graph missing | 事件时间线可用，关系信息暂缺 | Refresh | Selection/return remains local | CTH04-W-002 |
| Offline | Core/section `offline` | 暂时无法连接 | Retry | Never present the previous response as a new result | CTH04-W-005 |
| Blocked / permission denied | Invalid scope, `bound=false`, missing global grant/binding, or focused response without exact authorized binding; 401/403 | 经营主体信息暂不可用 | Retry after recovery | Do not fetch or reuse unscoped focused data; never display an untraceable event | CTH04-W-006 |
| Error | Malformed response or 5xx | 运营信息暂不可用 | Retry | Hide server details | CTH04-W-005 |
| Local inspect / return | User selects or clears an event | Inspecting one returned event | Return | Restore the same timeline; no server effect | CTH04-W-007 |

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-04)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- **Primary question:** what events were returned, in what order, and what relationship information is actually available?
- **Hierarchy:** scope → relationship availability → constellation area → synchronized event timeline. The relationship area is not allowed to visually imply edges when none are returned.
- **Wide desktop:** `cth04/desktop-layout` gives the constellation a stable region and the timeline a full-height companion region. The selected event inspector replaces only the local detail region and leaves the timeline visible.
- **Keyboard:** timeline rows are focusable; Enter/Space selects; Escape or Return clears selection. Graph unavailable status is announced and text-readable.
- **Screen identity:** a time axis plus explicit relationship gap differentiates this page from a generic event table.

## 5A. Web Workspace composition and desktop-only capability boundary

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-04)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- Web and desktop share the same read contract, local selection state and blocked relationship semantics. No browser-only graph library or second data source is introduced.
- Case navigation, Evidence opening and graph zoom are unavailable until canonical destination and lineage contracts are bound.
- A production claim requires runtime acceptance at desktop and browser widths; widget tests do not promote this spec.

## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-04)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- **Active task:** scan the vertical event path, open one returned event, then return to the path.
- **Touch:** event rows and Return are at least 48 logical pixels; event severity and tags are textual.
- **Interruption:** no pending write or local business cache is represented. Retry restarts the read gate.
- **Screen identity:** the event path is primary and causal edges are visibly withheld when unbound.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read/write/external effect | Idempotency / reversal | Evidence emitted | Confirmation and failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Load context/events | SYSTEM context + CTH event read | Optional global auth; screen-level Subject read UNKNOWN | Read only | Repeatable | Returned event fields only | Safe ready/empty/blocked/error copy |
| Select/return event | Flutter local state | None | No server effect | Immediately reversible | None | Enabled; preserve timeline |
| New event / to Case / link risk / open source | Action registry labels only; callable owner and destination UNKNOWN | UNKNOWN | Potential write/navigation/external effect | UNKNOWN | UNKNOWN | No controls or requests |

## 8. Accessibility, motion and localization

- Focus order is scope → relationship state → timeline items → selected details → Return. The selected row and Return target are announced.
- A graph, when later bound, must have a synchronized table/list equivalent; the current page uses text explaining unavailable edges and never relies on edge color alone.
- Loading, empty, blocked and error states are live regions. Severity and tags have spoken text.
- No authored motion is required; reduced motion has identical semantics.
- The bounded UI uses existing `screen.CTH-04`, context, common, state and `cth01.*` keys; no hardcoded screen copy remains. Canonical l10n must add `cth04.relationship_unavailable`, `cth04.event_detail`, `cth04.return_timeline`, `cth04.action_unavailable` and state copy in zh-CN/en/ko before acceptance, then replace the temporary generic mappings. No second localization owner is permitted.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State/error path | Platform/input | Test layer | Current evidence/reference |
| --- | --- | --- | --- | --- | --- |
| CTH04-W-001 | Pending request shows loading and no event fields | Loading | Widget | `app/test/features/cth/cth04/cth04_screen_test.dart` | Local evidence |
| CTH04-W-002 | Empty events remain empty; graph absence is separately explained | Empty/partial | Widget | Widget test | Current builder-shaped response |
| CTH04-W-003 | Graph `notcollected` never becomes a causal edge | Not collected | Widget | Widget test | Current graph gap |
| CTH04-W-004 | No freshness/cause claim is inferred from response generation time or list order | Unknown freshness | API/widget | Contract test required | Current source lacks fields |
| CTH04-W-005 | 5xx/malformed/offline state hides raw details and supports retry | Error/offline | Widget | Widget test | Safe copy implemented |
| CTH04-W-006 | Focused context without applied binding is blocked | Focus scope | Repository/widget | Repository test | Current runtime focus gap |
| CTH04-W-007 | Select and Return preserves event timeline and does not call a write action | Local Trace/Return | Widget; keyboard/touch | Widget test | Local implementation evidence |
| CTH04-W-008 | Resize 1440 → 390 without overflow and with spoken event labels | Responsive/accessibility | Widget + runtime E2E | Widget now; runtime pending | Desktop/mobile composition implemented |
| CTH04-W-009 | Return `bound=true` without global grant/lineage; the repository blocks instead of decoding the global event list | Global authorization/lineage block | Repository/widget | Repository test | Implemented hostile fixture |
| CTH04-W-010 | Return authorized `GLOBAL_ALL` and exact focused Subject fixtures; only authorized events are decoded | Authorized global/focus read | Repository | Repository test | Implemented legal global fixture; live backend binding pending |

## 10. Review decision and open questions

- **Decision:** `BLOCKED` for causal graph, source/Evidence trace, Case navigation and ROUND-10 acceptance. The bounded implementation is a read-only timeline with an honest graph gap.
- **Open owners:** CTH must define canonical relationship edges; Evidence must provide lineage; Case/action owners must define request, Permission, effect, confirmation and Trace/Return; SYSTEM must bind Subject scope; l10n must add the three locales.
- **Required before acceptance:** at least one real new event with lineage, verified relation edges or an explicit accepted no-edge state, focus binding, and real desktop/mobile E2E.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 理解事件先后和证实的关系边而不推因果。
- **屏幕专属呈现：** 实际时间轴与有证关系图切换；选节点看原来源
- **来源、范围与版本连续性：** 保留事件ID、源时间/capture time、relation version
- **四端差异：** Web/Desktop时间轴/关系图；Mobile按时间下钻；官网无内部事件图
- **失败与恢复：** 部分返回标partial；缺证据不画边；scope切换清旧图
- **补充验收：** 节点回源且返回定位准确；不做因果或写入动作。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。

### 原G117/G118具体终态合同：事件簇、观点对象与主张证据

事件面先簇清单/时间窗，再选中簇的代表原句、派生摘要和成员原帖；代表句可回准确原文，摘要只覆盖真实成员。增量新增成员带来源/时间，旧簇版本可比较，不把聚类相近自动画成因果边。观点详情先选择其实际对象/活动和被评价主张，原话、系统立场推断、支持证据和人工结论分栏；局部活动不外推品牌整体，Target/Claim用人可读对象/句子而非内部ID。

构图：CTH-04左簇列表、中代表句/成员、右原帖；CTH-06在现queue→reader中增加对象/主张抬头与三分区。移动簇→成员→原文，返回保簇/窗口；未绑定关系只显示已存在层。

无成员/代表句缺失、低置信未知、重复/冲突来源、语言不支持、源撤回分开。改窗口新分析，人工纠正形成版本，不覆盖原话；取消保选中和原稿，重开同簇/主张版本，不能因显示关系就创建Case。

Public Website仅用获准真实样例说明事件簇、观点对象与主张证据及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按簇结构与观点冲突建议比较布局，保成员表/原文等价，不能虚构因果或替用户定真假。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。
