# Final Data Pipeline + KOS/KOC/UGC + Monitoring + Content Template Specification

**Status:** FINAL / implementation authority
**Date:** 2026-09-04
**Scope:** Data ingestion, computation, visualization, monitoring objects and content-production templates

## 0. Core principle

Raw imported data must NEVER be pushed directly into dynamic visualization components.

The mandatory pipeline is:

```text
Raw Import
  ↓
Schema Validation
  ↓
Normalization / Cleaning
  ↓
Programmatic Functions
  ↓
Deterministic Computation
  ↓
Canonical Data Table
  ↓
Table Validation / Quality Gate
  ↓
Visualization Adapter
  ↓
Dynamic Table / Chart / Visualization
  ↓
UI Presentation
```

The visualization layer consumes validated table-shaped data, not uncontrolled raw payloads.

## 1. Data truth layers

Every dataset must maintain explicit layers:

```text
L0 Raw
L1 Normalized
L2 Computed
L3 Canonical Table
L4 Visualization View Model
L5 UI
```

Never overwrite L0 with processed values.

## 2. Function-first computation

Every derived metric must be produced by a deterministic function with:

- named input fields
- explicit output fields
- null/empty handling
- type handling
- boundary handling
- formula/version identifier
- test cases

Examples:

```text
interaction_rate()
risk_score()
sentiment_score()
engagement_score()
trend_delta()
trend_rate()
content_type()
creator_tier()
event_cluster()
topic_velocity()
```

No visual component is allowed to calculate business metrics ad hoc.

## 3. Canonical table contract

Each canonical row must have, where applicable:

```text
record_id
source
source_url
captured_at
published_at
entity_id
entity_name
platform
content_type
author_id
author_name
creator_tier
text_raw
text_normalized
sentiment
sentiment_confidence
risk_level
risk_score
interaction_count
like_count
comment_count
share_count
collect_count
view_count
topic_id
topic_name
event_id
event_name
calculation_version
source_version
quality_status
```

Fields not available must remain null/unknown rather than fabricated.

## 4. Table quality gate

Before visualization:

```text
Schema valid?
Types valid?
IDs unique where required?
Required fields present?
Dates parseable?
Counts numeric and non-negative?
Derived metrics reproducible?
Duplicates handled?
Source traceable?
Calculation version recorded?
```

If a critical check fails, the dataset is blocked from production visualization and marked for review.

## 5. Visualization adapter

The visualization adapter receives only canonical/validated table data.

Responsibilities:

- select fields
- order rows
- aggregate only through approved functions
- format labels
- preserve source identifiers
- attach calculation metadata
- provide drill-down IDs

Visualization components must not silently recalculate business logic.

## 6. Drill-down contract

Every dynamic table/chart row or point that represents a real object must retain a stable identifier:

`visualization → record/event/topic/entity ID → detail → evidence/source`

A chart is an interface to the data, not a separate source of truth.

---

# KOS / KOC / UGC Object Model

## 7. Creator classification

KOS, KOC and UGC are classifications of content creators/content behavior. They must not be inferred from one single arbitrary metric.

Store:

```text
creator_id
creator_tier
classification_method
classification_version
classification_confidence
classification_evidence
```

Classification rules must be configurable and versioned.

## 8. KOS template

KOS record:

```text
KOS ID
平台
账号
品牌/业态
账号定位
专业领域
粉丝/影响力指标（如可得）
内容数量
互动表现
内容主题
合作/商业属性
传播角色
风险状态
证据
```

KOS analysis sections:

`定位 → 内容 → 传播 → 互动 → 影响 → 风险 → 可合作价值`

## 9. KOC template

```text
KOC ID
平台
账号
品牌关联
内容类型
真实体验信号
互动表现
本地属性
内容主题
传播扩散
风险
证据
```

Analysis:

`真实体验 → 口碑 → 互动 → 扩散 → 风险`

## 10. UGC template

```text
UGC ID
平台
作者
发布时间
原始内容
标准化内容
品牌
业态
主题
情绪
风险
互动
事件
话题
证据
```

Analysis:

`用户表达 → 情绪 → 主题 → 事件 → 传播 → 风险`

---

# 舆情对象模板

## 11. 舆情事件模板

