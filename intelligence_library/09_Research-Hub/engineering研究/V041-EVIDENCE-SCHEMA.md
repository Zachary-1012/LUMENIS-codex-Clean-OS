# DCC V0.4.1 P1 — Evidence Schema (证据数据契约)

> Baseline ID: ZB-PROD-2026-08-31-04
> Version: 1.0
> Status: ACTIVE
> Phase: P1 — Evidence Contract（证据标准与契约定义）
> 本文件定义 Evidence 的数据标准，不含业务代码实现。P2 将基于本契约实现 Evidence Bundle。

---

## 1. 设计目标

Evidence 必须能够回答以下 11 个问题：

| 问题 | 对应字段 |
|---|---|
| WHO：谁产生/提交了证据 | actor |
| WHAT：发生了什么操作/检查 | operation, evidenceType |
| WHEN：什么时候检查 | timestamp |
| WHERE：针对哪个仓库/文件/对象 | repository, target, sourceReference |
| WHICH VERSION：针对哪个版本 | version |
| WHICH BASELINE：针对哪个 Baseline | baselineId |
| WHICH SHA：针对哪个 Git commit / pinned SHA | commitSha, remoteHead |
| SOURCE：证据来自哪里 | source |
| RESULT：检查结果是什么 | result |
| DECISION：系统因此允许、阻止还是要求重新规划 | decision |
| WHY：为什么得出这个结论 | reason |

---

## 2. Evidence 字段定义

每条 Evidence 必须包含以下 21 个字段。字段分为**必填**和**可选**，但核心标识字段必须填写。

### 2.1 标识字段

| 字段名 | 类型 | 必填 | 描述 | 示例 |
|---|---|---|---|---|
| `evidenceId` | string | 是 | Evidence 唯一标识，格式 `EVID-<timestamp-base36>-<random>` | `EVID-MZ3X2K-A1B2C3` |
| `evidenceType` | string | 是 | Evidence 类型，见第 4 节 Evidence Type 分类 | `REMOTE_HEAD_VERIFICATION` |
| `correlationId` | string | 否 | 关联 ID，用于将多条 Evidence 串联到同一任务/操作链。同一 Change Plan 产生的所有 Evidence 共享同一 correlationId | `TASK-V041-P1-20260831-001` |

### 2.2 来源字段

| 字段名 | 类型 | 必填 | 描述 | 示例 |
|---|---|---|---|---|
| `source` | string | 是 | Evidence 来源分类，见第 5 节 Source 分类（14种） | `GITHUB` |
| `sourceReference` | string | 否 | 来源的具体引用，如 API 端点、命令、文件路径、测试名称 | `GET /repos/Zachary-1012/DCC/commits/main` |
| `actor` | string | 是 | 产生证据的主体：系统模块名、AI Agent 名、人工审核者标识 | `dcc-remote-head-lock`, `doubao`, `manual-reviewer-01` |

### 2.3 仓库与版本字段

| 字段名 | 类型 | 必填 | 描述 | 示例 |
|---|---|---|---|---|
| `repository` | string | 是 | 目标仓库，格式 `owner/repo`。针对双仓库操作时填写主要操作对象 | `Zachary-1012/Development-Command-Console` |
| `branch` | string | 是 | 目标分支 | `main` |
| `commitSha` | string | 是 | 被检查的 Commit SHA（7-40位十六进制）。这是**实际被验证的对象**，不是预期值 | `b6b047cd79d46f16eb0397d2a7a83df71cc327f3` |
| `remoteHead` | string | 否 | 远程 HEAD SHA。用于对比本地与远程状态。网络失败时填 null 并在 result 标记 NOT_VERIFIED | `b6b047cd79d46f16eb0397d2a7a83df71cc327f3` |
| `baselineId` | string | 是 | 执行时的 Baseline ID。必须是当前生效的 Baseline，不得使用历史 Baseline 冒充当前 | `ZB-PROD-2026-08-31-04` |
| `version` | string | 否 | 被检查对象的版本号 | `0.3.0`, `5.9.9` |

