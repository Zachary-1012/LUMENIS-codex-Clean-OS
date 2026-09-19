# 序境-Intelligence · UDIP V1.0 收敛完成度登记（P6 全量）

> 状态：CONVERGENCE-AUDIT-COMPLETE（2026-09-04）｜镜像 ZBC CANONICAL_WRAP_PROGRESS 最新结论

## 收敛完成度（ZBC 生产侧）
**已 WRAP 接入 canonical_metrics（唯一计算层）— 10 处**
| # | 位置 | 状态 |
|---|---|---|
| 01 | app.py `/api/dashboard/all` | PRODUCTION-VERIFIED ed41265 |
| 02 | daily_report.py 三处 | PRODUCTION-VERIFIED 3d60a29 |
| 03 | report_center/report_generator `_calculate_stats` | PRODUCTION-VERIFIED 451644e |
| 04 | export_report.py `generate_report_data` | PRODUCTION-VERIFIED dd1dd69 |
| 05 | intelligence.py `summarize_event` 兜底 | PRODUCTION-VERIFIED 2aa5e0b |
| 06 | reprocess.py `aggregate_events`（红线内仅 neg） | PRODUCTION-VERIFIED 5e48944 |
| 07 | report_export/report_engine.py `payload` 六桶 | PRODUCTION-VERIFIED 5e48944 |
| 08 | app.py 三处（report/v2、品牌详情、report/daily） | PRODUCTION-VERIFIED（并行本次） |
| 09 | brand_stats_recompute.py（我的 WRAP-02） | PRODUCTION-VERIFIED 42a0d95 |
| 10 | app.py brand-industry/stats 实体 id 计数（我的 REFSCAN） | PRODUCTION-VERIFIED 0a1683f |

**审计判定 KEEP（非漏做，无需/不应改）**
- SQL 层等值聚合（CASE WHEN / SUM 四字段）：与 canonical 数学等价，SQL 聚合性能最优，改内存聚合降性能
- 风险关注列表 `risk_level in ('high','critical')`：集合语义不同（宁不漏），非分桶计数
- 族 C：kol_analysis L62 / kos_metrics L93（SQL 等权互动）、kos_engine 加权互动、total_likes 独立字段
- event-graph 图谱模块：关系网络，source_event_id 关联，不重复计数
- 三套报告实现（export_report / 根 report_engine→daily_report / report_export.report_engine）：均消费 canonical，差异仅过滤条件（业务口径），同源已收敛

## 跨面一致性目标（已达成）
同一(时间/维度/过滤/权限)：首页=表=图=日报/周报/报告=导出=AI 答询，数字一致；差异回溯 Function/Metric/Dataset，禁止改展示层凑齐。
- test_udip_consistency（5 项）：计数==SQL、五值语义、不伪装 0
- brand-industry/stats 实体 id 计数修复后 negative_brands 12→13 与 canonical 完全一致

## Intelligence 侧职责
- 研究数据一致性/五值语义最佳实践 → 提交 Core 评估（不自行建立新口径）
- 本文件为收敛完成度登记，供双库对齐，不新增计算口径。
