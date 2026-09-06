# P0 对账施工记录（2026-09-02）— OSAI 侧归档

> 双子星：OSAI 研究侧归档。施工执行在 Z-Brand-Core（生产侧）完成，本文件为研究侧镜像记录。
> 关联：Z-Brand-Core/docs/P0-RECONCILIATION-ENGINEERING-20260902.md（commit 6d7feb7，含追加）

## 结论速览

| 项目 | 状态 |
|---|---|
| P0-02 subject_hit 统一权威口径 | ✅ 已推送（run_live_engine 02b1fcd + app.py 经后台 merge 9507470 推送） |
| P0-04 requirements 补 waitress | ✅ 已推送（fec36be） |
| P0-05 版本号统一 v5.9.9 | ✅ 已推送（a4ea9a8 / 73fe04c） |
| P0-01 aggregate_events 替代映射 | 📝 已记录（daily_report/weekly_events/event_graph） |
| P0-03 OSAI archive 密钥风险 | ⚠️ 待用户决策（本地 .env 35 行真实密钥 + ZBC 生产副本 1643 文件） |
| 追加：live_engine ImportError 修复 | ✅ 已推送（9c9e625 + docs 6d7feb7） |

## 施工前核验（用户要求「检查最新仓库说明」）
- ZBC GitHub main HEAD=d4df89d，含 v5.9.9-t2 小红书 P0 编排层；对账基线落后于最新代码。
- 关键分层确认：database.py insert_note/get_events 已用 subject_rules.subject_hit（5 字段权威）兜底，AI verify 仅为采集增强标记（合规）。

## 主体口径收敛（P0-02）技术说明
- 权威源：subject_rules.py subject_hit（5 字段）/ subject_hit_text（单文本适配，历史调用点入口）。
- 收敛点：collector_v2/run_live_engine.py（02b1fcd）+ app.py:2747（subject_hit_text 委托，本地 8834d1a 已含，经后台 merge 9507470 推送 GitHub）。
- 验证：py_compile OK + 6/6 功能用例 PASS。

## 追加：live_engine 实时采集链路 ImportError 修复（commit 9c9e625）
- **根因**：`collector_v2/xhs/live_engine.py` 第 13-15 行导入 `normalize_note`/`deduplicate`/`filter_subject` 均为类方法、非模块级函数，自初始入库 b69b68f 后从未能 import，XHS Live 采集 CLI 链路不可用。
- **修复（最小、不重写口径）**：
  - subject_filter.py 新增模块级 `filter_subject(notes, subject_hit)`，**委托外部传入的权威 subject_hit 回调**（subject_rules.subject_hit_text）。
  - normalize.py 新增模块级 `normalize_note(note)`；deduplicate.py 新增模块级 `deduplicate(notes)`。
- **验证**：import OK / py_compile 4 文件 PASS / filter_subject 6 用例 3/6 命中 PASS（广州太古汇·太古汇保安·天河路383号 命中；上海·成都·北京 拒绝）。
- 施工前备份三文件为 *.bak_p0_20260902（.gitignore 已忽略），未污染仓库。

## 双子星边界
- 本次施工为用户显式授权例外；OSAI 本职仍为研究/学习/Contract。
- 未触碰权威主体词、生产数据、Cookie/Token；无密钥入仓库。
