# 学习：报告 API 收敛方案（GAP-10）+ 智谱第2次分析（2026-09-03）

> 来源：ZBC GAP-10 报告路由收敛 + 智谱 glm-4.5-air 深度分析（per_call 第 2 次）

## 本轮学到什么

1. **报告体系现状**：app.py 17 个报告路由，8 个是重复实现（brand-report/report.daily/report.generate/report.export/v2 等），6 个独立能力（reports 列表/verify/special-report 系列/旁路 preview）。新 report_center（ReportGenerator/ReportExporter）已建但旁路未接管。

2. **API 收敛方法论**（可复用）：
   - 聚类：把 17 路由按功能归为"重复实现"和"独立能力"
   - 定唯一 Owner：标准化报告归 report_center；特殊报告（special-report）保留独立
   - 安全接管：旁路 + Feature Gate 默认关 → 标 deprecated（X-Deprecated 头）→ 验证无调用方 → 退役
   - 绝不直接删路由，先保留兼容

3. **关键原则**：特殊业务（special-report 有独特触发/生成逻辑）不能一刀切并入统一 Owner；Owner 接管前必须与现有 RPT Owner 对齐防双写。

## 对 Zachary 的启示

- 收敛 = 聚类 + Owner + 渐进退役，不是"删旧代码"。
- 任何"统一平台"都应先有旁路验证 + Feature Gate，再逐步接管，保证可回滚。
- 特殊业务与标准化能力分离，是避免误伤的护栏。

## 产物

- ZBC: `docs/learning/REPORT-CONVERGENCE-PLAN-20260903.md`
- 智谱分析原文: `staging/_report_review_result.txt`（临时）
- 状态：方案已定，本轮只登记不施工（GAP-10 为 P2，待用户签字）
