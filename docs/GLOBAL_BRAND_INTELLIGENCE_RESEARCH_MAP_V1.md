# Z-Brand-Core / ZBMP｜Global Brand Intelligence Research Map v1

> 日期：2026-09-01
> 性质：研究与数据层增量，不改变现有生产核心

## 1. 结论

ZBMP 已经存在品牌目录、品牌知识库、品牌统计、品牌报告、案例库、Campaign/Topic 能力，因此 Global Brand Intelligence 不应再造第二套品牌系统，而应把这些能力连接成一个 Evidence-first 的品牌情报图谱。

仓库当前已有 `brand_directory.json`，包含 198 个广州太古汇场内品牌，说明现有 Brand Entity 是一个可复用入口，而不是只能服务广州。fileciteturn11file0

当前已有 `brand_knowledge_base.py`，已经具备品牌知识分类、SQLite 持久化、去重、搜索、批量导入和 JSON 导出能力；因此 BIL 的研究知识层应优先复用它，而不是重新建立平行知识库。fileciteturn12file0

当前 `case_library.json` 已有服务、食品安全、活动秩序、内容争议、危机响应等案例及 response formulas，因此 BIL 的案例体系应与现有 Case Library 建立关系，而不是另建孤立案例库。fileciteturn13file0

## 2. 全球研究对象

案例不限制广州、中国或时尚行业。优先覆盖：

- Luxury / Designer：Jacquemus、Miu Miu、Loewe、Prada、Gucci、Bottega Veneta、SHUSHU/TONG、Molly Goddard、Simone Rocha、Coperni、The Row、Acne Studios
- Sport / Outdoor：Nike、Adidas、Patagonia、Arc'teryx、Salomon、On、Lululemon、Hoka、Gymshark
- Beauty：Glossier、The Ordinary、Rare Beauty、Rhode、Aesop、CeraVe、Shiseido、Yves Rocher
- Lifestyle / Culture：Gentle Monster、Crocs、Dr. Martens、Uniqlo
- DTC / Community：SKIMS、Glossier、Gymshark 等
- Multi-brand / Portfolio：PVH、Shiseido 等

案例选择标准：是否能提供可验证的品牌机制、消费者信号、内容传播、市场差异、产品/渠道动作或生命周期变化。

## 3. 每个品牌统一分析模板

### A. Brand DNA
- 定位
- 核心价值
- 审美/文化符号
- 品类
- 价格带
- 核心差异化

### B. Market
- 原生市场
- 全球扩张
- 国家/地区差异
- 市场进入/退出
- 市场成熟度

### C. Consumer
- 核心人群
- 需求
- 购买动机
- 阻力
- 情绪
- Consideration / Purchase Intent

### D. Social
- Total Voice
- Organic Voice
- Commercial Voice
- UGC Share
- Creator Share
- Platform Mix
- Local vs Global

### E. Content / UGC
- 穿搭/使用
- 开箱
- Review
- 门店体验
- 产品比较
- Lifestyle
- Meme / Cultural Signal
- Advocacy

### F. Creator / Community
- Celebrity
- Mega Creator
- Micro/Niche Creator
- KOC
- Ambassador
- Community
- Advocacy

### G. Product
- Hero Product
- Product Buzz
- Product Sentiment
- Newness
- Price discussion
- Product lifecycle

### H. Campaign
- Campaign objective
- Creative mechanism
- Creator mechanism
- Community mechanism
- Earned/Owned/Paid
- Cross-platform propagation
- Consumer reaction

### I. Geography / Store / Channel
- Country
- City
- Commercial area
- Store
- Stockist
- Department store
- E-commerce
- Social-commerce
- Local UGC

### J. Competition
- Direct competitors
- Aspirational competitors
- Substitute brands
- Share of social conversation
- Differentiation

### K. Lifecycle
- Emerging
- Growing
- Peak
- Mature
- Declining
- Resurgent

### L. Business Interpretation
- Brand Health
- Cultural Momentum
- Consumer Intent
- Commercial Momentum
- Risk
- Opportunity

## 4. Research lessons already validated by external cases

### PVH
PVH 将 social intelligence 放进 consumer insights，用品牌/消费者对话反推组织策略；公开案例还展示了用 #OOTD 衡量“share of social wardrobe”、用情绪日历解释消费者情绪，并追踪多个品牌。citeturn0search5turn0search11

**ZBMP 可吸收：** Social Voice 不只是数量，而要形成“内容 → 人群 → 情绪 → 策略”的连接。

### Shiseido
Shiseido 面对多个国家、多个品牌和碎片化工具时，采用统一的全球 social listening、consumer intelligence 和 influencer intelligence 体系。citeturn0search0

