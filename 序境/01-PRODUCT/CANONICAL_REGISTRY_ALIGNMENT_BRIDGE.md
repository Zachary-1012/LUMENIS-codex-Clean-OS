# 序境-Core · Canonical Registry 对齐桥（UDIP V1.0 P6）

> 状态：ALIGNMENT-BRIDGE-DONE（2026-09-04）
> 背景：并行研发产生两套 Registry 编号并存：
> - 本文件 P0 建立 FUNCTION_REGISTRY（FUNC-RISK-01/02/03…）与 METRIC_REGISTRY（MET-RISK-01…）。
> - 并行会话（WRAP-01，commit ed41265）建立 `canonical_metrics.py`（FN-SENTIMENT-COUNT / FN-RISK-COUNT / FN-ENGAGEMENT，契约 OSAI CTR-CANONICAL-METRICS-P0-01）。
> 目的：**建立映射桥，消除双编号并存风险**，不删除任何一方实现，不推翻任何一方产物。

## 1. 双 Registry 语义对齐（权威映射）

| 并行侧 FN-*（canonical_metrics.py） | 本 P0 Registry（FUNCTION_REGISTRY） | Metric 消费 | 层级 |
|---|---|---|---|
| FN-SENTIMENT-COUNT | FUNC-CONTENT-01（情感三值计数） | MET-CONTENT-01 | 计数层（dashboard/all stats） |
| FN-RISK-COUNT（方案甲：high 独立/critical 独立） | FUNC-RISK-01（聚合 risk_index） | MET-RISK-01 | 计数层 → 指数层（下游） |
| FN-ENGAGEMENT | FUNC-CONTENT-02（互动聚合） | MET-CONTENT-02 | 计数层 |
| — | FUNC-RISK-02（brand_health_score） | MET-RISK-02 | 指数层（由 risk_index 派生） |

## 2. 权威边界（防双真相）
- **计数层权威**：`canonical_metrics.py`（FN-SENTIMENT/RISK/ENGAGEMENT）→ `/api/dashboard/all stats` 唯一实现（WRAP-01 已 PRODUCTION-VERIFIED）。
- **指数层权威**：`daily_report.generate_today_summary`（FUNC-RISK-01/02）→ `/api/metrics/canonical` + 报告 canonical 字段 + AI prompt（P2/P4/P5 已 PRODUCTION-VERIFIED）。
- **两者关系**：指数层消费计数层的**分层结果**（risk_level/sentiment），不重复计算单条；计数层不生产指数。层级清晰，非双真相。

## 3. 命名收敛约定（后续新代码）
- 新业务计算统一用 `FUNC-*`（Registry 规范 ID）+ 实现函数名标注 `FN-*` 契约 ID。
- 禁止再出现第三套编号；新增能力必须先在 FUNCTION_REGISTRY 登记。

## 4. Cross-Surface 一致性测试（P6 落地物）
- 新增 `tests/test_udip_consistency.py`：同一数据上验证：
  a) `canonical_metrics.sentiment_count/risk_count` 与 `/api/dashboard/all stats` 一致；
  b) `daily_report.generate_today_summary` 的 MET-RISK-01/02 与 `/api/metrics/canonical` 一致；
  c) 五值语义：无数据时区分 0 与 NULL/UNKNOWN（不伪装）。
- 目标：表=图=报告=导出=AI 对同一 Metric 取值一致；出现差异必须定位 Function/Metric/View，禁止改展示层数字对齐。

## 5. 状态
- 本文件为对齐桥文档；canonical_metrics.py / daily_report / FUNCTION_REGISTRY / METRIC_REGISTRY 均保留不动。
- 双库契约：OSAI `contracts/CTR-CANONICAL-METRICS-P0-01.md`（并行侧）与 ZBC `序境/01-PRODUCT/*_REGISTRY.md`（本侧）通过本桥互相引用、语义一致。
