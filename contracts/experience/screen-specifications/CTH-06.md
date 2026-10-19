# CTH-06 — 负面监测与反馈

```yaml
screen_id: CTH-06
status: BLOCKED
revision: 1
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-012
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: NON_AUTHORITATIVE_EXPLORATION_ONLY
reviewer: Codex delegated ROUND-10 bounded source review
reviewed_at: 2026-09-22
approval_reference: source baseline origin/main 5ba1aefc53a1babc293e990c23c62f841724c843; this is not per-screen acceptance
```

## 0. Authority basis and artifact disposition

- The governing experience row is the CTH-06 triage queue that distinguishes public opinion, customer feedback and confirmed incidents, with a source-first reader.
- The current source is `experience_screens._build_cth06()` through `GET /api/experience/screen/CTH-06`. It supplies the current negative/high-risk note table, but the declared feedback API, category semantics and per-item lineage are not fully bound.
- Fixture rows, `note_id` values and action JSON are non-authoritative evidence. A row identifier is not a Case or Evidence link.
- This composition is queue → reading pane → source availability, not a generic table and detail card.
- Sol design decision: `BLOCKED`; the slice is read-only and does not classify, link or mutate records.

## 1. User problem and product invariant

- **User task:** triage returned negative feedback, understand whether it is public opinion, customer feedback, a confirmed incident or not yet classified, and read the returned wording without losing queue context.
- **Context:** `GLOBAL_ALL` uses the returned global list only after a server `global_binding` (or current canonical equivalent) proves global grant/scope, CTH product/domain, `scope_verified`, `read_allowed` and verified lineage. A focused CTH context additionally requires an applied focus binding, exact Subject equality, CTH product/domain, `scope_verified`, `read_allowed` and verified lineage; otherwise it is blocked.
- **Completion signal for this slice:** returned rows are grouped by category when the response supplies a category; missing category stays `待分类反馈`, and the reading pane shows returned business fields only.
- **Invariant:** category labels do not create an incident or Case. Original source wording and lineage must remain distinguishable from derived classification. `bound=true` alone never authorizes a global list.
- **Out of scope:** classifying a row on the server, linking a Case, opening an original source, editing wording, resolving an incident, exporting and external notification.

## 2. Route, entry, exit and return

- **Entry:** `Cth06Screen(client: ...)` from the existing CTH workspace; no route or secondary repository is introduced.
- **Read sequence:** `settingsContext()` → `screen('CTH-06')`; current response fields are `table.state` and rows `time/date`, `title/summary`, `platform/channel`, `sentiment`, `risk`, and optional `category/cluster/kind`.
- **Scope gate:** `bound == true` is only route wiring. The adapter requires the authorized server global/focus binding first; each displayed row also requires explicit matching scope, read permission, verified Evidence lineage and a trace/evidence reference. No local Permission or lineage default is created.
- **Exit / return:** category filter and selected reading item are local. Clearing selection returns to the queue; no source deep-link or write action is attempted.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source/ViewModel field or callable | Definition / units / window | Freshness and missing-data behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Scope label | SYSTEM context read | `LumenisCoreClient.settingsContext()` | `GLOBAL_ALL` or applied CTH focus | Invalid/missing scope blocks; IDs hidden | — | Current context contract |
| P1 | Feedback queue | CTH note read builder | `_build_cth06()` `table.rows[time/date,title/summary,platform/channel,sentiment,risk]` | Returned negative/high-risk records; no total claim | Explicit empty stays empty; rows without matching scope/lineage/trace are withheld; source read failure is not empty | BACKEND-GAP-012 | Current source mapping; lineage pending |
| P1 | Triage category | CTH classification owner UNKNOWN | Optional row `category`, `cluster` or `kind` parsed to public opinion/customer feedback/confirmed incident/unclassified | Missing category is `待分类反馈`; it is not an incident | No category mutation; no inferred category from risk alone | BACKEND-GAP-012 | Current row shape only partially matches declared ViewModel |
| P1 | Reading pane | CTH source/Evidence owner UNKNOWN | Selected returned business fields from the same row | Preserve returned wording; no source claim without a bound origin | Show source unavailable copy; hide note IDs and internal fields | BACKEND-GAP-012 | Per-item lineage and source reader pending |

The adapter does not rename notes into Cases, does not call a negative-comments API directly and does not create a parallel feedback store.

## 4. State and recovery matrix

| State | Trigger/evidence | User-visible meaning | Available actions | Recovery/return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Context/table request pending | 正在加载负面反馈 | None | Announce; hide queue details | CTH06-W-001 |
| Empty / no feedback | `table.state=empty`, no rows | 当前范围内暂无负面反馈 | Refresh | Do not show a blank reading pane as success | CTH06-W-002 |
| Not collected | Table/source says not collected | 负面反馈尚未采集 | None | Keep distinct from empty | CTH06-W-003 |
| Fresh / stale | No source freshness contract | UNKNOWN | None | Do not label feedback live/latest | CTH06-W-004 |
| Partial | Rows exist but category/source detail is absent | 反馈可查看，分类或出处暂缺 | Refresh | Keep returned wording and name missing fields | CTH06-W-005 |
| Offline | Core/source failure | 暂时无法连接 | Retry | No stale success or invented row | CTH06-W-006 |
| Blocked / permission denied | Invalid scope, `bound=false`, missing global grant/binding, or focused response without exact authorized binding; 401/403 | 经营主体信息暂不可用 | Retry after recovery | No global fallback for a focused scope; no untraceable row is shown | CTH06-W-007 |
| Error | Malformed response/5xx | 运营信息暂不可用 | Retry | Hide raw details | CTH06-W-006 |
| Local reading/return | Select or clear a row/category filter | 阅读当前返回的反馈 | Return/clear filter | Restore queue and selected category locally | CTH06-W-008 |

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-06)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- **Primary question:** which returned negative voices need reading, and what is known versus still unclassified?
- **Hierarchy:** scope → triage filters → dense queue → source-first reading pane. Category chips explain returned classification state; they do not submit classification.
- **Wide desktop:** `cth06/desktop-layout` keeps the queue mounted beside the reading pane. Selecting a row opens its returned date, channel, sentiment, risk and summary without showing internal IDs.
- **Keyboard:** category controls and queue rows are focusable; Enter/Space applies/selects; Escape or Return clears the reading item. Category meaning is textual.
- **Screen identity:** triage queue plus source-availability reading pane distinguishes this from CTH-03 monitoring and CTH-04 events.

