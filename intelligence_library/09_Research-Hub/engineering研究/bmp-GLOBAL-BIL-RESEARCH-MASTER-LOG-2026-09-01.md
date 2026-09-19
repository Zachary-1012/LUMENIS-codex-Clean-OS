# ZBMP｜Global Brand Intelligence 全阶段研究、架构演进与推进总日志

项目：Z-Brand-Core / ZBMP
阶段：Global Brand Intelligence（Global BIL）
日期：2026-09-01
日志性质：完整阶段性研究与施工记录
范围：本阶段全部相关聊天讨论、研究结论、架构决策、GitHub 推进记录、数据库方向、下一阶段施工边界

---

## 00｜本日志目的

本日志用于完整保存本阶段围绕以下主题产生的全部有效成果：

* Jacquemus
* Patagonia
* SHUSHU/TONG
* BY FAR
* Molly Goddard
* 广州门店 / 中国 / 全球门店
* 小红书声量
* 小红书账号粉丝
* UGC
* 全球品牌案例
* ZBMP
* Z-Brand-Core
* Global BIL
* Brand Intelligence
* Consumer Voice
* Creator Intelligence
* Social → Commerce
* AI Discovery / GEO
* Creator → AI Discovery
* Product Intelligence
* Global → Local
* Brand Health
* Business Momentum
* Lifecycle
* Evidence
* Brand Learning
* 198 品牌盘库
* 198 × 17 Capability Matrix
* Staging Database
* Shadow Validation
* Production Adapter

同时记录：

哪些已经真实完成、哪些已经写入仓库、哪些只是架构设计、哪些因 GitHub 当前读取状态而暂时不能宣称完成。

---

## 01｜最初需求

最初提出的品牌研究对象：

* Jacquemus
* Patagonia
* SHUSHU/TONG
* BY FAR
* Molly Goddard

最初问题包括：

1. 广州是否有门店
2. 门店在哪里
3. 小红书声量多少
4. 小红书账号粉丝多少
5. 小红书有多少 UGC
6. 深入研究品牌
7. 形成长期学习能力
8. 将适合 Z-Brand-Core / ZBMP 的能力整合进去

---

## 02｜研究范围第一次扩展：不局限广州

随后明确：

研究范围不能只做广州。

需要覆盖：

广州
```
↓
```
中国
```
↓
```
亚洲
```
↓
```
欧洲
```
↓
```
美国
```
↓
```
全球

因此原本：

"品牌在广州有没有门店"

被重新定义成：

Global Brand
```
↓
```
Market Presence
```
↓
```
Country
```
↓
```
City
```
↓
```
District
```
↓
```
Store
```
↓
```
Channel

广州只是 Global Brand Entity 的一个 Market / Store 节点。

---

## 03｜第二次扩展：不只研究现有品牌库

随后明确：

不能只研究 ZBMP 现有品牌。

原因：

你的现有品牌库是业务资产，但全球 Benchmark 必须覆盖更多具有代表性的品牌机制。

因此研究对象扩展为：

* 现有 ZBMP 品牌
* 全球成熟品牌
* 新锐品牌
* 中国品牌
* 中国出海品牌
* 韩国品牌
* 日本品牌
* 欧洲品牌
* 美国品牌
* Luxury
* Designer
* Fashion
* Beauty
* Outdoor
* Sports
* DTC
* Creator-led
* Community-led
* Product-led
* Campaign-led
* Brand Revival
* Brand Failure
* Global Expansion
* Social Commerce
* AI-native / AI Discovery

---

## 04｜关键转折：从"品牌案例"转成"机制研究"

经过多轮讨论后，确定：

不能建立一个简单的：

全球品牌名单。

而应该建立：

Global Brand Mechanism Library

核心逻辑：

Brand
```
↓
```
Case
```
↓
```
Evidence
```
↓
```
Mechanism
```
↓
```
Context
```
↓
```
Outcome
```
↓
```
Transferability
```
↓
```
Hypothesis
```
↓
```
Validation
```
↓
```
Learning

因此：

Benchmark 不是品牌排行榜，而是机制训练集。

---

## 05｜Global BIL 的正式定位

Global BIL 最终定义为：

从品牌实体 → 市场 → 消费者 → 内容 → 创作者 → 产品 → Campaign → 渠道 → 商业结果 → 品牌健康 → 生命周期 → AI Discovery → Learning 的品牌智能层。

它不是传统 Social Listening 的扩大版。

最终目标是：

