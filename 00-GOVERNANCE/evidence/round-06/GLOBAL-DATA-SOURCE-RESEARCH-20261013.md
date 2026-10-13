# LUMENIS-全球数据源与采集目标完整研究总表-20261013

**发布人**：Zachary Zhang｜Product Owner
**研究负责人**：Brio（Muse）｜全球数据源研究负责人
**研究日期**：2026-10-13
**版本**：v2（返工修订版）  
**当前版本**：v3.1（阿康 2026-10-13 修订，本文件为唯一现行版；v2/v3 原稿仅作历史）
**交付对象**：Codex（产品研发与工程实现）、阿康（GrokBot，产品研发与工程接续）
**任务性质**：一次性全球数据资源调查、统计与采集目标供给

> **v2 修订说明**（PO 2026-10-13 批评后返工）：
> 1. 名单从"示例"升级为**完整可用名单**（12 平台 × 品牌官方/媒体/KOL/热榜/路径；七商场进驻品牌清单）
> 2. 新增**名单关系图谱**（品牌→商场→竞品→关键词→媒体，五波扩展顺序）
> 3. 新增**零授权采集路径**：每条记录给出"现在、零授权、就能拿数据"的具体路径（PO 目前零授权，需完整产品拉投资）
> 4. 新增**自立度**分级：高自立路径（公开页/RSS/自主解析）优先，授权型 API/第三方聚合只作补充
> 5. 新增**创意/剪辑/播客**精准概念（25 个教材概念，FCP/DaVinci 出处页码 + SH-01/BMP-08 映射）
> 6. v1 存档：`LUMENIS-全球数据源与采集目标完整研究总表-20261013-v1.md`

---

## 1. 执行摘要及真实核查范围

### 1.1 一句话结论

本轮共调查 **227 个数据源**、整理 **244 个真实采集目标**，覆盖全球七大区域、8 大数据类别。其中 **150 条（66%）已核实可获取**（109 条公开可读 + 41 条授权可获取），46 条有条件获取，17 条受限，10 条未核实，4 条已停用。产品合同隐含的 11 条数据需求中 4 条已覆盖、7 条部分覆盖、0 条完全缺失。

**v2 核心变化**：PO 目前零平台官方授权。本报告每条记录均给出**零授权采集路径**（具体 URL 模式、端点、字段、频率），并按**自立度**排序——高自立路径（公开页/RSS/开放文件/自主解析，产品自己能跑）优先，低自立（官方 API/第三方聚合）注明依赖风险。**零授权、产品自立的完整数据底座是可行的**：YouTube RSS + 微博/抖音/B站热榜 + TikTok Creative Center + Meta Ad Library + 四商场官网解析器 + 商标五库 + GDELT 文件流 + OSM 自建库 + WDI/WEO 整库文件 + 六家舆情站公开页 + 播客 RSS 直采。**更正（阿康 2026-10-13）**：上述路径均不需要平台官方授权或付费 API，但并非都"不依赖外部"——TikTok Creative Center、Meta Ad Library、微博/抖音/B站热榜本身是第三方平台的公开页面，页面结构、访问策略和可用性由平台控制，可能改版或下线（低自立/中自立）；gsxt.gov.cn 等官方查询需过验证码，产品不得绕过验证码，只能走人工辅助或放弃自动化；GDELT/OSM/WDI/WEO 依赖外部机构持续发布文件。真正完全自立的部分是：下载后的本地副本、自主解析器与本地转写/处理能力。

**采集器现状（阿康 2026-10-13 补）**：仓库 `lumenis/system/collector/adapters/` 在 PO 本机工作区为 34 个文件、GitHub main@8ec0bf3 为 35 个 .py（不含 `__init__.py`），含基础设施文件（base/config/registry/routing 等）；第 14 节同口径。旧稿"22 个适配器"作废。

### 1.2 自立度分级（v2 新增）

| 自立度 | 定义 | 示例 |
|--------|------|------|
| **高** | 公开页/RSS/开放文件/自主解析；产品自己能跑，不依赖外界 | YouTube 频道 RSS、微博热搜榜、GDELT 文件流、OSM planet |
| **低** | 官方 API/第三方聚合；政策可变、服务可停，注明依赖风险 | X API（$0.005/帖子）、WIPO API、tophub 聚合 |

产品哲学：序境具备独立的数据获取与处理能力（公开页/RSS/自主解析），不把第三方 API 授权或聚合服务存续当作唯一能力基础；授权型路径可作补充。

### 1.3 真实核查范围

- **时间**：2026-10-13 单日集中调查
- **方法**：11 路并行子研究（A1/A2/A3/A4/B/C/D/E/F/G/H），每类独立核验官方文档、开发者页面与真实公开入口
- **证据标准**：URL 必须可核验；API/费用/数据规模不得编造；未核实的一律标 NOT VERIFIED
- **分类文件**：11 个明细文件共 476KB，存放于 研究方原始工作区（A1/A2/A3/A4/B/C/D/E/F/G/H.md；C 类修订版见 `GLOBAL-DATA-SOURCE-RESEARCH-20261013-C-RETAIL.md`，其余未入库，仓库内无法复核其逐条分类——除 C 类外，汇总数字与分类为研究方自报，标记 NOT VERIFIED），每文件含统一字段大表 + 采集目标清单 + 本类统计
- **本文件性质**：16 节主表为编译合成，明细证据见分类文件；统计数字全部从逐条记录计算，无估算

### 1.4 关键发现速览

| 发现 | 类别 |
|------|------|
| 大陆平台无全域内容搜索 API，跨品牌舆情只能走公开页或第三方聚合 | A1 |
| X API 2026-02 起按量计费（约 $0.005/帖子）；Bluesky 是零成本基线，建议首个 PoC | A2/A3 |
| Meta Ad Library + TikTok Creative Center 是唯二免登录广告证据源 | A3 |
| GDPR 是欧洲生死线；俄语区是最大结构性缺口 | A4 |
| 商场官网是金矿（香港 ifc 商户 PDF 为金标准）；客流数据是最大缺口 | C |
| GDELT 2.0 + Google News RSS 是免费舆情主源 | D |
| YouTube Data API v3 是官方创作者数据接口，但每次请求需 API key 或 OAuth（需 Google Cloud 项目），在零授权前提下为 CONDITIONAL；零凭据替代为频道 RSS（YT-01）（阿康 2026-10-13 更正） | E |
| UN Comtrade 是唯一需采购决策源（约 $2,000/年） | F |
| 国家统计局区划代码 2024-10 起停更（中国地址标准化最大缺口） | G |

---

## 2. 序境当前产品实际数据需求映射

> **本节全部引自 GitHub main@3b6adcb 的现行治理文档原文，不做转述改写。**
> 依据：`00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`（2026-10-11 PO 校正版）、
> `AGENTS.md`（2026-10-11 PO 直接校正）、`contracts/experience/source-target-contract-v1.json`（v1）。

### 2.1 产品定位（架构原文）

序境是**面向商业运营与品牌市场的证据驱动工作平台**。**CTH、BMP 是两个业务领域；Shared 是可独立使用、也可供业务领域调用的共享能力；SYSTEM 提供共同基础**。

用户独立工作入口（7 项）：**商业运营、品牌市场、资料研究、提案/文稿、视频、播客、网页浏览**。需要时才连接其他能力。

**五轮是产品交付与验收安排**（SYSTEM → CTH → BMP → Shared → Agent Groups / 自研 AI），不是所有用户任务的强制流水线。

**通用电脑控制已撤出产品范围**：不再交付操作系统桌面、任意本机应用/键鼠控制。内置浏览器、采集、正常文件导入/导出、媒体制作、服务运行和研发工具不受此撤回影响。

### 2.2 AI 边界（架构原文表）

| 领域 | 正常用户成果与基础能力 | AI 增强 | 不可越过的边界 |
| --- | --- | --- | --- |
| SYSTEM / 采集与浏览 | 授权采集、去重、来源保存、刷新恢复、产品内浏览/人工操作 | 页面理解、提取辅助、资料检索与任务步骤建议 | 不绕登录/权限，不改原文，不接管用户电脑 |
| CTH / 商业运营 | 监测与指标、事件风险、案例、人工判断、行动及结果报告 | 解释关联、辅助归因研究、风险解读与决策建议 | 假设与事实分开；无因果证据不声称因果 |
| BMP / 品牌市场 | 品牌资料、传播分析、竞品比较、创作者/Campaign 管理及评价 | 洞察提炼、创意与策略建议、方案比较 | 样本表现不等于全市场/转化，不跨品牌权限 |
| Shared / 研究与创作 | 独立导入检索/研究；直接新建提案文稿、视频播客，编辑播放渲染、保存导出 | 语义检索、摘要、文稿生成、转写和剪辑建议 | 不依赖CTH/BMP；需要联动时带入其来源/版本；生成内容可改可拒绝 |
| Agent Groups / 自研 AI | 原任务的受控调用、状态、取消恢复与评价 | 跨域辅助步骤、模型质量改进与获准持续学习 | 唯一 Gateway/Agent Runtime；训练/晋升另行验收，无 OS 控制 |

**AI 只能增强，不生产 Canonical 事实**。无模型、无外部 AI API、无 GPU 时，编辑、保存、导出、重开、恢复等基础业务仍必须工作。

### 2.3 数据链（架构原文）

```
External Data → Evidence → Canonical Data → Function / Metric → Analysis → Experience / Report / User Outcome
```

- **本研究覆盖范围**：External Data 的来源研究、可用性证明、采集目标和来源说明
- **Source-Target 合同**（v1）必需字段：source_platform、source_url、source_id、canonical_ref、evidence_ref、locator、published_at、captured_at、availability、open_mode、return_context

### 2.4 各入口的数据需求（架构原文映射）

| 用户工作入口 | 数据需求 | 对应研究类别 |
|-------------|---------|-------------|
| 商业运营（CTH） | 获准商业主体、监测结果、事件/日历、风险、已有案例；区分商业体、门店、场内品牌与时间 | B、C、G |
| 品牌市场（BMP） | 品牌、目标市场、竞品比较、消费者/创作者/渠道研究、传播问题、已有 Campaign | B、D、E |
| 资料研究（Shared） | 网页、文件、图片、音视频、已获准采集结果、个人笔记；行业案例 | D、F、G |
| 提案/文稿（Shared） | 用户原创内容为主；可自愿引用研究/CTH/BMP 成果（带来源/版本） | —（原创为主） |
| 视频（Shared，SH-01） | 获准视频、图片、声音、字幕；素材权益核验 | E（创作者素材）、T4 教材概念 |
| 播客（Shared，BMP-08 兼容入口，制作能力归 Shared/C4） | 获准音频；说话人、章节、转写；响度真实核验 | T4 教材概念、播客 RSS |
| 网页浏览（SYSTEM） | 获准网址的真实页面；复用唯一受控浏览器会话 | A1–A4 |

**注**：SH-01 是 Shared Capability Catalog（独立研究与内容制作总目录），BMP-08 是播客制作室兼容入口（制作能力归 Shared/C4 媒体与项目 Owner）。内容制作不需要先完成商业分析，不强制选择 Subject、BrandFocus、Case、Campaign。

### 2.5 合同隐含需求查漏（H 类，11 条）

| H-ID | 需求 | 覆盖状态 |
|------|------|---------|
| H-001 | 商场客流/会员销售（POS） | 部分覆盖（C 有付费供应商，无免费公开源；需 PO 定 Owner） |
| H-002 | 主体→经营单元归属关系 | 部分覆盖（B 商标/企业注册 + G 实体区分，无单一权威源） |
| H-003 | 事件间关系/因果边 | 部分覆盖（D 的 GDELT 事件数据） |
| H-004 | 传播分阶段指标 | 部分覆盖（E 估算 + A3 广告库） |
| H-005 | 创作者生态身份层级 | 已覆盖（E） |
| H-006 | 竞品可比经营指标 | 已覆盖（B 品牌榜单/财报） |
| H-007 | 币种/汇率 | 已覆盖（F） |
| H-008 | 平台官方热榜/排行 | 部分覆盖（A1–A4 公开榜单；纯采集侧最大缺口） |
| H-009 | 品牌评估维度基准 | 已覆盖（B） |
| H-010 | Campaign 投放效果观测 | 部分覆盖（A3 广告透明度库） |
| H-011 | 本地生活/垂直点评反馈 | 部分覆盖（D+G；需 PO 裁决准入） |

**需 PO 决策**：H-001 数据源 Owner、H-007 汇率换算策略、H-010/H-011 准入、UN Comtrade 采购、B 免费价格数据空白。

---

## 3. 全球地区与国家覆盖矩阵

### 3.1 区域覆盖总览

| 区域 | 数据源数 | 已核实可获取 | 缺口说明 |
|------|---------|-------------|---------|
| 中国大陆/港澳台 | 22 | 10 | 大陆无全域内容搜索 API；B 站三重门应叫停直连 |
| 亚洲其他 | 21 | 10 | 印度本土三巨头无公开接口；东南亚/韩国论坛盲区；Naver API 迁移窗口 |
| 北美/拉美 | 21 | 12 | X 按量计费；TikTok Research API 不开放商业用途；拉美 Kwai 无公开 API |
| 欧洲/中东/非洲/大洋洲 | 32 | 27 | GDPR 合规前置；俄语区最大缺口；中东缺社交聆听源 |
| 全球通用（品牌/宏观/地理） | 131 | 91 | 详见 B/C/D/E/F/G |

### 3.2 结构性缺口（诚实记录）

- **俄语区**：VK/OK.ru 无匿名采集可行性，未授权前社交信号为空
- **印度**：ShareChat/Moj/Dailyhunt 均无公开数据接口（NOT VERIFIED）
- **东南亚/韩国论坛**：Kaskus/Pantip/VOZ/DC Inside 无公开 API
- **中东社交聆听**：Snapchat/TikTok 无公开采集通道
- **中国大陆商场级公开客流**：几乎空白
- **中国区商户 POI**：无免费批量源

---

## 4. 全球数据源总表（按可用性分层汇总）

| 可用性分层 | 数量 | 占比 | 说明 |
|-----------|------|------|------|
| VERIFIED_PUBLIC（公开可读） | 104 | 46% | 本轮有证据确认可公开读取 |
| VERIFIED_AUTHORIZED（授权可获取） | 41 | 18% | 官方文档确认可通过指定授权获取 |
| CONDITIONAL（有条件） | 48 | 21% | 存在许可/付费/账户/地区/技术条件 |
| RESTRICTED（受限） | 18 | 8% | 明确限制，不能直接自动采集 |
| NOT VERIFIED（未核实） | 12 | 5% | 资料不足 |
| SUPERSEDED（已停用） | 4 | 2% | 历史资源 |
| **合计** | **227** | 100% | 明细见分类文件（阿康 2026-10-13 复核：E-012/E-013/C-007/C-011/C-013/C-019/C-020/C-022 重分类后重算；除 C 类外逐条分类未入库，NOT VERIFIED） |

---

## 5. 全球社交及本土平台数据目录

### 5.1 中国大陆/港澳台（A1，22 源）

