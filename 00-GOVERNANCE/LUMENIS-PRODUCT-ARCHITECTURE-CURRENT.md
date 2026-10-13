# LUMENIS Product Architecture — CURRENT

## 2026-10-11 产品定位与业务闭环校正（最新直接 PO）

序境是面向商业运营与品牌市场的证据驱动工作平台。CTH、BMP 是两个业务领域；Shared 是可独立使用、也可供业务领域调用的共享能力；SYSTEM 提供共同基础。用户既可完成业务研究/决策，也可直接进行研究或内容制作，不新增产品入口或架构。

**通用电脑控制已撤出产品范围**：不再交付操作系统桌面、任意本机应用/键鼠控制、远程电脑助手或 Agent Zero GUI worker。该项为 PO 撤回的要求，不是已完成或后置任务。已有源码、研究与失败证据保留为历史；内置浏览器、采集、正常文件导入/导出、媒体制作、服务运行和研发工具不受此撤回影响。

### 独立入口与可组合的用户工作链

明确业务目标与主体/品牌/市场/时间/预算 → 复用已有获准资料并补充必要来源 → 后端完成清洗、确定性计算、适用的分析与证据核验 → 交付已分析的报告/方案/项目 → 用户判断、修改和采用 → 保存版本 → 关闭重开与恢复 → 记录实际结果并评价。

上面是 CTH/BMP 的一条业务链，不能变成全产品强制流水线。Shared 内容制作另有独立完整入口：直接新建提案/文稿、视频或播客 → 输入创作要求/手写内容/导入获准素材 → 编辑、审阅/预览/试听 → 渲染或导出 → 保存、修订、关闭重开与恢复。内容制作属于制作能力，不需要先完成商业分析，也不强制选择 Subject、BrandFocus、Case、Campaign 或先生成 SourceBrief。

创作 Brief 可由用户直接填写，描述用途、受众、风格、结构与素材；不等于已经完成的业务研究报告。引用 CTH/BMP 或研究成果时，自愿带入同一来源、范围与版本；创作结果也可按权限回用于业务。用户原创/自有素材按现有工作区/项目权限和实际素材权益处理，不伪造外部 Evidence 或把原创内容当 Canonical 事实。行业案例支持适用的研究和分析，不是新建空白文稿、编辑视频或录音的统一前置条件。

用户不用先选“数学分析”、论文算法、对数权重或内部 Agent/Task。系统按业务合同选用合适的方法；证据不足时给出可用的部分结果与精确限制，不编造趋势。来源样本计数只是覆盖说明，不能替代商业分析报告。

### AI 贯穿既有能力，基础链独立可用

| 领域 | 正常用户成果与基础能力 | AI 在同一工作流中的增强 | 不可越过的边界 |
| --- | --- | --- | --- |
| SYSTEM / 采集与浏览 | 授权采集、去重、来源保存、刷新恢复、产品内浏览/人工操作 | 页面理解、提取辅助、资料检索与任务步骤建议 | 不绕登录/权限，不改原文，不接管用户电脑 |
| CTH / 商业运营 | 监测与指标、事件风险、案例、人工判断、行动及结果报告 | 解释关联、辅助归因研究、风险解读与决策建议 | 假设与事实分开；无因果证据不声称因果 |
| BMP / 品牌市场 | 品牌资料、传播分析、竞品比较、创作者/Campaign 管理及评价 | 洞察提炼、创意与策略建议、方案比较 | 样本表现不等于全市场/转化，不跨品牌权限 |
| Shared / 研究与创作 | 独立导入检索/研究；直接新建提案文稿、视频播客，编辑播放渲染、保存导出 | 语义检索、摘要、文稿生成、转写和剪辑建议 | 不依赖CTH/BMP；需要联动时带入其来源/版本；生成内容可改可拒绝 |
| Agent Groups / 自研 AI | 原任务的受控调用、状态、取消恢复与评价 | 跨域辅助步骤、模型质量改进与获准持续学习 | 唯一 Gateway/Agent Runtime；训练/晋升另行验收，无 OS 控制 |

AI 的可选性是运行依赖边界，不是删除增强功能或把它们全部推迟到第五轮。各轮同时设计真实业务合同与可用的 AI 增强接点；第五轮关闭跨域增强、模型与最终验收的剩余项。基础链、AI 增益、训练/模型能力分别取证。无模型时完成适用计算与人工操作；真正 AI 专属步骤诚实不可用，保留输入和继续路径。

### 数学研究、行业材料与报告

OpenAI 数学论文方法在既有后端计算/业务/Shared Evaluation 中按实际假设采用，用于约束核验、可行方案比较、计数/抽样适用性、统计口径和误差边界。用户编辑的是真实业务约束，系统保留参数如何由数据或用户声明得到的映射，不能自动编造权重。有限子实现不冒称完整一般算法，确定性结果不冒称模型学习。论文原文、实现范围、上游修订和未完成项仍由现有 Math 采用记录追踪。

行业案例是分析的证据与方法基础：保留出处、日期、行业/市场、实际结果、适用条件与反例，明确可比与不可比之处；通过既有 Research/Source/Evidence 使用。缺案例影响对应结论的可信度和范围，由当前已授权 Owner 补足；不以泛化 AI 文本或仓库里有文档冒充采用，也不因此阻塞已有证据足够的独立成果。

### 用户看到什么

资料视图保留真实封面、标题/正文、作者、平台、原帖、原生时间/采集时间、实际互动维度和来源状态，以序境自己的业务布局呈现；未知显示“—”并说明原因。首采单封面不等于全部媒体已理解，后续媒体分析保留位置/时间码和实际覆盖。报告优先显示问题与结论、依据和比较、限制及可执行建议，方法/样本口径可展开追溯。编辑、保存、引用返回、修订和恢复均围绕同一任务与版本。

### 本次实际顺序

先统一当前规则与详细合同；继续已授权的真实来源→分析→CTH/BMP→成果保存/修订/重开/恢复；再按完整五轮退出条件关闭其余真实缺口。Public Website、Web Workspace、Windows/macOS Desktop 与 iOS Mobile 并行推进；Website 保持既有独立展示边界，Workspace/Desktop/Mobile 使用同一 Flutter `app/` 与同一 Product Core。先形成任务化的完整真实前端，不等待全部后端；已有真实 API/Core 合同立即绑定，其他依赖按既有 Owner 逐项接入并将缺口标为 OPEN/UNBOUND，不以模拟结果替代。44 份现有屏幕规格是覆盖基线，不是页面数或产品范围上限；每个表面独立通过自身真实任务验收。该执行更新经 `PO-20261011-WHOLE-PRODUCT-REUSE-EXPERIENCE` 批准。R01–R15/J1–J8/U01–U25 和既有设计/历史证据保留，只有通用电脑控制的明确子要求撤回，不删整项 ID。窗口实际开工、暂停与恢复只服从直接PO指令及本地事实记录，不写作线上产品约束。文档变更不证明界面已改、业务已验收或 Runtime 已加载。

### 用户工作方式蓝图 — 2026-10-11（PO 已确认）

本节把既有产品要求展开为用户的完整工作方式。Product Owner 已明确“以上ok，然后更新，然后重新规划各窗口应该做的事情给我审核，目的仍旧是产品闭环运行能够上线”。本蓝图及第11节解析采用方向已确认；这不是功能已实现、用户验收或开工批准。窗口执行审核稿归既有 Source Owner Index 的完整成果卡；任何已明确给出的直接PO派工按其适用范围执行，规划发布本身不派工。独立制作、AI 非依赖和撤回电脑控制保持约束，具体布局仍归唯一 Experience 与现有44屏合同。

#### 1. 用户进入序境后如何开始

用户从官网了解产品、工作示例与帮助，再进入工作区；也可以直接打开工作区或已有成果。工作区围绕现有 CTH、BMP、Shared、SYSTEM 入口提供“新建工作”和“继续已有工作”。不要求用户学习五轮研发顺序、内部 Agent 名称、论文操作名或复制 Task ID。

