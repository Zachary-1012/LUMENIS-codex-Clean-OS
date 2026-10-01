# 序境全产品前沿研究、升级选择与闭环执行方案

日期：2026-09-29。性质：**研究和能力来源保留；2026-10-02 起按 AGENTS.md 的 C1–C6 执行，J1–J8 不再单独派工**。

本材料不新增产品、Owner、Round 或设计权威；不表示下列升级已安装、已验收或已上线。ADOPT/ADAPT 是研究建议，实际接入仍须经过现有 Owner 的版本、依赖、许可、测试、真实用户工作与回滚验证。国家优先级调整来自本次用户明确纠正；具体基线版本与名单验收需落回现有 Global Contract。

## 1. 结论与目标

序境应交付的是商业运营、品牌市场和专业内容工作的真实结果。当前升级要同时解决五件事：

1. 把来源变成能持续刷新、准确归属、可追溯的数据资产。
2. 让 CTH/BMP 真正消费这些资产，完成判断、计划、执行记录和复盘。
3. 让通用创作、视频和播客分别交付可修改、可导出、可重开的专业成品。
4. 让 AI/Agent 在有依据、有状态、可恢复的工作流中完成任务，并通过实际反馈改进。
5. 让用户从四个产品表面进入同一工作，看到结果、理解缺口、完成恢复。

自研优先落实在业务语义、实体关系、判断方法、工作流、质量标准和产品体验。成熟编解码、时间线交换、转写、混音等通用技术优先复用合适组件；不移植整个第三方产品，不自行研究一套编解码器。前沿方案必须在序境真实任务上比现有实现更有效，GitHub 热度和演示视频均不足以作接入依据。

### 1.1 Product Owner 补充与执行调整（2026-09-29）

1. **单平台采集保留**：用户可在序境 AI 中明确说“只采集某平台”。意图解析形成明确的平台、对象、时间窗、字段和任务目的，经现有 Collector 执行；不得擅自扩大到其他平台。平台不支持、授权不足、解析歧义分别返回可处理的原因；缺少关键信息时只澄清必要项。来源选择与 MANUAL/AUTO 是两个独立设置，单次 AI 指令不自动开 AUTO。
2. **研发身份与用户版政策分开**：本工作站研发、测试、采集、浏览器、恢复仍只使用获准 HK/international allowlist，CN 个人工作账号继续禁止访问。用户版不继承开发者个人身份或固定地区白名单；通过用户明确授权的平台身份、scope、可撤销授权和隔离会话工作。这不是现在解除本机保护。官方 API/OAuth 适配路径必须保留；无资质或缺 scope 为 NOT_CONFIGURED/AUTHORIZATION_REQUIRED，不伪装成已接入或万能全字段接口。
3. **账号安全与保活**：研究已有会话管理与交互节奏，落实最少必要操作、状态检查、官方 refresh、限流/Retry-After、有限退避、断点与去重、风险熔断、人工重新登录、撤销后立即停止和凭据隔离。真实交互等待只用于页面就绪和降低无效操作；不承诺模拟真人能免封号，不伪造指纹、不绕验证码、不规避封禁，也不靠反复探测维持无效会话。无需 Cookie 的路径只承诺实际可得字段，不承诺登录/非登录可见内容永远相同。
4. **需求与文件真正进入分析**：用户目标、受众、约束、文件内容和既有/新增数据进入现有 Import/Research/AI/Creation owners；保留页码/表格/原段落定位、版本与读取覆盖。文件读取失败或截断必须可见，不能仅拿文件名当输入。产物必须体现事实、洞察、备选创意、选择理由、执行方案、评价标准与改稿；不能把检索段落拼接称为创作。广告公司案例作为方法研究，案例自报效果与独立验证分开，不照搬作品。
5. **资讯凝练与事实核实**：原始 Source/Evidence 保留可追溯原文/合法摘录及时间；用户默认获得面向任务的精华、适用范围、影响和待核事项。摘要是有版本的派生结果，绝不能覆盖原始证据。事实主张逐项定位、检查一手出处/时间/独立佐证/冲突/更正；官方来源也是声明来源，不自动等于结论真实。标明已获支持、有争议、未核实、来源过时等状态；模型分数不证明真假，转载同稿不算独立佐证。
6. **数据与业务并行、恢复逐项验收**：中国/全球名单、关系审核、字段和刷新继续建设；J2/J3 可在数据来源明确、scope 正确且足够回答具体任务时立即执行，不等待整个 J1 目录完成。广州太古汇/深圳罗湖万象城及 Nike/Le Labo 是代表任务，不代替覆盖验收。J1–J7 各自验证中断、有限重试、取消/授权撤销、失败状态、产物重开及适用重启恢复；J8 再做跨系统/跨端/发布级恢复与回滚。

