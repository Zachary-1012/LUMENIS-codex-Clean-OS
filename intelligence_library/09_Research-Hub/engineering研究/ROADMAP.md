# DCC 长期路线图 (Roadmap)

> Baseline ID: ZB-PROD-2026-08-31-04
> Version: 1.0
> Status: ACTIVE
> Last Updated: 2026-08-31

---

## 1. DCC 定位与演进方向

DCC（Development-Command-Console）的定位从"AI 开发命令控制台"演进为：

**AI Development + Audit + Evidence + Release Control + Learning Plane**

核心能力栈：
- 事实控制（GitHub 实际状态优先）
- 双仓库控制（Core = 生产 SoT，DCC = 研发 SoT）
- 权限控制（最小权限，WRITE/COMMIT/MERGE/DEPLOY/EXEC 默认 DENY）
- 变更计划（Change Plan + 状态机）
- 证据链（Evidence Schema + Evidence Bundle）
- 安全门（Security Gate + 凭据扫描 + 权限漂移检测）
- 长期经验（Learning Database + Case Library + Failure Database）
- 影子学习（Shadow Agent：只观察、预测、给第二意见，不拥有写权限）

**DCC 不是 OpenHands / SWE-agent 的简单复制品**。吸收它们的 Agent 能力，但保留自己的治理内核（事实基线、双仓库解耦、权限硬锁、证据链、安全门）。

---

## 2. 路线图总览

| 阶段 | 名称 | 状态 | 核心产出 |
|---|---|---|---|
| P0 | Baseline 04 收敛 | ✅ 完成 | 文档基线统一到 ZB-PROD-2026-08-31-04 |
| P1 | Evidence Contract | ✅ 完成 | Evidence 数据契约（21字段+14 Source+5 Result+4 Decision） |
| P2 | Evidence Bundle | ⏳ 待启动 | server/evidence-bundle.js + 8个JSON证据文件 + 测试 |
| P3 | Security Gate | ⏳ 待启动 | 安全门禁模块（凭据扫描+权限漂移+未授权文件检测） |
| P4 | Learning Database Contract | 📋 规划中 | Learning 数据契约（Case/Experience/Failure 数据模型） |
| P5 | Case / Experience Engine | 📋 规划中 | 案例检索+经验提取+相似度匹配+失败案例优先 |
| P6 | Shadow Learning | 📋 规划中 | Shadow Agent（预测+第二意见+对比评估，无写权限） |
| P7 | Release Candidate | 📋 规划中 | RC 生成+测试+安全+审计+晋级状态机 |
| P8 | Core Compatibility | 📋 规划中 | Core 兼容性检查+回归测试+Submodule 受控晋级 |

---

## 3. 各阶段详细定义

### P0 — Baseline 04 收敛 ✅

**目标**：修复 DCC 文档基线与当前 Submodule 架构事实不一致的问题。

**完成时间**：2026-08-31
**Commit**：`b6b047c`
**产出**：
- docs/V04-ARCHITECTURE.md（3处 03→04）
- docs/REPOSITORY-FACT-BASELINE.md（4处 03→04）
- docs/PRODUCTION-GATE-XHS-APP.md（2处 03→04）
- docs/DEVELOPMENT-LOG.md（追加 P0 记录）
- 历史记录（V04-CHANGE-CONTRACT.md、DEVELOPMENT-LOG 历史）的 03 保留不篡改
- 测试数据（snapshot.test.js、change-plan.test.js）的 03 保留不触碰

**验收**：仅文档修改，无代码误改，已 push 并通过二次 GitHub 核验。

---

### P1 — Evidence Contract ✅

**目标**：建立统一的 Evidence 数据契约，为 P2 Evidence Bundle 打标准基础。

