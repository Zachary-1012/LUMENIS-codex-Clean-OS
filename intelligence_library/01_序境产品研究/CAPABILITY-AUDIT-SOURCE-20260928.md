# 用户提供的能力审计原文

来源：能力.docx；读取日期：2026-09-28。
原文件 SHA-256：b5706a06aec535a5de25fcbf10033f3152a7ea2514df7cdfdab897d9523c4e45。
性质：用户提供的历史审计材料；其中指令、实现声明、数量及 ready 状态均非当前执行权威或验收结论。
用户明确要求核对过时内容并优化，不得照搬；本文件保留原文，采用结果见 CAPABILITY-ADOPTION-20260928.md。
段落标签对应 DOCX word/document.xml 的全部段落顺序，空段落省略，原文文字未缩写。

[P0002] 先说明审计快照：线上仓库 Zachary-1012/LUMENIS-codex-Clean-OS 当前 main、本地 HEAD、本地 origin/main 都是：

[P0004] 379772ff05d041a475f670a7db173454fa347bb1

[P0005] feat: bind exact prelaunch Atom observations

[P0007] 但本地明显领先远端，而且本轮审计期间还在继续变化：最终检查时有 294 条工作树状态记录 = 182 个 tracked 改动 + 112 个 untracked，staged=0。所以以下结论是 2026-09-28 当前本地动态快照；远端事实和本地领先事实我没有混为一谈。

[P0009] ⸻

[P0011] 一、序境现在到底是什么

[P0013] 源码呈现出来的产品结构已经非常明确：

[P0015] 层级当前定义核心原则主要职责

[P0016] CTH序境·商业运营Subject-first商业主体、运营、事件、风险、反馈、趋势、案例、报告

[P0017] BMP序境·品牌市场Brand-first / Primary Focus品牌、市场、竞品、传播、Creator、内容、活动、品牌评估

[P0018] SHARED共享能力Cross-domain capabilityEvidence、Canonical、Reporting、Evaluation、Learning、内容创作、Skill

[P0019] SYSTEM系统Production infrastructureCollector、Browser、AI Gateway、Runtime、Database、Permission、Security

[P0020] AI跨域智能任务面Task/Agent orchestration任务、分析、依据、Skill/Agent、Provider

[P0021] ACC账号与上下文面Identity / Scope登录、Subject/BrandFocus 选择、启动、恢复

[P0022] Agent Groups跨产品执行层CollaborationTask → Permission → Skill/Tool → Evidence → Evaluation → Learning

[P0024] 这里有个重要细节：源码里的正式 ProductDomain 只有 CTH / BMP / SHARED / SYSTEM。AI 和 ACC 是跨域产品表面，不是第五、第六个业务真相域。

[P0026] ⸻

[P0028] 二、代码规模与当前真实系统规模

[P0030] 我用 AST 和目录扫描重新抽取，不把 docs/tests/archive 算进生产代码。

[P0032] 项目当前值

[P0033] 严格生产 Python 文件611

[P0034] Flask / Blueprint API Routes805

[P0035] 有 API Route 的生产文件53

[P0036] Flutter 产品工作面44

[P0037] Flutter feature 目录44

[P0038] SYSTEM Collector 生产文件73

[P0039] Python 测试文件397

[P0040] Dart 测试文件60

[P0041] 当前数据库表113

[P0042] 当前非空表26

[P0043] 当前空表87

[P0045] 805 个 API ≠ 805 个产品功能。

[P0047] 里面同时存在 canonical owner、后台服务、兼容接口和历史迁移层。下面已经重新归类。

[P0049] ⸻

[P0051] 三、44 个用户可见工作面：完整能力表

[P0053] ACC｜账号、身份与工作上下文

[P0055] ID能力主要维度当前真实状态

[P0056] ACC-01领域登录 / 启动身份Runtime health、focus、账号边界已绑定；Product Account 仍 deferred；当前 Screen 部分 offline

[P0057] ACC-02主体/工作视角选择Domain、Subject、BrandFocus、Global/Focus已绑定；能读/选择/清除 Context；列表与工作视角模型已实现

[P0058] ACC-03全局工作空间启动Runtime、Context、CTH/BMP/AI 入口已绑定、ready

[P0059] ACC-04账号恢复与权限守卫Guard state、recovery path、auth已绑定；当前运行数据为空态

[P0061] ACC 背后远比 4 个页面丰富。account/api.py 当前有 51 条 API，包括：

[P0063] 资料、改密、设备/会话、成员、双域授权、登录审批、审计、账号恢复、Workspace Key、验证码、TOTP、Product Protection、导航配置、Skill 管理、MCP Skill、GitHub Connector、Quota。

[P0065] 后端账号体系已经很完整，但 Flutter 内测阶段仍明确：

[P0067] productAccountDeferred = true

[P0069] 所以“账号系统存在”和“正式 SaaS 产品账号墙已上线”是两件事。

[P0071] ⸻

[P0073] 四、CTH｜商业运营

[P0075] CTH 现在是全产品里Scope / Permission / Evidence 收口最严格的一块。

[P0077] ID用户能力数据/分析维度当前源码级状态

[P0078] CTH-01商业运营总览负面声音、开放事件、日报摘要、风险、运营变化账户+Context 保护已完成；真实业务数据当前仍 UNAVAILABLE

[P0079] CTH-02主体档案 / 业务单元 / 品牌业态Subject Registry、主体类型、组织关系Registry/选择能力已实现；完整业务单元/品牌事实仍存在未采集部分

[P0080] CTH-03实时监测Canonical content、平台、时间、情感、风险、Evidence目前 CTH 数据链最完整的页面；严格要求 Scope + Canonical + Evidence V2

[P0081] CTH-04事件与事件关系Event、时间线、关系、EvidenceExact actor scope 已强制；真正 scoped event 数据消费仍待闭环