| Source ID | 来源名称 | 获取方式 | 可用性 |
|---|---|---|---|
| A1-001 | 小红书开放平台（官方授权 API） | OAuth 2.0 授权 API | CONDITIONAL |
| A1-002 | 小红书公开内容（网页/搜索） | 网页公开读取（强登录墙） | RESTRICTED |
| A1-003 | 抖音开放平台（官方 API） | OAuth 2.0 + Scope | VERIFIED_AUTHORIZED |
| A1-005 | 微信公众号（官方内容 API） | AppID/AppSecret API | VERIFIED_AUTHORIZED |
| A1-006 | 微信公众号文章公开页 | 网页公开读取 | VERIFIED_PUBLIC |
| A1-008 | 微博开放平台（官方 API） | OAuth 2.0 | CONDITIONAL |
| A1-009 | 微博热搜榜（第三方聚合） | 第三方公开 API | VERIFIED_PUBLIC |
| A1-010 | 哔哩哔哩官方开放平台 | AppKey API（限自有内容） | VERIFIED_AUTHORIZED |
| A1-011 | 哔哩哔哩公开内容接口 | 非官方（robots.txt 禁止） | RESTRICTED |
| A1-012 | 快手开放平台（官方 API） | OAuth 2.0 | VERIFIED_AUTHORIZED |
| A1-014 | 知乎内容平台 | 公开网页（登录墙+反爬） | RESTRICTED |
| A1-017 | 豆瓣公开网页 | 网页公开读取 | VERIFIED_PUBLIC |
| A1-018 | 小宇宙播客 | 网页公开读取 | CONDITIONAL |
| A1-019 | Dcard（台湾） | 网页公开读取 | VERIFIED_PUBLIC |
| A1-020 | PTT（批踢踢） | 开放协议 BBS | VERIFIED_PUBLIC |
| A1-021 | 香港01 | 新闻网站公开读取 | VERIFIED_PUBLIC |

**关键结论**：大陆平台无全域内容搜索 API；B 站三重门（robots.txt+WBI+412）应叫停直连；港澳台 PTT/Dcard/香港01 是最便宜的公开起点。

### 5.2 亚洲其他地区（A2，21 源）

核心：Naver API 迁移窗口（旧密钥 2027-06-30 失效）；印度 TikTok 封禁仍有效；X API Basic $200/月起；东南亚/韩国论坛（Kaskus/Pantip/DC Inside）无公开 API。

### 5.3 北美/拉美（A3，21 源）

核心：X API 2026-02 改按量计费（约 $0.005/帖子）；TikTok Research API 不开放商业用途；Meta Ad Library + TikTok Creative Center 是唯二免登录广告证据源；Bluesky 零成本基线，建议首个 PoC。

### 5.4 欧洲/中东/非洲/大洋洲（A4，32 源）

核心：GDPR 是欧洲生死线（网关须内置 Art.6/9/14/17）；俄语区最大缺口；Nairaland 是非洲英语区高价值链路；中东缺社交聆听源。

**完整 96 条社交平台明细见**：`[研究方本地，未入库] ~/workspace/global-data-research/A1.md`、`A2.md`、`A3.md`、`A4.md`

---

## 6. 全球品牌、商业、零售与市场来源目录

### 6.1 品牌与市场（B，29 源）

| Source ID | 来源名称 | 官方入口 | 可用性 |
|---|---|---|---|
| B-001 | WIPO Global Brand Database（世界知识产权组织全球品牌数 | https://www.wipo.int/en/web/global-brand-database/ | CONDITIONAL |
| B-002 | EUIPO eSearch plus（欧盟知识产权局商标/外观综合检索） | https://www.euipo.europa.eu/en/search-ip | VERIFIED_PUBLIC |
| B-003 | TMview（多国商标统一检索，TMDN） | https://www.tmdn.org/tmview | VERIFIED_PUBLIC |
| B-004 | USPTO Trademark Search（美国专利商标局商标检索，新系统） | https://tmsearch.uspto.gov/ | VERIFIED_PUBLIC |
| B-005 | UK IPO 商标查询（英国知识产权局） | https://www.gov.uk/search-for-trademark | VERIFIED_PUBLIC |
| B-006 | 中国商标网（国家知识产权局商标局） | http://sbj.cnipa.gov.cn/ | CONDITIONAL |
| B-007 | J-PlatPat 商标检索（日本特许厅） | https://www.jpo.go.jp/e/support/j_platpat/trademar | VERIFIED_PUBLIC |
| B-008 | WIPO Madrid Monitor（马德里体系国际注册跟踪） | https://www3.wipo.int/madrid/monitor/en/showData.j | VERIFIED_PUBLIC |
| B-009 | Interbrand Best Global Brands（最佳全球品牌榜） | https://interbrand.com/ | CONDITIONAL |
| B-010 | Brand Finance Global 500（全球最具价值品牌 500 强） | https://brandfinance.com/ | CONDITIONAL |
| B-011 | Kantar BrandZ 最具价值全球品牌榜 |  | NOT VERIFIED |
| B-012 | UK Companies House（英国公司注册处） | https://find-and-update.company-information.servic | VERIFIED_PUBLIC |
| B-013 | SEC EDGAR（美国证券交易委员会电子申报库） | https://www.sec.gov/edgar/search/ | VERIFIED_PUBLIC |
| B-014 | OpenCorporates（全球公司开放数据库） | https://opencorporates.com/ | VERIFIED_PUBLIC |
| B-015 | 国家企业信用信息公示系统 GSXT（中国） | http://www.gsxt.gov.cn/index.html | CONDITIONAL |
| B-016 | Meta Ad Library（Meta 广告库） | https://www.facebook.com/ads/library | VERIFIED_PUBLIC |
| B-017 | Google Ads Transparency Center（Google 广告 | https://adstransparency.google.com/ | VERIFIED_PUBLIC |
| B-018 | TikTok Commercial Content Library（TikTok | https://library.tiktok.com/ads | VERIFIED_PUBLIC |
| B-019 | TikTok Creative Center – Top Ads（TikTok  | https://ads.tiktok.com/business/creativecenter/ins | CONDITIONAL |
| B-020 | LinkedIn Ad Library（领英广告库） | https://www.linkedin.com/ad-library | VERIFIED_PUBLIC |
| B-021 | Microsoft Advertising Library（微软广告库） |  | CONDITIONAL |
| B-022 | Open Food Facts（开放食品数据库） | https://world.openfoodfacts.org | VERIFIED_PUBLIC |
| B-023 | EMARKETER（营销与电商研究） | https://www.emarketer.com | CONDITIONAL |
| B-024 | Statista（统计数据门户） | https://www.statista.com | CONDITIONAL |
| B-025 | WARC（广告营销效果研究） | https://www.warc.com | RESTRICTED |
| B-026 | Google Trends（谷歌趋势） | https://trends.google.com/trends/explore | VERIFIED_PUBLIC |
| B-027 | PR Newswire（美通社新闻稿库） | http://www.prnewswire.com/news-releases/ | VERIFIED_PUBLIC |
| B-028 | Business Wire（商业资讯新闻室） | http://www.businesswire.com/newsroom | VERIFIED_PUBLIC |
| B-029 | Apple Newsroom（品牌官网新闻中心·示例） | https://www.apple.com/newsroom/ | VERIFIED_PUBLIC |

### 6.2 商业运营与零售（C，22 源）

| Source ID | 来源名称 | 官方入口 | 可用性 |
|---|---|---|---|
| C-001 | 广州太古汇官网（Taikoo Hui Guangzhou） | https://www.taikoohui.com | VERIFIED_PUBLIC |
| C-002 | 三里屯太古里官网（Taikoo Li Sanlitun） | https://www.taikoolisanlitun.com | VERIFIED_PUBLIC |
| C-003 | 香港太古广场官网（Pacific Place Hong Kong） | https://www.pacificplace.com.hk | VERIFIED_PUBLIC |
| C-004 | 上海国金中心商场官网（Shanghai IFC Mall） | http://shanghaiifcmall.com.cn/home | VERIFIED_PUBLIC |
| C-005 | 香港 ifc 商场官网（ifc mall Hong Kong） | https://ifc.com.hk/tc/mall/ | VERIFIED_PUBLIC |
| C-006 | 上海恒隆广场官网（Plaza 66） | https://www.plaza66.com | VERIFIED_PUBLIC |
| C-007 | 万达广场官网 | http://www.wandaplaza.cn | CONDITIONAL |
| C-008 | 华润万象生活官网 | https://www.crmixclifestyle.com.cn | VERIFIED_PUBLIC |
| C-009 | Apple 中国零售店查询 | https://www.apple.com.cn/retail/sitemap/sitemap.xm | VERIFIED_PUBLIC |
| C-010 | 优衣库中国店铺检索 | https://www.uniqlo.com/cn/shop/shop447.html | VERIFIED_PUBLIC |
| C-011 | 星巴克中国官网（门店查询） | https://www.starbucks.com.cn | CONDITIONAL |
| C-012 | 赢商网 | https://www.winshang.com | VERIFIED_PUBLIC |
| C-013 | 联商网 | https://www.linkshop.com.cn | NOT VERIFIED |
| C-014 | 第一太平戴维斯中国研究（Savills） | https://www.savills.com.cn | VERIFIED_PUBLIC |
| C-015 | 世邦魏理仕中国洞见与研究（CBRE） | https://www.cbre.com.cn | VERIFIED_PUBLIC |
| C-016 | 仲量联行中国（JLL） | https://www.joneslanglasalle.com.cn | VERIFIED_PUBLIC |
| C-017 | 戴德梁行（Cushman & Wakefield） | https://www.cushmanwakefield.com | VERIFIED_PUBLIC |
| C-018 | 国家统计局 | https://www.stats.gov.cn | VERIFIED_PUBLIC |
| C-019 | Placer.ai | https://www.placer.ai | RESTRICTED |
| C-020 | ShopperTrak（Sensormatic Solutions） | https://www.sensormatic.com/en_sg/shopper-insights | RESTRICTED |
| C-021 | 中国连锁经营协会（CCFA） |  | NOT VERIFIED |
| C-022 | 高德地图开放平台（POI 搜索） | https://lbs.amap.com | CONDITIONAL |

## 7. 全球消费者、创作者及媒体资源目录

### 7.1 消费者与舆情（D，19 源）

| Source ID | 来源名称 | 官方入口 | 可用性 |
|---|---|---|---|
| D-001 | Trustpilot（消费者评论平台） | https://developers.trustpilot.com/ | VERIFIED_AUTHORIZED |
| D-002 | Yelp（本地生活评论平台） | https://docs.developer.yelp.com/ | VERIFIED_AUTHORIZED |
| D-003 | Google 地图评论（Places API） | https://developers.google.com/maps/documentation/p | VERIFIED_AUTHORIZED |
| D-004 | TripAdvisor（公开页 + Terra API） | https://www.tripadvisor.com | CONDITIONAL |
| D-005 | 大众点评（商户公开页） | https://m.dianping.com/shopshare/H8lKZBNUD8rbZ4wA | VERIFIED_PUBLIC |
| D-006 | 黑猫投诉（公开投诉页） | https://tousu.sina.com.cn/ | VERIFIED_PUBLIC |
| D-007 | 全国12315平台（官方统计公报） | https://www.12315.cn | VERIFIED_PUBLIC |
| D-008 | 中国消费者协会年度报告 | https://www.cca.org.cn/ | VERIFIED_PUBLIC |
| D-009 | FTC Consumer Sentinel Network | https://www.ftc.gov/enforcement/consumer-sentinel- | RESTRICTED |
| D-010 | EU Safety Gate（RAPEX 危险产品预警） | https://ec.europa.eu/safety-gate-alerts/screen/sea | VERIFIED_PUBLIC |
| D-011 | BBB（商业信誉与投诉） | https://www.bbb.org | VERIFIED_PUBLIC |
| D-012 | Google News RSS（新闻聚合） | https://news.google.com/rss/search | VERIFIED_PUBLIC |
| D-013 | GDELT 2.0（全球新闻事件数据库） | https://gdeltproject.org/data.html | VERIFIED_PUBLIC |
| D-014 | NewsAPI.org（新闻聚合 API） | https://newsapi.org/ | VERIFIED_AUTHORIZED |
| D-015 | ACSI（美国客户满意度指数） | https://www.theacsi.org/ | CONDITIONAL |
| D-016 | 国际通讯社公开网站（新华 / AP / 路透） | https://www.xinhuanet.com | VERIFIED_PUBLIC |
| D-017 | 人民网领导留言板 | https://liuyan.people.com.cn/ | VERIFIED_PUBLIC |
| D-018 | TripAdvisor Legacy Content API（已废弃） | https://tripadvisor-content-api.readme.io/ | SUPERSEDED |
| D-019 | 黑猫投诉企业舆情/数据服务 | https://www.trustpilot.com/review/www.amazon.com | NOT VERIFIED |

### 7.2 创作者与内容传播（E，13 源）

| Source ID | 来源名称 | 官方入口 | 可用性 |
|---|---|---|---|
| E-001 | NoxI | https://www.noxinfluencer.com/ | VERIFIED_PUBLIC |
| E-002 | Social Blade（第三方社媒统计平台） |  | VERIFIED_PUBLIC |
| E-003 | 新榜 NewRa | https://www.newrank.cn | VERIFIED_PUBLIC |
| E-004 | HypeAuditor（第三方网红营销分析平台） | https://hypeauditor.com/blog/api/ | CONDITIONAL |
| E-005 | 巨量星图（抖音官方达人营销平台） |  | CONDITIONAL |
| E-006 | 小红书蒲公英（小红书官方品牌合作平台） |  | CONDITIONAL |
| E-008 | TikTok Creator Marketplace / TikTok O | https://creatorportal.tiktok.com/ | CONDITIONAL |
| E-009 | 飞瓜数据（第三方短视频/直播数据平台） |  | CONDITIONAL |
| E-010 | 蝉妈妈（第三方抖音数据平台） |  | CONDITIONAL |
| E-012 | YouTube Data API v3（Google 官方数据接口；需 API key/OAuth） | https://developers.google.com/youtube/v3/docs | CONDITIONAL |
| E-013 | 微博创作者/商业生态（平台官方） |  | NOT VERIFIED |

## 8. 官方统计、宏观、地理与其他数据来源

### 8.1 公共与宏观（F，23 源）

