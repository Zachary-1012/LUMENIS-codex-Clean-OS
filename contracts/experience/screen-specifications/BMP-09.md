# BMP-09 — 品牌评估

## 2026-10-24 品牌资料 / SourceBrief / BusinessWork 独立接线

BMP-09 保留实际评估维度、结果与来源的原 owner 合同；新 SourceBrief/BusinessWork 工作面不把人工意见或报告完成换成品牌分数。当前已选 BMP BrandFocus 的“导入本范围资料”复用 CTH-10 同一文件选择、来源用途声明及 Domain documents prepare → 明确确认 import，保持 `domain_id=zbmp` 和实际 `brand_focus_id`，不带 Shared workspace header，不以 CTH Subject 替代品牌身份。

按已选导入 source_ids 提交 SourceBrief，保留稳定请求身份，独立读取 task/job 后进入品牌工作；记录逐项匹配所选 BrandFocus，错品牌或错主体拒绝。方案选择、修订和成果保存沿原 BusinessDecisionWorkflow/Shared owner；人工执行未独立核实、内部制作、外部平台动作、来源报告的效果和因果归因保持独立。观察与费用增量各保原件/窗口/引用，旧指标不能被新费用来源替换；费用/退款/预算与跨币种未知分别呈现，来源撤回拒绝依赖重开。

同域保存使用服务端引用候选，用户明确确认后复用 Shared exact DATA_EXPORT 与父版本合同；saved_results 的最新精确 Artifact/draft digest 用于后续保存，重复同 revision 不重复生成。隔离消费者验证沿 `source_brief_domain_import_test.dart` 和 `business_work_panel_test.dart`；无AI基础路径可用不等于专业市场/创作者/传播判断、营销外发或实际商业效果已验收。

目录移除仍缺原注册 owner 生命周期HTTP合同；完整品牌专业链、全部原 coverage、四表面及真实用户验收均保留。本节记录实际接线边界，不提升现有整屏设计/验收状态，也不把历史 mock/样例或隔离测试当真实品牌材料。

```yaml
screen_id: BMP-09
status: OWNER_REVIEW
revision: 1
owner_domain: BMP
binding_ids: [BACKEND-GAP-026]
product_owner_approval: APPROVED_OVERALL_EXPERIENCE_CONSTITUTION_30_36
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: SOURCE_BACKED_SCOPE_BLOCKED_IMPLEMENTATION
reviewer: Bounded ROUND-13 implementation worker
reviewed_at: 2026-09-22
approval_reference: ROUND-13-BMP-CREATION-UI
```

## 1. User problem and product invariant

- A brand operator needs to understand movement by evaluation dimension, confidence and source coverage using actual observed results.
- Evaluation is derivative: it cannot rewrite the recorded result, replace its source or become a new truth store. Subjective generated text is not an evaluation result.
- `BACKEND-GAP-026` currently returns unfiltered evaluation records and drops source references; the page remains blocked until exact BrandFocus or global range and result lineage are available.
- Scope modes are explicit: authorized `GLOBAL_ALL` evaluation aggregates may be shown with global result lineage; `FOCUS` dimensions must match the selected BrandFocus. Focus data is never relabeled as global.

## 2. Route and bindings

- Read callable: `LumenisCoreClient.screen('BMP-09')` / `/api/experience/screen/BMP-09`.
- Display gate: `binding.scope_read_evidence_version` and `binding.evidence_lineage_version` must both be `v2`, `binding.read_access` must be `ALLOWED`, and `binding.scope_mode` must match the returned context. `FOCUS` requires the exact selected `brand_id`; `GLOBAL_ALL` requires a null `brand_id` plus `global_read=ALL_GRANTED`. Legacy self-reported scope/permission booleans are not accepted.
- Expected fields: `dimensions[].name`, `score`, `movement`, `confidence`, `evidence_coverage`, `source`, `brand_id`, `evidence_ref`, and `reports[]`.
- A report control uses `report:write` only to save a local report-request draft; it remains non-executing until the canonical owner returns a result.
- Only `actual_result` or `verified_result` sources are accepted by the view-model.

## 3. State and recovery

- Loading, not collected, offline and access-denied states are distinct.
- Unscoped or lineage-incomplete dimensions are hidden rather than shown with zero or a generated score.
- Ready shows score, movement, confidence and coverage together; reports remain separate from dimensions.
- Report request blocked/local-draft states never claim a report was generated or written.