[P0082] CTH-05舆情日历时间、负面、高风险、事件密度Scope 已强制；Canonical scoped 数据未最终接入

[P0083] CTH-06负面与用户反馈评论、负面、风险、客户声音Scope 已强制；最终 scoped feedback 绑定未闭合

[P0084] CTH-07趋势分析时间序列、情感、风险、传播变化Scope 已强制；最终 scoped trend 未闭合

[P0085] CTH-08案例/案例分析/知识Case、Event、Knowledge、EvidenceScope 已强制；canonical Case 生命周期仍未完成

[P0086] CTH-09风险中心与决策Risk、Decision、Evidence、ActionScope 已强制；Risk 有基础，Canonical Decision record 尚未完整闭环

[P0087] CTH-10报告 / 周报 / EvidenceReport、Artifact、Evidence、时间周期Scope 已强制；Shared Reporting 能力已存在，CTH 页面最终 scoped consumer 待接通

[P0089] CTH-03 当前特别值得单独说

[P0091] 它现在不是老式“查 notes 表显示出来”。

[P0093] 源码明确要求 Canonical Row 至少有：

[P0095] canonical_id

[P0096] source_id

[P0097] title/content

[P0098] publish_datetime/captured_at

[P0099] sentiment

[P0100] risk_level

[P0101] domain_id/product_id

[P0102] subject_id

[P0103] scope_status

[P0104] scope_evidence_ref

[P0106] 同时对应 Evidence 必须：

[P0108] * result=PASS

[P0109] * status=verified

[P0110] * integrity_version=2

[P0111] * integrity digest 验证通过

[P0112] * Assurance 至少是 writer-authenticated 或 content-integrity-only

[P0113] * 与当前 ReportScope 匹配

[P0114] * digest 是合法 64 位 hash

[P0116] 这已经接近你一直要求的：

[P0118] External → Evidence → Canonical → Subject → Experience

[P0120] 而不是普通数据库页面。

[P0122] ⸻

[P0124] 五、BMP｜品牌市场

[P0126] BMP 功能面非常广，但数据 Scope 收敛成熟度目前落后于 CTH。这是本轮源码审计最重要的结论之一。

[P0128] ID能力关键维度当前状态

[P0129] BMP-01品牌市场总览BrandFocus、声量、负面、高风险、互动、趋势、事件账号/Focus 保护已实现；当前业务真值 UNAVAILABLE

[P0130] BMP-02品牌中心 / 多品牌 / 竞品Brand directory、类别、品牌关系有真实 curated directory；尚不等于完整单品牌健康/声量分析

[P0131] BMP-03市场情报Intelligence asset、平台、市场信息页面已绑定；当前 table 为空 / NOT_COLLECTED

[P0132] BMP-04传播分析传播事件、渠道、实体、关系Runtime 有数据结构；最终 BrandFocus scope 仍需收口

[P0133] BMP-05Creator / KOS/KOL/KOC/UGCCreator、tier、relationship、conversion页面已绑定，但当前运行数据为空

[P0134] BMP-06内容中心内容资产、Content Generation、Evidence当前页面 ready，有真实后台内容模块

[P0135] BMP-07话题活动Campaign、Topic、Quota、Cooldown、运行态运行控制存在；最终只读 Campaign Business View 尚不完整

[P0136] BMP-08播客工作台Topic、Entity、Story、Breakout、Yield后台 Podcast Engine 存在；当前表面为空

[P0137] BMP-09品牌报告与评估Report、Evaluation、Evidence、评分Reporting/Evaluation 已有；部分表当前为空

[P0138] BMP-10品牌风险与事件Risk、Event、Brand页面和结构已存在；当前 Event/Risk 均为空

[P0139] BMP-11对标与竞品分析Competitor、Benchmark、ScoreBenchmark 后台存在；最终 Selected BrandFocus scope 仍待完成

[P0141] BMP 当前最大的结构性问题

[P0143] 现在 _FOCUS_BOUND_SCREEN_DOMAINS 只明确包含：

[P0145] CTH-01

[P0146] BMP-01

[P0148] CTH-03～10 又有单独的 exact-scope Permission 路径。

[P0150] 而 BMP-02～11 当前仍主要通过各自 builder 返回结果。

[P0152] 所以现在不能把：

[P0154] BMP-02～11 已有页面/API

[P0156] 等同于：

[P0158] BMP-02～11 已经完成 BrandFocus → Evidence → Canonical 的最终闭环。

[P0160] 这应该正是你现在让 Codex 做的数据收敛工作之一。

[P0162] ⸻

[P0164] 六、AI 能力

[P0166] ID能力具体维度当前状态

[P0167] AI-01发起任务Intent、Provider、Suggestion、Context、Unavailable Field已绑定并 ready

[P0168] AI-02任务进度Task、Step、Execution proof、Permission、Evidence refsAPI/模型完整；当前 timeline 空

[P0169] AI-03分析与依据Citation、Evidence、Context、Lineage、ThreadEvidence 面 ready；任务 timeline 当前空

[P0170] AI-04Agent / Skill 中心Skill owner、risk、permission、execution policy、evaluationready

[P0171] AI-05AI Gateway / ProviderProvider state、latency、calls、availabilityready

[P0173] AI Task 后台还有 34 个 API：

[P0175] * Provider 状态

[P0176] * Chat

[P0177] * Sentiment

[P0178] * Summary

[P0179] * Keyword

[P0180] * AI Filter

[P0181] * Channel Health

[P0182] * Analyze

[P0183] * Learning optimization

[P0184] * Task 创建

[P0185] * Task 执行

[P0186] * Steps

[P0187] * Evidence

[P0188] * Approve

[P0189] * Cancel

[P0190] * Task List

[P0191] * Skills

[P0192] * Agents

[P0193] * Capabilities

[P0194] * Trace

[P0195] * Permissions

[P0196] * Task Engine Health

[P0197] * DLQ