| Source ID | 来源名称 | 官方入口 | 可用性 |
|---|---|---|---|
| F-001 | 世界银行开放数据（World Ba | https://data.worldbank.org | VERIFIED_PUBLIC |
| F-002 | IMF 数据门户（IMF Data Portal） | https://www.imf.org/en/Publications/WEO | VERIFIED_PUBLIC |
| F-003 | UNdata（联合国统计司） | https://data.un.org | VERIFIED_PUBLIC |
| F-004 | OECD Data Explorer（经合组织数据） | https://sdmx.oecd.org/public/rest | VERIFIED_PUBLIC |
| F-005 | WTO 数据门户（世界贸易组织） | https://stats.wto.org | CONDITIONAL |
| F-006 | Eurostat（欧盟统计局） | https://ec.europa.eu/eurostat/web/main/data/databa | VERIFIED_PUBLIC |
| F-007 | 中国国家统计局（国家数据） | https://www.stats.gov.cn | VERIFIED_PUBLIC |
| F-008 | 美国人口普查局（U.S. Ce | https://api.census.gov/data.html | VERIFIED_AUTHORIZED |
| F-009 | 美国经济分析局（BEA） | https://www.bea.gov/resources/for-developers | VERIFIED_AUTHORIZED |
| F-010 | FRED（圣路易斯联储经济数据） | https://fred.stlouisfed.org/docs/api/fred/overview | VERIFIED_AUTHORIZED |
| F-011 | 英国国家统计局（ONS） | https://www.ons.gov.uk | VERIFIED_PUBLIC |
| F-012 | 日本 e-Stat（政府统计综合窗口） | http://api.e-stat.go.jp/rest/2.0/app/getStatsData | VERIFIED_AUTHORIZED |
| F-013 | data.gov（美国政府开放数据） | https://catalog.data.gov | VERIFIED_PUBLIC |
| F-014 | data.europa.eu（欧盟开放数据门户） | https://data.europa.eu | CONDITIONAL |
| F-016 | 欧洲央行欧元外汇参考汇率（ECB） | https://www.ecb.europa.eu/stats/policy_and_exchang | VERIFIED_PUBLIC |
| F-017 | UN Tourism（联合国旅游组织数据） | https://pre-www.unwto.org/un-tourism-world-tourism | VERIFIED_PUBLIC |
| F-018 | ILOSTAT（国际劳工组织统计） | https://ilostat.ilo.org/ | VERIFIED_PUBLIC |
| F-020 | 中国海关总署统计（GACC） | http://www.customs.gov.cn | VERIFIED_PUBLIC |
| F-021 | 国家公共数据资源登记平台（国家数据局） | https://www.gov.cn/yaowen/liebiao/202608/content_7 | CONDITIONAL |
| F-022 | BIS 统计（国际清算银行） | https://www.bis.org/statistics | VERIFIED_PUBLIC |

### 8.2 地理空间与实体（G，25 源）

| Source ID | 来源名称 | 可用性 |
|---|---|---|
| G-004 | GeoNames dump | https://download.geonames.org/export/dump/ |
| G-005 | GADM 分国家边界（有条件） | https://gadm.org/download_country.html |
| G-006 | Natural Earth 矢量 | https://www.naturalearthdata.com/downloads/ |
| G-008 | 民政部区划代码 | https://dmfw.mca.gov.cn/9095/xzqh/getList |
| G-010 | UN/LOCODE 代码表 | https://unece.org/trade/cefact/UNLOCODE-Download |
| G-011 | OpenAddresses 地址包 | https://batch.openaddresses.io |
| G-013 | 腾讯位置服务 WebService | https://lbs.qq.com/ |
| G-014 | Google Places API（New） | https://developers.google.com/maps/documentation/places/web-service/usage-and-billing |
| G-015 | 高德 Web 服务 API | https://lbs.amap.com |
| G-016 | 百度地图 Web 服务 API | https://lbsyun.baidu.com/apiconsole/key |
| G-018 | Yelp Fusion API | https://docs.developer.yelp.com/docs/plans |
| G-019 | 企查查开放平台 | https://agent.qcc.com/ |
| G-022 | Wikidata dump / SPARQL | https://query.wikidata.org/sparql |

**完整明细见**：`[研究方本地，未入库] ~/workspace/global-data-research/B.md`（29 源）、`C.md`（22 源）、`D.md`（19 源）、`E.md`（13 源）、`F.md`（23 源）、`G.md`（25 源）

---

## 9. 全球采集目标名单（可追溯来源）

### 9.1 统计

| 类别 | 采集目标数 |
|------|-----------|
| A1 中国大陆/港澳台 | 17 |
| A2 亚洲其他 | 37 |
| A3 北美/拉美 | 32 |
| A4 欧洲/中东/非洲/大洋洲 | 32 |
| B 品牌与市场 | 13 |
| C 商业运营与零售 | 18 |
| D 消费者与舆情 | 26 |
| E 创作者资源 | 6 |
| F 公共与宏观 | 48 |
| G 地理空间实体 | 15 |
| **合计** | **244** |

### 9.2 重点采集目标（示例，完整 244 条见分类文件）

**公开账号与官方主体**：
- 各平台官方账号（如 @小红书、@抖音、@微信派）——以平台认证标识核验归属
- 品牌官方账号——必须经平台认证标识二次核验，提及≠归属

**品牌/企业/购物中心**：
- 广州太古汇、北京三里屯太古里、香港太古广场、上海国金中心、香港 ifc（官网商户名录为金标准）
- Interbrand / Brand Finance 榜单品牌（方法论须固定单一来源）

**媒体/机构/官方统计**：
- 世界银行、IMF、UNdata、OECD、WTO、Eurostat、中国国家统计局、美国 Census/BEA/FRED、英国 ONS
- GDELT 2.0（事件数据）、Google News RSS（免费舆情）

**搜索词/主题词**（历史词条保留，不作为上限）：
- 品牌舆情：品牌名 + 评测/投诉/推荐/避雷
- 商业运营：商场名 + 开业/闭店/品牌进驻/客流
- 事件追踪：以 GDELT 事件 ID 为准

### 9.3 暂时无法获取的数据

| 数据 | 原因 | 替代来源 |
|------|------|---------|
| 大陆平台全域内容搜索 | 无官方 API | 第三方聚合（CONDITIONAL）+ 人工核验 |
| 商场级公开客流 | 几乎空白 | 付费供应商（CONDITIONAL） |
| 中国区商户 POI 批量 | 无免费批量源 | 高德 POI API（程序化最优路径） |
| 俄语区社交信号 | VK/OK 无匿名采集 | 授权后补充 |
| 印度本土平台数据 | 无公开接口 | NOT VERIFIED，待核 |

---

## 10. 数据获取方式、授权、费用与使用限制

### 10.1 获取方式分布

| 获取方式 | 说明 |
|---------|------|
| 官方 API（OAuth/ AppKey） | 需开发者注册、应用审核、用户/商家授权；多限自有数据 |
| 开放文件/数据下载 | 世界银行、UNdata、GADM（注意许可限制）等 |
| 公开网页 | 遵守 robots.txt、频率限制；登录墙/反爬的不做自动化 |
| 授权导出 | 创作者自有数据、商家后台 |

### 10.2 费用参考（已核实，不编造）

| 项目 | 费用 |
|------|------|
| X API Basic | $200/月起（2026-02 起按量约 $0.005/帖子） |
| UN Comtrade | 约 $2,000/年（唯一需采购决策源） |
| 微信公众号认证 | 300元/年（第三方手册提及，以官方为准） |
| 其余 | 无公开价格信息的一律标"未核实"，不编造 |

### 10.3 使用限制要点

- 不得绕过登录、访问限制、付费授权、平台风控、隐私保护或第三方许可
- 第三方估算数据必须在 Canonical 层打"估算"标签
- 品牌提及≠归属，归属须经平台认证标识二次核验

---

## 11. 适合优先交给 Codex / 阿康的数据源清单

### 11.1 立即可用（VERIFIED_PUBLIC，零成本）

| 优先级 | 数据源 | 说明 |
|--------|--------|------|
| P0 | GDELT 2.0 | 免费舆情/事件主源 |
| P0 | Google News RSS | 免费新闻聚合 |
| P0 | Bluesky | 零成本社交基线，建议首个 PoC |
| P0 | 世界银行/IMF/UNdata/OECD | 宏观数据免费 |
| P0 | OpenStreetMap | 地理实体免费（注意商业许可） |
| P1 | PTT/Dcard/香港01 | 港澳台舆情公开源 |
| P1 | Meta Ad Library | 免登录广告证据源 |
| P1 | TikTok Creative Center | 免登录广告证据源 |
| P1 | YouTube 频道 RSS（零凭据）；Data API v3 待取得 API key 后启用（CONDITIONAL） | 零授权下的 YouTube 官方路径为 RSS；Data API 需凭据 |

### 11.2 需授权后接入（VERIFIED_AUTHORIZED）

- 小红书开放平台（需开发者认证+应用审核；XHS 只用香港账号）
- 抖音/快手开放平台（限自有账号数据）
- 微信公众号 API（限自有公众号）
- Trustpilot/Yelp/Google Places API（需 API Key）

### 11.3 需 PO 决策后接入

- UN Comtrade（$2,000/年采购）
- X API（$200/月起）
- 付费客流供应商（H-001）
- 企查查（数据出境红线，需法务确认）

---

## 12. 无法获取、未核实及重要覆盖缺口

| 类别 | 缺口描述 | 状态 |
|------|---------|------|
| 社交平台 | 俄语区 VK/OK.ru 无匿名采集可行性 | RESTRICTED |
| 社交平台 | 印度 ShareChat/Moj/Dailyhunt 无公开接口 | NOT VERIFIED |
| 社交平台 | 东南亚/韩国论坛无公开 API | NOT VERIFIED |
| 社交平台 | 中东社交聆听无公开通道 | 缺口 |
| 社交平台 | 拉美 Kwai 无公开 API | NOT VERIFIED |
| 商业数据 | 大陆商场级公开客流几乎空白 | 缺口 |
| 地理数据 | 中国区商户 POI 无免费批量源 | 缺口 |
| 地理数据 | 国家统计局区划代码 2024-10 起停更 | 缺口 |
| 品牌数据 | 免费层价格数据空白 | 缺口 |
| 采集机制 | 平台官方热榜纯采集侧最大缺口（H-008） | 部分覆盖 |

---

## 13. 数据质量、身份归属、时间语义及合规风险

### 13.1 合规红线（研发必读）

1. **GDPR**：欧洲源开采前网关须内置 Art.6/9/14/17（A4）
2. **健康内容**属 Art.9 特殊类别，禁止个人健康陈述入库（A4）
3. **GADM** 仅学术/非商业，商业产品内置须先获书面许可（G）
4. **企查查**禁止境外主体访问、数据仅限境内（G）
5. **FAOSTAT** 为 CC BY-NC-SA（含非商业限制），需法务确认（F）
6. **第三方估算数据**（粉丝/互动/报价）必须在 Canonical 层打"估算"标签（E）
7. **品牌提及≠归属**，归属须经平台认证标识二次核验（E）

### 13.2 身份归属原则

- 内容提及某品牌 ≠ 该账号属于该品牌
- 关键词命中 ≠ 官方账号/员工/门店/合作达人
- 所有账号归属必须单独核验（认证标识 + 官方链接交叉）

### 13.3 时间语义

- published_at（发布时间）与 captured_at（采集时间）必须分别记录（Source-Target 合同必需字段）
- 历史覆盖：优先选择有明确历史回溯能力的源（如 GDELT、Internet Archive）

### 13.4 数据质量风险

- 第三方聚合：稳定性无保障，入库前标注 via=第三方聚合且二次核验
- 品牌价值榜单：三套方法论数值差数倍，时间序列须固定单一来源
- 免费层价格数据：空白，不做推断

---

## 14. 原有序境能力如何接入这些数据的对应建议

| 序境现有能力 | 接入建议 |
|-------------|---------|
| SYSTEM Collector（`lumenis/system/collector/adapters/`：本机 34 个文件 / GitHub main@8ec0bf3 35 个 .py，含基础设施文件） | 优先扩展 Bluesky、GDELT、Google News RSS（零成本）；现有平台适配器继续沿用（以仓库实数为准） |
| Source-Target 合同 v1 | 新数据源按 required_fields（source_platform、source_url、source_id、canonical_ref、evidence_ref、locator、published_at、captured_at、availability、open_mode、return_context）接入 |
| Evidence 存储 | GDELT 事件、广告库、公开榜单进入 Evidence 链；第三方估算打"估算"标签 |
| CTH 商业运营 | 商场官网商户名录（香港 ifc 为模板）+ 高德 POI API（门店级） |
| BMP 品牌市场 | WIPO/EUIPO/USPTO 商标库 + Interbrand/Brand Finance 榜单 + Meta Ad Library |
| Shared 研究 | 世界银行/IMF/UNdata 宏观数据 + OpenStreetMap 地理 + 播客/新闻公开源 |

**不做的**：不改写 Collector 架构；不在采集时做品牌分类/情绪判断（属后续工作流）；不绕过任何访问限制。

---

## 15. 研究核验日期、来源链接与统计方法

- **核验日期**：2026-10-13
- **来源链接**：每条数据源记录含官方入口 URL（见分类文件）；本主文件为编译合成
- **统计方法**：全部数字从 227 条逐条记录加总计算（104+41+48+18+12+4=227，阿康复核重分类后重算）；244 个采集目标逐类加总；无估算、无"全球覆盖百分之百"式断言
- **分类文件**：`[研究方本地，未入库] ~/workspace/global-data-research/` 下 A1/A2/A3/A4/B/C/D/E/F/G/H.md（共 476KB）
- **治理依据**：GitHub main@3b6adcb 的 AGENTS.md、LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md、LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md、source-target-contract-v1.json（只读核实）

---

## 16. 总体完成度、真正完成的研究范围与尚未证实的范围

### 16.1 RESULT（已完成）

- ✅ 227 个数据源逐条调查（含统一字段、可用性分层）
- ✅ 244 个真实采集目标整理（附可核验链接）
- ✅ 全球覆盖矩阵（区域×类别）
- ✅ 11 条合同隐含需求交叉判定（4 已覆盖 / 7 部分覆盖 / 0 未覆盖）
- ✅ 合规红线 7 条、研发接入建议、优先级清单
- ✅ 统计数字全部可复核

### 16.2 NOT VERIFIED（尚未证实）

- 10 条数据源未核实（印度本土平台、东南亚论坛等）
- 41 项隔离测试（数学方法）本轮未独立重跑——属上一轮遗留，非本任务范围
- 平台官方热榜纯采集侧缺口（H-008）待 PO 批准后另行 REA 深挖
- 部分第三方聚合的长期稳定性未验证

### 16.3 需 PO 决策（6 项）

1. H-001 商场客流数据源 Owner 指定
2. H-007 汇率换算策略
3. H-010/H-011 数据准入裁决
4. UN Comtrade $2,000/年采购
5. B 类免费价格数据空白的填补策略
6. PR #21 合入（非本任务范围，另行决策）

---

（历史记录：研究方于 2026-10-13 报告本研究完成。本文件仅为研究证据，不构成任何窗口的调度、待命或派工指令。）

---

## 17. 零授权采集路径总表（v2 新增）

**前提**：PO 目前零平台官方授权。以下每条均为"现在、零授权、就能拿数据"的具体路径，✅ 为本轮实测可读。

### 17.1 社交媒体零授权路径（按自立度排序）