### 2.4 时间与操作字段

| 字段名 | 类型 | 必填 | 描述 | 示例 |
|---|---|---|---|---|
| `timestamp` | string | 是 | 检查执行时间，ISO 8601 格式（UTC） | `2026-08-31T08:30:00.000Z` |
| `operation` | string | 是 | 执行的操作名称，动词短语 | `verify_remote_head`, `scan_credentials`, `run_tests` |
| `target` | string | 否 | 操作的具体目标对象，如文件路径、API端点、测试套件名 | `server/config.js`, `tests/snapshot.test.js` |

### 2.5 状态与结果字段（核心：expected vs observed 必须区分）

| 字段名 | 类型 | 必填 | 描述 | 示例 |
|---|---|---|---|---|
| `expectedState` | object | 是 | **预期状态**。任务开始时建立的期望值，来自 Snapshot / Lock / Change Plan。不得与 observedState 混写。 | `{ "dccHead": "b6b047c", "coreHead": "b2e68f5" }` |
| `observedState` | object | 是 | **实际观测状态**。执行检查时实际读取到的值。必须来自实际读取/执行，不得用预期值填充。网络失败时填 null。 | `{ "dccHead": "b6b047c", "coreHead": "b2e68f5" }` |
| `result` | string | 是 | 检查结果，见第 6 节 Result 枚举（5种） | `PASS` |
| `decision` | string | 是 | 系统决策，见第 7 节 Decision 枚举（4种）。Result 与 Decision 不得混为一谈。 | `ALLOW` |
| `reason` | string | 否 | 得出 result 和 decision 的具体原因说明。失败/阻止时必须填写。 | `DCC remote HEAD matches expected b6b047c` |

### 2.6 完整性字段

| 字段名 | 类型 | 必填 | 描述 | 示例 |
|---|---|---|---|---|
| `integrity` | object | 否 | 证据完整性信息，包含证据链上溯引用。见第 9 节 Integrity 规则。 | `{ "snapshotId": "SNAP-XXX", "changePlanId": "PLAN-XXX", "lockId": "LOCK-XXX" }` |

---

## 3. expected vs observed 区分规则（核心硬约束）

### 3.1 定义

- **expectedState**：任务开始时，通过 Snapshot / Remote HEAD Lock / Change Plan 建立的**期望值**。代表"我们认为应该是什么"。
- **observedState**：执行检查时，通过实际读取 GitHub / 运行测试 / 扫描文件得到的**实际观测值**。代表"实际是什么"。

### 3.2 硬规则

1. **不得用 expectedState 的值填充 observedState**。即使预期值与实际值相同，也必须分别记录。
2. **observedState 为 null 时，result 必须为 NOT_VERIFIED**，不得写 PASS。
3. **expectedState 与 observedState 不一致时，result 必须为 FAIL 或 REPLAN_REQUIRED**，不得写 PASS。
4. **网络失败、API 超时、权限不足导致无法读取时，observedState 填 null，result 填 NOT_VERIFIED，decision 填 REVIEW_REQUIRED**。
5. **历史测试结果不得作为当前 observedState**。每次检查必须重新执行。

### 3.3 示例

```json
{
  "operation": "verify_remote_head",
  "expectedState": { "dccRemoteHead": "b6b047c" },
  "observedState": { "dccRemoteHead": "b6b047c" },
  "result": "PASS",
  "decision": "ALLOW",
  "reason": "DCC remote HEAD matches expected b6b047c"
}
```

```json
{
  "operation": "verify_remote_head",
  "expectedState": { "dccRemoteHead": "b6b047c" },
  "observedState": { "dccRemoteHead": "a1b2c3d" },
  "result": "REPLAN_REQUIRED",
  "decision": "REPLAN",
  "reason": "DCC remote HEAD changed from b6b047c to a1b2c3d during execution"
}
```

```json
{
  "operation": "verify_remote_head",
  "expectedState": { "dccRemoteHead": "b6b047c" },
  "observedState": null,
  "result": "NOT_VERIFIED",
  "decision": "REVIEW_REQUIRED",
  "reason": "Network connection reset, unable to fetch DCC remote HEAD"
}
```