[P0199] 所以 AI 在序境里已经不是一个 /chat。

[P0201] ⸻

[P0203] 七、AI Gateway 本身的能力

[P0205] Canonical Owner：

[P0207] lumenis/system/ai_gateway/

[P0209] 当前包括：

[P0211] 能力实现

[P0212] 本地模型发现Ollama model catalog / local detection

[P0213] 云端/本地 Provider 路由Provider Config + capability routing

[P0214] 模型能力选择select_model_by_capability()

[P0215] 本地 Ollama Chat已实现

[P0216] Vision已实现

[P0217] Cloud 数据脱敏redact_for_cloud()

[P0218] Sentiment已实现

[P0219] Summary已实现

[P0220] Keyword已实现

[P0221] Translation已实现

[P0222] Search Enhancement已实现

[P0223] Report generation已实现

[P0224] Review Note已实现

[P0225] Event Summary已实现

[P0226] Batch已实现

[P0227] Cache已实现

[P0228] Budget accounting已实现

[P0229] Circuit Breaker已实现

[P0230] Retry/backoff已实现

[P0231] Provider fallback已实现

[P0232] Provider heartbeat已实现

[P0233] Failover log已实现

[P0234] Token usage已实现

[P0236] 当前运行态我实际查到：

[P0238] Local AI = running

[P0240] Provider：

[P0242] ollama

[P0244] Current Model：

[P0246] qwen3:1.7b

[P0248] 本机检测到：

[P0250] 5 个 Ollama 模型

[P0252] Fallback：

[P0254] local_rule

[P0256] 因此序境现在确实可以在外部云 AI 不可用时继续运行自己的确定性流程 + 本地 AI。

[P0258] 同时 Cloud AI governance 里：

[P0260] primary_provider = zhipu

[P0262] 但当前：

[P0264] active_providers=[]

[P0266] 当天云调用：

[P0268] 0

[P0270] 所以“有 Provider 路由能力”和“此刻正在调用某云模型”也已经分开。

[P0272] ⸻

[P0274] 八、Agent / Skill 能力

[P0276] 现在 Skill 的真实执行链已经是：

[P0278] Task → Permission → Action Firewall → Effect Fence → Execute → Artifact → Evidence → Evaluation → History Readback → Learning → Trace

[P0280] 并不是“AI 直接执行工具”。

[P0282] Canonical Runtime Skill

[P0284] 当前 in-memory Registry 是：

[P0286] 9 个

[P0288] 其中 SYSTEM 内建：

[P0290] Skill能力

[P0291] zbc.subject_authority_readSubject authority 状态只读

[P0292] zbc.skill_registry_snapshotSkill Registry 只读快照

[P0293] zbc.agent_boundary_auditAgent boundary / Permission 审计

[P0295] 另有 6 个 Shared Skills：

[P0297] Skill用户能力

[P0298] shared.union_search跨平台/跨来源选题搜索

[P0299] shared.video_shotcraft片头、镜头、转场草稿

[P0300] shared.cangjie内容结构化提炼

[P0301] shared.huashuBrief→选题→文案→视频→封面→评估

[P0302] shared.social_card多平台封面 SVG 草稿

[P0303] shared.last30days最近 30 天 Canonical 话题/变化扫描

[P0305] 数据库里的 skills_registry 当前有 21 行，但这不能直接解读成“21 个可执行能力”——它还包含 lifecycle/custom/disabled 等状态。

[P0307] ⸻

[P0309] 九、Shared｜共享能力

[P0311] SH-01～06

[P0313] 工作面能力当前状态

[P0314] SH-01内容创作工作区Skill catalog 可读；业务数据当前部分 offline

[P0315] SH-02Evidence 库ready

[P0316] SH-03Canonical / Metric 浏览能力 ready；当前 table empty

[P0317] SH-04Report / Export 中心ready

[P0318] SH-05Learning / Evaluation 资产结构 ready；当前资产空

[P0319] SH-06Notification / Task 中心runtime ready；当前 task table 空

[P0321] ⸻

[P0323] 十、Evidence：序境最重要的核心资产之一

[P0325] Evidence 当前已经包含：

[P0327] 维度能力

[P0328] IdentityEvidence ID

[P0329] Content integrityFull content hash

[P0330] Writer integrityHMAC Key Ring

[P0331] Canonical encodingCanonical JSON

[P0332] VersionEvidence Integrity V2

[P0333] Scopedomain / Subject / BrandFocus

[P0334] StatusPASS / fail / verified

[P0335] Assurancewriter-authenticated / content-integrity-only / legacy / unverifiable

[P0336] VerificationDigest 校验

[P0337] ResealEvidence reseal

[P0338] Legacy upgrade老 Evidence 升级

[P0339] Failed writes写失败记录

[P0340] DLQDead-letter replay

[P0341] Queryscoped Evidence query

[P0342] Health Evidence系统健康证据

[P0343] Collection Evidence采集证据

[P0344] StatisticsEvidence stats

[P0345] LineageEvidenceChain / provenance

[P0347] 当前 DB：

[P0349] app_evidence_records = 193

[P0351] 这不是 fixture 计数，是当前运行数据库。

[P0353] ⸻

[P0355] 十一、Canonical Data 能力

[P0357] Canonical 当前不是简单标准化字段表。

[P0359] 它包含：

[P0361] 能力当前实现

[P0362] Canonical Record有

[P0363] Canonical ID有

[P0364] Content Hash有

[P0365] Note → Canonical有

[P0366] Web Mention → Canonical有

[P0367] Collected Note → Canonical有

[P0368] Full Sync有

[P0369] Subject/Brand Scope有

[P0370] Scope Evidence Ref有

[P0371] Dedup有

[P0372] Sentiment有

[P0373] Time normalization有

[P0374] Schema version有

[P0375] Self-check有

[P0376] Get/List/Count有

[P0378] 当前 DB：

[P0380] notes = 220

