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

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-07)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- The primary question is “what was planned, what actually happened, and what can be measured?” Planned and actual values never share one undifferentiated status.
- Preserve the distinct lifecycle meanings `planned → budgeted → launched → observed → measured`; a request draft or budget plan cannot establish launch, observation, or a measured outcome. Missing backend support remains OPEN rather than inventing a stage result.

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-07)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-07)。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：营销日历与热点建议


**4. State additions**
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

**9. Executable acceptance**
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 建议可忽略，用户决定。

### Existing contract — Actions, authorization and effects

- `campaign:write` saves a local request draft for authorized content activity; no campaign write is sent or persisted.
- `campaign:close` saves a local campaign-close draft. Until the canonical server executor, Permission/effect fence and Evidence-bearing result exist, no close effect is attempted or reported.
- Quota/cooldown can be shown only as a process notice and cannot be relabeled as ROI, reach or outcome.



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

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-07)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：营销日历与热点建议

Web Workspace composition
Web：日/周/月与列表视图按任务切换；拖拽排期有键盘编辑等价路径，刷新读回计划版本并提示未保存改动，计划与执行回执分开。

## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-07)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- Mobile handles one selected milestone at a time, with its outcome kept distinct and channel details opened explicitly. Returning preserves the selected milestone, plan version and unsaved edits.

### 草图增补：营销日历与热点建议


### Existing contract — Accessibility and localization

- Lifecycle steps are announced in order with planned/actual distinctions in each label.
- Timeline milestones have a linear list equivalent; color is not the only stage signal.
- Integration key inventory: `screen.BMP-07`, `bmp07.subtitle`, `bmp07.lifecycle.*`, `bmp07.milestone.*`, `bmp07.channel.*`, `bmp07.outcome.*`, `bmp07.action.*`, `bmp07.recovery.*` for `zh-CN`, `en`, and `ko`.

## 7. Executable acceptance

- A topic quota response alone cannot render a campaign, ROI or measured outcome.
- A verified campaign keeps planned, budgeted, launched, observed and measured states distinct.
- BrandFocus leakage from another campaign is rejected by the view-model allowlist.
- Close/write actions remain blocked or save an explicitly local draft when exact approval/result fields are absent; no close or write success is shown.
- Desktop, compact and mobile widths preserve lifecycle and outcome semantics.

Current decision: `IMPLEMENTED / BLOCKED_FOR_CAMPAIGN_SCOPE`; the BMP owner must bind canonical activity results before real-user E2E acceptance.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 连接活动目标、预算、里程碑和实际结果。
- **屏幕专属呈现：** 目标→受众→渠道→预算→Outcome时间线；估算/承诺/实支各自分层
- **来源、范围与版本连续性：** 预算/日期变化定位受影响活动段、素材、资源和日程，父版可回滚
- **四端差异：** Web/Desktop编辑计划和影响预览；Mobile逐项审预算；官网仅公开示例
- **失败与恢复：** 无真实活动不造ROI；预算变化不触发付款/发布，冲突可回父版
- **补充验收：** 修改后只有受影响内容变化，新旧版本可重开比较。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。


## 2026-10-18 完整工作面细化：迁移、业务与内容模式

保留原状态/Owner/接口和完整终态；本文补足视觉交互，不宣称已接通或已验收。

### 合作草稿、执行批准与不明结果

