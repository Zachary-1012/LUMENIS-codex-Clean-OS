# 序境 / LUMENIS 全平台采集能力补充研究

研究时间：2026-10-17 19:39–19:47 UTC；北京时间 2026-10-18 凌晨。状态：文档研究完成，现场覆盖与项目权益未验。仅查官方公开资料与恢复包静态文件，未登录、申请权限、调用数据 API、启动产品、安装、改产品代码/数据库/运行环境。

## 原要求核对修订：G2 不被本研究替代

原 G2 是 17 类来源 × 19 项 live 交付维度，原要求完整保留。此处 22 源 × 14 类文档合同只是补充研究，两者不是相同分母，不能互相替代或宣称 G2 完成。已追加 `G2_RECONCILIATION_APPENDIX.md` 与 `06_G2_17x19_CROSSWALK.json/.csv`，逐格保留 323 项原要求、静态代码定位、官方条件和缺失证据。原第 17 行是“当前 main 中其他真实 Adapter”，并非第 17 个固定社媒；当前 main 未核，本轮只核恢复包。

## 一、结论与本次增量

1. 已恢复并复用原官方矩阵，现转为 **22 个源身份 × 14 类合同字段**的 JSON/CSV：16 社媒、Google/GitHub 两辅助源、HTTP/RSS/Atom/Sitemap 四通道。原逐平台正文完整保留，没有重复发明结论。83 个去重官方 URL 中，18 项在本轮重新读取或尝试读取；其余明确标记为复用研究，不能说全部本轮重验。
2. 22 是恢复包静态目录，不是完整产品上限。当前 Architecture 明确六主平台只是验收基线；官方/合作 API 是同一连接器的追加 provider，不另立采集系统，也不应成为所有当前合法公开/自有会话路径的强制前置。
3. **公开可见、文档有端点、实际应用获权、成功采到、获准分析、可保存、可向客户导出分别判断。** 本轮“未实测”不否定已有独立采集回执；已有回执也不能替代所有市场/对象/用途的验证。
4. 已补市场审查表 176 行。CN/HK/US/GB/EEA/JP/KR/其他只是可调整的审查维度，不声称用户已确定这些市场，更不把 176 行算成覆盖量。每个市场的账号准入、内容来源、受众地域、语言与现场可得性保持未知，只有确有官方证据的地区规则单列。
5. 最值得先修订的是能力与结果口径：账号身份 API 不等于内容 API；评论计数不等于评论正文；图片/视频链接不等于可下载重剪；当前累计计数不等于历史时间序列；平台原生字段不等于跨平台统一语义。

## 二、文件与证据如何读

- `00_REUSED_OFFICIAL_BASELINE.md`：原 16 社媒及 6 辅助/通道的完整条件、官方链接、分页/配额/使用限制与 匿名既有采集 个案假设。
- `01_PLATFORM_CAPABILITY_MATRIX.json/.csv`：账号、帖子、评论、媒体、身份、原生指标、历史、分页、速率、准入、商业许可、导出、保留、市场规则；每格有状态和说明。
- `02_PLATFORM_MARKET_REVIEW.json/.csv`：平台×市场审查，不是实际覆盖表。
- `03_ROUTE_ELIGIBILITY.json`：易被混用的同品牌不同 API/研究/合作路线。
- `04_ACCEPTANCE_CASES.json`：后续获具体执行授权后可跑的测试设计；当前全部 NOT_RUN。
- `evidence/source_register.json`：官方 URL、时间、版本、事实定位、本轮/复用及失败状态。
- `evidence/INPUT_HASHES.json`：恢复资料的固定指纹。恢复包不是当前远端 main 的承诺。

UNKNOWN 不能转换成 false、0、无内容或无能力；DOCUMENTED_CONDITIONAL 也不能转换成 true、可商用或已验收。矩阵保留原报告正文便于追溯；精确当前合同仍以获批产品、版本和实际条款为准。

## 三、对象与字段层面的新增发现

### 1. 小红书：身份命名空间必须进入数据合同

