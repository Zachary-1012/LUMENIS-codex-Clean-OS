# LUMENIS Screen Specifications

This folder holds the reviewed implementation specification for each canonical App screen. The 44 rows in `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md` §36 are distinct UX blueprints; they do not prove that routes, source fields, permissions, effects or acceptance behavior have been verified.

## Rules

- Follow the current authorization and actual live dispatch/admission state in root AGENTS.md and its local-ledger/tool-receipt evidence; each window is RUNNING only after fresh admission. This index defines screen-specification requirements and does not assign execution windows.
- Create one `<SCREEN-ID>.md` from [`SCREEN_SPEC_TEMPLATE.md`](SCREEN_SPEC_TEMPLATE.md) for each screen before implementing that screen. A file existing is not enough: M must review and record `DESIGN_READY` using the current user-selected model; no historical model assignment overrides that selection.
- Use `contracts/experience/lumenis_app_binding_registry.json` as the binding inventory. Update it only from current source/runtime evidence; never treat historical `BOUND`, task assignee or ViewModel labels as proof.
- Keep CTH Subject-first, BMP Brand/Market-first, Shared lineage and SYSTEM infrastructure boundaries intact.
- Do not copy screen layouts into a shared renderer. Shared tokens and semantic interaction primitives may be referenced, while each specification must define its own information hierarchy, composition and task choreography.
- `UNKNOWN` owner, callable, field source, actor scope, permission or evidence lineage blocks the dependent behavior. Record it as `DESIGN_EXPLORATION` if useful; never describe it as production-ready.
- PDFs, taskbooks, screenshots, wireframes, Figma frames, fixtures and generated visual proposals are non-authoritative references. List their disposition in the spec; never copy them directly or infer approval from visual polish.
- A repeated audit sketch frame does not authorize a shared renderer, universal card grid or substituted-title screen. Direct implementation without a current `DESIGN_READY` decision is `REWORK`.
- Set `APPROVED` only after the product owner or delegated design owner has reviewed the specification and its open questions. Record reviewer, date and the accepted change/review reference. A batch approval must list every covered screen ID and cannot silently approve unreviewed exceptions.
- Implementation, test and runtime status must cite current artifacts. A spec approval is not implementation acceptance.

## Status lifecycle

`DESIGN_EXPLORATION` → `OWNER_REVIEW` → `DESIGN_READY` → `IMPLEMENTED` → `ACCEPTED`

Use `BLOCKED` when a verified owner, contract, authorization or acceptance dependency is missing. `DESIGN_READY` is the only pre-implementation pass state. Do not skip states or infer status from code presence.

## Delivery order

After the overall product plan is accepted, resolve source bindings and detailed specifications for one end-to-end workflow slice at a time. Review distinct desktop and mobile compositions, then implement and accept that slice before starting dependent screens. Begin with the five proposed Golden Pages (AI-01, CTH-01, BMP-01, SH-01 and SYS-01) only when their bindings and user tasks are verified; this order does not override owner boundaries or authorize a generic shell.

## Intelligent UI 全屏语义映射（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

以下映射把 Intelligent UI 的任务适配方法落到既有 44 个 ScreenSpec。它是逐屏设计补充，不是第二设计权威；Owner、Binding、Permission、现有状态和未决问题仍以各规范及 Experience Constitution 为准。操作页不机械搬到公共官网；四个产品表面共享 Core/上下文和数据语义，但分别适配工作姿态。逐屏详情在对应文件末尾 `Intelligent UI 逐屏采用项（2026-10-08）`。