Research
```
↓
```
Intelligence
```
↓
```
Insight
```
↓
```
Decision
```
↓
```
Learning

---

## 06｜17 个核心 BIL 能力域

最终确定 17 个能力域：

1. Entity
2. Knowledge
3. Social Voice
4. UGC
5. Consumer Voice
6. Creator
7. Product
8. Campaign
9. Geography
10. Store / Channel
11. Community
12. Competitor
13. Brand Health
14. Business Momentum
15. Lifecycle
16. AI Discovery / GEO
17. Evidence

---

## 07｜第一个重要护栏：三个层面不能混

正式确定：

Social Heat
≠
Brand Health
≠
Business Momentum

Social Heat

回答：

大家正在谈什么？

包括：

* Social Voice
* UGC
* KOL
* KOC
* Creator
* Viral
* Media

Brand Health

回答：

消费者到底怎么看这个品牌？

包括：

* Awareness
* Buzz
* Perception
* Consideration
* Purchase Intent
* Satisfaction
* Quality
* Value
* Reputation
* Recommendation
* Rejection
* Switching

Business Momentum

回答：

品牌有没有真实商业动能？

包括：

* Product Demand
* Sales Signals
* Purchase Signals
* Store
* Retail
* E-commerce
* Market Expansion
* Channel Momentum

---

## 08｜第二个重要护栏：Coverage 不等于 Importance

确定不建立简单的：

Brand Score

而至少拆成：

Data Coverage
Evidence Quality
Benchmark Relevance
Brand Importance
Mechanism Fit
Transferability

原则：

数据多
≠
品牌重要
粉丝多
≠
品牌强
UGC 多
≠
购买高
AI 提及多
≠
品牌健康好

---

## 09｜Consumer Voice

研究后确定：

最响亮的人不一定代表最多消费者。

因此分为：

Loud Voice

* Celebrity
* Mega KOL
* Viral UGC
* Media
* 高互动内容

Quiet Voice

* 普通消费者
* 潜在消费者
* 已购买消费者
* 流失消费者
* 品牌转换者

最终链路：

发生了什么？
```
↓
```
消费者为什么这么说？
```
↓
```
谁在推动？
```
↓
```
是否影响考虑？
```
↓
```
是否影响购买？
```
↓
```
品牌应该做什么？

---

## 10｜Creator Intelligence

最初的"账号粉丝多少"不再被认为足够。

Creator Value 改为：

Reach
Relevance
Brand Fit
Authenticity
Community Density
Content Quality
UGC Generation
Consumer Intent
Commercial Signal

正式确定：

Creator Reach
≠
Creator Value

粉丝数只能作为：

动态 Snapshot。

不能作为永久品牌属性。

---

## 11｜UGC Intelligence

UGC 不再只是：

UGC 数量。

而需要研究：

* UGC Volume
* UGC Quality
* UGC Theme
* UGC Sentiment
* UGC Creator Type
* UGC Product Association
* UGC Consumer Intent
* UGC Commercial Signal
* UGC Lifecycle

核心原则：

UGC Volume
≠
UGC Quality
≠
Commerce Impact

---

## 12｜Social → Commerce

正式建立：

Content
```
↓
```
Attention
```
↓
```
Interest
```
↓
```
Consideration
```
↓
```
Product
```
↓
```
Purchase Intent
```
↓
```
Store / E-commerce
```
↓
```
Purchase
```
↓
```
UGC
```
↓
```
New Consumer

最终称为：

Brand Growth Loop

研究目标：

什么内容真正形成商业承接？

---

## 13｜Discovery Signal

进一步增加：

Discovery Signal

回答：

消费者在哪里发现品牌？

包括：

* Store
* Word of Mouth
* Xiaohongshu
* TikTok
* Instagram
* YouTube
* Search
* AI
* Creator
* Media
* Marketplace
* Other

形成：

Discovery
```
↓
```
Evidence
```
↓
```
Intent
```
↓
```
Action

---

## 14｜SEO / Social / AI Discovery 必须分离

正式确定：

SEO Visibility
≠
Social Visibility
≠
AI Visibility

AI Discovery 作为独立品牌可见性层。

---

## 15｜AI Discovery / GEO

AI Discovery 需要记录：

* Query
* Market
* Language
* Engine / Model
* Brand Mention
* Recommendation
* Position
* Citation
* Citation Source
* Competitor Co-mention
* Framing
* Observed At

并进一步拆：