| 路径 ID | 路径 | 自立度 | 频率建议 |
|---------|------|--------|---------|
| YT-01 | YouTube 频道 RSS `youtube.com/feeds/videos.xml?channel_id=UC...`（官方 feed、无需 key、近 15 条） | **高** | ≤1 小时 |
| WB-01 | 微博热搜榜 `s.weibo.com/top/summary` ✅（分钟级、含分类+热度） | **高** | ≤15 分钟 |
| DY-01 | 抖音热点榜 `douyin.com/share/billboard` ✅（50 条+热度值+时间戳） | **高** | ≤15 分钟 |
| BI-01 | B站排行榜 `bilibili.com/v/popular/rank/all` ✅（100 条、UP 主+播放数） | **高** | ≤1 小时 |
| WX-01/02 | 搜狗微信搜索 ✅ + 公众号文章页 `mp.weixin.qq.com` ✅（免登录可读） | **高** | 事件驱动 |
| TT-01 | TikTok Creative Center ✅（趋势/Top Ads，免登录公开） | **高** | ≤1 小时 |
| FB-01 | Meta Ad Library（浏览器端免登录公开） | **高** | ≤1 小时 |
| WB-02/03 | 微博话题搜索页 ✅ + 品牌蓝V主页解析 | **高** | ≤1 小时 |
| IG/FB/X-公开页 | IG/FB/X/TikTok 公开 profile/帖子页解析 | **高**·脆弱 | ≤1 小时 |
| XHS-01 | 小红书单页人工核验（人工，不可规模化） | **高**·人工 | 按需 |
| RSSHub/第三方聚合 | tophub/千瓜/蝉妈妈/新榜/RSSHub | **低** | 补充 |

**今日实测不可读**：小红书（强登录墙）、知乎热榜（403）、快手 Web（JSON 反爬）、YouTube trending（JS 墙）——已降级，不列入主路径。

### 17.2 品牌/商业零授权路径

| 路径 | 自立度 |
|------|--------|
| 四商场官网解析器（ifc 目录/太古汇中英页/海港城品牌页+PDF/plaza66 品牌页） | **高** |
| 商标五库网页人工查询（WIPO/EUIPO/TMview/USPTO/中国商标网） | **高** |
| EUIPO Open Data 全量 XML 下载一次、本地建 EUTM 索引 | **高** |
| 国家企业信用信息公示系统 gsxt.gov.cn（免登录+验证码） | **高** |
| 品牌官网 footer 社交链接确权 + 微博蓝V + 微信公众号公开页 | **高** |

### 17.3 舆情/宏观/地理零授权路径

| 路径 | 自立度 |
|------|--------|
| GDELT 文件流自建库（`data.gdeltproject.org/gdeltv2/`，每 15 分钟） | **高** |
| OSM planet/Geofabrik 自建 POI 库（周更/日更） | **高** |
| WDI/WEO 整库文件入库（CSV/Excel 下载） | **高** |
| FRED CSV 直下（`fredgraph.csv?id=GDP`，免 key） | **高** |
| 六家舆情站公开页自研渲染采集（Trustpilot→黑猫→Tripadvisor→大众点评→Yelp→Google 地图） | **高** |
| Google News RSS | **高** |
| 区划快照自建地址库（2023-06-30 基座 + 高德 adcode 校验补增量） | **高** |
| 小宇宙公开页解析（`xiaoyuzhoufm.com/podcast/{24位hex}`） | **高** |
| 出版方 RSS 直采（播客全量单集+enclosure 直链） | **高** |

---

## 18. 名单关系图谱（v2 新增）

### 18.1 品牌→商场→竞品关系

**枢纽品牌共现**（7 商场：广州太古汇/北京SKP/三里屯太古里/上海国金/上海恒隆/香港海港城/香港ifc）：
- **6 共现**：Louis Vuitton、Chanel
- **5 共现**：Dior、Gucci、Hermès、Cartier、Prada、Tiffany & Co.
- **4 共现**：Starbucks
- **3 共现**：Burberry、Fendi、Celine、Apple、adidas、city'super

**品牌关系卡**（10 张，完整版见 `v2/T2.md`）：
| 品牌 | 进驻商场数 | 同商场竞品 | 关键词 |
|------|-----------|-----------|--------|
| Louis Vuitton | 6 | Chanel/Dior/Gucci/Hermès/Prada | 老花、Monogram、独栋旗舰 |
| Chanel | 6（含 ifc 三处） | Dior/LV/Gucci/Hermès | 山茶花、5号香水 |
| Dior | 5（三里屯北区独栋） | Chanel/LV/Saint Laurent/Celine | 马鞍包 |
| Gucci | 5 | LV/Prada/Saint Laurent/Bottega Veneta | 双G、开云 |
| Hermès | 5 | Chanel/Dior/LV | 铂金包、Kelly、配货 |
| Cartier | 5 | Tiffany/Bvlgari/周生生/老铺黄金 | 猎豹系列、历峰 |
| Prada | 5 | Gucci/LV | 尼龙包 |
| Tiffany | 5（三里屯北区独栋） | Cartier/Bvlgari/老铺黄金 | 蒂芙尼蓝 |
| 老铺黄金 | 2（SKP一层+ifc） | Cartier/Tiffany/周生生 | 古法金、东方硬奢 |
| 周生生 | 2 | 老铺黄金/Cartier/Tiffany | 港资锚点 |

**品类集群**：腕表集群（ifc L1/L2 一采全收）/ 运动（Nike vs adidas vs lululemon）/ 美妆（Sephora 渠道 vs 专柜品牌）/ 餐饮首店 / 百货（Lane Crawford vs SKP）

### 18.2 采集扩展五波顺序

1. **第一波**：LV/Chanel（6 共现，验证商场名单）
2. **第二波**：Dior/Gucci/Hermès/Cartier/Prada/Tiffany（同商场竞品横向扩展）
3. **第三波**：品类集群（腕表/运动/美妆/餐饮）
4. **第四波**：本土对照（老铺黄金/周生生）
5. **第五波**：长尾（LCX、设计师品牌）

### 18.3 品牌-账号确权流程

微博站内搜品牌名认蓝V → 品牌官网 footer 社交链接确权（防重名）→ 微信公众号（微信站内搜官方认证主体）→ Instagram 公开页（handle 先经官网确权）。**提及≠归属**，归属须认证+官网互链双重核验。

---

## 19. 创意/剪辑/播客精准概念（v2 新增，支撑 Shared 内容制作）

**来源**：PO 原有教材研究（FCP 12.4 手册/DaVinci Resolve 20 Editor/Fairlight/Fusion，`work/frontend-2026-10-03/textbook-research/教材到序境-开发采用说明.md`）+ 2026-10-13 联网补充。25 个概念，每个带教材出处页码。

**Screen 定义**（按 `contracts/experience/screen-specifications/` 合同原文）：
- **SH-01**：Shared Capability Catalog——独立研究与内容制作总目录。用户可直接新建提案/文稿、视频或播客，不强制先创建 CTH/BMP 任务。
- **BMP-08**：播客制作室——兼容入口标签；**播客制作能力属于 Shared/C4 媒体与项目 Owner**，可独立使用，不因 BMP 标签变成 BMP 独占。

### 19.1 FCP 12.4 → SH-01 视频制作

| 概念 ID | 概念 | 教材出处 | SH-01 映射 | 数据需求 |
|---------|------|---------|-----------|---------|
| C-FCP-01 | 磁性时间线 | p.9 | 时间线引擎 | in/out 点、连接关系、操作类型 |
| C-FCP-02 | Roles（5 默认+自定义） | p.478-479 | 轨道/分轨 | 角色分配、subrole、lane 映射 |
| C-FCP-03 | 非破坏编辑 | p.13 | 版本/撤销语义 | 素材引用+编辑决策+版本链 |
| C-FCP-04 | 事件查看器（源/作品区分） | p.15 | 源/作品区分 | 双查看器状态 |
| C-FCP-05 | 精度编辑器（handles/roll/ripple） | p.547-548 | 精剪 | handles 时长、编辑点类型 |
| C-FCP-06 | 导出/stems/批量分享 | p.810 | 交付 | 导出任务、哈希、重开校验 |

### 19.2 Resolve Editor → SH-01

| 概念 ID | 概念 | 教材出处 | SH-01 映射 |
|---------|------|---------|-----------|
| C-ED-01 | 先粗剪后精剪 | p.10/p.84 | 阶段流 |
| C-ED-02 | 源 vs 时间线查看器 | p.10 | 源/作品区分 |
| C-ED-03 | 大改前复制时间线备份 | p.76 | 工程版本 |
| C-ED-04 | Roll vs Ripple 三分 | p.86/p.93 | 修剪语义 |
| C-ED-06 | 导出后实际重开检查 | p.608 | 交付验收铁律 |
| C-ED-07 | 多画幅重构（1:1/9:16） | p.553 | 多画幅 |

### 19.3 Resolve Fairlight → 播客制作（BMP-08 兼容入口，能力归 Shared/C4）

| 概念 ID | 概念 | 教材出处 | BMP-08 映射 |
|---------|------|---------|------------|
| C-FA-01 | 第一课即播客片头 | p.2 | 片头模板一等对象 |
| C-FA-02 | 片段增益 ≠ 最终响度（三级增益） | p.11/p.317/p.616 | clip gain dB→轨道→LUFS；"0 dB 不写成静音" |
| C-FA-03 | 对白编辑器（音节清晰） | p.82 | 对白清晰度硬门槛 |
| C-FA-04 | 棋盘式编辑（按人物拆轨） | p.106 | 分角色编辑 |
| C-FA-05 | AI 语音转文本（词级时间戳） | p.153 | 文本剪辑索引 |
| C-FA-06 | Ducker 自动避让 | p.552 | 自动避让 |
| C-FA-07 | 试听验证节奏（不画假波形） | p.70 | 铁律 |

### 19.4 Resolve Fusion → SH-01（包装）

| 概念 ID | 概念 | 教材出处 | SH-01 映射 |
|---------|------|---------|-----------|
| C-FU-01 | 任意节点状态查看 | p.17 | 中间结果对比 |
| C-FU-02 | Pass-through 旁路 | p.17 | 效果 A/B |
| C-FU-03 | Versions（单节点 6 快照） | p.161 | 包装可撤回 |
| C-FU-04 | Macro 只暴露必要参数 | p.163 | 品牌模板 |
| C-FU-05 | Clip Versions | p.163 | 片段级版本 |

### 19.5 播客数据源（零授权）

| 路径 | 自立度 |
|------|--------|
| 出版方 RSS 直采（全量单集+enclosure 直链） | **高**（主路径） |
| 小宇宙公开页解析 ✅（标题/简介/章节/评论/封面 CDN） | **高** |
| Spotify 公开节目页 | **高** |
| Spotify Charts / Podtrac 公开榜 / OP3 | **高** |
| Apple Charts JSON（`rss.marketingtools.apple.com`，已实测 cn 可用） | **低**（未文档化） |
| iTunes Search/Lookup（只拿 feedUrl 后转 RSS） | **低** |

**推荐闭环**：榜单发现 → iTunes lookup 取 feedUrl → RSS 直采 → 本地转写+说话人分离 → 按教材概念落地 SH-01/BMP-08。

**2026 AI 剪辑生态结论**：Opus Clip/Descript/CapCut 均无开放集成支撑独立运转；能力可被"本地转写+自研剪辑语义"覆盖，走自建=高自立。

---

---

## 20. 主体注册表种子清单（v3：R-J1 768 条；已核实主体见 scripts/data_candidates/subject_registry_seed_20261013.jsonl）

> **更正（阿康 2026-10-13）**：本节原称"直接可入库"不准确。按 `subject_registry.py` 与 `lumenis/shared/database/entity_relations.py`：主体须逐条核验后以 status=configured 进入 `lumenis_subject_registry`（CTH=company / BMP=brand，同名跨域可共存）；场内关系只能作为 TENANT_OF 候选，须经 Collector 抓取商场名录页形成 verified Evidence 后由 `record_venue_tenant_claim` 写入。已核实主体经 `scripts/import_subject_registry_seed.py` 走 `subject_registry.add_subject` 入库；未核实主体与场内关系候选不入库。

**表结构依据**：`subject_registry.py`（`lumenis_subject_registry` 表）
**数据文件**：`[研究方本地，未入库] ~/workspace/global-data-research/v2/R-J1/`（9 个 py + README）

### 20.1 统计

| 类别 | 条数 | 说明 |
|------|------|------|
| 商业主体（company → CTH） | 499 | 购物中心/百货、主题乐园、公司 |
| 品牌主体（brand → BMP） | 136 | 中国优秀/小众、境外在华、全球 |
| 场内关系 | 133 | 品牌→商场→铺位 |
| **合计** | **768** | |

### 20.2 商业主体全量（company → CTH，499 条）

