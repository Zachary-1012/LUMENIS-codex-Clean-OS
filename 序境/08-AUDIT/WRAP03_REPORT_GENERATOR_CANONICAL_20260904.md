# WRAP-03 Evidence｜report_center/report_generator.py 接入 Canonical 并消除 high/critical 口径分叉

- 日期：2026-09-04 ｜ 状态：**VERIFIED-IN-TEST**（随生产重载生效）
- 范围：`v4_upgrade/report_center/report_generator.py::ReportGenerator._calculate_stats` 五计数。

## 关键意义：消除 P0 审计发现的唯一口径分叉
- 改前 L131：`high_risk = risk_level in ('high','critical')`（与 daily_report/export 的 `=='high'` 不一致，潜在双真相）。
- 改后：统一走 `canonical_metrics.risk_count`，**high 只含 high（Q1 方案甲），critical 独立**。现网无 critical → 数字零变化；未来写入 critical 时不再被混入 high。

## 保留不动
- L133 total_engagement = likes + comments×2 加权传播分（非等权四字段，业务口径不同，保留）。
- positive_ratio/negative_ratio 百分比分母 total=len（报告口径，保留）。
- L139 复用 daily_report.calculate_risk_index（已在 WRAP-02 统一，自动继承 Canonical）。

## 新旧等价/差异验证（oracle 旧算法对比）
| 用例 | pos/neg/neu/medium/加权eng | high_risk |
|---|---|---|
| 真实全量 1052 | 全部一致 | 新23 = 旧23（crit=0，零变化）|
| 空集 | 一致 | 0=0 |
| critical 边界(2 critical+1 high) | 一致 | 新1 = 旧3 − 2 critical（方案甲预期差异）|

## 回归
report_center_route + report_deprecation + brand_report_master_model + report_periods 共 **30 项 PASS**。

## 回滚
`git revert <commit>`；不影响 WRAP-01/02 与 canonical_metrics 本体。