---

## 4. Evidence Type 分类

Evidence Type 描述证据的**业务类别**。至少支持以下类型：

| Evidence Type | 描述 |
|---|---|
| `BASELINE_VERIFICATION` | Baseline ID 验证 |
| `SNAPSHOT_CREATION` | Repository Snapshot 创建 |
| `REMOTE_HEAD_LOCK` | Remote HEAD Lock 创建 |
| `REMOTE_HEAD_VERIFICATION` | Remote HEAD 验证（执行期间检查远程是否变化） |
| `CHANGE_PLAN_CREATION` | Change Plan 创建 |
| `CHANGE_PLAN_STATUS_UPDATE` | Change Plan 状态更新 |
| `FILE_MODIFICATION` | 文件修改记录 |
| `GIT_DIFF_AUDIT` | git diff 审计 |
| `TEST_EXECUTION` | 测试执行结果 |
| `SECURITY_SCAN` | 安全扫描结果（Token/Secret/Credential） |
| `PERMISSION_BOUNDARY_CHECK` | 权限边界检查 |
| `SUBMODULE_VERIFICATION` | Submodule 状态验证 |
| `COMMIT` | Git Commit 记录 |
| `PUSH` | Git Push 记录 |
| `GITHUB_SECOND_VERIFICATION` | GitHub 二次核验 |
| `EVIDENCE_BUNDLE_GENERATION` | Evidence Bundle 生成（P2） |
| `RELEASE_CANDIDATE_CREATION` | Release Candidate 创建（P4） |
| `CORE_COMPATIBILITY_CHECK` | Core 兼容性检查（P4） |
| `MANUAL_REVIEW` | 人工审核记录 |

不得虚构不存在的 Evidence Type。新增类型必须在本文档中注册。

---

## 5. Evidence Source 分类（14种）

Source 描述证据的**技术来源**。至少支持以下 14 种：

| Source | 描述 | 典型 sourceReference 示例 |
|---|---|---|
| `GITHUB` | GitHub REST API / Git 远程操作 | `GET /repos/{owner}/{repo}/commits/{sha}` |
| `LOCAL_REPOSITORY` | 本地 Git 仓库读取 | `git rev-parse HEAD`, `git status` |
| `GIT_STATUS` | git status 输出 | `git status --short` |
| `GIT_DIFF` | git diff 输出 | `git diff --stat`, `git diff --check` |
| `TEST` | 自动化测试执行 | `node --test tests/snapshot.test.js` |
| `SECURITY_SCAN` | 安全扫描工具/脚本 | `credential-scan docs/`, `grep -r "ghp_"` |
| `CONFIG` | 配置文件读取 | `server/config.js`, `package.json` |
| `SUBMODULE` | Git Submodule 状态 | `git ls-tree HEAD tools/development-command-console`, `.gitmodules` |
| `BUILD` | 构建/编译输出 | `npm run build`（如适用） |
| `BRIDGE` | DCC Local AI Bridge API | `GET /api/status`, `POST /api/ai/task` |
| `CHANGE_PLAN` | Change Plan 模块输出 | `changePlan.createChangePlan()`, `changePlan.validatePlanForExecution()` |
| `SNAPSHOT` | Snapshot 模块输出 | `snapshot.createSnapshot()`, `snapshot.verifyLock()` |
| `MANUAL_REVIEW` | 人工审核者输入 | `reviewer-01 manual approval` |
| `EVIDENCE_BUNDLE` | Evidence Bundle 聚合输出（P2） | `evidence-bundle.generate()` |

不得虚构不存在的 Evidence Source。新增 Source 必须在本文档中注册。

---

## 6. Result 枚举（5种，硬锁定）

Result 描述**检查本身的执行结果**。只允许以下 5 种值，不得随意增加新的结果枚举。

