# 序境｜报告母模型契约（Decision Information First）

- 状态：ACTIVE · 依据《序境｜双子库全量收敛与产品研发总执行指令》第十二节
- 日期：2026-09-04
- 原则：**Decision Information First** —— 报告首屏必须是决策信息，不是大段文字。

## 一、母模型结构（所有报告统一）

```
问题中心 Problem Center
   ↓
事件 Events
   ↓
影响 Impacts
   ↓
风险 Risks
   ↓
证据 Evidence
   ↓
建议 Decisions / Actions
```

**问题中心**：本报告要回答的核心问题（一句决策问题）
**事件**：驱动该问题的事实事件（时间/主体/标题/要点）
**影响**：事件对品牌/业务的实际影响（可量化优先）
**风险**：当前与潜在风险（级别/趋势/触发条件）
**证据**：每个结论的支撑数据与来源（可追溯）
**建议**：可执行决策（短期/中期/长期）

## 二、数据字段契约

```json
{
  "decision_model": {
    "problem_center": { "question": "", "context": "" },
    "events": [ { "date": "", "subject": "", "title": "", "summary": "" } ],
    "impacts": [ { "dimension": "", "direction": "up|down|flat", "detail": "", "evidence_ids": [] } ],
    "risks": [ { "level": "high|medium|low", "topic": "", "trigger": "", "trend": "rising|stable|falling" } ],
    "evidence": [ { "evidence_id": "", "kind": "note|event|metric|source", "summary": "", "url": "" } ],
    "decisions": { "short_term": [], "medium_term": [], "long_term": [] }
  }
}
```

## 三、与现有报告的关系

- 现有 v3.0 报告结构（执行摘要/品牌传播/市场情报/舆情/事件图谱/建议）**保留不删**。
- 新增 `decision_model` 层作为**决策优先层**，位于报告最前（首屏决策信息）。
- 未来报告（日报/周报/月报/专报/日报弹窗）统一消费本母模型。

## 四、验证标准

- 报告 JSON 必须含 `decision_model` 完整 6 节点。
- Markdown 报告首屏为「问题中心」章节。
- 关键结论必须有 `evidence` 引用。