**完成时间**：2026-08-31
**Commit**：`a00a55d`
**产出**：
- docs/V041-CHANGE-CONTRACT.md（P1 变更合同）
- docs/V041-EVIDENCE-SCHEMA.md（Evidence 数据契约）
  - 21 个字段定义（evidenceId, evidenceType, correlationId, source, sourceReference, actor, repository, branch, commitSha, remoteHead, baselineId, version, timestamp, operation, target, expectedState, observedState, result, decision, reason, integrity）
  - 14 种 Source 分类
  - 5 种 Result 枚举（PASS/FAIL/BLOCKED/NOT_VERIFIED/REPLAN_REQUIRED）
  - 4 种 Decision 枚举（ALLOW/STOP/REPLAN/REVIEW_REQUIRED）
  - expected vs observed 硬约束
  - 证据链完整性规则（Baseline → Snapshot → Lock → Change Plan → Operation → Evidence → Decision）
  - 禁止伪证据 10 条
  - 历史记录保护规则
  - 3 个完整示例（PASS/ALLOW, BLOCKED/STOP, NOT_VERIFIED/REVIEW_REQUIRED）
- docs/DEVELOPMENT-LOG.md（追加 P1 记录）

**验收**：五道 Gate 全部 PASS，仅文档修改，已 push 并通过二次 GitHub 核验。

---

### P2 — Evidence Bundle ⏳ 待启动

**目标**：基于 P1 Evidence Schema，实现 Evidence Bundle 业务代码，把每次升级的证据固化为可追溯的 JSON 文件包。

**依赖**：P1 完成
**预计产出**：
- server/evidence-bundle.js（Evidence Bundle 生成器）
- tests/evidence-bundle.test.js（测试）
- Evidence Bundle 固定 8 个 JSON 文件：
  - baseline.json
  - repository-state.json
  - changed-files.json
  - test-results.json
  - security-results.json
  - regression-results.json
  - permission-results.json
  - audit-summary.json
- docs/V042-EVIDENCE-BUNDLE-SPEC.md（实现规范）

**硬约束**：
- Evidence Bundle 是证明系统，不是自动执行系统
- 不得扩大 WRITE/COMMIT/MERGE/DEPLOY/EXEC 权限
- 每个 Evidence 必须符合 P1 Schema
- 无法验证的内容标记 NOT_VERIFIED，不得写 PASS

---

### P3 — Security Gate ⏳ 待启动

**目标**：建立独立的安全门禁模块，在 Commit/Push 前自动扫描并阻止安全风险。

**依赖**：P2 完成（Security Gate 的扫描结果需要写入 Evidence Bundle）
**预计产出**：
- server/security-gate.js（安全门禁模块）
- tests/security-gate.test.js（测试）
- 扫描能力：
  - Token / PAT / Secret / Cookie / Credential / Private Key 检测
  - 权限边界漂移检测（config.js / security.js 未授权修改）
  - 未授权文件修改检测（Change Plan 范围外文件）
  - 生产代码修改检测（Core 业务代码、CTH-POMS / ZBMP）
  - 远程 HEAD 变化检测
  - Submodule 状态异常检测
- 决策：PASS / BLOCKED / REPLAN_REQUIRED

**硬约束**：
- Security Gate 命中真实凭据或权限漂移时，必须 STOP，不得让 AI 自行"修一下继续"
- 测试中的假 Token 可以存在，但必须明确属于测试数据，不得误报为真实泄露

---

### P4 — Learning Database Contract 📋 规划中

**目标**：定义 Learning 层的数据契约，包括 Case Library、Experience Database、Failure Database 的数据模型、可信度、去重、版本绑定、Evidence 引用和 Shadow 权限边界。

**依赖**：P1 完成（Evidence Schema 是 Learning 数据的基础）
**P4 之前不允许真正写学习代码**，只定义契约。

**预计产出**：
- docs/V044-LEARNING-CONTRACT.md（Learning 数据契约）
- Case 数据模型（外部案例 + 内部经验）
- Experience 数据模型（任务→方案→结果→原因→修正→最终结果）
- Failure 数据模型（专门记录失败，避免重复错误）
- 可信度评分规则（0.0-1.0，基于 Evidence 验证 + 人工修正 + 重复验证）
- 去重规则（相似 Case 合并 + 版本绑定）
- 版本绑定规则（每个 Learning Record 绑定 Baseline ID + DCC version + Core version）
- Evidence 引用规则（每个 Learning Record 必须引用至少 1 个 Evidence ID）
- Shadow Agent 权限边界（WRITE/COMMIT/MERGE/DEPLOY/EXEC 全部 DENY）

