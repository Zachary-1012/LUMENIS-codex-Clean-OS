# Canonical 统一管线 WRAP 进度矩阵（2026-09-04 起）

口径基线（Q1 方案甲，永久）：high 只计 risk_level=='high'，critical 独立不并入；情感三值精确、其余 unknown；FN-ENGAGEMENT=likes+comments+collects+shares 等权四字段；业务加权/两字段/差额法属不同 Metric，保留不强换。

## 已 WRAP（统一到 canonical_metrics 唯一计算层）
| # | 文件 / 位置 | 收敛的指标 | 明确保留（不同口径，勿强换） | 验证 | 状态 | Commit |
|---|---|---|---|---|---|---|
| 01 | app.py `/api/dashboard/all` | 情感/风险/等权互动（6 SQL→1 趟） | 输出 JSON 键结构零变化 | 回归+test_client+生产HTTP+浏览器 | PRODUCTION-VERIFIED | ed41265 |
| 02 | daily_report.py 三处 | risk_index/health/摘要纯分桶 | comments×2 加权传播分、赞+评两字段、比率分母 total=len | oracle(50.5/64.0)+40 回归 | PRODUCTION-VERIFIED | 3d60a29 |
| 03 | report_center/report_generator `_calculate_stats` | 五计数；**消除 high+critical 分叉** | comments×2 加权、百分比分母、复用 daily_report | oracle+30 回归 | PRODUCTION-VERIFIED | 451644e |
| 04 | export_report.py `generate_report_data` | 情感三计数+high | pending_neg 复合、负面优先排序、比率分母 | oracle+真实周/月/年 summary | PRODUCTION-VERIFIED | dd1dd69 |
| 05 | intelligence.py `summarize_event` 兜底 | neg/high | analyze_sentiment AI 链路、sample 不动 | oracle+14 回归 | PRODUCTION-VERIFIED | 2aa5e0b |
| 06 | reprocess.py `aggregate_events`（红线内） | 仅 neg 计数 | risk_score 阈值→risk_level 规则一字不动 | 29 测试+event_curation 脚本 | PRODUCTION-VERIFIED | 5e48944 |
| 07 | report_export/report_engine.py `payload` | 六桶（6 次 cnt→一次） | cnt 通用兜底、二次确认、发布日期过滤 | 四周期六桶全等 | PRODUCTION-VERIFIED | 5e48944 |
| 08 | app.py 三处：`/api/report/v2`、品牌详情、`/api/report/daily` | 情感三桶+high | v2 的 negative_count 取二次确认集合、品牌 neutral=total-pos-neg 差额法、daily 的 high 在负面子集计 | 表达式等价+34 回归+生产三路由 HTTP(stats 正常) | PRODUCTION-VERIFIED | 本次 |
| — | brand_stats_recompute.py | 巡检已先行 WRAP（含 Canonical==旧口径前置断言） | — | 复核一致 | 已完成（巡检） | 巡检 |

## 审计后判定 KEEP（不是漏做，是无需/不应改）
- **SQL CASE WHEN 趋势聚合**（app.py L2883/L3106/L4898/L4985，按 publish_date GROUP BY）：等值口径已与 Canonical 精确一致（='negative'、='high'，high 不含 critical）；改内存聚合反而降性能，KEEP。
- **风险关注列表筛选** `risk_level in ('high','critical')`（app.py L1555/L4175/L4178）：这是"待关注风险笔记集合"宁不漏，非 high 分桶计数，语义不同，KEEP。
- **根 report_engine.py**（112 行薄编排）：自身不计数，统计全部转发 daily_report（已 WRAP-02），自动继承，KEEP。
- app.py L1415 趋势点单值、L2625-2627 负面二次确认复合计数、L3603-3609 品类循环/fallback：结构特殊或复合业务，单点收益低，暂 KEEP（如需统一走 group_count 另开小批）。

## 待 WRAP
- [ ] 族 C KOS：kos_metrics / kol_analysis 四字段互动收敛 FN-ENGAGEMENT；kos_engine total_likes 仅 likes 归独立 FN-LIKES（不并入互动）
- [ ] 多端点 Reference Scan：/api/stats、/api/brand-stats、/api/brand-industry/stats 同源；evidence 两组；event-graph 两组
- [ ] 三套报告实现（export_report / 根 report_engine→daily_report / report_export.report_engine）口径差异 Reference Scan，只判同源收敛，不改数字

## Cross-Surface 一致性目标
同一(时间/维度/过滤/权限)：首页=表=图=日报/周报/报告=导出=AI 答询，数字必须一致；差异回溯 Function/Metric/Dataset，禁止改展示层凑齐。
