# Z-Brand-Core｜Brand Intelligence Layer (BIL) v1

> 文档版本：v1.0
> 生效日期：2026-09-01
> 定位：ZBMP 增量能力规范 / Phase 2 Architecture & Data Contract
> 变更性质：仅新增文档，不修改生产业务代码、数据库 Schema、采集核心、风险/事件/报告口径

---

## 0. 本次增量目的

将近期对 Jacquemus、Patagonia、SHUSHU/TONG、BY FAR、Molly Goddard 的品牌研究抽象成可复用的 **Brand Intelligence Layer（BIL，品牌情报层）**。

本层不是“五个品牌的硬编码功能”，而是一套可复用能力：任何品牌、品类、城市、竞品组均可通过 Brand Entity + Social Voice + UGC + Geography + Benchmark + Lifecycle 进入同一分析链路。

### 强约束

- 不推翻现有 Z-Brand-Core / ZBIP 架构。
- 不新建第二套 Core。
- 不把 ZBMP 拆成独立长期维护源码项目。
- 不修改 CTH-POMS 生产主体口径、风险、事件、报告和历史数据。
- 不让 AI 成为生产事实 Owner。
- 不把 XHS/RedNote 研究能力变成绕过平台限制的自动化能力。
- 当前 XHS App Evidence 仍遵循 Shadow / 用户主动证据路径；正式生产采集继续走既有 Adapter 与安全门禁。
- 本阶段先完成 Contract / Map / UI / 数据定义，再开发运行时代码。

---

## 1. BIL 在 ZBIP 中的位置

```text
ZBIP
│
├── CTH-POMS
│   └── 生产监测 / 舆情 / 风险 / 事件 / 报告
│
├── ZBMP
│   └── Brand Intelligence Layer（BIL）
│       ├── Brand Entity
│       ├── Social Voice
│       ├── UGC Intelligence
│       ├── Consumer Intent
│       ├── Geography Intelligence
│       ├── Brand Benchmark
│       └── Brand Lifecycle
│
├── DCC
│   └── 研发治理 / Evidence / Release
│
└── SICI
    └── 手机端研发执行
```

BIL 是 ZBMP 的能力域，不是新的独立产品。

---

## 2. 六层数据链

```text
Source / Evidence
      ↓
Brand Entity Resolution
      ↓
Content Normalization
      ↓
UGC / KOL / Official / Commercial Classification
      ↓
Consumer Intent + Geography + Product + Topic
      ↓
Voice / Benchmark / Lifecycle
      ↓
Insight / Report
```

AI 可辅助语义分类、聚类和解释；原始事实、统计数量、时间、主体最终口径仍由数据与规则层负责。

---

## 3. Domain Objects

### 3.1 Brand

```text
brand_id
canonical_name
aliases
category
sub_category
price_segment
origin
status
official_channels
created_at
updated_at
```

### 3.2 Brand Account

```text
account_id
brand_id
platform
account_type            # official / verified / creator / store
account_name
account_handle
profile_url
follower_count
follower_count_captured_at
verification_status
source
```

粉丝数必须保存 `captured_at`，不能把动态数字当成永久事实。

### 3.3 Brand Mention

```text
mention_id
brand_id
source_platform
source_content_id
source_url
title
content_excerpt
publish_datetime
captured_at
author_type
engagement_snapshot
product_entities
topics
geography
quality_status
```

### 3.4 UGC Classification

```text
content_id
ugc_type                 # ugc / koc / kol / official / commercial / unknown
consumer_intent          # discovery / consideration / purchase / ownership / service / resale / none
content_scene             # outfit / unboxing / store / review / price / lifestyle / event / other
sentiment
confidence
model_version
rule_version
human_adopted
```

### 3.5 Brand Geography

```text
brand_id
country
city
district
commercial_area
venue
store_name
presence_type             # official_store / authorized / stockist / department / unknown
status                    # active / historical / unknown
verified_at
source
```

### 3.6 Brand Benchmark

```text
benchmark_group_id
brand_id
metric
value
period_start
period_end
source_count
data_quality
```

### 3.7 Brand Lifecycle Snapshot