| Result | 定义 | 使用场景 |
|---|---|---|
| `PASS` | 实际检查成功，observedState 与 expectedState 一致，或检查项满足通过条件 | 测试全部通过、远程 HEAD 与预期一致、安全扫描无发现、权限边界未变 |
| `FAIL` | 实际检查失败，observedState 与 expectedState 不一致，或检查项不满足通过条件 | 测试有失败项、文件内容与预期不符、代码质量检查失败 |
| `BLOCKED` | 由于安全/权限/策略阻止，检查无法继续或结果被策略阻止 | 发现真实 Token/Secret、权限边界被扩大、未授权文件被修改、安全策略阻止操作 |
| `NOT_VERIFIED` | 没有足够事实完成验证，observedState 为 null 或不完整 | 网络失败无法 fetch、API 超时、权限不足无法读取、工具不可用 |
| `REPLAN_REQUIRED` | 事实基线发生变化，原计划失效，需要重新规划 | 远程 HEAD 变化、Core pinned SHA 变化、Baseline 冲突、工作区出现未预期的用户修改 |

### 6.1 Result 判定优先级

当多个条件同时满足时，按以下优先级判定（高优先级覆盖低优先级）：

1. `BLOCKED`（安全/权限阻止，最高优先级）
2. `REPLAN_REQUIRED`（基线变化，必须重新规划）
3. `FAIL`（检查失败）
4. `NOT_VERIFIED`（无法验证）
5. `PASS`（全部通过，最低优先级）

**例如**：测试通过但发现远程 HEAD 变化 → Result = REPLAN_REQUIRED（不是 PASS）。
**例如**：远程 HEAD 一致但发现真实 Token → Result = BLOCKED（不是 PASS）。

---

## 7. Decision 枚举（至少4种，硬锁定）

Decision 描述**系统基于 Result 做出的操作决策**。Evidence Result 与 Decision 不得混为一谈。

| Decision | 定义 | 典型对应 Result |
|---|---|---|
| `ALLOW` | 允许继续执行当前操作/进入下一阶段 | PASS |
| `STOP` | 立即停止当前操作，不得继续 | BLOCKED |
| `REPLAN` | 停止当前操作，重新建立事实基线并重新生成计划 | REPLAN_REQUIRED |
| `REVIEW_REQUIRED` | 暂停，需要人工审核或额外信息才能继续 | NOT_VERIFIED, FAIL（非阻断性失败） |

### 7.1 Result → Decision 映射规则

| Result | 默认 Decision | 说明 |
|---|---|---|
| PASS | ALLOW | 检查通过，允许继续 |
| FAIL | REVIEW_REQUIRED | 检查失败，需人工判断是否可继续（非安全类失败） |
| BLOCKED | STOP | 安全/权限阻止，必须立即停止 |
| NOT_VERIFIED | REVIEW_REQUIRED | 无法验证，需人工确认或补充信息 |
| REPLAN_REQUIRED | REPLAN | 基线变化，必须重新规划 |

### 7.2 Result vs Decision 区分示例

**示例 1：远程 HEAD 变化**
- Result = `REPLAN_REQUIRED`（事实基线发生变化）
- Decision = `REPLAN`（系统决定重新规划）
- 不是：Result = FAIL, Decision = STOP（混淆了结果与决策）

**示例 2：安全扫描发现真实 Token**
- Result = `BLOCKED`（安全策略阻止）
- Decision = `STOP`（系统决定立即停止）
- 不是：Result = FAIL, Decision = REVIEW_REQUIRED（安全问题必须 STOP，不是 REVIEW）

**示例 3：网络失败无法验证远程 HEAD**
- Result = `NOT_VERIFIED`（没有足够事实）
- Decision = `REVIEW_REQUIRED`（需要人工确认网络或补充验证）
- 不是：Result = PASS（不得把未验证写成通过）

---

## 8. Evidence 完整性规则（证据链上溯）

每条 Evidence 必须尽可能能够追溯到完整的操作链：

```
Baseline
    ↓
Snapshot（记录任务开始时的仓库状态）
    ↓
Remote HEAD Lock（锁定预期 HEAD）
    ↓
Change Plan（记录任务范围、允许/禁止操作）
    ↓
Operation（实际执行的操作）
    ↓
Evidence（操作产生的证据）
    ↓
Decision（基于证据的决策）
```

