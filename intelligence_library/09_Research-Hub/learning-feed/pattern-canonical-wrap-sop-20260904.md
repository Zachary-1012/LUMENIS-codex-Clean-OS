# 工程模式卡｜Canonical 业务计算收敛 WRAP 标准作业法（2026-09-04）

## 场景
统一数据管线把散落在多文件的同一业务计算（情感/风险/互动计数）收敛到唯一 Canonical 纯函数层 `canonical_metrics.py`，要求功能不减、数字不变、可逐文件回滚。

## 标准作业法（每处 WRAP 必走，已在 WRAP-01~03 验证）
1. **先判指标是否真同一**：等权四字段互动(likes+comments+collects+shares) ≠ 日报 comments×2 加权传播分 ≠ 健康度 likes+comments 两字段。名字相近不等于同一 Metric；业务加权口径必须原样保留，只收敛"纯分桶计数"。强换加权=改业务 Truth，禁止。
2. **等价性前置断言**：补丁脚本内先复制旧实现为 oracle，对①真实生产库②空集③unknown/critical 边界三组输入，要求改前改后逐值相等，断言通过才写盘。
3. **方案甲 critical 独立**：high 只计 risk_level=='high'；旧代码 `in('high','critical')` 归一后，现网无 critical 则零变化，有 critical 时新值=旧值−critical 数（这是预期修正，不是 bug）。
4. **零 I/O 纯函数 + 一次取数**：Canonical 只收 list[dict]，不连 DB；调用点把多趟 COUNT/SUM 合并为一趟 SELECT，扫描次数只减不增。
5. **输出字段零变化**：WRAP 不改返回 JSON 的键名/结构，前端零改动；新增 unknown/critical 等诊断字段不强行塞入既有契约。
6. **分层验证**：纯函数单测（含真实库 Canonical==SQL）→ 相关红线/模块回归 → Flask test_client 路由层 → 生产 supervisor 杀 worker 树自愈重载 → 真实 Basic Auth HTTP 比对 →（首处）浏览器零 pageerror 截图。
7. **最小回滚**：canonical_metrics.py 纯新增；每处 WRAP 独立 commit，revert 单文件即可，不牵连他处。

## 关键事实（ZBC 现网 2026-09 基线）
notes 1052：pos629/neu326/neg97；risk high23/med80/low949、无 critical；四互动字段零 NULL、等权和 461041、comments 和 49589。

## 已落地
- WRAP-01 app.py /api/dashboard/all（PRODUCTION-VERIFIED，6 趟 SQL→1 趟）
- WRAP-02 daily_report.py 三处纯计数（加权保留，oracle 等价）
- WRAP-03 report_center/report_generator.py（消除 high+critical 唯一分叉）

## 反模式（勿犯）
- 为"统一"把加权/两字段指标也改成等权四字段 → 数字变=事故。
- 只静态比对不上真实库/边界 → critical、NULL、unknown 会藏双真相。
- 在渲染层改数字凑齐 → 必须回溯 Function/Metric，禁止改展示对齐。