用户可以独立选择以下任一工作：商业运营、品牌市场、资料研究、提案/文稿、视频、播客、网页浏览。需要时才连接其他能力。商业任务选择实际主体或品牌/市场；独立创作只需自己的工作区/项目与素材权限，不强制商业身份。默认 GLOBAL/ALL 不暗选广州太古汇或参考品牌，也不代表全球资料齐全。

#### 2. CTH：完成一项商业运营工作

- **入口：** 进入 CTH，从获准商业主体、监测结果、事件/日历、风险或已有案例开始；也可提出一个明确运营问题。区分商业体、门店、场内品牌与时间，不因同名自动建立场内关系。
- **操作：** 选主体、时间、关注问题和适用预算/资源；查看事件、消费者反馈、媒体讨论和风险；按需补充资料或说明。用户审阅系统已分析的结果，检查依据、比较选项、修订判断、确定行动，并记录执行情况与真实结果。
- **系统处理：** 在后台按来源和业务口径清洗、去重、聚合、比较、执行风险规则，结合适用行业案例和反例，区分事实、推断与人工意见。用户输入的是问题与约束，不承担选择数学算法、填写工程参数或组装分析管线的工作。
- **成果：** 回答用户问题的监测/分析报告、事件和风险处理记录、方案比较、运营决定、行动记录及结果评价。报告必须有结论、支持依据、样本与时间范围、不能得出的结论和可执行后续；条数统计不能冒充运营洞察。计划、实际行动和观察到的效果分别呈现。
- **保存与恢复：** 同一案例/任务保留分析、选定方案、人工改动、预算、来源和版本。关闭后从工作历史重开；来源或预算变化时显示受影响内容，经用户采用后保存新版，旧版可回看/恢复。中断后回到上次已确认状态，不重复执行外部行动。
- **可选联动：** 可将选定材料和方案送入研究、提案、视频或播客，也可引用已有制作成果；完成 CTH 报告不要求同时制作三种内容。

#### 3. BMP：完成一项品牌、市场或 Campaign 工作

- **入口：** 进入 BMP，选择品牌、目标市场、竞品比较、消费者/创作者/渠道研究、传播问题或已有 Campaign。支持多品牌和市场的明确比较范围，不把某一参考品牌当全产品默认。
- **操作：** 输入目的、市场、期间、比较对象和适用预算；查看品牌与竞品资料、传播内容、创作者表现和趋势解释；调整方案、内容要求与执行计划；记录实际执行材料和观察到的结果，进行评价。
- **系统处理：** 在后台核对市场、币种、单位、统计期与分母，分析可比较数据，关联真实行业案例。平台官方排行、序境样本热点、模型推断和推荐分别说明；点赞/浏览量不能推导销售、全市场需求或因果增益。
- **成果：** 可使用的品牌/市场/竞品/创作者/传播研究报告、可编辑 Campaign 方案、内容要求、执行记录与效果评价。有数据给出分析结论，缺数据说明影响和可完成部分，不用空白或假零值填满页面。
- **保存与恢复：** 方案、预算、选定来源、创作者/渠道选择和人工决定属于同一版本链；保存、关闭、重开、修改、恢复均保留身份与引用。新数据或资源变化后只更新确认受影响部分，原决定和执行记录不被覆盖。
- **可选联动：** 用户可从方案发起制作，也可选择独立制作的内容用于 Campaign。内容做好不等于已发布；发布、外部执行及使用权继续经过适用授权。

#### 4. 独立研究：从资料得到有依据的认识

- **入口：** 直接进入 Shared 研究/资料工作，打开已有资料或新建研究主题；不要求先建立 CTH/BMP 项目。可从网页、文件、图片、音视频、已获准采集结果或个人笔记开始。
- **操作：** 导入、搜索、筛选、阅读、批注、整理引用和比较案例；提出研究问题，选取需要采用的材料，补充判断，编辑笔记、简报或报告。Discover 提供与当前工作有关且有出处的内容与案例，用户决定是否采用。
- **系统处理：** 保留原件和解析版本，索引可得内容；引用能回到页码、段落、图片位置或媒体时间码。分析先使用可用的确定性检索/比较；AI 可辅助语义检索、摘要与关联，理解覆盖和遗漏明确呈现。行业案例保留行业、地区、时间、方法、实际结果、局限和反例。
- **成果：** 有用的研究笔记、案例比较、简报、报告与可复用引用；用户可以只完成研究，不必进入制作、商业决策或模型训练。
- **保存与恢复：** 保存研究问题、材料选择、笔记和引用版本；重开定位原阅读位置/选中资料，修订保留父版本；来源更正或撤回时提示影响，保留历史说明而不继续违规引用。合法导出保留可追溯引用。
- **可选联动：** 被用户选中的研究材料可供 CTH/BMP、提案、视频、播客使用；传递现有材料与目标，不要求重新上传。资料入库和蒸馏不自动授予模型训练权。

#### 5. 提案与文稿：可以从空白独立开始

- **入口：** 在 Shared 直接新建提案/文稿，或打开已有作品。可从空白、用户填写的创作要求、已有文稿/素材或自愿继承的研究/业务成果开始。
- **操作：** 说明受众、用途、形式、风格及适用预算；编写与调整结构、文字、引用、图表和预算；比较创意/方案，预览、审阅和修改。普通书写编辑不要求先完成一轮数据分析。
- **系统处理：** 支持实际文档结构、格式、引用和确定性预算计算；AI 在用户选择时辅助构思和写作。外部事实需要依据，原创表达按原创内容保存，不能为了凑引用伪造来源。财务数字与资源约束保持可核查。
- **成果：** 可编辑、可交付的原创提案/文稿和相应实际导出文件。客户可用性由内容、结构、预算与真实文件共同决定，不以“已生成”字样验收。
- **保存与恢复：** 保存完整正文、结构、引用与版本；只修改选中内容，保留未选部分；关闭重开后继续，能够比较、恢复旧版本并再次导出。导出失败保留草稿及上一次有效文件。
- **可选联动：** 可采用研究或 CTH/BMP 材料，也可把文稿用作视频脚本/播客脚本；这些都不是新建文稿的前置条件。

#### 6. 视频：完成真正的制作工程与成片

视频与播客从既有 Shared 媒体制作入口进入同一编辑基础；根据项目内容选择视频或音频工作模式，复用素材、时间轴、版本和成果管理。不是再造两个编辑器，也不把两种成品验收合成一次“媒体成功”。

- **入口：** Shared 直接新建视频项目、打开已有工程，或明确采用某个脚本/业务方案；无需先建立品牌、案例或 SourceBrief。
- **操作：** 导入获准视频、图片、声音和字幕；组织素材和分镜，编排时间轴、剪切/分割/删除/换源，调整时长、字幕、声音、转场与适用效果；实际预览、撤销重做，设置输出并渲染，播放和检查成片。
- **系统处理：** 核验素材、可用格式与许可，执行媒体处理，维护时间轴、字幕、音画关系和版本；AI 可辅助脚本、转写、素材理解和剪辑建议。没有 AI 时手工制作、播放、渲染和导出仍可用。素材封面或静态脚本不能代替真实预览/渲染。
- **成果：** 真正可播放的成片，加上可继续编辑的完整项目、素材引用、时间轴、字幕与声音安排。既有批准的编辑和质量范围继续保留，不因某条渲染路径当前仅单视频轨而缩小终态要求；技术限制造成的缺口单列。
- **保存与恢复：** 项目和导出成片分别保存版本；重新打开恢复素材、片段、播放头和选择；修改某片段不破坏其他内容。取消渲染、中断、素材丢失或输出失败可诊断并恢复，不用填充/截短冒充完成，不覆盖旧成片。
- **可选联动：** 可从研究/文稿/Campaign 接续，也可独立制作后供其他任务使用。素材再利用和外部发布各自核实使用权。