### 8.1 Integrity 字段要求

`integrity` 对象必须尽可能包含以下上溯引用：

| 字段 | 类型 | 描述 |
|---|---|---|
| `baselineId` | string | 关联的 Baseline ID（与顶层 baselineId 一致，用于完整性校验） |
| `snapshotId` | string | 关联的 Snapshot ID |
| `lockId` | string | 关联的 Remote HEAD Lock ID |
| `changePlanId` | string | 关联的 Change Plan ID |
| `taskId` | string | 关联的任务 ID |
| `parentEvidenceId` | string | 父 Evidence ID（用于证据链中的顺序关系） |

### 8.2 禁止孤立证据

禁止只保存一个 `"PASS"` 而没有来源、时间、SHA、对象等上下文。每条 Evidence 必须至少包含：
- evidenceId
- evidenceType
- source
- actor
- repository
- commitSha
- baselineId
- timestamp
- operation
- expectedState
- observedState
- result
- decision

缺少以上任一字段的 Evidence 视为**不完整证据**，result 必须标记为 NOT_VERIFIED，decision 必须标记为 REVIEW_REQUIRED。

---

## 9. Integrity 校验规则

### 9.1 字段完整性校验

- 所有必填字段必须非空（observedState 除外，允许为 null 但必须标记 NOT_VERIFIED）
- commitSha 必须符合 7-40 位十六进制格式
- timestamp 必须符合 ISO 8601 格式
- result 必须是 5 种枚举之一
- decision 必须是 4 种枚举之一
- source 必须是 14 种已注册分类之一
- evidenceType 必须是已注册类型之一

### 9.2 逻辑一致性校验

- result = PASS 时，observedState 不得为 null，且必须与 expectedState 一致（或满足通过条件）
- result = NOT_VERIFIED 时，observedState 必须为 null（或包含 null 字段）
- result = BLOCKED 时，reason 必须填写阻止原因
- result = REPLAN_REQUIRED 时，reason 必须说明哪个基线发生了变化
- decision = STOP 时，result 必须为 BLOCKED
- decision = REPLAN 时，result 必须为 REPLAN_REQUIRED

### 9.3 时间一致性校验

- timestamp 不得早于关联 Snapshot 的 createdAt
- timestamp 不得晚于当前时间（允许 60 秒时钟偏差）

---

## 10. Correlation ID 规则

### 10.1 定义

Correlation ID 用于将多条 Evidence 串联到同一任务/操作链。同一 Change Plan 产生的所有 Evidence 共享同一 correlationId。

### 10.2 格式

推荐格式：`TASK-<version>-<phase>-<date>-<sequence>`
示例：`TASK-V041-P1-20260831-001`

### 10.3 规则

1. 同一 Change Plan 的所有 Evidence 必须使用相同的 correlationId
2. 不同 Change Plan 的 Evidence 不得共享 correlationId
3. correlationId 必须与 Change Plan 的 taskId 一致
4. Evidence Bundle（P2）通过 correlationId 聚合同一任务的所有 Evidence

---

## 11. 禁止伪证据规则（10条硬约束）

绝对禁止以下行为：

1. **禁止用预期 SHA 冒充实际 SHA**。expectedState 中的值不得复制到 observedState。
2. **禁止用本地 HEAD 冒充 remote HEAD**。remoteHead 字段必须来自实际 git fetch / GitHub API，不得用本地 HEAD 填充。
3. **禁止用历史测试结果冒充当前测试**。每次测试必须重新执行，observedState 必须来自当前执行。
4. **禁止用旧 Baseline 冒充当前 Baseline**。baselineId 必须是执行时当前生效的 Baseline，不得使用历史 Baseline。
5. **禁止测试未运行却写 PASS**。result = PASS 必须有实际测试执行记录和 observedState。
6. **禁止 GitHub 未读取却写 GitHub PASS**。涉及 GitHub 的检查必须实际 fetch / API 调用，网络失败时写 NOT_VERIFIED。
7. **禁止 Core 未验证却写 Core PASS**。涉及 Core 的检查必须实际读取 Core 状态，无法读取时写 NOT_VERIFIED。
8. **禁止网络失败却写验证成功**。网络连接重置、超时、DNS 失败时，observedState = null，result = NOT_VERIFIED。
9. **禁止推测结果写成事实**。基于经验/推测/概率的判断必须标记为 NOT_VERIFIED 或在 reason 中明确标注"推测"。
10. **禁止篡改历史 Evidence**。已生成的 Evidence 不得修改字段值。如需更正，必须生成新的 Evidence 并在 reason 中引用旧 Evidence ID 说明更正原因。