```text
事件 ID
事件名称
事件类型
首次发现时间
峰值时间
当前状态
涉及品牌
涉及业态
核心话题
内容数量
互动数量
正/中/负分布
风险等级
传播阶段
关键节点
KOS/KOC/UGC构成
证据集合
处置状态
```

事件结构：

`发现 → 聚合 → 判断 → 时间线 → 扩散 → 峰值 → 当前 → 处置 → 复盘`

## 12. 笔记模板

```text
笔记 ID
平台
URL
作者
作者类型
发布时间
标题
正文
品牌命中
话题命中
事件命中
情绪
情绪置信度
风险
互动数据
内容类型
AI分析
人工修正
Evidence
```

详情结构：

`原文 → 作者 → 命中 → 情绪 → 风险 → 互动 → AI判断 → 人工判断 → Evidence`

## 13. 话题监测模板

```text
Topic ID
话题名称
平台
开始时间
当前时间
相关内容数
互动数
新增速度
增长率
情绪结构
风险结构
关联品牌
关联事件
主要作者类型
趋势状态
证据
```

分析结构：

`规模 → 速度 → 情绪 → 作者 → 事件 → 趋势 → 风险`

## 14. 负面监测模板

```text
Negative ID
对象
发现时间
负面类型
严重程度
互动
传播速度
作者类型
是否集中爆发
关联事件
证据
当前处置
```

## 15. 风险预警模板

```text
Risk ID
触发规则
对象
触发时间
风险等级
风险分数
触发证据
传播规模
传播速度
影响范围
关联事件
建议动作
处置状态
```

Rule-based triggers remain authoritative. AI can assist classification but cannot silently replace hard business rules.

---

# 内容生产模板

## 16. 内容生产统一对象

Every content-production task must have:

```text
content_id
template_id
content_type
platform
topic
objective
audience
brand_voice
source_material
evidence
key_message
structure
copy
visual_direction
cta
risk_check
human_review
version
status
```

## 17. 小红书笔记模板

```text
标题
↓
开头钩子
↓
核心体验/事实
↓
场景细节
↓
用户价值/情绪价值
↓
自然转折
↓
品牌/活动信息
↓
CTA
↓
标签建议
```

Copy rules:

- Do not fabricate experiences or facts.
- Separate verified facts from creative expression.
- Preserve approved brand terminology.
- Avoid excessive marketing language.
- Produce platform-appropriate language without changing factual meaning.

## 18. 海报文案模板

```text
主标题
副标题
核心信息
时间
地点
参与方式
必要限制/注意事项
CTA
```

## 19. 视频脚本模板

```text
Hook
↓
Scene 1
↓
Scene 2
↓
Key message
↓
Emotional turn
↓
Brand/event information
↓
Ending
```

Each scene should specify:

`画面 / 台词或字幕 / 时长 / 信息目的 / 素材来源`

## 20. 评论回复模板

Comment reply must support:

```text
原评论
评论意图
情绪
风险
建议回复策略
自动回复草稿
人工审核状态
最终回复
```

Reply modes:

`感谢 → 信息补充 → 疑问解答 → 负面安抚 → 风险升级`

Risky comments must not be auto-published without the configured review gate.

## 21. 内容审核链

```text
Source Material
↓
Draft
↓
Fact Check
↓
Brand/Style Check
↓
Risk Check
↓
Human Review
↓
Approved Copy
↓
Publish / Export
```

---

# Templates and versioning

## 22. Template registry

Every production template must have:

```text
template_id
name
content_type
platform
version
status
owner
input_schema
output_schema
rules
risk_rules
created_at
updated_at
```

Never silently modify a production template. Create a new version.

## 23. Human-in-the-loop

Where configured, store:

```text
AI output
AI confidence
prompt version
model version
original input
final result
human correction
correction reason
```

This supports later evaluation and model improvement without replacing human judgment.

## 24. Final implementation rule

The system must treat data and content as structured production objects.

Data:

`Raw → Function → Table → Validation → Visualization`

Monitoring:

`Source → Note → Topic/Event → Analysis → Risk → Evidence → Action`

Creator/content:

`KOS/KOC/UGC → Classification → Content → Influence → Risk → Evidence`

Content production:

`Template → Source → Draft → Fact Check → Risk Check → Human Review → Approved Output`

No layer may skip its preceding validation boundary merely for UI convenience.
