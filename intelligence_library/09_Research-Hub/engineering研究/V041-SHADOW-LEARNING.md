# DCC V0.4.1 P2 — Shadow Learning 模块文档

**Baseline ID**: ZB-PROD-2026-08-31-04
**Phase**: P2 — Shadow Learning Implementation
**Module**: server/shadow-learning.js
**Status**: IMPLEMENTED
**Core Principle**: Shadow Agent is READ_ONLY, never modifies production

---

## 1. 模块定位

Shadow Learning 是 DCC 的影子学习引擎，负责在不影响生产系统的前提下，读取历史数据、识别重复模式、生成改进建议。

Shadow Agent 永远不拥有生产写权限。它可以预测、分析、推荐，但所有建议必须经过人工审查和批准才能进入正式流程。

**工作模型**:
```
                 真实任务
                    │
             ┌──────┴──────┐
             ↓             ↓
          正式流程       Shadow Agent
             │             │
             │        独立分析/预测
             │             │
             ↓             ↓
          实际结果      Shadow 结果
             │             │
             └──────┬──────┘
                    ↓
                对比评估
                    ↓
              记录成功/失败
                    ↓
              更新经验数据库
```

---

## 2. 权限硬锁

Shadow Agent 的权限是不可变的硬锁：

| 权限 | 状态 |
|---|---|
| read | ALLOW |
| analyze | ALLOW |
| recommend | ALLOW |
| write | DENY |
| commit | DENY |
| merge | DENY |
| deploy | DENY |
| exec | DENY |
| modifyPermissions | DENY |
| modifyProductionRules | DENY |

**绝对禁止**:
- 自动修改 Core/DCC 代码
- 自动 commit/push
- 自动 merge
- 自动 deploy
- 自动改变权限边界
- 自动改变生产规则
- 自动执行 shell/代码

---

## 3. 状态机

Shadow Analysis 的状态流转：

```
SHADOW (初始观察)
   ↓
CANDIDATE (生成候选)
   ↓
REVIEW_REQUIRED (等待人工审查)
   ├─→ APPROVED (人工批准)
   └─→ REJECTED (人工拒绝)
```

**合法转换**:
| 当前状态 | 允许转换到 |
|---|---|
| SHADOW | CANDIDATE, REJECTED |
| CANDIDATE | REVIEW_REQUIRED, REJECTED |
| REVIEW_REQUIRED | APPROVED, REJECTED, CANDIDATE |
| APPROVED | (终态，无 outgoing) |
| REJECTED | SHADOW (可重新开始) |

**禁止非法跳跃**: 例如 SHADOW → APPROVED 是不允许的。

---

## 4. 候选类型

Shadow Analysis 可以生成以下类型的候选：

| 类型 | 说明 |
|---|---|
| PATTERN | 可复用模式（从重复出现的 Case Type 中识别） |
| LESSON | 经验教训（从成功案例中提取） |
| RISK | 风险提示（从失败原因中识别） |
| REGRESSION_HINT | 回归提示（从 Failure Database 中识别） |
| ARCHITECTURE_HINT | 架构建议（基于双仓库结构） |
| SECURITY_HINT | 安全建议（从安全相关 Evidence 中识别） |

每个候选包含：
- candidateId / type / title / description
- evidence（支撑证据）
- confidence（置信度 0-1）
- status（PENDING）
- generatedByShadow: true
- sourceType: SHADOW_ANALYSIS

---

## 5. 核心功能

### 5.1 Shadow Analysis 管理

- `createShadowAnalysis(options)` — 创建 Shadow Analysis（初始状态 SHADOW）
- `getShadowAnalysis(analysisId)` — 获取单个分析
- `listShadowAnalyses(options)` — 列出分析（支持按 status/analysisType/targetRepository 过滤）

### 5.2 候选生成

- `generateCandidates(analysisId)` — 从输入数据中自动生成候选
  - 从重复 Case Type 生成 PATTERN
  - 从失败原因生成 RISK
  - 从 Failure Database 生成 REGRESSION_HINT
  - 从安全 Evidence 生成 SECURITY_HINT
  - 从双仓库结构生成 ARCHITECTURE_HINT
  - 自动去重（按 title）
  - 自动转换状态到 CANDIDATE

### 5.3 审查流程

- `submitForReview(analysisId, notes)` — 提交审查（状态 → REVIEW_REQUIRED）
- `approveShadowAnalysis(analysisId, approver, notes)` — 人工批准（状态 → APPROVED）
- `rejectShadowAnalysis(analysisId, rejecter, reason)` — 人工拒绝（状态 → REJECTED）
- `updateShadowStatus(analysisId, status, reason)` — 通用状态更新（带合法性检查）

### 5.4 候选提升（Promote）

- `promoteShadowCandidate(analysisId, options)` — 提升候选为 Change Plan 建议

