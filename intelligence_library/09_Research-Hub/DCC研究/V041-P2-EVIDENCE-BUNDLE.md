# DCC V0.4.1 P2 — Evidence Bundle 模块文档

**Baseline ID**: ZB-PROD-2026-08-31-04
**Phase**: P2 — Evidence Bundle Implementation
**Module**: server/evidence-bundle.js
**Status**: IMPLEMENTED
**Version**: DCC v0.3.0 (runtime version unchanged)

---

## 1. 模块定位

Evidence Bundle 是 DCC V0.4.1 P2 的核心模块之一，负责将一个开发任务相关的所有 Evidence 组织成可追溯的证据包。

它不产生新的事实，只收集、组织、验证已有的 Evidence。

**数据链**:
```
Baseline → Snapshot → Remote HEAD Lock → Change Plan → Operation → Evidence → Decision → Evidence Bundle
```

---

## 2. 核心功能

### 2.1 Bundle 创建与管理

- `createBundle(options)` — 创建 Evidence Bundle
- `getBundle(bundleId)` — 获取单个 Bundle
- `listBundles(options)` — 列出 Bundle（支持按 taskId/status 过滤）

### 2.2 Evidence 追加（不覆盖）

- `addEvidence(bundleId, evidence)` — 向 Bundle 追加 Evidence
- **硬规则**: 不允许覆盖已有 Evidence（相同 evidenceId 拒绝）
- **兼容**: 自动规范化旧格式 Evidence（补全缺失字段）

### 2.3 完整性验证

- `validateBundle(bundleId)` — 验证 Bundle 完整性
- 统计 PASS/FAIL/BLOCKED/NOT_VERIFIED/REPLAN_REQUIRED 数量
- 检查证据链缺失环节

### 2.4 状态判断

Bundle 状态枚举：
| 状态 | 含义 |
|---|---|
| `COMPLETE` | 包含完整证据链（核心环节 + Commit/Push） |
| `INCOMPLETE` | 缺少部分证据链环节 |
| `INVALID` | 包含无效 Evidence |
| `NOT_VERIFIED` | 无 Evidence 或全部为 NOT_VERIFIED |

### 2.5 Evidence 链追溯

- `getEvidenceChain(bundleId)` — 返回按证据链顺序排列的 Evidence
- 自动提取关键环节摘要（baseline/snapshot/lock/changePlan/tests/security/commit/push/secondVerification）

---

## 3. Evidence Schema 遵循

本模块严格遵循 P1 定义的 Evidence Schema（docs/V041-EVIDENCE-SCHEMA.md）：

- **21 个字段**: evidenceId, evidenceType, source, sourceReference, actor, repository, branch, commitSha, remoteHead, baselineId, version, timestamp, operation, target, expectedState, observedState, result, decision, reason, integrity, correlationId
- **5 种 Result**: PASS / FAIL / BLOCKED / NOT_VERIFIED / REPLAN_REQUIRED
- **4 种 Decision**: ALLOW / STOP / REPLAN / REVIEW_REQUIRED
- **硬约束**: expectedState ≠ observedState，不得把预期值伪装成实际观测值

---

## 4. 证据链类型

Bundle 完整性检查覆盖以下 Evidence 类型：

1. `BASELINE_VERIFICATION` — 基线验证
2. `SNAPSHOT_CREATION` — 快照创建
3. `REMOTE_HEAD_LOCK` — 远程 HEAD 锁定
4. `CHANGE_PLAN_CREATION` — 变更计划创建
5. `TEST_EXECUTION` — 测试执行
6. `SECURITY_SCAN` — 安全扫描
7. `GIT_DIFF_AUDIT` — Diff 审计
8. `COMMIT` — 提交
9. `PUSH` — 推送
10. `GITHUB_SECOND_VERIFICATION` — GitHub 二次核验

---

## 5. API 端点

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/api/evidence-bundle` | 列出 Bundle |
| POST | `/api/evidence-bundle` | 创建 Bundle |
| GET | `/api/evidence-bundle/:id` | 获取单个 Bundle |
| POST | `/api/evidence-bundle/:id/validate` | 验证 Bundle 完整性 |

---

## 6. 安全边界

- 仅内存存储，不写入文件系统
- 不修改 Evidence 原始事实
- 不允许覆盖已有 Evidence
- 不执行 git 命令
- 不修改任何仓库状态
- 不改变权限边界

---

## 7. 测试覆盖

测试文件: `tests/evidence-bundle.test.js`

覆盖范围：
- createBundle（正常/异常）
- getBundle / listBundles
- addEvidence（追加/拒绝重复/旧格式兼容）
- validateEvidence（完整/缺失字段/非法枚举）
- validateBundle（空/有证据/结果统计）
- getBundleStatus
- getEvidenceChain（排序/摘要）
- 常量导出验证

---

## 8. 与其他模块的关系

```
snapshot.js ──┐
change-plan.js ──┼──→ Evidence (由外部产生) ──→ evidence-bundle.js (收集组织)
security.js ────┘                                      │
                                                         ↼ Evidence Chain
config.js (权限不变)
```

Evidence Bundle 不依赖其他模块的内部实现，只接收符合 Schema 的 Evidence 对象。

---

## 9. 已知限制

1. 内存存储，Server 重启后数据丢失（后续 P3 可考虑持久化）
2. 不自动收集 Evidence，需外部调用 addEvidence
3. 完整性检查基于 evidenceType 匹配，不验证 Evidence 内容真实性
4. 不支持 Bundle 之间的关联（后续可扩展）

---

## 10. 后续阶段

- **P3 Security Gate**: 基于 Evidence Bundle 实现自动化安全门禁
- **P4 Learning Database Contract**: 将 Evidence Bundle 作为学习数据来源
- **P7 Release Candidate**: 使用 Evidence Bundle 作为 RC 的证据基础