[P0381] canonical_data = 220

[P0383] 所以现在确实已经出现：

[P0385] Raw/business note → Canonical

[P0387] 的真实数据量。

[P0389] ⸻

[P0391] 十二、实体、地点和全球范围维度

[P0393] entity_relations.py 已经把序境从“只识别帖子”推进到实体关系层。

[P0395] 包含：

[P0397] * Subject

[P0398] * Country

[P0399] * ISO Country

[P0400] * Locale

[P0401] * Time-valid relation

[P0402] * Evidence binding

[P0403] * Venue / tenant assertion

[P0404] * Domain

[P0405] * Entity relation repository

[P0407] 当前：

[P0409] lumenis_entity_relation_assertions = 269

[P0411] Subject Registry 当前：

[P0413] 157 条

[P0415] ⸻

[P0417] 十三、你说的“全球数据”到底覆盖到什么程度

[P0419] 这里源码给了非常明确的答案。

[P0421] 1. 平台字段理解 / Canonical Mapping 层：20 类来源

[P0423] 当前 platform_naming.py 能理解：

[P0425] 国内/区域全球/公开来源

[P0426] 小红书 / RedNoteInstagram

[P0427] 抖音Facebook

[P0428] 快手X

[P0429] 微博YouTube

[P0430] BilibiliTikTok

[P0431] 知乎Reddit

[P0432] 贴吧LinkedIn

[P0433] 视频号GitHub

[P0434] Web RSSPublic HTTP

[P0435] Web AtomSitemap

[P0437] 这些都有不同程度的：

[P0439] * native content ID

[P0440] * author ID

[P0441] * publish time

[P0442] * likes

[P0443] * comments

[P0444] * shares

[P0445] * collects

[P0446] * views

[P0447] * content type

[P0448] * URL

[P0449] * BigInt ID protection

[P0451] 2. Collector Operational Config：14 个

[P0453] 当前 Collector 运行配置里有：

[P0455] XHS、Douyin、Kuaishou、Bilibili、Weibo、Web RSS、Public HTTP、Atom、Sitemap、Tieba、Zhihu、Instagram、Facebook、X。

[P0457] 3. 当前数据库 Platform Registry：12 行

[P0459] 但是当前 /api/data-center/platforms 只展示 3 个产品可见平台：

[P0461] 平台当前 Registry

[P0462] 小红书ACTIVE

[P0463] BilibiliPARTIAL

[P0464] 抖音PARTIAL

[P0466] 所以这里存在一个正在收敛中的多注册表问题：

[P0468] Native Mapping 20

[P0469] ≠ Collector Config 14

[P0470] ≠ Platform Registry 12

[P0471] ≠ Data Center 可见 3

[P0473] 这就是我认为你当前“全球数据闭环”真正应该继续收口的一项。

[P0475] 而且 AcquisitionPlan 源码明确写的是：

[P0477] world_completeness = NOT_ASSERTED

[P0479] 这非常正确。

[P0481] 因此序境所说的“全球数据”应该准确理解为：

[P0483] 按已注册、已批准、可验证来源构建的全球覆盖范围。

[P0485] 不是声称：

[P0487] 全互联网 / 全世界信息全部覆盖。

[P0489] ⸻

[P0491] 十四、当前采集能力

[P0493] SYSTEM Collector 目前至少覆盖这些层：

[P0495] 层能力

[P0496] Acquisition PlanCTH/BMP query plan、Global/Focus scope

[P0497] Adapter Registry平台能力注册

[P0498] Platform Naming原生字段→Canonical

[P0499] Public Source公共网页

[P0500] RSS / AtomFeed

[P0501] SitemapURL discovery

[P0502] XHS / RedNotePrimary

[P0503] Bilibili / WeiboSecondary

[P0504] Douyin / Kuaishou / Zhihu / InstagramSecondary / gated

[P0505] Overture Places地点候选

[P0506] Venue Directory商业地点

[P0507] Multi-platform Import多平台导入

[P0508] Deduplicate去重

[P0509] Normalize标准化

[P0510] Spam Filter过滤

[P0511] Subject Filter主体匹配

[P0512] Persist持久化

[P0513] Evidence ExportEvidence

[P0514] QueueTask Queue

[P0515] Rate Limit限速

[P0516] Risk Engine风控

[P0517] Runtime Guardian生命周期

[P0518] DLQ Replay恢复

[P0519] Scheduler调度

[P0520] Health Center健康检查

[P0522] 当前实时状态

[P0524] 浏览器：

[P0526] CDP 9223 = running

[P0528] 数据库：

[P0530] 220 notes

[P0532] 今天数据：

[P0534] 220

[P0536] 但当前 XHS / RedNote：

[P0538] SESSION_EXPIRED

[P0540] 健康中心：

[P0542] overall_status = critical

[P0544] 原因是：

[P0546] 当前 HK/International collection Cookie/session 无效。

[P0548] 这说明：

[P0550] Collector 架构存在、Browser Runtime 也在线，但当前 XHS live collection 处于身份恢复阻塞。

[P0552] ⸻

[P0554] 十五、内容创作能力

[P0556] content_generation.py 当前正式注册 8 类生成能力：

[P0558] 类型能力

[P0559] ad_copy广告文案

[P0560] podcast_topic播客选题

[P0561] brand_report品牌报告

[P0562] creative_idea创意方向

[P0563] kos_contentKOS 内容

[P0564] video_script视频脚本

[P0565] social_ops社媒运营策略

[P0566] pr_responsePR 回应话术

[P0568] 标准流程是：

[P0570] Research Context → Generation → Evidence → Evaluation

[P0572] 并不是只把 Prompt 发给模型。

[P0574] 内容质量内部还有 4 个维度：

[P0576] 维度

[P0578] Relevance 相关性

[P0580] Creativity 创意性

[P0582] Brand Fit 品牌契合

[P0584] Platform Fit 平台适配