---

## 12. 历史记录规则

### 12.1 历史事实不可篡改

不得修改历史事实。例如：
- V0.4.0 执行时使用 Baseline `ZB-PROD-2026-08-31-03`
- 即使当前 Baseline 已升级为 `ZB-PROD-2026-08-31-04`
- 历史记录（DEVELOPMENT-LOG.md、V04-CHANGE-CONTRACT.md、历史 Evidence）中的 03 不得替换成 04

### 12.2 当前生效文档可更新

只有"当前生效文档"可以更新 Baseline 引用：
- REPOSITORY-FACT-BASELINE.md（当前事实基线）
- V04-ARCHITECTURE.md（当前架构文档）
- PRODUCTION-GATE-XHS-APP.md（当前生产门禁）
- DUAL_REPO_RELEASE_POLICY.md（当前发布策略）
- DUAL_REPO_RELEASE_STATE.md（当前发布状态）

### 12.3 Evidence 中的 Baseline ID

每条 Evidence 的 baselineId 字段记录的是**执行时的 Baseline**，这是历史事实，后续 Baseline 升级时不得追溯修改历史 Evidence 的 baselineId。

---

## 13. Evidence Bundle 结构（P2 预留，本阶段不实现）

P2 将基于本 Schema 实现 Evidence Bundle，固定为以下 8 个 JSON 文件：

| 文件 | 内容 | 对应 Evidence Type |
|---|---|---|
| `baseline.json` | Baseline 验证结果 | BASELINE_VERIFICATION |
| `repository-state.json` | 双仓库状态快照 | SNAPSHOT_CREATION, REMOTE_HEAD_LOCK, SUBMODULE_VERIFICATION |
| `changed-files.json` | 修改文件清单 + git diff | FILE_MODIFICATION, GIT_DIFF_AUDIT |
| `test-results.json` | 测试执行结果 | TEST_EXECUTION |
| `security-results.json` | 安全扫描结果 | SECURITY_SCAN |
| `regression-results.json` | 回归测试结果 | TEST_EXECUTION (regression) |
| `permission-results.json` | 权限边界检查结果 | PERMISSION_BOUNDARY_CHECK |
| `audit-summary.json` | 审计汇总 + 最终决策 | GITHUB_SECOND_VERIFICATION, MANUAL_REVIEW |

每个 JSON 文件包含一个或多个符合本 Schema 的 Evidence 对象数组。

---

## 14. 完整 Evidence 示例

### 示例 1：Remote HEAD 验证通过

```json
{
  "evidenceId": "EVID-MZ3X2K-A1B2C3",
  "evidenceType": "REMOTE_HEAD_VERIFICATION",
  "correlationId": "TASK-V041-P1-20260831-001",
  "source": "GITHUB",
  "sourceReference": "git fetch origin && git rev-parse origin/main",
  "actor": "dcc-remote-head-lock",
  "repository": "Zachary-1012/Development-Command-Console",
  "branch": "main",
  "commitSha": "b6b047cd79d46f16eb0397d2a7a83df71cc327f3",
  "remoteHead": "b6b047cd79d46f16eb0397d2a7a83df71cc327f3",
  "baselineId": "ZB-PROD-2026-08-31-04",
  "version": "0.3.0",
  "timestamp": "2026-08-31T08:30:00.000Z",
  "operation": "verify_remote_head",
  "target": "origin/main",
  "expectedState": {
    "dccRemoteHead": "b6b047cd79d46f16eb0397d2a7a83df71cc327f3"
  },
  "observedState": {
    "dccRemoteHead": "b6b047cd79d46f16eb0397d2a7a83df71cc327f3"
  },
  "result": "PASS",
  "decision": "ALLOW",
  "reason": "DCC remote HEAD matches expected b6b047c",
  "integrity": {
    "baselineId": "ZB-PROD-2026-08-31-04",
    "snapshotId": "SNAP-MZ3X1K-D4E5F6",
    "lockId": "LOCK-MZ3X1K-G7H8I9",
    "changePlanId": "PLAN-MZ3X1K-J0K1L2",
    "taskId": "TASK-V041-P1-20260831-001"
  }
}
```

