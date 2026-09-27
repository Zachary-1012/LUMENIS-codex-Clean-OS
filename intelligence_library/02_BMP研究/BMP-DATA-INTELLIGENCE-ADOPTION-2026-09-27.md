# BMP 数据情报与品牌决策采用建议

**研究日期：** 2026-09-27
**状态：** `RESEARCH / ADOPTION CANDIDATE`；不是生产能力、全球覆盖或 Round 验收声明
**范围：** BMP 品牌负责人如何把市场、竞品、消费者、媒体社媒、创作者、内容、传播与销售反馈转成可复核的品牌决策。
**边界：** 沿用现有 BMP、SYSTEM Collector、Shared Evidence/Canonical Data、Shared Research/Content/Evaluation/Learning 与 Permission 负责人；本文件不创建新产品、数据存储、采集器、AI、指标或 Experience 负责人。

## 1. 结论与采用原则

BMP 的核心工作应从一个可授权的 BrandFocus 出发，回答“在什么市场、对什么人、相对哪些替代选择、应做什么品牌/传播/内容决策，之后结果如何”。`GLOBAL / ALL` 仍是产品默认范围；BrandFocus 只是用户选定的工作焦点，不是采集范围、访问许可或后台任务开关。

采用证据分层、统一来源 lineage、分母明确的指标、按市场/平台/内容年龄分层的比较、明确的缺失状态、人工可复核的决策记录。平台热度、搜索指数、品牌估值、媒体提及和销售结果各自回答不同问题；它们不能互相代替，也不能单独证明因果。

优先交付物是有来源的市场与竞品脉冲、消费者需要/摩擦证据包、创作者适配 shortlist、品牌/内容 Brief、campaign 与测量计划、结果/差异回顾和有反证的版本化学习资产。每份交付都应包含可用证据、范围、时间窗口、未知项、建议理由、责任人和下一步。

## 2. 过往规划与当前所有者映射

| 现有规划/契约 | 保留并采用 | 需要收敛或重新核实 | 现有负责人及 Round |
|---|---|---|---|
| `intelligence_library/02_BMP研究/DATA_AND_CONTENT/FINAL_DATA_PIPELINE_KOS_KOC_UGC_IMPLEMENTATION_DIRECTIVE.md` | Raw → validated/normalized → deterministic function → canonical table → quality gate → ViewModel/UI；稳定 ID 到详情和 Evidence；KOS/KOC/UGC、事件、话题、风险与内容模板字段；公式/版本、空值、可复现、AI/人工更正区分。 | 这是 2026-09-04 的历史执行指令，不是当前实现证明。不要重建它列出的表或指标；确认每项归属现有 canonical owner。单个分数、达人级别、情感标签须带方法、版本、置信和证据，不能从一个任意指标直接推断。 | BMP 组合/市场/竞品/传播/创作者由现有 BMP caller 消费；Evidence、DB、Collector、AI、Permission、Shared 内容/报告/评估/学习保持原 owner。ROUND 12–13，15。 |
| `品牌营销知识/brand-marketing-knowledge-02…25` 与 `_index.md` | 将真实消费者摩擦、社群/创作者共创、品牌与代理商/平台三方约束、传播时序、内容事实核验、复盘学习作为研究标签和 Brief 问题。15 号知识文中的 Le Labo 可作为待核实的奢香类问题线索。 | 索引写明“条目存在不代表生产实现或验收”，其“文件”区为空。知识文件内无一手出处、量化主张、市场/样本范围或授权说明的案例/百分比均属 `UNVERIFIED`，不得成为 KPI、事实或自动训练标签。尤其将传闻案例、搜索到的单例与全球规律分开。 | Shared Research/Evidence 与版本化 Learning Assets；Round 07、12–13、15。 |
| `brand_knowledge_base.py` 与 `brand_propagation.py` | 当前代码包含营销知识检索分类、传播实体/事件、平台、情绪、互动和摘要等既有概念。 | 文件头仍带历史 Z-Brand/ZBMP 归属；知识记录有 title/content/source/url/tags/hash/relevance/timestamps，但没有可见的 source edition、许可证/访问状态、独立发布/捕获/事件/派生时间、主张级 Evidence、版本/反证/审核状态契约。代码存在不等于运营知识库、有效数据或可供 AI 可信消费。不得照此创建第二个知识或传播库。 | Source Owner Index 将 CTH/BMP 视为业务 caller；当前领域模型和 Shared Evidence/DB/Research owner 决定是否复用。ROUND 12–13。 |
| `ad_intelligence/` 与 `api_dual_domain.py` | 已有广告 campaign/creative/metric 容器、部分 Meta Ads API 只读骨架、平台 ROI/漏斗/素材分析概念；BMP API 有显式验证的 `brand_key`、品牌聚合、情绪分布等局部消费字段。 | 广告骨架字段有默认 0；分析器取不到 spend/revenue 时仍可能算零值；跨平台币种函数标为占位；平台接入资质/授权和实际运行未由本次只读研究证明。BMP 屏幕契约要求来源、BrandFocus/global scope、lineage、`read_allowed`，不要把未绑定响应、fixture 或目录数据视为实采。 | 广告平台接口只在品牌拥有/获授权账户且相应连接获准后使用；SYSTEM Permission/API、Collector 与 Shared Evidence/DB 是边界。ROUND 06（采集/授权）、12–13、15。 |
| BMP-02…09 当前屏幕规格及 `LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md` | BMP-02 明确 BrandFocus 与竞品谱系；其 contract 将当前组合数据绑定标成 `BLOCKED`，不能用 curated directory 代替 lineage。品牌负责人任务为真实可比的消费者/市场/竞品/创作者证据 → 有界决策和理由 → Brief/审批 → 真实结果/反馈。 | Screen specification 是设计/绑定验收输入，不证明页面已运行。任何品牌工作需保留入口、真实输入、可见结果、Evidence、Permission、失败恢复、返回路径和用户验收。 | BMP/Experience/API owner；ROUND 08–09 基础，12–13 业务，15 release 复验。 |