[P0586] ⸻

[P0588] 十六、内容方法论 / 创作结构

[P0590] 新的 Shared Content Contract 已经进一步定义：

[P0592] Narrative Pattern

[P0594] Story premise、Observation、Conflict、Progression、Resolution、Viewer inference、Source refs。

[P0596] White Description

[P0598] 具体物件、动作、对话、环境声、留白，以及：

[P0600] * 抽象情绪词密度

[P0601] * 解释性旁白冗余

[P0602] * 画面文字重复率

[P0604] Emotion Experience

[P0606] Trigger、Context、Sensory Cue、Relationship、Contradiction、Before、Turning Point、After。

[P0608] Visual Motif

[P0610] Motif、首次意义、重复、转化、最终 payoff。

[P0612] Shot

[P0614] Narrative beat、Emotional beat、Shot purpose、Shot size、Camera motion、Action、Continuity、Audio、VO、Subtitle、Transition、Timing、Evidence ref。

[P0616] 这已经超过普通“AI 写文案”。

[P0618] ⸻

[P0620] 十七、视频能力

[P0622] 目前真实实现有：

[P0624] MediaAsset

[P0625] Media Fingerprint

[P0626] ffprobe

[P0627] AudioMix

[P0628] Timeline

[P0629] TimelineClip

[P0630] TimelineTrack

[P0631] Transition

[P0632] TimedOverlay

[P0633] EditDecision

[P0634] EditDecisionList

[P0635] EDL proposal / apply

[P0637] 但当前源码仍明确存在：

[P0639] artifact_integration = unavailable_for_edited_timeline

[P0641] 和：

[P0643] canonical_evidence_binding = unavailable

[P0645] 因此视频能力的准确状态是：

[P0647] 编辑核心存在；最终 Artifact/Evidence 闭环尚未完成。

[P0649] ⸻

[P0651] 十八、KOS / Creator 能力

[P0653] 后台 kos_routes.py 当前有 53 条 API。

[P0655] 实际覆盖：

[P0657] 领域能力

[P0658] Creator profile列表 / 详情 / refresh

[P0659] 内容Comments / Content DNA

[P0660] IdentityKOS Identity

[P0661] 分层Tier / KOC Tier

[P0662] IntentIntent Analysis

[P0663] BenchmarkCompetitor Benchmark

[P0664] FunnelViewership → WeCom → Sales

[P0665] CostCPL/CPC/Cost-per-WeCom

[P0666] Attribution单人/多触点归因

[P0667] OutreachOutreach

[P0668] LeadsLead

[P0669] Cooperation合作状态

[P0670] Ownership品牌归属

[P0671] Manual confirmation人工归属确认

[P0672] CampaignCampaign

[P0673] Channel ROI渠道 ROI

[P0674] ReportKOS Report

[P0675] Reply回复生成

[P0676] Email邀约 / 发送

[P0677] Execution生命周期

[P0678] Paid MediaPlan / Execute / Result

[P0679] RewardIssue / Execute / Ledger

[P0680] ProfessionalEnable / Disable / Import / Metrics

[P0682] 特别注意：

[P0684] 真实投流与 Reward 被 Security 体系区分为高风险 Action。

[P0686] 其中：

[P0688] AD_EXECUTE = CRITICAL

[P0690] 不能把 AI 建议直接当真实资金动作。

[P0692] ⸻

[P0694] 十九、Topic / Campaign

[P0696] 当前 16 个 API，包括：

[P0698] * status

[P0699] * topics

[P0700] * run

[P0701] * recovery

[P0702] * runtime-state

[P0703] * half-open probe

[P0704] * note detail

[P0705] * detail backfill

[P0706] * timeline

[P0707] * stats

[P0708] * notes

[P0709] * export

[P0710] * campaign list

[P0711] * save

[P0712] * toggle

[P0714] 所以 Topic Campaign 已经是一个带 runtime/recovery 的能力，不只是关键词列表。

[P0716] ⸻

[P0718] 二十、Podcast

[P0720] 当前 9 个核心路由：

[P0722] * Overview

[P0723] * Entities

[P0724] * Entity

[P0725] * Create Entity

[P0726] * Topic Score

[P0727] * Story Nodes

[P0728] * Runtime Validate

[P0729] * Breakout

[P0730] * Content Yield

[P0732] 并且 Content Generation 还有：

[P0734] podcast_research

[P0736] 所以 Podcast 当前包含：

[P0738] Research → Topic → Entity → Story Node → Breakout → Content Yield

[P0740] ⸻

[P0742] 二十一、案例 / PR / Knowledge

[P0744] 实际后台存在：

[P0746] PR Case

[P0748] * PR Case List

[P0749] * Detail

[P0750] * ACT Principle

[P0751] * Trigger

[P0752] * Response Template

[P0753] * Case Match

[P0755] Public Opinion / Case Analysis

[P0757] * Case stats/list/detail/search

[P0758] * Methodology

[P0759] * System insight

[P0760] * Template match

[P0761] * Crisis SOP

[P0762] * AI evaluate

[P0764] Event Graph

[P0766] * Events

[P0767] * Chain

[P0768] * Type

[P0769] * Relation

[P0770] * Import

[P0771] * Rebuild relation

[P0773] 这就是 CTH-04 / CTH-08 后面的已有资产，但当前 final canonical scope 仍在收口。

[P0775] ⸻

[P0777] 二十二、Reporting：不是简单“导出 Word”

[P0779] 当前 Reporting 有至少三层。

[P0781] 基础周期

[P0783] 类型

[P0785] Daily

[P0787] Weekly

[P0789] Monthly

[P0791] Yearly

[P0793] Special

[P0795] CTH 报告

[P0797] 类型

[P0799] 日报

[P0801] 周报

[P0803] 月报

[P0805] 事件专报

[P0807] 风险专报

[P0809] 太古汇情报报告

