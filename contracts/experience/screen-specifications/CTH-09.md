# CTH-09 — 风险与决策工作台

```yaml
screen_id: CTH-09
status: BLOCKED
revision: 1
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-015
  - BACKEND-GAP-016
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
artifact_disposition: BOUNDED_BLOCKED_STATE_IMPLEMENTATION_ONLY
reviewer: Codex bounded ROUND-11 Luna batch
reviewed_at: 2026-09-22
approval_reference: Product Owner approval of App / Experience Constitution §§30–36; this is not CTH-09 acceptance
```

## 1. User problem and product invariant

- **Role / context:** CTH operator working in `GLOBAL / ALL` or an authorized focused CTH Subject.
- **User task:** inspect the basis of a risk, review a separate decision ledger, and understand whether an action is merely proposed, awaiting approval or actually executable.
- **Completion signal for this bounded slice:** show risk and decision rows only when the response proves actor/context scope and trusted references. No control may execute a decision in this batch.
- **Invariant:** risk, insight, decision and action remain distinct. Severity is never conveyed by color alone, and a static action declaration is not authorization.
- **Current limitation:** the current screen builder returns risk notes with `NOTE:<id>` references and has no Decision record, write callable or actor-to-Subject Permission decision.

## 2. Route, entry and return

- **Entry:** nested CTH decision workflow from a Case or the CTH work surface. The shared route is outside this bounded path.
- **Required read binding:** the context contract must be valid and the screen response must include `binding.actor_scope=verified`, matching `context_mode`, `domain=CTH`, and `evidence_lineage=verified`. Focus mode must echo `subject_id`.
- **Exit / Trace / Return:** selecting a risk or decision is local state. Return restores the risk feed and selected row; no context switch or external effect is made.

## 3. Verified data and callable bindings

| Priority | UI field / action | Source / callable | Definition and missing behavior | Binding |
| --- | --- | --- | --- | --- |
| P0 | Risk register | CTH risk owner | Requires `risks[]`, stable risk ID, level, score when actually returned, description and trusted `evidence[]` | `BACKEND-GAP-015`, currently not scope/lineage safe |
| P0 | Decision ledger | CTH Decision owner | Requires `decisions[]`, owner/status, requested action and explicit action contract state | `BACKEND-GAP-016`: existing BusinessDecisionWorkflow and Flutter reader; decision action composition and live acceptance unverified |
| P1 | Source trail | Canonical Evidence owner | Only allowlisted IDs are displayed; `NOTE:<id>` is not Evidence | Current response cannot satisfy this |
| EFFECT | Confirm action | Permission + approval + Effect Fence + real result contract | Disabled unless all exact gates and a callable are present; this UI has no mutation client | Not bound |

Trusted CTH-09 fixture IDs are `EV-7710`, `EV-7699` and `EV-7712` (not a single-subject scope). Unknown or `NOTE:` references are withheld.

## 4. State and recovery matrix

| State | Trigger | User-visible meaning | Available action | Acceptance |
| --- | --- | --- | --- | --- |
| Loading | Read pending | 正在读取风险与决策 | None | CTH09-W-001 |
| Empty | Bound response contains no risk or decision rows | 当前范围内暂无待处理风险或决策。 | Refresh | CTH09-W-002 |
| Not collected | Risk/decision section absent | 风险或决策资料尚未接入。 | Refresh | CTH09-W-003 |
| Partial | Risk is present but some basis/action lineage is missing | 部分资料尚未完成核验，未核验依据不显示。 | Inspect safe rows; retry | CTH09-W-004 |
| Blocked | Scope, lineage or decision owner missing; 401/403 | 当前范围暂不能查看风险与决策。 | Retry; return | CTH09-W-005 |
| Offline / Error | Transport or malformed response | 暂时无法读取风险与决策，请稍后重试。 | Retry | CTH09-W-006 |
| Ready | Bound risk/decision payload | Show matrix/feed, ledger and selected basis | Local selection only | CTH09-W-007 |

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-09)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-09)。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：经营决策结果与依据（区间/缺失）


**4. State additions**
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

**9. Executable acceptance**
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 适用数学方法由后端按假设选择，保留来源、分母与可复现版本；用户收到经营成果，不需要选择论文或内部参数。

算法在后端执行；用户看到业务指标、来源、适用区间与局限。图中数值、置信度及样本阈值仅为布局示例，不是默认值或通用阈值；不满足实际假设时不出虚构区间，不要求用户选论文或模型。

### Existing contract — Purpose-built composition