Mention
Citation
Recommendation
Position
Share of Voice
Query Intent
Citation Source

核心护栏：

AI Mention
≠
AI Recommendation

---

## 16｜Creator → AI Discovery

进一步形成新的研究方向：

Creator
```
↓
```
Content
```
↓
```
Audience Response
```
↓
```
Search / Discovery
```
↓
```
AI Retrieval
```
↓
```
AI Citation
```
↓
```
AI Recommendation
```
↓
```
Consideration
```
↓
```
Commerce
```
↓
```
UGC
```
↓
```
Brand Health
```
↓
```
Learning

严格禁止直接推断：

Creator 被 AI 提及
≠
Creator 导致 AI 推荐
AI 引用 Creator
≠
Creator 对 AI 输出存在因果影响
内容主题相似
≠
直接影响关系成立

---

## 17｜Product Intelligence

进一步确定：

AI-mediated Commerce 的底层不仅是 Brand，还必须是 Product。

Product Intelligence：

Product
```
├── Name
├── Category
├── Attribute
├── Price
├── Availability
├── Market
├── Retailer
├── Review
├── Creator Content
└── Consumer Need
```

最终：

Consumer Query
```
↓
```
AI
```
↓
```
Product
```
↓
```
Brand
```
↓
```
Retailer
```
↓
```
Purchase

长期定位：

Brand × Product Intelligence

---

## 18｜Global → Local Transfer Engine

全球案例不能简单复制到中国或广州。

正式确定：

Global Brand DNA
+
Local Culture
+
Local Consumer
+
Local Platform
+
Local Creator
+
Local Channel
=
Local Strategy Hypothesis

地理层级：

GLOBAL
```
↓
```
REGION
```
↓
```
COUNTRY
```
↓
```
CITY
```
↓
```
DISTRICT
```
↓
```
STORE
```
↓
```
PLATFORM
```
↓
```
COMMUNITY

---

## 19｜ZBMP 198 品牌重新定义

现有：

brand_directory.json

被重新定位为：

广州太古汇 Local Market / Channel Dataset

不是 Global Brand Master。

最终：

Global Brand Entity
```
↓
```
Market Presence
```
↓
```
China
```
↓
```
Guangzhou
```
↓
```
Taikoo Hui
```
↓
```
Store / Channel

因此：

广州太古汇是一个高价值业务场景，而不是 Global BIL 的边界。

---

## 20｜Benchmark Brand Selection

Benchmark 不按名气排序。

选择维度：

* Strategic Relevance
* Archetype Coverage
* Market Diversity
* Mechanism Diversity
* Lifecycle Value
* Evidence Quality
* Data Availability
* Transferability

等级：

S
A
B
C

---

## 21｜第一批 Benchmark

第一批建立的 Benchmark Seed：

S

* Patagonia
* Jacquemus
* Glossier
* Salomon
* Nike
* Miu Miu

A

* Gentle Monster
* Lululemon
* On
* The Ordinary
* Aesop
* Uniqlo
* Adidas
* SHUSHU/TONG
* BY FAR
* AllSaints
* boohoo
* Hot Topic

B

* Molly Goddard

这些品牌用于：

机制覆盖，而不是品牌排名。

---

## 22｜第一批机制库

建立的 Brand Mechanisms：

values_community
cultural_visual_growth
ugc_cocreate
creator_community
global_culture
luxury_cultural_momentum
retail_experience
ambassador_community
product_innovation
education_trust
global_local
china_global_niche
social_lifecycle
brand_resurgence
creator_commerce
ai_discovery

标准结构：

Brand
```
↓
```
Mechanism
```
↓
```
BIL Domains
```
↓
```
Context
```
↓
```
Outcome
```
↓
```
Transferability
```
↓
```
Guardrail

---

## 23｜全网研究得到的主要行业验证

本阶段持续检索全球 Brand Intelligence、Creator Commerce、UGC、AI Search、Brand Health 案例。

重要验证包括：

Creator Commerce

Hot Topic、boohoo 等案例证明：

Creator
```
↓
```
UGC
```
↓
```
Storefront
```
↓
```
Affiliate / Commerce
```
↓
```
Commercial Result

可以形成完整商业链路。

---

UGC 与 Brand Health

ASOS 等案例同时出现：

* UGC
* Participation
* Brand Lift
* Ad Recall
* Brand Association

进一步验证：

UGC、Content、Brand Health 必须分开。

---

Global → Local

Weekday 等跨市场案例验证：