[P0811] BMP / ZBMP 报告

[P0813] 类型

[P0815] Brand

[P0817] Performance

[P0819] Competitive

[P0821] Growth

[P0823] Content

[P0825] Brand Risk

[P0827] Scoped Reporting 还负责：

[P0829] * Actor Scope authorization

[P0830] * Evidence query

[P0831] * Canonical query

[P0832] * Evidence integrity

[P0833] * Canonical lineage

[P0834] * Scope matching

[P0835] * Public-value sanitization

[P0836] * Stable payload

[P0837] * Return token

[P0838] * Markdown

[P0839] * CSV

[P0840] * Artifact persistence

[P0841] * Stale lineage detection

[P0842] * Reopen

[P0844] 另外 Export API 有：

[P0846] Excel

[P0847] Word

[P0848] Unified Export

[P0849] Preview

[P0850] File Retrieval。

[P0852] ⸻

[P0854] 二十三、Reporting 自身的业务分类体系

[P0856] Event Type：12 类

[P0858] 产品/服务质量、客户服务、价格促销、品牌形象、安全、设施环境、停车交通、营销活动、会员 CRM、租户品牌、公众舆论、Other。

[P0860] Risk：4 级

[P0862] Critical / High / Medium / Low。

[P0864] Sentiment：4 类

[P0866] Positive / Neutral / Negative / Mixed。

[P0868] 传播主体：7 类

[P0870] Official / KOL / KOC / Normal User / Media / Competitor / Bot。

[P0872] Fact Status：4 类

[P0874] Confirmed / Partially Confirmed / Unconfirmed / Refuted。

[P0876] Report Period：5 类

[P0878] Daily / Weekly / Monthly / Yearly / Event。

[P0880] ⸻

[P0882] 二十四、Evaluation：现在有完整 5 大维度、20 个指标

[P0884] 这是当前源码真正定义的评价体系。

[P0886] 大维度指标PASSWARN

[P0887] Datacompleteness≥90%≥70%

[P0888] Datafreshness_hours≤24h≤72h

[P0889] Dataduplication_rate≤5%≤15%

[P0890] Dataprovenance_rate≥95%≥80%

[P0891] AIaccuracy≥85%≥70%

[P0892] AIconfidence_avg≥70%≥50%

[P0893] AIhuman_correction_rate≤10%≤25%

[P0894] AIprovider_reliability≥90%≥75%

[P0895] AIfallback_rate≤20%≤40%

[P0896] Collectorsuccess_rate≥85%≥60%

[P0897] Collectorfailure_rate≤10%≤30%

[P0898] Collectorrecovery_rate≥70%≥40%

[P0899] Collectorlatency_sec≤120s≤300s

[P0900] Reportgeneration_success≥90%≥70%

[P0901] Reportartifact_validity≥90%≥70%

[P0902] Reportevidence_coverage≥80%≥60%

[P0903] Runtimeuptime_hours≥24h≥1h

[P0904] Runtimeheartbeat_rate≥95%≥80%

[P0905] Runtimecrash_count0≤3

[P0906] Runtimerecovery_count≤2≤5

[P0908] 状态统一：

[P0910] pass / warn / fail / unknown

[P0912] 而且：

[P0914] None → unknown，绝不自动 PASS。

[P0916] 一个需要你未来确认的地方是 runtime.recovery_count 当前按“越少越好”设计；技术上它是在衡量“需要恢复的次数”，逻辑成立，但名称本身容易被理解成“恢复成功次数”，后面最好重新命名。

[P0918] 另外 AI accuracy 目前源码自己也承认是简化口径：把部分 filter result 当“正确”，真正的 accuracy 以后仍应该绑定人工标注/benchmark。

[P0920] ⸻

[P0922] 二十五、Learning：不是 AI 自己随便改系统

[P0924] 当前 Learning 包含：

[P0926] * Feedback

[P0927] * Pattern

[P0928] * Rule Suggestion

[P0929] * Learning Loop

[P0930] * Operation Learning

[P0931] * Collector Learning

[P0932] * Content Asset Learning

[P0933] * Persistence

[P0934] * Memory

[P0935] * History

[P0936] * Optimization Suggestion

[P0937] * Promotion status

[P0938] * Review state

[P0939] * Rollback availability

[P0940] * Version

[P0942] 核心逻辑已经是：

[P0944] 真实结果 → Feedback → Evaluation → Suggestion → Review/Promotion → Versioned Asset

[P0946] 而不是模型直接修改 Product Truth。

[P0948] ⸻

[P0950] 二十六、Security / Permission 维度

[P0952] Permission Level：11 级

[P0954] READ

[P0955] AUDIT

[P0956] ANALYZE

[P0957] RESEARCH

[P0958] PLAN

[P0959] PATCH_PREVIEW

[P0960] TEST

[P0961] VERIFY

[P0962] HUMAN_APPROVAL

[P0963] COMMIT

[P0964] PUSH

[P0966] Risk：4 级

[P0968] LOW / MEDIUM / HIGH / CRITICAL。

[P0970] Operation：15 类

[P0972] Operation风险定位

[P0973] AI_CALLLow

[P0974] REPORT_GENERATELow

[P0975] FILE_WRITEMedium

[P0976] COLLECTOR_START/STOPMedium

[P0977] DATA_EXPORTMedium

[P0978] SKILL_EXECUTEMedium

[P0979] BROWSER_OPERATIONMedium

[P0980] EXTERNAL_NETWORKLow

[P0981] AD_PREVIEWMedium

[P0982] CONFIG_MODIFYHigh

[P0983] DB_WRITEHigh

[P0984] DATA_IMPORTHigh

[P0985] RUNTIME_OPERATIONHigh

[P0986] AD_EXECUTECritical

[P0987] DATA_DELETECritical

[P0989] 此外还有：

[P0991] * Actor role

[P0992] * Resource grant

[P0993] * Domain action

