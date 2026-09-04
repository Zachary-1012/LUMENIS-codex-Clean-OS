# WRAP-02 Evidence｜daily_report.py 接入 Canonical（保留加权业务口径）

- 日期：2026-09-04 ｜ 状态：**VERIFIED-IN-TEST**（函数级等价 + 40 项回归；随下次生产重载生效）
- 范围：`daily_report.py` 三处**纯情感/风险分桶计数**，其余一律不动。

## 改了什么
| 函数 | WRAP 的计数 | 明确保留不动（业务口径不同，禁止强换） |
|---|---|---|
| calculate_risk_index | negative/high/medium → sentiment_count/risk_count | L48 传播分 `likes+comments*2`（评论加权、仅两字段，非等权四字段互动）；neg_ratio 分母 total=len；neg_engagement 加权 |
| calculate_brand_health_score | positive/negative → sentiment_count | L116-119 `likes+comments` 两字段健康度口径；pos_ratio 分母 total；official |
| 今日舆情摘要 | positive/neutral、risk=中+高 → Canonical 桶组合 | effective_notes 的 AI 过滤口径、risk_index/health 调用 |

## 为什么加权互动不替换
Canonical FN-ENGAGEMENT = likes+comments+collects+shares 等权四字段；日报风险指数用 comments×2 加权、健康度只用赞+评，是**不同业务 Metric**。强换会改变分值=改变业务 Truth（触红线），故仅统一"情感/风险分桶"，加权公式原样保留并注释说明。

## 新旧等价（脚本内 oracle 完整复制旧函数，对真实库+边界逐值断言）
| 用例 | risk_index 旧/新 | brand_health 旧/新 | 摘要(pos,neu,risk=中+高) 旧/新 |
|---|---|---|---|
| 真实全量 1052 | 50.5 / 50.5 | 64.0 / 64.0 | (629,326,103) / 同 |
| 空集 | 0.0 / 0.0 | 50.0 / 50.0 | (0,0,0) / 同 |
| critical+unknown 边界 | 5.0 / 5.0 | 56.6 / 56.6 | (1,0,1) / 同（critical 不计入 high、不计入中+高，方案甲一致） |

## 回归
daily_report_redline + report_periods + report_special + report_center_route + risk_engine + canonical 共 **40 项 PASS**，日报/风险红线未破坏。

## 回滚
`git revert <commit>`；canonical_metrics 为纯新增依赖，回滚本文件不影响 WRAP-01。