#### 7. 播客：完成真正可听的节目

- **入口：** Shared 直接新建节目、打开音频工程，或选择已有脚本/资料；品牌播客是可选业务用法，不是所有播客的强制入口。
- **操作：** 写脚本，导入或录制获准音频；试听真实声音，查看波形，剪切、分段、排序、删除或换源，编辑人声/音乐/效果混音；管理说话人、章节、转写与时间码，调整音量和适用质量参数，再导出并试听节目。
- **系统处理：** 保持脚本、转写、音频片段和时间位置的一致关系；AI 可做转写、建议和获准生成，手工转写与编辑始终可用。文字改了不表示声音已重录；明确标出待替换音段。System Read Aloud 只是朗读预览，不能冒充播客成品。
- **成果：** 可听的真实音频节目、完整可编辑工程，以及对应脚本、章节和转写。节目时长、响度和输出质量按真实音频核验；不得循环、静音填充或截短来凑成果。
- **保存与恢复：** 保存脚本与音频版本，关闭重开恢复片段、位置、章节与混音；替换一段后正确移动后续内容，支持撤销/重做和旧版恢复。导出失败不损坏已保存工程和上一次可听结果。
- **可选联动：** 可引用独立研究、文稿或业务材料，也可直接录制/导入开始。独立路径和从业务续接路径分别验收。

正常制作不要求额外勾选“这是demo”才能编辑或导出；真实的文件选择、素材权益、权限和外部发布审批继续执行。视频项目转入音频工作时保留原项目及其轨道/叠加层，明确处理范围，不因切换模式静默丢弃内容。

#### 8. 内置浏览器：在原工作中查阅和操作网页

- **入口：** 点击原帖/引用的“查看原文”，或从现有浏览器入口打开获准网址。不需要先建立 CTH/BMP 任务，也不会因此启动通用电脑控制。
- **操作：** 内置浏览器像普通浏览器一样使用（参照 OpenAI 应用内浏览器）：地址栏、前进后退、刷新、多标签页、可折叠；采集在系统后台运行，登录/查看/点击等页面操作都在内置浏览器内；登录失效时所有平台都弹产品内登录窗口，登录后任务续跑。用户明确选择人工接管时获得独占控制，可停止并返回原工作；外部浏览器只作用户可选的查看原文跳转，不采集。
- **系统处理：** 复用唯一受控浏览器会话、动作与真实画面通道，保持身份/权限、人工接管租约、取消及恢复。自动采集静默后台运行，不自行弹窗；不读取个人日常浏览器身份，不绕过站点登录或挑战。
- **成果：** 能核对实际原文并完成获准网页步骤；若用户选择保存网页资料/笔记，则走既有资料与成果合同。浏览页面本身不等于正式采集、来源权益已审定或外部操作成功。
- **保存与恢复：** 返回时恢复原任务、筛选、选择和阅读位置；获准保存的笔记/引用可重开修订。会话中断时保留任务和已保存成果，重新核实登录/权限后继续，不能假称过期会话已恢复。
- **可选联动：** 研究、CTH/BMP、文稿及媒体引用可打开同一浏览器；受控网页辅助不扩展为操作系统键鼠、任意桌面应用或 Agent Zero GUI。

#### 9. 每条工作都共用的资料、结果与恢复规则

**工作区首页与导航（2026-10-12 PO）。** 打开工作区直接进入聊天/任务界面；复用 ACC-03 与 AI-01 同一输入、对话、草稿、上下文和成果合同。导航栏提供 CTH、BMP、Shared 独立研究、提案/视频/播客制作、内置浏览器与 SYSTEM 既有入口。聊天采用 GPT 与 Grok Bot 中经官网操作说明/获准 REA 核实的适用优点，包含任务输入、附件、上下文编辑、分段回复、智能 UI、停止/续做、结果引用及保存恢复；按序境原创 Experience 呈现。进入某能力不必先让 AI 执行一轮，无模型时仍能从同一导航完成正常业务。四端角色、独立制作、来源权限和完整验收不变；官网仍承接介绍与进入工作区。

**采集与资料呈现。** 用户选择主体/品牌/主题、明确范围和可选时间，系统接收获准平台、公开网页、上传或导入的数据；原始观察、待核验与正式接收分别可辨。无统一“2026-01-01起”的硬截断。六主平台不是数据上限，词条随时间/品牌/活动/事件增补并保留原词。平台与公开网页类别同权，不等于每条内容质量相同。一个平台受限不阻塞已有获准数据的研究、分析和制作。

资料应显示真实封面、正文、作者/来源、原帖、原生发布时间与采集时间、实际点赞/评论等维度及缺失原因。未知显示“—”并与真实零区分。初采最多一张代表封面，其余媒体位置和后续处理能力保留；没有观看/解析的部分明确标记，不宣称已理解全部内容。资料按用户任务组织，不复制社交平台信息流，不用后台诊断或数学输入表替代用户成果。

用户可以核对国家/市场、别名、商业体/门店/租户关系和身份候选；看到各平台可用、需验证、已取得、待核验、正式接收、待分析、失败/恢复等真实阶段。获准时选择刷新周期，暂停或取消任务、重试或从检查点继续；自动持续采集必须沿现有明确启用规则，不因浏览原帖自动启动。Instagram、Facebook、微信公众号、小红书、抖音、X 的实际覆盖分别呈现，公开网页、RSS/Atom/Sitemap、文件导入等同样进入共同来源体系。某路径缺会话或验证只限制该路径，不能虚报成功或阻塞其他已准入工作。

**报告与智能交互。** 报告首先回答用户问题，再提供依据、对比、方法口径、局限与可操作建议。图表、比较表、阅读器、编辑画布与时间轴按任务选择；简单问题用清楚文字。后台可逐步返回有用结果，明确尚未完成部分；用户已编辑的内容不被后续返回覆盖。方法、样本/遗漏和计算假设可查看，但不成为必填工程步骤。

**行业材料与数学方法。** 按实际问题采用有出处的行业案例、机制、结果与反例；资料不足时说明受限结论，补充能改善当前结果的材料。论文方法在后端按假设和适用性采用，业务参数来自真实数据或用户明确声明。相同原则用于研发：先固定问题/约束，检查反例与结果，审查适用证明；不把名称、引用、有限枚举或工具安装当成整篇算法或模型能力。

最新直接 PO 的 REA 研究授权覆盖各 Owner 对当前功能所需网站、App、GitHub 前沿
实现的定向解析和采用，小红书、抖音及 AI 机器人仅为例子。对采集缺失核查真实页面、
允许接口与字段/分页/恢复路径，修复既有 Collector；不能用推断补造原始数据。
具体采用沿现有 Source Owner Index，保留身份、来源权益、许可及外部效果边界。
普通产品流程不展示内部数学/模型推理操作台，后端产出有用的分析后报告/成果；
AI 聊天可提供面向用户的分析说明和工作进展，其余页面保留真实业务约束、来源与
不确定性和后续操作。AI 不可用仍能完成对应基础任务，真实计算与真实模型收益分验。

**2026-10-12 PO：缺口必须解决，不能留空交付。** 每个已批准能力的资料不足、规则
冲突、实现/接线缺失和未验收项，必须在既有 Owner 成果卡落实具体问题、当前解决
动作、输入和验收出口，连续处理；不能以空白、未验证或暂无反馈结束研发。缺少
真实用户评价时，补查对应官网、帮助、演示、更新记录和可靠评测，形成有依据的
适配判断，不能把官方宣传或单例评论写成用户共识。业务事实未知仍如实保留，
不编造数据、不绕过权限。真正不可解除的外部阻塞须有证据、影响和恢复条件，
独立工作继续。必需缺口未闭时，不宣称对应任务或全产品完成，不通过缩减范围、
把必需修复标为 DEFER 或新建另一套规划消除未完成项。

