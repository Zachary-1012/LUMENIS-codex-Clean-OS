# LUMENIS Product Architecture — CURRENT

## 五轮架构产品闭环 — 2026-10-09 Product Owner 直接批准

这是唯一产品交付轮次；C1–C6/W1–W6 是保留的工程源码职责，不是六轮产品交付，
不构成单业务窗口限制或额外产品阶段。五轮也不新增五个 Codex 窗口。

| 产品轮次 | 完整成果 | 保留的工程责任协作 |
| --- | --- | --- |
| 第一轮 SYSTEM | Core、Collector、Browser、Scheduler、DB、Evidence、Permission、Runtime 与恢复完整闭环 | C1/C2/C6 原源码责任，F 的实际界面；M 审阅与集成裁决 |
| 第二轮 CTH | 商业主体监测、分析、事件、风险、决策、行动、结果及报告完整闭环 | C3 业务规则，按原合同消费 C1/C2/C5/C6 和 F |
| 第三轮 BMP | 品牌、市场、竞品、创作者、传播、Campaign、执行及评价完整闭环 | C3 业务规则，按原合同消费 C1/C2/C4/C5/C6 和 F |
| 第四轮 Shared | 真实资料导入、研究、提案、视频、播客、Artifact、版本、导出及评价完整闭环 | C4/C5 原制作与资料责任，C1/C2/C3/C6/F 按原边界协作 |
| 第五轮 Agent Groups / 自研 AI | 在唯一 AI Gateway 与 Agent Runtime 内完成智能增强，并关闭四入口跨领域集成与最终产品验收 | C2 智能责任，C1/C3/C4/C5/C6/F 按原合同集成；M 验收 |

每轮退出必须有真实用户操作、实际有用成果、保存/修订、重开/恢复、来源与权限核验、
适用的真正产品 E2E；适用 Outcome/Evaluation、三层 Gate 和最终 PO 重复操作保留。
当前轮的跨域必要依赖必须在当前轮修复，不能以工程 Owner 或后轮名义延期。
四入口继续指 CTH、BMP、Shared、SYSTEM，不把 Agent Groups 变成第五个产品入口。
基本业务先证明无 AI 正常链，智能增强收益单独证明；前四轮的可选 AI 缺失不能阻断基础任务，
第五轮既定智能要求仍须真实兑现，不能借 AI 可选原则取消。

保留 J1–J8、R01–R15、U01–U25、44 屏及原资料/设计/历史证据全部要求。
Website / Web Workspace 实际业务优先；Windows/macOS Desktop 与 iOS Companion
专项验收后续完成，不以本次文档提交宣称 SYSTEM、原生端或全产品闭环。
不新增费用、账号、模型服务、训练或部署；禁止单元/集成及换名模块套件，
保留编译、静态、安全、数据一致性与真实用户 E2E。

Product Owner decides actual window start, pause, resume, model and reasoning effort.
GitHub and local CURRENT files record verified observations only; every observation
includes its verification time and evidence source. Unknown window/model/effort is
`NOT_VERIFIED`, never inferred from historical PAUSED/RUNNING, resume conditions,
role defaults or configuration. The existing live ledger is a factual continuity
record, not an autonomous dispatcher. A current direct PO instruction is required
for scheduling; publishing this rule starts no window. Owner, Permission, source
rights, data, cost, shared-write reservations and real acceptance remain binding.


> Status: **CANONICAL / SOLE PRODUCT ARCHITECTURE AUTHORITY**
> Product Owner approved blueprint: 2026-10-04
> Scope: CTH / BMP / Shared / SYSTEM; one product, four surfaces.

AGENTS.md is the only repository execution router. This file is the sole product
blueprint. Experience Constitution owns UI/UX; Source Owner Index maps existing
code and complete outcomes. Reports and historical directives cannot compete
with these named authorities. Approval defines the required end state, not proof
that every capability is implemented or accepted.

ONE Product / ONE Repository / ONE main / ONE Production Truth / ONE Product Core
/ ONE Canonical Data / ONE Evidence / ONE Permission / ONE Runtime / ONE Collector
/ ONE Browser Runtime / ONE AI Gateway / ONE Agent Runtime / ONE Reporting System
/ ONE Evaluation System / ONE Learning System / ONE Design Authority.

This is the retained **Only One / All-in** architecture: CTH is Subject-first;
BMP is Brand-first / Primary Focus, with Brand/Market-first business work. The
Shared Capability Layer serves both domains. Agent Groups coordinate through
the existing Agent Runtime and never become another business or security owner.

**Multi-surface product direction:** Public Website, Flutter Web Workspace,
Desktop on Windows/macOS, and Mobile on iOS share the same Core.
Platform availability and acceptance are verified separately from this target.

2026-10-08 最新 PO 顺序：优先闭环 Public Website + Web Workspace；Desktop App/Mobile Companion 专项实现、打包与实机验收后置至前两端闭环以后。保留全部四端/44屏/官网家族及 R/J/U 能力，不删旧成果、不将后置项记为通过。当前 Web 所需业务与 Core/SYSTEM 能力仍完整推进，沿既有 Owner/Permission/Evidence 与真实保存、修改、重开、恢复、评价链验收。既有三层 Gate 按本轮表面记录，四端完整 Goal/Release 不因本轮完成自动关闭。具体表面边界见 Multi-Surface Decision；零新增费用不变；实际窗口由PO决定，不再固定单业务窗口拓扑。


## 2026-10-09 AI 非依赖原则与分层验收

序境所有基础业务能力在无模型、无外部 AI API、无 GPU、无推理服务时，仍须完成正常任务。AI 只增强效率、理解、建议、生成及辅助决策，不生产事实，不拥有 Canonical Data，不是核心业务链必经条件。AI 专属动作缺模型可准确标为 UNAVAILABLE，不能因此阻断普通任务。安全/权限拒绝、来源权益失效和真实输入缺失仍是有效阻塞，不能伪造或绕过。

| 领域 | 无 AI 必须完成的基础任务 | 可选 AI 增强 |
| --- | --- | --- |
| C1 数据采集 | 真实采集、来源记录、去重、入库、刷新、恢复 | 页面理解和提取辅助 |
| CTH | 监测、指标计算、事件、风险规则、人工判断记录、报告 | 解释、趋势推断、建议 |
| BMP | 品牌资料、传播分析、竞品比较、Campaign 管理 | 创意、洞察、方案辅助 |
| Shared 研究 | 导入、检索、引用、归档、人工研究、导出 | 语义检索、摘要、关联 |
| 提案/视频/播客 | 人工编写编辑、素材处理、播放、渲染、保存、导出 | 生成、转写、剪辑建议 |
| Browser/Computer | 确定性操作、人工接管、文件处理、恢复 | 自主规划、智能 GUI |
| SYSTEM | 权限、调度、数据库、运行恢复、安全 | 异常分析、修复建议 |