**关键约束**:
- 只有 APPROVED 状态的分析才能提升
- 提升只产生 Change Plan **建议**（suggestion），不是实际 Change Plan
- 建议状态为 REVIEW_REQUIRED，需要人工确认后才能创建实际 Change Plan
- 建议的 allowedOperations 只包含 read/analyze/document
- 建议的 forbiddenOperations 包含 write/commit/merge/deploy/exec
- **不直接修改代码**

### 5.5 推荐与权限

- `getShadowRecommendations(options)` — 获取所有提升后的建议
- `getShadowPermissions()` — 获取 Shadow 权限状态（硬锁确认）

---

## 6. API 端点

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/api/shadow-learning` | 列出 Shadow Analysis |
| POST | `/api/shadow-learning/analyze` | 创建分析并自动生成候选、提交审查 |
| GET | `/api/shadow-learning/:id` | 获取单个分析 |
| POST | `/api/shadow-learning/:id/status` | 更新状态（approve/reject） |
| POST | `/api/shadow-learning/:id/promote` | 提升候选为 Change Plan 建议 |

**`/api/shadow-learning/analyze` 的自动化流程**:
1. 创建 Shadow Analysis（状态 SHADOW）
2. 自动生成候选（状态 → CANDIDATE）
3. 自动提交审查（状态 → REVIEW_REQUIRED）
4. 返回更新后的分析

---

## 7. 输入数据格式

Shadow Analysis 接受以下输入数据（inputData）：

```json
{
  "cases": [
    { "caseType": "...", "result": "...", "failureReason": "..." }
  ],
  "failures": [
    { "failureType": "...", "failureReason": "..." }
  ],
  "evidences": [
    { "evidenceType": "...", "result": "..." }
  ],
  "patterns": [
    { "patternName": "...", "confidence": 0.8 }
  ]
}
```

模块会自动汇总输入数据摘要（inputSummary），包括 caseCount/failureCount/evidenceCount 等。

---

## 8. 安全边界

- Shadow Agent 默认 READ_ONLY
- 绝不自动修改 Core/DCC
- 绝不自动 commit/push/deploy
- 绝不自动改变权限/生产规则
- 所有输出标记为 generatedByShadow=true, sourceType=SHADOW_ANALYSIS
- Shadow 输出只能作为建议，不能作为事实来源
- Promote 只产生 Change Plan 建议，不直接修改代码
- 建议需要人工确认后才能创建实际 Change Plan

---

## 9. 测试覆盖

测试文件: `tests/shadow-learning.test.js`

覆盖范围：
- createShadowAnalysis（正常/异常/权限/输入摘要/状态历史）
- getShadowAnalysis / listShadowAnalyses（过滤）
- updateShadowStatus（合法转换/非法转换/非法枚举/历史记录）
- generateCandidates（PATTERN/RISK/REGRESSION_HINT/SECURITY_HINT/置信度/自动状态转换）
- submitForReview（正常/无候选）
- approveShadowAnalysis / rejectShadowAnalysis
- promoteShadowCandidate（正常/未批准/建议状态/禁止操作/不直接改代码）
- getShadowRecommendations
- getShadowPermissions（硬锁确认）
- 常量导出验证（SHADOW_STATUSES/STATUS_TRANSITIONS/SHADOW_PERMISSIONS/CANDIDATE_TYPES）

---

## 10. 与 Learning Store 的关系

```
Learning Store (learning-store.js)
    │
    │ 提供 Case / Failure / Pattern / Lesson 数据
    ↓
Shadow Learning (shadow-learning.js)
    │
    │ 读取历史数据，识别模式，生成建议
    ↓
Shadow Candidate (PATTERN / LESSON / RISK / REGRESSION_HINT / ...)
    │
    ↓ 人工审查批准
Change Plan Suggestion (REVIEW_REQUIRED)
    │
    ↓ 人工确认
Actual Change Plan (由 change-plan.js 创建)
```

Shadow Learning 依赖 Learning Store 提供的数据，但当前通过 inputData 参数传入，不直接 require learning-store（保持模块独立性，便于测试）。

---

## 11. 已知限制

1. 内存存储，Server 重启后数据丢失
2. 候选生成基于规则匹配，不使用 ML 算法
3. 不支持自动从 Learning Store 拉取数据（需手动传入 inputData）
4. 不支持 Shadow 结果与实际结果的自动对比评估（后续 P6 实现）
5. Promote 只产生建议，不自动创建 Change Plan（需人工确认）

---

## 12. 后续阶段

- **P3 Security Gate**: 将 Shadow 识别的 RISK/SECURITY_HINT 纳入自动化安全门禁
- **P6 Shadow Learning**: 实现 Shadow 结果与实际结果的自动对比评估，完善影子学习闭环
- **P7 Release Candidate**: 使用 Shadow 分析作为 RC 审批的参考输入