## 3. 品牌负责人的真实任务与交付物

1. **理解市场位置：** 在明确国家/区域、品类、时间和渠道的范围内，判断类别需求、价格/产品/分销变化和品牌/竞品的位置；交付 market pulse 与来源/覆盖说明。
2. **找出消费者问题：** 对齐调查、服务反馈、评论和搜索需求中的需要、使用场景、期望、障碍、误解及反复出现的问题；交付主题证据包，指出哪些是定量发现、定性线索和待验证假设。
3. **做品牌与竞品选择：** 比较目标受众、价值主张、创新、价格、分销、品牌心智和传播方式；交付有反证的品牌/竞品对照和明确的选择标准。
4. **选渠道/创作者/内容：** 根据受众重叠、专业性、品牌安全、受众地域、内容可信度、付费披露和历史结果，提出可测试的 shortlist；交付 Brief、内容/渠道矩阵和测量计划。粉丝数或点赞数本身不构成适配。
5. **读传播与风险：** 识别品牌、产品、品类或事件相关的传播变化及消费者问题，检查速度、负面集中、来源可靠性和可行动性；交付需人工处置的事件/风险记录，不让情绪模型直接代表公众意见。
6. **解释结果并学习：** 将 campaign 目标、投入、创意版本、触点、销售/转化或品牌调查结果和比较基线对齐；交付差异说明、因果强度/局限、批准的下一步和经评估的学习资产。

所有交付必须让负责人能回到原始来源与版本，检查真实值、定义、时间、范围、方法、缺口和审批历史。未经授权的销售、身份或平台数据不得由公开社交信号推算。

## 4. 字段优先级与数据语义

`P0` 是任何可比较结果的共同底座；`P1` 支撑日常决策；`P2` 在来源、许可和真实工作需要成立后扩展。以下是现有 owner 的字段建议，不授权添加 schema 或外部连接。