第一优先：真实来源→规范数据→确定性计算/人工操作→有用成果→保存/修订/重开/恢复。第二优先：以同一真实任务证实 AI 增益。第三优先：另获许可的数据、训练、评估和晋升。保留全部批准的增强范围，不把其未完成记作已完成；不能借模型缺失延迟基础任务。现有 REAL DELIVERY CARD 分别记录 no-AI 基础结果和 AI 增强状态，不新增验收体系或第二执行合同。

A0/B0/C0 V2 本轮仅准入准备：外部模型条款/默认关闭设计审阅、数据卡与上游/Teacher 权利审阅、自研 AI 现状及非 AI 任务断点核查。A1 外部 API、B1 数据下载导入、B2 训练及模型部署各需独立授权。包内 C1 RUNNING 与旧暂停回执均为有日期的历史快照，不决定当前开工。A0 方案编号不表示 Agent Zero，也不表示 C1 业务窗口。待核实的 analysis_agent 全任务失败不能靠改状态或规则文字冒称修复。

### 当前语义与兼容边界（2026-10-07 校准）

2026-10-08 PO定向DDD增补：仅对当前真实任务的名称/身份冲突、规则重复矛盾、跨模块映射错误、旧调用越界、状态/结果/来源传递丢失，采用统一领域语言、既有CTH/BMP/Shared/SYSTEM限界上下文及现有接口上下文映射。Subject、BrandFocus、Source、Evidence、Brief、Artifact、Outcome在各当前上下文保持既定含义/身份/状态/行为；兼容名称由原解析器转换，不全仓重命名、迁库或新建统一对象模型。业务规则与状态变更归现有Owner，Flutter/API Controller/DB工具只是调用方。正常代码不因形式重构。

Collector→Canonical→CTH/BMP→SourceBrief→SavedWork/Content Project→Evaluation沿既有合同传递身份、权限、来源用途、状态、版本及错误，不让下游猜测；只修真实受影响调用/适配层。当前实际获准的对应源码Owner完成具体问题修复、正常操作恢复、跨界正向/越界回归和原功能保持；M只处理跨Owner冲突及成果验收，F独立消费真实合同。保留原三层Gate；不新建DDD阶段、审计窗口、框架或验收体系。不能直接改善当前结果正确性、可用性或效率的调整按既有规则DEFER。

本节澄清已有产品定义，不迁移存储 ID、增加 Owner 或改变机器治理合同。

| 概念 | 当前含义 | 兼容与禁止混用 |
|---|---|---|
| 序境 / LUMENIS | 一个产品 | ZBC、Z-Brand-Core、母平台等旧命名不得成为当前用户可见产品层级；旧仓库/包/环境变量名按调用方保留 |
| CTH / BMP | 商业运营域 / 品牌市场域 | `PRODUCT_CTH`、`PRODUCT_ZBMP`、`product_id=CTH/ZBMP` 和 `domain_id=cth/zbmp` 是现存技术合同；`product_id` 字段名不意味着两个产品 |
| Subject / BrandFocus | 商业主体上下文 / 品牌聚焦上下文 | 不互作别名，不从名字、页面或 Context 推导 Permission；同名主体、城市、门店、时间分别绑定 |
| GLOBAL / ALL | 默认未聚焦的获准全域工作范围 | 不等于隐式广州太古汇，不等于无限权限或全球数据已齐全；Clear 保留历史成果的原范围 |
| Source / Evidence / Canonical | 来源、可定位且带出处的证据、经当前合同接收的规范事实 | 研究笔记、AI 输出、缓存、文件存在、mock、旧报告不能自行升级为 Production Truth |
| Metric / Truth Table / ViewModel | 按明确单位/分母/时间口径计算及表达事实 | `0` 是已知数值，`UNKNOWN`/缺测不是零；ViewModel 不创建另一份业务真相 |
| Product AI | 单一 SYSTEM Owned AI Gateway 及获准绑定的执行版本 | Codex/Astra/Sol/Luna 是工程资源；兼容 Provider 注册和状态枚举不证明产品推理可用或允许 fallback |
| 四 Surface | Public Website / Web Workspace / Desktop / Mobile Companion | Desktop App 是 Desktop 的描述性名称；Flutter 是实现技术；历史 APP ONLY/Web-only 不再决定产品范围 |

状态必须随其已有 Owner/字段解释：例如 `query_plan.status=READY` 只说明查询计划可提交，
不证明平台 Session 已就绪；`collector_guard=NEED_VERIFY` 是平台验证挑战，旧
`cookie_status=NEED_VERIFY` 仅表示认证元数据还未验证连通。报告、API 组合与界面必须保留
已有字段名、reason、时间和范围，不能把不同来源状态合并成一个无限定的“已就绪/已验证”。
这里只规定解释与呈现，不新增通用状态服务，不批量改枚举或历史数据。

`PUBLISHED_STATE` 与 `LIVE_DISPATCH`、`ELIGIBLE` 与 `RUNNING`、`VERIFIED` 与
`JOB_CLOSED`、`JOB_CLOSED` 与 `RELEASED`、`RELEASED` 与 `OPERATING` 分别独立。
治理状态的机器语义继续由 Governance Machine v1.2.0 定义；采集、队列、AI 与数据状态
继续由其已有源码/合同定义。发现冲突应修相应边界，不能把某一领域枚举复制为全产品状态权威。

逐项源码证据、兼容词及尚待行为修复项见
[Semantic Calibration Ledger](evidence/round-15/SEMANTIC-CALIBRATION-20261007.md)。
该清单是本蓝图及现有合同的索引，不是第二份语义权威。当前域边界严格拒绝未知值和
矛盾标识；BMP/zbmp 只在已批准的兼容边界归一为 ZBMP/zbmp，不改历史存储 ID。
无选择保持 GLOBAL / ALL，明确 CTH 只选择业务域，不暗中选择广州参考主体。机器环境
不能覆盖请求；跨域与 Subject 权限仍由原 Permission/registry owner 核实。旧参考过滤器
只承担明确的历史参考用途，不能为 GLOBAL 或其他商业体生成参考主体结果。

研究方法须通过现有产品输入、处理、校验与成果路径采用。冻结业务命题/约束与独立
反例后验证实际实现；人工纠正保留来源和生命周期，仅获准晋升的学习记录进入提示上下文。
OpenAI Math/Lean/Comparator 是方法来源，不构成序境已获形式化证明、商业因果或训练授权。
具体实现、证据和未验证运行范围见同一语义清单及 Math 采用记录。

Latest PO: F builds real frontend directly from current Experience, screen contracts and source; no separate design draft, Figma completion or M DESIGN_READY approval is a coding prerequisite. Update existing specifications alongside code. Existing design artifacts and review states remain provenance, not proof of implementation. Do not authorize implementation from a PDF, screenshot, fixture, Figma frame or a generic swapped-title renderer alone; the current contracts and direct PO construction instruction govern. Website/Web closes first, then native Windows/macOS and iOS only. Android/Linux native clients are no longer delivery targets; preserve historical source/evidence. Linux server/CI and browser access remain separate. Preserve all other current capabilities and acceptance requirements.