- **Desktop/Web:** a ranked risk register with score tracks and text severity on the left; a separate decision ledger with owner/status/effect readiness on the right; a selected-basis inspector below or beside them. This is not the CTH-08 case board.
- **Mobile:** a ranked risk feed, selected risk basis, then decision ledger. Each disabled action states why it cannot be executed.
- **Accessibility:** level, score and status are included in semantics; critical/high/medium/low text is always present; selection uses keyboard and touch; blocking/error states are live regions.



### 三语状态文案

| Key | zh-CN | en | ko |
|---|---|---|---|
| loading | 加载中 | Loading | 불러오는 중 |
| missing | 数据缺失 | Data unavailable | 데이터 없음 |
| unavailable | 暂不可用 | Currently unavailable | 현재 사용할 수 없음 |
| denied | 无权执行此操作 | This action is not permitted | 이 작업 권한이 없습니다 |
| retry | 重试 | Retry | 다시 시도 |
| cancel | 取消 | Cancel | 취소 |
| save | 保存 | Save | 저장 |
| revise | 修订 | Revise | 수정 |
| reopen | 重新打开 | Reopen | 다시 열기 |
| recover | 恢复 | Recover | 복구 |
| return | 返回原任务 | Return to task | 원래 작업으로 돌아가기 |

全部新增标签、说明、确认及读屏名称须沿现有三语键实现；上表仅通用状态，不证明全产品翻译/运行完成。逐屏验收覆盖 zh-CN/en/ko、200%字号、键盘/读屏和减少动态。

## 5A. Web Workspace composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-09)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：经营决策结果与依据（区间/缺失）

Web Workspace composition
Web：以经营结论和下一步为主，来源/方法分层展开；键盘可比较方案与修订业务约束，保存后刷新读回同一决策版本，不自动执行行动。

## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-09)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：经营决策结果与依据（区间/缺失）

Purpose-built mobile composition
业务结果为首屏，依据分层展开；触控、字号放大与任务返回可用，保存后可重开版本。

### Existing contract — Actions, authorization and effects

| Action | Required proof | UI behavior |
| --- | --- | --- |
| Inspect basis | Bound read response and trusted reference | Enabled as local selection only |
| Record decision | Exact CTH Decision write callable, Permission decision, approval when required, Effect Fence admission and result contract | Disabled; no request is issued |
| Execute proposed action | Matching actor/domain/Subject scope, `PermissionResult.verification_state=verified`, approval token where required, staged/idempotent effect and observable result | Disabled; no optimistic success |

HTTP 200, `VERIFIED_AVAILABLE` in a JSON registry, a risk score or a button label is not authorization or effect success.

## 7. Executable acceptance

| Acceptance ID | Action / expected result | State path | Platform/input | Test layer |
| --- | --- | --- | --- | --- |
| CTH09-W-001 | Pending read hides risk/decision rows and announces loading | Loading | All widths | Widget |
| CTH09-W-002 | Bound empty response stays empty and does not use the fixture | Empty | Desktop/mobile | Widget |
| CTH09-W-003 | Missing Decision section is not-collected and no action control appears enabled | Not collected | All widths | Widget |
| CTH09-W-004 | Unknown/NOTE evidence and hostile fields are omitted | Partial / hostile input | All widths | Widget |
| CTH09-W-005 | Missing binding blocks the screen; every write/action control is disabled | Blocked | Desktop/mobile | Widget + repository |
| CTH09-W-006 | 401/403/offline/malformed response hides server detail and offers retry | Error | Desktop/mobile | Widget |
| CTH09-W-007 | Matrix/ledger desktop, tablet and mobile feed compositions recompose without overflow; Trace/Return preserves selection | Ready | 1440 / 900 / 390 logical px | Widget |

## 8. Review decision and open dependencies

- **Decision:** BLOCKED for full CTH-09 acceptance. The bounded implementation is read-only and fail-closed.
- **Required before DESIGN_READY / ACCEPTED:** canonical Decision owner and API, actor-to-Subject read/write Permission, approval token flow, Effect Fence/effect result contract, item-level Evidence lineage and runtime/E2E evidence.
- **Current disposition:** current risk notes and static action declarations cannot be shown as an authorized decision loop.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 区分风险依据、决策状态、审批和实际动作。
- **屏幕专属呈现：** 风险、Decision ledger、Action receipt分区显示提案到执行状态
- **来源、范围与版本连续性：** 沿用已有Actor/scope/approval/effect ID，不为风险创建平行任务
- **四端差异：** Web/Desktop并列风险与账本；Mobile先状态再依据；官网不露内部审批
- **失败与恢复：** 未经批准无执行控制；effect UNKNOWN禁止重试并保留上下文
- **补充验收：** 服务端状态一致；真实Outcome/Evaluation才能称闭环完成。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。


## 2026-10-18 全项前端细化：本屏实际工作构图（待本地构建验收）