**AI 与产品增强检索。** 复用现有资料/研究检索和唯一 AI Gateway：按 actor、
workspace、Subject/BrandFocus、来源用途/撤回和版本先过滤获准集合，再以向量
余弦相似度与 BM25 并行召回，按稳定来源/片段身份融合去重，由已准入交叉编码
Reranker 对查询与候选二次精排。不同量纲分数不直接相加；余弦重排、字符串权重
不冒充交叉编码模型。精确编号/实体另行匹配，BM25 不代替身份确认；排名只表示
相关性，不是事实可信度或业务准确率，不按平台类别降权。模型/分词/索引/配方与
资料版本可追溯，失效来源排除。无模型时词法和精确检索仍可完成正常工作，但
不能把降级当完整 Hybrid + Reranker 验收。用户看到资料、引用及成果，不配置
向量、算法或内部参数。不新增资料库、模型网关、事实源或未授权费用/模型服务。

用户可检索、阅读、比较案例的行业/市场/时间/条件与实际结果，选择适用部分加入报告或方案并保留引用。行业案例资料与 CTH 运营 Case 是不同对象：前者帮助理解经验，后者记录自己的业务问题及处理，不因读过案例就生成已执行的业务事实。

**AI 与持续改进。** AI 可在所有适用路径辅助理解、分析、建议、生成和受控网页步骤，输出可接受、修改或拒绝，不替用户确定事实和外部效果。无模型时保留普通计算/编辑/手工判断与所有适用保存恢复；AI 专属动作局部说明不可用。用户反馈、正确与失败案例进入已有评价/学习流程，经过来源权益、质量、独立对照和批准才用于学习或晋升；不自动训练、不修改原始事实。

模型可用时，用户可在原任务内描述目标、附上材料、要求解释或修改；现有 AI/Agent 能力复用该任务上下文，调用获准工具，逐步给出有依据的结果。用户能检查依据、直接编辑、拒绝建议、取消或继续，成果仍保存到原工作。用户不需要把数据搬进另一套 AI 产品；人工接管、外部效果审批和不确定结果的恢复保持明确。

**工作接续。** 用户通过历史任务/项目/成果重新打开，不需复制内部 ID。草稿、已提交版本、导出结果分别显示；未保存或提交结果不明时明确提示。重试优先读回原请求，避免重复成果与外部效果；恢复旧内容形成可追踪的新版本，不删除历史。来源撤回、权限变化、预算变化提示真实影响，只应用用户确认的修订。必要的登录验证、文件重新定位或数据缺口给出具体恢复动作。

**共同管理。** 搜索、偏好、语言、中英韩、无障碍、通知、任务状态、权限与设置继续属于完整产品；通知应打开对应工作，设置实际生效并可恢复。产品账号重构不成为新增的工作入口障碍，既有服务端权限仍执行。Skill 商店/GitHub 等已批准增强保留各自授权；它们不成为普通工作必需，也不因此批准外部模型或费用。

**使用表面。** 官网负责产品说明、帮助、真实示例和进入工作区；Web Workspace、Windows/macOS Desktop 与 iOS Companion 按既有角色并行建设，共用一个 Product Core，后三者共用现有 Flutter `app/`。移动端按查阅、审阅与接续等既定角色适配，不压成一张桌面长页。已有后端合同直接接入；缺少的绑定保持 OPEN/UNBOUND 并沿现有 Owner 补齐。各端按本端任务与运行证据独立验收。原生 Android/Linux 不再是交付目标，已有资料/源码保留，Linux 服务端和窄屏浏览器支持不受影响。

#### 10. 独立使用和可选联动的确认对照

| 用户工作 | 可以独立完成 | 只有用户选择时才联动 | 始终需要 |
| --- | --- | --- | --- |
| CTH | 商业监测、分析、决定、行动/结果记录与报告 | BMP比较、独立研究、提案/视频/播客 | 实际主体/时地、获准来源和相关业务权限 |
| BMP | 品牌市场研究、比较、Campaign管理和评价 | CTH场所关系、研究、提案/视频/播客 | 实际品牌/市场范围、可比数据和相关权限 |
| 独立研究 | 导入、检索、笔记、引用、研究报告 | CTH/BMP、文稿/视频/播客、获准学习 | 工作区/资料权限、适用来源用途 |
| 提案/文稿 | 空白写作、编辑、审阅、保存与导出 | 业务Brief、研究引用、转为媒体脚本 | 工作区/项目权限；外部事实/素材按实际需要核验 |
| 视频 | 素材导入、剪辑、预览、渲染、工程保存 | 脚本、研究、业务任务、Campaign | 获准素材、可用媒体处理与项目权限 |
| 播客 | 脚本/录音或音频导入、编辑混音、试听导出 | 行业研究、业务任务、品牌节目、视频音轨 | 获准音频、可用处理与项目权限 |
| 内置浏览器 | 打开获准网页、人工操作、笔记和返回 | 原帖/引用、资料捕获、受控网页辅助 | 浏览器任务/会话权限和实际站点访问条件 |

五轮架构是研发与验收顺序，不是所有用户必须执行的流水线。每项能力既验独立正常路径，也验已批准的组合路径；不能用一条 CTH/BMP 示例替代整个产品，也不能让所有内容制作等待采集覆盖、研究或模型训练。

本稿与原验收范围对应如下，仅作导航，不新建清单或改写验收定义：资料与采集 = J1/U01–U05；CTH = J2/U06–U09；BMP = J3/U10–U12；提案 = J4/U13；视频 = J5/U14；播客 = J6/U15；研究与 AI/学习 = J7/U16–U20；浏览器、工作接续、设置与四表面 = J8/U21–U25。R01–R15 的完整安全、运行及跨域依赖继续采用 [Source Owner Index](LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md) 原映射，44屏依现有详细规格验收，不以本稿简述代替。

#### 11. 新增解析成果如何优化用户工作（采用方向已确认，实施仍待验收）

已接收本轮 Claude/Grok Bot/剪映/WPS 解析与原创适配包。这里采用的是经审阅的操作方法与原创适配，不宣称恢复厂商云端模型、私有算法或复制完整软件。REA 是研发分析工具，不要求最终用户安装、运行或每次调用它；Cursor 后续解析已取消，早期材料仅保留。

| 本批已有材料与适配方向 | 应怎样改善上述真实工作 | 接到哪个既有能力 | 当前仍需证明 |
| --- | --- | --- | --- |
| Claude/Grok Bot 客户端的任务、工具和上下文静态映射；原创待执行计划 | 用户给目标和材料后，能查看计划、改动建议、执行状态、取消/继续和成果；上下文跟随原工作，已做内容不丢失 | 现有 Task/Plan/PlanStep、工具登记、Agent/Permission 和版本化成果 | 实际调用者、安全和恢复接线；静态映射不能证明云端智能，也不恢复电脑控制 |
| 原创带版本/hash/diff的局部编辑适配 | 用户看清将改哪里、保留什么，确认后只改目标内容；资源已变化时提示冲突，不覆盖新编辑 | 原 Content Project/SavedWork/Artifact 及编辑 Owner | 各实际对象的应用、读回、撤销/恢复；不能把通用修改函数当全产品已支持 |
| 剪映程序观察与原创 Timeline 编辑适配 | 视频/播客共用既有媒体制作入口，完成拆分、剪切、轨道/声音、字幕及批量编辑；保持先前素材和版本 | 现有 Timeline、媒体处理/渲染、C4 和 Shared Artifact | 完整用户编辑、预览/试听、渲染/导出和恢复；私有工程格式、复杂特效和生成算法未由解析包取得 |
| WPS 程序与公开接口观察；原创 DOCX/XLSX/PPTX 适配 | 用户在既有资料/成果流程导入和使用适用办公文件，保留可编辑文字、表格与演示内容；将真实输出作为成果/附件保存、修订、重开和导出 | 现有 Importer、报告/提案、SavedWork/Artifact，沿已有成果入口 | 各格式内容/主部件/类型、安全限额、依赖许可、实际客户端打开与格式保真；不是新增完整 WPS 套件，也不声称所有专有格式/宏/嵌入对象可用 |
| 已有媒体入口与附件补丁 | 移除无业务意义的demo勾选及DOCX-only阻挡，让用户直接完成正常制作/保存；保留真正授权检查和旧成果读取 | 原媒体API/SH-01规格、SavedWork、Permission | 与主仓来源用途等并发修改逐处合并；历史兼容、安全、实际成果版本和正常用户路径仍需验收 |

