# Canonical Capability Convergence V1｜Contract 落库 + 第一阶段审计 Evidence

- **日期**：2026-09-04
- **指令**：《一次性研发总指令｜Canonical Capability Convergence V1》（长期有效）
- **仓库**：ZBC（序境-Core）+ OSAI（序境-Intelligence）

## 一、Contract 落库（双库同步）

《CANONICAL_CAPABILITY_CONVERGENCE_V1.md》已写入：
- ZBC：`序境/00-GOVERNANCE/CANONICAL_CAPABILITY_CONVERGENCE_V1.md`
- OSAI：`序境/00-GOVERNANCE/CANONICAL_CAPABILITY_CONVERGENCE_V1.md`

定位：GOVERNANCE / 长期 Contract（Zero Sequence 兼容，不修改产品 Truth、产品定义、架构、角色、业务边界、品牌标准、安全红线及既有正确口径）。

核心原则（摘要）：
- 10 条绝对防爆规则（一事实一 Source、一计算一 Function、一指标一 Metric、UI/Report/Export/AI 不重算业务 Truth、无 `_for_ai/_for_dashboard/*_for_report` 消费者复制、新代码前 Reference Scan）
- 旧功能分类 KEEP/MERGE/REPLACE/LEGACY/DELETE，禁止凭感觉删除
- 替换协议 DUAL RUN（OLD→NEW→DUAL RUN→DIFF/ORACLE→CONTRACT TEST→REGRESSION→E2E→PRODUCTION VERIFICATION→PROMOTE→LEGACY→IMPACT SCAN→DELETE）
- 最优计算路径 8 级优先（已有 Data/Function/Metric 直接复用，可增量不全量，可缓存则缓存，可并行则并行，确定性不调 AI）
- 最重要一条：不重写已正确工作的代码；新实现必须证明更统一/更可复用/更可测试/更可追踪/更稳定/更高效才替换，否则 KEEP

## 二、第一阶段审计（全仓 Reference Scan，2026-09-04）

### 2.1 消费者驱动重复计算扫描（`_for_ai/_for_dashboard/_for_report/_for_export/_for_kos/_for_ui`）
**结果：0 命中**。此前 WRAP-01~09 已消除该类消费者复制。符合防爆规则 9。

### 2.2 前端 JS 业务计算扫描（static/js/*.js）
命中约 15 处百分比/占比/round/toFixed，经甄别**均为展示层格式转换**（消费后端已算好的数据，如 `d.percentage`、`(n/total*100).toFixed(1)`），非第二套业务 Truth。判定 KEEP（UI 展示层）。

### 2.3 Python SQL 聚合重复扫描（COUNT/SUM/AVG/GROUP BY）
命中约 30 处，逐一判定：
- **已 WRAP**：dashboard/all、daily_report、report_generator、export_report、report_engine、app.py report 三处、kos_attribution → canonical（矩阵 WRAP-01~09）
- **KEEP（不同业务语义）**：
  - `/api/brand-stats`（app.py L1364）：场内业态/品牌 TOP10/pie 占比，业务=业态维度
  - `/api/brand-industry/stats`（app.py L2300）：行业维度，REFSCAN 已修复实体 id 计数（0a1683f）
  - `/api/negative-review/stats`（app.py L2329）：负面审核口径（subject+去重+去噪+确认状态）
  - 三者口径不同源（行业/业态/负面审核），非重复计算
- **KEEP（性能最优）**：SQL CASE WHEN 趋势聚合（L2883/L3106/L4898/L4985）等值口径与 Canonical 精确一致，改内存聚合降性能
- **待评估（不急于改）**：`/api/brand-stats` 内联 `engagement=likes+comments+collects+shares` 两处（L1390 业态/L1396 品牌）——符合 FN-ENGAGEMENT 语义，但为遍历内联累加，非独立函数；按"不重写已正确工作代码"暂 KEEP，如需统一另开小批。

### 2.4 结论
全仓未发现需立即 REPLACE 的重复计算。当前重复率处于低位（WRAP 系列已收敛核心口径）。本次第一阶段 = Contract 落库 + Reference Scan 判定记录。后续阶段（Capability Registry 更新、Cross-Surface 一致性、Legacy 清理）按指令十阶段渐进推进。

## 三、与 UDIP V1.0 的关系
- UDIP V1.0 = 数据管线收敛（一次采集/一次标准化/一次计算/多处消费）
- Canonical Capability V1 = Capability 级总纲（覆盖 Data/Function/Metric/UI/AI 全层）
- 本 Contract 将 UDIP 提升为全产品 Canonical Capability 治理，二者兼容不冲突。

## 四、验证
- 未改动生产代码（本次仅 Contract 落库 + 审计判定）
- 无生产回归风险；如需验证现有路径，回归基线不变