| name_zh | name_en | industry | 层级路径 | 核验 |
|---------|---------|----------|----------|------|
| 深圳万象城 | MixC Shenzhen | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 深圳万象天地 | MixC World Shenzhen | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 杭州万象城 | MixC Hangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 杭州城北万象城 | MixC North Hangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 上海万象城 | MixC Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 成都万象城 | MixC Chengdu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 重庆万象城 | MixC Chongqing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 沈阳万象城 | MixC Shenyang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 无锡万象城 | MixC Wuxi | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 合肥万象城 | MixC Hefei | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 郑州万象城 | MixC Zhengzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 郑州郑东万象城 | MixC Zhengdong Zhengzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 南昌万象城 | MixC Nanchang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 长沙万象城 | MixC Changsha | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 西安万象城 | MixC Xi'an | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 昆明万象城 | MixC Kunming | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 贵阳万象城 | MixC Guiyang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 武汉武昌万象城 | MixC Wuchang Wuhan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 温州滨江万象城 | MixC Binjiang Wenzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 常州万象城 | MixC Changzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 呼和浩特万象城 | MixC Hohhot | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 淮安万象城 | MixC Huai'an | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 兰州万象城 | MixC Lanzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 长春万象城 | MixC Changchun | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/华润万象系 | VERIFIED |
| 北京西单大悦城 | Xidan Joy City Beijing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/大悦城系 | VERIFIED |
| 北京朝阳大悦城 | Chaoyang Joy City Beijing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/大悦城系 | VERIFIED |
| 上海静安大悦城 | Jing'an Joy City Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/大悦城系 | VERIFIED |
| 上海长风大悦城 | Changfeng Joy City Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/大悦城系 | VERIFIED |
| 天津大悦城 | Joy City Tianjin | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/大悦城系 | VERIFIED |
| 沈阳大悦城 | Joy City Shenyang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/大悦城系 | VERIFIED |
| 成都大悦城 | Joy City Chengdu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/大悦城系 | VERIFIED |
| 重庆大悦城 | Joy City Chongqing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/大悦城系 | VERIFIED |
| 杭州大悦城 | Joy City Hangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/大悦城系 | VERIFIED |
| 武汉大悦城 | Joy City Wuhan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/大悦城系 | VERIFIED |
| 北京长楹天街 | Changying Paradise Walk Beijing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 北京房山天街 | Fangshan Paradise Walk Beijing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 北京大兴天街 | Daxing Paradise Walk Beijing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 上海闵行天街 | Minhang Paradise Walk Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 上海宝山天街 | Baoshan Paradise Walk Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 南京江北天街 | Jiangbei Paradise Walk Nanjing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 苏州狮山天街 | Shishan Paradise Walk Suzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 杭州滨江天街 | Binjiang Paradise Walk Hangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 杭州西溪天街 | Xixi Paradise Walk Hangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 杭州钱江天街 | Qianjiang Paradise Walk Hangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 成都滨江天街 | Binjiang Paradise Walk Chengdu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 成都西宸天街 | Xichen Paradise Walk Chengdu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 重庆北城天街 | Beicheng Paradise Walk Chongqing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 重庆时代天街 | Times Paradise Walk Chongqing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 重庆龙兴天街 | Longxing Paradise Walk Chongqing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 重庆江岸天街 | Jiang'an Paradise Walk Chongqing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 西安香醍天街 | Paradise Walk Xi'an | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 武汉滨江天街 | Binjiang Paradise Walk Wuhan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 武汉新荣天街 | Xinrong Paradise Walk Wuhan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 昆明时代天街 | Times Paradise Walk Kunming | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 济南西城天街 | Xicheng Paradise Walk Jinan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 烟台龙口天街 | Longkou Paradise Walk Yantai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 西安长乐天街 | Changle Paradise Walk Xi'an | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/龙湖天街系 | VERIFIED |
| 北京来福士 | Raffles City Beijing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/凯德系 | VERIFIED |
| 上海来福士 | Raffles City Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/凯德系 | VERIFIED |
| 重庆来福士 | Raffles City Chongqing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/凯德系 | VERIFIED |
| 杭州来福士 | Raffles City Hangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/凯德系 | VERIFIED |
| 深圳来福士 | Raffles City Shenzhen | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/凯德系 | VERIFIED |
| 成都来福士 | Raffles City Chengdu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/凯德系 | VERIFIED |
| 上海北外滩来福士 | Raffles City The Bund Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/凯德系 | VERIFIED |
| 北京凯德MALL太阳宫 | CapitaMall Taiyanggong Beijing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/凯德系 | VERIFIED |
| 北京凯德MALL望京 | CapitaMall Wangjing Beijing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/凯德系 | VERIFIED |
| 上海凯德龙之梦虹口 | CapitaMall Longzhimeng Hongkou Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/凯德系 | VERIFIED |
| 广州凯德广场云尚 | CapitaMall Yunshang Guangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/凯德系 | VERIFIED |
| 广州太古汇 | Taikoo Hui Guangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/太古系 | VERIFIED |
| 北京三里屯太古里 | Taikoo Li Sanlitun Beijing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/太古系 | VERIFIED |
| 成都远洋太古里 | Sino-Ocean Taikoo Li Chengdu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/太古系 | VERIFIED |
| 上海兴业太古汇 | HKRI Taikoo Hui Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/太古系 | VERIFIED |
| 北京颐堤港 | INDIGO Beijing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/太古系 | VERIFIED |
| 广州太古仓 | Taikoo Warehouse Guangzhou | 商业 | 商业主体宇宙/中国境内/购物中心与百货/太古系 | VERIFIED |
| 上海恒隆广场 | Plaza 66 Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/恒隆系 | VERIFIED |
| 上海港汇恒隆广场 | Grand Gateway 66 Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/恒隆系 | VERIFIED |
| 大连恒隆广场 | Olympia 66 Dalian | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/恒隆系 | VERIFIED |
| 沈阳市府恒隆广场 | Forum 66 Shenyang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/恒隆系 | VERIFIED |
| 济南恒隆广场 | Parc 66 Jinan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/恒隆系 | VERIFIED |
| 昆明恒隆广场 | Spring City 66 Kunming | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/恒隆系 | VERIFIED |
| 武汉恒隆广场 | Heartland 66 Wuhan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/恒隆系 | VERIFIED |
| 无锡恒隆广场 | Center 66 Wuxi | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/恒隆系 | VERIFIED |
| 天津恒隆广场 | Riverside 66 Tianjin | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/恒隆系 | VERIFIED |
| 上海国金中心商场 | Shanghai IFC Mall | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/新鸿基九龙仓系 | VERIFIED |
| 上海环贸iapm商场 | iapm Mall Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/新鸿基九龙仓系 | VERIFIED |
| 北京apm | Beijing apm | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/新鸿基九龙仓系 | VERIFIED |
| 苏州中心商场 | Suzhou Center Mall | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/新鸿基九龙仓系 | VERIFIED |
| 香港新城市广场 | New Town Plaza Hong Kong | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/新鸿基九龙仓系 | VERIFIED |
| 香港apm | apm Hong Kong | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/新鸿基九龙仓系 | VERIFIED |
| 香港国际金融中心商场 | ifc mall Hong Kong | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/新鸿基九龙仓系 | VERIFIED |
| 香港海港城 | Harbour City Hong Kong | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/新鸿基九龙仓系 | VERIFIED |
| 香港时代广场 | Times Square Hong Kong | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/新鸿基九龙仓系 | VERIFIED |
| 长沙国金中心IFS | Changsha IFS | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/新鸿基九龙仓系 | VERIFIED |
| 成都国际金融中心IFS | Chengdu IFS | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/新鸿基九龙仓系 | VERIFIED |
| 重庆国金中心IFS | Chongqing IFS | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/新鸿基九龙仓系 | VERIFIED |
| 北京SKP | SKP Beijing | 百货 | 商业主体宇宙/中国境内/购物中心与百货/SKP系 | VERIFIED |
| 西安SKP | SKP Xi'an | 百货 | 商业主体宇宙/中国境内/购物中心与百货/SKP系 | VERIFIED |
| 武汉SKP | SKP Wuhan | 百货 | 商业主体宇宙/中国境内/购物中心与百货/SKP系 | NOT VERIFIED |
| 昆明SKP | SKP Kunming | 百货 | 商业主体宇宙/中国境内/购物中心与百货/SKP系 | NOT VERIFIED |
| 北京银泰中心in01 | Yintai Centre Beijing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/银泰系 | VERIFIED |
| 杭州银泰in77 | Intime 77 Hangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/银泰系 | VERIFIED |
| 成都银泰中心in99 | Intime 99 Chengdu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/银泰系 | VERIFIED |
| 杭州武林银泰 | Wulin Intime Hangzhou | 百货 | 商业主体宇宙/中国境内/购物中心与百货/银泰系 | VERIFIED |
| 上海百联南方购物中心 | Bailian Nanfang Mall Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/百联系 | VERIFIED |
| 上海第一八佰伴 | Shanghai No.1 Yaohan | 百货 | 商业主体宇宙/中国境内/购物中心与百货/百联系 | VERIFIED |
| 上海永安百货 | Wing On Shanghai | 百货 | 商业主体宇宙/中国境内/购物中心与百货/百联系 | VERIFIED |
| 上海青浦百联奥特莱斯 | Bailian Outlets Qingpu Shanghai | 奥特莱斯 | 商业主体宇宙/中国境内/购物中心与百货/百联系 | VERIFIED |
| 北京王府井百货大楼 | Wangfujing Department Store Beijing | 百货 | 商业主体宇宙/中国境内/购物中心与百货/王府井系 | VERIFIED |
| 北京双安商场 | Shuang'an Beijing | 百货 | 商业主体宇宙/中国境内/购物中心与百货/王府井系 | VERIFIED |
| 广州王府井百货 | Wangfujing Guangzhou | 百货 | 商业主体宇宙/中国境内/购物中心与百货/王府井系 | VERIFIED |
| 成都王府井百货 | Wangfujing Chengdu | 百货 | 商业主体宇宙/中国境内/购物中心与百货/王府井系 | VERIFIED |
| 长沙王府井百货 | Wangfujing Changsha | 百货 | 商业主体宇宙/中国境内/购物中心与百货/王府井系 | VERIFIED |
| 重庆王府井百货 | Wangfujing Chongqing | 百货 | 商业主体宇宙/中国境内/购物中心与百货/王府井系 | VERIFIED |
| 北京合生汇 | Hopson One Beijing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/合生汇系 | VERIFIED |
| 上海合生汇 | Hopson One Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/合生汇系 | VERIFIED |
| 广州合生汇 | Hopson One Guangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/合生汇系 | VERIFIED |
| 北京侨福芳草地 | Parkview Green Beijing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/芳草地系 | VERIFIED |
| 上海静安嘉里中心 | Jing An Kerry Centre Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/嘉里系 | VERIFIED |
| 北京嘉里中心商场 | Kerry Centre Beijing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/嘉里系 | VERIFIED |
| 北京国贸商城 | China World Mall Beijing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/国贸系 | VERIFIED |
| 广州天河城 | Teemall Guangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 广州正佳广场 | Grandview Mall Guangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 杭州大厦 | Hangzhou Tower | 百货 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 南京德基广场 | Deji Plaza Nanjing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 南京德基广场二期 | Deji Plaza Phase II Nanjing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 武汉楚河汉街 | Chu River Han Street Wuhan | 商业街 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 西安赛格国际购物中心 | Sage International Shopping Center Xi'an | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 上海K11 | K11 Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 广州K11 | K11 Guangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 武汉K11 | K11 Wuhan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 沈阳K11 | K11 Shenyang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 天津K11 | K11 Tianjin | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 武汉武商MALL | Wushang MALL Wuhan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 武汉广场 | Wuhan Plaza | 百货 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 武汉世贸广场 | Wuhan World Trade Plaza | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 宁波阪急 | Hankyu Ningbo | 百货 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 上海久光百货 | Hisamitsu Shanghai | 百货 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 大连久光百货 | Hisamitsu Dalian | 百货 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 厦门宝龙一城 | Xiamen Baolong One | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 上海七宝万科广场 | Qibao Vanke Plaza Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/独立知名项目 | VERIFIED |
| 杭州西溪印象城 | Xixi InCity Hangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/印力系 | VERIFIED |
| 杭州奥体印象城 | Olympic InCity Hangzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/印力系 | VERIFIED |
| 宁波印象城 | InCity Ningbo | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/印力系 | VERIFIED |
| 温州印象城 | InCity Wenzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/印力系 | VERIFIED |
| 上海南翔印象城MEGA | Nanxiang InCity MEGA Shanghai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/印力系 | VERIFIED |
| 常州吾悦国际广场 | Wuyue Plaza Changzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/吾悦系 | VERIFIED |
| 南京江宁吾悦广场 | Wuyue Plaza Jiangning Nanjing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/吾悦系 | VERIFIED |
| 苏州高新区吾悦广场 | Wuyue Plaza Suzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/吾悦系 | VERIFIED |
| 昆明呈贡吾悦广场 | Wuyue Plaza Chenggong Kunming | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/吾悦系 | VERIFIED |
| 北京CBD万达广场 | Wanda Plaza Beijing CBD | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 北京石景山万达广场 | Wanda Plaza Beijing Shijingshan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 北京通州万达广场 | Wanda Plaza Beijing Tongzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 北京槐房万达广场 | Wanda Plaza Beijing Huaifang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 北京双桥万达广场 | Wanda Plaza Beijing Shuangqiao | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 北京丰台万达广场 | Wanda Plaza Beijing Fengtai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 北京五棵松万达广场 | Wanda Plaza Beijing Wukesong | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 北京东坝万达广场 | Wanda Plaza Beijing Dongba | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 北京延庆万达广场 | Wanda Plaza Beijing Yanqing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 北京平谷万达广场 | Wanda Plaza Beijing Pinggu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 北京怀柔青春万达广场 | Wanda Plaza Beijing Huairou Qingchun | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 北京昌平乐多港万达广场 | Wanda Plaza Beijing Changping Ledougang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 天津河东万达广场 | Wanda Plaza Tianjin Hedong | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 天津东丽万达广场 | Wanda Plaza Tianjin Dongli | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 天津滨海万达广场 | Wanda Plaza Tianjin Binhai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 天津武清福源万达广场 | Wanda Plaza Tianjin Wuqing Fuyuan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 天津蓟州万达广场 | Wanda Plaza Tianjin Jizhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 天津大港万达广场 | Wanda Plaza Tianjin Dagang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 上海五角场万达广场 | Wanda Plaza Shanghai Wujiaochang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 上海宝山万达广场 | Wanda Plaza Shanghai Baoshan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 上海江桥万达广场 | Wanda Plaza Shanghai Jiangqiao | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 上海周浦万达广场 | Wanda Plaza Shanghai Zhoupu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 上海松江万达广场 | Wanda Plaza Shanghai Songjiang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 上海金山万达广场 | Wanda Plaza Shanghai Jinshan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 上海闵行颛桥万达广场 | Wanda Plaza Shanghai Minhang Zhuanqiao | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 上海青浦万达茂 | Wanda Mall Shanghai Qingpu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 上海崇明万达广场 | Wanda Plaza Shanghai Chongming | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 上海临港万达广场 | Wanda Plaza Shanghai Lingang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 上海马桥万达广场 | Wanda Plaza Shanghai Maqiao | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 上海浦江万达广场 | Wanda Plaza Shanghai Pujiang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 重庆南坪万达广场 | Wanda Plaza Chongqing Nanping | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 重庆万州万达广场 | Wanda Plaza Chongqing Wanzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 重庆巴南万达广场 | Wanda Plaza Chongqing Banan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 重庆永川万达广场 | Wanda Plaza Chongqing Yongchuan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 重庆沙坪坝万达广场 | Wanda Plaza Chongqing Shapingba | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 重庆大渡口万达广场 | Wanda Plaza Chongqing Dadukou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 重庆涪陵万达广场 | Wanda Plaza Chongqing Fuling | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 重庆北碚万达广场 | Wanda Plaza Chongqing Beibei | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 重庆铜梁万达广场 | Wanda Plaza Chongqing Tongliang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 重庆綦江万达广场 | Wanda Plaza Chongqing Qijiang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 石家庄裕华万达广场 | Wanda Plaza Shijiazhuang Yuhua | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 石家庄长安万达广场 | Wanda Plaza Shijiazhuang Chang'an | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 唐山路南万达广场 | Wanda Plaza Tangshan Lunan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 秦皇岛海港万达广场 | Wanda Plaza Qinhuangdao Haigang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 廊坊广阳万达广场 | Wanda Plaza Langfang Guangyang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 邯郸邯山万达广场 | Wanda Plaza Handan Hanshan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 保定嘉德万达广场 | Wanda Plaza Baoding Jiade | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 沧州任丘万达广场 | Wanda Plaza Cangzhou Renqiu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 郑州二七万达广场 | Wanda Plaza Zhengzhou Erqi | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 郑州中原万达广场 | Wanda Plaza Zhengzhou Zhongyuan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 郑州惠济万达广场 | Wanda Plaza Zhengzhou Huiji | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 郑州高新万达广场 | Wanda Plaza Zhengzhou Gaoxin | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 洛阳涧西万达广场 | Wanda Plaza Luoyang Jianxi | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 开封龙亭万达广场 | Wanda Plaza Kaifeng Longting | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 许昌魏都万达广场 | Wanda Plaza Xuchang Weidu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 安阳文峰万达广场 | Wanda Plaza Anyang Wenfeng | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 新乡牧野万达广场 | Wanda Plaza Xinxiang Muye | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 周口开元万达广场 | Wanda Plaza Zhoukou Kaiyuan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 昆明西山万达广场 | Wanda Plaza Kunming Xishan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 昆明呈贡万达广场 | Wanda Plaza Kunming Chenggong | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 曲靖麒麟万达广场 | Wanda Plaza Qujing Qilin | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 沈阳太原街万达广场 | Wanda Plaza Shenyang Taiyuanjie | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 沈阳铁西万达广场 | Wanda Plaza Shenyang Tiexi | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 沈阳北一路万达广场 | Wanda Plaza Shenyang Beiyilu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 沈阳奥体万达广场 | Wanda Plaza Shenyang Aoti | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 沈阳沈北万达广场 | Wanda Plaza Shenyang Shenbei | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 大连高新万达广场 | Wanda Plaza Dalian Gaoxin | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 大连开发区万达广场 | Wanda Plaza Dalian Kaifaqu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 大连甘井子万达广场 | Wanda Plaza Dalian Ganjingzi | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 丹东万达广场 | Wanda Plaza Dandong | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 锦州万达广场 | Wanda Plaza Jinzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 鞍山高新万达广场 | Wanda Plaza Anshan Gaoxin | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 营口站前万达广场 | Wanda Plaza Yingkou Zhanqian | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 哈尔滨香坊万达广场 | Wanda Plaza Harbin Xiangfang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 哈尔滨哈西万达广场 | Wanda Plaza Harbin Haxi | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 哈尔滨哈东万达广场 | Wanda Plaza Harbin Hadong | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 齐齐哈尔万达广场 | Wanda Plaza Qiqihar | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 佳木斯万达广场 | Wanda Plaza Jiamusi | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 牡丹江万达广场 | Wanda Plaza Mudanjiang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 长沙开福万达广场 | Wanda Plaza Changsha Kaifu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 长沙银盆岭万达广场 | Wanda Plaza Changsha Yinpenling | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 株洲神农万达广场 | Wanda Plaza Zhuzhou Shennong | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 湘潭岳塘万达广场 | Wanda Plaza Xiangtan Yuetang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 衡阳蒸湘万达广场 | Wanda Plaza Hengyang Zhengxiang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 常德武陵万达广场 | Wanda Plaza Changde Wuling | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 怀化鹤城万达广场 | Wanda Plaza Huaihua Hecheng | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 益阳赫山万达广场 | Wanda Plaza Yiyang Heshan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 合肥包河万达广场 | Wanda Plaza Hefei Baohe | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 合肥天鹅湖万达广场 | Wanda Plaza Hefei Tian'ehu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 合肥瑶海万达广场 | Wanda Plaza Hefei Yaohai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 芜湖镜湖万达广场 | Wanda Plaza Wuhu Jinghu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 蚌埠蚌山万达广场 | Wanda Plaza Bengbu Bangshan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 阜阳颍州万达广场 | Wanda Plaza Fuyang Yingzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 马鞍山雨山万达广场 | Wanda Plaza Ma'anshan Yushan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 淮南国庆路万达广场 | Wanda Plaza Huainan Guoqinglu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 六安金安万达广场 | Wanda Plaza Lu'an Jin'an | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 滁州南谯万达广场 | Wanda Plaza Chuzhou Nanjiao | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 济南魏家庄万达广场 | Wanda Plaza Jinan Weijiazhuang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 济南高新万达广场 | Wanda Plaza Jinan Gaoxin | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 青岛CBD万达广场 | Wanda Plaza Qingdao CBD | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 青岛李沧万达广场 | Wanda Plaza Qingdao Licang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 青岛西海岸万达广场 | Wanda Plaza Qingdao Xihaian | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 烟台芝罘万达广场 | Wanda Plaza Yantai Zhifu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 烟台开发区万达广场 | Wanda Plaza Yantai Kaifaqu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 潍坊奎文万达广场 | Wanda Plaza Weifang Kuiwen | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 临沂滨河万达广场 | Wanda Plaza Linyi Binhe | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 淄博富力万达广场 | Wanda Plaza Zibo Fuli | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 泰安泰山万达广场 | Wanda Plaza Tai'an Taishan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 德州德城万达广场 | Wanda Plaza Dezhou Decheng | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 南京建邺万达广场 | Wanda Plaza Nanjing Jianye | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 南京江宁万达广场 | Wanda Plaza Nanjing Jiangning | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 苏州平江万达广场 | Wanda Plaza Suzhou Pingjiang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 苏州吴中万达广场 | Wanda Plaza Suzhou Wuzhong | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 无锡滨湖万达广场 | Wanda Plaza Wuxi Binhu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 无锡惠山万达广场 | Wanda Plaza Wuxi Huishan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 常州新北万达广场 | Wanda Plaza Changzhou Xinbei | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 徐州云龙万达广场 | Wanda Plaza Xuzhou Yunlong | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 南通港闸万达广场 | Wanda Plaza Nantong Gangzha | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 扬州邗江万达广场 | Wanda Plaza Yangzhou Hanjiang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 盐城盐都万达广场 | Wanda Plaza Yancheng Yandu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 镇江润州万达广场 | Wanda Plaza Zhenjiang Runzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 宁波鄞州万达广场 | Wanda Plaza Ningbo Yinzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 宁波江北万达广场 | Wanda Plaza Ningbo Jiangbei | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 杭州拱墅万达广场 | Wanda Plaza Hangzhou Gongshu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 杭州余杭万达广场 | Wanda Plaza Hangzhou Yuhang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 温州龙湾万达广场 | Wanda Plaza Wenzhou Longwan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 绍兴柯桥万达广场 | Wanda Plaza Shaoxing Keqiao | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 嘉兴南湖万达广场 | Wanda Plaza Jiaxing Nanhu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 金华义乌万达广场 | Wanda Plaza Jinhua Yiwu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 南昌红谷滩万达广场 | Wanda Plaza Nanchang Honggutan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 南昌西湖万达广场 | Wanda Plaza Nanchang Xihu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 南昌青山湖万达广场 | Wanda Plaza Nanchang Qingshanhu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 上饶万达广场 | Wanda Plaza Shangrao | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 九江濂溪万达广场 | Wanda Plaza Jiujiang Lianxi | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 武汉楚河汉街万达广场 | Wanda Plaza Wuhan Chuhe Hanjie | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 武汉经开万达广场 | Wanda Plaza Wuhan Jingkai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 武汉菱角湖万达广场 | Wanda Plaza Wuhan Lingjiaohu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 武汉汉阳万达广场 | Wanda Plaza Wuhan Hanyang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 武汉东西湖万达广场 | Wanda Plaza Wuhan Dongxihu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 襄阳樊城万达广场 | Wanda Plaza Xiangyang Fancheng | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 宜昌伍家岗万达广场 | Wanda Plaza Yichang Wujiagang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 荆州万达广场 | Wanda Plaza Jingzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 太原龙湖万达广场 | Wanda Plaza Taiyuan Longhu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 太原龙城万达广场 | Wanda Plaza Taiyuan Longcheng | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 大同平城万达广场 | Wanda Plaza Datong Pingcheng | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 运城盐湖万达广场 | Wanda Plaza Yuncheng Yanhu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 长治高新万达广场 | Wanda Plaza Changzhi Gaoxin | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 呼和浩特赛罕万达广场 | Wanda Plaza Hohhot Saihan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 包头青山万达广场 | Wanda Plaza Baotou Qingshan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 鄂尔多斯万达广场 | Wanda Plaza Ordos | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 赤峰红山万达广场 | Wanda Plaza Chifeng Hongshan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 西安李家村万达广场 | Wanda Plaza Xi'an Lijiacun | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 西安大明宫万达广场 | Wanda Plaza Xi'an Daminggong | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 西安高新万达广场 | Wanda Plaza Xi'an Gaoxin | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 咸阳秦都万达广场 | Wanda Plaza Xianyang Qindu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 渭南临渭万达广场 | Wanda Plaza Weinan Linwei | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 乌鲁木齐经开万达广场 | Wanda Plaza Urumqi Jingkai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 乌鲁木齐德汇万达广场 | Wanda Plaza Urumqi Dehui | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 乌鲁木齐高新万达广场 | Wanda Plaza Urumqi Gaoxin | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 喀什万达广场 | Wanda Plaza Kashgar | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 长春重庆路万达广场 | Wanda Plaza Changchun Chongqinglu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 长春红旗街万达广场 | Wanda Plaza Changchun Hongqijie | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 吉林昌邑万达广场 | Wanda Plaza Jilin City Changyi | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 延吉万达广场 | Wanda Plaza Yanji | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 福州仓山浦上万达广场 | Wanda Plaza Fuzhou Cangshan Pushang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 福州金融街万达广场 | Wanda Plaza Fuzhou Jinrongjie | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 泉州浦西万达广场 | Wanda Plaza Quanzhou Puxi | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 泉州晋江万达广场 | Wanda Plaza Quanzhou Jinjiang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 厦门湖里万达广场 | Wanda Plaza Xiamen Huli | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 厦门集美万达广场 | Wanda Plaza Xiamen Jimei | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 莆田城厢万达广场 | Wanda Plaza Putian Chengxiang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 漳州碧湖万达广场 | Wanda Plaza Zhangzhou Bihu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 贵阳观山湖万达广场 | Wanda Plaza Guiyang Guanshanhu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 贵阳云岩万达广场 | Wanda Plaza Guiyang Yunyan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 六盘水钟山万达广场 | Wanda Plaza Liupanshui Zhongshan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 凯里万达广场 | Wanda Plaza Kaili | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 广州白云万达广场 | Wanda Plaza Guangzhou Baiyun | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 广州番禺万达广场 | Wanda Plaza Guangzhou Panyu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 广州增城万达广场 | Wanda Plaza Guangzhou Zengcheng | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 广州南沙万达广场 | Wanda Plaza Guangzhou Nansha | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 广州萝岗万达广场 | Wanda Plaza Guangzhou Luogang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 深圳龙岗万达广场 | Wanda Plaza Shenzhen Longgang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 深圳宝安福城万达广场 | Wanda Plaza Shenzhen Bao'an Fucheng | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 东莞长安万达广场 | Wanda Plaza Dongguan Chang'an | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 佛山南海万达广场 | Wanda Plaza Foshan Nanhai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 江门蓬江万达广场 | Wanda Plaza Jiangmen Pengjiang | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 成都金牛万达广场 | Wanda Plaza Chengdu Jinniu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 成都锦华路万达广场 | Wanda Plaza Chengdu Jinghualu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 成都蜀都万达广场 | Wanda Plaza Chengdu Shudu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 成都双流万达广场 | Wanda Plaza Chengdu Shuangliu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 绵阳涪城万达广场 | Wanda Plaza Mianyang Fucheng | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 绵阳经开万达广场 | Wanda Plaza Mianyang Jingkai | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 宜宾万达广场 | Wanda Plaza Yibin | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 泸州龙马潭万达广场 | Wanda Plaza Luzhou Longmatan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 南宁青秀万达广场 | Wanda Plaza Nanning Qingxiu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 南宁安吉万达广场 | Wanda Plaza Nanning Anji | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 南宁万达茂 | Wanda Mall Nanning | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 柳州城中万达广场 | Wanda Plaza Liuzhou Chengzhong | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 桂林七星万达广场 | Wanda Plaza Guilin Qixing | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 银川金凤万达广场 | Wanda Plaza Yinchuan Jinfeng | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 银川西夏万达广场 | Wanda Plaza Yinchuan Xixia | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 兰州城关万达广场 | Wanda Plaza Lanzhou Chengguan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 天水秦州万达广场 | Wanda Plaza Tianshui Qinzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 酒泉肃州万达广场 | Wanda Plaza Jiuquan Suzhou | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 西宁海湖万达广场 | Wanda Plaza Xining Haihu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 西宁北川万达广场 | Wanda Plaza Xining Beichuan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 海口秀英万达广场 | Wanda Plaza Haikou Xiuying | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 拉萨城关万达广场 | Wanda Plaza Lhasa Chengguan | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 拉萨柳梧万达广场 | Wanda Plaza Lhasa Liuwu | 购物中心 | 商业主体宇宙/中国境内/购物中心与百货/万达系 | VERIFIED |
| 上海迪士尼乐园 | Shanghai Disneyland | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/迪士尼系 | VERIFIED |
| 香港迪士尼乐园 | Hong Kong Disneyland | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/迪士尼系 | VERIFIED |
| 北京环球度假区 | Universal Beijing Resort | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/环球系 | VERIFIED |
| 广州长隆旅游度假区 | Chimelong Tourist Resort Guangzhou | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/长隆系 | VERIFIED |
| 珠海长隆海洋王国 | Chimelong Ocean Kingdom Zhuhai | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/长隆系 | VERIFIED |
| 天津方特欢乐世界 | Fantawild Adventure Tianjin | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 天津方特水上乐园 | Fantawild Water Park Tianjin | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 邯郸方特国色春秋 | Fantawild Glorious History Handan | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 大同方特欢乐世界 | Fantawild Adventure Datong | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 沈阳方特欢乐世界 | Fantawild Adventure Shenyang | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 台州方特狂野大陆 | Fantawild Wild Land Taizhou | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 台州方特水上乐园 | Fantawild Water Park Taizhou | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 临海熊出没欢乐港湾 | Boonie Bears Happy Harbor Linhai | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 芜湖方特梦幻王国 | Fantawild Dreamland Wuhu | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 芜湖方特东方神画 | Fantawild Oriental Heritage Wuhu | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 芜湖方特水上乐园 | Fantawild Water Park Wuhu | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 厦门方特梦幻王国 | Fantawild Dreamland Xiamen | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 厦门方特东方神画 | Fantawild Oriental Heritage Xiamen | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 厦门方特水上乐园 | Fantawild Water Park Xiamen | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 赣州方特东方欲晓 | Fantawild Oriental Dawn Ganzhou | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 宜春熊出没乐园 | Boonie Bears Land Yichun | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 济南方特东方神话 | Fantawild Oriental Mythology Jinan | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 济宁方特东方欲晓 | Fantawild Oriental Dawn Jining | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 泰安方特欢乐世界 | Fantawild Adventure Tai'an | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 郑州方特欢乐世界 | Fantawild Adventure Zhengzhou | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 长沙方特东方神画 | Fantawild Oriental Heritage Changsha | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 株洲方特欢乐世界 | Fantawild Adventure Zhuzhou | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 南宁方特东盟神画 | Fantawild ASEAN Legend Nanning | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 自贡方特恐龙王国 | Fantawild Dinosaur Kingdom Zigong | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 绵阳方特东方神画 | Fantawild Oriental Heritage Mianyang | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 嘉峪关方特欢乐世界 | Fantawild Adventure Jiayuguan | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 嘉峪关方特丝路神画 | Fantawild Silk Road Dream Jiayuguan | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 荆州方特东方神画 | Fantawild Oriental Heritage Jingzhou | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 鹰潭方特东方神画 | Fantawild Oriental Heritage Yingtan | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 宁波方特东方神画 | Fantawild Oriental Heritage Ningbo | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 宁波方特东方欲晓 | Fantawild Oriental Dawn Ningbo | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/方特系 | VERIFIED |
| 深圳欢乐谷 | Happy Valley Shenzhen | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/华侨城系 | VERIFIED |
| 北京欢乐谷 | Happy Valley Beijing | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/华侨城系 | VERIFIED |
| 上海欢乐谷 | Happy Valley Shanghai | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/华侨城系 | VERIFIED |
| 成都欢乐谷 | Happy Valley Chengdu | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/华侨城系 | VERIFIED |
| 武汉欢乐谷 | Happy Valley Wuhan | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/华侨城系 | VERIFIED |
| 天津欢乐谷 | Happy Valley Tianjin | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/华侨城系 | VERIFIED |
| 重庆欢乐谷 | Happy Valley Chongqing | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/华侨城系 | VERIFIED |
| 南京欢乐谷 | Happy Valley Nanjing | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/华侨城系 | VERIFIED |
| 深圳世界之窗 | Window of the World Shenzhen | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/华侨城系 | VERIFIED |
| 长沙世界之窗 | Window of the World Changsha | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/华侨城系 | VERIFIED |
| 深圳锦绣中华民俗村 | Splendid China Folk Park Shenzhen | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/华侨城系 | VERIFIED |
| 深圳东部华侨城 | OCT East Shenzhen | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/华侨城系 | VERIFIED |
| 上海海昌海洋公园 | Haichang Ocean Park Shanghai | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/海昌系 | VERIFIED |
| 天津海昌极地海洋公园 | Haichang Polar Ocean Park Tianjin | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/海昌系 | VERIFIED |
| 青岛海昌极地海洋公园 | Haichang Polar Ocean Park Qingdao | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/海昌系 | VERIFIED |
| 大连海昌发现王国 | Haichang Discovery Kingdom Dalian | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/海昌系 | VERIFIED |
| 大连老虎滩海洋公园 | Laohutan Ocean Park Dalian | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/海昌系 | VERIFIED |
| 成都海昌极地海洋公园 | Haichang Polar Ocean Park Chengdu | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/海昌系 | VERIFIED |
| 武汉海昌极地海洋公园 | Haichang Polar Ocean Park Wuhan | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/海昌系 | VERIFIED |
| 三亚海昌梦幻海洋不夜城 | Haichang Fantasy Ocean Night City Sanya | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/海昌系 | VERIFIED |
| 郑州海昌海洋公园 | Haichang Ocean Park Zhengzhou | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/海昌系 | VERIFIED |
| 广州融创文旅城 | Sunac Cultural Tourism City Guangzhou | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/融创系 | VERIFIED |
| 无锡融创文旅城 | Sunac Cultural Tourism City Wuxi | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/融创系 | VERIFIED |
| 成都融创文旅城 | Sunac Cultural Tourism City Chengdu | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/融创系 | VERIFIED |
| 重庆融创文旅城 | Sunac Cultural Tourism City Chongqing | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/融创系 | VERIFIED |
| 昆明融创文旅城 | Sunac Cultural Tourism City Kunming | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/融创系 | VERIFIED |
| 济南融创文旅城 | Sunac Cultural Tourism City Jinan | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/融创系 | VERIFIED |
| 哈尔滨融创乐园 | Sunac Land Harbin | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/融创系 | VERIFIED |
| 合肥融创乐园 | Sunac Land Hefei | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/融创系 | VERIFIED |
| 南昌融创乐园 | Sunac Land Nanchang | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/融创系 | VERIFIED |
| 桂林融创文旅城 | Sunac Cultural Tourism City Guilin | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/融创系 | VERIFIED |
| 杭州宋城 | Songcheng Hangzhou | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/宋城系 | VERIFIED |
| 三亚宋城千古情 | Sanya Eternal Love | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/宋城系 | VERIFIED |
| 丽江千古情 | Lijiang Eternal Love | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/宋城系 | VERIFIED |
| 九寨千古情 | Jiuzhai Eternal Love | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/宋城系 | VERIFIED |
| 桂林千古情 | Guilin Eternal Love | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/宋城系 | VERIFIED |
| 张家界千古情 | Zhangjiajie Eternal Love | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/宋城系 | VERIFIED |
| 西安千古情 | Xi'an Eternal Love | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/宋城系 | VERIFIED |
| 上海锦江乐园 | Jinjiang Action Park Shanghai | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/其他知名乐园 | VERIFIED |
| 常州中华恐龙园 | China Dinosaur Park Changzhou | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/其他知名乐园 | VERIFIED |
| 苏州乐园森林世界 | Suzhou Amusement Land Forest World | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/其他知名乐园 | VERIFIED |
| 北京石景山游乐园 | Shijingshan Amusement Park Beijing | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/其他知名乐园 | VERIFIED |
| 成都国色天乡乐园 | Guose Tianxiang Chengdu | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/其他知名乐园 | VERIFIED |
| 西安乐华欢乐世界 | Lewua Happy World Xi'an | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/其他知名乐园 | VERIFIED |
| 昆明七彩云南欢乐世界 | Colorful Yunnan Happy World Kunming | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/其他知名乐园 | VERIFIED |
| 桂林乐满地主题乐园 | Leman Resort Guilin | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/其他知名乐园 | VERIFIED |
| 柳州卡乐星球欢乐世界 | Kale Planet Liuzhou | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/其他知名乐园 | VERIFIED |
| 福州贵安欢乐世界 | Guian Happy World Fuzhou | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/其他知名乐园 | VERIFIED |
| 海口长影环球100奇幻乐园 | Changying Global 100 Haikou | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/其他知名乐园 | VERIFIED |
| 三亚亚特兰蒂斯水世界 | Atlantis Aquaventure Sanya | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/其他知名乐园 | VERIFIED |
| 哈尔滨极地公园 | Harbin Polar Park | 主题乐园 | 商业主体宇宙/中国境内/主题乐园与游乐场/其他知名乐园 | VERIFIED |

