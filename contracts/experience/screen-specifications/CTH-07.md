# CTH-07 — 趋势分析

```yaml
screen_id: CTH-07
status: BLOCKED
revision: 1
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-013
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: NON_AUTHORITATIVE_EXPLORATION_ONLY
reviewer: Codex delegated ROUND-10 bounded source review
reviewed_at: 2026-09-22
approval_reference: source baseline origin/main 5ba1aefc53a1babc293e990c23c62f841724c843; this is not per-screen acceptance
```

## 0. Authority basis and artifact disposition

- The governing experience row is the CTH-07 aligned time-series canvas with metric-definition rail, compatible comparisons and a decomposition panel.
- The current backend is `experience_screens._build_cth07(binding, authorize)` through the existing screen route and `_cth_temporal_screen`: it reads the authorized native-time metric Owner and returns `temporal_metrics`, current global/focus binding and `trend_metadata` (numerator, denominator, time_window, subject, source, freshness, recipe, snapshot_sha256). The adapter and four-surface E2E still require verification. Statistical decomposition and source contributions do not establish causal contributions.
- Static trend fixtures and action metadata are non-authoritative. A chart array alone does not prove numerator, denominator, Subject, source, freshness or an explanation for change.
- The implementation is purpose-built as definition → aligned chart → arithmetic change explanation. It does not guess causal contributions.
- Sol design decision: `BLOCKED`; a trend is rendered only when its definition and aligned values are source-backed.

## 1. User problem and product invariant

- **User task:** understand how a returned CTH metric changed over one stated window, what its numerator/denominator mean, and which returned series is selected.
- **Context:** global data requires `GLOBAL_ALL` plus a server `global_binding` (or current canonical equivalent) proving global grant/scope, CTH product/domain, `scope_verified`, `read_allowed` and verified lineage; the definition subject must also be global. Focused data additionally requires an applied CTH focus binding, exact Subject equality, CTH product/domain, `scope_verified`, `read_allowed` and verified lineage. Missing fields block the chart.
- **Completion signal for this slice:** a user can select a returned series and read its labels, values, definition and simple first-to-last delta. The UI does not claim why the delta happened when contribution data is absent.
- **Invariant:** arithmetic change is not causal analysis. No missing series, source error or undefined denominator becomes zero. `bound=true` alone never authorizes a global aggregate.
- **Out of scope:** adding metrics/cohorts through a server call, exporting, editing a metric, causal explanation, Evidence navigation and any external effect.

## 2. Route, entry, exit and return

- **Entry:** `Cth07Screen(client: ...)` from the existing workspace; no new route.
- **Read sequence:** `settingsContext()` → `screen('CTH-07')`. The adapter verifies the server scope/read/lineage binding, then reads `chart.labels`, `chart.series[name,data]` and `trend_metadata`/`truth.trend`; every series must align to all labels.
- **Scope gate:** global definitions must be `GLOBAL/ALL`, `global_all` or `global` and carry the authorized global binding; focused definitions must match the returned Subject ID and authorized focus binding. Missing or mismatched scope blocks the chart.
- **Exit / return:** series chips and detail selection are local; there is no server-side metric/cohort mutation and no deep-link to a contribution source.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source/ViewModel field or callable | Definition / units / window | Freshness and missing-data behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Scope label | SYSTEM context read | `LumenisCoreClient.settingsContext()` | `GLOBAL_ALL` or applied CTH focus | Invalid/missing scope blocks; internal IDs hidden | — | Current context contract |
| P1 | Aligned series | CTH aggregate read | `_build_cth07()` chart `labels`, `series[name,data]` | Same time labels for every series; numeric values only | Unaligned/missing data or missing server authorization/lineage produces NOT_COLLECTED; no zero-fill | BACKEND-GAP-013 | Current authorized temporal metric projection; complete UI binding not established |
| P1 | Definition rail | CTH native-time metric Owner | `trend_metadata` or `truth.trend`: numerator, denominator, time_window, subject, source, freshness | All six fields required; units/window shown as returned | Missing/unsafe source means no chart | BACKEND-GAP-013 | Current server supplies metadata; App adapter same-version acceptance remains separate |
| P1 | Change explanation | Metric/decomposition owner UNKNOWN | Local first-to-last difference only; contribution data is not returned | Numeric delta over the displayed window; not a cause | Show “贡献拆解暂未返回” when absent | BACKEND-GAP-013 | Arithmetic/statistical output is not causal attribution; causal contribution owner remains unverified |
| BLOCKED | Add/remove metric or cohort | CTH trend/action owner UNKNOWN | ViewModel/action declaration only; no verified request/result | UNKNOWN | No controls or optimistic overlay | BACKEND-GAP-013 | `trend_api/canonical_metrics` UNKNOWN |