原frontmatter与真实绑定状态保持；下列完整终态不得缩成现有只读API，也不得以未接通按钮冒运行证据。仅使用服务端已准入字段/当前许可，具体接口沿本屏上文，所有新交互由本地原Owner接线。

### 研究采用、业务决策与实际复盘

研究结果“采用到当前业务”先显示目标CTH主体或BMP品牌聚焦、原Shared来源/版本、当前可用权益与将创建的领域资料；资料权利确认只在实际跨用途/范围动作发生时要求，普通导入不附加通用权利表。缺目标范围时回现有范围选择，不能临时伪造主体。确认关闭回原Shared段落，批准导入与B业务方案采用为独立步骤，各自有真实读回。
业务页宽屏左侧原研究依据，主区方案逐项比较（资源/约束/预期结果与未知并列），右侧当前决策与行动阶段。内部选择主按钮写“采用此方案”，不写“已经执行”；实际Action回执在独立阶段条，已有Task/Word/Artifact以可打开成果呈现。结果区分来源声称、实际产物、未知业务结果；评价区用当前真实口径，不把预计营收/任务完成换成增长。
复盘入口仅在真实结果记录后出现：useful/not_useful/inconclusive用“有帮助/无帮助/暂不能判断”，观察为主文本、1–8条限制和下一步保留/修订/停止依次填写，来源选择只列当前已绑定材料。取消只保草稿；保存反馈显示版本和OPERATOR_FEEDBACK性质，不显示自动因果结论。取消工作后的“恢复记录”确认说明不启动行动。复核/来源变更时页顶固定提示旧批准失效，对照新旧依据并显式重新采用；单点重试不得复活旧批准。
Web保研究→业务→结果深链与原Shared返回锚点；Desktop并读方案/来源并从真实产物打开，关闭应用后按原work revision恢复；iOS先方案摘要与约束→对照→确认→行动/结果，不合成一个“完成”绿勾。官网以去敏真实流程说明从研究到决策，不演示未发生的外部投放或增长。
界面AIGC可按目标建议比较列和结果解释顺序，金额、单位、未知、引用与审批控件仍固定真实数据；用户锁定的方案列/人工观察不被重写。价值是看清选择依据、执行证据和效果未知，必要时能修正而不丢历史。
生成式界面根据目标与真实比较字段提议原创方案对照和分阶段成果揭示，未执行区保空态文本而非庆祝动画；不同业务问题可用不同原生表/局部图解/证据阅读构成。用户冻结当前比较列，任何重新构图不改变已选择方案、金额、批准或结果。


### 全项具体工作合同：路径归因与有限对照

保留原评价Owner与只读投影状态；真实新动作未接线时OPEN。新增任务专属合同：path贡献的非因果限定；DID干预点、设计声明/前趋势结果；合成控制供体及分期/权重/留出误差。校验同期间/单位、同版本来源，明确改变输入会使旧建议失效。验收重复路径、未知身份、干预前不足、溢出假设未满足、供体排除后不可行、取消/断线/旧回调，不能只验一条READY。

BMP-09中央为同时间轴处理/对照或真实路径矩阵，右侧“比较依据”固定干预时点、分母、窗口和假设。合成控制按需打开供体抽屉，前/后期用文字与竖线标界，贡献条与权重表同源；缺区间不画置信带。Desktop/Web并读，iOS先结论/限制→可选供体→同源表；官网带方法边界。UI适配按问题切路径/前后对照，不合成缺失边或供体；保用户钉住对象，可恢复稳定平面表。

具体操作与恢复：效果比较先由用户声明“比较观测路径/比较干预前后”及业务对象。路径归因展示已观察路径、转化定义/窗口、重复/未知身份情况，再列各渠道的描述性信用与移除假设；Markov/Shapley不等因果增量。DID展示处理/对照两序列、干预时点、前趋势容忍及设计假设，前趋势检查和效应估计分区。合成控制显示供体列表、可纳入/排除及理由、前期拟合/留出段、干预后比较、供体权重与敏感性；用户排除供体只形成新分析，不篡改原观察。设计不足只交观测对比，不能靠勾选假设升级因果。
待补数据、前期检验失败、供体不足/拟合不佳、超出有限通道上限、计算失败与完成分开；取消保原选择、恢复先读原任务和准确输入版。用户可看到为什么能比较、哪些解释仍不成立。


### 全项具体工作合同：多准则、组合、排期及人员配置

新增业务可编辑字段及Owner结果映射，不暴露任意JSON、内部算法参数或论文选择器。状态至少：需补单位/币种、判断不一致、不可行约束、预算/时限耗尽、已有可行但未证最优、完整枚举失败、计划待采用、保存冲突。采用计划/配置只保存Decision/Brief，联系/采购/发布另获原授权。验收预算变动、必选与互斥冲突、资源重叠、未知覆盖不求和、等数/规模限制、无可行配置、取消后重开、旧计算晚到不盖新约束。

