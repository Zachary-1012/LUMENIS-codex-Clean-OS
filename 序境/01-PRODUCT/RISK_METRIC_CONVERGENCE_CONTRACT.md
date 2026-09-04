# 序境-Core · risk_index 双真相收敛方案（Contract，不改生产）

> 状态：P0-2 DESIGN-DONE（2026-09-04；仅定义 Contract，不改生产代码）
> 背景：UDIP V1.0 Inventory 审计发现两套风险算法并存：
> - **A** `daily_report.py::calculate_risk_index`（FUNC-RISK-01 / MET-RISK-01）— 聚合级，5 维加权 0-100
> - **B** `ai_analyzer.py::assess_risk`（FUNC-RISK-03 / MET-RISK-03）— 笔记级，high×25+med×10 0-100
> 目标：统一语义、消除"两个风险数字"，但不删任何既有生产能力（先定 Contract，再渐进迁移）。

---

## 1. 现状事实（审计确认）

| 项 | A（聚合风险） | B（笔记风险） |
|---|---|---|
| 位置 | daily_report.py | ai_analyzer.py |
| 层级 | 品牌/日期聚合（0-100） | 单笔记（0-100） |
| 输入 | notes 集合 + events | 单条 title/content/互动 |
| 消费方 | 日报/周报风险指数、告警 | notes.risk_score、负评确认流、事件关联 |
| 写入 | 计算结果供报告 | notes 表 risk_score 字段 |
| 关系 | **由 B 的分层信号派生，但算法独立** | 底层信号 |

## 2. 收敛 Contract（统一语义）

### 2.1 语义分层（不冲突，是层级关系）
```
MET-RISK-03 单笔记风险分（raw 信号，0-100）   ← 感知层：单条内容风险
        ↓ 聚合（Aggregate：按风险等级加权、负面占比、多来源……）
MET-RISK-01 聚合风险指数（0-100）             ← 决策层：品牌/日期舆情风险
```

### 2.2 关键定义（防"两个真相"）
- **MET-RISK-03（notes.risk_score）**：保持现状为"单笔记风险信号"，由 ai_analyzer 写入，**是唯一笔记级风险权威**。
- **MET-RISK-01（risk_index）**：保持现状为"品牌聚合风险"，由 daily_report 计算，**是唯一聚合级风险权威**。
- **禁止**：任何页面/图表/报告用 MET-RISK-03 当 MET-RISK-01 展示，或反之；两者在同一展示面必须显式标注层级（"单篇风险" vs "品牌风险指数"）。
- **禁止**：任何新模块再新增第三套"风险"算法。

### 2.3 派生关系声明（Lineage 标注）
```
MET-RISK-01 = f(MET-RISK-03 分布, events 状态, 互动, 持续时间, 多来源)
           ↑ 依赖 notes.risk_level（由 MET-RISK-03 映射 low/med/high）+ notes.sentiment
```
即：MET-RISK-01 消费 MET-RISK-03 的**分层结果**（risk_level），不重复计算单篇风险。这使 B 是 A 的下游输入，语义闭环而非双真相。

### 2.4 收敛动作（分阶段，本期不做）
1. **本期（P0-2）**：仅登记 Contract + Lineage 声明（本文档）。
2. **P1**：在 `daily_report.py` 聚合处加显式注释/命名（不改逻辑）——声明"本函数消费 MET-RISK-03 的 risk_level 分层"。
3. **P2**：前端/报告展示时，两指标同时出现处加层级标签（"单篇风险" / "品牌风险指数"），消除视觉混淆。
4. **验收**：同一时间窗下，前端/表格/图表/报告/导出/AI 对 MET-RISK-01 的取值完全一致；对 MET-RISK-03 的取值完全一致。差异即违规。

## 3. 五值语义补充（防伪装 0）
- notes 无风险命中 → risk_score 应为真实低值或 NULL，**不得用 0 冒充"已评估为无风险"**。
- 空 notes 聚合 → MET-RISK-01 返回 None/UNKNOWN（调用方判空），不得回退 0。

## 4. 一致性测试（Cross-Surface）
同一品牌+同一天：
- `MET-RISK-01`：日报 = 周报汇总口径 = 前端 Dashboard = 导出 = AI 回答，值必须一致。
- `MET-RISK-03`：笔记详情 = 事件关联 = 列表页，值必须一致。
出现差异 → 按 UDIP V1.0 §17 定位 Function/Metric/View/Filter/TimeWindow，**禁止改展示层数字对齐**。

## 5. 结论
两套算法**不是竞争双真相，而是层级关系**：单篇风险（B）→ 聚合风险（A）。本期已用 Contract 固定该语义，无需删除任何生产代码；后续仅做消费端标签与一致性验证。
