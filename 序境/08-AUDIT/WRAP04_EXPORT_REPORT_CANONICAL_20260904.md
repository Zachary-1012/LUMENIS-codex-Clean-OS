# WRAP-04 Evidence｜export_report.py 接入 Canonical

- 日期：2026-09-04 ｜ 状态：**VERIFIED-IN-TEST**（真实调用 generate_report_data 验证，随生产重载生效）
- 范围：`export_report.py::generate_report_data` 的情感三计数 + 高风险计数（L157-163 区）。

## 保留不动（业务逻辑，非纯分桶）
- L185 pending_neg＝负面且 negative_confirmed∈(0,None) 的复合业务计数，保留。
- L188-190 负面优先排序、L259-260 positive_rate/negative_rate 分母 total=len，保留。
- 周期过滤、二次确认口径、重点笔记选取全部不动。

## 流向确认
统计进入返回 `summary.{positive,negative,neutral,high_risk,positive_rate,negative_rate}` 与管理层结论文案（L232/237）。

## 等价验证
- oracle 对真实库/空集/critical 边界：(pos,neg,neu,high) 新旧全等（真实 629/97/326/23）。
- 真实调用 generate_report_data：weekly(2/1/32/high0,5.7%/2.9%)、monthly(2/1/20,8.7%/4.3%)、yearly(329/45/244/high10,53.2%/7.3%) 正常产出、零报错；critical 不计入 high（方案甲）。
- 回归 report_periods + report_special + api_smoke PASS。

## 回滚
`git revert <commit>`，单文件独立。