## 5A. Web Workspace composition and desktop-only capability boundary

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-06)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- Web and desktop share the same read-only queue model and local selection. No browser-only source automation is introduced.
- Source opening, classification, Case linking and export remain unavailable until their canonical owners provide scope, Permission, effect and Trace contracts.
- Runtime acceptance must verify a real row and keyboard reading flow; widget fixtures alone are insufficient.

## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-06)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- **Active task:** filter the returned feedback, open one item, read its wording and return to the queue.
- **Layout:** filters → stacked queue items → full-width reading pane. The category state remains visible when the reading pane is open.
- **Touch:** filter chips, rows and Return have at least 48 logical pixels. Risk and sentiment are not color-only.
- **Interruption:** retry restarts the context and table read; no local mutation or offline cache is represented.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read/write/external effect | Idempotency / reversal | Evidence emitted | Confirmation and failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Load context/feedback | SYSTEM + CTH read builder; actor/Subject binding UNKNOWN | Optional global auth; screen READ UNKNOWN | Read only | Repeatable | Returned row only | Safe state copy |
| Filter/select/return | Flutter local state | None | No server effect | Reversible | None | Enabled |
| Classify / link Case / open original source | CTH classification, Case and Evidence owners UNKNOWN | UNKNOWN | Potential write/navigation | UNKNOWN | UNKNOWN | No enabled controls |

## 8. Accessibility, motion and localization

- Queue rows announce summary, date, channel, sentiment, risk and category; internal IDs are not in the accessible tree.
- A source-first reader must have a linear text equivalent. The current source gap is announced as a message, not represented by an empty link.
- Loading, empty, unavailable and error statuses use live regions; category and risk have text labels.
- No authored motion is required; reduced motion keeps the same queue/reader relationship.
- The bounded UI uses existing `screen.CTH-06`, context, common, state and `cth01.*` keys; no hardcoded screen copy remains. Canonical l10n must add `cth06.category_filter`, `cth06.unclassified`, `cth06.source_unavailable`, `cth06.reading_return`, `cth06.action_unavailable` and state copy in zh-CN/en/ko before acceptance, then replace the temporary generic mappings. No second l10n owner.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State/error path | Platform/input | Test layer | Current evidence/reference |
| --- | --- | --- | --- | --- | --- |
| CTH06-W-001 | Pending response keeps feedback hidden and announces loading | Loading | Widget | `app/test/features/cth/cth06/cth06_screen_test.dart` | Local evidence |
| CTH06-W-002 | Empty table does not create a reading item | Empty | Widget | Widget test | Local evidence |
| CTH06-W-003 | Not-collected table remains distinct | Not collected | Widget/repository | Contract test required | Parser preserves state |
| CTH06-W-004 | No latest/live claim is inferred without source freshness | Unknown freshness | API/widget | Contract test required | Current source gap |
| CTH06-W-005 | Missing category/source detail stays visibly incomplete and no action button appears | Partial | Widget | Widget test | Local evidence |
| CTH06-W-006 | Offline/error hides raw server detail and offers retry | Offline/error | Widget | Widget test required | Safe copy implemented |
| CTH06-W-007 | Focused unbound context is blocked | Focus scope | Repository/widget | Repository test required | Current focus gap |
| CTH06-W-008 | Filter and read one item, then return without write/effect | Local Trace/Return | Widget; keyboard/touch | Widget test | Local evidence |
| CTH06-W-009 | A real new negative record preserves source wording and lineage into the reader | Real user work | Runtime/E2E | Required before ROUND-10 PASS | Not yet run |
| CTH06-W-010 | Return `bound=true` with rows but no global grant/lineage; the repository blocks before exposing feedback | Global authorization/lineage block | Repository/widget | Repository test | Implemented hostile fixture |
| CTH06-W-011 | Return an authorized `GLOBAL_ALL` fixture; only rows with explicit global scope and trace are decoded | Authorized global read | Repository | Repository test | Implemented legal fixture; live source binding pending |

## 10. Review decision and open questions

- **Decision:** `BLOCKED` for source-first lineage, classification actions and ROUND-10 acceptance. The bounded implementation provides a read-only triage queue with explicit gaps.
- **Open owners:** Evidence/source owner must bind original records; CTH/Case owner must define classification/link operations; SYSTEM must bind Subject authorization; canonical l10n must add three locales.
- **Required before acceptance:** real new negative feedback, preserved source wording and lineage, category semantics, focused binding, action Permission/effect/Trace, and desktop/mobile E2E.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 分拣反馈并读原始措辞。
- **屏幕专属呈现：** triage队列加原文Reader；派生类别可编辑且不等于事故/Case
- **来源、范围与版本连续性：** 保留原文、平台时间、Evidence、scope及人工/AI分类版本
- **四端差异：** Web/Desktop队列与原文并读；Mobile逐条打开再回队列；官网不呈私密反馈
- **失败与恢复：** 未分类保持待分类；撤源标需复核，不删原文
- **补充验收：** 分类与原文可分别核对；无Case receipt不称已建Case。

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
