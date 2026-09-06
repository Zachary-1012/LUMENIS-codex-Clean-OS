# 序境｜文件清理审计清单

> 状态：AUDIT / NO-BLIND-DELETE
> 日期：2026-09-04

## 处理规则

1. 研究成果、当前 Contract、架构基线与安全资产：KEEP/MIGRATE。
2. 当前唯一有效规范：进入 `序境/` Canonical 体系。
3. 阶段性 inventory / reconciliation / handoff / work log：逐项判断后归档。
4. 重复、无引用、无当前职责且已被 Canonical 文档完整替代：可 DELETE。
5. 无法证明安全删除：HUMAN_REVIEW，不盲删。
6. 历史资料如具有审计证据价值，统一进入 `99-ARCHIVE`。

## 当前重点检查

- 根目录编号式 `01_*` 至 `22_*` 审计矩阵
- 日期型 `AUDIT_HANDOFF_*`
- 日期型 `WORK_LOG_*`
- 已被序境治理文档替代的旧命名/旧架构说明
- 重复的双库 Contract / Baseline / Convergence 文档
- P0 运行时研究与安全研究的实际引用关系

## 禁止直接删除

- 当前 README / Contract / Security / Evidence 基线
- 当前有效研究成果及其实现规格
- 被 ZBC 引用的 Contract
- P0 Resident Runtime / Browser / Agent 安全研究
- 未完成验证的迁移矩阵

## 豆包执行要求

`reference scan → dependency scan → contract scan → research-value check → test → archive/delete → verify`

无法证明安全删除的资产必须标记 `HUMAN_REVIEW`。