## 4. Purpose-built composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-09)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- Desktop uses a score matrix beside a report shelf, preceded by a BrandFocus line and an actual-result qualifier.
- This is a scorecard/evidence-coverage workflow, not a generic trend dashboard or repeated metric-card renderer.

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-09)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-09)。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：公开数据营销组合与归因


**4. State additions**
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

**9. Executable acceptance**
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 数据同权、按用途、重构；不使用付费源。

### Existing contract — Actions, authorization and effects

- `report:write` saves a local evaluation-report draft only when exact read/action permission is present. Until the canonical server executor, Permission/effect fence and Evidence-bearing result exist, no report is generated or written.
- No score recalculation, source correction or learning promotion is performed by the screen.



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

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-09)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：公开数据营销组合与归因


## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-09)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：公开数据营销组合与归因


### Existing contract — Accessibility and localization

- Each score row announces dimension, score, movement, confidence and source coverage in one linear label.
- Mobile list is the non-visual equivalent of the desktop matrix; no chart-only meaning.
- Integration key inventory: `screen.BMP-09`, `bmp09.subtitle`, `bmp09.scorecard.*`, `bmp09.report.*`, `bmp09.movement.*`, `bmp09.confidence.*`, `bmp09.coverage.*`, `bmp09.recovery.*` for `zh-CN`, `en`, and `ko`.

## 7. Executable acceptance

- A subjective or AI-only score is rejected by the source allowlist.
- A record without selected BrandFocus or source lineage is not displayed.
- A missing score remains unavailable rather than zero.
- Report request is blocked or explicitly local-only without a write result; no generated/written success is shown.
- Wide and narrow layouts preserve actual-result-only semantics.

Current decision: `IMPLEMENTED / BLOCKED_FOR_EVALUATION_SCOPE`; canonical evaluation owner must restore source references and brand filtering before real-user E2E acceptance.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 理解品牌评估变化、置信和覆盖情况。
- **屏幕专属呈现：** 维度、真实Outcome、置信、分母和方法并列，文本意见不冒充分数
- **来源、范围与版本连续性：** 绑定原Outcome/Evidence/评估方法与版本，不改写源事实
- **四端差异：** Web/Desktop可比较维度和周期；Mobile逐维度和来源；官网只发布审核结果
- **失败与恢复：** 未评估/样本不足为UNKNOWN；历史版本保留但可标stale
- **补充验收：** 分数可回样本和方法，结果变化生成新版本，不自动Promotion。

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

既有品牌业务工作子视图沿同一 `BusinessWorkPanel` 使用宽屏三域：左侧当前 BrandFocus 的原研究依据并可打开经 Owner 重新核验的引用；中间纸面比较方案并保留报告回答、假设、未知、执行成果与版本阅读；右侧固定当前决定、负责人、复核时间、资源约束及执行/观察/费用入口。普通字号以导航后实际内容宽度 960px 为三域起点，1280×720 窗口保留原侧栏仍同屏；按实际文字缩放提高所需宽度，空间不足或大于 150% 字号时重排。窄屏与放大字体重排为单列分段，决定置前、来源可展开，保持全部功能可达，不替换本屏其他指标、作者与财报工作面。

纸面问题默认至两行，长问题可展开为完整可选择原文；折叠不改问题。原核对动作移至工具栏。方案标题、依据、核查、假设和未知通过排印与段距分层，保全部正文与动作；来源/决定工具面与正文纸层区分，外壳不再重复套通用纸卡。材质变化不改 BrandFocus、版本或授权。

“修改决定”复用原严格日期表单和 `adopt` 合同，分别提交新的决定原因、负责人、复核时间与修订原因；保留同一来源简报、问题、方案、所选方案及资源约束，沿原 revision/CAS 和稳定提交身份追加版本。历史决定、原 Artifact 与撤权/冲突保护保留；新决定不借旧成果显示已保存。本段仅同步现有构图与消费者行为，独立运行和视觉验收仍按实际证据记录。

业务已保存成果的原版本阅读对话提供导出，复用唯一 SavedWork export 路由及 `Sh04ExportFiles`，使用当前精确 BMP/BrandFocus 范围，保持 ZBMP 兼容标识，不改独立 Shared workspace 权限。明确选择 DOCX/PDF/MD/TXT/XLSX/PPTX；默认交付文件，归档副本另选。导出前重新核对所选 Artifact/hash/version/draft digest 和业务工作 revision，新旧版本不互换，不为导出另存新版本。取消目的地、撤权、来源/范围变化和失败均不显示成功；浏览器仅确认已交付下载，桌面仅在用户所选位置保存完成后确认。短内容区或大字时，原底部动作随内容滚动，保留正文和全部操作的可达性。

