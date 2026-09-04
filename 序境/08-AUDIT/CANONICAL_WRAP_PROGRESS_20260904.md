# Canonical 统一管线 WRAP 进度矩阵（2026-09-04 起）

口径基线（Q1 方案甲，永久）：high 只计 risk_level=='high'，critical 独立不并入；情感三值精确、其余 unknown；FN-ENGAGEMENT=likes+comments+collects+shares 等权四字段；业务加权/两字段指标属不同 Metric，保留不强换。

| # | 文件 / 位置 | 收敛的指标 | 明确保留（不同口径） | 验证 | 状态 | Commit |
|---|---|---|---|---|---|---|
| 01 | app.py `/api/dashboard/all` stats 段 | 情感三桶/风险三桶/等权互动（6 趟 SQL→1 趟） | 输出 JSON 键结构零变化 | 30 回归+test_client+生产 HTTP+浏览器截图 | PRODUCTION-VERIFIED | ed41265 |
| 02 | daily_report.py 三处 | risk_index/health/今日摘要的纯情感、风险分桶 | comments×2 加权传播分、赞+评两字段健康度、比率分母 total=len | oracle 等价(50.5/64.0)+40 回归 | PRODUCTION-VERIFIED(重载) | 3d60a29 |
| 03 | report_center/report_generator.py `_calculate_stats` | 五计数；**消除 high in(high,critical) 分叉** | comments×2 加权、百分比分母、复用 daily_report | oracle+30 回归，critical 边界方案甲正确 | PRODUCTION-VERIFIED(重载) | 451644e |
| 04 | export_report.py `generate_report_data` | 情感三计数+high | pending_neg 复合计数、负面优先排序、比率分母 | oracle+真实 weekly/monthly/yearly summary+回归 | PRODUCTION-VERIFIED(重载) | dd1dd69 |
| 05 | intelligence.py `summarize_event` 规则兜底 | neg/high（AI 失败兜底文案） | analyze_sentiment 的 AI 分析、sample 字段不动 | oracle(97/23)+14 回归 | VERIFIED-IN-TEST | 本次 |
| 06 | brand_stats_recompute.py `recompute_brand_stats` | 情感三桶/风险分桶/等权互动（逐品牌预聚合） | 品牌 LIKE 匹配口径不动、risk 判定逻辑保留（neg 驱动） | 198 品牌逐品牌前置断言 Canonical==旧口径 0 失败 + 写盘 0 不一致 + brand 回归 EXIT=0 + 备份可回滚 | PRODUCTION-VERIFIED | 42a0d95 |

## 待 WRAP（族 A/B/C 剩余，逐文件走同一 SOP）
- [x] brand_stats_recompute.py L77 区（#06 已完成）
- [ ] reprocess.py L124（mentions 维度，注意输入集）
- [ ] report_export/report_engine.py L92 cnt
- [ ] app.py 其余 stats 段：L1480 品类循环 / L1651 cnt / L2242 / L2299 negative_review / L2499 / L2805 SQL / L2904-2908 SQL
- [ ] 族 C：kos_metrics / kol_analysis 四字段互动收敛 FN-ENGAGEMENT；kos_engine total_likes 仅 likes 归独立 FN-LIKES（不并入互动）
- [ ] 多端点 Reference Scan：/api/stats、/api/brand-stats、/api/brand-industry/stats 同源关系；evidence 两组；event-graph 两组

## Cross-Surface 一致性目标
同一(时间/维度/过滤/权限)下：首页 = 表 = 图 = 日报/周报/报告 = 导出 = AI 答询，数字必须一致；差异回溯 Function/Metric/Dataset，禁止改展示层凑齐。
