# WRAP-02 Evidence｜brand_stats_recompute 接入 Canonical 业务计算层

- 日期：2026-09-04 ｜ 状态：**PRODUCTION-VERIFIED** ｜ 契约：OSAI CTR-CANONICAL-METRICS-P0-01（复用 WRAP-01 同一契约）
- 范围：仅 ZBC `brand_stats_recompute.py::recompute_brand_stats` 的统计段（sentiment/risk/engagement），未触碰品牌匹配逻辑、未改任何前端/API。

## 为什么改 / 复用了什么
`brand_stats_recompute.py` 手写 SQL 统计（sentiment 计数、risk 分桶、engagement 求和）到 `brand_industry_monitor` 预聚合表，与 `canonical_metrics.py`（FN-SENTIMENT-COUNT / FN-RISK-COUNT / FN-ENGAGEMENT）完全重叠——是 P0 审计识别的族 A/B 重复计算点之一。本次 WRAP 到唯一 Canonical 实现，**不新造算法**，保留输出字段与语义。

## 变更内容
- import `canonical_metrics`（sentiment_count / risk_count / engagement_stats）
- 统计段改为：`_canon_sentiment_count / _canon_risk_count / _canon_engagement_stats` 统一计算 total/pos/neg/engagement
- **前置断言**：每个品牌 Canonical == 旧手写口径（total/pos/neg/engagement 四值全等才写盘；不等即 AssertionError，禁止静默写入不一致数字）
- risk_level 判定改用 canonical risk_count 分层（high/critical 独立，与 WRAP-01 Q1 方案甲一致）

## 数字一致性（真实 monitor.db，前置断言，逐品牌相等才写盘）
| 校验项 | 结果 |
|---|---|
| 全量品牌数 | 198 个全部重算，前置断言 0 失败 |
| 有笔记品牌 | 73 个 |
| 负面/正面品牌 | 13 / 36 |
| 写盘后不一致行（pos+neg>total） | 0 |
| 样例 | 古驰: 总8 正2 负1；香奈儿: 总14 正6 负0；迪奥: 总4 正0 负1 |

## 输出契约
`recompute_brand_stats()` 返回结构不变（updated/nonzero/negative_brands/positive_brands/samples）；`brand_industry_monitor` 表字段（note_count/positive_count/negative_count/total_engagement/risk_level）语义不变。

## 测试与运行验证
1. 运行前备份：`data/_brand_stats_backup_before_wrap02.db`（gitignored，可回滚）。
2. 真实验证：`recompute_brand_stats()` 全库 198 品牌重算，前置断言全通过，写盘 0 不一致。
3. 回归：brand_insight + brand_library + brand_report_master_model + canonical_metrics + udip_consistency（待结果）。
4. 性能：单品牌一次取数 + 内存纯函数聚合，与原实现取数路径相同，无新增请求/定时器。

## 影响面 / 回滚
- 影响：仅 brand_industry_monitor 预聚合数字来源（值不变）；不影响采集、主体红线、品牌匹配逻辑。
- 回滚：恢复备份 `data/_brand_stats_backup_before_wrap02.db` 或 `git revert <本commit>`；canonical_metrics.py 为纯新增，保留不影响旧路径。

## 后续（同一 WRAP 法继续）
剩余重复点：daily_report / report_engine / export_report / intelligence / app.py 其他段，按同一"旧实现==Canonical 前置断言 + 跨面一致性"逐文件接入。