### 作者、传播与同口径品牌比较

作者入口复用BMP-05三阶漏斗，左侧当前品牌/平台/时间范围，中间作者列表，右侧单作者证据检查器。账号按平台分行，不将相似昵称合并成同一人；层级标“启发式分层”，具体采用条件/未知在详情，不用统一达人价值分数。评论从明确父笔记进入，顶栏保父帖与样本窗口；传播读回按真实事件顺序，互动数、已观测事件和未知触达分别标注。
BMP-11比较区只并列当前BrandFocus授权样本与可比时间窗，列标题带定义/分母/覆盖；采样缺口占独立说明区，不用柱高宣称市场冠军。BMP-09指标可从手工导入或实际专业号来源进入，值旁显示“人工录入/平台读回”、单位/日期/版本，零分母或缺项显示未知；编辑手工值先保原值与修改理由/来源，预览后形成新版本，不改平台观测。
筛选切换时保当前已看作者/比较选择但重验scope；跨品牌、撤源、旧签名或专业号未配置时停止受限动作并清敏感预览，保合法草稿。加载与无匹配分开，取消编辑回原指标，保存失败保输入；恢复先读当前来源，不用本地cookie或界面开关声明授权。Web比较可锁列并深链回原作者/笔记；Windows/macOS可并读资料与指标并从实际文件导入，失链保上次合法可读状态；iOS按范围→作者/指标→依据/比较两两切换，横向表提供逐列读屏，不挤成缩略图。官网只展示去敏样本口径，不声称平台完整覆盖或商业收益。
界面AIGC按用户问题建议作者证据列、评论主题分组或可比样本对照，事实指标/分母不让模型补零，用户可锁列和撤销重排；未知保持可见。价值是知道哪些比较可信，减少跨平台身份和样本口径误用。


### 全项具体工作合同：财报原件到字段核对

在原资料核对子视图增加原件格式、主体范围、原生期间、单位、字段定位、缺失原因、定点更正链与匹配待核的显示合同；原Source/Importer负责真值，前端不能把文件名/字符串匹配写成身份确认。输入变更只作新分析请求，保存需要原SavedWork读回。验证SEC/XBRL/人工与区域披露各一条已支持正常路径、同名主体、重复字段、未知币种、年报不可拆季、原件撤回、取消后重开及四端原字段返回；不存在callable保持OPEN/UNBOUND。

财报核对：顶部“主体/范围 · 期间 · 币种/单位 · 当前原件版本”；左侧已保留原件列表，中间字段核对表，右侧原文定位。表上只有“改比较范围、查看原值/更正、保存核对、用于当前分析”，非算法选择。Web窄宽用字段列表→原文抽屉；Desktop保并读与键盘下一字段；iOS先字段值与缺失原因，再逐项口径/原文和待核选择；官网仅用有证据公开例展示这一链。UI适配遇到更正/口径冲突时建议原值/更正双栏，平时收起；不改表内数值，不把内容生成算UI能力。

具体操作与恢复：在原财报资料入口选择已保留原件后，先显示识别格式、申报主体/合并范围、财政期间、币种与单位；SEC companyfacts、XBRL、人工原文标注及已支持区域披露分别标真实解析范围。主区为“字段—值/缺失—期间—口径—原件定位”核对表，右侧固定原页/原文。点一行只定位其引文；人工标注可选原文范围、字段含义与期间，另存派生记录，不改原件。未知主体通过名称/标识原文并读请求核对，候选匹配不自动合并实体。重复值/总计分部/定点更正单列，不自动加总。
财报季度选择另列原生季度、累计、半年、全年；没有完整季度不能均分造数。花费代理以刊例价、曝光及相应假设逐项显示输入出处和区间，明确不是实支。解析完成、待核对、缺失、口径冲突、来源变化、保存待读回分开；取消解析保原件与已核字段，重开回原件/字段选区。用户得到可追溯、可比较的数据而非一个自动可信分数。
OpenDART请求配置只描述公司/年/报告/报表类型与凭证是否可用；凭证未配显示待连接，不填入聊天或把配置生成称采集成功。


### 全项具体工作合同：宏观季度与信息截止检查

