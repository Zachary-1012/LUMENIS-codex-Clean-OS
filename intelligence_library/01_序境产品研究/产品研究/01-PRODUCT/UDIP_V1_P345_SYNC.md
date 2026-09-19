# 序境-Intelligence · UDIP V1.0 P3/P4/P5 登记

> 状态：MIRROR-SYNC（2026-09-04）
> 生产实现以 ZBC（序境-Core）为准；本文件为 Intelligence 侧研究/评估登记。

## P3 Visualization Registry（已落 ZBC `序境/01-PRODUCT/VISUALIZATION_REGISTRY_V1.md`）
- 登记 8 个可视化视图（VIS-TREND-01/DONUT-01/RANKING-01/RISK-01/HEALTH-01/TIMELINE-01/KPI-01/DRILL-01）。
- 新增 canonical 视图：VIS-RISK-01（风险指数卡）、VIS-HEALTH-01（品牌健康度卡），消费 `/api/metrics/canonical`。
- 原则：可视化只消费 Canonical Dataset/Metric；Renderer 不隐藏业务计算；动态状态映射到现有链路不新建框架。

## P4 报告统一消费 Canonical（已落 ZBC app.py）
- `api_report_v2` 响应新增 `canonical` 字段：MET-RISK-01/02 由 `_canonical_report_metrics()` 权威计算（消费 daily_report.generate_today_summary），不重复计算业务 Truth。
- 保留现有 `stats`（原始计数）不动，前端不受影响；两语义显式区分。

## P5 AI 语义层接入（已落 ZBC app.py）
- `api_ai_chat` 注入 canonical 指标摘要：AI 回答风险/健康度问题时**只引用、不重算** MET-RISK-01/02。
- AI 边界保持：Registry → Permission → Policy → Execute → Verify → Evidence → Audit；AI 无 Production Write。

## Intelligence 侧待办
- 研究可视化/数据叙事最佳实践 → 作为 RECOMMENDATION 提交 Core（供 VIS-* 迭代参考）。
- 评估是否需要把 VIS-TREND/DONUT/RANKING 逐步迁移到 Canonical 数据集（评估收益与回归成本后再定）。