Creator 策略不能简单跨语言、跨文化复制。

---

AI Discovery

2026 年 AI Visibility 研究持续出现：

* AI Mention
* Citation
* Recommendation
* AI Share of Voice
* Position
* Query Intent

因此 AI Discovery 可以作为独立层。

---

Consumer Voice

YouGov 等 Brand Intelligence 产品进一步验证：

Brand Intelligence 不只需要回答"发生了什么"，还必须回答"为什么"。

---

## 24｜Brand Learning

最终确定：

ZBMP 需要从：

Case Library

升级为：

Brand Learning System

闭环：

Case
```
↓
```
Evidence
```
↓
```
Mechanism
```
↓
```
Conditions
```
↓
```
Outcome
```
↓
```
Transferability
```
↓
```
Hypothesis
```
↓
```
Observed Result
```
↓
```
Feedback
```
↓
```
Pattern Revision

目标：

新品牌进入系统后，可以匹配历史案例中的相似机制，而不是每次从零研究。

---

## 25｜Evidence Contract

正式确定所有研究必须严格区分：

FACT
```
↓
```
OBSERVATION
```
↓
```
INTERPRETATION
```
↓
```
HYPOTHESIS
```
↓
```
RECOMMENDATION

禁止：

* 推测写成事实
* AI 输出写成事实
* 粉丝数直接代表品牌价值
* UGC 数量直接代表商业效果
* Social Heat 直接代表 Brand Health
* 相关性直接写成因果关系

动态数据原则上保留：

* Source
* Published At
* Observed At
* Market
* Platform
* Evidence Type
* Confidence
* Method Version

---

## 26｜198 × 17 Capability Matrix

正式确定：

198 Brands
×
17 BIL Domains
=
3,366 Capability Cells

Cell 状态：

EXISTS
PARTIAL
MISSING
N/A
CONFLICTED
UNKNOWN

最重要护栏：

UNKNOWN
≠
MISSING

没有研究过的品牌不能直接判定为没有能力。

---

## 27｜三批盘库顺序

Batch 1

Entity
Knowledge
Social
UGC
Consumer
Creator
Product

Batch 2

Campaign
Geography
Store / Channel
Community
Competitor

Batch 3

Brand Health
Business Momentum
Lifecycle
AI Discovery
Evidence

---

## 28｜数据库策略

Global BIL 数据必须：

Staging First

标准：

Research
```
↓
```
Normalization
```
↓
```
Entity Resolution
```
↓
```
Staging
```
↓
```
Validation
```
↓
```
Shadow
```
↓
```
Regression
```
↓
```
Production Adapter

禁止直接污染现有生产舆情链路。

---

## 29｜与现有 ZBMP / CTH-POMS 的边界

现有核心逻辑保持不变。

特别保护：

* 主体过滤
* 主体判断
* 事件聚合
* 舆情判断
* 报告主流程

外部 AI：

只能辅助。

不能覆盖：

系统核心规则。

---

## 30｜GitHub 已推进资产

本阶段此前已经形成/推送以下相关资产：

docs/GLOBAL_BIL_V1_1_RESEARCH_PROTOCOL.md
docs/GLOBAL_BIL_NEXT_EXECUTION_PLAN_V1.md
docs/GLOBAL_BIL_CAPABILITY_MATRIX_V1.md
docs/GLOBAL_BIL_198_BRAND_MATRIX_EXECUTION_V1.md
docs/GLOBAL_BIL_2026_09_RESEARCH_UPDATE.md
docs/GLOBAL_BIL_CREATOR_AI_DISCOVERY_V1.md
docs/GLOBAL_BIL_BENCHMARK_SELECTION_V1.md
data/global_bil_benchmark_seed_v1.json
data/global_bil_benchmark_mechanisms_v1.json
migrations/009_global_bil_staging.sql

此前记录的相关 Commit：

47133a0afe13c6472f7fb433c2659f742f2ddbea
183a62daff1d1701bda109e326aac4ffbdb33f9c
6eb48c410f1d111ac9034e36ae02d6334296ea00
adca4012d28ff53172bd9819ca7833e9c01e9194
23a5b1918d757ae4c8e8780a80c5a72433c0a749
598930e4afaf6ffb678eba2a26786c5179c73969
a0c8ca3edcab7aa9f27dfa3d90979f69249b91c2
d8abb0edf574beae92a55eb494363f732932b8cc
50c1938734038edc24ac794a258b2d955ddf9e8d
be12811be58cf5fd30597a6e9c741ef92c8359cc
453237594598fa044597527e1e7650aff18df721
0031666cfe7bc82f0eaad63705b5813f3a9a8393