### 示例 2：安全扫描发现真实 Token（BLOCKED）

```json
{
  "evidenceId": "EVID-MZ3X2K-B4C5D6",
  "evidenceType": "SECURITY_SCAN",
  "correlationId": "TASK-V041-P1-20260831-001",
  "source": "SECURITY_SCAN",
  "sourceReference": "credential-scan server/config.js",
  "actor": "dcc-security-gate",
  "repository": "Zachary-1012/Development-Command-Console",
  "branch": "main",
  "commitSha": "b6b047cd79d46f16eb0397d2a7a83df71cc327f3",
  "baselineId": "ZB-PROD-2026-08-31-04",
  "timestamp": "2026-08-31T08:31:00.000Z",
  "operation": "scan_credentials",
  "target": "server/config.js",
  "expectedState": {
    "credentialsFound": false
  },
  "observedState": {
    "credentialsFound": true,
    "credentialType": "github_pat",
    "file": "server/config.js",
    "line": 42
  },
  "result": "BLOCKED",
  "decision": "STOP",
  "reason": "Real GitHub PAT found in server/config.js line 42. Security policy violation.",
  "integrity": {
    "baselineId": "ZB-PROD-2026-08-31-04",
    "taskId": "TASK-V041-P1-20260831-001"
  }
}
```

### 示例 3：网络失败无法验证（NOT_VERIFIED）

```json
{
  "evidenceId": "EVID-MZ3X2K-C7D8E9",
  "evidenceType": "REMOTE_HEAD_VERIFICATION",
  "correlationId": "TASK-V041-P1-20260831-001",
  "source": "GITHUB",
  "sourceReference": "git fetch origin",
  "actor": "dcc-remote-head-lock",
  "repository": "Zachary-1012/Development-Command-Console",
  "branch": "main",
  "commitSha": "b6b047cd79d46f16eb0397d2a7a83df71cc327f3",
  "remoteHead": null,
  "baselineId": "ZB-PROD-2026-08-31-04",
  "timestamp": "2026-08-31T08:32:00.000Z",
  "operation": "verify_remote_head",
  "target": "origin/main",
  "expectedState": {
    "dccRemoteHead": "b6b047cd79d46f16eb0397d2a7a83df71cc327f3"
  },
  "observedState": null,
  "result": "NOT_VERIFIED",
  "decision": "REVIEW_REQUIRED",
  "reason": "git fetch failed: Connection was reset. Unable to verify DCC remote HEAD. Local tracking branch origin/main = b6b047c matches local HEAD, but remote state cannot be confirmed.",
  "integrity": {
    "baselineId": "ZB-PROD-2026-08-31-04",
    "taskId": "TASK-V041-P1-20260831-001"
  }
}
```

---

## 15. 版本历史

| 版本 | 日期 | Baseline | 变更 |
|---|---|---|---|
| 1.0 | 2026-08-31 | ZB-PROD-2026-08-31-04 | 初始版本。定义 21 个字段、14 种 Source、5 种 Result、4 种 Decision、完整性规则、禁止伪证据规则、历史记录规则。 |

---

**本文件为 Evidence 数据契约（P1），定义标准与规则。业务代码实现将在 P2（Evidence Bundle）中进行。本文件不得在未经授权的情况下修改字段定义或枚举值。**