**核心硬规则**：
> **Learning is advisory, never authoritative.**
> 学习层只能提供建议，不能成为事实来源。事实仍然是 GitHub 实际状态 + 实际测试 + 实际扫描 + 实际 Evidence。

---

### P5 — Case / Experience Engine 📋 规划中

**目标**：实现案例检索、经验提取、相似度匹配引擎，让 DCC 能从历史经验中学习。

**依赖**：P4 完成（Learning Contract）+ P2 完成（Evidence Bundle 提供经验数据来源）
**预计产出**：
- server/case-engine.js（案例检索引擎）
- server/experience-extractor.js（经验提取器：从 Evidence Bundle 提取 Case/Experience/Failure）
- server/similarity.js（相似度匹配）
- tests/（对应测试）
- 能力：
  - 检索历史相似任务
  - 发现某方案曾失败 → 降低该方案优先级
  - 优先推荐曾成功的方案
  - Failure Database 优先匹配（避免重复错误）
  - 经验可信度衰减（旧经验在新 Baseline 下可信度降低）

---

### P6 — Shadow Learning 📋 规划中

**目标**：实现 Shadow Agent，在正式流程旁边独立分析、预测、给第二意见，但永远不拥有生产写权限。

**依赖**：P5 完成（Case/Experience Engine 提供预测基础）
**预计产出**：
- server/shadow-agent.js（Shadow Agent 模块）
- tests/shadow-agent.test.js（测试）
- Shadow Agent 能力：
  - 预测应该怎么改
  - 判断风险
  - 推荐测试
  - 推荐架构
  - 推荐 Git 操作
  - 找相似案例
  - 预测某个方案可能失败
  - 对当前 Change Plan 给第二意见
- Shadow Agent 权限边界：
  - WRITE = DENY
  - COMMIT = DENY
  - MERGE = DENY
  - DEPLOY = DENY
  - EXEC = DENY
- 对比评估：正式流程结果 vs Shadow 预测结果 → 记录成功/失败 → 更新经验数据库

**工作流**：
```
真实任务
    │
┌───┴───┐
↓       ↓
正式流程  Shadow Agent
│       │
│   独立分析/预测
│       │
↓       ↓
实际结果  Shadow 结果
│       │
└───┬───┘
    ↓
对比评估
    ↓
记录成功/失败
    ↓
更新经验数据库
```

---

### P7 — Release Candidate 📋 规划中

**目标**：建立 DCC → Core 的受控发布管线，DCC 新版本必须经过 RC 状态机才能申请进入 Core。

**依赖**：P2（Evidence Bundle）+ P3（Security Gate）完成
**预计产出**：
- server/release-candidate.js（RC 生成与状态机）
- tests/release-candidate.test.js（测试）
- RC 状态机：
  - CANDIDATE → TESTED → AUDITED → APPROVED → PROMOTABLE → PROMOTED
  - 异常：FAILED / BLOCKED / REVOKED
- RC 包含：
  - RC ID
  - DCC SHA
  - Core SHA
  - Submodule SHA
  - 测试结果
  - 安全结果
  - Evidence Bundle
  - Diff
  - Rollback SHA
- 任何一个状态不能伪装成另一个状态
- 没有进入 APPROVED，不能发生 promotion

---

### P8 — Core Compatibility 📋 规划中

**目标**：建立 Core 兼容性检查和回归测试能力，在 DCC RC 晋级 Core 前验证不会破坏 CTH-POMS / ZBMP 生产业务。

**依赖**：P7（Release Candidate）完成
**预计产出**：
- server/core-compatibility.js（Core 兼容性检查器）
- tests/core-compatibility.test.js（测试）
- 检查维度：
  - 文件层（submodule path、.gitmodules、pinned SHA）
  - 版本层（Core version、DCC version、Baseline ID）
  - 功能层（CTH-POMS、ZBMP、collector、risk engine、reporting、database）
  - 安全层（WRITE、MERGE、DEPLOY、EXEC、SECRET、TOKEN、COOKIE）
  - 测试层（DCC tests、Core regression、integration tests）