这些能力必须随序境既有工作流运行，不停留为离线样例或单独 wheel。接入优先复用已有 Owner，逐处审查补丁，不整文件覆盖当前工作；验证许可证和已有依赖后处理必要缺项，禁止把研究工具目录硬编码为用户运行前提。解析没有取得或没有证明的能力仍在原缺口内，不凭包内检查数量升级为完整实现。

#### 12. 最终要求与当前未完成项（有界证据，非全产品新审计）

下表依据本轮已读源码、既有回执及 2026-10-11 本机操作记录。它不会把旧证据当同版本重验；未核实不等于能力不存在，也不等于已通过。完整实施/运行明细继续归 [CURRENT](LUMENIS-CODEX-TAKEOVER-CURRENT.md) 与 [Real Delivery](LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md)。

| 工作 | 已有依据 | 仍需完成/证明，不能由本稿升级 |
| --- | --- | --- |
| 资料采集与可视呈现 | 已有真实来源、规范接收和浏览器后台修复源码及部分历史运行证据 | 六平台各自持续采集、身份/刷新/恢复和当前产品视图完整性；已有数据不能等这些全部齐全才使用 |
| CTH | 本轮真实资料 SourceBrief、确定性样本统计、方案选择及中断/重开/恢复记录 | SourceBrief/统计还不等于完整运营分析；正式成果引用用途、保存/修订/版本读回链修复正在本地，尚未据此完成同版运行/用户验收；正常用户不应填写论文表单 |
| BMP | 本轮真实品牌资料、方案选择及恢复记录 | 有用的品牌市场分析、正式成果保存/修订/重开和真实用户入口仍需连同来源用途修复验收；Campaign计划不等于已执行或有效果 |
| 独立研究 | 已有导入、SourceBrief、引用、SavedWork/Artifact实现与部分回执 | 无CTH/BMP前置的独立入口、案例采用、准确覆盖展示、引用撤回和完整保存恢复需同版实操；材料存在不等于已研究采用 |
| 提案/文稿 | 已有提案与Word导出、版本/引用实现 | 直接空白/创作要求起步、完整编辑和实际导出/重开/修订的独立用户链未在本轮重验，不标完成 |
| 视频 | 已有时间轴、换源、媒体处理/渲染及历史成果；有限渲染路径限制明确 | 独立新建到实际编辑、播放、导出、旧版恢复的完整用户链和批准编辑范围仍待验；单轨有限路径不能替代全部承诺 |
| 播客 | 已有计划、音频换源重排、导出与历史音频成果 | 独立节目入口、实际录音/导入、波形/剪辑/混音、脚本音频绑定、试听及保存重开恢复仍须同版验收 |
| 内置浏览器 | 已有SYSTEM受控浏览、任务与笔记保存源码和有界旧回执 | 真正网页画面/操作、人工独占接管、安全返回、当前登录身份传递和恢复需同版证明；只读画面或接口成功不足以关闭浏览器目标 |
| AI与数学增强 | 已有唯一Gateway、有限数学计算、研究采用和版本合同 | 完整主算法、适用性、各业务有效增益、实际模型训练/重载/独立评价分别未全闭合；基础链不等待它们 |
| 本轮解析/媒体办公适配 | 接收包、75项清单字节校验与原始说明已核对；包含独立补丁和隔离工程回执 | 尚未正式接入主仓与当前Runtime；较宽回归的PDF依赖和提案API错误仍未关闭；Flutter/真实用户链缺证据，不将示例和工程检查当成产品完成 |
| 全产品与四表面 | 已有44份屏幕规格、客户端与Core源码；44份规格是覆盖基线而非范围上限 | Website、Web、Windows/macOS Desktop 与 iOS Mobile 的真实任务、跨能力正常联动、来源变化影响传播和恢复按端并行建设、独立验收。窗口状态在本地按直接PO指令核验，本稿不证明实现或发布 |

验收依据是用户能否完成上面的工作，而非模块、提交或测试数量。本次未缩减保留的 J1–J8、R01–R15、U01–U25 与44屏；各工作对应原Owner及验收清单，通用电脑控制只有被明确撤回的子要求退出。蓝图确认不升级第12节任何实现/运行状态。窗口工作与依赖安排在[Source Owner Index的完整成果卡](LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md)中记录；[Real Delivery](LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md)保留真实用户与上线门槛。实际窗口按最新直接PO指令与新鲜准入核验；本蓝图不构成派工。公网部署、生产发布、新费用和外部效果仍按各自现有授权门槛执行。

## 2026-10-10 Product Owner amendment — branches and testing reinstated

Scoped development branches and PRs are permitted globally; validate and review before merging into main. This does not create another product or change release authority. Unit tests and integration tests are authorized again for defect reproduction and regression verification. Earlier 2026-10-08 prohibitions against creating, running or requiring these test types, including statements retained below for historical provenance, are **SUPERSEDED**. These tests are engineering evidence, not substitutes for real end-to-end user acceptance, running-service verification, production data, or user outcomes. Testing authorization does not authorize live collection, external model calls, GPU training, spending, deployment, or destructive database operations.

## 2026-10-10：v2 数学能力在五轮内的采用边界

复用用户指定 v2 包与固定 `openai/math@fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb`。现有 Shared Evaluation 内的 16 个类型化计算入口经唯一 Task/API 与 SourceBrief、Permission、SavedWork/Artifact 接入，不建立第二个分析引擎、数据库或 Agent Runtime。现有 Math 采用记录列明逐篇公式、适用假设、有限实现与完整主算法的未闭合项。

| 既有架构轮 | 实际采用与终态要求 |
| --- | --- |
| SYSTEM | 严格输入/资源边界、独立来源和身份核验、幂等请求及已提交任务续接；不能把求解器成功当作整个系统成功。 |
| CTH | 声明运营安排/分配的对象、资源与权重，计算有限可行情景；来源仍为来源，情景概率不是经营事实或因果。 |
| BMP | 在真实品牌范围内比较明确声明的方案；复用相同计算/成果合同，不能借 CTH 范围获得品牌授权。 |
| Shared | 成果保存、父子修订、独立读回、导出与恢复；原问题/参数/版本及论文适用限制随成果保留。 |
| Agent Groups / 自研 AI | Agent 消费同一受控计算入口；单独记录训练、checkpoint、独立新任务收益与晋升。确定性求解结果不计入模型能力。 |

基础任务无需 AI。精确有理数恒等式、有限枚举、数值 exp/log、原创有理区间适配和固定 theorem 的 Lean 重放分别验收。完整一般算法保持未完成，不因一个有限计算或编译成功而缩减原要求。115 的理论大常数须先算成本，不能调小常数继承原概率保证；107 没有实测乘法瓶颈和生成程序时不得替换 BLAS/CUDA。官方上游撤回/修订记录属于版本准入，非全部论文正确性认证。


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

保留 J1–J8、R01–R15、U01–U25、既有44份屏幕规格及原资料/设计/历史证据全部要求；44份规格不是新增映射屏幕或官网内容家族的上限。
Public Website、Web Workspace、Windows/macOS Desktop 与 iOS Companion 并行建设，按各自角色和真实任务独立验收；单端结果不替代其他端或全产品闭环。
不以本次文档提交宣称 SYSTEM、任一表面或全产品闭环。
不新增费用、账号、模型服务、训练或部署；按2026-10-10批准恢复隔离单元/集成回归，
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
Shared Capability Layer is independently usable and also serves both domains. Agent Groups coordinate through
the existing Agent Runtime and never become another business or security owner.