## 4. State and recovery matrix

| State | Trigger/evidence | User-visible meaning | Available actions | Recovery/return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Context/chart request pending | 正在加载趋势分析 | None | Announce; no line or table values | CTH07-W-001 |
| Empty / no series | Explicit empty chart state | 当前范围内暂无趋势记录 | Refresh | Do not build an empty/zero line | CTH07-W-002 |
| Not collected / definition missing | Chart arrays or definition absent | 趋势暂不可用，口径尚未完整返回 | Refresh | Keep raw arrays hidden | CTH07-W-003 |
| Fresh / stale | Source freshness field absent/returned | Only show returned freshness | None | Never infer “latest” from response time | CTH07-W-004 |
| Partial | One series misaligned or contribution missing | 趋势可读，但解释项暂缺 | Refresh | Render only complete aligned series; arithmetic delta may remain | CTH07-W-003 |
| Offline | Core/source failure | 暂时无法连接 | Retry | Failure is not zero | CTH07-W-005 |
| Blocked / permission denied | Invalid scope, `bound=false`, missing global grant/binding, or focused response without exact authorized binding; 401/403 | 经营主体信息暂不可用 | Retry after recovery | Do not reuse global trend for focus; do not render an unauthorized aggregate | CTH07-W-006 |
| Error | Malformed response/5xx | 运营信息暂不可用 | Retry | Hide raw details | CTH07-W-005 |
| Local series selection | Choose a compatible returned series | 查看所选指标 | Switch series | Preserve definition/window; no server effect | CTH07-W-007 |

## 5. Purpose-built desktop composition

集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-07)。

- **Primary question:** what changed over the stated window, and what exactly does the metric measure?
- **Hierarchy:** scope/window → metric-definition rail → aligned chart and table → change/decomposition panel. Units/window remain adjacent to axes and values.
- **Keyboard:** series chips are focusable; Enter/Space selects; chart has an accessible label and synchronized data table; no chart-only meaning.

## 5A. Web Workspace composition and desktop-only capability boundary

- Web and desktop share the same series/definition model, table alternative and no-guessing rules. No client-side trend API or metric store is added.
- Metric/cohort controls, Evidence contribution links and export are unavailable until contracts bind.
- Runtime E2E must verify resize, keyboard series selection and truthful missing-definition state.

## 6. Purpose-built mobile composition

- **Active task:** choose one returned metric and understand its aligned values and window.
- **Layout:** chart/table first, metric switcher second, definition rail third, change explanation fourth; the selected metric remains visible.
- **Touch:** metric chips and retry meet 48 logical pixels; chart has a spoken label and the data table remains available.
- **Interruption:** no cached trend or pending metric change is represented. Retry repeats the read.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read/write/external effect | Idempotency / reversal | Evidence emitted | Confirmation and failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Load context/trend | SYSTEM + CTH native-time metric Owner; verified GLOBAL_ALL/FOCUS binding and current read recheck | Existing server scope-read Permission | Read only | Repeatable | Returned series/definition only | Safe ready/not-collected/error state |
| Select returned series | Flutter local state | None | No server effect | Reversible | None | Enabled |
| Add/remove metric/cohort, inspect contribution, export | CTH metric/action/Evidence owners UNKNOWN | UNKNOWN | Potential write/read/export | UNKNOWN | UNKNOWN | No enabled controls |

## 8. Accessibility, motion and localization