- 输出：COMPATIBLE / INCOMPATIBLE / BLOCKED
- 晋级流程：
  ```
  DCC development
    ↓
  DCC tests
    ↓
  Security Gate
    ↓
  Evidence Bundle
    ↓
  Release Candidate
    ↓
  RC SHA
    ↓
  读取 Core HEAD
    ↓
  读取 Core pinned SHA
    ↓
  DCC/Core compatibility diff
    ↓
  Core regression
    ↓
  人工批准
    ↓
  Core 更新 Submodule
    ↓
  Core regression
    ↓
  最终批准
  ```

---

## 4. 阶段间依赖关系

```
P0 (Baseline 04)
    ↓
P1 (Evidence Contract) ←────────────┐
    ↓                                │
P2 (Evidence Bundle)                 │
    ↓                                │
P3 (Security Gate)                   │
    ↓                                │
P4 (Learning Database Contract)      │  P1 Schema 是 Learning 数据的基础
    ↓                                │
P5 (Case / Experience Engine) ───────┘  P2 Evidence Bundle 提供经验数据来源
    ↓
P6 (Shadow Learning)
    ↓
P7 (Release Candidate) ← P2 + P3 提供 Evidence + Security
    ↓
P8 (Core Compatibility) ← P7 提供 RC，P5/P6 提供经验预测
```

**关键路径**：P0 → P1 → P2 → P3 → P7 → P8（发布管线）
**学习路径**：P1 → P4 → P5 → P6（学习能力，与发布路径并行）

---

## 5. 全阶段硬约束（每个阶段都必须遵守）

1. **事实优先**：GitHub 实际状态 > 当前源码 > Baseline 文档 > 聊天记录 > AI 推测
2. **双仓库解耦**：DCC 可以领先，Core 必须稳定；DCC HEAD ≠ Core pinned SHA 是正常状态，不是错误
3. **最小权限**：WRITE/COMMIT/MERGE/DEPLOY/SHELL EXEC/CODE EXEC 默认 DENY，不得扩大
4. **证据链**：每次修改必须产生 Evidence，无法验证标记 NOT_VERIFIED，不得虚构
5. **安全门**：发现真实 Token/Secret/Credential 或权限漂移，必须 STOP
6. **Core 保护**：不得修改 Core 业务代码，不得自动更新 Core pinned SHA，不得删除/覆盖用户未提交文件
7. **历史不可篡改**：历史记录中的 Baseline ID、Commit SHA、测试结果不得追溯修改
8. **Learning is advisory**：学习层只能提供建议，不能成为事实来源，不得自动修改生产规则
9. **Shadow 无写权限**：Shadow Agent 永远 WRITE/COMMIT/MERGE/DEPLOY/EXEC = DENY
10. **每阶段重新建立 Baseline**：新阶段开始前必须重新读取 GitHub 实际状态，不得使用旧 SHA

---

## 6. 当前状态总结（2026-08-31）

| 项目 | 状态 |
|---|---|
| DCC HEAD | `a00a55d`（P1 Evidence Contract） |
| DCC version | 0.3.0（功能已到 V0.4.0+，版本号未升） |
| DCC workspace | 干净 |
| Core HEAD | `af09bcd`（持续独立开发） |
| Core pinned DCC SHA | `a00a55d`（Core auto-watch 已跟进 P1） |
| Core version | 5.9.9 |
| 当前 Baseline | ZB-PROD-2026-08-31-04 |
| 权限边界 | READ/TASK/AUDIT = ALLOW, TEST = CONTROLLED, WRITE/COMMIT/MERGE/DEPLOY/EXEC = DENY |
| 已完成阶段 | P0 ✅, P1 ✅ |
| 下一阶段 | P2 Evidence Bundle（需重新建立 Baseline 并获得授权） |

---

**本路线图为活文档，每完成一个阶段后更新状态。新阶段启动前必须重新读取 GitHub 实际状态，不得使用本文件中的 SHA 作为当前事实。**
