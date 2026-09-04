# 序境-Core · Visualization Registry（UDIP V1.0 P3）

> 状态：VIS-REGISTRY-DONE（2026-09-04）
> 原则：可视化只能消费 Canonical Dataset / Metric；Renderer 不得隐藏业务计算；用户筛选条件由 View Model / Query 状态驱动。

## 1. 可视化视图登记（现状 Inventory）

| VIS-ID | 视图 | 前端载体 | 数据源 API | Canonical 状态 |
|---|---|---|---|---|
| VIS-TREND-01 | 舆情趋势 | renderTrend (app.js) | /api/overview (notes 计数) | 原始计数（非 canonical，登记待统一） |
| VIS-DONUT-01 | 情感占比 | renderDonut (app.js) | /api/dashboard/all → stats | 原始计数（非 canonical） |
| VIS-RANKING-01 | 热门话题排行 | renderTopics (app.js) | /api/hot-topics | 原始计数（非 canonical） |
| VIS-RISK-01 | 风险指数卡 | loadCanonicalMetrics (app.js) | /api/metrics/canonical | **Canonical（MET-RISK-01）** |
| VIS-HEALTH-01 | 品牌健康度卡 | loadCanonicalMetrics (app.js) | /api/metrics/canonical | **Canonical（MET-RISK-02）** |
| VIS-TIMELINE-01 | 事件时间线 | ui_interactions_v5.8.0.js renderTrendChart | /api/events | 事件数据（事件 Truth） |
| VIS-KPI-01 | 顶部指标卡 | app.js 指标卡 | /api/dashboard/all stats | 原始计数 |
| VIS-DRILL-01 | 证据下钻 Drawer | app.js openNote/Evidence | /api/notes + evidence_api | 证据层（Evidence Truth） |

## 2. Canonical 消费边界（硬规则）
- **新增可视化**：必须标注消费的 MET-* / 数据契约；禁止页面内嵌业务公式。
- **已有可视化**：登记为"原始计数（非 canonical）"，在 P2 之后的迭代中逐步改为消费 Canonical 数据集；**本期不强行改写**（避免破坏生产稳定）。
- **风险/健康度**：唯一 Canonical 出口 = `/api/metrics/canonical`（MET-RISK-01/02）；前端/报告/导出/AI 一律消费该出口。

## 3. 动态可视化状态模型（映射到现有，不新建框架）
```
INPUT → DETECTED → VERIFIED → CLASSIFIED → CORRELATED → IMPACT/RISK → DECISION → ACTION → FEEDBACK
```
- 前端已有实现映射：采集信号（notes 入库）→ 风险卡（MET-RISK-01）→ 事件卡（events）→ 告警弹窗（alerts）→ 行动按钮 → 反馈（Evidence）。
- 不在任何视图额外新增一套状态框架。

## 4. 一致性约束
- 同一 Metric 在 Dashboard / Table / Chart / Report / Export / AI 下取值必须一致（Cross-Surface）。
- 前端图表若与 canonical 卡同屏出现计数口径（total/negative/high），必须显式区分"计数"与"指数"语义，不互相冒充。

## 5. 本期 P3 交付
- 本 Registry 落盘（登记现状 + 边界规则）。
- 新增 canonical 可视化（风险指数卡 / 品牌健康度卡）已在 P2 落地（VIS-RISK-01 / VIS-HEALTH-01）。
- 后续 P3 迭代：把 VIS-TREND-01 / VIS-DONUT-01 等逐步迁移到 Canonical 数据集视图。
