# CTR-CANONICAL-METRICS-P0-01｜统一数据智能管线 · 首批 Canonical Function/Metric 契约（草案）

- 类型：Contract Draft（Research/Intelligence → Core 的实现规范，**不直接写 Production**）
- 日期：2026-09-03 ｜ 状态：READY_FOR_REVIEW（含 1 项待用户拍板口径）
- 事实依据：ZBC `序境/08-AUDIT/PIPELINE_P0_AUDIT_20260903.md`（源码级 P0 Inventory，commit b33b8aa）
- 遵循：Unified Data Intelligence Pipeline V1.0；一次采集/一次标准化/一次业务计算/多处消费；Canonical Table 是唯一数字 Truth Surface。

## 1. 分层与所有权（不可越界）
`External→Raw/Evidence→Canonical Data→【Function】→【Metric】→Canonical Table→View Model→Visualization→UI/Report/Export/AI`
- Function/Metric/Canonical Table 的**唯一 Owner = 序境-Core**；Intelligence 只产出本契约与评估，不持 Production Write。
- View Model 允许"占比/归一化/格式化"，但**分母口径由 Metric 定义**，渲染层不得自定业务口径。
- AI 仅经 Semantic Layer 只读 Metric/Canonical Dataset/Evidence，不得回写 Truth。

## 2. Function / Metric 元数据 Schema（注册必填）
Function：`function_id, version, purpose, inputs, outputs, formula, dependencies, dimensions, time_window, unit, error_policy, quality_requirements, tests, evidence, status`。
Metric：`metric_id, definition, function_id, dataset, dimensions, unit, time_window, filters, version, owner, evidence, tests, status`。
同一 metric_id 必须全产品同语义；状态机 Candidate→Implemented→Verified-In-Test→Production-Verified。

## 3. 首批 Canonical（对应 P0 审计识别的重复族）
### FN-SENTIMENT-COUNT v1（收敛族 A：现 8 文件 15+ 处）
- inputs: notes[]（dict 列表，含 sentiment）、dimensions（可选 category/brand/event/时间窗）
- outputs: {positive, neutral, negative, unknown, total}
- formula: 按 sentiment 精确匹配三值；空/非三值 → unknown（**不并入任一、不伪装 0**）
- error_policy: 输入非 list → 抛 TypeError；单条缺字段计 unknown 且 quality 标记
- tests: 三值完备=total；含 unknown 时 positive+neutral+negative<total；空集返回全 0 且 status=empty（区别于 unknown）

### FN-RISK-COUNT v1（收敛族 B，消除 high/high+critical 分叉）
- outputs: {high, medium, low, other, total}
- formula: risk_level 精确分桶。**【Q1 已决策 2026-09-04：方案甲】** high 桶仅 high；critical 作为独立更高桶（risk_count 输出 critical 字段），不并入 high，不另造第二口径。
- 落地进度：canonical_metrics.risk_count 已实现方案甲；WRAP-01 dashboard/all、WRAP-02 daily_report、WRAP-03 report_generator（原 in('high','critical') 分叉已消除）、WRAP-04 export_report 已统一；剩余 intelligence/brand_stats_recompute/reprocess/report_engine/app.py 其余段待逐文件 WRAP。
- 现状基线：DB 仅 high23/medium80/low949、无 critical，方案甲迁移全程数字零变化（已逐处 oracle 验证）。

### MET-NEG-RATIO / MET-POS-RATIO v1
- formula: negative / (positive+neutral+negative)；**分母固定三值总和，不含 unknown**
- unit: %（保留 1 位仅在 View Model）；time_window 必填；已验证现网 97/1052=9.2%、629/1052=59.8%

### FN-ENGAGEMENT v1（收敛族 C：kos_metrics 与 kol_analysis 已同式）
- formula per-note = likes+comments+collects+shares（缺项按 0 但记 quality）；聚合 sum/avg/count
- 区别：FN-LIKES = 仅 likes（kos_engine total_likes 归此），二者命名严格区分，禁止用"互动"指代"赞"

### FN-KOS-AUTHOR-AGG v1
- dimensions: author_id × 主体归属（过 Subject Gate）× 时间窗
- outputs: note_count, engagement_sum/avg, likes_sum；主体未过 Gate 的账号不得进入目标主体 KOS 聚合

## 4. 数据五态（Quality Gate 统一，禁止缺失伪装 0）
显式区分 `0（真实测得零）/ NULL（未采集）/ UNKNOWN（采集到但无法判定）/ STALE（超过 freshness）/ ERROR（采集或计算失败）`；Canonical Table 每值带 quality 标记；`COALESCE/||0/get(...,0)` 仅允许在已证明非空的 View 层，业务计数层禁用静默兜底。复用既有 data_quality_gate.py / schema_registry.py，不重造。

## 5. Cross-Surface Consistency Test（一致性验收）
同一 (metric_id, 时间窗, 维度, 过滤, 权限) 下，首页/页面表/图表/日报/周报/导出/AI 七处取值必须相等；测试从 Canonical Table 取基准，逐 surface 比对，差异定位到 Function/Dataset/Filter/Cache/Version，**禁止改展示层数字凑齐**。

## 6. 迁移与删除 Gate（渐进，不长期双真相）
Existing→Wrapper/Adapter→Canonical Function→并行比对（数字必须一致，Q1 两方案当前都一致）→逐调用点 Cutover→旧实现仅在 Reference+Dependency+Runtime 三 Scan + 回归 + 回滚路径齐备后删除。族 A 先新增 Canonical 纯函数与单测，不动 15+ 调用方；随后逐文件 WRAP。

## 7. 不在本契约范围
不重写采集/主体/风险红线；不合并数据库表；不决定端点裁并（另出端点 Reference Scan 报告）；可视化渲染器收敛（双趋势图）归 VIS Registry 契约。