同一结果绑定地区、指标、单位、quarter列表、as_of与vintage_basis；每季AVAILABLE/MISSING及reason必须可读，整体INSUFFICIENT不隐藏已可用季度。取消只停止当前分析，保选择和上版；恢复先读原任务，迟到结果不得改新截止。验收缺三月之一、同采集时点冲突、假日量不入季度、跨地区、来源撤回和重开同一截止。

宏观对齐在趋势主图下放“季度覆盖条”，空缺格保留空心与文字原因；选一季后旁侧打开原观察表及聚合式说明。顶部地区/指标/期间/截止紧凑常驻，“查看缺月、比较修订、用于预算情景”就地可用。Desktop/Web并列曲线与覆盖表；iOS季度列表→该季来源明细，允许修改条件后明确提交；官网示范有证范围。UI可按缺口选择覆盖表优先或完整序列图优先，不能插值成完整曲线，用户锁定的比较列不移位。

具体操作与恢复：宏观资料检查面用地区、指标、期间、信息截止作为业务输入，结果先给可用季度清单及缺口，再展示每季使用的原观察、发布与采集时间、聚合方法和来源。全国社零月额完整三个月才求和；CPI三个月同比均值明确只是均值；文旅季度总量与假日量分列；商圈客流是监测范围内人次，不当全市人数。当前季度对齐按采集截止筛选，并非历史首次发布日期重建。冲突同一时点、缺月、假日代季、地区不符各给具体原因；不默默补0或复制相邻季度。修改截止/地区前预览哪些季度和下游评价将改变，另存新版本。


### 全项具体工作合同：实验、概率校准和预测区间

增加实验启用开关与预登记规则的真实字段，不提供自动分发成功控件。校准/区间的分集不足、重复ID/已知泄漏、未知训练来源、无模型/依赖不可用、陈旧版本各保真实状态。撤销观察草稿不删除已提交观察；重复提交按原Owner幂等，取消后重开同版数据。验收无观察、0成功、有重复、改版后旧样本隔离、每集不足20、校准与区间结果不串用、断线后不重复计算/分发。

效果工作面三种任务按当前问题出现：变体比较表＋区间；可靠性曲线＋分箱表；预测值/区间＋保留集覆盖。顶部固定版本/窗口/观察出处，右侧仅展示当前任务的样本与假设检查；“补观察、比较版本、保留/停止、保存评价”靠近相应结果。Web/Desktop保同字段并列；iOS先每版/每组结论和缺口，点开语义表；官网只用已核案例。UI自身AIGC在三种原生构图中提出局部适配，不替用户改停止规则、不绘制假区间，不挤走正在填写的观察。

具体操作与恢复：实验从选定作品变体与真实观察进入：显示每版成功数/试验数、分配单位、观察窗口、用户预先声明的最少观察数及停止概率；“建议下一观察变体”是可选计算，开启不分发流量。结果列后验区间、停止建议及未满足条件；缺观察与真实0不同，改标题/封面后新建变体版本。
概率检查单独显示校准集/测试集样本数、标签来源、模型版本与分离声明，可靠性曲线与同源分箱表联动，ECE/Brier只说明此保留集上的经验校准；未独立验证训练隔离不得写概率已可信或模型已可上线。预测区间另用真实预测/观测和独立校准/测试集，显示目标覆盖、实际测试覆盖、样本量与宽度，不把校准曲线画成个体预测区间。用户面向“检查预测是否可靠/查看区间”操作，方法名仅在详情。


### 全项具体工作合同：路径归因与有限对照

保留原评价Owner与只读投影状态；真实新动作未接线时OPEN。新增任务专属合同：path贡献的非因果限定；DID干预点、设计声明/前趋势结果；合成控制供体及分期/权重/留出误差。校验同期间/单位、同版本来源，明确改变输入会使旧建议失效。验收重复路径、未知身份、干预前不足、溢出假设未满足、供体排除后不可行、取消/断线/旧回调，不能只验一条READY。

BMP-09中央为同时间轴处理/对照或真实路径矩阵，右侧“比较依据”固定干预时点、分母、窗口和假设。合成控制按需打开供体抽屉，前/后期用文字与竖线标界，贡献条与权重表同源；缺区间不画置信带。Desktop/Web并读，iOS先结论/限制→可选供体→同源表；官网带方法边界。UI适配按问题切路径/前后对照，不合成缺失边或供体；保用户钉住对象，可恢复稳定平面表。