[P0994] * Subject scope

[P0995] * BrandFocus scope

[P0996] * Global scope

[P0997] * Approval Token

[P0998] * Audit Entry

[P0999] * Action Firewall

[P1000] * Effect Fence

[P1001] * Idempotency

[P1002] * Fail-closed

[P1004] 这部分已经是序境区别于普通 AI Agent 产品的重要能力。

[P1006] ⸻

[P1008] 二十七、Browser 能力

[P1010] 后台至少有两套服务表面，最终正在收敛到 SYSTEM Browser。

[P1012] Browser Surface：29 API

[P1014] 包括：

[P1016] Tabs、New/Close/Activate、Navigate、History、Screenshot、Extract、Search、Bookmarks、General Browser、Find、Downloads、Download Monitor、Hybrid Analyze。

[P1018] Internal Browser：16 API

[P1020] 包括：

[P1022] Accounts、State、Screenshot、Navigate、Tabs、Refresh、Evaluate、Click、Type、Scroll、History、Find、Selector、Task。

[P1024] Canonical Runtime 里还有：

[P1026] * CDP Adapter

[P1027] * Playwright Adapter

[P1028] * XHS Collector Bridge

[P1029] * Browser Contract

[P1030] * Policy

[P1031] * Router

[P1033] 但：

[P1035] SYS-06 是 44 个页面里唯一被 Flutter 明确标成 unavailable 的页面。

[P1037] 所以准确说法是：

[P1039] Browser Core/Backend 已经很强，但最终用户 Workspace Browser 尚未正式开放。

[P1041] ⸻

[P1043] 二十八、SYSTEM 8 个工作面

[P1045] ID能力当前运行态

[P1046] SYS-01Runtime Healthready

[P1047] SYS-02Collector Statusready

[P1048] SYS-03Database & Truth Chainready

[P1049] SYS-04Security & Permissionready

[P1050] SYS-05Settings / Appearance / Languageready

[P1051] SYS-06Internal BrowserBackend ready；Flutter unavailable

[P1052] SYS-07Acceptance / Evaluationready

[P1053] SYS-08Observability / Logsready

[P1055] SYS-03 当前运行数据库能看到：

[P1057] 113 tables

[P1059] 其中：

[P1061] * notes 220

[P1062] * canonical_data 220

[P1063] * app_evidence_records 193

[P1064] * platform_contents 30

[P1065] * platform_registry 12

[P1066] * topic_campaigns 1

[P1067] * topic topics 7

[P1068] * topic snapshots 7

[P1069] * metric snapshots 30

[P1070] * schema_version 18

[P1071] * subject registry 157

[P1072] * entity relations 269

[P1073] * web_runs 193

[P1075] 这说明 Truth/Data 系统不是空架构。

[P1077] ⸻

[P1079] 二十九、运行、恢复、可观测

[P1081] 产品还有：

[P1083] Runtime Guardian

[P1084] Worker State

[P1085] Heartbeat

[P1086] Crash

[P1087] Recovery

[P1088] DLQ

[P1089] Alerts

[P1090] Circuit Breaker

[P1091] Network status/reset

[P1092] Cache

[P1093] Collector quality

[P1094] Security scan

[P1095] Security audit

[P1096] File integrity

[P1097] System health

[P1098] Module health

[P1099] Adaptive collection

[P1100] Recovery cycle

[P1101] Feedback cycle

[P1102] Boundary confirmation。

[P1104] architecture_api.py 里还有：

[P1106] Adaptive

[P1107] Recovery

[P1108] Feedback

[P1109] Boundary Safety

[P1110] File Integrity

[P1111] Architecture Status。

[P1113] ⸻

[P1115] 三十、Public Website 与多端产品

[P1117] 现在真实产品 Surface 是：

[P1119] Surface当前情况

[P1120] Public WebsiteAstro；中文/英文/韩文

[P1121] Web WorkspaceFlutter Web + same-origin Flask host

[P1122] Windows AppFlutter

[P1123] AndroidFlutter

[P1124] iOSFlutter source target

[P1125] macOSFlutter source target

[P1126] LinuxFlutter source target

[P1128] 本轮前面实际验证过：

[P1130] * Flutter tests：431 passed

[P1131] * Flutter Web Release：Build success

[P1132] * Public Website：Build + 9/9 tests

[P1133] * Windows Release：成功重新 build

[P1134] * Windows App smoke：Alive=True / Responding=True

[P1135] * Android APK：已有 Release build

[P1136] * 当前 Windows 没有 Android emulator/device，所以 Android 实机 acceptance 尚未建立

[P1137] * macOS / iOS / Linux 当前这台机器无法给出 runtime acceptance

[P1139] 所以：

[P1141] “代码支持六端” ≠ “六端全部 Release Accepted”。

[P1143] ⸻

[P1145] 三十一、现在真正的产品语义维度

[P1147] 把整个代码库抽象成业务数据维度，序境实际上已经覆盖：

[P1149] 维度内容

[P1150] IdentitySubject / BrandFocus / User / Actor

[P1151] OrganizationCompany / Business Unit / Brand / Tenant

[P1152] GeographyCountry / ISO / City / Venue / Location

[P1153] TimePublish / Capture / Event / Period / Freshness

[P1154] SourcePlatform / URL / Origin / Adapter

[P1155] ContentNote / Post / Video / Article / Feed

[P1156] CreatorAuthor / KOL / KOC / KOS / UGC

[P1157] EngagementLike / Comment / Share / Collect / View

[P1158] SentimentPositive / Neutral / Negative / Mixed

[P1159] RiskCritical / High / Medium / Low

[P1160] EventEvent Type / Chain / Relation / Fact Status

[P1161] MarketBrand / Competitor / Market Intelligence

[P1162] PropagationChannel / Event / Creator / Relation

[P1163] Content CreationBrief / Pattern / Draft / Script / Shot / Artifact