**ZBMP 可吸收：** Global Brand Intelligence 必须支持 Portfolio → Brand → Market → Platform 的多级视图。

### Glossier
研究显示，消费者分享个人体验不仅是 review，还可以成为学习、品牌倡导、品牌共创和社区关系建设的机制。citeturn0search1turn0search14

**ZBMP 可吸收：** UGC 必须进一步判断 Advocacy、Co-development Signal，而不是只计数。

### Salomon
公开案例显示，其全球运动员项目产生大量自然 UGC，并把 athlete/community 体系作为全球传播机制。citeturn0search12

**ZBMP 可吸收：** Creator Intelligence 必须区分“粉丝量”与“社区生产力/UGC贡献”。

### The Body Shop
公开案例展示了全球品牌、竞品、campaign 的持续追踪，并把 social listening 用于 campaign inspiration、产品表现、声誉、趋势与产品开发。citeturn0search9

**ZBMP 可吸收：** Brand Intelligence 必须贯通 Campaign → Product → Reputation → Opportunity。

### YouGov Fashion Retail
品牌追踪与受众画像被用于持续观察品牌健康、campaign 共鸣、Buzz、Consideration 和 Purchase Intent。citeturn0search7

**ZBMP 可吸收：** Brand Health 与 Consumer Intent 应作为独立结果层，不被 Social Voice 取代。

### BoF Brand Pulse
BoF 在 2025 年推出的 AI-powered Brand Pulse 用 Discoverability、Identity、Value、Connection、Love 五个维度评估时尚品牌表现。citeturn0search8

**ZBMP 可吸收：** 品牌表现需要从“声量”升级为多维品牌健康模型。

## 5. BIL v1.1 指标层

```text
Brand Health
├── Awareness / Discoverability
├── Identity
├── Value
├── Connection
├── Love / Advocacy
│
Social
├── Total Voice
├── Organic Voice
├── UGC
├── Creator
├── Engagement
└── Momentum
│
Consumer
├── Consideration
├── Purchase Intent
├── Ownership
├── Satisfaction
├── Advocacy
└── Co-development
│
Business / Market
├── Market Presence
├── Store Presence
├── Channel Presence
├── Product Momentum
└── Commercial Momentum
```

任何综合指数必须保存原始指标、统计周期、数据质量和版本，不允许用 AI 单次判断覆盖事实数据。

## 6. Evidence 规则

每条研究结论至少包含：

```text
brand_id
metric_or_claim
value_or_text
source_type
source_url
published_at
captured_at
market
platform
evidence_quality
status
analysis_version
```

状态：`VERIFIED / HISTORICAL / NOT_VERIFIED / CONFLICTED / UNKNOWN`

## 7. 研究数据库原则

第一阶段允许把研究数据写入 **Research/Knowledge Domain**；不直接写入生产事实表。

建议：

```text
Research Evidence
      ↓ validation
Brand Intelligence Store
      ↓ adapter
ZBMP read model
      ↓
UI / Report / Benchmark
```

现有 `brand_knowledge` 适合承载知识条目，但不足以单独承载时间序列 Social/UGC/Market Observation。因此后续只在确认复用边界后新增最小 observation tables，不复制 Brand Entity。

## 8. Benchmark 选取

Benchmark 不固定五个品牌。按 Archetype 动态选取：

- Global Luxury
- Designer / Independent
- Sport / Outdoor
- Beauty Community
- DTC
- Creator-led
- Heritage / Revival
- Value / Mass
- Sustainability / Purpose
- Retail / Experience
- China-to-Global
- Global-to-China

每个 Archetype 至少 3 个案例，优先包含成功 + 失败/转型样本。

## 9. 下一阶段

1. 从 `brand_directory.json` 完整解析现有 198 个 Brand Entity。
2. 读取现有 brand knowledge / brand stats / case / campaign / report 能力，形成 Field Reuse Map。
3. 建立 `Brand × Capability Coverage Matrix`。
4. 从全球公开案例补足缺失 Archetype。
5. 形成第一批 30–50 个高价值 Benchmark Brands。
6. 将经过 Evidence 校验的研究案例导入 Research Domain。
7. Shadow 计算 Social / UGC / Intent / Geography / Lifecycle。
8. 完成 BIL → ZBMP Adapter 后再考虑 UI 正式接入。

## 10. 红线

不因全球品牌研究而修改现有 CTH-POMS 主体过滤、风险、事件、报告生产口径；不把历史门店当现行门店；不把搜索结果数直接称为 UGC；不把粉丝数直接当影响力；不把 AI 推测写成事实。