> 共 445 条商业主体

### 20.3 品牌主体全量（brand → BMP，136 条）

| name_zh | name_en | industry | 层级路径 |
|---------|---------|----------|----------|
| 珀莱雅 | Proya | 美妆 | 品牌主体宇宙/中国优秀品牌 |
| 薇诺娜 | Winona | 美妆 | 品牌主体宇宙/中国优秀品牌 |
| 花西子 | Florasis | 美妆 | 品牌主体宇宙/中国优秀品牌 |
| 完美日记 | Perfect Diary | 美妆 | 品牌主体宇宙/中国优秀品牌 |
| 珂拉琪 | Colorkey | 美妆 | 品牌主体宇宙/中国优秀品牌 |
| 橘朵 | Judydoll | 美妆 | 品牌主体宇宙/中国优秀品牌 |
| 自然堂 | Chando | 美妆 | 品牌主体宇宙/中国优秀品牌 |
| 百雀羚 | Pechoin | 美妆 | 品牌主体宇宙/中国优秀品牌 |
| 相宜本草 | Inoherb | 美妆 | 品牌主体宇宙/中国优秀品牌 |
| 丸美 | Marubi | 美妆 | 品牌主体宇宙/中国优秀品牌 |
| 上美 | Shanghai Shangmei | 美妆 | 品牌主体宇宙/中国优秀品牌 |
| 李宁 | Li-Ning | 服装 | 品牌主体宇宙/中国优秀品牌 |
| 安踏 | Anta | 服装 | 品牌主体宇宙/中国优秀品牌 |
| 波司登 | Bosideng | 服装 | 品牌主体宇宙/中国优秀品牌 |
| 太平鸟 | Peacebird | 服装 | 品牌主体宇宙/中国优秀品牌 |
| 江南布衣 | JNBY | 服装 | 品牌主体宇宙/中国优秀品牌 |
| INXX | INXX | 服装 | 品牌主体宇宙/中国优秀品牌 |
| 元气森林 | Genki Forest | 食品 | 品牌主体宇宙/中国优秀品牌 |
| 农夫山泉 | Nongfu Spring | 食品 | 品牌主体宇宙/中国优秀品牌 |
| 三只松鼠 | Three Squirrels | 食品 | 品牌主体宇宙/中国优秀品牌 |
| 良品铺子 | Bestore | 食品 | 品牌主体宇宙/中国优秀品牌 |
| 卫龙 | Weilong | 食品 | 品牌主体宇宙/中国优秀品牌 |
| 海天 | Haitian | 食品 | 品牌主体宇宙/中国优秀品牌 |
| 老干妈 | Lao Gan Ma | 食品 | 品牌主体宇宙/中国优秀品牌 |
| 伊利 | Yili | 食品 | 品牌主体宇宙/中国优秀品牌 |
| 蒙牛 | Mengniu | 食品 | 品牌主体宇宙/中国优秀品牌 |
| 安慕希 | Ambrosial | 食品 | 品牌主体宇宙/中国优秀品牌 |
| 华为 | Huawei | 科技消费品 | 品牌主体宇宙/中国优秀品牌 |
| 小米 | Xiaomi | 科技消费品 | 品牌主体宇宙/中国优秀品牌 |
| 大疆 | DJI | 科技消费品 | 品牌主体宇宙/中国优秀品牌 |
| 科沃斯 | Ecovacs | 科技消费品 | 品牌主体宇宙/中国优秀品牌 |
| Anker | Anker | 科技消费品 | 品牌主体宇宙/中国优秀品牌 |
| 全聚德 | Quanjude | 老字号 | 品牌主体宇宙/中国优秀品牌 |
| 狗不理 | Goubuli | 老字号 | 品牌主体宇宙/中国优秀品牌 |
| 陶陶居 | Tao Tao Ju | 老字号 | 品牌主体宇宙/中国优秀品牌 |
| 广州酒家 | Guangzhou Restaurant | 老字号 | 品牌主体宇宙/中国优秀品牌 |
| 同仁堂 | Tongrentang | 老字号 | 品牌主体宇宙/中国优秀品牌 |
| 云南白药 | Yunnan Baiyao | 老字号 | 品牌主体宇宙/中国优秀品牌 |
| 王老吉 | Wanglaoji | 老字号 | 品牌主体宇宙/中国优秀品牌 |
| 五芳斋 | Wufangzhai | 老字号 | 品牌主体宇宙/中国优秀品牌 |
| 知味观 | Zhiweiguan | 老字号 | 品牌主体宇宙/中国优秀品牌 |
| 楼外楼 | Louwailou | 老字号 | 品牌主体宇宙/中国优秀品牌 |
| 松鹤楼 | Songhelou | 老字号 | 品牌主体宇宙/中国优秀品牌 |
| 胡庆余堂 | Huqingyutang | 老字号 | 品牌主体宇宙/中国优秀品牌 |
| 陈李济 | Chenliji | 老字号 | 品牌主体宇宙/中国优秀品牌 |
| 敬修堂 | Jingxiutang | 老字号 | 品牌主体宇宙/中国优秀品牌 |
| Uma Wang | Uma Wang | 独立设计师 | 品牌主体宇宙/中国小众品牌 |
| 陈鹏 | Chen Peng | 独立设计师 | 品牌主体宇宙/中国小众品牌 |
| 8on8 | 8on8 | 独立设计师 | 品牌主体宇宙/中国小众品牌 |
| Pronounce | Pronounce | 独立设计师 | 品牌主体宇宙/中国小众品牌 |
| Short Sentence | Short Sentence | 独立设计师 | 品牌主体宇宙/中国小众品牌 |
| Susan Fang | Susan Fang | 独立设计师 | 品牌主体宇宙/中国小众品牌 |
| Shushu/Tong | Shushu/Tong | 独立设计师 | 品牌主体宇宙/中国小众品牌 |
| Rui Zhou | Rui Zhou | 独立设计师 | 品牌主体宇宙/中国小众品牌 |
| Angel Chen | Angel Chen | 独立设计师 | 品牌主体宇宙/中国小众品牌 |
| Feng Chen Wang | Feng Chen Wang | 独立设计师 | 品牌主体宇宙/中国小众品牌 |
| Marrknull | Marrknull | 独立设计师 | 品牌主体宇宙/中国小众品牌 |
| Xuzhi | Xuzhi | 独立设计师 | 品牌主体宇宙/中国小众品牌 |
| 观夏 | To Summer | 香氛 | 品牌主体宇宙/中国小众品牌 |
| 闻献 | Documents | 香氛 | 品牌主体宇宙/中国小众品牌 |
| Blank Me | BlankMe | 护肤 | 品牌主体宇宙/中国小众品牌 |
| Rever | Rever | 个护 | 品牌主体宇宙/中国小众品牌 |
| Manner | Manner | 咖啡 | 品牌主体宇宙/中国小众品牌 |
| Seesaw | Seesaw | 咖啡 | 品牌主体宇宙/中国小众品牌 |
| M Stand | M Stand | 咖啡 | 品牌主体宇宙/中国小众品牌 |
| Grid Coffee | Grid Coffee | 咖啡 | 品牌主体宇宙/中国小众品牌 |
| Louis Vuitton | Louis Vuitton | 奢侈品 | 品牌主体宇宙/境外品牌在中国营业 |
| Chanel | Chanel | 奢侈品 | 品牌主体宇宙/境外品牌在中国营业 |
| Dior | Dior | 奢侈品 | 品牌主体宇宙/境外品牌在中国营业 |
| Gucci | Gucci | 奢侈品 | 品牌主体宇宙/境外品牌在中国营业 |
| Hermès | Hermès | 奢侈品 | 品牌主体宇宙/境外品牌在中国营业 |
| Cartier | Cartier | 奢侈品 | 品牌主体宇宙/境外品牌在中国营业 |
| Prada | Prada | 奢侈品 | 品牌主体宇宙/境外品牌在中国营业 |
| Tiffany | Tiffany & Co. | 奢侈品 | 品牌主体宇宙/境外品牌在中国营业 |
| Nike | Nike | 运动 | 品牌主体宇宙/境外品牌在中国营业 |
| Adidas | Adidas | 运动 | 品牌主体宇宙/境外品牌在中国营业 |
| Puma | Puma | 运动 | 品牌主体宇宙/境外品牌在中国营业 |
| New Balance | New Balance | 运动 | 品牌主体宇宙/境外品牌在中国营业 |
| Salomon | Salomon | 运动户外 | 品牌主体宇宙/境外品牌在中国营业 |
| Arc'teryx | Arc'teryx | 运动户外 | 品牌主体宇宙/境外品牌在中国营业 |
| lululemon | lululemon | 运动 | 品牌主体宇宙/境外品牌在中国营业 |
| Apple | Apple | 科技 | 品牌主体宇宙/境外品牌在中国营业 |
| Dyson | Dyson | 科技 | 品牌主体宇宙/境外品牌在中国营业 |
| DJI | DJI | 科技 | 品牌主体宇宙/境外品牌在中国营业 |
| Samsung | Samsung | 科技 | 品牌主体宇宙/境外品牌在中国营业 |
| Sony | Sony | 科技 | 品牌主体宇宙/境外品牌在中国营业 |
| Bose | Bose | 科技 | 品牌主体宇宙/境外品牌在中国营业 |
| Zara | Zara | 快时尚 | 品牌主体宇宙/境外品牌在中国营业 |
| H&M | H&M | 快时尚 | 品牌主体宇宙/境外品牌在中国营业 |
| Uniqlo | Uniqlo | 快时尚 | 品牌主体宇宙/境外品牌在中国营业 |
| COS | COS | 快时尚 | 品牌主体宇宙/境外品牌在中国营业 |
| Mango | Mango | 快时尚 | 品牌主体宇宙/境外品牌在中国营业 |
| L'Oréal | L'Oréal | 美妆 | 品牌主体宇宙/境外品牌在中国营业 |
| Estée Lauder | Estée Lauder | 美妆 | 品牌主体宇宙/境外品牌在中国营业 |
| Shiseido | Shiseido | 美妆 | 品牌主体宇宙/境外品牌在中国营业 |
| Lancôme | Lancôme | 美妆 | 品牌主体宇宙/境外品牌在中国营业 |
| Louis Vuitton | Louis Vuitton | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Dior | Dior | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Fendi | Fendi | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Celine | Celine | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Loewe | Loewe | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Givenchy | Givenchy | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Bvlgari | Bvlgari | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Tiffany | Tiffany & Co. | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Gucci | Gucci | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Saint Laurent | Saint Laurent | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Bottega Veneta | Bottega Veneta | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Balenciaga | Balenciaga | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Alexander McQueen | Alexander McQueen | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Cartier | Cartier | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Van Cleef & Arpels | Van Cleef & Arpels | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Jaeger-LeCoultre | Jaeger-LeCoultre | 奢侈品 | 品牌主体宇宙/全球品牌 |
| IWC | IWC | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Montblanc | Montblanc | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Piaget | Piaget | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Vacheron Constantin | Vacheron Constantin | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Chloé | Chloe | 奢侈品 | 品牌主体宇宙/全球品牌 |
| Coach | Coach | 轻奢 | 品牌主体宇宙/全球品牌 |
| Kate Spade | Kate Spade | 轻奢 | 品牌主体宇宙/全球品牌 |
| Tory Burch | Tory Burch | 轻奢 | 品牌主体宇宙/全球品牌 |
| Furla | Furla | 轻奢 | 品牌主体宇宙/全球品牌 |
| Longchamp | Longchamp | 轻奢 | 品牌主体宇宙/全球品牌 |
| Patagonia | Patagonia | 运动户外 | 品牌主体宇宙/全球品牌 |
| The North Face | The North Face | 运动户外 | 品牌主体宇宙/全球品牌 |
| On | On | 运动户外 | 品牌主体宇宙/全球品牌 |
| Hoka | Hoka | 运动户外 | 品牌主体宇宙/全球品牌 |
| Dior Beauty | Dior Beauty | 美妆 | 品牌主体宇宙/全球品牌 |
| Guerlain | Guerlain | 美妆 | 品牌主体宇宙/全球品牌 |
| YSL Beauty | Yves Saint Laurent Beaute | 美妆 | 品牌主体宇宙/全球品牌 |
| Giorgio Armani Beauty | Giorgio Armani Beauty | 美妆 | 品牌主体宇宙/全球品牌 |
| MAC | M.A.C | 美妆 | 品牌主体宇宙/全球品牌 |
| Jo Malone | Jo Malone London | 美妆 | 品牌主体宇宙/全球品牌 |
| La Mer | La Mer | 美妆 | 品牌主体宇宙/全球品牌 |
| NARS | NARS | 美妆 | 品牌主体宇宙/全球品牌 |
| Clé de Peau Beauté | Cle de Peau Beaute | 美妆 | 品牌主体宇宙/全球品牌 |
| SK-II | SK-II | 美妆 | 品牌主体宇宙/全球品牌 |

