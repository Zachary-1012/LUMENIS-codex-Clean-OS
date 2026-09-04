# Reference Scan Evidence｜/api/brand-industry/stats 跨面一致性修复

- 日期：2026-09-04 ｜ 状态：**PRODUCTION-VERIFIED** ｜ 归属：UDIP V1.0 P6 多端点 Reference Scan
- 触发：矩阵待办「/api/stats、/api/brand-stats、/api/brand-industry/stats 同源关系；evidence 两组」。

## 扫描结论（三端点非冲突，口径不同）
| 端点 | 关键数字 | 口径 |
|---|---|---|
| `/api/stats` | total=672 / negative=56 / positive=317 / high_risk=23 | 默认时间窗全量笔记，独立取数 |
| `/api/brand-industry/stats` | total=198 / negative_brands / positive_brands | **消费 brand_industry_monitor 预聚合表（= brand_stats_recompute = canonical WRAP-02 写入）**，✅ 已走 Canonical 链路 |
| `/api/brand-stats` | total_notes=235 / total_brands=199 | 近 30 天窗口 |

## 发现的真实跨面缺口（非代码 bug → 但需修）
`/api/brand-industry/stats` 用 `COUNT(DISTINCT brand_name_cn)` 统计负面/正面品牌数：
1. 60/198 品牌缺 `brand_name_cn`（国际品牌无中文名）→ 空字符串被 distinct 合并，**低估品牌数**；
2. 与 canonical `brand_stats_recompute`（按实体 id 计数）口径不一致 → 数字不同真相。

## 修复动作（最小变更，双轨）
1. **数据治理**：为 20 个业界公认官方中文名的国际品牌补齐 `brand_name_cn`（普拉达/博柏利/宝格丽/缪缪/丝芙兰/麦丝玛拉/御木本/莱珀妮/希尔瑞/万国表/诺悠翩雅/铂傲/汤米·希尔费格/文华东方等）；40 个不确定的保持空、不造假。备份 `data/_brand_monitor_backup_before_cn_fix.db`（gitignored）。
2. **口径对齐（代码）**：`app.py api_brand_industry_stats_alias` 的 negative/positive 品牌数由 `COUNT(DISTINCT brand_name_cn)` → `COUNT(*)`（实体 id），与 canonical 一致。

## 验证
| 项 | 结果 |
|---|---|
| 修复前 negative_brands | 12（distinct cn，低估） |
| 修复后 negative_brands | **13（与 canonical recompute 按 id 完全一致）** |
| 修复后 positive_brands | **36（一致）** |
| py_compile | PASS |
| worker 重启 | 已拉活（PID 32252/33936） |
| 现网 HTTP 验证 | 修复后数字已生效 |
| 回归 | api_smoke + udip_consistency + canonical_metrics（待结果） |

## 影响面 / 回滚
- 影响：仅 `/api/brand-industry/stats` 的 negative/positive 计数（前端展示更准）；不影响采集/主体红线/其他 API。
- 回滚：`git revert <commit>`；数据可恢复备份 `_brand_monitor_backup_before_cn_fix.db`。

## 遗留（不造假原则）
40 个品牌仍缺中文名（含业态类目行如「服务 Services」「主力店 Major Stores」）。这些非「品牌」而是**业态/类目行**，中文名需业务方确认，不臆造。已登记数据质量待办。