```text
brand_id
period
social_voice_index
ugc_index
consumer_intent_index
offline_presence_index
momentum_index
lifecycle_stage
confidence
```

生命周期只能基于实际时间序列计算，不允许由单次搜索结果直接判定。

---

## 4. Social Voice 统一口径

禁止把“搜索结果数量”直接等同于 UGC。

### Voice hierarchy

```text
Total Mention
├── Official
├── Commercial
├── KOL
├── KOC
└── Organic UGC
```

### Organic UGC further split

```text
Organic UGC
├── Discovery
├── Consideration
├── Purchase
├── Ownership
├── Experience
├── Store Visit
├── Service
├── Resale
└── Other
```

### 核心指标

```text
Total Voice
Organic Voice
UGC Volume
UGC Share
Commercial Share
Consumer Intent Rate
Purchase Intent Rate
Store-related Mention Rate
Local UGC Rate
Voice Momentum
```

任何指标必须同时保存统计周期和数据质量状态。

---

## 5. Brand × Geography

目标不是只回答“有没有店”，而是判断品牌在目标城市的真实存在度：

```text
Brand
 ↓
City
 ↓
District
 ↓
Commercial Area
 ↓
Venue / Store / Stockist
 ↓
Local Social Mentions
 ↓
Consumer Intent
```

例如广州研究可以形成：

```text
品牌 → 广州 → 天河 → 太古汇 → 渠道/门店
                         ↓
                  本地 UGC / 打卡 / 购买 / 试穿
```

门店状态必须区分：`active / historical / unknown`，不得把历史门店显示为当前营业门店。

---

## 6. Brand Presence Index

第一版只定义模型，不立即接管生产统计。

```text
BPI = f(
  Social Presence,
  Organic UGC,
  Consumer Intent,
  Local Presence,
  Offline Presence,
  Influencer Presence,
  Product Presence,
  Momentum
)
```

所有维度必须保留原始指标与计算版本；最终指数只是派生结果，不覆盖原始数据。

---

## 7. Brand Lifecycle

```text
Emerging
   ↓
Growing
   ↓
Peak
   ↓
Mature
   ↓
Declining
   ↘
   Resurgent
```

判定至少需要连续时间窗口，并同时观察：

- Social Voice
- Organic UGC
- Consumer Intent
- Product Discussion
- Influencer Exposure
- Offline Presence
- Momentum

特别关注：

> 社交热度增长 ≠ 商业健康增长
> 线下收缩 ≠ UGC立即归零
> 高声量 ≠ 高消费意图

BY FAR 作为研究样本的价值正是用于验证这一生命周期逻辑，而不是预设其当前阶段。

---

## 8. Benchmark Seed v1

以下五个品牌仅作为 **研究样本 / Benchmark Seed**，不写入生产统计硬编码：

| Brand | Research Role |
|---|---|
| Jacquemus | 国际设计师品牌 / 社交视觉传播 |
| Patagonia | 户外 / 价值观 / 社群生活方式 |
| SHUSHU/TONG | 中国设计师 / 女性审美 / 明星传播 |
| BY FAR | 社交爆发 / 线下变化 / 存量 UGC 生命周期 |
| Molly Goddard | 小众设计师 / 艺术时尚 / 审美传播 |

### 数据状态规则

- 未经当前周期验证的数据：`NOT_VERIFIED`
- 历史公开数据：`HISTORICAL`
- 当前可验证数据：`VERIFIED`
- 来源冲突：`CONFLICTED`
- 无法确认：`UNKNOWN`

绝不为了填满 Benchmark 而制造数字。

---

## 9. UI 信息架构

新增入口建议挂在 ZBMP，不改变 CTH-POMS 主生产导航。

```text
品牌情报
├── 品牌总览
├── 社交声量
├── UGC 生态
├── 消费意图
├── 小红书账号
├── 门店与渠道
├── 城市分布
├── 竞品矩阵
├── 生命周期
├── 趋势变化
└── Intelligence Report
```

品牌详情页统一回答：

```text
WHO     品牌是谁
WHAT    当前发生什么
WHY     为什么发生
ACTION  下一步可以做什么
```