- Every series chip exposes its label and selected state. The chart has a non-visual label and a synchronized data table with date/value text.
- Axis units/window and definition fields are plain text; color is not the only series distinction. Missing contribution state is announced.
- Loading, unavailable, empty and error states are live regions. No authored motion is required.
- The bounded UI uses existing `screen.CTH-07`, context, common, state and `cth01.*` keys; no hardcoded screen copy remains. Canonical l10n must add `cth07.definition_rail`, `cth07.series_switcher`, `cth07.chart_label`, `cth07.decomposition_missing`, `cth07.action_unavailable` and state copy in zh-CN/en/ko before acceptance, then replace the temporary generic mappings. No second l10n owner.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State/error path | Platform/input | Test layer | Current evidence/reference |
| --- | --- | --- | --- | --- | --- |
| CTH07-W-001 | Pending response announces loading and hides trend values | Loading | Widget | `app/test/features/cth/cth07/cth07_screen_test.dart` | Local evidence |
| CTH07-W-002 | Explicit empty trend does not create zero values | Empty | Widget | Widget test | Local evidence |
| CTH07-W-003 | Raw arrays without complete definition or alignment stay unavailable | Not collected/partial | Widget/repository | Widget + contract test | Current backend metadata gap |
| CTH07-W-004 | Definition shows numerator, denominator, window, Subject, source and freshness when returned; no inferred freshness | Definition/freshness | Widget/API | Contract test required | Adapter contract implemented |
| CTH07-W-005 | Offline/5xx/malformed response is safe and retryable | Offline/error | Widget | Widget test required | Safe copy implemented |
| CTH07-W-006 | Focused unbound or mismatched scope is blocked | Focus scope | Repository/widget | Repository test required | Current runtime focus gap |
| CTH07-W-007 | Select a series and retain chart/table/definition alignment without an effect | Local interaction | Widget; keyboard/touch | Widget test | Desktop/mobile evidence |
| CTH07-W-008 | A real new event feeds a source-backed trend with an honest definition and lineage | Real user work | Runtime/E2E | Required before ROUND-10 PASS | Not yet run |
| CTH07-W-009 | Return `bound=true` with chart arrays but no global grant/lineage; the repository blocks before decoding the trend | Global authorization/lineage block | Repository/widget | Repository test | Implemented hostile fixture |
| CTH07-W-010 | Return authorized `GLOBAL_ALL` and exact Guangzhou Taikoo Hui `FOCUS` definitions; only matching scope is rendered | Authorized global/focus read | Repository | Repository test | Implemented legal fixtures; contribution lineage still pending |

## 10. Review decision and open questions

- **Decision:** `BLOCKED` for canonical trend analysis and ROUND-10 acceptance. The bounded implementation only draws a complete, scope-matching, definition-backed trend and labels missing decomposition honestly.
- **Open owners:** CTH metric owner must define the callable and units; Evidence must bind contribution/source lineage; SYSTEM must bind Subject read authorization; action owner must define metric/cohort requests; l10n must add three locales.
- **Required before acceptance:** real new data, complete trend definition, source freshness, Subject binding, non-zero/failure distinction, contribution lineage and desktop/mobile E2E.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 解读有定义指标在特定窗口内的变化。
- **屏幕专属呈现：** 图表、表格、分母/定义/单位/时间/来源并列
- **来源、范围与版本连续性：** 同指标和scope进入分析；解释带同一Evidence版本
- **四端差异：** Web/Desktop图与定义表并读；Mobile看变化再展开数据点；官网只用核准公开数
- **失败与恢复：** 空值/缺分母/stale/error不转0；不同比较窗阻止趋势
- **补充验收：** 图表表格一致可回源；没有归因证据不解释原因。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。


### 全项具体工作合同：宏观季度与信息截止检查

同一结果绑定地区、指标、单位、quarter列表、as_of与vintage_basis；每季AVAILABLE/MISSING及reason必须可读，整体INSUFFICIENT不隐藏已可用季度。取消只停止当前分析，保选择和上版；恢复先读原任务，迟到结果不得改新截止。验收缺三月之一、同采集时点冲突、假日量不入季度、跨地区、来源撤回和重开同一截止。