| 优先级 / 信号族 | 建议保留的高价值字段 | 决策用途与关键质量要求 |
|---|---|---|
| **P0 来源与观测** | `source_id`, `provider/platform`, `origin_type`, `source_url/external_id`, `source_edition/reference_window`, `brand_focus_id/canonical_scope`, `published_at`, `occurred_at`, `captured_at`, `derived_at`, `observed_at`, `collector_run_id`, `content_hash`, `raw_snapshot_ref`, `access_status`, `policy_status`, `license_status`, `truth_state`, `method/version`, `Evidence ref`, `locale/timezone`, `unit/currency/denominator`, `quality/confidence`, `human_correction/reason` | 将来源事实、观察快照和派生结论分开；保留历史快照；去重按来源身份/平台规则，不因文字相似合并不同来源；记录权限和使用目的。时间字段含义不能折叠。 |
| **P0 品牌实体/关系** | canonical brand ID、正式名/别名/本地文字、母公司/品牌组合/子品牌、品类/行业 taxonomy 版本、总部与经营区域、国家/语言/市场、关系方向/依据/有效期、竞争集合版本、身份解析置信和冲突状态、基线 inclusion-rule 版本 | 支撑全球实体去重与 BrandFocus。关系须有来源和生效时间；不能把作者、域名、提及或 CTH Subject 自动升格为品牌。 |
| **P1 市场与竞品** | category/market size 与定义、销量/价值/增速、份额与分母、价格带/促销/创新、分销/可售性、区域、渠道、竞品关系与产品、财报期间与币种、预测/实绩区分、来源覆盖/缺口 | 支撑位置、机会和压力分析。财报净销售不能直接代表品类份额；排行/估值是特定方法下的 proxy，不是市场需求事实。 |
| **P1 消费者与需求** | 消费场景/任务、需要/期待/障碍、使用和复购阶段、品牌关联、主题/属性/情感方面、购买考虑/偏好/意向、调查问题版本、样本数/招募/市场/权重/误差说明、公开内容聚合范围、匿名化方式 | 将公开文本作为可见发声线索，将调查作为其抽样目标总体下的态度证据，将零售反馈作为具备授权的行为证据；不能将三者混为“消费者整体”。个人身份最小化。 |
| **P1 媒体/社媒/传播** | platform/account 类型与验证状态、organic/paid/earned/owned、内容 ID/URL、媒体/创作者身份、格式、主题/实体命中依据、披露标签、发布时间、内容年龄、国家/语言、展示/观看/完播/互动/分享/评论/收藏/点击/引流、source-defined denominator、评论主题与样本、事件/传播阶段、付费投放关联、抓取/平台覆盖缺口、每次快照的 `observed_at` | 互动指标必须保留来源定义和窗口；公开可见内容与品牌私有 analytics 分开。跨平台归一化只比较定义/受众/年龄可比的数据。榜单、曝光或高热度不等于购买、品牌提升或因果。 |
| **P1 创作者/KOS/KOC/UGC** | creator canonical ID/别名、国家/语言、领域/专业与证据、受众地域/组成/重叠（授权聚合数据）、历史主题/内容质量、真实样本链接、广告披露/品牌合作、品牌安全/风险、成本/权益/授权期限与地域、互动分子分母与观察时间、转化/品牌调查（授权数据）、方法/评估者/置信度 | 适配得分拆开领域可信度、受众吻合、内容匹配、风险、成本和授权条件，解释权重和反证。不得仅靠粉丝数/单条爆款分级或推荐。KOS/KOC/UGC 需定义与版本。 |
| **P1 Campaign/内容** | objective 与目标群体、brief 版本、campaign/creative/content IDs、创意变体/素材权利、平台/位置/格式、预算/币种、计划与实际起止时间、曝光与频次、UTM/促销码/落地页、试验/holdout、审批/披露、内容版本、目标 KPI 的公式/窗口/分母、品牌调查与样本、实际收入/成本/退货/毛利（授权）、归因模型/lookback | 连接创意与真实目标。把计划/预测与已发生结果分开；无销售/投放权限时明确 unavailable，不从公开点赞推估 ROAS。 |
| **P2 风险/时序/深度** | topic/event cluster 版本、首次发现/峰值/消退时刻、传播速度和参与者构成、风险触发规则版本、severity、置信/反证/人工 disposition、响应 action/permission、service issue taxonomy、地区/渠道缺测 | 仅用实际观测快照算速度。误报/拒绝/陈旧比例也进入质量评估；风险标签不能自动触发外部行动。 |