一、闭环后，用户实际得到什么

用户在序境提出一个商业或品牌任务，提供目标、主体、市场、时间、预算与已有资料。序境能理解文件和材料，补充授权范围内的真实数据，形成有依据的判断与可执行方案，接着制作文稿、视频或播客。用户改变预算、来源或创作要求时，系统定位受影响部分、提出修改、经确认后应用，保留旧版、修改原因与可回滚关系。用户可以保存、关闭、换端、重开和在中断后继续，不必重述目标或重新选择同一批材料。

**Platform-native Source → Source/Evidence/Canonical → LUMENIS presentation → Open Original → Return** 是同一产品闭环。平台内容被正式接收后，序境保留原生正文、作者、来源平台、原始 URL/locator、发布时间、采集时间、原生指标、许可与 Evidence lineage，但用户看到的是按 CTH/BMP 任务语义和 LUMENIS Experience 重新组织的呈现，不复制来源平台 Feed、视觉外壳、无限滑动或自动播放。获准用户可从记录、事件、趋势、案例、风险、报告或创作引用中点击“查看原贴 / Open Original”，默认把经过校验的公开 HTTPS 目标放在序境内置受控浏览器中，用户也可明确选择外部浏览器，并在返回时恢复原任务、GLOBAL/FOCUS、筛选、选中对象和滚动位置。普通原贴跳转不读取本地 Cookie、不静默登录、不启动采集、不生成新 Evidence、不发布也不写外部状态；受控网页导航与证据捕获继续只归 SYS-06。

示例一：广州太古汇活动策划。用户输入客群、活动周期和预算；系统限定该场所及场内品牌关系，区分品牌自述、消费者讨论、媒体报道和广告，给出依据与不确定性，形成活动方案、预算分配、文稿、视频与播客任务。预算变更后只修相应方案、镜头或音频内容，保留来源与旧成果。销售、客流、满意率或真实活动效果没有数据时，不能编造。

示例二：Nike或Le Labo品牌任务。选定市场、城市和时间范围后，系统把竞争品牌、消费者讨论、内容传播、渠道和商业主体关系放在可比较口径下，形成研究、Brief与可编辑作品。跨城市、币种和统计期间不直接混排；平台热榜、序境样本热点和用户偏好推荐分别解释。

示例三：来源更正。某来源撤回或被纠错，序境能定位引用它的判断、报告、文稿、镜头和节目段落，展示影响，要求明确采用新版后修订，保存旧版和原因。原始Evidence不被新结论覆盖。

### 全产品智能交互蓝图（2026-10-08）

用户应能在任何现有工作环节直接理解结果并继续操作：从采集原始材料、研究比较、判断与方案，到提案/视频/播客的编辑、版本修订、保存、跨端恢复以及运行问题处理，交互始终由真实任务和当前资料决定。智能UI不是一个独立模块，也不局限在AI聊天页；全44屏及官网已有内容家族逐项适配，功能范围保持现有J1–J8/U要求。

```text
同一用户目标与获准材料
  → 现有Core返回事实、范围、来源/版本、可用动作与诚实状态
  → 当前屏幕选择合适的文字/对照/图形/表单/阅读器/编辑画布/时间轴
  → 用户直接筛选、比较、调整或修改，并可回看依据
  → 现有Owner验证权限与版本，计算影响并显示差异
  → 明确采用 → 保存新成果/父版本 → 重开、跨端接续、撤销/恢复
  → 真实Outcome/Evaluation反馈到现有能力改进
```

例如商业体比较能检查城市与时间口径；活动预算调整能看到受影响段落和镜头；媒体编辑能在同一来源/脚本/时间轴中定位并只改选中部分；来源撤回能定位对应结论；采集/模型不可用时能理解缺口并继续不依赖它的工作。设置、通知、任务状态和恢复入口也按实际动作与返回关系设计。模型只提出有依据的解释/方案，UI和AI都不创造事实、权限或外部效果。

唯一Experience §38细化八项要求与验收；44屏在既有screen-specifications中明确各自任务和视觉动线，既有文字草图同步增补，四端角色见Multi-Surface Decision。保留二维手绘水彩、丰富且有用的交互、中英韩与无障碍、操作端避免不必要整页滚动。该蓝图定义闭环目标，不能据此把规则更新等同功能已上线或屏幕已验收。

二、锁定的产品组成

CTH：商业主体运营。覆盖场所、场内品牌/业态、事件、消费者反馈、风险、案例、运营决策、活动和结果评价。广州太古汇、深圳罗湖万象城用于代表性深度验收，不是产品默认范围。

BMP：品牌与市场。覆盖品牌、市场、竞品、消费者、创作者、传播、内容与Campaign。Nike、Le Labo用于代表性验收，不是品牌目录上限。

Shared Capability：资料导入与研究、引用、内容创作、文稿/视频/播客、Artifact与导出、评价和学习。CTH/BMP调用这些能力，业务语义仍归各自领域。

SYSTEM：采集、产品浏览器、Scheduler、AI Gateway、Agent/Skills/Memory、数据库、Permission/Action Firewall/Effect Fence、配置、运行恢复和可观测。各能力沿已有Owner升级，不再增加平行的采集器、数据库、模型网关、权限或设计系统。

默认工作范围保留GLOBAL / ALL。进入具体商业或品牌工作时，明确选取相应Subject或BrandFocus；Clear只清当前聚焦，不抹去已保存任务的范围、权限与历史。

三、四个入口的闭环形态

| 入口 | 用户用途 | 必须接通 | 保留的边界 |
|---|---|---|---|
| Public Website 官网 | 理解产品、查看真实能力与操作演示、进入工作区、帮助/联系 | 文字、交互、可控操作视频、真实可用入口；中英韩内容 | Cue为官网视觉与节奏主参考，319b视频仅用于官网；演示必须标明范围，不拥有业务数据或权限 |
| Web Workspace | 浏览器中完成研究、方案、制作、审阅与继续工作 | 同一Core、资料、任务、版本、引用、编辑和恢复 | 采用现有Flutter Web；不能把旧Jinja/static界面重新当第二产品 |
| Desktop App | 本地媒体处理、专业编辑、文件操作与高级工作 | 同一任务和版本；视频/播客真实播放器、横向时间轴、导出、重开恢复 | 不另建业务数据库；本机工具能力与服务器能力分别反馈 |
| Mobile Companion | 查看、审阅、批准、轻操作、通知与任务接续 | 真实任务/成果/版本、适配触控、返回路径与权限 | 按移动任务重组，不缩小PC界面，也不冒称所有桌面重计算能力已在手机运行 |