宏观对齐在趋势主图下放“季度覆盖条”，空缺格保留空心与文字原因；选一季后旁侧打开原观察表及聚合式说明。顶部地区/指标/期间/截止紧凑常驻，“查看缺月、比较修订、用于预算情景”就地可用。Desktop/Web并列曲线与覆盖表；iOS季度列表→该季来源明细，允许修改条件后明确提交；官网示范有证范围。UI可按缺口选择覆盖表优先或完整序列图优先，不能插值成完整曲线，用户锁定的比较列不移位。

具体操作与恢复：宏观资料检查面用地区、指标、期间、信息截止作为业务输入，结果先给可用季度清单及缺口，再展示每季使用的原观察、发布与采集时间、聚合方法和来源。全国社零月额完整三个月才求和；CPI三个月同比均值明确只是均值；文旅季度总量与假日量分列；商圈客流是监测范围内人次，不当全市人数。当前季度对齐按采集截止筛选，并非历史首次发布日期重建。冲突同一时点、缺月、假日代季、地区不符各给具体原因；不默默补0或复制相邻季度。修改截止/地区前预览哪些季度和下游评价将改变，另存新版本。


### 全项具体工作合同：传播网络、Hawkes/Bass与MMM

将Hawkes/Bass点估计、网络中心性、MMM非因果限定作为必显语义，不由通用“置信”字段代填。依赖未安装/样本不足/拟合失败/诊断缺失与来源版本分开。取消保输入；重开不重新训练，预算另算绑定同源版本。验收无边、HITS非唯一、少于30观察、重复时刻、无变化渠道、季度不连续/年拆季拒绝、宏观地区/截止不符、诊断NaN、依赖不可用和恢复。

传播主区“真实边图/同源边表”并列，时间模型在独立页签用观测点＋拟合线＋分期标志；方法抽屉标点估计与缺区间。MMM沿BMP-09上方数据覆盖条、中部渠道贡献/情景对比、右侧诊断与来源；区间只画Owner真实返回者。iOS先缺口/结论→同源表→方法，Desktop/Web保并读；官网只展示有证边与适用范围。UI适配在网络、时间、季度比较三种原生视图中按已存在数据提出布局，不补边、补期或臆造ROI。

具体操作与恢复：传播检查把真实观察关系与时间模型分开。图只列转发/提及/合作的已观察边，节点表同时列中心性和边覆盖；HITS无法唯一识别就显示该项不足，不使整张图失真。时间面选择事件窗/时间单位或累计采用序列，先看观测与前半训练/后半回测及简单基线，样本少、重复时刻或非单调累计明确阻断。当前Hawkes/Bass有限实现仅点估计，未量化的参数/预测不确定性不得画成区间或“预测必然峰值”。
MMM主面先核原季度、申报主体/合并范围、币种、渠道真实花费或代理、结果单位与宏观来源；给训练/留出覆盖、共线/常量渠道/依赖状态，再呈渠道贡献及预算情景。诊断不通过时隐藏看似可靠的优化结论，保诊断和输入；无因果ROI证据明确NOT_ESTABLISHED。预算变化仅计算场景，不能付款或发布。


### 全项具体工作合同：有分母的比例、声量、情感、问卷与销售份额

必须显示真实分母和NO_DATA；统计置信、样本代表性、原始值真实性分开。修改筛选只改变新分析，不覆盖旧结论。验收零分母、0成功、有未知标签、SOV重叠提及、重复问卷ID/缺答、非推荐问题、同口径销售缺失/币种错配、取消/重开。缺业务输入仍保允许来源阅读，不能要求用户选Wilson/NPS计算器。

指标解释在主值旁常驻“多少/总共多少 · 窗口 · 覆盖”；展开后同源计数表/区间及排除原因。问卷结果用0–10响应分布＋三组计数＋缺答，净情感用标签计数＋未知，销售份额用分子/市场总量与口径表。Desktop/Web可固定两种指标并看，iOS逐项解释和可访问计数表；官网案例直写观察范围。UI按计数/问卷/金额选择语义准确的图表，未知保留文字空态；不把无数据补0，不用光影暗示置信。