### 20.4 场内关系全量（品牌→商场，133 条）

| 品牌 | 商场 | 铺位 |
|------|------|------|
| gaga | 广州太古汇 | L302 |
| 尚莲·越南泰国料理 | 广州太古汇 | L303 |
| glance | 广州太古汇 | L304 |
| Dim bar | 广州太古汇 | L305 |
| 小山 炉端烧•鮨 | 广州太古汇 | L306 |
| 御寶閣潮州酒家 | 广州太古汇 | L307 |
| Grid Coffee | 广州太古汇 | MU16a |
| 面道鲜师 | 广州太古汇 | MU16b |
| 荔事唐 | 广州太古汇 | MU16c |
| 鮨·半藏 | 广州太古汇 | MU16e |
| 喜家德 | 广州太古汇 | MU16d |
| 熟客·星马印料理 | 广州太古汇 | MU16f |
| 太二前传 | 广州太古汇 | MU16g&h |
| 入续·糖水铺与包·臻选 | 广州太古汇 | MU16i |
| 花厨café | 广州太古汇 | MU16j |
| SONG Cafe | 广州太古汇 | MU16k |
| 九十葉 | 广州太古汇 | MU16m |
| ZAKUZAKU | 广州太古汇 | MU16l |
| 阿嬷手作 | 广州太古汇 | MU17 |
| 美奈小馆 | 广州太古汇 | MU18 |
| 鼎泰丰 | 广州太古汇 | MU19 |
| 叁木司.日式餐酒馆 | 广州太古汇 | MU20 |
| 鳗几 | 广州太古汇 | MU21 |
| 香奈儿 | 广州太古汇 |  |
| 古驰 | 广州太古汇 |  |
| 路易威登 | 广州太古汇 |  |
| 迪奥 | 广州太古汇 |  |
| 爱马仕 | 广州太古汇 |  |
| 芬迪 | 广州太古汇 |  |
| 普拉达 | 广州太古汇 |  |
| 卡地亚 | 广州太古汇 |  |
| Ole' | 广州太古汇 |  |
| 丝芙兰 | 广州太古汇 |  |
| Adidas Originals | 广州太古汇 |  |
| 星巴克 | 广州太古汇 |  |
| Godiva | 广州太古汇 |  |
| TWG Tea | 广州太古汇 |  |
| 古驰 | 北京SKP | 开业引入, 2007 |
| 普拉达 | 北京SKP | 开业引入, 2007 |
| 香奈儿 | 北京SKP | 开业引入, 2007 |
| 路易威登 | 北京SKP |  |
| 老铺黄金 | 北京SKP | 一层 |
| 星巴克臻选 | 北京SKP | 一层星意坊 |
| sacai | 北京SKP | SKP-S |
| 路易威登 | 北京三里屯太古里 | 北区独栋 |
| 迪奥 | 北京三里屯太古里 | 北区独栋 |
| 蒂芙尼 | 北京三里屯太古里 | 北区独栋 |
| 爱马仕 | 北京三里屯太古里 | 北区 |
| agnès b. | 北京三里屯太古里 | 北区, 北京首间旗舰店 |
| Canada Goose | 北京三里屯太古里 | 北区 |
| COMME des GARÇONS | 北京三里屯太古里 | 北区 |
| Emporio Armani | 北京三里屯太古里 | 北区 |
| Furla | 北京三里屯太古里 | 北区 |
| theory | 北京三里屯太古里 | 北区 |
| Dover Street Market | 北京三里屯太古里 | 北区 |
| A.P.C | 北京三里屯太古里 |  |
| adidas | 北京三里屯太古里 | 南区, 全球首家品牌中心 |
| Apple | 北京三里屯太古里 | 南区, 中国首家Apple Store |
| Puma | 北京三里屯太古里 | 南区 |
| Mango | 北京三里屯太古里 | 南区 |
| COS | 北京三里屯太古里 | 南区 |
| izzue | 北京三里屯太古里 | 南区 |
| Byredo | 北京三里屯太古里 | 南区 |
| 周生生 | 北京三里屯太古里 |  |
| Uniqlo | 北京三里屯太古里 | 西区 |
| Nike | 北京三里屯太古里 | 西区 |
| 路易威登 | 上海恒隆广场 |  |
| 香奈儿 | 上海恒隆广场 |  |
| 卡地亚 | 上海恒隆广场 |  |
| 思琳 | 上海恒隆广场 |  |
| 古驰 | 上海恒隆广场 |  |
| 圣罗兰 | 上海恒隆广场 |  |
| 爱马仕 | 上海恒隆广场 |  |
| 迪奥 | 上海恒隆广场 |  |
| 宝格丽 | 上海恒隆广场 |  |
| 芬迪 | 上海恒隆广场 |  |
| 普拉达 | 上海恒隆广场 |  |
| 范思哲 | 上海恒隆广场 |  |
| Escada | 上海恒隆广场 |  |
| 罗意威 | 上海恒隆广场 |  |
| 浪凡 | 上海恒隆广场 |  |
| 蒂芙尼 | 上海恒隆广场 |  |
| 路易威登 | 上海国金中心商场 |  |
| 香奈儿 | 上海国金中心商场 |  |
| 古驰 | 上海国金中心商场 |  |
| 爱马仕 | 上海国金中心商场 |  |
| 卡地亚 | 上海国金中心商场 |  |
| 普拉达 | 上海国金中心商场 |  |
| 蒂芙尼 | 上海国金中心商场 |  |
| 利苑 | 上海国金中心商场 | 3F |
| 路易威登 | 香港海港城 |  |
| 迪奥 | 香港海港城 |  |
| 香奈儿 | 香港海港城 |  |
| 古驰 | 香港海港城 |  |
| 普拉达 | 香港海港城 |  |
| 芬迪 | 香港海港城 |  |
| 思琳 | 香港海港城 |  |
| 罗意威 | 香港海港城 |  |
| 蒂芙尼 | 香港海港城 |  |
| 卡地亚 | 香港海港城 |  |
| 圣罗兰 | 香港海港城 |  |
| 博柏利 | 香港海港城 |  |
| 爱马仕 | 香港海港城 |  |
| Givenchy | 香港海港城 |  |
| Hugo Boss | 香港海港城 |  |
| 范思哲 | 香港海港城 |  |
| Polo Ralph Lauren | 香港海港城 |  |
| Chaumet | 香港海港城 |  |
| Chopard | 香港海港城 |  |
| Lane Crawford | 香港海港城 | 海运大厦 |
| city'super | 香港海港城 |  |
| 夏姿·陈 | 香港海港城 |  |
| Fred Perry | 香港海港城 |  |
| 香奈儿 | 香港ifc | L2/L3, 时装+美妆三处铺位 |
| 卡地亚 | 香港ifc | L2 2066 |
| 老铺黄金 | 香港ifc | L2 2024-25 |
| 周生生 | 香港ifc | L1 LA1 |
| 迪奥 | 香港ifc |  |
| 蒂芙尼 | 香港ifc |  |
| lululemon | 香港ifc | L3 |
| 丝芙兰 | 香港ifc |  |
| 利苑 | 香港ifc | L3 |
| 翡翠拉麵小籠包 | 香港ifc |  |
| Shake Shack | 香港ifc | 香港首店 |
| Lane Crawford | 香港ifc | 82000呎旗舰 |
| IWC | 香港ifc | L1/L2 腕表珠宝区 |
| 积家 | 香港ifc | L1/L2 腕表珠宝区 |
| 沛纳海 | 香港ifc | L1/L2 腕表珠宝区 |
| 帝舵 | 香港ifc | L1/L2 腕表珠宝区 |
| 万宝龙 | 香港ifc | L1/L2 腕表珠宝区 |
| 萧邦 | 香港ifc | L1/L2 腕表珠宝区 |
| 御木本 | 香港ifc | L1/L2 腕表珠宝区 |
| 塔思琦 | 香港ifc | L1/L2 腕表珠宝区 |

