# Canonical 统一管线 WRAP 进度矩阵（2026-09-04 起）

口径基线（Q1 方案甲，永久）：high 只计 risk_level=='high'，critical 独立不并入；情感三值精确、其余 unknown；FN-ENGAGEMENT=likes+comments+collects+shares 等权四字段；业务加权/两字段指标属不同 Metric，保留不强换。

| # | 文件 / 位置 | 收敛的指标 | 明确保留（不同口径） | 验证 | 状态 | Commit |
|---|---|---|---|---|---|---|
| 01 | app.py `/api/dashboard/all` stats 段 | 情感三桶/风险三桶/等权互动（6 趟 SQL→1 趟） | 输出 JSON 键结构零变化 | 30 回归+test_client+生产 HTTP+浏览器截图 | PRODUCTION-VERIFIED | ed41265 |
| 02 | daily_report.py 三处 | risk_index/health/今日摘要纯情感、风险分桶 | comments×2 加权传播分、赞+评两字段健康度、比率分母 total=len | oracle(50.5/64.0)+40 回归 | PRODUCTION-VERIFIED | 3d60a29 |
| 03 | report_center/report_generator.py `_calculate_stats` | 五计数；**消除 high in(high,critical) 分叉** | comments×2 加权、百分比分母、复用 daily_report | oracle+30 回归，critical 边界方案甲正确 | PRODUCTION-VERIFIED | 451644e |
| 04 | export_report.py `generate_report_data` | 情感三计数+high | pending_neg 复合计数、负面优先排序、比率分母 | oracle+真实 weekly/monthly/yearly summary+回归 | PRODUCTION-VERIFIED | dd1dd69 |
| 05 | intelligence.py `summarize_event` 规则兜底 | neg/high（AI 失败兜底文案） | analyze_sentiment 的 AI 分析、sample 字段不动 | oracle(97/23)+14 回归 | VERIFIED-IN-TEST | 2aa5e0b |
| 06 | reprocess.py `aggregate_events`（**红线函数内**） | 仅 neg 计数表达式 | risk_score 连续分阈值→risk_level 推导规则一字不动；事件聚合权威逻辑不动 | 构造等价+event_aggregation_authority 等 29 测试+event_curation 脚本全过 | VERIFIED-IN-TEST | 本次 |
| 07 | report_export/report_engine.py `payload` | 情感三桶+风险三档（6 次 cnt→一次 Canonical） | cnt 通用分桶函数保留兜底；confirmed_negative、严格发布日期过滤、周月报二次确认口径不动 | 四周期(0/82/310/822)六桶新旧全等+回归 | VERIFIED-IN-TEST | 本次 |
| — | brand_stats_recompute.py | 巡检已先行 WRAP（顶部 import canonical、内置 Canonical==旧口径前置断言） | — | 现状复核一致 | 已完成（非本轮） | 巡检提交 |

## 待 WRAP（族 A/B/C 剩余，逐文件走同一 SOP）
- [ ] app.py 其余 stats 段：L1480 品类循环 / L1651 cnt / L2242 / L2299 negative_review / L2499 / L2805 SQL / L2904-2908 SQL
- [ ] 族 C：kos_metrics / kol_analysis 四字段互动收敛 FN-ENGAGEMENT；kos_engine total_likes 仅 likes 归独立 FN-LIKES（不并入互动）
- [ ] 多端点 Reference Scan：/api/stats、/api/brand-stats、/api/brand-industry/stats 同源关系；evidence 两组；event-graph 两组
- [ ] 两套报告引擎口径差异（export_report 与 report_export/report_engine 的 notes 过滤口径不同）登记 Reference Scan，只判同源/收敛，不在 WRAP 中改数字

## 多端点 Reference Scan 结果（2026-09-04，已执行）
三端点时间窗/口径不同，非同源冲突；数字差异均可归因：
| 端点 | 关键数字 | 口径 | 结论 |
|---|---|---|---|
| `/api/stats` | total=672 / negative=56 / positive=317 / high_risk=23 | 默认时间窗全量笔记 | 独立取数（与 brand 无关） |
| `/api/brand-industry/stats` | total=198 / negative_brands=12 / positive_brands=32 | **消费 brand_industry_monitor 预聚合表（=brand_stats_recompute=canonical WRAP-02 写入）** | ✅ 已间接走 Canonical 链路 |
| `/api/brand-stats` | total_notes=235（近30天）/ total_brands=199 | 30 天窗口 | 不同时间窗，独立 |

**发现的真实数据质量项**（非代码 bug）：`/api/brand-industry/stats` 用 `COUNT(DISTINCT brand_name_cn)` 计数负面/正面品牌，而 PRADA(id=11)、i.t(id=71) 的 `brand_name_cn=''`（缺中文名）→ 空字符串被 distinct 合并，导致 negative_brands=12 < recompute 按 id 口径的 13。**recompute(canonical) 的 13 是正确实体口径**；端点 distinct-cn 在缺中文名时低估。修复需补齐品牌中文名（业务数据，非改代码），已登记数据质量待办。

## Cross-Surface 一致性目标
同一(时间/维度/过滤/权限)下：首页 = 表 = 图 = 日报/周报/报告 = 导出 = AI 答询，数字必须一致；差异回溯 Function/Metric/Dataset，禁止改展示层凑齐。