官方能力核验（访问 2026-09-29）：[小红书账号开放接口](https://openaccount.xiaohongshu.com/docs/api-reference)提供授权/token/撤销等能力，不据此声称开放全站搜索；[抖音 Web 授权](https://open.douyin.com/platform/resource/docs/develop/permission/web/permission)区分用户授权与无需用户授权接口；[TikTok token 生命周期](https://developers.tiktok.com/docs/en/oauth-user-access-token-management)包含刷新与撤销；[X 错误处理](https://developer.x.com/en/support/twitter-api/error-troubleshooting)作为失败和限流处理依据。只采用各平台实际授予的接口/字段，不将这些服务相互等同。

## 2. 当前基线与本轮边界

研究开始及本轮复核的源码基线：`22e84d112bea547d62f7266d1c6593bb994d1580`，HEAD 与 fetch 后 origin/main 一致；研究开始工作树干净。该 SHA 是研究快照，未来执行必须重新取 live main。

本轮之前的同次只读产品库快照：schema v18；Registry 179；Raw/Canonical 各 267；Evidence 421；web_runs 442；关系断言 293，均 UNREVIEWED；FK violations 0。Raw 来源 public_http 218、web_atom 30、Douyin 13、X 6；scope VERIFIED 264、UNASSIGNED 3；发布时间已知 57、未知 210；质量 ok 51、missing 209、error 7。**这是资产和缺口快照，不是覆盖率或产品闭环证明。** 本研究未启动新采集、未读取凭据、未写产品数据库。

已有资产继续用：v18 实体关系、原始数据/Evidence/Canonical 链、Public HTTP/Atom/Sitemap、已有社媒适配器、Shared Timeline、Importer、Flutter、报告/评估/学习。DuckDB 1.5.5 已用于现有 Overture Places 本地 Parquet 适配；MarkItDown 0.1.8 已有本地 HTML/PPTX 有界导入。两者不重复立项。

截至当前证据，R01 已接受，R02 只有有界范围通过；R03–R15 未形成完整累计出口，R09–R11 没有当前完整出口证据。Global Commercial/Brand Coverage 未通过，广州太古汇深度 PARTIAL；FULL_UNIVERSE_READY、RELEASED、OPERATING、COMMERCIAL_READY 仍为 NO。旧百分比不继承。

### 防遗漏的输入与路线

- [《能力.docx》34 节完整采用表](CAPABILITY-ADOPTION-20260928.md)及其逐段原文保留；旧状态按当前源码重核。
- [《补充需求.docx》23 项映射](../09_Research-Hub/engineering研究/补充需求-20260928/feature-inventory.md)及 1,193 段原文保留。
- [当前 Source Owner Index](../../00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md)负责源码/Owner/15 轮导航。
- [Content & Creation 学习来源契约](../../00-GOVERNANCE/LUMENIS-CONTENT-CREATION-LEARNING-SOURCE-CONTRACT-V1-20260911.md)继续保留叙事、白描、情绪体验、视觉母题、分镜、活动和评价。
- 每次执行用现有 `locate_capability_context.py --capability <family> --query <term>` 读取该能力的规则、源码、测试与研究；本材料通过现有资料库索引可发现。不另造检索系统。
- 本文覆盖能力家族与执行链，不声称逐一验收全部源码函数。任何细项进入 Batch 时，仍要核对上述原文节号、现有 taskbook 和匹配 Screen Contract。

## 3. 全产品能力与升级矩阵

以下编号是本研究的行标识，便于回查，**不是新模块或新 Round**。技术依据见第 7 节；业务依据见第 8 节。

| 行 | 能力 / 用户真正要完成的工作 | 拟升级或复用方向 | 现有 Owner / Round | 可验收的真实结果 |
|---|---|---|---|---|
| U01 | GLOBAL、国家/市场、主体与品牌选择 | 中国经营市场优先；总部/发源地/法人/经营/营销/场所分开；同一 Canonical ID 可关联多市场 | Registry、Shared DB、Global Context；R03/04/09 | Global→新加对象→Focus→Clear；既有数据保留、无错主体 |
| U02 | 多平台采集与原生字段 | 逐平台恢复已有适配器；公共/登录/不可得字段分别实测；保留原始字段和历史观察 | SYSTEM Collector；R06 | 社媒正文/作者/互动等真实值进入双域，含缺失原因及原始依据 |
| U03 | 来源、正文与质量 | 官方/媒体来源用于身份与事实；社媒用于传播/消费者表达；正文解析对照现有实现，小范围评测 Trafilatura | Collector、Evidence、Canonical；R03/06 | 导航页不冒充文章；发布时间不借采集时间；错误与缺失分开 |
| U04 | 自动维护与恢复 | 复用 APScheduler/queue；按 freshness 只处理到期项；幂等、退避、断点、重启恢复 | SYSTEM Runtime/Scheduler；R05/06 | 不依赖 Codex 的真实定时周期、失败及恢复记录 |
| U05 | 场内经营关系 | 商业主体→项目/场所→门店/业态→品牌/活动；租户关系具有来源和有效期 | CTH + Registry/Relations；R03/09/10 | 广州太古汇内 Nike 门店事件不污染 Nike 全国营销范围 |
| U06 | 监测、事件、日历、趋势 | 跨源事件去重但保留来源；区分发生/发布/采集时间；显示基线与可比性 | CTH monitoring/event callers；R10 | 运营人员能定位变化、证据、时间及受影响经营环节 |
| U07 | 消费反馈与风险处置 | 问题聚类、主题/对象/位置归属、严重性与可信度分开；回应候选和执行记录 | CTH case/risk/decision；R10/11 | 一条真实问题→Case→选择→Action→Outcome→复盘 |
| U08 | 商业活动与运营计划 | 资源/档期/场内品牌/预算输入→可执行计划；不可得客流/销售保持未知 | CTH + Shared Creation/Reporting；R11 | 可发给运营团队的计划，含责任、依赖、资源及衡量方法 |
| U09 | 品牌组合、市场与消费者研究 | 品牌/集团/子品牌/法人分开；需求、使用情境、品类、价格/渠道由证据支持 | BMP brand/market；R12 | Nike/Le Labo 及非参考品牌的市场判断与机会 Brief |
| U10 | 竞品与创意/广告研究 | 品类、市场、受众、期间对齐；广告创意与真实投放/转化分开；非公开数据不猜 | BMP + ad_intelligence；R12 | 可复核竞品比较、传播差异及行动建议 |
| U11 | KOL/KOC/KOS/UGC 与合作 | 适配性、历史内容、受众证据、合作历史、成本来源、执行/反馈分开 | BMP creator/KOS callers；R12/13 | Creator shortlist→合作 Brief→内容/反馈；不以粉丝量代替效果 |
| U12 | Campaign、传播与评估 | 目标→内容/渠道/排期→执行记录→结果；输出/受众反应/业务结果分层 | BMP campaign/propagation/evaluation；R13 | 可用活动方案及复盘；真实结果与计划假设明确区分 |
| U13 | 通用原创、提案与比稿 | 已验来源→策略选择→原创概念→多方案→文案/视觉/分镜→交付；保留改稿与反馈 | Shared Content + pitch/campaign callers；R07/13/14 | 公司/个人可用于客户审阅的方案包，含预算假设、排期、风险和可编辑源件 |
| U14 | 视频创作 | 现有 Timeline+FFmpeg/ffprobe；OTIO 交换、字幕、音轨/叠层；专业编辑基础复用 | Shared Content/Artifact；R07/13/14 | 手工空时间线或受审 EDL→真实预览→成片→重开→评价 |
| U15 | 播客创作 | 独立音频工作流；转写/说话人/段落/剪辑/混音/响度/章节；复用音频组件 | podcast + Shared Content/Artifact；R13/14 | 原创访谈/故事节目及母带、发布候选、show notes、衍生内容 |
| U16 | 研究资料库与 Evidence 查验 | 文档/表格/网页/媒体导入；来源定位、引文、别名与版本；检索结果保留范围 | Importer、Research、Evidence；R04/07/14 | 问题→证据片段→判断→引用/返回原文；未知问题诚实无答案 |
| U17 | 报告、导出、复用 | 报告是证据快照，指标有口径和时间；正式输出与可编辑版本一致 | Shared Reporting/Artifact；R11/13/14 | Word/PDF/表格或已有支持格式可打开，图表/中文/页码/引用正确 |
| U18 | AI 对话、模型路由与决策增强 | 现有 Gateway；确定性计算先行，生成/分类分路，结构化校验、弃答、fallback | SYSTEM AI Gateway；R07/14 | 真实任务有结果/明确失败；Jev/本地候选同题评测后择优 |
| U19 | Agent 协作与 Skill Store | 有界任务、输入输出约束、可暂停恢复、检查点；技能信任/许可/升级/卸载可追溯 | Shared Agent Skills + existing runtime；R07/14 | 发现→启用→真实运行→历史→升级回退→停用/卸载 |
| U20 | 评估与受控学习 | 来源质量、业务正确性、成品质量、时间/成本、用户反馈分别评价；版本化 shadow→promotion | Shared Evaluation/Learning；R07/13/15 | 新版本在保留集与真实任务改善，能回退，不改写源事实 |
| U21 | 内置 AI 浏览器 | 复用默认支持引擎及批准独立 Profile；真实网页 viewport、导航/任务返回、会话恢复 | SYSTEM Browser + SYS-06；R06/14 | 页面/目标/版本一致；用户登录后复用；撤销/过期可恢复 |
| U22 | 开放产品入口与服务端边界 | 产品账号/密码继续后置；当前受信本地使用模式、资源范围和外部效果仍可验证 | existing Permission/effects；R04/14 | 产品不被账号墙阻挡；越界读写和未授权发布仍被拒绝 |
| U23 | 四端、三语言与可操作体验 | 按工作重组信息，不固定复制 44 页；PC制作、Web工作、Mobile审阅各司其职 | Flutter/Website、Experience；R08/09/14 | 同一上下文/任务/结果连续；中英韩、键盘/触摸/缩放/错误恢复 |
| U24 | 任务通知、设置与诊断 | 进度来自任务状态；通知直达结果；深层日志按需呈现；偏好独立于业务事实 | Shared Notification + SYSTEM；R05/14 | 离开→收到完成/失败信息→回到原任务，不丢草稿/结果 |
| U25 | 运行、安全与发布 | 当前 launcher/recovery，追踪链、依赖锁定/许可、备份恢复、分平台打包与同 SHA 验证 | SYSTEM + Release；R05/15 | 重启/离线/源失效/导出失败可恢复；候选包离开研发工具独立完成任务 |

### 34 节与已有界面能力的保留映射

能力原文节号→研究行：1–2→U01/U25；3→U01/U22/U23；4→U05–U08；5→U09–U12/U15；6–8→U18/U19；9→U13–U17/U20/U24；10–12→U01/U03/U05/U16；13–14→U02–U04；15–17→U13/U14；18–19→U10–U12；20→U15；21→U06/U07；22→U17；23→U06/U07/U10；24–25→U20；26→U22/U25；27→U21；28–29→U04/U24/U25；30→U23；31–34→全部链条。

| 既有 Screen 能力索引（不是强制页面数量） | 对应研究行 |
|---|---|
| ACC-01、ACC-02、ACC-03、ACC-04 | U22、U01、U23、U25 |
| CTH-01、CTH-02 | U01、U05、U08 |
| CTH-03、CTH-04、CTH-05、CTH-06、CTH-07 | U02、U06、U07 |
| CTH-08、CTH-09、CTH-10 | U07、U08、U17、U20 |
| BMP-01、BMP-02、BMP-03、BMP-04、BMP-05 | U09、U10、U11、U12 |
| BMP-06、BMP-07、BMP-08、BMP-09、BMP-10、BMP-11 | U12、U13、U14、U15、U20、U07/U10 |
| AI-01、AI-02、AI-03、AI-04、AI-05 | U18、U19、U16、U25 |
| SH-01、SH-02、SH-03、SH-04、SH-05、SH-06 | U13–U17、U01/U03、U20、U24 |
| SYS-01、SYS-02、SYS-03、SYS-04、SYS-05、SYS-06、SYS-07、SYS-08 | U25、U02/U04、U01/U03、U22、U23、U21、U20、U24 |

## 4. 数据策略调整：中国工作价值优先，全球视野保留

### 4.1 新旧要求如何适配

本次用户已纠正按国家平均扩量的方向：已形成的国家候选和来源全部保留，完成去重、归属与状态整理；不继续为了每国 50+50 的配额无差别扩大名单。原数量目标不再作为本次继续扩量的驱动。**数据真实性、跨地区验证、双域分离、可新增主体、维护与业务消费的验收不降低。**

建议下一版 baseline 明确两个集合：

- **中国优先工作集**：中国经营的国内及国际品牌；全国/区域/品类代表、精品小众与新兴品牌；购物中心、街区、百货、文旅/酒店等已批准商业类型及经营组织。按城市/区域、品类、价格/定位、经营方式、成熟度、可获得证据分层。
- **全球参照集**：保留已研究的国家候选，用于跨市场背景、竞品和行业对照；有业务问题时增量扩展。并非所有优秀全球品牌/商业主体都在中国，不能因此删除海外参照。

中国、韩国、日本、英国、法国、美国、加拿大、澳大利亚、马来西亚、新加坡、泰国、巴西、挪威、其他国家继续作为用户入口；“其他”背后仍存实际国家代码，不是一个虚构国家。台湾/香港等地域标识按既有产品地理口径及合适标准映射，不能随研究私自改变政治/地区分类。

分母以规则版本及接受的 inventory 为准；应报告候选/已核身份/可采来源/真实观察/可用业务维度/已审关系/近期成功/业务消费各层数量。改变名单不能把过去未完成证据自动变成 PASS。

### 4.2 “优秀”和“小众”怎样选

不以粉丝量、榜单排名、官网能打开或模型推荐作唯一依据。逐条保留：实体类型与身份、确实经营证据、为什么符合用户工作、地区/品类代表性、可持续观察来源、独立佐证、纳入理由、规则版本。小众保留专门候选层，不要求大流量；来源不足先 PENDING_REVIEW，不强填。

行业榜单可发现候选，官网/运营方目录证明一方主张，监管/法人登记辅助核身份，独立行业媒体作交叉验证。GLEIF/WIPO 只覆盖其实际覆盖对象；不能要求每家小店有 LEI 或把商标搜索结果自动当品牌权属结论。[D1–D5]

### 4.3 身份关系和最简单的用户选择

品牌、法律实体、经营组织、项目/商业体、具体门店是不同对象。Nike 全球品牌、Nike 在中国的经营主体、某商场内 Nike 门店可以关联，不能合并成一个“美国主体”。字节等经营组织可以进入已批准 CTH Subject 类型；只有法人身份不能据此虚构场所、门店或商业运营指标。

复用现有 relations，按事实分别表达 HQ、ORIGIN、LEGAL_JURISDICTION、OPERATES_IN、MARKET_ACTIVITY、VENUE_LOCATION、TENANT_OF 及已有的所有/运营关系。现有 schema 尚未支持的关系类型通过原 DB owner 扩展，不额外建图数据库。每条记录须有 Evidence、有效时间、观察时间、审核状态；重复/冲突保留裁决历史。

选择交互建议：业务领域→市场（默认中国，可全球）→行业/类型→搜索/列表；默认按“经营市场”观察，可以切换“总部/发源地”。条目直接显示对象类型与所在地/经营范围；选定后按需打开关系脉络，避免一开屏就是大图。CTH 的“场内”关系查询与 BMP 的品牌市场观察始终分开；新增主体在同一 Registry 完成，不做固定白名单。

### 4.4 官网与社媒各自承担什么

| 数据面 | 来源职责 | 必须保留 | 不能声称 |
|---|---|---|---|
| 身份/地点/租户 | 官网、运营方目录、法人/地址/授权开放数据 | 来源版本、对象类型、地点、关系依据 | 官网记录=消费者口碑/营销效果 |
| 新闻/事件 | 官方发布、出版者媒体、RSS/Atom | 正文、作者、原始发布时间/未知、事件时间 | 抓取日期=新闻发布时间 |
| 社媒内容/传播 | 当前平台目录中的小红书/RedNote、抖音、微博、B站、知乎、X、Instagram 等已规划来源 | 平台 ID、作者、内容、原生互动、观察时刻、评论/回复与媒体等可见字段 | 把网页数代替社媒维度；未登录一定拿到登录所有字段 |
| 消费者表达 | 可获得的评论/反馈/UGC及用户提供研究 | 场景、对象、样本范围、偏差/缺失 | 平台发言人代表全体消费者 |
| 经营/投放结果 | 用户授权的实际经营、活动、成本、投放材料或合法可得来源 | 口径、周期、单位、来源 | 点赞=销售；可见广告=完整花费/ROI |

逐个平台出同一张字段验收表：计划字段、公开可得、授权登录可得、此次真实获取、丢失原因、刷新时间、Canonical 消费位置。不会因无 Cookie 就偷偷缩字段合同；同时不承诺平台不开放的数据能凭开源工具取得。需要登录时使用获准身份的正常登录/恢复；XHS 仅 HK/international allowlist，CN 个人账号禁止访问。

### 4.5 数据出口

先处理现有 3 条未分配 scope、7 条 error 的具体原因和 293 条关系的审核，不把 UNREVIEWED 批量改为已审。210 条未知发布时间保持未知，补源能证实才补。采集成功只证明该来源读取，仍需归属、质量与业务消费。

技术验收：Run1→Source/Raw/Evidence/Canonical→双域结果；立即 Run2→身份和关系不重复、未变化不生成假新内容、观察值按时间留存；重启重开一致。真实后续 scheduled cycle 才证明自运行。用户采集 MANUAL 默认，AUTO 显式 opt-in；已批准 prelaunch 公共基线单独受既有维护策略控制。调度每天评估到期项，不每天全库清洗重抓。官方身份/目录与高频内容使用不同 freshness 策略。

## 5. 三种制作能力：基础复用，成果与体验分别验收

### 5.1 通用创作与专业方案

入口可以是完整客户 Brief，也可以是空白创作。已有素材/历史案例先研究方法并保留来源；创意、文案、方案结构和执行构想围绕当前客户重新形成。最终交付必须区分事实、洞察、假设、预算估算与建议。

一个可给客户看的方案包至少包含：问题与目标、研究依据、受众和场景、策略取舍、原创主张与创意方向、渠道/内容/活动展开、资源与制作清单、可解释的预算假设、排期/责任、衡量方法、风险和备选；附可编辑文件、预览件、引用及变更记录。具体项按客户任务裁剪，不输出每次一样的空模板。

现有 Narrative/Copy/Visual/Motion/Campaign/Evaluation Pattern 作为方法资产；AI 不能把他人作品换标题作为原创，不能虚构客户经历、预算报价、消费者访谈和投放效果。提案完成标准是用户能修改、讲解和交给真实客户评审；不保证中标或商业回报。

### 5.2 视频

现有 Timeline 保留唯一编辑语义；FFmpeg/ffprobe 负责成熟媒体处理，OTIO 用于交换与适配，libass 负责需要的字幕渲染。OTIO 不是播放器、渲染器或媒体资产库。[V1–V3]

第一段产品收口覆盖真实多素材导入、媒体指纹/元数据、trim/split/reorder、多个必要音视频轨、基础转场/叠层、音量/淡入淡出、CJK 字幕、预览、可取消导出和重开。若现有 FFmpeg 路径无法在合理复杂度下承载多轨，再评测 MLT 作为可替換 renderer；不同时把 FFmpeg/MLT/GStreamer 全部塞入产品。[V4]

AI 可按 Brief 建议分镜和 EDL；手工空时间线、修改、撤销/恢复、版本差异和审阅均须可用。12 个用户素材的历史指纹证明只代表素材核对；必须经产品入口实际编辑并输出新成片，不能以终端直接调用 ffmpeg 代替产品能力。

验收样片：至少两个视频片段+一个音频素材，含切割重排、转场、中文字幕/品牌元素、混音与真实导出。检查时长、PTS/A-V 同步、帧率、画幅、音频峰值、文字缺字、首尾黑帧和容器兼容；预览与成片一致；中断重试不污染已接受 Artifact。所有约束按实际素材与交付规格制定，不编造通用“专业分数”。

### 5.3 播客

播客保留音频优先的研究→访谈/故事→脚本→录制/导入→转写校对→段落编辑→混音→节目成品→章节/show notes→衍生传播→反馈路径。

基础首选为 whisper.cpp 本地转写、现有 Shared owner 后的 FFmpeg 音频处理与 loudnorm。ffmpeg-normalize 与 librosa 暂不增加，原生处理不足时再评测。自动转写是派生草稿，人物/专名/时间戳必须可校正；自动识别说话人不能当法定身份识别。模型权重、代码、音色和素材授权分别核对，不因代码 MIT 就默认任何声音都可商用。

本轮子研究定位到具体集成断点：BMP-08 已有脚本/资料/音频/权利的独立工作台，但当前明确没有可播放音频与真实波形；Flutter snapshot 所需的 scope/Evidence/audio 字段与 `experience_screens.py` builder 的统计/表格输出形状有差异，需要先由现有 ViewModel owner 核实并对齐。Shared Timeline 有音轨/混音参数，当前受限 renderer 尚不能交付音频导出。先修这条制作/契约链，不再追加一套选题研究 API。这是源码结论，未在本轮执行真实 API 或音频 E2E。

音频任务验收：两位说话人的获准素材→保留原音→可编辑转写→删除一段/重排一段→去噪或音量处理的 A/B 试听→配乐/旁白平衡→目标渠道指定的响度/true peak/编码→完整音频和章节→重开修改。降噪不能损伤人声才算改善；不要把某个 LUFS 目标当全部播客的统一规则。发布前仍走既有 Effect Fence；本轮可交付离线成品和发布候选。

发布候选按 [Apple Podcast 要求](https://podcasters.apple.com/support/823-podcast-requirements)核对 GUID、enclosure URL/长度/MIME、HEAD/byte-range 等；按 [章节支持](https://podcasters.apple.com/support/5482-using-chapters-on-apple-podcasts)与 [Podcast Namespace](https://github.com/Podcastindex-org/podcast-namespace)适配已有章节元数据。未部署托管就标托管待验，不能把本地 RSS 文件称为已上线节目。

## 6. AI、Agent、资料库和学习的实用升级

研究/问答先检索同一 Evidence/Canonical/资料库授权范围；每条事实引用定位到原文片段或媒体时间段。既有检索先评测召回、引用准确、跨实体污染与拒答，再决定是否增加混合检索或 reranker。向量库/知识图谱不默认新增。

Agent 采用明确输入、工具允许列表、结构化输出校验、检查点、可中断恢复、最终结果验证。可学习 LangGraph 等项目的持久化和人审设计，但不引入第二套 Agent Runtime。Skill Store 的 discovery、信任/许可、启用、参数、结果、运行历史、更新、回退、禁用/卸载全部保留。

Jev 继续是 typed decision 的待验证候选；不能称其开源免费，也不能替代 LUMENIS Gateway。自研先指在现有 owner 内构建任务数据、特征/规则、分类/排序/校准与评估闭环，不以从零训练通用大模型作当前上线前置。开源模型按任务、硬件、许可证、延迟与准确性比较；未知结果能弃答，规则/较小本地模型可先处理明确任务。

AI 验收使用盲测保留集+真实任务：事实依据、完整性、对象归属、重复执行一致性、工具结果验证、中文/英文/韩文质量、失败恢复、成本/延迟。LLM judge 只作一类信号，不能自评分即通过。Learned Pattern/提示词/模型/规则变更有版本、来源、适用范围、负例、shadow 结果与回滚；原始 Evidence 不被学习回写。

既有封面、视觉母题和图文任务也保留生成/编辑能力需求。对开源图像模型，官方 [Qwen-Image 模型卡](https://huggingface.co/Qwen/Qwen-Image)与 [FLUX.1-schnell 模型卡](https://huggingface.co/black-forest-labs/FLUX.1-schnell)列 Apache-2.0，可作为现有 Gateway 的有界评测候选；不能将同系列新版本或 dev 模型自动沿用该许可。对比中文文字、指定品牌素材保持、局部编辑一致性、可修改版式、推理资源和成品可用率后择一。当前不下载权重、不增加付费依赖，也不以新模型名字证明质量领先。最终必须有实际可用图片；若模型不能稳定排对文字，使用现有排版/导出能力保留可编辑文字层，不将错误字烘焙到成品里。

### 当前必须衔接的三个具体断点

1. `agent_runtime/durable_adapter.py` 当前能记步骤，但 DB 写入/权限受阻时退回内存，进程重启后的 `recover()` 主要返回步骤历史；这不等于恢复工作上下文并安全续跑。沿既有 TaskEngine 补完整检查点/持久状态和幂等续跑，拒绝或存储不可用要显示真实状态，不能靠接 LangGraph 另建运行时解决。
2. `lumenis/shared/learning/content_assets.py` 的 `promote_pattern()` 仍明确抛出 `CANONICAL_PROMOTION_GATE_NOT_CONNECTED`，候选停在 EXPERIMENT。接上已有 Evaluation、Permission、review/retire 后才允许晋升；撤回版本必须退出检索，同时保留历史成品引用。
3. `content_generation.py` 中有研究 query/context length/has research 等元信息，不足以证明每条事实有引用。补齐的是事实主张到原文/Evidence/时间的链路，以及审阅改稿的可编辑结果，不能只增加 research 字符数。

这三个发现是当前源码断点，研究中未执行相应 runtime。其验收分别是跨进程续跑且无重复效果、晋升/撤回实际生效、客户方案逐项查证并修订导出。

### 前沿方法的采用与保留

- [LlamaIndex CitationQueryEngine](https://developers.llamaindex.ai/python/examples/query_engine/citation_query_engine/)：子研究核得 v0.14.25、MIT。ADAPT 编号引用/source nodes 检查方式；不替换既有索引/资料库/证据所有者。
- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)：子研究核得 1.2.12、MIT。ADAPT stable task/thread id、checkpoint、resume 和重跑节点需幂等的原则；REJECT 引入第二 Agent Runtime。
- [Inspect AI](https://inspect.aisi.org.uk/)：子研究核得 0.3.272、MIT、Beta。ADAPT 为隔离的成果评估工具候选；任务/模型代码按不可信代码隔离执行，不放入产品运行时。
- [Ragas metrics](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/)：子研究核得 v0.4.3、Apache-2.0。ADAPT 证据支撑/检索 precision/recall 的维度；DEFER 依赖，指标用人工标注保留集校验，不让 judge 自证正确。
- [Pydantic AI deferred tools](https://ai.pydantic.dev/deferred-tools/)：子研究核得 v2.51.0、MIT。ADAPT 结构化结果与等待输入原则；人工同意和服务端授权独立；REJECT 第二 Agent Runtime。
- [DeskCraft，2026-06 论文](https://arxiv.org/abs/2606.03103) / [代码](https://github.com/mrwwk/DeskCraft)：ADAPT 长任务中途修订、分层评价思路；论文/演示不是序境性能证明，未核许可的媒体样本不用于训练或商业成品。

这些前沿成果共同支持的方向是：可观察的过程、可修订的成果、可恢复的状态和可查证的事实。当前不把六套框架都接入；它们只进入既有 Owner 的具体断点修复和对照评测。

## 7. 开源与技术选择：最小接入清单

访问日期均为 2026-09-29；“仍维护”只依据当日官方仓库活动，不等于安全审计通过。下列许可说明是接入工程约束；实际交付需核定版本、传递依赖、二进制选项、模型权重和素材权利。

| 来源 | 当期观察 / 许可 | 决策与适配边界 |
|---|---|---|
| [V1 FFmpeg](https://ffmpeg.org/legal.html) / [源码](https://github.com/FFmpeg/FFmpeg) | LGPL 2.1+ 为主要基础，GPL/nonfree 配置及依赖改变分发条件；当日 upstream `d85cdd25970e5101fa5848a4c0972af4b966e90e` | ADAPT 现有渲染；锁定合适稳定构建及 build flags/notice/source obligations；不能以“命令行独立进程”宣称免除许可证义务 |
| [V2 OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO) | Apache-2.0；当日 `dc8366533acd6730228a9802b7cc7a8b6439d2ef`，近期维护 | ADAPT 时间线互换/导入导出，保留 LUMENIS 资产/编辑/Evidence ID；不替代 Timeline owner |
| [V3 libass](https://github.com/libass/libass) | ISC；`f61db567e6593df3470e91594bcd4ad2d0473aff` | ADAPT 必要字幕；字体许可/缺字与资源路径限制另验 |
| [V4 MLT](https://www.mltframework.org/docs/copyrightpolicy/) / [源码](https://github.com/mltframework/mlt) | framework LGPL 2.1，应用及模块需分别核对；`0926a754fcb85b0a1a61a89c56e2a03ff3ea8270` | 条件 ADAPT：多轨/转场确有缺口时比较；melt/GPL 与插件不能混称宽松可闭源 |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | MIT 代码；子研究核得 v1.9.4 / `927cfce`，2026-09-11；权重单独核验 | ADAPT 现有 AI Gateway 后的本地转写；真实中文/中英混合专名及设备性能实测 |
| [ffmpeg-normalize](https://github.com/slhck/ffmpeg-normalize) | MIT；子研究核得 v1.41.1 / `8979aee`；依赖实际 FFmpeg 构建 | DEFER 新依赖，优先复用 FFmpeg 原生 loudnorm，避免双实现 |
| [librosa](https://github.com/librosa/librosa) | ISC | DEFER 非必要特征分析依赖；不把音乐分析直接当语音质量结论 |
| [audio_waveforms](https://pub.dev/packages/audio_waveforms) | MIT；v2.0.2 主要目标 Android/iOS/macOS，未证明 Windows/Web | DEFER 直接引入；不能拿移动控件代表四表面支持 |
| [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet)、[pyannote.audio](https://github.com/pyannote/pyannote-audio) | 前者代码 MIT/Apache-2.0、权重另核；后者代码 MIT，[community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) CC-BY-4.0 且获取需接受条件 | DEFER 默认依赖；只有实际降噪/说话人分段缺口才试验，保留原音/人工纠正，不自动获取或分享用户联系信息 |
| [Audacity](https://github.com/audacity/audacity)、[Shotcut](https://github.com/mltframework/shotcut) | GPL 系列，分别以实际版本 COPYING 为准 | 研究编辑工作流和质量样例；不整体嵌入/换皮，不以 GPL=禁止商业使用解释 |
| [GStreamer](https://gstreamer.freedesktop.org/documentation/application-development/appendix/licensing.html)、[PyAV](https://github.com/PyAV-Org/PyAV) | GStreamer 核心 LGPL、各插件另核；PyAV BSD，绑定 FFmpeg 义务仍在 | DEFER 默认引入；只有实时预览/特定解码缺口才限定评测 |
| [Trafilatura](https://github.com/adbar/trafilatura) | 当前 Apache-2.0；1.8.0 之前 GPLv3+ | ADAPT 候选：只解析已由安全 fetcher 获得的 bytes；比较正文/元数据效果，不让其另开网络路径 |
| [Browser Use](https://github.com/browser-use/browser-use) | MIT；`4cbe921673b48a488f5415d9159249afd12a625b`；云服务/模型可另收费 | 先 ADAPT 状态观察与操作验证原则；完整 Agent 包 DEFER，不替换 Browser/Collector |
| [Crawl4AI](https://github.com/unclecode/crawl4ai/blob/main/LICENSE) | Apache-2.0 文本并附醒目 attribution 要求；`e5d2e786d1a101225f3f6a3e6fd344d76eeb13af` | DEFER 大包接入；只有动态正文对照明显改善才做 adapter，不把网页 Markdown当 Canonical |
| [APScheduler 3.x](https://apscheduler.readthedocs.io/en/3.x/userguide.html) | 现有依赖 `>=3.10.0`；当前文档支持持久任务、misfire/coalescing；项目 MIT | ADAPT 当前 owner 的幂等注册、到期调度、失约恢复；先核运行版本，不套用 master/4.x API，不另建 scheduler |
| [OpenTelemetry Python](https://github.com/open-telemetry/opentelemetry-python) | Apache-2.0；`a514e9e9e5bd631379ada452ae068773e7f52b81` | 条件 ADAPT 现有 task/run/result trace 缺口；遥测先本地脱敏，不新增外部 SaaS 或发送 Cookie |
| [OpenLineage](https://github.com/OpenLineage/OpenLineage) | Apache-2.0；`7a84fd4d48aeed4d0e6f391e2b7fbc11c0ff4fd9` | ADAPT lineage 事件表达原则；不新建 Evidence store/服务器，现有 refs 足够则不装 |
| [DuckDB](https://github.com/duckdb/duckdb)、[MarkItDown](https://github.com/microsoft/markitdown) | MIT；本仓已有 1.5.5、0.1.8 的有界适配 | REUSE；前者只做已有本地 Parquet 读取，后者沿 Importer；不重复宣布新增 |
| [LangGraph](https://github.com/langchain-ai/langgraph) | MIT；研究版本 1.2.12，采用前仍需锁定 | ADAPT 检查点/恢复思想，REJECT 第二编排框架；不迁移现有 Agent Runtime |
| [Playwright trace](https://playwright.dev/docs/trace-viewer)、[WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Playwright 已有；WCAG 是标准不是 UI 模板 | ADOPT 可操作性/焦点/拖动替代/点击目标验收；trace 必须去凭据再留证 |

Firecrawl、Crawlee、Scrapy、Scrapling、AutoScraper、curl-impersonate、scrcpy 等前一轮比较结论继续保留在既有 [OSS 采集采用记录](../../00-GOVERNANCE/evidence/round-06/ROUND-06-OSS-COLLECTOR-ADOPTION-2026-09-29.md)。不因本轮扩大研究范围而全量安装。现代库的版本更新不是序境必须升级依赖的充分理由。

### 浏览器与采集安全的具体适配

[Chrome 官方说明](https://developer.chrome.com/blog/remote-debugging-port)限制默认用户资料目录的调试；使用默认浏览器引擎与接管日常个人 Profile 是两件事。序境显示自己的界面及真实来源 viewport，复用获准独立 Profile，提供正常登录/过期恢复；不能许诺永久保活。

[OWASP SSRF 指南](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)支持将 URL/解析地址/网络出口校验放在 fetch 边界。本次适配是正常 DNS 变化可复核更新、重定向逐跳检查、记录来源与失败；不能因安全 pin 过时永久采不了，也不能删除校验来扩大采集。

## 8. 数据与业务研究来源

所有外部数据都需按实际来源许可和可见范围使用；开源工具许可证不授予社媒数据商业使用权。开发环境可以执行用户已批准的公共/获准账户采集；未取得的商业授权继续如实记录在商业发布条件中，不伪装已授权。

| 来源 | 采用范围 / 不采用的推断 |
|---|---|
| [D1 ISO 3166](https://www.iso.org/iso-3166-country-codes.html)、[UN M49](https://unstats.un.org/unsd/methodology/m49/) | 地理编码/区域映射参考；不将总部国家当唯一市场归属 |
| [D2 GLEIF](https://www.gleif.org/en/organizational-identity/lei-vlei/the-legal-entity-identifier-lei) | 法律实体身份及可得关系佐证；不替代品牌/店铺 ID，也不宣称覆盖全部中国主体 |
| [D3 WIPO Brand Database](https://www.wipo.int/en/web/global-brand-database/faqs_branddb) | 商标/品牌身份线索；权属需核原登记和范围，不是品牌商业优劣评分 |
| [D4 Kantar BrandZ 方法](https://www.kantar.com/Campaigns/BrandZ/Methodology) | 消费者感知、品牌和财务证据分开评价的思路；不复制付费数据/专有分数 |
| [D5 OpenCorporates coverage/freshness](https://blog.opencorporates.com/2025/03/05/how-to-check-data-coverage-and-freshness-in-opencorporates/) | 把覆盖与新鲜度分开呈现；API/数据许可另核，不默认免费接入 |
| [D6 Overture Places](https://docs.overturemaps.org/guides/places/) / [schema](https://docs.overturemaps.org/schema/reference/places/place/) | 当前既有适配继续保留 GERS/来源/版本/类型；存在性 confidence 不等于当前经营/品质/覆盖，按实际版本逐源核许可 |

### CTH/BMP：业务研究如何变成执行能力

| 业务来源与时间 | 研究判断 | 落实到序境 |
|---|---|---|
| [IAB Creator Measurement Landscape，2026-01-29](https://www.iab.com/guidelines/creator-economy-as-is-measurement-landscape/) | 创作者测量存在碎片化指标和 proxy ROI 问题；不能靠一个综合分证明适配和回报 | U11/U12：Creator 候选按内容/受众/场景/历史合作/成本依据逐项比较，未知可见；至少比较两名真实创作者并交合作 Brief |
| [Google Conversion Lift 方法](https://support.google.com/google-ads/answer/14102450?hl=en-GB) | 实验/对照的增量与普通归因不同；平台方法不是通用免费数据源 | U12/U20：传播互动、意见、到访、交易、归因、因果增量分层；没有合格实验只报观察结果 |
| [ICSC tenant mix 研究练习，2024](https://www.icsc.com/news-and-views/icsc-exchange/we-asked-people-to-choose-the-tenant-mix-for-a-marketplace-heres-what-we-learned) | 业态/位置/客群共同影响运营选择；这是方法参考，不是最新中国经营基准 | U05/U08：场内事实卡→活动/资源计划，未核库存/独家性/营业状态不能生成确定承诺 |
| [ISO 31000:2018](https://www.iso.org/standard/65694.html) | 成熟风险方法覆盖识别、分析、评价、处置和监控，不能缩成一个风险分 | U07：证据强度、严重性、责任人、期限、决策和结果分开；不宣称产品获得 ISO 认证 |
| [FTC Endorsement Guides FAQ](https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking) | 美国合作披露参考，不能替代中国/其他市场规则 | U11/U12：合作内容有赞助/权利/披露检查位置；规则随实际投放市场核验，不把粉丝自然内容和付费合作混计 |
| [PyMC-Marketing](https://github.com/pymc-labs/pymc-marketing) | 当日维护活跃，Apache-2.0；Python ≥3.12 / PyMC ≥6；可研究 MMM/CLV/实验校准，部分新方法仍 alpha | ADAPT 测量原则，DEFER 当前安装。只有足够的真实花费、业务结果、时间序列、对照设计后才试验；不拿 267 条来源内容推导营销 ROI |

业务子研究指出的当前接线重点：CTH-05/07 的时间窗和趋势分母、CTH-06 的意见/反馈/确认事件及逐项 lineage、CTH-08/09/10 的 Case/行动/报告绑定、BMP-05 的跨品牌 creator scope、BMP-07/09/11 的计划与真实 outcome 区分。以上来自当期源码/Screen Contract，不是本轮真实运行测试；执行时只修首个对应断点，不开展业务域整体重写。

前沿研究也包括“现在不应该上什么”：没有原始经营数据就上因果模型，只会把输入缺失藏进复杂模型。成熟方法是设计未来测量的依据，当前先交付有来源、可执行、可复盘的业务工作。

### 广告公司案例与资讯核实补充（2026-09-29 访问）

| 一手发布来源 | 吸收的方法 | 对 J2/J3/J4/J7 的落实与限制 |
|---|---|---|
| [IPA：KFC / BBH，2008](https://ipa.co.uk/knowledge/case-studies/kfc-finger-lickin-good-results) | 从流失顾客与业务问题选择传播任务，再说明创意为何回应该问题 | Brief 要有问题、目标受众、备选解释与创意理由；公开摘要的效果是奖项案例报告，未取得付费全文/原始数据，不写成独立复核的因果证据 |
| [IPA：Currys PC World / AMV BBDO，2016](https://ipa.co.uk/knowledge/case-studies/currys-pc-world-we-start-with-you) | 服务定位同时落实到传播与顾客体验 | CTH/BMP 方案必须写实际执行资源与体验动作，不能只给口号；页面披露的归因收益不等于序境验证过的经营事实 |
| [Google：KFC Australia / MediaCom，2022](https://business.google.com/aunz/think/search-and-video/kfc-advertising-strategy-boost-sales/) | 对类似门店做有/无搜索广告的四周比较，预先明确业务结果 | 评价区分互动、到访、销售和因果；该方法披露与成效为平台案例自报，缺原始数据/独立审计，不能直接推广成所有行业效果 |
| [IFCN 原则](https://ifcncodeofprinciples.poynter.org/the-commitments) | 重要主张可回查出处、一手来源优先、呈现反证、说明利益关系与更正 | 应用于资讯分析与 Fact Wall 的审核方法；不宣称序境是 IFCN 认证机构，也不把“官方”或模型置信度当判真结论 |

以上历史案例用于工作方法，不能代替最新市场资料或复用其受版权保护的创意成品。现有 SH-01 的 `BACKEND-GAP-046` / ViewModel 已规划 claim→Evidence/Brief/UNKNOWN，但截至本次源码核对仍缺逐条主张解析，不能声称 Fact Wall 已工作。实施复用现有 Content/Research/Evidence/Evaluation：读取 Brief 原文→提出可决策问题→引用和反证→洞察与适用条件→至少两个原创方向及选择理由→可编辑产物→真实反馈。持久化学习候选继续走现有 `content_assets.py`，不因案例或模型评分自动晋升。

## 9. 历史工作包与真实交付物（现映射 C1–C6）

以下是原轮次中的 Batch 依赖，不是增加轮次。已有通过的局部能力直接复用；每个 Batch 只解决一个可验收链段，禁止一次改多个 Owner 后才发现无法收口。

| 顺序 | 既有 Round | 工作与进入依赖 | 本次应交付的东西 / 退出条件 |
|---|---|---|---|
| A | R03/04/06 | 用现有 DB/关系/source；按本次中国优先调整名单版本与分母；修 scope/error/关系审核/逐平台链 | 已核工作集 + 字段覆盖表 + 真实 CTH/BMP 数据结果；未采/不可得明确 |
| B | R05/06 | 在已有计划和受信执行上下文中验证 due 刷新/幂等/恢复 | Run1/Run2/reopen 技术证据及真实未来周期；无 Codex 代跑 |
| C | R09/10/11 | 任务所需真实输入已够用即可并行，不等 A 的完整目录；C1 主体/场内关系，C2 事件反馈，C3 决策/运营方案与结果逐批 | 广州太古汇、深圳罗湖万象城和随机非参考主体各自真实工作；报告可重开；中断/失败/撤销及适用重启恢复同步验证 |
| D | R12/13 | 任务所需真实输入已够用即可并行，不等 A 的完整目录；D1 市场/竞品，D2 Creator/传播，D3 Campaign/评估逐批 | Nike/Le Labo 和非参考品牌的 Brief/合作方案/活动复盘；全域背景保留；恢复同步验证 |
| E | R07/13/14 | 先复用证据/Artifact/Provider；E1 原创提案，E2 视频 render adapter，E3 播客 audio adapter 独立执行 | 客户方案、真实新视频、真实新播客三个独立交付包；源件/预览/导出/重开/审阅 |
| F | R07/14 | 配合每条业务链补 AI 工具结果验证、资料库引文、Skill完整生命周期、评价学习 | 真实任务完成/失败可解释、恢复可复现；规则/模型升级可回滚 |
| G | R08/09/14 | 前端在依赖可用时并行绑定；每个任务设计先通过现有 DESIGN_READY | 四表面各有真实可操作路径；三语言与响应/无障碍；当前入口指向当前构建 |
| H | R15 | 原 R02–R14 依赖和真实 Job 均已验收；只汇总真实证据 | 同 SHA Gate/构建/重启恢复/回滚/独立运行验收包，提交用户审核后按发布授权行动 |

A–G 可在不冲突的 Owner/路径上交叉执行，验收依赖仍有顺序。完整中国/全球目录不是 CTH/BMP 代表任务的进入门槛；两种进度独立报告。每个模块开发时即验证局部恢复，H 只负责累计跨系统/跨端/发布级恢复，不是第一次故障检查。数据维护独立持续，不因做视频或前端停止；单来源暂时失效只阻塞相关字段/结果，不停止所有研发。账号密码重设计与订阅付费不在当前 Batch，不因此卡住本地产品使用。

### 首批具体 Task Cards

1. **数据可用性**：从现有平台 coverage 与 production rows 取一个明确 blocker；只修该 adapter/normalizer 或 scope owner；真实 Source→可见结果后再接下一个平台。官网身份记录不能代替社媒验收。
2. **CTH 与 BMP 消费**：对同一快照分别生成真实运营简报和品牌研究 Brief，复用现有 Report/Artifact；找出首个真实断点，定位 caller 后修，禁止新建报告系统。
3. **视频 renderer**：已有 Timeline 导出两段视频+一条音轨+字幕，使用固定 FFmpeg 构建；无 UI 时仅记 TESTED，不记用户完成。下一 Batch 再接现有 API/Artifact 和前端。
4. **播客成品**：现有 Podcast 数据/音频素材走转写校正→剪辑/响度→成品；同样先能力后 API/体验，每段有真实产物。
5. **前端绑定**：同一用户任务的入口、输入、进度、结果、来源、修改/返回、失败恢复一次闭合；不以新画面数量验收。

各卡的具体文件白名单在进入时从 locator/owner/callers 确定；不能在本研究里把未核验的历史文件当允许编辑清单。

## 10. 八个真实验收包

### 2026-09-30 视频工作台补充：成熟编辑基础与序境适配

Product Owner 补充纳入既有 J5 / Shared Content & Creation；不替代 J4 通用创作或 J6 播客，也不增加 Round。

- **素材浏览与剪辑分工**：研究 Final Cut Pro 的素材浏览器、快速掠览、范围选择与时间线工作区。播放头负责确定编辑/播放位置，掠览位置用于临时寻找素材；两者状态分别保存、可键盘操作，不能因鼠标浏览而改写剪辑位置。外部界面只提取操作原则，SH-01 的具体布局仍由当前 Screen/Experience authority 决定。
- **磁性与连接关系**：现有 `Timeline.trim/reorder/delete` 已对主视频序列重排；这不等于完整磁性时间线。当前音轨与字幕采用绝对时间，后续在同一 Timeline owner 补足连接对象、偏移、移动/删除/裁短策略和撤销/重开一致性；保留用户明确的独立定位选择，禁止静默移动或丢弃关联素材。
- **工程互通**：Premiere 原生项目是 `.prproj`，After Effects 是 `.aep`，Final Cut 的现代交换格式是 FCPXML。XML 不是统一无损格式；先验证已有 Timeline 的交换子集、分数帧率、音轨、字幕/转场损失和媒体重连。序境项目保留为可恢复原件，第三方工程另存并逐项说明不支持项，不能把 JSON 改扩展名当互通。
- **成熟基础复用**：优先评估现有 FFmpeg、OpenTimelineIO 及维护中的适配器；采用前锁定版本、许可证、通知/源码义务、传递依赖和可替换接口。公开 SDK、付费软件可研究交互和合法集成；付费可用不等于获得复制专有源码或插件的许可。不得为接入编辑器另建素材库、Artifact、Evidence 或渲染 owner。
- **性能按设备验证**：代理媒体/原片切换、缩略图与波形缓存、按需解码、后台预处理、取消与恢复属于预览能力的研究与适配范围；代理必须能追溯并重连原素材。Windows 与 Apple Silicon 分别记录素材编码、分辨率、帧率、时间线复杂度、预览掉帧/延迟和内存；未在 Mac 实测，不声称达到 M 芯片 4K 流畅度。
- **专业基础验收**：素材整理、精确裁切/分割/重排、多轨音频、转场、字幕、音画同步、撤销/版本、成片导出、工程重开/缺失素材恢复必须落到真实操作。插件/AE 互通按实际接口与授权分批验证，不承诺原生 Adobe 插件兼容。新能力不打断当前已运行的导入→编辑→导出→重开验收。

这些是新增验收要求和已核对的缺口，不是能力通过声明；后续按现有 owner 的小 Batch 实现，并在 J5 报告逐项交付。

对应的[官方文档及固定 GitHub 源码研究](VIDEO-WORKFLOW-INTERCHANGE-RESEARCH-20260930.md)已核出：现有 FCPX 社区适配器不能直接承诺转场、混音或分数帧率无损交换。保留互通要求，实施先解决当前字幕不能进入成片的实际断点；不能只不断增加预检而不交付制作结果。

| 包 | 用户路径 | 必需结果 |
|---|---|---|
| J1 数据与新对象 | GLOBAL→国家/市场→新增 Subject/BrandFocus→真实来源→Focus→Clear | 证据、字段/关系、缺失/新鲜度、增量刷新、不重复、同库重开 |
| J2 CTH | Global→商业体→场内对象/事件→Case→Decision→Action→Outcome | 运营计划/简报及真实状态变化；未知经营结果不伪造 |
| J3 BMP | Global→品牌→竞品/消费者/Creator→Brief/Campaign→复盘 | 可用品牌方案与依据；外部效果执行另授权 |
| J4 通用制作 | 新 Brief→研究→策略/原创方向→方案/素材→改稿→导出 | 可发客户的文件、可编辑原件、引用/假设、版本与反馈 |
| J5 视频 | 真实媒体→手工或审核 EDL→编辑预览→render→Artifact→导出/重开 | 新成片与项目源件；音画同步/字幕/失败恢复/来源权利 |
| J6 播客 | 真实音频/原创采访→转写校对→段落/音轨→混音→成品/章节→重开 | 实际可听节目、脚本/章节/描述、可编辑项目与试听评价 |
| J7 AI/Skills/学习 | 用户任务→受控 Skill→真实工具结果→引用/成品→反馈→shadow→回滚 | 不把空结果/模型文字当执行成功；版本提升有前后对照 |
| J8 独立运行/四端 | 当前启动入口→Web工作→Desktop能力→Mobile审阅→离线/重启恢复 | 同一任务/Context/Artifact连续；真实定时维护和恢复证据；无需 Codex代调用 |

上述每包均包括真实输入、入口、可见结果、Evidence、服务端边界、错误恢复与返回路径。样例是能力证明的一部分，不能代替冻结范围、全字段或全部平台验收。用户审阅/USER_VERIFIED 与工程 TESTED/运行 VERIFIED 分开记录。

### 八次交付报告与持续执行

J1–J8 保留为能力来源标签，映射 C1–C6，不另排八轮/八份报告。C 窗口报告包含任务、真实输入、产物、事实/推断/创意、精确 SHA、验证、E2E、恢复及缺口。同一证据复用到 J/R；未通过保持 PARTIAL/REWORK/BLOCKED。

当前执行状态只见 CURRENT：六轮方案已批准，产品窗口暂停，等 Product Owner 恢复指令；历史 J 排期不驱动任务。

## 2026-10-01 — 序境自有 AI 里程碑与取材修正

本节更新进行中的交付目标，保留前述 J1–J8、十五轮及六项真实验收义务。
Codex Cloud 是已配置的研发资源，不是序境产品部署。停止产品及研发调用
本地模型和智谱，只保留接口、既有成果与来源记录，不再延长 CPU 推理重试。

| 既有交付包 | 当前必须推进的结果 |
|---|---|
| J1 | 采集暂不完备时由开发者全网检索真实材料，经现有导入、Evidence、Canonical 链补入；明确人工/研发辅助发现，不冒充自动采集覆盖 |
| J2/J3 | 先按具体 CTH/BMP 任务选材料，区分品牌宣称、独立观察、个体观点、推断和创意；财报/讽刺不能冒充跑鞋消费者需求；资料充分才做对应结论 |
| J4/J5/J6 | 保留方案、视频、播客的全部已批准目标；采用同一来源与反馈链，恢复各自开发时消费真实案例，不丢专业制作要求 |
| J7 | 真实任务输入、报告版本、错误原因、修订与评估进入现有 Shared Learning；负样本不转成正向训练目标；候选学习资产、训练执行、留出评估、版本晋升分别留证 |
| J8 | 自有推理与工具执行在外部模型调用禁用、Codex 不代做任务时仍完成真实业务和恢复；最终由 Product Owner 统一重复操作验收 |

训练/学习材料必须绑定原任务、来源 Evidence、产物版本、反馈和适用范围。
未知/失败保留原状；外部文章的可读取性不自动等于权重训练或再分发许可。
以自有报告/反馈与经确认可用的材料建立样本，未经授权的全文不送外部训练服务。
`分析不可用` 是退出旧推理依赖后的临时诊断，不能作为本里程碑完成状态。

### 明确研究对象及当前采纳（查阅 2026-10-01）

- **OpenAI / Codex / ChatGPT**：[Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)
  的任务轨迹与结果评估方法适配现有 Evaluation、Reporting、Agent Runtime；
  ADAPT 方法，不直接增加外部推理依赖。现有 Codex Cloud 用于同一提交的隔离研发验证。
- **Claude / Anthropic**：[Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  的任务相关上下文选择、按需检索与持久任务笔记，适配现有 Source Brief、Skills、学习记录；
  ADAPT。先补合适的证据，再优化提示，不把更长上下文当成更强分析。
- **Meta Muse**：[官方产品说明](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/)
  和[安全设计](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse)
  是本次确认的对象：研究长期任务、执行环境、浏览器和独立动作授权边界；
  ADAPT 到既有 Runtime/Browser/Permission/Effect Fence，部署选择后置，不新增第二运行时。

以上为公开工程/产品方法研究，未复制专有代码、未获取模型内部推理或权重，
未新增依赖；不声称只读文档便获得对应模型能力。既有研究继续保留，过时运行建议
由本次明确决策覆盖，不能因此删除历史证据或遗漏产品能力。

### 自有推理的基础权重与训练边界（查阅 2026-10-01）

官方 [gpt-oss 发布说明](https://openai.com/index/introducing-gpt-oss/)
提供 Apache-2.0 开放权重以及自有环境运行/微调的路线；这与调用 OpenAI 托管 API
是不同部署方式，也不意味着权重由序境从零训练。Product Owner 已于本轮明确
批准采用 OpenAI 允许商用的开放基础权重，由序境自行训练、部署；不再等待基础
权重方向选择。尚未下载或启用模型，已停用的本地模型、智谱仍不恢复。

官方 [微调示例](https://developers.openai.com/cookbook/articles/gpt-oss/fine-tune-transfomers)
演示在已有基础模型上用 TRL/LoRA 和监督样本训练，示例环境为 H100 80GB。
这个示例不能证明本机具备对应训练速度，也不能把少量报告反馈等同于从零预训练。
此外该模型是文本模型，不能单独兑现本里程碑的图像理解要求。

决策：`ADAPT / OPENAI_OPEN_WEIGHTS_APPROVED`。优先核验官方 `openai/gpt-oss-20b`
固定版本、许可证、训练样本、LoRA 和独立部署；Codex 的开源客户端代码不等于
Codex 模型权重，不能借客户端许可证宣称专有模型可自行部署。
既有 Reporting、Learning、Evaluation 与 AI Gateway 保持唯一 owner；训练输入、
样本权利、留出任务、产物质量、推理部署和版本回滚分别需要实证。
人工选材或确定性摘录仍不是已训练推理；实际 GPU 训练、部署与留出任务效果尚未
验证。当前电脑实测约 16GB RAM、AMD 集成显卡 512MB；官方示例的 H100 80GB
是参考配方而非所有微调路线的绝对下限。算力开支和外部数据上传须另行确定；
Codex Cloud 不作为序境产品推理服务。原有学习对象和全部产品目标继续保留。

## 11. 提效、版本与停止条件

不再按 commit/文件/测试数量报进度。每批说明：关闭哪个 blocker、状态从哪到哪、commit、真实结果路径、剩余缺口及下一步。只跑变化 owner 的必要回归和 blocking gates；Round/集成候选时才 full gate。不通过反复全仓审计制造工作。

研究→小型对照 PoC→采用的 adapter→原 owner 真实链→必要测试→用户体验→回滚→精确 stage/commit/push。新依赖写入现有 Third-Party Register；研究条目不是安装清单。线上源码、证据和 CURRENT 状态同批发布；不 git add .，不积累多人长期未收敛候选。

Hosted CI 未实际运行则记录 EXECUTION_LAYER_UNAVAILABLE/LIVE_NOT_VERIFIED，不能当产品失败也不能写 PASS；不反复重跑 zero-step。最终发布须取得当期规定的同 SHA 独立验证，不能用本次研究静态检查代替。

**停止条件不是“方案写完”或“组件接上”。** 产品闭环要求当前冻结能力有真实任务、结果、恢复和适用表面的验收；商业上线另受真实数据权利、发布、运行及用户最终审核约束。本材料只完成研究与执行方案交付；未在本轮宣称任何产品能力因此闭环。

## 12. 本轮执行记录与核验范围

主控汇总前序视频/中国数据研究，并分派 CTH/BMP、Shared/AI 与播客三个只读研究切片；实际并发上限为主控加三个子 Agent，没有宣称十个窗口运行。子研究没有源码/DB写入；本文与索引/CURRENT 更新由主控单点编写。

按工作站规则尝试 OpenCode/Zhipu 做仅限文稿的机械检查。第一次 CLI 参数未被正确解析，未推理；纠正后返回 429/资源包不足，exit 1，没有可采用模型输出，实际模型未确认。没有重试充值问题、改变任何模型配置或读取凭据；最终覆盖/链接检查由确定性本地脚本完成，来源与决策由主控核验。

提交前核验范围为文稿本地链接、25 行能力/34 节/44 个 Screen ID 覆盖、Git diff whitespace、AI-native Constitution 与 Takeover governance。由于本轮仅资料与状态更新，不运行采集、渲染、数据库迁移、产品 E2E 或重型云端 Matrix；这些仍属于第 9–10 节的实际实施验收。静态文稿检查不能使任何产品状态升级。