---

## 21. 全产品数据需求映射（J1-J8，v3 新增）

**依据**：`LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md` J1-J8 定义；`PRODUCT-LOGIC-REVIEW-20261008.md` 全能力逻辑检查。
**研究文件**：`[研究方本地，未入库] ~/workspace/global-data-research/v2/R-J2.md` 至 `R-J8`（8 份报告，每份开头设"补足的 JX 缺口"节）。

### 21.1 J1 资料与采集（U01-U05）→ R-J1

768 条主体（商业 499 / 品牌 136 / 场内关系 133），见第 20 节。补足缺口：主体登记、别名、关系、市场分类。

### 21.2 J2 CTH 商业运营（U06-U09）→ R-J2（21 条）

| 类别 | 关键源 | 零授权路径 |
|------|--------|-----------|
| 事件日历 | 太古汇官网"最新活动"、广交会 cantonfair.org.cn | 官网公开页解析（高自立） |
| 商业风险 | gsxt.gov.cn、zxgk.court.gov.cn、creditchina.gov.cn | 官方公开查询（高自立，需过验证码） |
| 消费者反馈 | 大众点评/黑猫/Trustpilot 门店级视角 | 公开页渲染采集（高自立） |
| 运营决策 | 赢商网、联商网、戴德梁行开放 PDF | 公开页/PDF（高自立） |

### 21.3 J3 BMP 品牌市场（U10-U12）→ R-J3（27 条）

| 类别 | 关键源 |
|------|--------|
| 创作者/KOL | NoxInfluencer、微播易、新榜、蝉妈妈、飞瓜、HypeAuditor、Social Blade |
| 传播趋势 | 微博/抖音/B站热榜、TikTok Creative Center、Meta Ad Library、Google Trends |
| Campaign 案例 | SocialBeta、数英网、梅花网、广告门、Marketing-Interactive、Campaign Asia |
| 竞品对比 | Interbrand、Brand Finance、SEC EDGAR、巨潮资讯 |

### 21.4 J4 提案（U13）→ R-J4

- 行业案例库 11 条（HBR、长江商学院、艾瑞、麦肯锡/BCG/贝恩等）
- **创意 Brief 升级框架**：保留现有 5 字段，补足 7 新增字段（背景/核心冲突/关键洞察/商业目标/单一核心信息/支撑理由/预算约束/验收标准），可产品化
- 提案三件套：SCQA + 金字塔 + MECE

### 21.5 J5 视频（U14）→ R-J5

- 免费素材库 11 项（Pexels、Pixabay、Coverr、Mixkit 等）
- 视频脚本 5 套模板 + 分镜字段清单
- 剪辑方法：卡点四步法、转场选用表、字幕规范

### 21.6 J6 播客（U15）→ R-J6

- 播客脚本框架：30 分钟标准单集模板、三幕式、访谈话术
- 免费音频库 7 个（Pixabay Music 首选）
- 制作方法：响度 -16 LUFS、多轨工作流

### 21.7 J7 研究与 AI（U16-U20）→ R-J7（24 条）

- 学术论文：arXiv、Semantic Scholar、OpenAlex（零授权高自立）
- 行业报告：世行 WDS、IMF SDMX、信通院、艾瑞/易观
- 技术文档：MDN、W3C、RFC、GitHub、NIST

### 21.8 J8 浏览器与四端（U21-U25）→ R-J8

- 浏览器源 7 组：维基/百度百科、gov.cn 政策库、人民网/新华网/BBC 等
- RSS 12 源已核验（BBC、Al Jazeera、DW、Guardian、NHK 等）
- 跨端：CRDT（Yjs/Automerge）、Service Worker 离线

---

（历史记录：研究方于 2026-10-13 报告本研究完成。本文件仅为研究证据，不构成任何窗口的调度、待命或派工指令。）