具体操作与恢复：指标以业务问题进入，先呈分子、分母、计数规则、时间/地区/平台和缺失量。负面率或转化率按明确可比试验计数显示Wilson区间，重复事件不能偷换独立试验；区间不修复选择偏差。声量份额只针对互斥已观察提及总量，范围缺口与平台覆盖常驻，不命名总体市场份额。
净情感用已知正/中/负标签作分母并单列未知数；推荐调查必须有真实0–10“愿意推荐”问卷定义、调查/样本范围和响应，推荐者/中立者/贬损者及缺答分别列，不能从情感推NPS。销售份额只读用户提供的同口径销售金额或件数：主体、市场定义、地区、品类、期间、币种/单位并读；缺总额、分子大于总额、货币或定义不一致不计算。两类份额和两类态度结果可并读但不能揉成总分。

### 原G144/G145具体终态合同：趋势分解、告警与启发式限定

趋势结果保原序列并按实际返回展开趋势/季节/余项，告警/变点用带时点、方法版本及原始值的标记，可点回同源观察。ETS/ARIMA等合法预测只在实际输出区间时画预测段，训练历史与未来范围分界；<14点明确INSUFFICIENT，保原观察表。方法/回测详情列实际异常召回与误报率、评估窗及缺测，原≥0.8目标不伪称已达成。
旧KOS/归因/CTR启发式结果逐值标v1和“启发式未校准”，不是概率；无数据不回默认0/50。只有原Owner提供同模型校准证据和当前适用结果才可显示概率/区间，UI标签不能自行升级资格。

构图：顶部对象/期间/口径，主图为原序列与可选择分解层，旁侧同源表；选告警后右侧打开观察/方法/回测，启发式标签紧邻实际值。iOS先结论/缺口，再单图层与可访问表。

不足点数、断点缺值、常量序列、模型不可用、拟合/回测失败分开；改窗口新分析，取消保原序列和上版，重开不自动训练。未知不被平滑线遮掉，旧告警不当当前事件。

Public Website仅用获准真实样例说明趋势分解、告警与启发式限定及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按解释目的安排分解图、原值表和告警证据，用户锁图层/简洁/撤销；不造预测带或用亮度表现可靠性。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

模型可计算与业务告警已批准必须在同一结果区分列：原Alert Owner当前返回alert_evaluation.state=CONFIGURATION_REQUIRED、reason=APPROVED_SCOPED_BUSINESS_RULE_REQUIRED，旁列真实model_state/model_reason/monitoring_state。即便model_state为READY，也只能说明当前统计计算状态，不能画成“已启用告警”、已获批准或实时监测正常。保原binding/window/source/snapshot_sha256/recipe依据入口；回溯变点不叫未来预警，控制图默认值不当已校准业务阈值。

当前alerts=[]、write_state=NOT_PERFORMED、notification_state=NOT_PERFORMED分别显示“未生成业务告警／未写入／未通知”，不能把空列表显示“无风险”或“所有告警已处理”；rule和threshold为空就显示尚缺当前范围的已批准规则。cooldown.state=NOT_APPLICABLE、reason=NO_COMMITTED_MODEL_ALERT表示没有已提交模型告警，不能启动倒计时或假造冷却到期。读取/刷新不产生告警、通知或授权；缺批准时可继续查看原序列和统计、返回原Owner的规则审查说明，未有实际批准入口不放一键启用的假控件。

旧人工输入阈值须另卡呈现legacy_heuristic；仅真实非DEFAULT有效正数配置可显示CONFIGURED_LEGACY_HEURISTIC，但business_validation仍NOT_VERIFIED、scope_binding仍UNVERIFIED_LEGACY_INPUT、window为空仍未核。MANUAL来源标签不证明当前scope/window绑定或模型校准，历史DEFAULT-IC020行更不能当用户批准。此卡不与模型业务告警合并，不因用户看过卡片自动补齐批准。

Web与桌面在图旁分列“统计状态／业务告警配置／写入与通知”，窄屏和iOS用可展开同一状态组且首行仍可见未批准，官网获准样例也标此界限；刷新、重开、取消后继续读回同一真实版本。拒绝/失效状态保可读原工作，不以颜色、可爱动效或UI自身生成隐藏缺配置。验收覆盖READY但未批准、来源/范围变更、默认旧阈值、真实人工旧阈值及重复读取零写，原G145完整趋势/异常目标保留，当前状态不冒完整告警功能验收。