每个数值都应带 truth state 与来源时间。严格区分 `0`、`NULL`、`UNKNOWN`、`NOT_AVAILABLE`、`NOT_COLLECTED`、`STALE`、`OFFLINE`、`ERROR`、`BLOCKED` 和 `PENDING/SCHEDULED`。聚合值应给分子、分母、单位、范围、窗口、被排除行数和 quality gate。`share of voice` 要披露声音份额按提及数、可见媒体量、互动或其他什么定义；`sentiment` 是方法标注而非消费者总体态度。

## 5. Nike、Le Labo 与全球基线的实际使用示例

这些示例只说明如何把已公开事实挂到研究问题上；不执行采集、不访问个人账户，也不声称任何媒介/社媒行动造成了销售变化。

| 用例 | 已有可引用事实 | BMP 下一步应补的可比 Evidence | 允许形成的结论 |
|---|---|---|---|
| **Nike / 全球运动服饰** | NIKE FY2026 业绩公告（2026-06-30）报告全年收入 $46.4B、按报告口径同比持平；Q4 批发收入 +4%、Direct -7%（报告币值口径），Direct 数字业务 -12%、自营门店 -7%。这些是公司财报 period facts，不是媒体 attribution。Kantar BrandZ 2025 Top 100 的 Nike #51 可作为一个按其方法纳入的基线 entry；Kantar 2026 页面公布全榜规模/样本方法，不应据当前摘录推断 Nike 的 2026 排名。 | 各区域/运动品类需求与份额；跑步/训练/篮球等使用任务；产品创新、价格、存货/促销、经销与自营渠道；创作者、赛事、earned/owned/paid 内容；按地区/产品/渠道的 authorized sell-through、退货与品牌/购买 lift；趋势和销售的同窗/滞后关系。 | 可说财报显示的渠道/时间段变化值得形成分区域、品类、数字/门店、批发对照研究问题。不能只凭 Q4 推断成因、消费者情绪、某社媒 campaign 成败或品牌声量。 |
| **Le Labo / 全球高端香氛** | ELC FY2026 results（2026-08-19）称 Fragrance 净销售 +10%，Luxury Brands 双位数增长由 Le Labo、TOM FORD、KILIAN PARIS 带动；Le Labo 增长主要与 Classic Collection、Violette 30 与 perfuming hand creams 等创新、消费者覆盖扩大和已有分销增长有关。公司报告 FY2026 全球 Fragrance 新增 33 家自营门店（品牌分配未在该句单列）。这是公司层披露，不应外推为每个市场/门店表现。另有 [Le Labo Violette 30 官方产品页](https://www.lelabofragrances.com/classic-collection/violette-30)，标题显式包含“Le Labo Fragrances”，页面提供品牌自述产品内容；页面没有可确认的发布日期。 | 国家/城市、百货/自营/旅行零售/电商分销；香型/经典系列/新品可售性、价格和礼赠/自我购买场景；经授权的消费者访谈/调查与门店反馈；香评媒体、调香内容、创作者专业度/品牌适配、二手转售/真伪风险；门店开设、库存、营销和地区收入的共同时间序列。PublicHttpAdapter 的 2026-09-27 修复在实时读取中将 Le Labo 提及保留在 16,000 字边界内；该稿日期信号冲突，且尚未以 Le Labo 精确范围写入 Raw/Evidence/Canonical，网页探针不能当成产品数据。产品页可作为公开品牌内容线索，不能替代消费者、媒体或销售数据。 | 可把公司披露的增长驱动当作检验假设：经典系列/新品/覆盖扩展分别在何市场有 Evidence？“分销扩张”是可验证的触点变化，并不单独证明社交传播、创作者或顾客忠诚造成增长。产品页的 `published_at` 应为 `UNKNOWN`，不得用财报发布日期或 FY26 财务周期冒充产品页发布时间/产品发布日期。 |
| **全球品牌基线 / 一版候选 inclusion rule** | Kantar BrandZ 2026 页面称 Top 100 由 4.6M 消费者观点、超过 22,000 个品牌数据形成，跨 54 个市场；其品牌估值将财务价值与消费者品牌贡献结合。Interbrand 2025 Best Global Brands 的资格含跨区收入、区域存在、公开财务、长期正经济利润、全球知名度和品牌强度等门槛。两者是不同方法与商业产品。 | 在**一个经 Product Owner 批准并版本化**的规则中，以多来源/多层次名单交叉发现候选，覆盖声明的地区、品类和品牌类型；再逐实体通过 canonical identity/alias/owner/region/industry、关系、纳入依据、来源 edition、来源/Evidence、授权/许可、更新时间与成熟度审核。小众/私有品牌、地区品牌和来源限制记录在 coverage gaps，而不是消失。Nike 与 Le Labo 分别用来验证全球体育品牌和奢香品牌样例；不得由它们代表总体。 | “GLOBAL / ALL”只能报告已声明 population 内可证明的覆盖率和未覆盖差距，不声称收尽世界品牌。排行榜用于候选发现/研究对照，不能单独定义全集；4 个样例绝不是 global sample 或 global coverage。 |

### 全球基线的必要分母与抽样

基线候选规则需预先说明涵盖地域、行业、品牌/子品牌类型、来源 edition、纳入与排除、别名/母子品牌去重、关系证据、冲突处理与复审周期；规则审批后不可回写成一张随意增长的名单。每次成熟度报告给出 population/version、已识别实体/合格实体、可用来源/授权实体、Fresh/Complete/Evidence-backed 实体、拒绝/冲突/未采集实体、地区与行业分层，以及失败样本。

按 canonical registry 中可用总体做轮换/分层随机验收：包括非参考商业品牌、品牌和跨地区实体；记录 seed、分层和每个样本的真值状态。成熟样本的空白/全零/占位/虚构值是 defect；总体尚不存在时报告样本数 0 和 owner gap。广州太古汇是 CTH 受控深度参考主体，不是 BMP 默认 BrandFocus 或 Global Brand Coverage 替代物。Global Commercial Coverage、Global Brand Coverage、Guangzhou Taikoo Hui Reference Coverage 是一个 internal edition 的三个独立诊断维度；只有三者均 YES 且两套 baseline 与用户添加路径完成，才可报告 `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=YES`。当前治理文档记录三者尚未通过。

## 6. 接入链、授权、新鲜度与验收

```text
Authorized Source / Real Input
→ SYSTEM Collector or existing authorized import adapter
→ immutable Source / Capture and Evidence with provenance
→ existing canonical brand/content/event/metric owner
→ deterministic function with formula/version and quality gate
→ Truth Table / scoped ViewModel
→ BMP decision, Brief, campaign or report
→ authorized Permission / approval for consequential action
→ actual outcome + evaluation + versioned learning asset
→ shadow/targeted validation → approval/promotion → observability/rollback
```

- **Source suitability gate:** capture provider, exact source URI/ID, source type, retrieval/capture method, jurisdiction/market, published/occurred/captured/observed times, source edition, original content hash/snapshot reference, paid/organic/disclosure status, identity matching evidence, allowed purpose, terms/license/privacy status and derivation method. Keep original source Evidence immutable; analysis and human correction are separate derived records.
- **Permission gate:** default collection remains manual and bounded. Only use public HTTP/RSS/Atom/Sitemap/browser or platform API through existing SYSTEM owner and the source's documented scope. A public page is not an API license; visible content is not permission to bulk capture, retain, profile individuals, republish, or train on it. BrandFocus never authorizes a source. TikTok Research API is for qualifying non-profit researchers with project approval, so it is `REJECT` for commercial LUMENIS ingestion absent a new explicit legal/commercial approval; use an authorized business product/account only when owner credentials, permitted endpoints, platform terms and Permission pass. Never touch the protected Mainland XHS identity; this study performed no XHS login/session/browser activity.
- **Freshness gate:** preserve `published_at`, `occurred_at`, `captured_at`, `observed_at`, `derived_at`; metric snapshots append by observation time. Display last attempt, source-specific refresh interval, age, status and retry/unavailable reason. Campaign results require their planned maturity window; future T+ windows remain `PENDING/SCHEDULED`. Search-interest, media and social data use separate freshness windows, not one global “current” flag.
- **Metric/Truth Table gate:** calculations are named deterministic functions with input field/unit/window/denominator, filter rules, timezone/currency handling, formula version and reproducible Evidence IDs. Avoid joining incompatible exposure/engagement definitions. Any use of survey comparisons states target population, source sample and method. Causal claims require appropriate test/control or an explicitly limited observational interpretation.
- **User work acceptance:** one real brand lead starts from permitted `GLOBAL / ALL` or a BrandFocus, inspects authorized comparable brand/market/consumer/competitor/creator Evidence, chooses one bounded option, produces a reviewable Brief and measurement plan, passes required approval, receives a real result/explicit blocked or unavailable state, then reviews the outcome and returns to context. Validate recovery, source drill-down and cross-surface return path. Sample fixtures, report files, HTTP 200, model prose and four example brands cannot pass.

## 7. Source suitability and adoption decisions

Research checked on **2026-09-27**. Dates below are publication/edition dates shown by the source; where a source page has no explicit updated date, record “page accessed 2026-09-27; source date not stated” in any later asset. URLs point to publisher originals. No report PDF or platform payload was copied into this file.

| Source and source date | Best use / available dimensions | Quality, licensing and limits | Decision |
|---|---|---|---|
| [NIKE FY2026 fourth-quarter and full-year results](https://about.nike.com/en/newsroom/releases/nike-inc-reports-fiscal-2026-fourth-quarter-and-full-year-results), 2026-06-30 | Audited/public company reporting for brand revenue, geography, Direct/wholesale, digital/store direction and period. | High authority for company-reported financial statements; aggregated and period-delayed. It does not contain social listening, individual consumer attitudes, platform attribution or creator performance. Public page is not permission to collect behind login or claim causality. | **ADOPT** as market/company signal when mapped with period, currency, segment and company-source Evidence. |
| [The Estée Lauder Companies FY2026 results](https://investors.elcompanies.com/en/news-and-media/newsroom/press-releases/2026/08-19-2026-110037466), 2026-08-19 | Parent-company reported Le Labo/fragrance growth drivers, product launches, region-wide growth context and distribution activity. | High authority for ELC's company statements; some outputs aggregate multiple brands/geographies. Does not provide itemized Le Labo regional social, customer or store data. The 2026-09-27 adapter change retains up to 16,000 body characters after excluding page chrome; a live read included a Le Labo mention at offset 10,651. Publication-date signals conflict, and no Le Labo-scoped Raw/Evidence/Canonical import has occurred, so this probe is not product data. External research citation is available, but quote/summarize narrowly and review corporate content terms before commercial reuse or bulk retention. | **ADOPT** as dated primary-company research citation. **DEFER** any claim of Le Labo product Evidence until the returned passage is persisted with exact BrandFocus, provenance and honest date state. |
| [Le Labo Violette 30 official product page](https://www.lelabofragrances.com/classic-collection/violette-30), page accessed 2026-09-27; publication date not stated | Brand-owned product description and current product/collection language; page title explicitly identifies “Le Labo Fragrances”. | Primary for the brand's own public product presentation, not independent consumer/media intelligence. No visible publication date; the FY2026 results mention Violette 30 as a fiscal-2026 launch, which does not establish this page's publish date. Local adapter truncation may omit visible text; verify returned title/description/body and preserve retrieval time. Brand-site terms, privacy/cookie settings and commercial derived-use rights still require review. | **ADAPT** as a current brand-content/source discovery signal only; use `published_at=UNKNOWN` unless the page explicitly provides it. |
| [Kantar BrandZ Most Valuable Global Brands 2026](https://www.kantar.com/Campaigns/BrandZ/Global), 2026 edition; page accessed 2026-09-27 | Brand valuation/consumer equity signal; published page reports 4.6M respondents, 22K+ brands and 54 markets, and describes combination of financial and brand contribution measures. | Specialist panel/valuation source with methodological/product IP; sample and construct are specific, and published Top 100 is not the whole universe. Full report/data likely controlled/commercial; verify applicable license before storage, excerpt reuse or redistribution. | **ADAPT** for one candidate discovery/benchmark lens and methodology provenance; cannot be sole global baseline. |
| [Interbrand Best Global Brands 2025](https://www.interbrand.com/best-global-brands/), 2025 edition; page accessed 2026-09-27 | Cross-region revenue, presence, public financial availability, long-term profit, awareness and brand strength qualification perspective. | Published proprietary ranking and separate valuation model; exclusions follow its eligibility rules. Limited to the described ranking/available publication. Check license before bulk reuse. | **ADAPT** as a distinct candidate/eligibility lens; don't merge its scores into Kantar's or infer full coverage. |
| [Google Trends data FAQ](https://support.google.com/trends/answer/4365533?hl=en), current help page accessed 2026-09-27 | Relative search-interest over query time/geography; sampling, normalization, noise, low volume “0”, and non-poll limitations are described by Google. | Valuable for demand/interest direction, not absolute demand or individual behavior; query/topic choice, locale, period and sampling affect comparability. Preserve query, geography, window, export/capture and retrieval date; follow Google terms. | **ADOPT** as one corroborating signal with exact query/topic and scale warning; combine with sales, survey and other sources. |
| [TikTok Next 2026](https://newsroom.tiktok.com/introducing-tiktok-next-2026-our-trend-forecast-for-marketers-for-the-year-ahead?lang=en), 2026-01-14; [Research API Codebook](https://developers.tiktok.com/docs/en/research-api-codebook) and [Research API FAQ](https://developers.tiktok.com/docs/en/research-api-faq), pages accessed 2026-09-27 | Publisher's 2026 platform trend hypotheses about discovery, communities, creator trust, emotional value; codebook/FAQ define Research Tools public-video scope and permission/update limitations. | Trend report is platform-authored marketing research, with platform/product point of view; forecast is hypothesis, not external validation. Research Tools require eligibility, project application and approval and are for qualifying non-profit researchers; developer account alone grants no access. Video-query metrics may use archived data (new videos up to 48h; view/follower stats up to 10 days). | **ADAPT** report themes to research questions only. **REJECT** Research API as a commercial collection path without separate explicit authorization; never convert report percentages into universal priors. |
| [ICC/ESOMAR International Code, 2025 revision](https://standards.esomar.org/assets/documents/icc-esomar-code-2025.pdf), 2025 edition; accessed 2026-09-27 | Research accountability, responsible data collection, privacy, transparency, intellectual property and human oversight principles for analytics/AI. | Professional code; applicable law/platform contracts still govern. The code does not itself license a dataset or resolve jurisdiction-specific compliance. | **ADOPT** as a quality and governance lens; map each collection/reuse to actual legal/Permission owner. |
| Existing BMP research knowledge files dated 2026-09-03 | Historical hypotheses, templates and category ideas. | Many claims lack direct source URL, edition, sample definition and permission metadata. Search result or AI-generated assertion is not proof; no external rights were verified. | **DEFER** any quantified claim or case until source verification; **REJECT** unsupported figures and automatic promotion. |

## 8. Versioned learning assets and promotion path

Research and model output may propose a `PatternCandidate`; it cannot change Evidence, Canonical Truth, Permission, approvals or external effects. Each learning asset should carry:

`asset_id`, `version`, `status` (`DRAFT` / `EXPERIMENT` / `SUPPORTED` / `ADOPT` / `REJECT` / `INSUFFICIENT_EVIDENCE` / `DEPRECATED`), owner, task/category/region/channel applicability, inclusion/exclusion rules, source and Evidence IDs, source editions, first/last observed windows, sample/cohort definition, metric/formula version, positive and counter-evidence, confidence/uncertainty, human review and rationale, test/holdout results, permission/license boundary, promotion approver, effective date, observability, rollback target and deprecation reason.

Promote only through the existing Shared Evaluation/Learning owner after out-of-sample or targeted validation on authorized real inputs, failure and subgroup review, brand-lead approval where the claim affects a recommendation, and rollback/expiry rules. Re-test a transfer to another brand, region, platform, category, creator tier or campaign type; a successful Nike observation is not a Le Labo rule. Keep forecast, association and causal finding as separate claim types. Learning may recommend a promotion but cannot approve its own Permission or external action.

## 9. 15-round ownership and open gaps

| Round | BMP intelligence contribution / exit evidence |
|---|---|
| 03–05 | Shared DB/identity/Permission/runtime prerequisites; protect scope, actor authorization and runtime independence. This research changes none. |
| 06 | Existing SYSTEM Collector/public source and platform adapter authorization, provenance, failure states, manual default, capture/freshness and canonicalization. TikTok Research API remains outside commercial path without explicit approval. |
| 07 | Shared Research/AI/Evaluation/Learning consumers; typed evidence-linked claims, confidence, counter-evidence, no AI truth, source scope and versioned candidates. |
| 08–09 | Experience binding for actual user entry, `GLOBAL / ALL` → BrandFocus → Return, empty/NOT_COLLECTED/stale/blocked/unavailable states, evidence drill-down and actual surface workflow. BMP-02 current spec says `BLOCKED` for verified portfolio binding. |
| **12** | Global BMP entity/relationship/market/competitor/creator maturity; approved inclusion rule and registry-backed brand baseline; brand lead makes comparable market/portfolio decision from real permitted sources. |
| **13** | Authorized content/channel/creator/propagation/campaign/outcome/evaluation/learning; actual Brief/approval/result/feedback loop and metrics with denominators. |
| **15** | Exact release-SHA revalidation, random non-reference brand/region samples, global baseline completeness, permissions, all three universe maturity dimensions and real user E2E/commercial gates. It closes acceptance; it does not implement missing Round 12/13 capability. |

**Current evidence from this bounded study:** source router `bmp_job` returned `ROUTED_NOT_VERIFIED`; its owner roots are `api_dual_domain.py`, `subject_context.py`, `subject_registry.py`, `brand_knowledge_base.py`, `brand_propagation.py`, `ad_intelligence/` and the Flutter feature tree. The BMP-02 screen contract in the checked local tree states `BLOCKED` because its current builder lacks a verified BrandFocus/global lineage binding. Source files expose partial field shapes and adapters, but this task did not run application, query product DB, call platform API, inspect authenticated accounts, acquire data, run user E2E or establish runtime freshness. Current governance says `Global Brand Coverage = NO / NOT YET VERIFIED`; none of these research findings changes it.

**Recommended first executable follow-up for Sol/Round owner:** after resolving current mainline and protected work, issue one bounded ROUND 12/13 Task Card to trace existing brand registry/market and creator/content owners against the field priorities above; accept only source-linked gaps and a real BrandFocus user job with a measured output. Build no baseline by copying a ranking. Use the existing canonical registry and Evidence owners and keep any source contract or new collection under the rightful owner.

## 10. Research sources

All accessed 2026-09-27; publication dates are recorded in §7. Additional primary references:

- [YouTube Analytics API metrics](https://developers.google.com/youtube/analytics/metrics) — platform-owned metric definitions (views, engaged views, watch time, shares, subscribers); use only for authorized channel/report access, and keep YouTube definitions separate from other platforms.
- [Amazon Ads Brand Lift methodology](https://advertising.amazon.com/help/G7SUSMZ2GKJP42QS) — updated 2025-05-02; describes exposed/control survey groups and sampling. Measurement design reference only, not access to Nike or Le Labo retail/customer data.
- [Amazon Ads brand measurement overview](https://advertising.amazon.com/library/guides/brand-health-tracking) — platform-defined sales, new-to-brand, attribution, brand-lift and opt-in panel products; account, market and product availability vary. Not cross-platform ground truth.
- [Global BrandZ 2025 ranking graphic](https://www.kantar.com/campaigns/brandz/-/media/DF40203C054F4A8F8C34221EFC6C7F21.ashx) — Nike appears at #51 in that 2025 ranking edition; an edition-specific rank is not present-day coverage.

**External research method note:** the workstation `firecrawl-search` skill was inspected, but the Firecrawl CLI was not installed/callable. Official publisher pages were searched and opened through the available web research tool instead. Search snippets were not treated as product evidence; the URLs above are the primary pages selected for this adoption study.
