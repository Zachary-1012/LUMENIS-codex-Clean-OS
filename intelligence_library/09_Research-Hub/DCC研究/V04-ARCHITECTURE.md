# DCC V0.4 Architecture — Controlled Development & Release Gate

> Baseline ID: ZB-PROD-2026-08-31-04
> Version: V0.4.0 (Phase 1: Snapshot + Change Plan + Remote HEAD Lock)
> Status: ACTIVE

## 1. V0.4 定位

DCC V0.4 从 "AI Development Command Console" 升级为：

**AI Development + Audit + Evidence + Release Control Plane**

核心目标：
- AI 可以提出变更 → DCC 自动形成证据 → 自动验证 → 生成 Release Candidate → 由 Core 决定是否接收
- DCC 成为两个仓库之间的安全中间层
- 不放开写权限，不自动 commit/push/merge/deploy

## 2. V0.4 分阶段路线

| 阶段 | 版本 | 功能 | 状态 |
|---|---|---|---|
| Phase 1 | V0.4.0 | Repository Snapshot + Change Plan + Remote HEAD Lock | ✅ ACTIVE |
| Phase 2 | V0.4.1 | Evidence Bundle + Security Gate | ⏳ TODO |
| Phase 3 | V0.4.2 | Release Candidate + Core Compatibility Reader | ⏳ TODO |

## 3. V0.4.0 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      DCC Bridge (127.0.0.1:8787)            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Snapshot    │    │ Change Plan  │    │ (Future)     │ │
│  │  Module      │    │  Module      │    │ Evidence     │ │
│  │              │    │              │    │ Release Gate │ │
│  │ - create     │    │ - create     │    │              │ │
│  │ - get        │    │ - get        │    │              │ │
│  │ - list       │    │ - list       │    │              │ │
│  │ - lock HEAD  │    │ - status     │    │              │ │
│  │ - verify     │    │ - update     │    │              │ │
│  │ - release    │    │ - validate   │    │              │ │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘ │
│         │                     │                               │
│         └──────────┬──────────┘                               │
│                    ▼                                          │
│         ┌─────────────────────┐                              │
│         │   In-Memory Storage  │                              │
│         │   (Map, no disk I/O) │                              │
│         └─────────────────────┘                              │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 4. Snapshot Module (server/snapshot.js)

### 4.1 功能

1. **Repository Snapshot** — 记录任务开始时的双仓库状态
2. **Remote HEAD Lock** — 锁定预期 HEAD，执行期间检测远程变化
3. **Lock Verification** — 验证锁定是否仍然有效，发现变化立即 STOP

### 4.2 Snapshot 数据结构

```json
{
  "id": "SNAP-XXXXXX",
  "createdAt": "ISO-8601",
  "baselineId": "ZB-PROD-2026-08-31-04",
  "core": {
    "repository": "owner/Z-Brand-Core",
    "head": "40-char-SHA",
    "visibility": "private",
    "pinnedDccSha": "40-char-SHA"
  },
  "dcc": {
    "repository": "owner/Development-Command-Console",
    "head": "40-char-SHA",
    "visibility": "private"
  },
  "workingState": "clean",
  "relevantFiles": ["server/server.js"],
  "status": "ACTIVE",
  "evidence": { "source": "dcc-snapshot", "checkedAt": "ISO-8601" }
}
```

### 4.3 Remote HEAD Lock 数据结构

```json
{
  "id": "LOCK-XXXXXX",
  "snapshotId": "SNAP-XXXXXX",
  "taskId": "TASK-XXXXXX",
  "expectedCoreHead": "40-char-SHA",
  "expectedDccHead": "40-char-SHA",
  "lockedAt": "ISO-8601",
  "status": "LOCKED | BROKEN | RELEASED",
  "lastVerifiedAt": "ISO-8601",
  "verificationCount": 0,
  "evidence": { "source": "dcc-remote-head-lock" }
}
```

### 4.4 Lock Verification 结果

| 状态 | 含义 | 动作 |
|---|---|---|
| VALID | 当前 HEAD 与预期一致 | CONTINUE |
| REMOTE_CHANGED | Core 或 DCC HEAD 已变化 | STOP_REPLAN_REQUIRED |

### 4.5 API 端点

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | /api/snapshot | 列出所有快照 |
| POST | /api/snapshot | 创建快照 |
| GET | /api/snapshot/:id | 获取单个快照 |
| POST | /api/snapshot/lock | 创建 Remote HEAD Lock |
| GET | /api/snapshot/lock/:id | 获取 Lock 状态 |
| POST | /api/snapshot/lock/:id/verify | 验证 Lock |

## 5. Change Plan Module (server/change-plan.js)

### 5.1 功能

1. **Change Plan 生成** — 将开发需求转化为结构化变更计划
2. **状态机管理** — DRAFT → PLANNING → APPROVED → EXECUTING → COMPLETED/FAILED
3. **执行前校验** — 验证计划是否可执行（状态 + 必要字段）

### 5.2 Change Plan 数据结构