---

## 31｜本阶段研究中的重要架构判断

最终形成以下"不可轻易推翻"的原则：

Social Heat
≠
Brand Health
≠
Business Momentum
SEO
≠
Social
≠
AI Discovery
Creator Reach
≠
Creator Value
UGC Volume
≠
UGC Quality
≠
Commerce Impact
AI Mention
≠
AI Recommendation
Data Coverage
≠
Brand Importance
UNKNOWN
≠
MISSING
Correlation
≠
Causation

这些规则属于数据质量和系统可信度护栏。

---

## 32｜关于最初五个品牌的最终处理方式

最初研究对象：

Jacquemus
Patagonia
SHUSHU/TONG
BY FAR
Molly Goddard

不再单独做成孤立品牌报告。

而是作为：

Global Benchmark Seed

进入：

Brand Entity
```
↓
```
Global Presence
```
↓
```
Market
```
↓
```
Store
```
↓
```
Social
```
↓
```
UGC
```
↓
```
Creator
```
↓
```
Product
```
↓
```
Campaign
```
↓
```
Consumer
```
↓
```
Brand Health
```
↓
```
Lifecycle
```
↓
```
AI Discovery
```
↓
```
Mechanism
```
↓
```
Transferability

因此最初问题最终被升级成一个长期可计算的数据模型。

---

## 33｜下一阶段真正要做的事情

当前不应该继续无限增加文档。

下一阶段直接进入真实资产：

第一阶段

读取最新 Z-Brand-Core：

Repository
```
↓
```
Latest Commit
```
↓
```
BIL Files
```
↓
```
Brand Entity
```
↓
```
brand_directory
```
↓
```
Existing Modules

---

第二阶段

建立：

198 Brand Inventory

核对：

* Brand ID
* Brand Name
* Alias
* Category
* Existing Knowledge
* Existing Intelligence
* Existing Case
* Existing Store
* Existing Data Source

---

第三阶段

执行：

198 × 17 Capability Matrix

得到：

EXISTS
PARTIAL
MISSING
N/A
CONFLICTED
UNKNOWN

---

第四阶段

进行：

Global Benchmark Mapping

将全球 Benchmark 机制映射到现有品牌：

Existing Brand
```
↓
```
Similar Archetype
```
↓
```
Similar Mechanism
```
↓
```
Similar Lifecycle
```
↓
```
Similar Consumer
```
↓
```
Similar Market
```
↓
```
Benchmark

---

第五阶段

进行：

Gap Detection

最终回答：

ZBMP 已经有什么？

真正缺什么？

哪些能力只是部分存在？

哪些能力有数据但没有结构化？

哪些能力值得建设？

哪些全球案例可以直接学习？

哪些机制不能直接复制？

---

## 34｜当前真实状态

必须严格区分：

已形成

* Global BIL 架构
* 17 Capability Domains
* Benchmark Selection
* 第一批 Benchmark Seed
* 第一批 Mechanism Library
* Consumer Voice
* Creator Intelligence
* Social → Commerce
* Discovery Signal
* AI Discovery / GEO
* Creator → AI Discovery
* Product Intelligence
* Global → Local
* Brand Health
* Business Momentum
* Lifecycle
* Evidence Contract
* Brand Learning
* 198 × 17 Matrix 规则
* Staging-first 原则

---

已有 GitHub 推进记录

相关文档、Seed、Mechanism、Migration 已有此前阶段 Commit 记录。

---

尚未真实完成

以下不能写成"已完成"：

* 198 个品牌的真实全量 Capability 核验
* 3,366 个 Cell 全量填充
* 完整 Entity Resolution
* 完整 Evidence-backed Staging Import
* Shadow Runtime
* Production Adapter
* 全量真实 UGC / 粉丝 / 声量数据库

---

## 35｜当前阻塞原因

最新一次 GitHub 实际检索中：

当前连接没有返回目标私有仓库的可检索内容。

因此无法安全地假设当前仓库状态仍与之前完全一致。

原则：

不使用旧上下文冒充最新代码状态。

在重新获得仓库真实读取能力之前：

不应该声称：

* 已读取最新代码
* 已完成 198 品牌盘库
* 已完成 3,366 Cell
* 已完成数据库导入
* 已完成 Shadow
* 已完成生产接入