| 屏幕 | 用户任务 / 专属呈现 | 来源、版本与端侧动线 |
|---|---|---|
| [ACC-01](ACC-01.md) | 确认内部工作区入口可用并继续宿主指定目标；显示入口状态与宿主提供的继续动作；无 callback 不伪造路由或账户流程 | 传递宿主实际 route 与原任务位置，失败时保留入口；Web接浏览器route；Desktop回原窗口；Mobile恢复原任务；官网只说明公开入口 |
| [ACC-02](ACC-02.md) | 查看当前GLOBAL_ALL或明确选择一个可访问Subject视角；列表、当前视角和确认预览并置；说明选择不授予业务读取权限 | 只有服务端确认的scope envelope传递给下游，切换后回原工作；Web/Desktop提供目录与预览；Mobile逐项选择；官网不展示私有目录 |
| [ACC-03](ACC-03.md) | 从首页开始真实工作或继续原任务；以任务、草稿、已访问页面和既有工作流组织，不做KPI营销模板 | 恢复Task/Brief/scope/Artifact版本，建议只开草稿不触发效果；Web多区并读；Desktop快捷续接；Mobile突出一个待续任务；官网只作公开介绍 |
| [ACC-04](ACC-04.md) | 理解一项真实阻断并沿已有恢复路径返回；展示发生了什么、影响哪个任务、已绑定的恢复路径 | 关联原Task、请求scope、operation与恢复receipt，保留未提交内容；Web/Desktop并列工作与受控说明；Mobile按阻断→影响→恢复；官网不显示内部诊断 |
| [AI-01](AI-01.md) | 把用户目标、当前资料与约束组成可检查的执行意图；自然语言目标与现有Brief/Evidence/scope/Budget/缺项并列；建议可编辑拒绝 | 沿用同一Task/Brief/引用/Actor/scope；真实结果返回execution ID及Evidence状态；Web/Desktop并看输入与资料；Mobile逐项确认；官网仅公开且标注示例 |
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
| [BMP-08](BMP-08.md) | 把授权来源变成可审阅脚本及可编辑播客音轨；脚本、来源、rights、音轨和发布状态分层；横向拖动时间轴 | 同Brief/来源/audio version连续；本地Read Aloud不等于成片；Web/Desktop脚本与音轨并列；Mobile分段查看；官网只放授权成片 |
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
| [SH-01](SH-01.md) | 发现共享能力并进入当前研究/创作/媒体工作；当前Task→已绑定能力→原生Reader/编辑器；Timeline/ShotPlan保留专用工作区 | 沿用Brief/SourceTarget/Evidence/Artifact/timeline版本，目录本身不执行；Web/Desktop承担并读与复杂编辑；Mobile任务摘要后打开素材；官网只列已证能力 |
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
- 保留足够交互、序境二维手绘/水彩/版画视觉与可访问性；颜色有层次但不过量。创作人物服从用户脚本/描述，只借鉴手绘平面感觉，不复制参考人物，不采用3D AI质感。
- 研究进入决策或创作时继续携带同一Brief、来源、Evidence、scope、时间、预算约束和版本，不要求用户重复解释或重选资料；变化时定位影响范围、显式采用新版本、保留父版本和回滚。
- Intelligent UI 只改变呈现方式，不拥有数据真相、权限或效果执行。未知、未采集、过期、错误、拒绝和partial分别显示，不补零、不伪造成功。此映射不改变任一屏幕状态，也不自动批准 DESIGN_READY。

### 可编辑设计工程与源码同步 — 2026-10-08 审计增补

既有 F 负责全部 44 屏与官网内容家族的可编辑设计工程，M 负责审查，C1-C6 提供真实字段/动作/状态合同，C6 协调共享绑定。执行须等 Product Owner 确认；本轮 M 更新规则和工具链不恢复任何其他窗口。

在现有 ScreenSpec/README 保存 `Screen ID → 设计规格 → Figma file/node/revision → Flutter Screen/Component → Repository/ViewModel/Action → Core/Permission → 测试/运行/Evidence` 的映射，不建第二设计注册表或权威。Figma 是开发设计资产，唯一 Experience Constitution 和既有 Product Core 真相不变；无访问时保留 NOT_VERIFIED/BLOCKED，禁止用 PNG 或伪造 .fig 冒充。优先复用获授权现有工程；新建工程须必要访问与 PO 认可。

先补完整信息架构、组件/变量关系和当前真实状态，再沿五个 Golden Pages（AI-01、CTH-01、BMP-01、SH-01、SYS-01）与业务依赖推进高保真和实现，不削减其余页面。全部 44 屏及官网家族保留四端适配、中英韩、明暗主题、字号/宽度、可访问性与完整失败恢复；Figma 使用可编辑 Components/Variants/Variables/Auto Layout/Prototype。主题尽量映射既有 LumenisTheme，Website Astro/CSS只共享语义设计决策。

每次设计修改必须定位受影响源组件/Token/动作、必要回归和回退版本，保留未修改工作、状态恢复、焦点和路由；不得为了重构巨型 Screen/Shell 或统一样式而重写业务。CTH事件因果边、ACC-03/04绑定登记及默认入口需分别核对，缺少关系数据或真实 callable 不能靠绘图宣告完成。

验收同时看真实输入、可信 Evidence、Core/ViewModel、用户操作、成果保存/重开/修订、失败恢复和 Evaluation。SOURCE / RUNTIME / DATABASE / TEST-CI / USER OUTCOME 独立记录；设计采用、实现存在与实际完成分开。工具链升级只改善研发环境，不能算序境产品新增能力。

### 2026-10-08 有用分段与直接操作补充

应用唯一Experience §38“智能UI的逐步交付与组件选择合同”：本屏明确首个有用块、后续补充/更正、Task/run/输入与结果版本、可用组件及动作、保存回执和恢复。采用原组件保持稳定布局/焦点/选区，旧响应不覆盖用户编辑；事实和引用一致、缺值维度保留、纯文本可用。普通确定性操作不等待模型；按本屏任务决定是否需要动态UI，不能为了统一而套通用卡片。状态仍为原实现/设计状态，新增设计待本屏审阅，未派工。