CTH-09上部目标与约束，中部方案同字段并列，右侧取舍解释；不一致判断行就地高亮并有文字。BMP-05候选列表旁固定预算/覆盖，选中组合与备选在同一比较层。BMP-07排期条上方资源/时窗，底部冲突清单可定位，拖拽另有起止时间键盘输入。人员配置为“人×岗位”可勾选矩阵＋完整方案清单，iOS逐人选择岗位并审阅冲突，不缩小矩阵。Web/Desktop可并读；官网真实例；iOS只开已支持约束编辑/方案审阅，复杂排期续接同版本。UI适配按目标提出取舍表、预算组合或资源排期视图，不改变权重/资格/约束，锁定比较维度与选中项。

具体操作与恢复：方案比较有三种已有业务输入面。取舍比较：逐项编辑指标值/单位、越高越好或成本方向及“更看重哪项”的成对判断，显示权重、判断不一致位置与排序敏感性；不要求用户操作AHP/TOPSIS名词。创作者组合：预算、每项真实成本、声明效益单位、必须覆盖、候选纳入/排除并读，显示选中组合/替代与未满足约束；效益相加假设不冒独立触达。排期：开始时点/时区、时段长度、资源、任务时长/窗口、强制任务、先后关系和互斥可编辑，冲突定位具体资源/时段，改变约束后只提新计划，不执行活动。
人员到岗位的有限配置另以等数人员/岗位和明确可任职配对矩阵呈现，当前每侧最多12。只展示可行完整配置和等权情景下配对占比，不称录用概率、最佳成本排班或业务适配事实。源资料只保上下文，资格由用户声明；不在界面自动推断。达到预算上限不能展示截断枚举为完整分布；取消/资源不足保矩阵及旧成果。


### 全项具体工作合同：数学当前审查与有限结果说明

每个已映射operation读回源审查状态，offline_review结果显示OFFLINE_PIN_REVIEW_ONLY、当前撤回NOT_VERIFIED、publishable=false；执行前后复核失败不冒完成。方法详情保来源和operation对应，而不是泛写OpenAI Math。验收审查变更、旧结果重开、资源耗尽、数值/精确类型区分及16项完整映射；不在前端增加论文求解器面板。

方案结果右侧“方法与范围”折叠层：先一句有限结论，再来源、假设、精度、未实现、审查时点。当前状态变更先用稳定文字条提示，不移动用户正在比较的方案。Web/Desktop侧读，iOS从结论打开详情再回同方案；官网案例带同一范围。UI适配根据“精确有限/数值近似/区间证明/形式重放未验”选择解释组件，不把视觉可信度当数学证明。

具体操作与恢复：数学结果在“方法与范围”详情内显示本次具体运算、固定论文/源码身份、已实现的有限部分、未实现部分、当前审查状态与时点、计算资源/精度类别。适用于原16种operation的状态复核，不将它们重新算新增16能力。当前审查不可核、撤回状态未知或仅离线固定源复核时，区分可读旧结果与不可发布/不可新执行，并给合法复核入口；旧PASS不迁移到新版本。普通用户仍从业务问题/约束进入，工程内部ID仅详情可查。


### 全项具体工作合同：按业务问题发现能力而非挑算法

能力发现显示business_purpose和availability/missing_dependencies时，普通文案用业务目的及影响，技术包名仅详情。按需输入从当前可信owner取得，UI不能猜权重/单位。测试无AI正常任务、缺依赖、依赖有但数据不合格、用户继续编辑时旧能力响应迟到、返回同问题及方法详情关闭恢复焦点。

首页问题输入→原任务工作面；结果前一条“本次可分析… / 还缺…”说明，可展开方法/依赖详情。布局直接按问题落到比较表、时间序列、区间或约束表，不先出现数学工具库。Desktop/Web/iOS保同一问题和输入，官网展示业务结果入口；UI可建议合适原生构图并保简洁/锁定/恢复，不改变计算方法、权限或原始值。

具体操作与恢复：保留现J19“用户问问题，不先选论文”的入口：由当前业务对象/问题及允许数据，系统检查适用方法与实际依赖，先给能回答什么、需补什么与不能回答什么。只在缺必要业务输入时补充范围、资源、期间或观察定义；不把registry里的算法/包名排成使用前置选择大厅。依赖AVAILABLE仅表示对应导入能力，不代表输入适用、运行通过或业务有效；未具备时保原资料与手工/确定性可用路径，不自动安装或切外部服务。