具体操作与恢复：效果比较先由用户声明“比较观测路径/比较干预前后”及业务对象。路径归因展示已观察路径、转化定义/窗口、重复/未知身份情况，再列各渠道的描述性信用与移除假设；Markov/Shapley不等因果增量。DID展示处理/对照两序列、干预时点、前趋势容忍及设计假设，前趋势检查和效应估计分区。合成控制显示供体列表、可纳入/排除及理由、前期拟合/留出段、干预后比较、供体权重与敏感性；用户排除供体只形成新分析，不篡改原观察。设计不足只交观测对比，不能靠勾选假设升级因果。
待补数据、前期检验失败、供体不足/拟合不佳、超出有限通道上限、计算失败与完成分开；取消保原选择、恢复先读原任务和准确输入版。用户可看到为什么能比较、哪些解释仍不成立。


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


### 全项具体工作合同：按业务问题发现能力而非挑算法

能力发现显示business_purpose和availability/missing_dependencies时，普通文案用业务目的及影响，技术包名仅详情。按需输入从当前可信owner取得，UI不能猜权重/单位。测试无AI正常任务、缺依赖、依赖有但数据不合格、用户继续编辑时旧能力响应迟到、返回同问题及方法详情关闭恢复焦点。

首页问题输入→原任务工作面；结果前一条“本次可分析… / 还缺…”说明，可展开方法/依赖详情。布局直接按问题落到比较表、时间序列、区间或约束表，不先出现数学工具库。Desktop/Web/iOS保同一问题和输入，官网展示业务结果入口；UI可建议合适原生构图并保简洁/锁定/恢复，不改变计算方法、权限或原始值。

具体操作与恢复：保留现J19“用户问问题，不先选论文”的入口：由当前业务对象/问题及允许数据，系统检查适用方法与实际依赖，先给能回答什么、需补什么与不能回答什么。只在缺必要业务输入时补充范围、资源、期间或观察定义；不把registry里的算法/包名排成使用前置选择大厅。依赖AVAILABLE仅表示对应导入能力，不代表输入适用、运行通过或业务有效；未具备时保原资料与手工/确定性可用路径，不自动安装或切外部服务。


### 原要求具体工作合同：五维负样本复盘与BIL机制覆盖

复盘从准确作品/实验版本及允许观测进入，可按Topic、Hook、Persona、Template、CTA五维切换或并看；同时保普通、低表现、失败与高表现样本，缺样本类型明确提示，不能只显示胜出者。每条案例随行保原URL、日期、市场、平台、方法、分母和证据等级，分开原帖可核数据、部分访谈、行业假设、二手线索；生成例永不进入真实案例池。
BIL选例按机制覆盖展开品牌健康、社媒热度、UGC、触达质量、文化/购买意图、品牌DNA、本地执行、门店体验、增长、创作者归因、AI发现/传统曝光各自证据，不能合为品牌排行榜。用户可记录机制假设、反例、适用/不适用条件并采用为待验证Brief；旧案例正文/标签/日期/指标不自动复制到新ContentContext。

上部固定问题、样本窗与作品版，中部五维切片对照表，左侧样本类型及证据等级筛选，右侧所选案例原件/分母/机制笔记。BIL以覆盖矩阵显示哪些问题有何类证据，空格写未知；选择用于新Brief时预览“保留的机制/要重新核的事实”。Web/Windows/macOS并看正负例，iOS逐案例同字段对照，官网只给可核样例不排名。UI可按问题生成原创对照布局和缺口说明，不能挑选只剩好例、编分母或自动作因果结论；筛选和布局可锁定/复原。

筛选只改变阅读集合，不删失败记录；采用产生新任务引用和人工假设，不能自动晋升学习资产。验缺失败样本、相同标题不同版本、跨平台指标不可比、访谈不等原始数、生成例排除、风险因果措辞、取消采用和原筛选重开。新增统计区间和九维审阅不顶替本五维复盘要求。

### 原G106具体终态合同：平台原生信号与改写依据

选定创意/内容版本后，原生信号面逐行列停留、完播、重看、私发转发、评论、收藏、点赞的值/单位/期间/分母/可得状态和来源。指标优先是原方法语境，不自动变跨平台统一权重；不可得不补0。ROI区域单列成本、实际收益、归因范围及缺项，不能由点赞计算。打开“据此改写”返回该平台可编辑草稿，保事实母版并显示钩子/结构/时长/包装改变理由。

构图：左内容与平台版本，中间同字段信号表，右原生来源与改写差异；ROI与互动反馈不同区域。iOS逐平台同字段切换，不用同一柱高冒同尺度。

平台字段缺失、定义不可比、费用/收益不足、数据过期各保文字；取消保原稿，重开原信号版本，采用改写只改该平台候选，不自动发布或恢复外部权限。