### 便利操作合同：CV10 季度缺口点到所缺原件，再回原选择

适用工作与省步目标：用户在宏观季度结果看到缺一个月、同日版本冲突或假日量不能替代季度量，需要补资料而不重填地区、指标、期间、截止日。 关联新增能力：D07, D08；细化J02原有减步与原工作面合同；不是新模块，不增批处理、比较导出、模式复用或独立快捷服务。

原Owner与真实接口边界：POST /api/experience/reports/macro/analyze 与 /macro/save 接evidence_ids/selection；季度行已有MISSING/AVAILABLE、reason、信息截止、来源与聚合口径。 待补：待补缺口→原导入入口的上下文回链与已选Evidence暂存。后端目前给季度原因，不保证逐缺月地址；月份、可补来源只由真实已解析观察与授权来源目录得出，无依据时只说本季资料不足。当前是重算该宏观分析请求，不宣称增量计算引擎。 代码依据：lumenis/importer/macro.py:134–190 align_quarters；lumenis/importer/macro.py:192–272 analyze_macro_sources / save_macro_analysis；experience_runtime.py:5186–5213 macro/analyze and macro/save

控件位置与四表面操作：季度行“补这一处资料”展开缺口：已覆盖月份/冲突的两个实际版本/假日资料类型，按能证明的粒度显示。按钮“选择已导入原件”“导入原件”进入原J05，带回合法新Evidence后回同季度，原地区/指标/期间/as_of全部保留并可检查；点“重新检查本分析”再计算，不把补件自动视为已采用。 四表面：官网：真实去敏季度例展示完整三月与缺月不同结果。；Web Workspace：CTH-07/BMP-09结果行展开缺口，导入完成回同格。；Windows/macOS：可拖入用户明确选择的原件进入现导入器，保当前分析布局。；iOS：季度纵列→缺口Sheet→系统已授权文件选择→回同季度，不另开多层模块。 省去：省去重复输入四个selection字段；省去记住缺失期间后首页找导入；省去补完资料再重建分析。UI自身AIGC：可把该季度相关月份与来源条整理到同一个展开区，不能补0、推断未发表月值或把假日量画为季度总量。

持久化、权限与错误恢复：查看与补件选择不写分析；导入沿原权限，保存宏观新版本沿macro/save，旧版不覆盖。新增Evidence若跨scope必须重新授权，不能用保留的选择绕过。 没补到所需月继续MISSING；假日代季度、截止后采集、同时间冲突逐项原位保留。取消导入回缺口格；离线保本次选择为明确未同步草稿，不显示已入库。 验收：社零三月齐才求和，CPI月同比均值仍明确为均值；补件后cutoff不自动延后；同一补件重复返回不重复计入evidence_ids。当前为研发合同，未实测减步数字，未宣称四端接线完成。

验收以同一真实任务记录原路径/新路径的操作、切换、重复录入、失误与恢复；没有实测前不填写节约秒数或成功率。便利界面与接线仍须本地构建，后端只按实际Owner测试证据判断，不能用本段规划声称已完成。

### 便利操作合同：CV11 统计错误直接定位需修的输入，保留其余草稿

适用工作与省步目标：用户问比例是否可靠、每天走势如何或市场份额多少，遇到成功数超过总数、日期断档、非数值或口径不匹配时只修必要处。 关联新增能力：D10, D12, D29, D40, D41, D42, D43, D44；细化J02原有减步与原工作面合同；不是新模块，不增批处理、比较导出、模式复用或独立快捷服务。

原Owner与真实接口边界：GET/POST /api/experience/reports/statistics 已有业务目的、源Evidence、options和能力可用性检查；多项错误仍只返回STATISTICS_*代码，数值输入验证不返回行列。 待补：原Reporting/Importer Owner须补结构化error.path、可证行号/列号和源hash绑定，或前端只对原公开规则做明确标注的本地预检。不可从一个通用错误猜第几行。源数据当前作为Evidence读取，不存在任意改Evidence后直接重算API；修订应回原导入/用户原稿，另存新源再重算。 代码依据：experience_runtime.py:4870–4904 GET/POST reports/statistics；lumenis/shared/reporting/statistics_methods.py:10–23 _statistics_numbers；lumenis/shared/reporting/business_brief.py:1377–1450 options and dataset validation；lumenis/shared/reporting/business_brief.py:1510–1545 source hash recheck and provenance payload