---

## 36｜恢复仓库访问后的立即施工顺序

Z-Brand-Core 最新仓库
```
        ↓
```
真实代码核对
```
        ↓
```
现有 BIL 文件核对
```
        ↓
```
Brand Entity 核对
```
        ↓
```
198 Brand Inventory
```
        ↓
```
Entity Resolution
```
        ↓
```
Batch 1
```
        ↓
```
Batch 2
```
        ↓
```
Batch 3
```
        ↓
```
3,366 Cell Matrix
```
        ↓
```
Global Benchmark Mapping
```
        ↓
```
Gap Analysis
```
        ↓
```
Evidence-backed Staging
```
        ↓
```
Validation
```
        ↓
```
Shadow
```
        ↓
```
Regression
```
        ↓
```
Production Adapter

---

## 37｜长期最终形态

最终 ZBMP / Global BIL 的完整结构：

GLOBAL RESEARCH
```
        ↓
```
BRAND INTELLIGENCE
```
        ↓
```
CONSUMER INTELLIGENCE
```
        ↓
```
CREATOR INTELLIGENCE
```
        ↓
```
PRODUCT INTELLIGENCE
```
        ↓
```
DISCOVERY INTELLIGENCE
```
        ↓
```
COMMERCE INTELLIGENCE
```
        ↓
```
BRAND HEALTH
```
        ↓
```
LIFECYCLE
```
        ↓
```
MECHANISM LIBRARY
```
        ↓
```
AI DISCOVERY
```
        ↓
```
GLOBAL → LOCAL
```
        ↓
```
BRAND LEARNING
```
        ↓
```
DECISION

最终不是：

"这个品牌有多少小红书笔记？"

而是能够回答：

这个品牌是谁？
```
↓
```
消费者为什么谈它？
```
↓
```
谁真正影响消费者？
```
↓
```
什么内容推动？
```
↓
```
什么产品推动？
```
↓
```
消费者有没有购买意向？
```
↓
```
有没有商业承接？
```
↓
```
品牌健康如何？
```
↓
```
竞争发生了什么？
```
↓
```
品牌处于什么生命周期？
```
↓
```
AI 如何理解这个品牌？
```
↓
```
全球机制是什么？
```
↓
```
能否迁移到中国？
```
↓
```
能否迁移到广州？
```
↓
```
为什么可以 / 不可以？
```
↓
```
下一步应该做什么？
```
↓
```
结果是否验证？
```
↓
```
系统学到了什么？

---

## 38｜最终战略定义

本阶段最终形成的核心思想：

ZBMP 不应该只是"监测品牌"。

应该逐步成为：

Global Brand Intelligence + Local Market Intelligence + Brand Learning System

其中：

Global BIL
=
全球品牌知识与机制
ZBMP
=
品牌 × 市场 × 消费者 × 内容 × 商业
CTH-POMS
=
广州太古汇核心舆情与业务场景
Brand Learning
=
把全球案例转化为可验证的机制知识
AI Discovery
=
新的品牌发现与推荐入口
Decision Engine
=
最终商业价值输出

最终目标：

越研究品牌，系统越懂品牌；越懂品牌，越能理解消费者；越理解消费者，越能判断新品牌和新市场；每一次真实验证又反过来让系统继续学习。

---

## 39｜本阶段结论

本阶段已经完成一次重要的架构跃迁：

几个品牌的查询
```
        ↓
```
全球品牌研究
```
        ↓
```
品牌案例库
```
        ↓
```
机制库
```
        ↓
```
Global BIL
```
        ↓
```
Consumer / Creator / Product
```
        ↓
```
Discovery / Commerce
```
        ↓
```
AI Discovery
```
        ↓
```
Global → Local
```
        ↓
```
Brand Learning
```
        ↓
```
Decision Engine

因此后续不再回到"简单查品牌信息"的模式。

所有新的品牌研究，都应该进入这套统一结构：

Entity → Evidence → Mechanism → Consumer → Market → Outcome → Transferability → Learning

而所有进入 ZBMP 的能力，都必须满足：

可验证、可追溯、可解释、可回滚、可复用。

---

日志状态

阶段状态：架构与研究模型已形成，全球案例机制库已启动，Staging 方案已建立，真实 198 品牌全量盘库待 GitHub 私有仓库读取恢复后继续。

下一断点：198 Brand Inventory → 3,366 Capability Matrix → Global Benchmark Mapping → Evidence-backed Staging。