Public Website仅用获准真实样例说明平台原生信号与改写依据及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按可比字段优先安排证据列，用户锁列/简洁/撤销；不造指标或把版式重排当商业回报。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

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

### 原G168具体终态合同：花费代理的乘项与锚点

花费代理详情明确列公开刊例CPM/CPC或计价区间、已采曝光/内容量、商单/广告识别概率及各自来源/期间/单位/版本；使用内容量代理时直写该假设，不冒唯一曝光。公开新闻稿/获奖案例/招标披露仅作有来源的锚点，列与估计是否可比及差异。输出区间、缺失和敏感因素，不能将代理点值写实支或据其自动投放。

构图：顶部当前渠道/期间，中间各乘项的出处/区间/未知表，右公开锚点原文，下方代理范围与缺口；移动逐乘项审查后看整体假设，数值有同源表。

无刊例或无曝光按原要求MISSING；识别概率未校准单独标明，单位/期间不匹配不算。改输入只新建情景版本，取消保原数据；重开保原锚点，来源撤回提示受影响结果。

Public Website仅用获准真实样例说明花费代理的乘项与锚点及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按贡献不确定性突出原输入，不能压掉最大缺口或生成费用事实；保锁定/撤销，价值是避免伪精确预算。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 便利操作合同：CV09 财报数字旁展开原行、表头和量纲

适用工作与省步目标：在品牌/经营研究中核一笔收入、营销费用或零售额；不用离开当前结果再找PDF页、表头和单位。 关联新增能力：D03, D04；细化J02原有减步与原工作面合同；不是新模块，不增批处理、比较导出、模式复用或独立快捷服务。

原Owner与真实接口边界：POST /api/experience/reports/financial/analyze 可读当前授权Evidence；/financial/save 可保存有来源的研究版。区域表格facts已有行/表头定位、列号、原数值字面量、source_scale及币种，歧义为REVIEW_REQUIRED。 待补：待前端把原行与表头两处锚点同时送SH-02；若某格式没有精确字段定位只开真实可用原件范围。不存在通用“直接编辑规范财务事实”的授权，不能画自动修正/升为Canonical的成功按钮。 代码依据：lumenis/importer/financial_tables.py:171–208 parse_regional_statement locator/source_scale/value_literal；lumenis/importer/financial.py:385–486 analyze_financial_source / save_financial_analysis；experience_runtime.py:4927–4965 financial/analyze and financial/save

控件位置与四表面操作：数字后放“核原行”轻按钮，打开可收起的原件条：原数值字面量、列所属期间、表头币种/倍率、提取后的数值及主体。量纲计算写成实际字面量×实际倍率，不做未授权换汇。先保持当前业务结果可见；“返回此数值”恢复同筛选/滚动。REVIEW_REQUIRED把具体歧义和所需原文放在这一条，不让人到设置页找。 四表面：官网：去敏财报例展示同一原行/表头/结果关系。；Web Workspace：财报行旁就地并读SH-02，关面回原数字。；Windows/macOS：同Web，原文件读取仅使用已导入/用户显式选择的文件。；iOS：数字详情Sheet先显示值/单位，再按需切原行与表头；返回原列表同一行。 省去：省去手抄数值到笔记；省去另开原件后重找表头；省去返回研究结果后重新定位同一行。UI自身AIGC：可把真实表头与选中数值排成上下关系或侧读，不能猜期间/币种或自动改值；关闭适配恢复固定字段顺序。

持久化、权限与错误恢复：并读只读；明确保存核对结果才走financial/save，带request_id、原work_id/previous_artifact_id和当前actor/scope。核对批注不能覆盖原Evidence，声明更正按已有来源/人工标注工作流另存；读回后才显示已保存。 原件撤权/变hash停止旧锚点，保合法自写批注；定位失效展示原件可读范围而非伪高亮。取消收起核对条并回原数字，未知写入回执先查原request，不重复新建。 验收：同一PDF有多个表头时绝不借上一表倍率；元/千元/万元及括号负数只显示源码真实解析结果；扫描件/歧义表头不假装可一键核对。当前为研发合同，未实测减步数字，未宣称四端接线完成。

验收以同一真实任务记录原路径/新路径的操作、切换、重复录入、失误与恢复；没有实测前不填写节约秒数或成功率。便利界面与接线仍须本地构建，后端只按实际Owner测试证据判断，不能用本段规划声称已完成。

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