控件位置与四表面操作：结果区保业务问题与上版结果，错误旁“到需修处”；有精确path时聚焦成功数/总样本两个框或具体日期行，显示原值、所需条件和原数据定位。只把相关输入展开，其余折叠但不清空。无path则定位完整真实输入表并写“服务未返回具体行”，不乱圈红格。方法名仅高级详情，不先推算法选择器。 四表面：官网：去敏示例演示失败输入到修正后结果，不显示假计算。；Web Workspace：SH-03/CTH-07按可证path定位一组输入，返回原业务问题。；Windows/macOS：同Web并允许用户原数据编辑器并读；不修改外部原文件。；iOS：错误列表一次一项，点开对应输入行；保当前键盘焦点和未改字段。 省去：省去反复全表找错；省去失败后重录合法参数；省去复制错误码去别处查方法。UI自身AIGC：可按真实error.path选择最小修正面与顺序；不能生成数据填补、擅改阈值或替用户选择结论。

持久化、权限与错误恢复：更正保在原稿或新导入版，不改不可变Evidence；重算重新核新源权限与hash。统计计算、保存研究稿和用户采用结论分别显示真实状态，沿现SavedWork/研究保存合同，不发明statistics/save接口。 取消修改回上版原值；新源解析失败保草稿和旧结果并标旧版；依赖缺失保UNAVAILABLE且仍可读数据。没有真实单结果计算接口时重新执行本分析，不承诺只算一个单元格。 验收：通用NUMERIC_INPUT_INVALID不得伪造行号；Wilson分母为实际trials，NPS只用真实0–10问卷；日期缺口不插值或补0，三种统计口径不互换。当前为研发合同，未实测减步数字，未宣称四端接线完成。

验收以同一真实任务记录原路径/新路径的操作、切换、重复录入、失误与恢复；没有实测前不填写节约秒数或成功率。便利界面与接线仍须本地构建，后端只按实际Owner测试证据判断，不能用本段规划声称已完成。

## 2026-10-18 恢复候选后的当前接口接续（F待执行）

当前静态事实：后端`experience_screens._cth_temporal_screen`直接返回现temporal owner；当前Dart强制experience-row-projection v2，恢复候选强制旧experience-query-receipt v1，两者均未接现shape。不得给后端补假projection/聚合Evidence来迁就旧UI。

F输入合同：原screen endpoint的envelope含sections及truth；`temporal_metrics`是完整派生快照，含binding/recipe/coverage/source_freshness/totals/days及原来源contributions；scope用`global_binding`或`focus_binding`。`trend_metadata`含numerator/denominator/time_window/subject/source/freshness/recipe/snapshot_sha256；chart.labels为日期，series每项name/metric/data，data允许null。snapshot_sha256仅计算身份，不是来源Evidence。界面不得因null丢掉整条系列或补14天零值。窗口、原生发布时间缺失、样本范围/可比性和来源贡献沿Owner真实状态显示。

F输出/视觉：原趋势图区上方保范围/时间口径，缺测点以断点/未知展示；右侧依据抽屉为真实contributions，不能以计算hash替原件。模型READY不等业务告警批准；CONFIGURATION_REQUIRED/APPROVED_SCOPED_BUSINESS_RULE_REQUIRED时零告警写入、alerts=[]、NOT_PERFORMED、cooldown NOT_APPLICABLE。原人工启发式单独标scope/window未核。验收用真实builder输出做GLOBAL/FOCUS、known/null/partial/empty、撤权及来源变化解析测试；无旧projection时不误报未绑定，不自动告警或推断市场覆盖。Dart适配和四端效果仍OPEN。

本段校准旧current断言，历史验收不改写。源码/字段以现Owner为准，静态对齐不升级IMPLEMENTED/ACCEPTED。执行集合Codex、Zack、阿康；F是模块归属，不派个人。
