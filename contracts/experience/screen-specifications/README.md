# OEVIRA Screen Specifications

本索引维护已纳入主线的逐屏合同；完整规划及视觉文字草图沿各自唯一入口维护。2026-10-18的PR83阶段稿记录属于历史基线，后续内容校准见CURRENT及唯一规划开篇，不再当作当前待合并任务。“完整”表示必须覆盖的产品范围，不表示现有前端已达标。各屏Owner、接口、状态、交互、视觉、可访问性和四表面验收保留独立证据；已有实现、限定验证与用户接受不能互相替代。当前整体前端未获用户验收，开发须按完整规划和各屏实际合同逐项升级，不能以现有布局限定目标。

本索引的 reviewed/内容核对指已明确审阅的文稿范围；未审条款、实现、运行、研究与效果不随之通过。原待项按[唯一规划开篇接续表](../../../00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md#现有未闭项与原工作面接续非新队列)关联原页面、[唯一草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md)和同版证据，继续原Owner工作，不新设等待设计批准的实现门槛。

This folder holds the reviewed implementation specification for each canonical App screen. The 44 rows in `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md` §36 are distinct UX blueprints and a coverage baseline, not a ceiling on the product's pages or approved tasks; they do not prove that routes, source fields, permissions, effects or acceptance behavior have been verified.

## Rules

- This index and the screen specifications define Experience requirements; they do not assign work or record current window state. Current dispatch/pause/resume is established by the latest direct Product Owner instruction and the local live ledger/tool receipts, not by published rules or historical notes.
- Reuse the existing `<SCREEN-ID>.md` and update it alongside implementation. The complete frontend/backend plan is [product-plan-full.md](../../../00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md), and its full-product visual/operation sketch is [FULL-PRODUCT-SKETCH.md](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md); update them in place under Architecture/Experience and the actual screen contracts, never create duplicate current versions. Direct implementation does not require a separate design draft/Figma or M DESIGN_READY prerequisite. A specification file or design status alone never proves acceptance.
- Use `contracts/experience/lumenis_app_binding_registry.json` as the binding inventory. Update it only from current source/runtime evidence; never treat historical `BOUND`, task assignee or ViewModel labels as proof.
- Keep CTH Subject-first, BMP Brand/Market-first, Shared lineage and SYSTEM infrastructure boundaries intact.
- Do not copy screen layouts into a shared renderer. Shared tokens and semantic interaction primitives may be referenced, while each specification must define its own information hierarchy, composition and task choreography.
- `UNKNOWN` owner, callable, field source, actor scope, permission or evidence lineage blocks the dependent behavior. Record it as `DESIGN_EXPLORATION` if useful; never describe it as production-ready.
- PDFs, taskbooks, screenshots, wireframes, Figma frames, fixtures and generated visual proposals are non-authoritative references. List their disposition in the spec; never copy them directly or infer approval from visual polish.
- A repeated audit sketch frame does not authorize a shared renderer, universal card grid or substituted-title screen. Direct implementation is authorized by the latest PO and current contracts; unbound/fabricated behavior or generic repeated layouts remain REWORK.
- Set `APPROVED` only after the product owner or delegated design owner has reviewed the specification and its open questions. Record reviewer, date and the accepted change/review reference. A batch approval must list every covered screen ID and cannot silently approve unreviewed exceptions.
- Implementation, test and runtime status must cite current artifacts. A spec approval is not implementation acceptance; editing a rule does not change any existing design, implementation, runtime, or user-acceptance status.

## Status lifecycle

Keep design review, implementation and outcome acceptance as separate evidence fields. The actual design-review record may progress `DESIGN_EXPLORATION` → `OWNER_REVIEW` → `DESIGN_READY`; implementation is recorded independently as `IMPLEMENTED`; user-outcome acceptance is recorded independently as `ACCEPTED` only after its real evidence passes. These are not one required serial lifecycle: direct construction under current contracts does not wait for DESIGN_READY, and none of the three fields implies another.

Use `BLOCKED` when a verified owner, contract, authorization or acceptance dependency is missing. Design-review states record actual review and are not a mandatory coding sequence. Maintain each screen's existing specification with source changes. Do not fabricate DESIGN_READY or infer acceptance from code presence.

## Surface scope and acceptance

2026-10-11 PO correction: build Public Website, Web Workspace, Windows/macOS Desktop and iOS Mobile in parallel under their approved roles. Website uses the existing `website/`; Workspace/Desktop/Mobile share one Flutter `app/` and Product Core. Build the complete task-shaped frontend without waiting for all backend work; bind available real APIs/Core immediately and connect remaining existing-owner dependencies incrementally, keeping missing behavior OPEN/UNBOUND. Preserve the 44 ScreenSpecs as baseline, not a product ceiling. Native targets are Windows/macOS Desktop and iOS Mobile; Android/Linux native-client source remains historical, while browser coverage across operating systems and Linux server/CI remain in scope. Direct construction needs no separate design draft/Figma or M DESIGN_READY approval. Approval: `00-GOVERNANCE/evidence/approvals/PO-20261011-WHOLE-PRODUCT-REUSE-EXPERIENCE.json`.

The full visual and interaction scope covers all 44 baseline App screens, existing Public Website content families and any other approved product task/page. Golden Pages and workflow sequencing order implementation only; they do not cap or replace the complete screen/site scope. Each of the four surfaces has a distinct role and is accepted only from its own real operation, runtime and recovery evidence. One surface's acceptance does not pass another or the whole product. This paragraph records product scope, not current window dispatch state.

## Intelligent UI 全屏语义映射（2026-10-08）

All 44 screens and the existing Website families receive a product-wide, task-specific visual and interaction upgrade under the sole Experience Constitution. Present externally sourced content and capabilities through OEVIRA's existing Experience and owners. Keep original source material, evidence, works, and provenance unchanged; any excerpt or derived presentation stays identifiable as such.

Apply the Product Architecture's `2026-10-09 来源类别同权与已有数据优先闭环`: public webpages and platform sources have equal source-category base weight. Evaluate each record's quality, identity, time, rights, and permitted use on its own; equal category weight does not merge those dimensions.

Reuse the current Architecture and Experience corrections for the shared product boundaries: CTH/BMP remain business domains; Shared creation can start from the user's own brief or permitted assets without a CTH/BMP task, Subject, Case, Campaign, or SourceBrief prerequisite; AI enhances product-wide paths while ordinary business work remains useful without a model; analysis and mathematics return backend-produced business results rather than requiring users to choose paper operations. SYS-06 covers the controlled in-product browser only; external opening is an explicit choice and general OS/computer control is withdrawn.

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

以下映射把 Intelligent UI 的任务适配方法落到既有 44 个 ScreenSpec。它是逐屏设计补充，不是第二设计权威；Owner、Binding、Permission、现有状态和未决问题仍以各规范及 Experience Constitution 为准。操作页不机械搬到公共官网；四个产品表面共享 Core/上下文和数据语义，但分别适配工作姿态。逐屏详情在对应文件末尾 `Intelligent UI 逐屏采用项（2026-10-08）`。

| 屏幕 | 用户任务 / 专属呈现 | 来源、版本与端侧动线 |
|---|---|---|
| [ACC-01](ACC-01.md) | 确认内部工作区入口可用并继续宿主指定目标；显示入口状态与宿主提供的继续动作；无 callback 不伪造路由或账户流程 | 传递宿主实际 route 与原任务位置，失败时保留入口；Web接浏览器route；Desktop回原窗口；Mobile恢复原任务；官网只说明公开入口 |
| [ACC-02](ACC-02.md) | 查看当前GLOBAL_ALL或明确选择一个可访问Subject视角；列表、当前视角和确认预览并置；说明选择不授予业务读取权限 | 只有服务端确认的scope envelope传递给下游，切换后回原工作；Web/Desktop提供目录与预览；Mobile逐项选择；官网不展示私有目录 |
| [ACC-03](ACC-03.md) | 从首页开始真实工作或继续原任务；打开即聊天/任务入口，导航进入各业务和独立能力；保留任务、草稿、已访问页面与工作接续，不做KPI营销模板 | 恢复Task/Brief/scope/Artifact版本，建议只开草稿不触发效果；Web多区并读；Desktop快捷续接；Mobile突出一个待续任务；官网只作公开介绍 |
| [ACC-04](ACC-04.md) | 理解一项真实阻断并沿已有恢复路径返回；展示发生了什么、影响哪个任务、已绑定的恢复路径 | 关联原Task、请求scope、operation与恢复receipt，保留未提交内容；Web/Desktop并列工作与受控说明；Mobile按阻断→影响→恢复；官网不显示内部诊断 |
| [AI-01](AI-01.md) | 把用户目标、当前资料与约束组成可检查的执行意图；自然语言问题、选中资料与必要业务约束可编辑；建议可接受、修改或拒绝，内部合同/算法字段不铺满操作页 | 沿用同一Task/Brief/引用/Actor/scope；真实结果可读、可保存并能查看来源与必要状态；execution ID及合同字段只由后台保留，不要求用户输入；Web/Desktop并看输入与资料；Mobile逐项确认；官网仅公开且标注示例 |
| [AI-02](AI-02.md) | 跟踪真实任务阶段与持久化产物；按服务端实际状态组合阶段轴、当前输出和Evidence/Artifact检视 | 同一run/model/recipe/input scope版本贯穿恢复与保存；Web/Desktop阶段轴加检视；Mobile聚焦当前阶段；官网不呈现内部运行 |
| [AI-03](AI-03.md) | 逐条核验分析结论的来源并继续修订；Claim—Citation—不确定性阅读，围绕一个结论局部修订 | 保留Evidence ID、source locator、scope和父版本；下游复用同Brief；Web/Desktop消息与引用并读；Mobile先结论后引用；官网不显示私有讨论 |
| [AI-04](AI-04.md) | 查找适合当前任务的已验证能力，并按现有 Owner 合同完成已批准的使用与生命周期操作；呈现能力输入/输出、版本、许可、风险与评估；当前目录只读，已批准的启用/运行/更新/停用等操作按现有 Skills owner 补齐，缺口保持 OPEN | 保留既有 skill ID/version、输入和原 Task；每个生命周期/运行操作单独经过既有 Permission，不因选择而授权；Web/Desktop目录与详情；Mobile显示当前Task可用能力；官网只列已验证能力 |
| [AI-05](AI-05.md) | 查看AI服务真实状态和延迟样本；脱敏状态、采样时间及有界延迟；不显示原始provider/model | 诊断与具体业务任务版本分开，不把诊断数据写回任务；Web/Desktop状态与样本；Mobile显示当前状态；官网不暴露拓扑 |
| [BMP-01](BMP-01.md) | 回答授权品牌的市场信号与值得关注的趋势；市场脉冲、趋势候选和证据抽屉；给时间窗、样本与来源覆盖 | 品牌/global scope、Evidence、采集时间和指标版本随同一Brief进入方案；Web/Desktop信号与来源并读；Mobile先优先信号再证据；官网只讲已验证能力 |
| [BMP-02](BMP-02.md) | 理解品牌组合、子品牌与竞品关系；带来源关系图加选中实体档案，明确已核实/推断/未知 | 每条边保留BrandFocus、entity ID、关系来源和版本；Web/Desktop图和档案；Mobile可展开关系列表；官网不展示私有谱系 |
| [BMP-03](BMP-03.md) | 识别需要进一步验证的机会信号；置信/动量图、排序清单和来源简报并置，解释排名依据 | 信号ID/来源/窗口/scope/评分版本随同一Brief传给提案；Web/Desktop图、列表、简报并读；Mobile排序原因后详情；官网仅公开审定案例 |
| [BMP-04](BMP-04.md) | 看品牌传播链哪些阶段实际有观测；左到右渠道路径与定义矩阵，每阶段区分observed/unavailable | 渠道、单位、来源、时间和品牌范围绑定；选中渠道不改归因事实；Web/Desktop河流和矩阵；Mobile逐阶段下钻；官网不呈私有数据 |
| [BMP-05](BMP-05.md) | 比较创作者匹配度和风险依据；按已返回KOS/KOL/KOC/UGC类别呈列表和来源档案 | 指标定义、时间、BrandFocus、来源及评估版本进入后续任务；Web/Desktop列表与档案；Mobile先理由后样本；官网仅授权案例 |
| [BMP-06](BMP-06.md) | 把授权素材和内容想法推进为可审阅版本；Draft→Review→Approved→Delivered专属编辑流程，来源/rights贴近正文 | 继承同Brief/Evidence/品牌/语言；修改保存子版本和受影响片段；Web/Desktop正文与证据并读；Mobile聚焦待审与修订；官网不编辑内部稿件 |
| [BMP-07](BMP-07.md) | 连接活动目标、预算、里程碑和实际结果；目标→受众→渠道→预算→Outcome时间线；估算/承诺/实支各自分层 | 预算/日期变化定位受影响活动段、素材、资源和日程，父版可回滚；Web/Desktop编辑计划和影响预览；Mobile逐项审预算；官网仅公开示例 |
| [BMP-08](BMP-08.md) | 从自有创作Brief/手写脚本/获准音频独立制作可审阅播客；授权业务来源是可选输入，脚本、来源、rights、音轨和发布状态分层；横向拖动时间轴 | 独立路径沿用自有Brief/audio version；选用业务来源时才连续绑定SourceBrief/Evidence/rights；本地Read Aloud不等于成片；Web/Desktop脚本与音轨并列；Mobile分段查看；官网只放授权成片 |
| [BMP-09](BMP-09.md) | 理解品牌评估变化、置信和覆盖情况；维度、真实Outcome、置信、分母和方法并列，文本意见不冒充分数 | 绑定原Outcome/Evidence/评估方法与版本，不改写源事实；Web/Desktop可比较维度和周期；Mobile逐维度和来源；官网只发布审核结果 |
| [BMP-10](BMP-10.md) | 按严重性、扩散和时效处理有证据的品牌风险；风险队列、原始依据、派生判断、后续状态分开 | 绑定品牌scope、Evidence、判断版本与决策receipt；Web/Desktop队列和详情；Mobile先风险依据和原文；官网不呈私有风险 |
| [BMP-11](BMP-11.md) | 在口径一致时比较品牌基准；先展示币种/期间/口径/分母，再显示可比矩阵和差距 | 每格保留定义、币种、样本、来源、范围、计算版本；Web/Desktop多品牌矩阵；Mobile逐项查看口径；官网不公开客户比较 |
| [CTH-01](CTH-01.md) | 查看商业运营活动并检视单个事件；Subject/context、运营脉冲、事件流和选中详情组合 | 保留scope、时间窗、event ID和来源锚点；下游继承相同范围；Web/Desktop流和详情并读；Mobile按脉冲→事件；官网不显示私有运营 |
| [CTH-02](CTH-02.md) | 浏览商业主体目录与已核实关联；主体列表和有证关系档案；资料暂缺不能由名称猜补 | 目录选择元数据不更改live Subject；正式切换经ACC-02确认；Web/Desktop列表和关系档案；Mobile搜索展开；官网不公开内部名录 |
| [CTH-03](CTH-03.md) | 查看监测变化、平台lane并阅读一条信号；时间窗脉冲+Collector lane+单条reader；平台热度与自有样本分开 | 原始platform ID、发布时间、采集时间、scope、Evidence进入Research；Web/Desktop流与lane检视；Mobile先变化后单条；官网只讲已验证采集 |
| [CTH-04](CTH-04.md) | 理解事件先后和证实的关系边而不推因果；实际时间轴与有证关系图切换；选节点看原来源 | 保留事件ID、源时间/capture time、relation version；Web/Desktop时间轴/关系图；Mobile按时间下钻；官网无内部事件图 |
| [CTH-05](CTH-05.md) | 寻找真实变化日期并查看当日样本；真实日密度与当日列表关联，标记分子/分母/窗口 | 保留scope、日期、时区、metric定义和source；Web/Desktop日历+列表；Mobile日期摘要后列表；官网不显示内部日历 |
| [CTH-06](CTH-06.md) | 分拣反馈并读原始措辞；triage队列加原文Reader；派生类别可编辑且不等于事故/Case | 保留原文、平台时间、Evidence、scope及人工/AI分类版本；Web/Desktop队列与原文并读；Mobile逐条打开再回队列；官网不呈私密反馈 |
| [CTH-07](CTH-07.md) | 解读有定义指标在特定窗口内的变化；图表、表格、分母/定义/单位/时间/来源并列 | 同指标和scope进入分析；解释带同一Evidence版本；Web/Desktop图与定义表并读；Mobile看变化再展开数据点；官网只用核准公开数 |
| [CTH-08](CTH-08.md) | 追踪真实Case到Outcome并区分复用知识；Case→Insight→Decision→Action→Outcome泳道；知识独立显示审阅状态 | 所有节点绑定同一canonical Case/scope/来源和版本；知识不覆盖事实；Web/Desktop全链和知识并看；Mobile逐阶段返回；官网不露私有Case |
| [CTH-09](CTH-09.md) | 区分风险依据、决策状态、审批和实际动作；风险、Decision ledger、Action receipt分区显示提案到执行状态 | 沿用已有Actor/scope/approval/effect ID，不为风险创建平行任务；Web/Desktop并列风险与账本；Mobile先状态再依据；官网不露内部审批 |
| [CTH-10](CTH-10.md) | 创建或重开有来源的运营简报并检查结论；正文/方法/引用/Action-Outcome分页阅读；从同一SourceBrief Job重开 | 沿用job/report/hash/brief/evidence/scope/父版；源失效局部复核；Web/Desktop正文与来源栏；Mobile逐页返回；官网仅审批公开版；朗读限当前绑定文本 |
| [SH-01](SH-01.md) | 从自有Brief/获准素材直接开始独立创作，或由现有Task进入研究/创作/媒体工作；已绑定能力→专属Reader/编辑器，Timeline/ShotPlan保留专用工作区 | 独立创作沿用自有Brief/Content Project；采用业务来源时才带入SourceTarget/Evidence/Artifact/timeline版本；目录本身不执行；Web/Desktop承担并读与复杂编辑；Mobile任务摘要后打开素材；官网只列已证能力 |
| [SH-02](SH-02.md) | 检索并阅读同一组有来源研究材料；按平台原生形态组合图文/长文/短视频/线程/音频Reader | 保留Source/Evidence/platform ID/scope/time/rights；进入Brief不重搜；Web/Desktop列表与Reader并行；Mobile搜索→列表→单篇→原位返回；官网不载内部资料 |
| [SH-03](SH-03.md) | 理解Canonical指标定义、成熟度和Source链；Schema/Metric树加逐级lineage，不展示原始DB表/路径 | 查询沿用GLOBAL/FOCUS读权，Metric版本和Evidence引用可带入分析；Web/Desktop树+关系；Mobile搜索→定义→来源；官网仅展示公开核准口径 |
| [SH-04](SH-04.md) | 重开真实Artifact、比较版本并回到原Task；类型化Viewer和版本序列展示父版、来源、局部diff | Artifact ID/hash、父Brief/Task、scope、source refs保持一致；本地朗读只读READY重开文本；Web/Desktop专属Viewer；Mobile成果→差异→原任务；官网不提供私有Artifact |
| [SH-05](SH-05.md) | 审阅学习资产的样本、方法、反例和生命周期；candidate/verified/rejected/promoted/rollback证据流，页面只读 | 引用Outcome/Evidence/Evaluation及父版；Promotion回Learning owner审批；Web/Desktop候选和版本差异；Mobile状态→依据→原Owner；官网无内部资产 |
| [SH-06](SH-06.md) | 从任务/通知/警报返回原业务工作；任务、通知、警报分lane，选中呈来源/scope/状态/下一步 | 保留原Task/Notification/Artifact ID和origin，打开回原任务；Web/Desktop列表+详情；Mobile lane→原工作→返回同一条；官网无内部通知 |
| [SYS-01](SYS-01.md) | 读RuntimeGuardian状态和Worker/DLQ保护指标；health snapshot按整体→队列→防护解释，采样时间在场 | 同一guardian/source/timestamp；业务指标不得混入；Web/Desktop状态脊柱；Mobile故障优先；官网不承诺内部健康 |
| [SYS-02](SYS-02.md) | 查Collector各平台lane和进入Evidence的真实状态；平台manifest/lane/attempt/receipt显示configured/active/partial/blocked | 关联真实Collector task与Source/Evidence receipt，不伪造覆盖率；Web/Desktop矩阵和单lane详情；Mobile按平台读；官网只讲验证过能力 |
| [SYS-03](SYS-03.md) | 核对schema、integrity、readability与Truth chain层次；分别呈schema、自检、应用读取、链路阶段，不给总绿灯掩盖缺口 | 绑定实际check/time/chain ref；不泄漏DB路径/业务行；Web/Desktop分层检查；Mobile阻断优先；官网不呈系统诊断 |
| [SYS-04](SYS-04.md) | 安全理解允许范围和审计可用性；allowlisted安全级别、控制化scope与audit状态，不显示策略细节 | 真实permission仍按Actor/scope/operation服务端判定，本页不授予权限；Web/Desktop访问姿态+审计；Mobile逐行展示；官网不露策略 |
| [SYS-05](SYS-05.md) | 调整设备外观并返回相同工作状态；本地偏好预览/对照/撤销，配色和壁纸只影响本端呈现 | 保持route/scroll/selection/draft；偏好使用现有本地owner，不变业务数据；Web按网页本端；Desktop适配窗口；Mobile适配触摸；官网使用公开品牌视觉而非用户私有壁纸 |
| [SYS-06](SYS-06.md) | 在原任务授权范围内读取和操作受控来源，完成必要的验证并返回原任务；按真实 capability 显示地址、当前来源、页面与允许操作；RecoverySheet 需要 LOGIN_FORM/VERIFY 时承接受控交互，再交还 PlatformSession 健康复核；不露账号/profile/port/path | 保留 Task/来源/target/page revision，返回恢复草稿和选择；来源保存经既有 Evidence owner，浏览画面不自动成为 Evidence；不接触私人 profile；Web/Desktop 承接授权浏览与原 Task；Mobile 适配已批准的阅读/验证/返回流程，能力不具备时保留 OPEN 而非永久只读；官网不执行内部浏览 |
| [SYS-07](SYS-07.md) | 检查实际Evaluation gate证据和未完成项；check→scope→run version→Evidence→状态，分开blocked/unknown/pass | 关联实际Evaluation版本；审批推广由相应owner执行；Web/Desktop检查与证据；Mobile先阻断；官网只讲真实验证能力 |
| [SYS-08](SYS-08.md) | 查看脱敏日志目录和可追溯Trace；仅呈实际inventory/时间/结构化trace；无trace不画假图 | trace绑定合法Task/run ID后回原任务；路径和秘密在投影前脱敏；Web/Desktop摘要与trace；Mobile按Run查看；官网不公开日志 |

### 共用验收边界

- Web Workspace、Desktop App、Mobile Companion、Public Website 共享 Product Core、ViewModel、Actor、Scope、Source/Evidence、Task、Artifact 和版本语义；布局按端侧职责区别。官网仅呈现已验证公开能力或清楚标记的示例。
- 保留足够交互与可访问性；整体视觉依已批准研究、任务和屏幕合同，不固定二维或三维。手绘彩绘用于身份/对象图标及适合的页面元素；颜色有层次但不过量。人物服从用户脚本/描述，不复制参考人物。
- 研究进入决策或创作时继续携带同一Brief、来源、Evidence、scope、时间、预算约束和版本，不要求用户重复解释或重选资料；变化时定位影响范围、显式采用新版本、保留父版本和回滚。
- Intelligent UI 只改变呈现方式，不拥有数据真相、权限或效果执行。未知、未采集、过期、错误、拒绝和partial分别显示，不补零、不伪造成功。此映射不改变任一屏幕状态，也不自动批准 DESIGN_READY。

### 可编辑设计工程与源码同步 — 2026-10-08 审计增补

既有前端责任覆盖44屏基线、官网家族和四端完整范围；四表面按既有角色并行建设，各自独立验收，C6协调既有共享绑定。Website使用现有`website/`；Workspace/Desktop/Mobile共用Flutter `app/`与同一Product Core。已有真实API/Core立即接入，尚未具备的接口由原Owner接续并保持OPEN/UNBOUND。此为产品范围与来源责任，不表示任何窗口当前已派工或正在运行。保留可用的现有工程/Foundation/节点；无需Figma-first或等待逐屏DESIGN_READY后才编码，也不新增费用。批准依据：`00-GOVERNANCE/evidence/approvals/PO-20261011-WHOLE-PRODUCT-REUSE-EXPERIENCE.json`。

现有映射为 `Screen ID → 设计规格 → 可编辑载体/路径/版本 → Flutter Screen/Component → Repository/ViewModel/Action → Core/Permission → 测试/运行/Evidence`。Figma 保留 file/node/revision；源码载体保留 Dart/Token/SVG 路径、版本、编辑和预览方式，不能称为原生 Figma。工具受限单独记录；禁止 PNG、PPT、静态截图、假 .fig 替代完整可编辑交付，不重复创建设计文件或新增收费服务。Experience仍是唯一设计权威。

完整信息架构、组件/变量、全部44屏及官网家族直接通过可编辑源码和真实任务交互交付，不另立设计稿阶段；已有Flutter交互按其现有真实合同直接修复，不等待全部Figma页面完成。优先ACC-03、AI-01、CTH/BMP、SH-01/BMP-08、SYS-06接线，Golden Pages均为排序而非范围上限。整体视觉依已批准研究与任务；手绘彩绘用于图标及适合页面元素。保留四端、中英韩、主题、字号/宽度、可访问性与失败恢复。Figma或源码载体均给出真实可编辑路径/版本、原有ScreenSpec映射和缺口；截图仅辅助。主题复用LumenisTheme，官网Astro/CSS保持既定边界；真实Core/Permission/来源/保存/恢复与跨端验收不可由Widget测试替代。

每次设计修改必须定位受影响源组件/Token/动作、必要回归和回退版本，保留未修改工作、状态恢复、焦点和路由；不得为了重构巨型 Screen/Shell 或统一样式而重写业务。CTH事件因果边、ACC-03/04绑定登记及默认入口需分别核对，缺少关系数据或真实 callable 不能靠绘图宣告完成。

验收同时看真实输入、可信 Evidence、Core/ViewModel、用户操作、成果保存/重开/修订、失败恢复和 Evaluation。SOURCE / RUNTIME / DATABASE / TEST-CI / USER OUTCOME 独立记录；设计采用、实现存在与实际完成分开。工具链升级只改善研发环境，不能算寰意产品新增能力。

### 2026-10-08 有用分段与直接操作补充

应用唯一Experience §38“智能UI的逐步交付与组件选择合同”：本屏明确首个有用块、后续补充/更正、Task/run/输入与结果版本、可用组件及动作、保存回执和恢复。采用原组件保持稳定布局/焦点/选区，旧响应不覆盖用户编辑；事实和引用一致、缺值维度保留、纯文本可用。普通确定性操作不等待模型；按本屏任务决定是否需要动态UI，不能为了统一而套通用卡片。现有实现、设计及验收状态保留；逐屏设计评审记录只按实际评审更新，不构成编码前置，也不声明当前窗口派工状态。

2026-10-08 SYS-06 revision 5 retained a general computer/OS executor target as historical source material. The direct PO correction on 2026-10-11 withdrew general OS/computer control from product requirements. Preserve its code and evidence as history; current SYS-06 covers the controlled in-product browser, authorized page actions, human takeover/stop, task return and saved-result continuity. Its external-browser option is explicit. The withdrawn OS-executor target is not an active requirement or acceptance gate; the current browser acceptance status remains as recorded in its existing evidence.

## 2026-10-18 研究能力接续索引

原SH-01/02/04/05/06、AI-01/02/03、CTH-10、BMP-03/04已在各自合同内补充研究/资料/方案/行动/评价/学习交互与负例，参见唯一完整规划§1.3。这是同一原screen合同的增量，不新增页面权威，不接受GGI旧HTML。公共后端owner已交付实际routes与有界HTTP证据；仅未核实前端绑定OPEN，真实四表面NOT_VERIFIED。


## 全项规划核对与本地构建接续（2026-10-18）

本轮在原44屏内补足研究、统计、内容制作、会话、学习及系统工作面的具体控件、四表面层级、确认/取消/恢复与界面自身AIGC。唯一完整规划与空间草图仍为原链接；逐屏新增“全项具体工作合同”及同名工作面须与原章节一起实现，不替换原195G、R/J/U、非G、原创和200以上交互要求。Windows、macOS、Web、iOS分别取实机/构建证据，官网只承接公开说明与去敏演示。文稿覆盖不升级任何ScreenSpec实现状态，也不代表全产品或商用验收。先复核服务端身份/Permission、来源/版本及连接实际核验，再接各原Owner；当前长节目复盘、完整OAuth及其他未闭合事项保留原需求与明确缺口，不以有限实现缩写目标。

本轮专属工作面中的“UI自身AIGC仅可……”限定事实、权限、可执行动作和来源安全，不取消原创界面生成。原两条路径并行保留：按任务适配真实控件，以及生成原创、可编辑、可预览采用/撤销的视觉与空间构图；不得降格成固定模板换色或只做内容生成。原200以上交互、动效、物理要求与四表面分别验收仍完整，实际事实/安全字段始终用可核原生表达。用户可锁定、回到基础布局、减少动态，无AI仍完成正常工作。


## 44屏共同工作空间约束：舒展、直接继续、不缩功能

五个架构分工是产品内部能力、数据和Owner边界，不是用户完成一件事必须依次打开的五层页面。首页以“我想做什么/继续哪件工作”为入口：选择研究、写作、制作、经营或品牌问题后直接进入该任务的具体工作面，并带当前合法材料、已保存版本和可用上下文；不要求先选架构、再选模块、再重新录同一问题。必要主体/市场/执行范围在使用该动作时就地说明和选择；当前范围明确且仍获授权则复用，歧义或跨域采用须明确核对，不能靠少点一步绕过Permission或复制跨域数据。

工作面默认舒展：一个清楚的主要编辑/阅读区域、少量必要即时操作、可按需展开的上下文/依据。留白用于区分任务层级与当前焦点，不用巨大装饰把正文挤到屏外；有创意的非对称构成、尺度对比和阶段揭示围绕真实对象展开，不把每个字段塞进紧密小卡。现各专属合同的左/中/右描述是信息关系和宽度足够时的可选并读，不代表默认三栏全部常开；桌面也先保主工作舒展，用户决定何时并读。密集表格/多窗仅在当前任务确需且用户选择时展开，可回舒适阅读；不删除字段、功能或完整比较能力来换留白。200%字体、三语长文本、窄窗和键盘出现时仍可到达主操作。

跨能力继续工作优先就地展开或直接带上下文跳转并保返回锚点：来源旁记要点、结论回原文、错误直达需修输入、当前稿查看影响、通知回待决定处。返回不经过首页重新找对象，不重复要求已合法保存的输入；多个真实任务可各自保稿和版本，系统不会因切面自动停止任务或重新发送外部动作。现有路由/Owner缺接线时明确缺项并保原工作，不能用假浮窗模拟后端已完成。便利操作适用于所有能够复用同一真实合同的能力，不限随手记；当前有用的小巧思纳入既有Owner/本地前端实施范围，而不是减少原能力或再造一套快捷操作服务。

官网以工作故事、真实成果与可控演示舒展叙事，不把架构图当必经导航；Web和Windows/macOS保直接任务入口、原位置返回和用户选择的并读；iOS以一个主工作面、可逆Sheet与清楚回链呈现，不层层堆弹窗。底部便笺、加载小动作和AI表达不能遮挡原稿、重要错误或确认。界面自身AIGC可以提出符合当前任务的原创空间/视觉构图和交互呈现，采用前可预览，用户锁定/撤销有效；不复制参考品牌皮肤、人物或叙事，不把规则重排或静态插画冒实时生成。

验收用完整任务路径对照：从首页合法输入到首次有用编辑/阅读、跨来源核对后回原选区、转用成果而不重复录入、切任务再继续、失败后原位恢复。分别记录导航层数、返回/复制/重复输入次数、首个有用结果耗时、错误和工作丢失；未知未测不填漂亮数字。减步骤不能跳掉必要确认/证据，视觉舒展不能牺牲信息可找性；现仍是设计与接口合同，实际四端布局和可用性由本地同版构建验证。

本轮新增品牌视觉参考范围限定为Miu Miu、Prada、YEARPLAN、Le Labo、观夏及韩国品牌；韩国品牌先从已给参考核实，不自行扩大名单。已有视频/品牌产品研究继续复用，新的官方来源核验只补这个范围。关注布局、留白、字体、材质叙事和交互节奏如何服务真实工作，最终转化为寰意原创表达；未核官方页面/实际画面时只列待核，不能宣称研究完成或复制外观。此限定不阻塞已明确的舒展布局、直接继续和可逆交互合同；后续证据附回本章而非另建产品规划。

## 无需独立屏的要求仍须跨屏验收

审计中的“无需独立屏”只说明不另造页面，绝不表示没有前端要求或从验收排除。三语/无障碍/四表面（如G15/G16/G36/G58）映射各屏共同约束；范围与真实状态（如G8/G40/G89/G126）在相应现有工作面可见；用户成果（如G131/G132）保原成果展示与交接。其余工程/研究要求仍按原Owner、已有旅程及跨屏验收判断，不能因未新增屏而删除、标不适用或自动通过。