四端共同遵守：原创二维手绘水彩/版画纸感；线性功能glyph、彩绘对象identity icon、第三方来源icon分层；颜色丰富但不滥用；人物根据脚本或描述生成；合理的AIGC呈现按任务设计，不使用助手虚构的70–80%/20–30%固定配额。除官网外避免无必要的整页纵向滚动，必要长文和无障碍操作不被截断。增加有用交互，不做换标题的模板页。

产品账号重设计、实时对话语音、开发者模式仍按已明确后置范围保留。当前开放产品入口，不加新的登录/升级墙；服务端权限、平台授权和效果控制继续执行。

四、完整能力覆盖与可验收出口

| 工作包 | 已有能力范围 | 闭环必须出现的真实结果 |
|---|---|---|
| J1 数据建设 | 中国优秀/小众品牌和商业主体优先，既有国家候选、关系、别名、时间、市场分类 | 新增主体可使用；关系有Evidence；六主平台真实单帖被正式接收；刷新/增量/恢复独立运行 |
| J2 商业运营 | CTH监测、事件、日历、消费者与风险、Case/Insight/Decision | 正确范围下产生可操作方案，授权动作与真实结果可追踪，结果可保存、反馈和评价 |
| J3 品牌市场 | BMP市场、竞品、消费者、创作者、内容、传播、Campaign | 真实可比研究进入既有 SH-01 Discover：按主体、平台和时间解释趋势、热点与相似作品，再接入 Brief/活动方案和制作；实际行动与未知效果分开 |
| J4 原创提案 | 文档读取、资料理解、策略/概念、预算资源与Word等交付 | 用户可编辑和交付的提案，来源正确、理由清楚、可修订、导出、重开和回滚 |
| J5 视频 | 素材、分镜、轨道、音频字幕、转场、预览、局部替换、渲染 | 真正新成片与可编辑项目；时间轴滚动/缩放/seek同步；保存、恢复、缺媒体处理成立 |
| J6 播客 | 研究、脚本、采访/叙事、音频、转写、段落章节、混音 | 可听节目和完整工程；实际试听、语言与音量质量通过；局部修订不破坏其他段落 |
| J7 资料与自有AI | 导入、检索、精确引用、多模态、现有 SH-01 Discover、Gateway、Agent/Skills/Memory、学习评价 | Discover 的趋势、热点和相似作品分析有来源、范围、时间与相关性说明；自有AI能基于已授权的产品资料为用户的创作/方案给出可追溯建议、备选与理由，并进入既有Brief/成果保存修订链；已批准权重训练、重载、独立评价、晋升/回滚有实际证据 |
| J8 跨端与运行 | 四入口、Core、FFmpeg/ffprobe、进程、DB、配置、通知、打包发布 | 同版本任务在目标端可用，重启/取消/授权撤销/回滚可恢复，离开Codex也能持续运行 |

上述工作包完整保留现有U01–U25：全局主体；精确关系；总部/发源/市场/所在地；采集；历史指标/新鲜度；事件日历；消费者与趋势；风险；运营决策；品牌市场；创作者与传播；Campaign；提案；视频；播客；资料库与引用；报告/Artifact；自有AI；Agent/Skills/Memory；评价与学习；产品浏览器；开放入口与权限；四端；设置偏好通知；运行安全发布。

R01–R15仅作为保留的验收依赖，不再成为另一套派工日程。C1–C6仍承担数据、自有AI、业务、制作、资料共享、运行整合六个完整成果，F独立负责四端。这里未新增第七轮、隐藏窗口或新产品。

五、研究资料如何成为产品能力基石

资料不以“已保存/有摘要/进入训练集”作为完成。每项采用必须进入一个已有能力，产生规则、处理逻辑、质量标准或交互行为，并在真实任务中验证。原件、已读范围、版本与许可单独保留。

| 既有研究 | 直接改善的能力 | 落地位置与结果 |
|---|---|---|
| 采集OSS、公开来源方法、词条种子 | 精确查找、详情/评论/媒体提取、时间与去重、持续刷新 | C1 Collector/registry/Scheduler；采集回答业务问题；用户100词/41源按版本扩充，不伪造热榜 |
| 传播/新闻/网络传播、广告商业与品牌案例 | 事实核验、来源角色、框架/议程、替代解释、代表性和因果判断 | C3/C5研究/业务服务及C2评价；报告对判断给依据、反例和适用范围 |
| 广告法与行业规范 | 广告识别、事实主张、地区/条件/时效、引用校正 | C3/C4/C5现有决策、内容和Evidence边界；提示实质风险，不把模型输出称法律裁决 |
| SNU课程与教材 | 研究设计、分析方法、创作训练和评价尺度 | 现有研究/创作/Evaluation；课程目录、已读教材、未读材料分开，不由课纲推断整课已掌握 |
| OpenAI/Codex/ChatGPT/Claude/Muse资料 | 目标执行、恢复、上下文、工具身份、结构输出、多模态质量 | C2 Gateway/Agent/Skills/Memory与C6运行；不替代序境Permission/Evidence/效果Owner |
| Baseten推理工程 | 模型加载、资源与延迟、传输/缓存、成本、恢复 | C2/C6现有运行；实际计量与恢复结果，不把书名或安装成功当推理能力 |
| 剪辑/视听/V2、音频与中英韩/音乐情绪资料 | 镜头节奏、视听关系、节目结构、音频理解和专业编辑 | C4 Timeline/render/podcast及F真实编辑；真看真听，保留位置与来源 |
| 前端视频与Cue/Manus/OpenAI官方页面 | 任务入口、对象身份、操作叙事、可逆交互、状态恢复 | F现有屏幕、官网及Experience规范；逐帧阅读与帧提取分开，不套厂商模板 |
| Source连续性与局部修订 | 同源资料跨研究/制作/业务消费，错误影响定位 | C5 SavedWork/Artifact、C3领域消费者、C4制作；显式采用版本，保留原件和回滚 |

研究阅读用于产品方法，并不自动授予全文再分发或模型训练许可。训练材料另走现有批准流程；已许可资料的正常产品使用不能被错误地要求先完成模型训练。

六、当前唯一执行方式

1. AGENTS保留唯一执行路由，去掉重复总纲、过时暂停/恢复日志和固定历史机器指令。CURRENT只保留当前事实及接续位置。
2. 本文件是唯一产品蓝图，外部审阅稿仅保留为批准依据，不是另一个执行入口。
3. Source Owner Index只记录每项能力的源码、调用方、共享输入、成果出口和当前缺口。Experience、Permission/Evidence、DB/API是各自专业合同，不再次定义总产品或总执行顺序。
4. 已有有效实现直接合入对应主源码；一个能力只保留一个当前实现、一张当前完整任务卡和一份当前交付记录。停止建立平行候选源码目录和重复研究矩阵。
5. 对历史副本，先比较独有差异。完全被主线替代的代码副本退出工作入口、保留固定提交/哈希回执；未合入的有效代码先并入主实现；原件、模型版本、Artifact历史、数据库备份与失败证据不混作可删候选。
6. 遇到已知问题，直接沿确定的Owner/调用点修复。需要新技术依据时做一次针对性官方/GitHub研究，选择方法后执行。必要回归只验证改动风险和最终结果，不以反复测试、对照表或候选数量充当进度。
7. 真实依赖按合同直接衔接；共享写入由当轮唯一集成人协调。完成一个用户成果后同轮提交源码、文档状态与证据，验证remote main及实际运行加载一致。其他成果不等无关GPU、全目录或全量阅读。