从作者/活动的“建立合作草稿”进入现有业务对象，不自动创建投放。宽屏主区是可编辑目标/资源/范围/动作草稿，右侧版本与将受影响对象；下方用分开的“草稿→请求审阅→已批准→执行回执”阶段行。批准确认显示当前精确请求摘要、对象、动作、范围与版本；撤销批准为独立动作。用户看得到批准不是执行，不把客户端布尔值、legacy解锁cookie或页面隐藏当服务端Permission。
仅已注册且当前可用渠道才显示合法执行入口；未配置写“尚无可用执行渠道”，仍能保存方案。提交后由Owner读回真实执行与receipt；超时未知提示“结果待核”，提供核原请求回执和返回草稿，不自动重新发送。取消请求、撤销批准、停止当前动作分别说明效果边界，已产生的外部结果不被删除。旧scope/来源/请求变更使旧批准失效，重新预览批准；失败保原稿与历史，不显示空成功。
Web恢复原工作和请求版本，刷新不会执行；Windows/macOS窗口重开先核原执行回执，后台Core状态另示；iOS先草稿摘要→精确批准Sheet→结果页，实际禁止的执行动作保持说明并返回已存任务，既有合法审阅不因窄屏丢失。官网演示草稿/批准/真实执行的区别，不将未绑定渠道做动效假演示。界面AIGC可按任务建议行动摘要/资源比较顺序，批准与执行控制独立固定、不能生成或替点确认；用户锁定的草稿不被覆盖。价值是减少误批、误发与重复外部效果。


### 全项具体工作合同：多准则、组合、排期及人员配置

新增业务可编辑字段及Owner结果映射，不暴露任意JSON、内部算法参数或论文选择器。状态至少：需补单位/币种、判断不一致、不可行约束、预算/时限耗尽、已有可行但未证最优、完整枚举失败、计划待采用、保存冲突。采用计划/配置只保存Decision/Brief，联系/采购/发布另获原授权。验收预算变动、必选与互斥冲突、资源重叠、未知覆盖不求和、等数/规模限制、无可行配置、取消后重开、旧计算晚到不盖新约束。

CTH-09上部目标与约束，中部方案同字段并列，右侧取舍解释；不一致判断行就地高亮并有文字。BMP-05候选列表旁固定预算/覆盖，选中组合与备选在同一比较层。BMP-07排期条上方资源/时窗，底部冲突清单可定位，拖拽另有起止时间键盘输入。人员配置为“人×岗位”可勾选矩阵＋完整方案清单，iOS逐人选择岗位并审阅冲突，不缩小矩阵。Web/Desktop可并读；官网真实例；iOS只开已支持约束编辑/方案审阅，复杂排期续接同版本。UI适配按目标提出取舍表、预算组合或资源排期视图，不改变权重/资格/约束，锁定比较维度与选中项。

具体操作与恢复：方案比较有三种已有业务输入面。取舍比较：逐项编辑指标值/单位、越高越好或成本方向及“更看重哪项”的成对判断，显示权重、判断不一致位置与排序敏感性；不要求用户操作AHP/TOPSIS名词。创作者组合：预算、每项真实成本、声明效益单位、必须覆盖、候选纳入/排除并读，显示选中组合/替代与未满足约束；效益相加假设不冒独立触达。排期：开始时点/时区、时段长度、资源、任务时长/窗口、强制任务、先后关系和互斥可编辑，冲突定位具体资源/时段，改变约束后只提新计划，不执行活动。
人员到岗位的有限配置另以等数人员/岗位和明确可任职配对矩阵呈现，当前每侧最多12。只展示可行完整配置和等权情景下配对占比，不称录用概率、最佳成本排班或业务适配事实。源资料只保上下文，资格由用户声明；不在界面自动推断。达到预算上限不能展示截断枚举为完整分布；取消/资源不足保矩阵及旧成果。


### 原要求具体工作合同：免费来源数据类别与聚光未配置边界

原来源任务范围内，按平台注册的广告/流量、创作者中心、公开内容等实际对象显示当前合法取得路径与可得字段。每行分别列免费/费用未知/需额外许可、公开路径/获准自有会话/已授API、身份条件与实际最近结果；“平台注册”不等“免费可采全部”。缺某类数据保其他可用材料，不能以公开视频替广告账户观测或把零条当成功。
聚光为来源/活动当前任务的一项：未配置专业号、授权未知/失效、字段未取得分别写具体原因；未配置保持UNAVAILABLE，用户可跳过继续当前规划，不强制开通或付费。KFS的F“24h互动>20再投”只列方法假设及适用性，旁边明确“未执行投放”，不能据此出现自动充值/投放成功。

