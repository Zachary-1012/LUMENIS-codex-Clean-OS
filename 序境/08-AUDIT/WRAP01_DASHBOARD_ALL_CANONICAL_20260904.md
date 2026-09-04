# WRAP-01 Evidence｜/api/dashboard/all 接入 Canonical 业务计算层

- 日期：2026-09-04 ｜ 状态：**PRODUCTION-VERIFIED** ｜ 契约：OSAI CTR-CANONICAL-METRICS-P0-01
- 范围：仅 ZBC `app.py::api_dashboard_all` 的 stats 段（L4920 区），**未触碰** overview/trend/events/risk_alerts/hot_topics/ai_status 等其他段，未改任何前端。

## 为什么改 / 复用了什么
首页 stats 是全产品总览数字源头，原实现用 6 趟独立 SQL（1 GROUP BY + 3 COUNT + 2 SUM）各算一遍情感/风险/互动，正是 P0 审计识别的"族 A/B/C 重复计算"的总览入口。本次 WRAP 到唯一 Canonical 实现 `canonical_metrics.py`（FN-SENTIMENT-COUNT / FN-RISK-COUNT / FN-ENGAGEMENT），一次取数 + 内存纯函数聚合，**不新造算法**。

## 口径（Q1 方案甲，已锁）
high 只含 risk_level='high'，critical 独立；情感三值精确、其余 unknown；engagement=likes+comments+collects+shares。

## 改前→改后数字一致性（真实 monitor.db，补丁脚本内前置断言，必须相等才写盘）
| 字段 | 旧 6 趟 SQL | 新 Canonical | 一致 |
|---|---|---|---|
| total | 1052 | 1052 | ✓ |
| positive/neutral/negative | 629/326/97 | 629/326/97 | ✓ |
| high/medium/low_risk | 23/80/949 | 23/80/949 | ✓ |
| total_engagements | 461041 | 461041 | ✓ |
| total_comments | 49589 | 49589 | ✓ |

等价性前提已实证：notes 四互动字段零 NULL（故 SQL 行内加法与 Canonical 逐字段 COALESCE 等价）；sentiment 仅三值（97+326+629=1052，无 unknown）。

## 输出契约
`result.stats` 字段名/结构完全不变（sentiment dict、total、positive、neutral、negative、high_risk、medium_risk、low_risk、total_engagements、total_comments、categories），前端零改动。

## 测试与运行验证
1. 单测：`tests/test_canonical_metrics.py` 16 项全 PASS（含真实库 Canonical==SQL 一致性用例）。
2. 回归：canonical + api_smoke + daily_report_redline + sentiment_engine 共 30 项全 PASS（日报红线未破坏）。
3. 路由层：Flask test_client GET /api/dashboard/all → HTTP 200，stats 与基线完全一致，trend 14 点完整，测试会话已自清理。
4. 生产：supervisor 杀旧 worker 树后 4s 自愈（新 worker 11:09:08），真实 Basic Auth HTTP 调 8201 返回一致 → PASS。
5. 性能：6 趟全表扫描 → 1 趟 SELECT（6 列）+ 内存聚合，全表仅 1052 行，扫描次数下降，无新增请求/定时器。

## 影响面 / 回滚
- 影响：仅 /api/dashboard/all 的 stats 数值来源（值不变）；不影响采集、主体红线、风险红线、其他端点。
- 回滚：`git revert <本commit>` 即可恢复原 6 趟 SQL；canonical_metrics.py 为纯新增，保留不影响旧路径。

## 后续（不在本次）
剩余族 A/B 重复点（daily_report / report_center / export_report / intelligence / brand_stats_recompute / report_engine / app.py 其他段）按同一 WRAP 法逐文件接入，每处都做"旧实现==Canonical"前置断言 + 跨面一致性（表=图=报告=导出）。
