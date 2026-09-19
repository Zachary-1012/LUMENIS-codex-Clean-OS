# KOS 内容生产最终可执行规范

**Status:** FINAL / implementation authority
**Date:** 2026-09-04
**Scope:** KOS research, planning, copy generation, review, publishing and feedback loop

> 本规范中的 KOS 指产品既定的 KOS 运营/内容体系。不得把 KOS 做成泛化的内容生成器。

## 1. KOS 总链路

```text
Topic / Brand / Campaign Input
        ↓
Context & Knowledge Retrieval
        ↓
Audience / Platform / Goal Definition
        ↓
Content Strategy
        ↓
Template Selection
        ↓
Copy Generation
        ↓
Rule Validation
        ↓
Human Review / Approval
        ↓
Publish-ready Asset
        ↓
Publishing / Scheduling
        ↓
Monitoring
        ↓
Comment / Feedback Analysis
        ↓
Learning Sample
        ↓
Template / Strategy Optimization
```

AI 可以生成与建议，但不得绕过规则、审核和既定发布流程直接改变生产事实。

## 2. 内容对象层级

```text
Campaign
 ├── Topic
 ├── Content Series
 │    ├── Post
 │    │    ├── Title
 │    │    ├── Hook
 │    │    ├── Body
 │    │    ├── CTA
 │    │    ├── Hashtags
 │    │    └── Visual Brief
 │    └── Video Script
 ├── KOS Persona
 ├── Comment Strategy
 └── Performance Feedback
```

## 3. 每条内容必须先建立 Brief

标准 Brief：

```text
content_id
campaign_id
platform
content_type
target_audience
communication_goal
core_message
supporting_points
tone
persona
forbidden_claims
keywords
cta
visual_direction
reference_evidence
version
```

Brief 未完成，不进入生成阶段。

## 4. 文案模板体系

### A. 小红书种草 / 体验型

```text
Hook
↓
真实场景
↓
个人感受 / 体验
↓
具体细节
↓
价值判断
↓
轻 CTA
```

### B. 情绪 / 共鸣型

```text
情绪切口
↓
生活瞬间
↓
用户共鸣
↓
品牌/内容自然出现
↓
余韵
```

### C. 知识 / 信息型

```text
问题
↓
结论
↓
证据
↓
解释
↓
行动建议
```

### D. 活动预热型

```text
事件钩子
↓
为什么值得关注
↓
关键体验
↓
时间/地点/参与方式
↓
CTA
```

### E. 视频短脚本

```text
0–3s Hook
↓
3–10s Context
↓
10–25s Core Story
↓
25–40s Emotional / Information Peak
↓
40–60s Payoff + CTA
```

实际时长由平台与内容类型参数决定，不得硬编码为所有视频相同。

## 5. 标题模板

标题生成不是随机改写。

模板维度：

```text
Emotion
Curiosity
Scene
Benefit
Contrast
Identity
Question
Time / Event
```

生成时记录：

```text
title_template_id
title_variant
keyword_set
generation_model
prompt_version
```

## 6. 正文模板字段

```text
opening_hook
context
main_body
proof_or_detail
emotional_payoff
cta
hashtags
```

每个字段都有明确职责，不允许把所有文字塞进一个 prompt 后不可解释地生成。

## 7. KOS 人设模板

每个 KOS 账号必须有：

```text
persona_id
persona_name
platform
audience
content_pillars
voice
sentence_style
preferred_topics
forbidden_topics
commercial_boundary
visual_style
cta_style
```

人设必须稳定；同一账号不能每篇内容随机改变语言人格。

## 8. 评论回复模板

评论处理链：

```text
New Comment
↓
Classify
├── Positive
├── Neutral
├── Question
├── Complaint
├── Risk
└── Spam
↓
Generate Suggested Reply
↓
Rule Check
↓
Auto / Human Approval according to policy
↓
Reply
↓
Record Outcome
```

回复模板：

### Positive
```text
感谢 / 共鸣
＋具体回应
＋自然延伸
```

### Question
```text
直接回答
＋必要补充
＋避免过度营销
```

### Complaint
```text
承接情绪
＋事实回应
＋解决路径
```

### Risk
```text
不争辩
＋不扩大
＋升级人工审核
```

系统必须允许设置“自动回复 / 建议回复 / 必须人工”的策略。

## 9. 文案质量检查

生成后必须检查：

```text
[ ] 是否符合 Brief
[ ] 是否符合 Persona
[ ] 是否符合平台语言
[ ] 是否包含未经证实的事实
[ ] 是否存在夸大承诺
[ ] 是否重复
[ ] 是否出现禁用词
[ ] CTA 是否合理
[ ] 标题与正文是否一致
[ ] 文案是否与视觉 Brief 一致
```

## 10. 内容版本管理

每次生成保存：

```text
content_id
version
prompt_version
model_version
template_id
input_context
output
validation_result
human_revision
final_text
approved_at
```

不能只保存最终文案，否则无法学习。

## 11. 数据反馈闭环

内容发布后进入：

```text
Impression
→ Engagement
→ Comment
→ Sentiment
→ Conversion / Goal Metric
```

最终反馈回到：

```text
Template Performance
Persona Performance
Topic Performance
Hook Performance
CTA Performance
```

用于下一轮模板排序与推荐。

## 12. 模板选择逻辑

不要随机选择模板。

模板选择至少考虑：

```text
platform
content_goal
audience
campaign_stage
persona
historical_performance
risk_level
```

可以形成：

`Template Score = weighted performance + context fit - risk penalty`

具体权重必须配置化并记录版本，不允许散落在前端代码里。

## 13. KOS 与数据系统连接

KOS 不直接读取未经处理的原始采集数据。

正确链路：

```text
Raw Monitoring Data
↓
Validation / Normalization
↓
Canonical Table
↓
Metrics / Insight Functions
↓
KOS Strategy Input
↓
Template Selection
↓
Copy Generation
```

这样内容策略使用的是经过计算、验证的事实，而不是前端临时统计。

## 14. 人机协作边界

```text
AI：检索、分类、生成、建议、评分
程序：规则、计算、校验、状态机、审计
人：关键判断、风险拍定、最终批准
```

高风险内容必须进入人工审核。

## 15. 最终验收

```text
[ ] Brief 完整
[ ] 模板可追溯
[ ] Persona 可追溯
[ ] Prompt 版本可追溯
[ ] Model 版本可追溯
[ ] 生成结果可追溯
[ ] 校验结果可追溯
[ ] 人工修改可追溯
[ ] 最终版本可追溯
[ ] 发布状态可追溯
[ ] 评论策略可配置
[ ] 发布后数据回流
[ ] 模板效果可评估
[ ] 高风险内容有人审
```

## 16. 禁止事项

- 不允许一个超级 Prompt 包办 Brief、策略、文案、审核和发布
- 不允许前端直接修改内容事实
- 不允许没有版本号的模板进入生产
- 不允许没有 Persona 约束的 KOS 自动批量生成
- 不允许把真实数据与 AI 推测混在一起
- 不允许自动回复绕过风险规则
- 不允许为了追求数量牺牲内容质量与品牌边界