七、优先完成能力的执行顺序

P0执行入口裁决已经收敛，不再作为单独待办批次：`AGENTS.md` 是唯一执行路由；本蓝图是唯一产品蓝图；Source Owner Index 只负责定位，CURRENT 只记当下事实。`README.md` 的四入口说明以当前源码校准：Public Website 承载官网，Flutter 同源承载 Web Workspace/Desktop/Mobile 并共用 Core。source-bound/v3 是当前新增来源绑定合同，v1/v2 仅作兼容；业务数据使用 canonical 数据库，符合 §9 条件的 SYSTEM 操作队列是受限例外；历史APP ONLY、旧双库/资料删除规则、旧硬编码全盘扫描脚本及过时 locator 路由/候选状态只作有固定版本的历史证据，不能重新成为执行入口。现行能力 locator 继续按本任务词和 Source Owner Index 路由。发现新的当前源码冲突时，直接修正对应所有者文件并与该成果同轮发布，不新建平行规则或审计队列。

第一批：正式资料/采集→研究→source-bound创作→CTH/BMP使用。沿现主线已接通的v3继续使用真实许可材料、正式refs与范围，闭合用户可用内容、保存、修订、重开和Evaluation。把20项已经在main的集成文件从“待合候选”工作入口退出。

第二批：视频与播客完整正常路径。合并仍在本地的必要媒体实现，解决播放、横向时间轴、实际渲染/试听、版本与Artifact绑定。与F完成对应端的实际操作；不等待自有训练先验证确定性的编辑和恢复。

独立能力链：自有AI实际训练与服务；按五轮架构及必要依赖落实，实际窗口由PO决定，不设固定业务席位。现有/免费资源优先，许可允许的基础权重、自有训练部署、实际step/loss/checkpoint/重载/独立语义评价。以真实CTH/BMP/创作结果验收；Codex Cloud和免费临时GPU不冒充上线推理服务。开发电脑关闭、Codex停止、外部模型API禁用时，承诺的产品运行必须由序境自有运行环境完成；部署与资源可用性要实际证明。

第三批：跨端统一运行与发布。一个同版本成果在承诺的四入口衔接；不要求四端相同布局。验证启动/崩溃/取消/撤权/重试/重开/恢复，完成同SHA Product/App门禁、备份回滚与打包。工程可用后由你重复完成核心任务，记录耗时、成本、正确性、修改成本与人工补救。

此顺序按五轮架构成果及真实依赖推进，窗口调度由PO决定；不要求先完成全部中国/全球目录才验证业务，也不能用几个代表性任务冒充覆盖完成。



## Technical owner and compatibility contracts

## 6. AI / Skill / Agent

Current provider and engineering roles (2026-10-01/02):

- lumenis/system/ai_gateway/ remains the sole SYSTEM owner. C2 supplies approved
  commercially usable open foundation weights, owned training/inference and
  held-out business evaluation; existing/free resources first. Codex Cloud
  configuration is not proof of production inference or free GPU capacity.
- Ollama/LM Studio/llama.cpp/Zhipu/OpenCode model routes are stopped in product
  and development. Retain interfaces/history; no calls, probes, auto-discovery,
  fallback or reactivation. Jev is an inactive historical typed candidate,
  not a prerequisite or default comparison provider.
- Owned AI must prove understanding, reasoning, original creation, tools,
  continuity/recovery and controlled learning on real CTH/BMP/creation work.
  Source Brief, multimodal inputs, uncertainty, latency/cost, feedback,
  promotion and rollback remain required; excerpts are not analysis.
- OpenAI, Codex, ChatGPT, Claude and Meta Muse remain public-documentation and
  observable-behavior research targets. No proprietary internals/weights or
  unlicensed training targets are presumed available.