[P1164] EvidenceSource / Hash / Integrity / Assurance / Lineage

[P1165] CanonicalUnified ID / Fields / Dedup / Scope

[P1166] PermissionActor / Role / Resource / Domain / Exact Scope

[P1167] ActionRead / Analyze / Write / Import / Export / Publish

[P1168] EvaluationData / AI / Collector / Report / Runtime

[P1169] LearningFeedback / Pattern / Rule / Promotion / Rollback

[P1170] ReportingDaily / Weekly / Monthly / Special / Brand / Risk

[P1171] RuntimeHealth / Worker / Circuit / Recovery

[P1172] ExperienceDesktop / Mobile / Web / Public Site

[P1174] 这其实已经是一个相当完整的商业信息操作模型。

[P1176] ⸻

[P1178] 三十二、当前最重要的“不应被误判为完成”的部分

[P1180] 项目准确状态

[P1181] CTH-01Context 已保护，业务总览数据尚未真正连接

[P1182] CTH-03Scope + Evidence + Canonical 闭环最成熟

[P1183] CTH-04～10权限/Scope 已收敛，但最终数据消费者仍被明确 fail-closed

[P1184] BMP-01Brand Focus 保护存在，业务真值未接通

[P1185] BMP-02～11功能丰富，但 BrandFocus exact scope 仍没有达到 CTH 的严格程度

[P1186] 全球数据20 个平台字段规范 ≠ 20 个 live collector

[P1187] XHSPrimary collector 存在，但当前 SESSION_EXPIRED

[P1188] YouTube/TikTok/Reddit/LinkedIn/GitHub 等Schema/registry/planned 能力，不可声称当前 live collection

[P1189] 视频编辑Core 已有，Artifact/Evidence final binding 未完成

[P1190] SYS-06Backend exists，Flutter deliberately unavailable

[P1191] Product Account后端账户系统丰富，但 Flutter pre-beta account wall deferred

[P1192] Billing / Subscription未发现 LUMENIS 自身完整 SaaS Billing/Subscription 闭环；KOS paid 是广告投流，不是软件订阅

[P1193] Full Python Release Gate当前尚不能宣称全绿

[P1194] Hosted CI当前 HEAD 没有足够证据让我称为完整 Release GREEN

[P1196] ⸻

[P1198] 三十三、当前运行态的真实闭环数据

[P1200] 这一组数字很重要，因为它说明现在已经不是“全靠 fixture”。

[P1202] 数据当前运行 DB

[P1203] Notes220

[P1204] Canonical Data220

[P1205] Evidence193

[P1206] Subject Registry157

[P1207] Entity Relation Assertions269

[P1208] Platform Contents30

[P1209] Metric Snapshots30

[P1210] Web Runs193

[P1211] Topic Campaigns1

[P1212] Topic Records7

[P1213] Schema Version18

[P1215] 但是：

[P1217] Events = 0

[P1218] Daily Reports = 0

[P1220] 所以现在的数据闭环重点仍然很明确：

[P1222] Source / Raw / Evidence / Canonical 已经出现真实资产；Event / Decision / Reporting 等更高层业务闭环还需要继续吃这套新 Canonical truth。

[P1224] ⸻

[P1226] 三十四、我对序境当前产品结构的源码级判断

[P1228] 从这次审计结果看，序境已经不是“很多功能堆在一起”。

[P1230] 真正逐渐形成的是这条主干：

[P1232] Approved Source / Platform

[P1233]         ↓

[P1234] Acquisition Plan

[P1235]         ↓

[P1236] Collector / Browser / Import

[P1237]         ↓

[P1238] Raw Native Data

[P1239]         ↓

[P1240] Evidence V2

[P1241]         ↓

[P1242] Canonical Data

[P1243]         ↓

[P1244] Subject / BrandFocus / Entity Relation

[P1245]         ↓

[P1246] Permission + Exact Scope

[P1247]         ↓

[P1248] CTH / BMP Functions

[P1249]         ↓

[P1250] Metrics / Intelligence / AI / Skills

[P1251]         ↓

[P1252] Experience

[P1253]         ↓

[P1254] Report / Content / Artifact

[P1255]         ↓

[P1256] Evaluation

[P1257]         ↓

[P1258] Learning

[P1260] 当前最大的成熟度差异就在中间：

[P1262] Source → Evidence → Canonical

[P1264] 已经推进得非常明显。

[P1266] 而：

[P1268] Canonical → exact CTH/BMP business surface → Report/Decision

[P1270] 正在收口。

[P1272] 这也验证了你前面说的判断：现在把数据闭环钉死以后，后续十五轮里的大量工作会从“重新修底层”变成“消费既定 Truth Contract + 验收”。

[P1274] ⸻

[P1276] 一个我认为非常重要的新发现

[P1278] 这次不只是发现“还有什么没做”，而是发现了现在最值得统一的三个地方：

[P1280] 当前存在的多口径需要收敛到

[P1281] Platform Native Mapping 20 / Collector Config 14 / Registry 12 / Data Center visible 3单一 Platform Capability Authority

[P1282] CTH 已进入 exact scoped Canonical/Evidence；BMP 大量页面仍是 builder/data-source 层CTH/BMP 同一套 exact scope truth discipline

[P1283] 805 API 中 canonical owner + compatibility + historical surface 混存Canonical API owner map + compatibility retirement

[P1285] 这三个完成以后，序境的复杂度会显著下降。

[P1287] 而最核心的产品资产已经比较明确：

[P1289] Subject / BrandFocus + Evidence + Canonical + Entity Relation + Permission + Evaluation + Learning。

[P1291] Collector、AI、Agent、内容、报告、App 最终都是在消费这套基础设施。

[P1293] 这份表就是我根据当前源码与运行态整理出来的产品能力基线，不是产品规划稿。后续每日评估应该以这里的分类继续追踪，而不是重新从“有没有某个文件/页面”开始判断。