```json
{
  "id": "PLAN-XXXXXX",
  "createdAt": "ISO-8601",
  "updatedAt": "ISO-8601",
  "requirement": "自然语言需求描述",
  "baselineId": "ZB-PROD-2026-08-31-04",
  "snapshotId": "SNAP-XXXXXX",
  "source": "doubao | codex | claude | local-agent",
  "target": {
    "repository": "owner/repo",
    "files": ["server/snapshot.js"]
  },
  "operations": {
    "allowed": ["create-file", "modify-file"],
    "forbidden": ["modify-core", "auto-deploy"]
  },
  "expected": {
    "tests": ["snapshot.test.js"],
    "evidence": ["test-results", "git-diff"]
  },
  "rollbackStrategy": "回滚策略描述",
  "promotionImpact": "晋级影响描述",
  "status": "DRAFT",
  "statusHistory": [{ "status": "DRAFT", "at": "ISO-8601", "note": "Plan created" }],
  "evidence": { "source": "dcc-change-plan" }
}
```

### 5.3 状态机

```
DRAFT ──► PLANNING ──► APPROVED ──► EXECUTING ──► COMPLETED
  │          │            │             │
  │          │            │             └──► FAILED ──► DRAFT
  │          │            └──► CANCELLED ──► DRAFT
  │          └──► CANCELLED ──► DRAFT
  └──► CANCELLED ──► DRAFT
```

| 当前状态 | 允许转换到 |
|---|---|
| DRAFT | PLANNING, CANCELLED |
| PLANNING | APPROVED, CANCELLED, DRAFT |
| APPROVED | EXECUTING, CANCELLED |
| EXECUTING | COMPLETED, FAILED, CANCELLED |
| COMPLETED | (终态) |
| FAILED | DRAFT |
| CANCELLED | DRAFT |

### 5.4 执行前校验 (validatePlanForExecution)

计划必须满足以下条件才可执行：
1. 状态为 APPROVED
2. target.files 非空
3. operations.allowed 非空
4. expected.tests 非空

### 5.5 API 端点

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | /api/change-plan | 列出所有计划（可按 status 过滤） |
| POST | /api/change-plan | 创建计划 |
| GET | /api/change-plan/:id | 获取单个计划 |
| POST | /api/change-plan/:id/status | 更新状态 |
| POST | /api/change-plan/:id/update | 更新内容（仅 DRAFT/PLANNING） |
| POST | /api/change-plan/:id/validate | 校验可执行性 |

## 6. 安全边界（V0.4.0 维持不变）

| 权限 | 状态 |
|---|---|
| READ | ALLOW |
| TASK | ALLOW |
| AUDIT | ALLOW |
| TEST | CONTROLLED |
| WRITE | DENY |
| COMMIT | DENY |
| MERGE | DENY |
| DEPLOY | DENY |
| SHELL EXEC | DENY |
| CODE EXEC | DENY |

**V0.4.0 新增安全保障**：
- Snapshot/Change Plan 仅内存存储，不写入磁盘
- 不执行 git 命令（不调用 child_process）
- 不修改任何仓库状态
- 所有操作返回 Evidence（source + checkedAt）
- 不接受/存储 Token/Secret/Credential
- Remote HEAD Lock 发现远程变化立即 STOP，防止并发 Agent 覆盖

## 7. 测试覆盖

| 模块 | 测试数 | 覆盖 |
|---|---|---|
| snapshot.js | ~50 | isValidSha, isValidRepo, createSnapshot, getSnapshot, listSnapshots, createLock, verifyLock, getLock, listLocks, releaseLock, Security Boundary |
| change-plan.js | ~43 | createChangePlan, getChangePlan, listChangePlans, updatePlanStatus, updateChangePlan, validatePlanForExecution, Security Boundary, Status Machine |
| 原有测试 | 82 | bridge.test.js (36) + github-audit.test.js (46) |
| **总计** | **175** | |

## 8. 与 Core 的关系

```
DCC (Development SoT)
  │
  ├── Snapshot: 记录 Core HEAD + DCC HEAD + Core pinned SHA
  ├── Change Plan: 规划 DCC 自身变更（不碰 Core）
  ├── Remote HEAD Lock: 检测 Core/DCC 远程变化
  │
  └── 不自动更新 Core pinned SHA
      （需等待 V0.4.2 Release Candidate + Core Compatibility + 人工批准）
```

**V0.4.0 不做的事**：
- 不自动 push Core
- 不自动 merge
- 不自动 deploy
- 不自动修改生产代码
- 不自动升级 submodule
- 不自动获取生产 Token
- 不自动执行任意 shell

## 9. 后续阶段 (TODO)

### V0.4.1 — Evidence Bundle + Security Gate
- Evidence Bundle 生成（baseline.json, repository-state.json, changed-files.json, test-results.json, security-results.json, regression-results.json, permission-results.json, audit-summary.json）
- 安全扫描集成
- 权限校验集成

### V0.4.2 — Release Candidate + Core Compatibility Reader
- Release Candidate 生成（RC ID, DCC SHA, Core SHA, Submodule SHA, 测试结果, 安全结果, Diff, Evidence, Rollback SHA）
- Core Compatibility Reader（文件层/版本层/功能层/安全层/测试层兼容性检查）
- Promotion Gate 状态机（CANDIDATE → TESTED → AUDITED → APPROVED → PROMOTABLE → PROMOTED）
- Core Promotion 提议（DCC 提出建议，人工批准后 Core 更新 gitlink）