- local_ai_client.py, /api/local-ai/* and .opencode/opencode.json are retained
  compatibility/history, not permission to revive stopped providers.
- Codex/Cloud are development resources, not product inference, Evidence,
  Permission or Truth owners. Surfaces consume the one Core/Gateway result.
- Realtime conversational voice is deferred; file audio/video/image
  understanding and podcast/media production remain C2/C4 requirements.

The platform identity boundary is also explicit: media Cookie/session/browser authorization belongs to the SYSTEM collector/browser chain and stays separate from the future LUMENIS product account. Product account and password design is deferred until product closure reaches 100%, followed by a Product Owner redesign; this timing does not weaken server-side Permission, approval or effect-fence enforcement.

### Platform acquisition decision — Product Owner, 2026-10-07

The current pre-investment closure does not assume that social platforms have granted LUMENIS official/partner API access. Current capability therefore continues to use approved public sources, Product-Owner-authorized owned R&D accounts and managed read-only session/browser connectors where required. Lack of official authorization must not be used to downgrade a proven collection outcome merely to simplify engineering.

The six current primary social platforms are an acceptance baseline rather than a final product limit. Platform acquisition converges on a universal connector contract: one PlatformManifest, one PlatformSession truth owner and one shared recovery Experience over the existing SYSTEM Collector/Browser. Future official or partner APIs are additional providers under that same connector, not a new product, truth stack or prerequisite for current product closure. New platforms must reuse the same Source → Evidence → Canonical path and may not create their own scheduler, account system, Evidence/Canonical store or frontend platform architecture.

Production write chain:

```text
Task → Permission → Action Firewall → Effect Fence / Idempotency
→ Execute → Evidence → Evaluation → Trace
```

AI/Agent cannot bypass Permission or directly overwrite Production Truth.

## 7. Product independence

### Approved public acquisition and local presentation addition — 2026-10-08

SYSTEM Collector's existing PlatformAdapter/CollectionResult boundary owns
capability-specific access classification and backend selection. Anonymous public
HTTP/feeds/DOM precede any separately authorized session route; no backend owns
Evidence, Canonical, Permission or persistence. This batch excludes login-based
OpenCLI integration. Optional Skill store and GitHub connections retain their
existing account authorization; this restriction does not change those features.

Shared/Media and the Flutter platform boundary own **System Read Aloud**: current
authorized visible text → selected installed local voice/locale/rate → transient
playback. Report/Brief review, podcast script listening and video narration-script
review share this capability. It creates no audio Artifact, Source, Evidence or
model-learning input, and is not the final production voice owner. No third-party
service account, cloud speech or paid model is introduced. A future saved voice
output remains a separate explicitly authorized Media/AI capability.

LUMENIS Production Core must run independently.

- LUMENIS does not depend on GGI production code or production databases.
- OSAI / LUMENIS Intelligence is not a startup, collection, analysis, reporting or core-runtime prerequisite.
- LUMENIS Command / 序枢 is a private R&D sidecar: Observe → Control → Verify.
- Cross-repository exchange is versioned, traceable Contract/Artifact only.
- Sidecar failure or deletion must not break LUMENIS.

## 8. Convergence target

```text
lumenis/
├─ domains/
│  ├─ cth/
│  └─ bmp/
├─ shared/
│  ├─ content/
│  ├─ evidence/
│  ├─ research/
│  ├─ evaluation/
│  ├─ learning/
│  └─ reporting/
├─ system/
│  ├─ collector/
│  ├─ runtime/
│  ├─ browser/
│  ├─ ai_gateway/
│  ├─ database/
│  ├─ security/
│  └─ observability/
└─ core/

app/
└─ Flutter LUMENIS Experience
   ├─ Web Workspace
   ├─ Desktop App
   └─ Mobile Companion

website/                     committed Public Website implementation; release status requires actual evidence
└─ Public Website only       no Product Truth / workflow owner
```

This is an ownership target, not permission to mass-move files. Every move requires owner/caller/read-write/runtime/test tracing.

For each vertical delivery slice, record the surface matrix over one Product Core contract: Web Workspace primary/available; Desktop enhanced/exclusive; Mobile view/notify/approve/light action; Public Website explanation/demo only. Layouts need not match, but business meaning and state semantics must. Start current acceptance on actual Website/Web browsers; native Windows/macOS and iOS hosts follow Website/Web closure; record unavailable device/runtime combinations as `UNVERIFIED`, and do not claim a surface or OS release until its build and runtime flows pass.

### Current runtime caller map

These paths are the current owners for production callers. A route or compatibility façade may preserve an established API name, but it may not own the underlying business, security, data or runtime truth.

| Caller family | Canonical owner | Behavior that migration must preserve |
| --- | --- | --- |
| `account/api.py`, `agent_runtime/`, `agent_capability/router.py`, `agent_smart_tool/base.py`, `ai_api.py`, `ai_task_engine.py` | `lumenis/shared/agents/skills/{registry,package_runtime,execution}.py` | Skill discovery, source preview/validation, permission checks, execution state transitions, effect fencing and execution Evidence. |
| `subject_registry.py`, `experience_screens.py`, `lumenis/shared/evidence/api.py`, agent callers | `lumenis/system/security/{permission,action_firewall,effect_fence}.py` | Domain-aware Operation/Risk decisions, system scope, approval state, fail-closed behavior and audited side-effect boundaries. |
| `app.py`, `agent_runtime/observation.py` | `lumenis/system/ai_gateway/{channel,providers,core}.py` | Provider health, fallback order, retry/error classification, circuit breaking and token accounting. |
| `browser_runtime_api.py` and browser callers | `lumenis/system/browser/runtime/{contract,policy,router}.py` | Existing status/probe route contracts, authorization context and safe browser state transitions. |
| `data_query_api.py`, collector scheduling/operations | `lumenis/system/collector/guard/` | Resource limits, queue/DLQ replay, schedule state, recovery gating and runtime switches. |
| `compliance_gate.py`, `engineering_metrics.py`, `experience_runtime.py`, `topic_campaign.py`, `xhs_cookie_bridge.py` | `lumenis/system/collector/adapters/` | Platform registry, source-specific collection policy, schedule decisions, rate/safety limits and normalized records. |
| `kos_routes.py`, `scripts/collect_now.py` | `lumenis/system/collector/runtime/xhs/` and `runtime/pipeline/` | Live collection, deduplication, existing `subject_hit()` semantics, persistence, comments, quality fields and platform-blocked/verification-required states. |
| `collector_automation.py`, collector Evidence writers, `runtime_preflight.py` | `lumenis/shared/evidence/{chain,store,api,production_contract}.py` | Stable identifiers/hashes, primary database path, source/domain/Subject lineage, replay behavior and explicit write-failure evidence. |
| `experience_screens._build_bmp02` | `web_discovery.get_brand_directory()` with `data/brand_directory.json` | Preserve the curated 194-brand / 13-category retail directory and honest source/update metadata; external benchmarking stays unavailable until sourced. |
| `experience_runtime.py`, `experience_screens.py`, `risk_engine.py`, `content_generation.py` | `lumenis/shared/reporting/` | CTH operational/risk report semantics remain separate from BMP brand/market report semantics; export remains permission-gated. |
| `system_features_api.py`, `experience_screens._build_bmp09`, `architecture_api.py`, evaluation/learning callers | `lumenis/shared/{evaluation,learning}/` | Unknown is not PASS, records retain lineage, learning stays reviewable and never writes Production Truth automatically. |
| Business / Canonical Production Truth | `lumenis/shared/database/` | `data/monitor.db` selected through the single compatibility override `ZBC_DB_PATH` remains the only CTH/BMP/Shared business-truth database; all business schema/version ownership stays in the Shared Database migrations. |
| SYSTEM durable task queue | `lumenis/system/collector/guard/task_queue.py` through `DatabaseRepository` | Existing `data/task_queue.db` holds only operational queue/lease state, never Canonical Data, Evidence or business outcomes. Preserve its durable records and replay semantics; any future move requires an explicit data migration verified for data preservation and actual recovery. No new module-local SQLite sidecar is allowed without an architecture entry, recovery/retention owner and acceptance evidence. |

The production import gate parses Python import nodes and rejects exact retired owners. It excludes tests, audit prose and comments from the production dependency decision, while actual migrated behavior, preserved data and recovery require real runtime evidence under the existing owner. The formal 2026-10-08 PO policy retains compilation/static/security/data checks and real product E2E, and forbids creating/running unit/integration or renamed module suites; historical tests/failures remain preserved.

## 9. Convergence disposition

Every current or historical capability receives exactly one status:

```text
KEEP      current owner is already canonical
MERGE     multiple implementations become one owner
RESTORE   valid capability is absent or functionally regressed
MIGRATE   capability survives but moves to canonical ownership/app Experience
DELETE    duplicate/obsolete code after capability parity is proven
RESEARCH  source-traceable input adopted through existing capability owners
```

User-supplied videos, images, books, cases and valid prior analyses remain
traceable research inputs. They do not become a second design authority. Retire
wrong execution references and obsolete renderers only after preserving unique
requirements and behavior; do not delete original materials merely for their age.

## 10. Completion gate

Convergence is complete only when:

```text
original baseline capability regressions = 0
later capability regressions = 0
unclassified old-repo capabilities = 0
parallel runtime owners = 0
parallel Experience implementations = 0
surface-specific business truth owners = 0
competing active UI/UX authorities = 0; source reference originals retained
clean clone = PASS
blocking CI = GREEN
critical E2E = PASS
LUMENIS production repositories = 1
```


### 2026-10-08 前端审计与工具维护增补

按最新PO直接构建真实前端，依既有Experience/ScreenSpec/Owner合同随源码更新设计决定与验收证据；不等待独立设计稿/Figma或M逐屏设计审批。原DESIGN_EXPLORATION/DESIGN_READY保留为真实设计审核记录，不再作为强制编码阶段；实现与验收据实记录，不建立第二设计真相。已有Figma可编辑工程和局部节点有本地收据，当前云端版本未核；免费受限时沿Experience§38采用可编辑源码，不等待付费。C1–C6/F/M/W1–W6 保留原源码责任和完整成果；实际开工、暂停、恢复、模型与推理档位由 Product Owner 决定，本文件只记录有时间和证据来源的已核实事实，不设单业务窗口限制；实际派发/准入以本地ledger和真实工具回执为准，各窗 fresh admission 后才进入 RUNNING。本规则更新不提升运行或用户验收状态。

工具维护保护现有模型/effort/tier、登录方式、权限、网络/代理及会话；只更新核实的稳定兼容版本，开发插件不变成产品依赖。需要中断桌面/会话、重启、扩大权限或新增登录/费用时等待精确批准。既有未发布源代码、私有配置及生产DB保持原边界。

### 2026-10-08 成熟基础能力与序境特色的统一升级

现有 J1–J8 / U01–U25 产品终态同时包含两层：普通用户能直接操作的成熟基础能力；在这些能力上连续使用 Source/Evidence/Canonical、CTH/BMP、业务约束、研究、创作版本及 Evaluation/Learning。智能建议、组件数量或安装成功不能替代第一层。现有可靠能力复用，断开的调用先修，确实缺失的通用底层能力才经第三方准入适配；不创建另一套编辑器内核、Timeline、播放器服务、Agent、Truth、Runtime或永久候选。

| 已有用户工作 | 必须保留的基础能力与组合结果 | 现有Owner |
| --- | --- | --- |
| J1 数据 | 真实来源发现、搜索/筛选/排序/详情/分页/刷新、历史与增量、时间语义/去重、原文打开与失败恢复，再以正式来源回答业务问题 | C1；C5来源准入；C6组合；F交互 |
| J2/J3 商业与品牌 | 主体/品牌选择、同口径比较/时间范围/趋势/图表、事件/Campaign、竞品/创作者分析、保存/收藏/报告/导出/历史版本；判断回到确切来源与实际行动/Outcome | C3；C1/C5输入；C2受控分析；C6/F |
| J4 提案 | 资料导入/阅读、文档编辑、实际预算调整、审阅/版本/保存/重开/Word导出；继承原Brief和引用，改约束只影响关联内容 | C4；C3/C5内容与SavedWork；C6/F |
| J5 视频 | 真实素材导入/缩略图/预览，选择拖动裁切分割删除重排，横向时间轴平移/缩放/吸附/定位，轨道/音量/淡变/混音/字幕/转场/画幅，撤销重做/保存/恢复/重开/实际可播放导出；项目与导出状态一致 | C4现有content_creation Timeline/rendering、shared_artifacts；C6/F |
| J6 播客 | 导入或授权录音、真实播放/Seek/波形、多轨编辑/混音/静音/淡变/Duck、降噪/响度、手工转录及修订、脚本/章节/时间码/声音关联、成品保存重开重导出；形成研究→节目→Evaluation连续链 | C4现有podcast、Shared Timeline/Renderer；C5 SavedWork；C2仅ASR/模型；C6/F |
| J7 资料与Agent | 阅读/搜索/精确定位/引用/版本/任务历史、Skill发现与管理、取消/恢复/checkpoint、真实结果保存；沿现有Agent/Skills/Memory/Research/Evaluation，不复制第二平台 | C5资料；C2执行；C3消费；C6/F |
| J8 四端 | 导航/文件选择/输入/设置/通知、中英韩、键盘与触控/无障碍、加载与真实错误、恢复同一任务；Website/Web/Desktop/Mobile依批准角色呈现同一业务语义 | F呈现；C6运行/共享；各C提供业务合同 |

视频/播客先连已有 Flutter→Core→Timeline→Renderer→Artifact/SavedWork。实时编辑预览、临时导出、正式保存、独立重开分别验收；现有一条视频轨若阻塞已批准分层任务，只扩现有renderer。Read Aloud只预览文本，不能代替录音、ASR或成品。AI/外部平台阻塞不暂停可独立进行的确定性编辑、手工转录和文档能力。

竞品机制沿原Owner增强：多源可比信号/事件关系/解释/预警→C1/C3/C5；创意审阅/版本差异/局部修订/审批复用→C4/C5；文本与真实音视频双向时间定位→C4；按需工具/引用/checkpoint恢复→C2/C5。来源、方法及可证明的任务收益写回现有验收，不把竞品宣传当事实或追平证据。

本次为规则采用；C1–C6/F/M/W1–W6 保留原源码责任和完整成果；实际开工、暂停、恢复、模型与推理档位由 Product Owner 决定，本文件只记录有时间和证据来源的已核实事实，不设单业务窗口限制，实际派发/准入以本地ledger和真实工具回执为准，各窗 fresh admission 后才进入 RUNNING，并依现有 Owner 与门禁执行。逐项事实状态与两层正常用户任务验收归 Real Delivery Overlay；界面、可编辑设计及 GPT/Apple/Tesla 操作对标归Experience §38。原用户要求/资料/历史失败证据保留，未经明确后置的功能不删除。规则采用和派工均不证明实现、运行或用户验收完成。

### 2026-10-08 采集范围与数据可得性

采集按主体/话题/任务语义及显式用户约束运行，不设全产品统一历史起点。Source/Evidence保留出版/事件/采集时间并区分，视图按任务正确整理；旧资料不删除。维度定义完整、采集能力闭环、实际数据覆盖是三个不同判据：准确维度即使缺值仍展示“—”及真实原因，不要求客观不可得的数据全部非空。必要业务证据不足仍不可给结论；缺值不得掩盖实现缺口。详细唯一合同与当前旧日期源码待改处见Global§10；相关Owner在PO授权范围内，实际派发/运行状态仍需本地ledger及真实工具回执。

### 2026-10-08 全产品逻辑收敛与逐步交付

同一用户目标沿已有Task/Brief携带actor、GLOBAL/Focus、资料、来源用途、时间/预算及版本；读取全域不强制选择参考主体，特定业务动作再按真实合同确定范围。数据缺口按任务影响说明，普通编辑和确定性计算不依赖模型服务。研究结果、决策、文稿及媒体使用可回读的既有上游引用；移交时不要求用户重述目标或重选材料。

先形成有依据的有用部分，再按同一任务增量丰富；表现由任务决定，交互控件使用已批准本屏组件和动作。最终完整性、事实准确性、用户修改和保存版本不得因提前显示而降低。Experience §38定义分段校验、更正、等待时间与恢复；现有Task/Source/Evidence/SavedWork/Artifact/Timeline分别保持唯一所有权。

来源/预算变化时沿已有引用/父版本找出受影响成果，未能追踪的依赖明确未知；局部修订由对应文稿/媒体Owner执行，不把通用SavedWork修订用于绕开task-owned合同。Action回执、Outcome观测与Evaluation分别存在，学习与模型晋升仍单独准入。产品代码拥有采集和持续任务，不依赖Codex代操作。

本轮[全产品逻辑审阅记录](evidence/round-15/PRODUCT-LOGIC-REVIEW-20261008.md)覆盖J1–J8/U01–U25的逻辑与交接，给出已发布源码断点及顺序。它是本蓝图的取证材料，不是第二执行蓝图。改进首先收敛现有连接与正常结果；不新增产品能力家族、平行候选或无收益研究。已获授权的窗口按本地ledger、真实工具回执和 fresh admission 确定实际执行状态。

### 已核读研究的及时产品采用 — 2026-10-08

原始资料是既有能力的知识与可信度基础，不能只沉积成文档或等待训练。M 对有当前产品收益的已核实结论，及时在本蓝图、Source Owner Index 和该能力的既有详细合同中形成同一采用决定，随同版本发布并通知当前受影响执行窗口。未读原文、部分阅读、研究建议、源码实现、运行验收和 MODEL_TRAIN 各自记录，不互相晋升；已有正确实现直接复用，不另造框架或重做全量研究。完整材料范围仍保留，未读/缺失不能由抽样或目录覆盖率冲抵。

沿现有 Source→Evidence→Canonical→研究/业务→SavedWork/Artifact→修订/恢复/Evaluation 保留两类信息：原文实际说了什么，以及任务如何使用和限制这些信息。来源版本、精确位置、实际读取区间、时间/地域/样本与方法语境必须在相应既有合同中可追溯；未提供的信息保持未知。宣传指标、互动、作者经验和消费者/经营结果不可相互替代。相似文本不抹去来源身份；材料读取不自动建立事实真实性或用途授权。

当前采用顺序：C1 在自身 J1 闭环落实 Global §10 的真实原文/媒体覆盖、时间语义、来源不丢失和可消费引用；M 在获授权的已有非 C1 成果收敛中核对 C5 来源语境/片段覆盖、C3 比较依据与 Outcome、C4 媒体时间码/版本及 C2 研究与学习准入隔离。暂停窗口不因规则更新自动恢复。C1 不等其余研究完成、另一窗口或 GPU，也不接管下游业务推断；具体缺口和操作随原 Owner 入口更新。采用决定不是新增产品能力或验收通过。

当前 C1 的处理优先级依 Global §10 最新直接指令：主体相关发帖批量取得后立即通过原数据链，关键词/主题后置分析、同步采集每帖只处理一张真实封面；范围/权限/原文覆盖/连续恢复保留。图片与视频的完整内容理解要求不取消：通过既有 SYSTEM Queue/Gateway 和 Shared 媒体路径后处理实际图片、音轨与时间画面，携带原帖/图位置/时间码、版本及实际覆盖供研究、业务和创作消费；封面、OCR、转写、模型解释分别记录，不冒充全媒体已读。不等全量词库、逐图研究或全部平台结束，不复制 Collector 或把未测/未读状态当成果。C1 自行接通既有 SYSTEM principal 的精确内部用途；导入许可、关键词许可与媒体分析/派生保存分别核验，派生结果不改原文权益，也不替代商业报告/引文/训练/导出授权。具体预算、检查和恢复归 Global §10，同一当前数据链不得因必要绑定交回逐函数审批。

### 2026-10-08 产品自主电脑操作与浏览器

闭环终态包含产品自己的授权电脑任务执行，而不依赖Codex代操作：同一Task/Actor/Scope/目标电脑→观察→规划→获准操作→实际结果核验→Evidence→返回原任务/保存成果→暂停取消恢复。受控浏览器是已有实现基础；通用OS应用、键鼠及获准文件操作由C2/C6在既有Agent/SYSTEM Runtime中补齐适配器，不能用浏览器自动化冒充全部电脑操作。手机承载受控电脑/浏览器的观察、接管、停止和任务返回，未授权控制手机OS；PC与Web Workspace在产品内承载可操作页面，外部浏览器仅可选。具体视觉和动作状态归Experience §11/§38与SYS-06。

仍是同一个产品、同一权限/效果/任务/证据权威。先复用已有ai_browser_api/runtime和SYSTEM browser adapters闭合真实交互，安全补齐当前loopback-only的远端客户端绑定；不能简单删除防护或把raw CDP暴露给前端。真实OS控制按目标平台逐端证明权限、停止和恢复；运行环境不可用如实标记，不假装全平台已具备。该用户要求不批准新付费机器、默认无人值守外部写入或访问受保护身份。

### 全产品数据到成果链升级 — 2026-10-09

Global §10 记录本轮完整直接 PO 命令及原实现落实点：采集授权/原始保留、来源有效性、用途权限、身份候选/确认、业务分析分开，合法未绑定原始观察在原 Source/隔离链持久可恢复，不自动成为主体事实。Shared 保持同一 ID/use/时间/版本/状态；CTH 使用已核验时地关系与反馈，BMP/SH-01 Discover 区分原生热度/样本/推断；Research/Reporting/Evaluation 将可检索引用的真实来源接入同一 SourceBrief/SavedWork/Content Project 的保存、关闭重开、修订、追溯和恢复。SYSTEM 继续原 Scheduler/Runtime/Browser/Permission/Gateway，不因 AI 不可用停止合法确定性工作。

C1 保留采集链及获准必要依赖的源码责任；当前窗口执行状态不得由本蓝图推断。跨 Owner 写入仍由 M/W6 既有预约有界交接；原非 C1 候选、未集成成果及完整资料采用继续保留，实际执行需当前PO指令。仅修数据链影响的现有 Web 消费与状态/来源返回，不重做44屏、不新增架构或队列。六平台各自实证与阻塞分列，至少一个获准平台通过完整真实操作链；同口径吞吐、延迟、覆盖缺失、身份/数据错误、恢复、成果保存重开须有真实数据，无旧基线写 BASELINE NOT VERIFIED。旧逻辑先追有效 caller 再收敛，全部历史/原件/有效兼容保留。

本规则采用不证明源码已改、运行已加载或用户已验收；最终 A–F 成果、OBSERVED/INFERRED/NOT VERIFIED 和 ACCEPTED 条件归既有 Real Delivery Overlay，保持完整 R/J/U 和当前编译/静态安全数据/真实E2E，不执行模块单元/集成套件。
