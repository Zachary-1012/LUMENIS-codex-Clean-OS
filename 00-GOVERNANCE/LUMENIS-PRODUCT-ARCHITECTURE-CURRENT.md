# LUMENIS Product Architecture — CURRENT

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
Desktop on Windows/macOS/Linux, and Mobile on Android/iOS share the same Core.
Platform availability and acceptance are verified separately from this target.

### 当前语义与兼容边界（2026-10-07 校准）

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
治理状态的机器语义继续由 Governance Machine v1.1 定义；采集、队列、AI 与数据状态
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

Design artifacts remain DESIGN_EXPLORATION until a current screen specification
passes DESIGN_READY. Do not authorize implementation from a PDF, screenshot, fixture, Figma frame
or a generic swapped-title renderer. Original capabilities and later valid
capabilities must survive convergence.

一、闭环后，用户实际得到什么

用户在序境提出一个商业或品牌任务，提供目标、主体、市场、时间、预算与已有资料。序境能理解文件和材料，补充授权范围内的真实数据，形成有依据的判断与可执行方案，接着制作文稿、视频或播客。用户改变预算、来源或创作要求时，系统定位受影响部分、提出修改、经确认后应用，保留旧版、修改原因与可回滚关系。用户可以保存、关闭、换端、重开和在中断后继续，不必重述目标或重新选择同一批材料。

**Platform-native Source → Source/Evidence/Canonical → LUMENIS presentation → Open Original → Return** 是同一产品闭环。平台内容被正式接收后，序境保留原生正文、作者、来源平台、原始 URL/locator、发布时间、采集时间、原生指标、许可与 Evidence lineage，但用户看到的是按 CTH/BMP 任务语义和 LUMENIS Experience 重新组织的呈现，不复制来源平台 Feed、视觉外壳、无限滑动或自动播放。获准用户可从记录、事件、趋势、案例、风险、报告或创作引用中点击“查看原贴 / Open Original”，把经过校验的公开 HTTPS 目标交给系统浏览器，并在返回时恢复原任务、GLOBAL/FOCUS、筛选、选中对象和滚动位置。普通原贴跳转不读取本地 Cookie、不静默登录、不启动采集、不生成新 Evidence、不发布也不写外部状态；受控网页导航与证据捕获继续只归 SYS-06。

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

并行批：自有AI实际训练与服务。现有/免费资源优先，许可允许的基础权重、自有训练部署、实际step/loss/checkpoint/重载/独立语义评价。以真实CTH/BMP/创作结果验收；Codex Cloud和免费临时GPU不冒充上线推理服务。开发电脑关闭、Codex停止、外部模型API禁用时，承诺的产品运行必须由序境自有运行环境完成；部署与资源可用性要实际证明。

第三批：跨端统一运行与发布。一个同版本成果在承诺的四入口衔接；不要求四端相同布局。验证启动/崩溃/取消/撤权/重试/重开/恢复，完成同SHA Product/App门禁、备份回滚与打包。工程可用后由你重复完成核心任务，记录耗时、成本、正确性、修改成本与人工补救。

此顺序按真实依赖并行，不要求先完成全部中国/全球目录才验证业务，也不能用几个代表性任务冒充覆盖完成。



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

For each vertical delivery slice, record the surface matrix over one Product Core contract: Web Workspace primary/available; Desktop enhanced/exclusive; Mobile view/notify/approve/light action; Public Website explanation/demo only. Layouts need not match, but business meaning and state semantics must. Start acceptance on actual available browser, desktop and mobile reference hosts; record unavailable device/runtime combinations as `UNVERIFIED`, and do not claim a surface or OS release until its build and runtime flows pass.

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
| SYSTEM durable task queue | `lumenis/system/collector/guard/task_queue.py` through `DatabaseRepository` | Existing `data/task_queue.db` holds only operational queue/lease state, never Canonical Data, Evidence or business outcomes. Preserve its durable records and replay semantics; any future move requires an explicit, tested data migration. No new module-local SQLite sidecar is allowed without an architecture entry, recovery/retention owner and acceptance evidence. |

The production import gate parses Python import nodes and rejects exact retired owners. It excludes tests, audit prose and comments from the production dependency decision, while the relevant test suite remains responsible for proving each migrated behavior.

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

采用用户本轮前端审计中的可编辑设计→屏幕规范→真实源码→验收证据链，细则归 Experience §38 及原44份ScreenSpec/README。保持原 Blueprint、Owner、DESIGN_EXPLORATION→DESIGN_READY→IMPLEMENTED→ACCEPTED，不建立第二设计真相。Figma实际文件/节点/版本本轮 NOT_VERIFIED；不以本地无 .fig 推断云端无工程。其余窗口待 Product Owner 确认后执行，本轮只由 M 收敛规则、处理已授权修复/工具维护和同步。

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

本次为规则采用，具体实施等待Product Owner确认。逐项事实状态与两层正常用户任务验收归 Real Delivery Overlay；界面、可编辑设计及GPT/Apple/Tesla操作对标归Experience §38。原用户要求/资料/历史失败证据保留，未经明确后置的功能不删除。