**Multi-surface product direction:** Public Website and one Flutter `app/` for
Web Workspace, Windows/macOS Desktop and iOS Mobile share one Product Core.
All four surfaces build in parallel with their approved roles and separate
real-task acceptance. Build the complete task-shaped frontend without waiting
for all backend work; bind available real APIs/Core immediately, and track
missing bindings as OPEN/UNBOUND for incremental connection through existing
owners. The 44 existing screen specifications are a baseline, not a page or
product-scope ceiling. No new product, owner, design system or paid service is
introduced. Platform availability and acceptance are verified separately from
this target. This 2026-10-11 update supersedes the 2026-10-08 Website/Web-first
execution order; the historical receipt remains provenance. Approval:
`evidence/approvals/PO-20261011-WHOLE-PRODUCT-REUSE-EXPERIENCE.json`.


## 2026-10-09 AI 非依赖原则与分层验收

### 数据分析必须独立运行；数学研究落实到分析方法

最新 PO 明确：数据分析不可被 AI 阻断。已获准的 Source/Evidence/Canonical 数据经现有 CTH/BMP/Shared Owner 完成去重后的计数、时间聚合、既定指标、可比范围的比较、规则判断、人工判断记录及报告；模型、GPU、Gateway 或外部 AI API 不可用不应阻断这些基础操作、下游工作流、保存、修订、重开或恢复。不得以“rule-based/AI optional”标签和空文本冒充真实分析，也不得用模型答案填补原始数据缺失。

基础结果携带输入来源/版本、主体与市场范围、出版/事件/采集时间、指标定义、单位、分母、实际样本数、遗漏与不确定性。跨平台类别同权，具体口径不可比时明示；NULL/UNKNOWN 与真实零分开，分母缺失/为零时按指标定义给出不可计算状态，不虚构比例或趋势。缺少必要证据只限制相应结论；已能完成的分析必须形成有用且可续接的成果。

