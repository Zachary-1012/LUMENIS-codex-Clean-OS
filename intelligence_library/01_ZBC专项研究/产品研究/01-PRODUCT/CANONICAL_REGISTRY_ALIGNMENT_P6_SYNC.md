# 序境-Intelligence · Canonical Registry 对齐桥（P6）登记

> 状态：MIRROR-SYNC（2026-09-04）
> 并行研发产生两套编号，本登记确认对齐方案（映射而非覆盖），生产实现以 ZBC 为准。

## 对齐结论
- 计数层权威：`canonical_metrics.py`（FN-SENTIMENT-COUNT / FN-RISK-COUNT / FN-ENGAGEMENT）→ `/api/dashboard/all stats`（WRAP-01，PRODUCTION-VERIFIED）。
- 指数层权威：`daily_report.generate_today_summary`（FUNC-RISK-01/02）→ `/api/metrics/canonical` + 报告 + AI（P2/P4/P5）。
- 关系：指数层消费计数层的**分层结果**，不重复计算单条；计数层不生产指数。
- 映射桥：ZBC `序境/01-PRODUCT/CANONICAL_REGISTRY_ALIGNMENT_BRIDGE.md`。

## 命名收敛约定（双库一致）
- 新业务计算统一 `FUNC-*`（Registry 规范 ID）+ 实现函数标注 `FN-*`（契约 ID）。
- 禁止第三套编号；新增能力必须先在 FUNCTION_REGISTRY 登记。

## Intelligence 侧职责
- 对 canonical_metrics / daily_report 的口径差异做评估时，先引用本桥，不自行建立新口径。
- 研究数据一致性/五值语义最佳实践 → 提交 Core 评估。
