# 报告体系 API 收敛方案（GAP-10，智谱深度分析）

> 日期：2026-09-03 | 分析模型：glm-4.5-air（per_call 授权第 2 次）
> 关联：GAP-10（报告多路由 12+ 收敛 + report_center 接管）
> 状态：**方案已定，本轮只登记不施工**（需用户签字后才进入 P0 收敛）

---

## 1. 现状（真实代码审计）

- app.py 有 **17 个报告相关路由**，分散在多处。
- `v4_upgrade/report_center`（ReportGenerator / ReportExporter 标准化报告中心）**已建但旁路未接管**（Feature Gate: `ZBC_REPORT_CENTER=1` 默认关）。
- GAP-10 目标：收敛重复路由 + 决策 report_center 是否成为统一 Owner。

## 2. 智谱聚类结论

### 重复实现（likely duplicate，8 个）
`/api/brand-report/generate`、`/api/brand-report/export/<id>`、`/api/report/daily`、`/api/report/generate`、`/api/report/export`、`/api/report/v2/<type>`、`/api/reports/<id>/download`（与 file 重复）、`/api/v2/report/export`（与 report/export 重复）。

### 独立能力（keep，6 个）
`/api/reports`（列表）、`/api/report/verify`（验证）、`/api/special-report/generate`、`/api/report/special/export`、`/api/special-report/check-trigger`（特殊报告，独特业务）、`/api/v2/report-center/preview`（旁路预览）。

### Owner 建议
- report_center 应成为**标准化报告**（日报/周报/月报/年报 + Word/PDF 导出 + 多品牌 CTH/ZBMP）唯一 Owner。
- 特殊报告（special-report）**不**并入 report_center（独特业务逻辑），保留独立。

## 3. 分阶段收敛方案（待签字后执行）

- **P0**：确保 report_center 默认关；加 `/api/report-center/status`；给重复路由响应头加 `X-Deprecated: true`；有限环境验证。
- **P1**：文档迁移指南 → 逐步扩量 → 监控。
- **P2**：确认后完全切换，退役重复路由（保留兼容一段时间）。

## 4. 风险（智谱指出）

1. **Owner 冲突**：report_center 接管前必须先与 RPT-001/002 现有 Owner 对齐，否则双写不一致。
2. **特殊报告误伤**：special-report 有独特业务，绝不能并入标准化流程。
3. **切换回滚**：任何退役前必须先标 deprecated + 验证无调用方，再退。

## 5. 本轮行动

**不施工**。已在 FEATURE-GAP-REGISTER 登记 GAP-10 为 P2；本方案作为决策输入，待用户签字后进入 P0 收敛。

---

## 6. 复用知识（给后续/OSAI）

- API 收敛通用套路：**聚类 → 定唯一 Owner → 旧路由标 deprecated 保留兼容 → 验证无调用方 → 退役**，绝不直接删。
- 特殊业务（如 special-report）与标准化能力必须分离，不能一刀切并入统一 Owner。
- "旁路 + Feature Gate 默认关"是新能力接管的**安全渐进路径**（同 report_center 模式）。