SYS-02平台lane详情“本任务数据”表列数据类别→字段→取得路径→费用/许可条件→实际状态，选行打开具体限制和原来源；BMP-07在所选活动的数据依据中显示聚光可用性及方法说明，不另建广告管理器。Web/Windows/macOS表与详情并读，iOS一类别一详情并保原lane/活动，官网只公开验证过路径。UI可据实际缺项聚焦解释，不生成授权、专业号或预算执行；简洁同源列表可锁。

选择来源/类别不自动登录、请求付费API或外发；恢复依原Source/Session/Permission明确动作。验每平台注册字段缺失、免费但未获权、授权但无数据、聚光专业号未配置、授权撤回、零条与未知、取消和重开；完整平台注册范围逐项运行仍OPEN，不能以一来源示例验全部。

### 原G105/G120/G173具体终态合同：节点交叉、当月适配与跨市场稿件

现营销日历顶部依次选择日期/时区、行业、区域和平台；国内节气/节日/大促与海外/区域节点可交叉筛选。7行业与26海外节点沿原版本化数据读取，展示实际已载/缺项和来源，不按目标数造日期。建议结果列节点、真实适用期、情绪主题、调性及与当前Brief关联理由；当月自动绑定作为可检查提案，用户可改/忽略。报告保marketing_nodes的真实节点引用，CSV导出先预览日期、时区、区域、任务、平台和版本，排期导出不是发布。
出海视频从同日历选择7区域节点，脚本中标具体关联段及平台包装差异；TikTok/IG Reels/YT Shorts分别保原生版本。KOC层级与店铺承接是当前计划/链接和真实观察分区，缺授权、缺店铺或无转化观测不编闭环。

构图：月/周/列表主面，顶部交叉筛选，右侧节点/来源与加入计划；选中脚本段后同区域的平台稿并读，底部CSV预览与导出。iOS按日期→节点→关联脚本/计划逐层，不缩小整个日历。

日期未知、地区不适用、过期节点、日历年份未覆盖、缺来源和计划冲突分开；改区域/日期先列受影响稿件/排期，取消不改计划，重开保节点版本，旧建议不覆盖人工日期。

Public Website仅用获准真实样例说明节点交叉、当月适配与跨市场稿件及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按密度建议月历、顺序列表或平台差异对照，保同一节点/所选稿和撤销；生成营销创意不等UI AIGC。价值是节点有据可用且跨市场改写不丢事实。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。


### 2026-10-21 交互源码吸收：开发前行为边界

材料：[独立审核包](../../../research/engineering/documentation-evidence/reports/product_research_deadline_20261018/interaction_equivalent_20261017/README.md)，静态对读 `src/contracts.mjs 的 initialRevision/proposeRevision、studies.mjs 的 revision`。这里只吸收适用行为与反例，不执行、移植或发布审核包，不改变本屏既有实现/验收状态。

预算/需求局部变更先以当前活动版本和真实单位生成提议，明确旧新值、受影响成果位置及未核依赖；人工备注、未提交数值和其他成果不被覆写。采用检查当前Permission/基线/来源版本，取消保原稿，撤销依原Owner生成可追溯修订；演示整数人民币分/固定天数只是数值机制，不是产品通用货币或收入模型。

沿当前 `app/lib/features/bmp07/` 及Shared依赖Owner区分计划改变与执行/发布。验收人工备注之后再采用、预算改动使旧提议失效、已知依赖外不瞎改、部分失败仅重试受影响项；不得将本地修订历史标作跨媒体真正更新。

活动排期的 `schedule.mjs` 仅作原Owner行为参考：日期调整先提议并绑定活动计划版本，取消保原日期，确认核当前编辑权及基线；撤销仅沿现有Owner支持的修订形成新版本。日期计算及实际外部执行回执由原排期Owner定义，不从demo civil-day或本地receipt推导新增calendar API。未有真实可调用写接口的活动操作保持OPEN、禁相应效果，不借CTH-05只读舆情日历落写。