2026-08-19 账号参考的 open_id 是本应用范围内身份，基础资料包括昵称、头像与地区。它不能证明笔记检索权限，也不能用昵称把两个平台的人合成同一个真实主体。内部候选匹配可以保留置信度与依据，不能替换身份确认。该参考并未建立 匿名既有采集 笔记或楼中楼的全量获取合同。[官方账号参考](https://openaccount.xiaohongshu.com/docs/api-reference)

### 2. TikTok：时间单位与媒体链接寿命不是同一问题

2026-08-24 Video Object 的 create_time 是 UTC 秒；Display 列表 cursor 的单位另按列表合同。封面链接 TTL 为 6 小时；正文/元数据保留规则不能拿这个 TTL 代替。likes/comments/shares/views 分开保存，embed/share link 也不等于源视频可重剪或转售。[Video Object](https://developers.tiktok.com/docs/en/tiktok-api-v2-video-object)

### 3. YouTube：来源时间、市场字段、分析许可分开

video 的 publishedAt 可能不同于上传时间；channelId 也有重新归属情形。regionRestriction 约束可见地区，文本/音频语言与创作者所在地、受众地域不能混成“市场”。视频资源统计和媒体元数据并非媒体二进制授权。[Video resource](https://developers.google.com/youtube/data/reference/rest/v3/videos)

重新确认：当前默认配额是每天 100 次 search.list、100 次 videos.insert，其余端点合计 10,000 units。具体项目额度仍未知。[Quota/Audit，2026-10-15](https://developers.google.com/youtube/data/guides/quota_and_compliance_audits)

重新确认：接受适用分析附录后，规定的统计/衍生指标可保留至 36 个月；标题、创作者名、描述与评论正文仍执行 30 天刷新/删除。不能将该例外扩为 LUMENIS 已获批，或把受众敏感属性推断作为分析成果。[分析附录，2026-09-14](https://developers.google.com/youtube/terms/derived-metrics-policy)

### 4. X：长文、回复、编辑与计数是独立维度

note_tweet、edit_history_tweet_ids、conversation_id、referenced_tweets 应作为可选源字段保存，不靠普通 text 或单一“评论数”代替。public_metrics 与 non_public/organic/promoted metrics 权限不同；个人资料 location 是自由文本，不能直接作为地理真值。[X v2 字段字典](https://docs.x.com/x-api/fundamentals/data-dictionary)

### 5. 仍未补齐的官方合同

微信公众号 subscription/service 新发布记录链接本轮依旧不可读；Facebook Pages posts 文档本轮返回 429。没有因此填写第三方 SDK 参数，或把文档访问 429 写成生产平台限额。小红书内容/评论合作、快手/B站评论正文、知乎/贴吧/视频号通用读取、各平台实际应用/账号/合同仍未取得。

## 四、同品牌多路线必须分开

| 平台 | 适用路线 | 不可偷换为 |
|---|---|---|
| TikTok | Display：获授权账号展示；Research：合资格非商业研究；Portability：合资格地区用户自身导出 | 任意第三方品牌全历史商业评论库 |
| Facebook | 有实际角色/feature 的 Pages；另有学术/非营利研究 Content Library | 普通个人内容全网读取或商业研究通行证 |
| Instagram | Instagram Login；Facebook Login；各自专业账号、scope 与 app review | 个人消费者账号全量数据，或混用两套 scope |
| X | recent 7 天；archive 对应付费/企业 entitlement | 用 recent 补全全历史，或 cookie 证明 API 权限 |
| 小红书 | 账号授权、商业合作内容、获准网页会话分别核验 | basic_info 证明笔记/评论或网页可见证明商业导出 |
| YouTube | 公共元数据；账号 OAuth；经接受的分析附录 | 公共 API key 自动取得所有衍生分析及长期保存权 |
| Reddit/LinkedIn | 实际批准产品、合同、角色、字段和用途 | OAuth 成功即可以转售原始语料或跨源长期仓储 |

研究用、非商业用、商业分析、模型推理、模型训练、公开展示、向客户导出是不同用途。不能泛化为全部禁止，也不能用其中一个许可放行其余用途。

## 五、与 ONE Collector / Browser / SourceUse 的衔接

### 已恢复的边界事实

- Architecture 当前文稿强调一个 PlatformManifest、一个 PlatformSession 真相 Owner、同一 SYSTEM Collector/Browser 和 Source→Evidence→Canonical 路径。不同提供方不能各自建立调度器、账号系统或事实库。
- `browser_extract.py` 是已获授权页面的有界确定性提取器；模块声明自己不导航、不发 HTTP、不读凭证、不做 SourceUse 准入。其静态上限为 32,768 字符、256 blocks、512 KiB 结果；这是产品局部提取预算，绝不是某平台内容上限。不能以截断结果判断源端已经读完。
- 当前计划明确独立资料、研究、编辑与成果保存无需虚构业务主体或社媒登录。Permission 与来源用途仍在服务端执行。无模型也应能完成基本工作。

以上是静态事实，未执行这些模块或证明当前部署已接线。

### 建议的提供方选择，不是新系统

| 输入条件 | 同一既有链中的方式 | 返回用户的真实结果 |
|---|---|---|
| 用户自有/已获准文件、导出 | 原 Importer → Source/Evidence；保留导出来源/时段/缺项 | 文件范围内的可编辑研究与分析；缺失平台指标保持未知 |
| 可合法读取的公开精确 URL、RSS/Atom | 原 Collector 的相应 provider；浏览器仅在需要页面交互时参与 | 实际页面/条目范围、采集时刻、截断标志；不冒充全站历史 |
| 合法且已授权的账号浏览器会话 | 原 Browser/PlatformSession，由既有 Permission 与 SourceUse 约束 | 会话实际可见对象；挑战/撤权明确阻塞本路径 |
| 已获权的官方 API | 同 PlatformManifest 的 API provider | 版本、scope、页面与额度回执；依然披露索引缺口 |
| 已采购且用途匹配的合作/供应商数据 | 同连接器的 licensed provider | 合同限定平台/字段/市场/历史，禁止将供应商宣传写成实得覆盖 |
| 路径不可用 | 保留任务/已获准材料与 checkpoint | 明确缺什么、可继续编辑/分析什么，不用伪数据补洞 |

不能在账号挑战、权限拒绝后自动换身份、代理、隐藏接口、提取 token 或绕过验证。也不能把某平台受限当作独立文件编辑、其他许可来源研究或已完成成果重开的全局阻塞。

### 最小完整性合同

采集请求固定 platform/provider/version、任务范围、账号/角色引用、查询/排序/语言/市场证据、时间区间与时区、用途版本。每页记录输入/输出游标、has_more/next、原始返回/新增/重复/过滤数、业务错误码、限额/重置、停止理由。根评论和回复各有未完成队列。

完整度至少四项：发现范围、详情展开、评论树展开、字段非空与许可范围。无法知道母体时不能报告“召回率 100%”。可以报告对明确输入清单的详情成功率、已发现回复任务完成率、去重率和字段缺失率，附分母与排除项。平台展示评论总数可能包含不可见、折叠、删除或未授范围，不可直接当真实召回分母。

历史语料与历史计数分别处理：今天读到 2024 年帖子上的累计点赞数，是今天的观测，不是 2024 年点赞数。缺少历史快照时，不倒推、插值或把模型估计写成原生值。

## 六、市场、身份与媒体使用验收

“市场”至少拆为：请求/应用准入地区、平台/产品地区、作者明确提供地区、内容事件地区、受众地区、语言、内容可见地区。每项带来源、时点、置信度和 UNKNOWN，不使用中文文本=中国、英语=美国、账号地区=受众地区等替代。

跨平台身份保持 platform+provider+namespace+source_id；昵称/头像只生成候选，不能确认真实人或品牌。认证标识的含义随平台和时间保存，不将一个蓝标推为组织授权。身份候选与合法原始观察分层；无法绑定主体不意味着删除原始已获准资料。

媒体合同至少拆 metadata_read、preview/embed、download_binary、OCR/ASR、model_inference、edit/remix、publish、export、training。每个用途独立定许可与受众；有 URL 不代表其中所有用途可用。OCR/ASR 是后续生成派生文本，不伪称源站原文；需要正文/资产权利和获准计算路径。

## 七、对 Brandwatch / 数说的实际可证明对比

Brandwatch Listen 公开说明有 X firehose、限定 Facebook/Instagram 公共账号池、需要认证的自有/目标来源；LinkedIn 为自有公司页，TikTok 自有频道及提及另有时间/刷新范围。YouTube 使用第三方提供方；Reddit 明确不保证逐帖逐评论全覆盖。不要把 Listen、Consumer Research 与加购源的能力合并，也不要忽略其新增 Bluesky 来源。[Listen 来源说明](https://social-media-management-help.brandwatch.com/en/articles/17449910-sources-for-listen-mentions)

数说聚合公开页展示关键词/账号/单帖监测、评论分析、原文排序、多模态和商业接口。但没有公开足够完整的平台×字段×市场×历史×许可表，因此实际覆盖、价格与召回未知。官网“全网”不能作为实测值，反过来也不能因缺表断言它不支持某平台。[数说聚合](https://www.datastory.com.cn/product/hermes)

公平对比需用同一品牌/别名、日期、时区、市场、语言、对象层级、账号类别和许可用途；分别报告供应商原生可得覆盖与统一输入资料包上的分析能力。供应商 API 套餐、自有来源、第三方持有数据与用户自行授权是不同成本与准入。没有真实样本、合同和导出回执，本轮不能评“序境优于它们”，也不把供应商未公开的商业合作能力填成不存在。

建议采购前要求每家提供：版本/产品名、来源名单和地区、历史与实时延迟、评论层级、删除同步、字段及受众、模型处理/训练限制、保存/导出条款、额度计费、同一金标准样本回执。本轮只准备清单，未对外询价或联系。

## 八、扩展范围，不将目录当上限

- Mastodon：官方文档可证明实例级公开时间线与 ID 游标，单页最大 40；实例可关闭匿名预览。实例已知的联邦内容不是全网全集。默认 300 次/5 分钟也需实际实例核验；公开协议不授予所有内容的商业重用。候选价值是开放社群信号，不能宣布已接入。[时间线](https://docs.joinmastodon.org/methods/timelines/)；[联邦范围](https://docs.joinmastodon.org/user/network/)；[限流](https://docs.joinmastodon.org/api/rate-limits/)
- Bluesky：Brandwatch 官方来源页已列该来源；本轮直接官方开发文档跳转为空页面，未取得可用完整 API 合同，因此保留候选，不能填造搜索/历史/速率/商业条款。
- 新闻、博客、论坛、评价站点、行业/官方报告：按任务需要纳入具体站点，不拿 HTTP/RSS 四个技术通道伪装四个完整内容市场。每个发布方仍有对象、时间、许可与覆盖合同。
- Threads、Telegram、Discord、地区性平台等可由实际用户任务触发后续范围确认。本轮未核其当前官方合同，不将它们标成已研究或已支持。

## 九、研发交接优先顺序与停止条件

P0：先展示来源/提供方/对象/市场/缺项和真实状态；分别记录许可、会话、运行、分析与导出。保持“未配置、权限不足、受限、部分、成功零条”区别。以已存在、合法且仍有效材料走完研究→可编辑成果→保存/重开，不要求所有平台先齐。

P1：对已获具体执行授权的单个平台，按多页详情、根/子评论、长文/媒体、时间边界、删除/撤权/限流和断点恢复逐项验收。适配器存在、离线测试通过、界面有按钮都不能代替真实回执。既有有效成果应复用，不因换提供方名重新采集。

P2：以真实业务缺口决定引入官方/合作 provider 或新增平台，比较许可、字段、市场、历史、延迟与成本。只在当前 Owner 内提出有界修改；本报告没有给出或代替产品修改授权。

文档研究的停止条件已经满足：当前恢复目录全部列出并可追溯，关键补充与不能证实处明确。下一阶段需要实际提供方合同/权限证据及对具体测试/修改的明确授权。本轮不会把开放问题无限轮询成“已验证”，也不会发起生产采集补齐它们。