OpenAI Math 已核读研究直接服务上述分析：先区分可行性、优化、计数和抽样；固定业务约束与基线；区分条件列联表均匀性与真实样本代表性；报告真实来源覆盖、抽样框与偏差；比较总处理成本而非只比较查询次数。方法通过现有计算、报告和评价路径采用，详见 [现有 Math 采用记录的本次落实表](evidence/round-15/OPENAI-MATH-ADOPTION-20261007.md#2026-10-09-数据分析无-ai-阻断与数学方法落实)。不新增数学框架、第二分析引擎或测试体系；复杂算法在不满足原文假设或无当前收益时仍 DEFER。

AI 解释、语义关联、建议和生成单独记录输入、版本、状态及评价，不改写 Canonical，不把可选增强失败提升为基础任务失败；真正的 AI 专属任务仍可诚实 UNAVAILABLE。现存 `ai_task_engine.py` 的分析实现/失败判定缺口仍须由获准 Owner 修复和真实操作验收；本规则采用不冒称修复或部署。


序境所有基础业务能力在无模型、无外部 AI API、无 GPU、无推理服务时，仍须完成正常任务。AI 只增强效率、理解、建议、生成及辅助决策，不生产事实，不拥有 Canonical Data，不是核心业务链必经条件。AI 专属动作缺模型可准确标为 UNAVAILABLE，不能因此阻断普通任务。安全/权限拒绝、来源权益失效和真实输入缺失仍是有效阻塞，不能伪造或绕过。

| 领域 | 无 AI 必须完成的基础任务 | 可选 AI 增强 |
| --- | --- | --- |
| C1 数据采集 | 真实采集、来源记录、去重、入库、刷新、恢复 | 页面理解和提取辅助 |
| CTH | 监测、指标计算、事件、风险规则、人工判断记录、报告 | 解释、趋势推断、建议 |
| BMP | 品牌资料、传播分析、竞品比较、Campaign 管理 | 创意、洞察、方案辅助 |
| Shared 研究 | 导入、检索、引用、归档、人工研究、导出 | 语义检索、摘要、关联 |
| 提案/视频/播客 | 人工编写编辑、素材处理、播放、渲染、保存、导出 | 生成、转写、剪辑建议 |
| 产品内浏览器 | 网页浏览、确定性网页操作、人工接管、任务返回与恢复 | 同一受控会话内的网页理解与步骤辅助 |
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
| 四 Surface | Public Website / Web Workspace / Desktop / Mobile Companion | Desktop App 是 Desktop 的描述性名称；Flutter 是实现技术；四表面按各自角色并行建设、独立验收 |

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

Latest PO: F builds the complete task-shaped frontend directly from current Experience, screen contracts and source across Public Website, Web Workspace, Windows/macOS Desktop and iOS Mobile in parallel. Website remains the public presentation surface; one Flutter `app/` serves Web/Desktop/Mobile over the same Product Core. No separate design draft, Figma completion or M DESIGN_READY approval is a coding prerequisite. Update existing specifications alongside code. Bind available real APIs/Core immediately; connect remaining existing-owner dependencies incrementally and keep missing behavior OPEN/UNBOUND without mock results. Existing design artifacts and review states remain provenance, not proof of implementation. Do not authorize implementation from a PDF, screenshot, fixture, Figma frame or a generic swapped-title renderer alone; the current contracts and direct PO construction instruction govern. Keep each surface's role, actual user operation and acceptance evidence distinct. The 44 existing specifications are a baseline, not a ceiling. Android/Linux native clients are no longer delivery targets; preserve historical source/evidence. Linux server/CI and browser access remain separate. No new product, owner, design system or paid service is introduced. This 2026-10-11 rule supersedes the 2026-10-08 Website/Web-first order. Approval: `evidence/approvals/PO-20261011-WHOLE-PRODUCT-REUSE-EXPERIENCE.json`.

一、闭环后，用户实际得到什么

用户既可以独立研究、编写提案/文稿、制作视频或播客，也可以提出商业或品牌任务。选择业务任务时，提供目标、主体、市场、时间、预算与已有资料。序境能理解文件和材料，补充授权范围内的真实数据，形成有依据的判断与可执行方案，按需要选择继续制作文稿、视频或播客。用户改变预算、来源或创作要求时，系统定位受影响部分、提出修改、经确认后应用，保留旧版、修改原因与可回滚关系。用户可以保存、关闭、换端、重开和在中断后继续，不必重述目标或重新选择同一批材料。

**Platform-native Source → Source/Evidence/Canonical → LUMENIS presentation → Open Original → Return** 是同一产品闭环。平台内容被正式接收后，序境保留原生正文、作者、来源平台、原始 URL/locator、发布时间、采集时间、原生指标、许可与 Evidence lineage，但用户看到的是按当前 CTH/BMP 或独立 Shared 工作语义和 LUMENIS Experience 重新组织的呈现，不复制来源平台 Feed、视觉外壳、无限滑动或自动播放。获准用户可从记录、事件、趋势、案例、风险、报告或创作引用中点击“查看原贴 / Open Original”，默认把经过校验的公开 HTTPS 目标放在序境内置受控浏览器中，用户也可明确选择外部浏览器，并在返回时恢复原任务、GLOBAL/FOCUS、筛选、选中对象和滚动位置。普通原贴跳转不读取本地 Cookie、不静默登录、不启动采集、不生成新 Evidence、不发布也不写外部状态；受控网页导航与证据捕获继续只归 SYS-06。

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

唯一Experience §38细化八项要求与验收；44屏在既有screen-specifications中明确各自任务和视觉动线，既有文字草图同步增补，四端角色见Multi-Surface Decision。整体视觉依已批准研究与当前任务；手绘彩绘限于图标及适合页面元素，不固定二维或三维。保留丰富且有用的交互、中英韩、无障碍及操作端避免不必要整页滚动。该蓝图定义闭环目标，不能据此把规则更新等同功能已上线或屏幕已验收。

二、锁定的产品组成

CTH：商业主体运营。覆盖场所、场内品牌/业态、事件、消费者反馈、风险、案例、运营决策、活动和结果评价。广州太古汇、深圳罗湖万象城用于代表性深度验收，不是产品默认范围。

BMP：品牌与市场。覆盖品牌、市场、竞品、消费者、创作者、传播、内容与Campaign。Nike、Le Labo用于代表性验收，不是品牌目录上限。

Shared Capability：可独立使用的资料导入与研究、引用、内容制作、文稿/视频/播客、Artifact与导出、评价和学习。用户可直接进入制作，CTH/BMP也可调用或消费成果；业务语义归各自领域，制作不以业务任务存在为前提。

SYSTEM：采集、产品浏览器、Scheduler、AI Gateway、Agent/Skills/Memory、数据库、Permission/Action Firewall/Effect Fence、配置、运行恢复和可观测。各能力沿已有Owner升级，不再增加平行的采集器、数据库、模型网关、权限或设计系统。

默认工作范围保留GLOBAL / ALL。进入具体商业或品牌工作时，明确选取相应Subject或BrandFocus；Clear只清当前聚焦，不抹去已保存任务的范围、权限与历史。

三、四个入口的闭环形态

| 入口 | 用户用途 | 必须接通 | 保留的边界 |
|---|---|---|---|
| Public Website 官网 | 理解产品、查看真实能力与操作演示、进入工作区、帮助/联系 | 文字、交互、可控操作视频、真实可用入口；中英韩内容 | Cue为官网视觉与节奏主参考，319b视频仅用于官网；演示必须标明范围，不拥有业务数据或权限 |
| Web Workspace | 浏览器中完成研究、方案、制作、审阅与继续工作 | 同一Core、资料、任务、版本、引用、编辑和恢复 | 采用现有Flutter Web；不能把旧Jinja/static界面重新当第二产品 |
| Desktop App | 本地媒体处理、专业编辑、文件操作与高级工作 | 同一任务和版本；视频/播客真实播放器、横向时间轴、导出、重开恢复 | 不另建业务数据库；本机工具能力与服务器能力分别反馈 |
| Mobile Companion | 查看、审阅、批准、轻操作、通知与任务接续 | 真实任务/成果/版本、适配触控、返回路径与权限 | 按移动任务重组，不缩小PC界面，也不冒称所有桌面重计算能力已在手机运行 |

四端共同遵守：整体视觉方向依据用户已批准研究、当前任务与屏幕合同，不固定二维或三维；手绘彩绘用于五位架构身份/功能图标及适合的局部页面元素。线性功能glyph、彩绘身份图标、第三方来源icon分层；颜色丰富但不滥用；人物根据脚本或描述生成；AIGC呈现按任务设计，不使用助手虚构的70–80%/20–30%固定配额。除官网外避免无必要的整页纵向滚动，必要长文和无障碍操作不被截断。增加有用交互，不做换标题的模板页。

产品账号体系、用户与创始人两种开发者模式、六项商业能力、视觉、Logo和角色均在工程闭环内。免费 Google 登录和邮箱验证码为账号登录的明确例外；Apple 登录待开发者账号开通后启用。设置分区可借鉴成熟产品的信息结构，视觉与资产采用序境原创表达。不设账号墙，服务端权限、平台授权和效果控制继续执行。仅真实用户验证及付费/授权来源安排在上线后；既有工程操作、安全、恢复验收仍须完成。

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

P0执行入口裁决已经收敛，不再作为单独待办批次：`AGENTS.md` 是唯一执行路由；本蓝图是唯一产品蓝图；Source Owner Index 只负责定位，CURRENT 只记当下事实。`README.md` 的四入口说明以当前源码校准：Public Website 承载官网，Flutter 同源承载 Web Workspace/Desktop/Mobile 并共用 Core。source-bound/v3 是当前新增来源绑定合同，v1/v2 仅作兼容；业务数据使用 canonical 数据库，符合 §9 条件的 SYSTEM 操作队列是受限例外；研发只使用当前有效入口和真实版本；具体历史证据不承担执行指令。现行能力 locator 继续按本任务词和 Source Owner Index 路由。发现新的当前源码冲突时，直接修正对应所有者文件并与该成果同轮发布，不新建平行规则或审计队列。

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
  and development; calling code deleted; no calls, probes, auto-discovery,
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

For each vertical delivery slice, record the surface matrix over one Product Core contract: Web Workspace primary/available; Desktop enhanced/exclusive; Mobile view/notify/approve/light action; Public Website explanation/demo only. Layouts need not match, but business meaning and state semantics must. Build and evaluate the four surfaces in parallel; accept each on its actual platform through its own real task and runtime flow. Record unavailable device/runtime combinations as `UNVERIFIED`, and do not claim a surface or OS release until its build and runtime flows pass. One surface's closure does not gate another surface's construction or acceptance.

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

The production import gate parses Python import nodes and rejects exact retired owners. It excludes tests, audit prose and comments from the production dependency decision, while actual migrated behavior, preserved data and recovery require real runtime evidence under the existing owner. The 2026-10-10 PO instruction restores isolated unit/integration regressions, alongside compilation/static/security/data checks and real product E2E; historical tests/failures remain preserved.

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

### 2026-10-09 来源类别同权与已有数据优先闭环

Product Owner 直接更正（2026-10-11复核为既有要求，不另建权重机制）：所有平台数据与公开网页数据的来源类别基础权重相同，不得仅因来自网页、某个平台或某个平台尚未完善而降权、弃用、推迟分析或阻断产品闭环。采集工具不同不形成不同等级的产品数据；全部沿现有 Source → Evidence → Canonical 接收，使用同一套来源质量、身份、时间、权益和用途规则。本条贯穿采集/接收、检索与样本选择、后端分析、CTH/BMP判断、Shared研究/制作引用、报告导出及Evaluation；下游不能按平台名或公开网页类别隐式降权，界面也不能营造类别高低等。类别同权不混淆品牌自述、消费者反馈、经营事实、搜索摘要与原始来源，也不使未经核验的材料自动成为事实。

真实采集、原始记录持久化及刷新/恢复能力已有适用证明后，当前获准执行的 Owner 必须优先用已有、适用于任务且获准使用的数据打通：既有工作流 → 数据分析/分类 → CTH/BMP 判断与使用 → Research/SourceBrief → SavedWork/Artifact → 保存、修订、重开、恢复、来源追溯与 Evaluation。无需重新采集已有有效来源，不等待六平台全部完善、全部字段非空或全域覆盖后才接通工具流；基础正常业务链不等待 AI。

某平台授权、会话、字段、分页或采集实现的缺口，只阻塞该路径及确实依赖其缺失证据的结论；其他合法已有资料和独立正常工作流继续。真实缺少任务必需证据时，明确受影响结论及恢复条件，可完成的有用部分仍保存并可续接。完整六平台/既有其他平台的目标、未知值和各平台未完成项保留；用公开网页跑通任务不冒充某社交平台已验收，也不宣称全球覆盖或整个 SYSTEM 已闭环。此规则变更不自动恢复窗口或扩大权限、费用及外部效果。

### 2026-10-08 全产品逻辑收敛与逐步交付

2026-10-11 PO重申：适用范围是整个产品。每个既有Owner先核对当前蓝图/合同、原资料、已有源码及真实调用；已有正确能力直接复用，冲突与旧有效调用定向修正，只有证实缺口才在原Owner补齐。用户询问“有没有”不能被解释成新增功能授权；未找到或未读完只能记未核实。沿原任务卡记录差异与采用，不另建全产品规则、权重表、执行框架或重复候选。外来方法、解析、工具和组件须转化为现有产品输入、处理、权限、结果及恢复合同；只有安装或文档不算采用。其用户呈现遵守唯一Experience，原始证据和网页内容保持真实。

同一用户目标沿已有Task/Brief携带actor、GLOBAL/Focus、资料、来源用途、时间/预算及版本；读取全域不强制选择参考主体，特定业务动作再按真实合同确定范围。数据缺口按任务影响说明，普通编辑和确定性计算不依赖模型服务。研究结果、决策、文稿及媒体使用可回读的既有上游引用；移交时不要求用户重述目标或重选材料。

先形成有依据的有用部分，再按同一任务增量丰富；表现由任务决定，交互控件使用已批准本屏组件和动作。最终完整性、事实准确性、用户修改和保存版本不得因提前显示而降低。Experience §38定义分段校验、更正、等待时间与恢复；现有Task/Source/Evidence/SavedWork/Artifact/Timeline分别保持唯一所有权。

来源/预算变化时沿已有引用/父版本找出受影响成果，未能追踪的依赖明确未知；局部修订由对应文稿/媒体Owner执行，不把通用SavedWork修订用于绕开task-owned合同。Action回执、Outcome观测与Evaluation分别存在，学习与模型晋升仍单独准入。产品代码拥有采集和持续任务，不依赖Codex代操作。

本轮[全产品逻辑审阅记录](evidence/round-15/PRODUCT-LOGIC-REVIEW-20261008.md)覆盖J1–J8/U01–U25的逻辑与交接，给出已发布源码断点及顺序。它是本蓝图的取证材料，不是第二执行蓝图。改进首先收敛现有连接与正常结果；不新增产品能力家族、平行候选或无收益研究。已获授权的窗口按本地ledger、真实工具回执和 fresh admission 确定实际执行状态。

### 已核读研究的及时产品采用 — 2026-10-08

原始资料是既有能力的知识与可信度基础，不能只沉积成文档或等待训练。M 对有当前产品收益的已核实结论，及时在本蓝图、Source Owner Index 和该能力的既有详细合同中形成同一采用决定，随同版本发布并通知当前受影响执行窗口。未读原文、部分阅读、研究建议、源码实现、运行验收和 MODEL_TRAIN 各自记录，不互相晋升；已有正确实现直接复用，不另造框架或重做全量研究。完整材料范围仍保留，未读/缺失不能由抽样或目录覆盖率冲抵。

沿现有 Source→Evidence→Canonical→研究/业务→SavedWork/Artifact→修订/恢复/Evaluation 保留两类信息：原文实际说了什么，以及任务如何使用和限制这些信息。来源版本、精确位置、实际读取区间、时间/地域/样本与方法语境必须在相应既有合同中可追溯；未提供的信息保持未知。宣传指标、互动、作者经验和消费者/经营结果不可相互替代。相似文本不抹去来源身份；材料读取不自动建立事实真实性或用途授权。

当前采用顺序：C1 在自身 J1 闭环落实 Global §10 的真实原文/媒体覆盖、时间语义、来源不丢失和可消费引用；M 在获授权的已有非 C1 成果收敛中核对 C5 来源语境/片段覆盖、C3 比较依据与 Outcome、C4 媒体时间码/版本及 C2 研究与学习准入隔离。暂停窗口不因规则更新自动恢复。C1 不等其余研究完成、另一窗口或 GPU，也不接管下游业务推断；具体缺口和操作随原 Owner 入口更新。采用决定不是新增产品能力或验收通过。

当前 C1 的处理优先级依 Global §10 最新直接指令：主体相关发帖批量取得后立即通过原数据链，关键词/主题后置分析、同步采集每帖只处理一张真实封面；范围/权限/原文覆盖/连续恢复保留。图片与视频的完整内容理解要求不取消：通过既有 SYSTEM Queue/Gateway 和 Shared 媒体路径后处理实际图片、音轨与时间画面，携带原帖/图位置/时间码、版本及实际覆盖供研究、业务和创作消费；封面、OCR、转写、模型解释分别记录，不冒充全媒体已读。不等全量词库、逐图研究或全部平台结束，不复制 Collector 或把未测/未读状态当成果。C1 自行接通既有 SYSTEM principal 的精确内部用途；导入许可、关键词许可与媒体分析/派生保存分别核验，派生结果不改原文权益，也不替代商业报告/引文/训练/导出授权。具体预算、检查和恢复归 Global §10，同一当前数据链不得因必要绑定交回逐函数审批。

### 产品内受控浏览器与任务连续性 — 2026-10-11 校正

沿已有 SYSTEM Browser/CDP/Playwright、Task、Permission 与 SourceTarget 实现真实网页会话。浏览器进程负责网页执行；Core 负责 actor/task/scope/session、动作与来源边界；已有前端负责真实画面、网址/历史/当前状态、人工操作和返回。网页会话与页面可视化传输不是同一层；一张截图、任意 iframe 或外部弹窗均不能代替可操作的产品内浏览器。

自动采集继续无头后台运行，人工登录/验证/接管必须由用户明确发起，复用获准的隔离身份。普通浏览不用 AI；AI 可在相同会话与权限内增强网页理解和受控步骤。用户可停止或独占接管，返回恢复原任务、范围、选中来源和草稿。浏览动作与正式 Source/Evidence 接收分别处理，只有获准保存才生成相应资料/成果版本。

外部浏览器只作用户可选的查看原文跳转，不用于采集、登录或交互；禁止自动外弹、读取个人浏览器档案、暴露 raw CDP、绕过网页安全限制，不能简单删除 loopback 防护冒称 Web 可用。无需通用桌面/OS executor，不安装 Agent Zero GUI 来满足本链。Website、Web、Windows/macOS Desktop 与 iOS Mobile 并行构建并按端独立核验。模型/远端工作机/部署可用性各自据实，不因类比 ChatGPT 承诺关机后持续运行。

工程参考（2026-10-11 核读）：[OpenAI browser environment integration](https://developers.openai.com/api/docs/guides/tools-computer-use-integration#prepare-an-environment) 提供会话保持、浏览器自动化和画面获取的公开实践；[ChatGPT cloud browser](https://help.openai.com/en/articles/20001280-using-cloud-browser-in-chatgpt) 说明独立会话、人工接管和网站/重要动作授权。这里只采用适用的公开原则，不宣称取得 ChatGPT 私有实现，不将其云电脑/付费资源带入序境。

### 全产品数据到成果链升级 — 2026-10-09

Global §10 记录本轮完整直接 PO 命令及原实现落实点：采集授权/原始保留、来源有效性、用途权限、身份候选/确认、业务分析分开，合法未绑定原始观察在原 Source/隔离链持久可恢复，不自动成为主体事实。Shared 保持同一 ID/use/时间/版本/状态；CTH 使用已核验时地关系与反馈，BMP/SH-01 Discover 区分原生热度/样本/推断；Research/Reporting/Evaluation 将可检索引用的真实来源接入同一 SourceBrief/SavedWork/Content Project 的保存、关闭重开、修订、追溯和恢复。SYSTEM 继续原 Scheduler/Runtime/Browser/Permission/Gateway，不因 AI 不可用停止合法确定性工作。

C1 保留采集链及获准必要依赖的源码责任；当前窗口执行状态不得由本蓝图推断。跨 Owner 写入仍由 M/W6 既有预约有界交接；原非 C1 候选、未集成成果及完整资料采用继续保留，实际执行需当前PO指令。仅修数据链影响的现有 Web 消费与状态/来源返回，不重做44屏、不新增架构或队列。六平台各自实证与阻塞分列，至少一个获准平台或公开网页来源通过完整真实操作链；同口径吞吐、延迟、覆盖缺失、身份/数据错误、恢复、成果保存重开须有真实数据，无旧基线写 BASELINE NOT VERIFIED。旧逻辑先追有效 caller 再收敛，全部历史/原件/有效兼容保留。

本规则采用不证明源码已改、运行已加载或用户已验收；最终 A–F 成果、OBSERVED/INFERRED/NOT VERIFIED 和 ACCEPTED 条件归既有 Real Delivery Overlay，保持完整 R/J/U 和当前编译/静态安全数据/真实E2E，按当前批准执行相关隔离单元/集成回归，结果不替代真实用户验收。