遵循 ZBIP Progressive Disclosure：核心信息首屏外露，次要信息折叠，Evidence 可追溯。

---

## 10. API Contract（规划）

第一阶段只定义接口，不接管现有生产接口。

```text
GET  /api/brand-intelligence/brands
GET  /api/brand-intelligence/brands/:id
GET  /api/brand-intelligence/brands/:id/voice
GET  /api/brand-intelligence/brands/:id/ugc
GET  /api/brand-intelligence/brands/:id/intent
GET  /api/brand-intelligence/brands/:id/geography
GET  /api/brand-intelligence/brands/:id/lifecycle
GET  /api/brand-intelligence/benchmark
```

生产实现前必须再次读取当前路由、数据模型和权限结构，禁止凭本文件直接写入业务代码。

---

## 11. 与现有 CTH-POMS 的边界

BIL 可以消费 CTH-POMS 已经合法产生的标准化数据，但不得改变：

- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `_subject_sql_and_values()`
- `aggregate_events()` 主体过滤
- `build_daily_report()` 主体过滤
- `publish_datetime`
- `captured_at`
- 风险 / 事件 / 报告生产口径

推荐数据关系：

```text
CTH-POMS Production Data
        ↓ read / contract
Normalization / Adapter
        ↓
BIL Analysis
        ↓
ZBMP Insight
```

禁止反向写入 CTH-POMS 核心事实表来“修正”品牌分析结果。

---

## 12. 与 XHS / RedNote 的边界

```text
Source
 ↓
Raw Evidence
 ↓
Normalize
 ↓
Quality Gate
 ↓
Subject / Brand Gate
 ↓
Dedup
 ↓
Database
 ↓
BIL
```

BIL 不负责平台访问限制处理，不绕过验证码、封禁、访问限制或平台风控。

采集失败必须保持真实失败状态；不得以 `0` 伪装成功。

---

## 13. AI Contract

AI 可负责：

- 品牌实体辅助识别
- 产品实体识别
- Topic 分类
- UGC / KOL / KOC / Commercial 辅助分类
- Consumer Intent 分类
- 情绪与语义分析
- 聚类
- 趋势解释
- 洞察文字

AI 不负责最终决定：

- 原始事实
- 统计总量
- 真实发布时间
- 主体最终归属
- 门店当前状态
- 核心风险事实

所有 AI 结果保存：

```text
model_version
prompt_version
input_summary
output
confidence
human_adopted
human_correction
created_at
```

---

## 14. Phase Plan

### Phase 1 — Research / Contract

本文件完成：Domain Objects / 指标 / 生命周期 / Geography / Benchmark / API / UI 边界。

### Phase 2 — Data Mapping

读取真实数据库、路由、Adapter、已有 ZBMP 能力，形成：

- BIL Data Map
- Field Reuse Map
- Ownership Map
- Conflict Map

### Phase 3 — Shadow

只读、旁路、Shadow；不改变生产任务。

### Phase 4 — Validation

用五个 Benchmark Seed 验证：

- Brand Entity
- UGC 分类
- Consumer Intent
- Geography
- Voice
- Lifecycle

### Phase 5 — Production Adapter

通过完整回归、安全门禁、Evidence 后，再接入 ZBMP 正式工作流。

---

## 15. Evidence / 完成定义

本阶段只有“文档契约完成”，不代表运行时代码完成。

后续每次 BIL 开发必须记录：

```text
Task
Baseline
HEAD
Remote HEAD
Scope
Files Changed
Files Not Changed
Owner
Dependencies
Risk
Tests
Evidence
NOT_VERIFIED
Commit SHA
Rollback
Next Step
```

---

## 16. 本次施工红线

**本文件允许：**
- 定义新能力
- 定义数据对象
- 定义指标口径
- 定义 UI / API contract
- 建立 Benchmark Seed
- 建立研究与生产边界

**本文件不授权：**
- 修改生产采集器
- 修改主体过滤
- 修改风险引擎
- 修改事件聚合
- 修改报告 SQL
- 修改生产数据库结构
- 自动启用新的 XHS 采集方式
- 自动部署
- 自动 Merge

下一阶段必须先审计真实代码后，再决定最小运行时补丁。
