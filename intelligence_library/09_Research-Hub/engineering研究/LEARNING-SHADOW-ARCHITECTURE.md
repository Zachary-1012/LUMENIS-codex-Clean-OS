# DCC Learning & Shadow Layer 架构基线

> Baseline ID: ZB-PROD-2026-08-31-04
> Version: 1.0
> Status: ARCHITECTURE BASELINE（架构基线，P4 前不写学习代码）
> Last Updated: 2026-08-31

---

## 1. 定位

DCC 不应该直接变成一个"训练 AI 的平台"，而应该先成为一个能够持续产生**高质量、可验证、可追溯软件工程经验数据**的系统。

有了这个基础以后，AI 才能进行：
```
检索 → 类比 → 预测 → Shadow → 实际结果 → 评价 → 经验沉淀 → 再检索
```

最终形成持续学习闭环：
```
知识
 ↓
经验
 ↓
预测
 ↓
影子执行
 ↓
真实结果
 ↓
评价
 ↓
经验更新
 ↓
下一次更好的预测
```

**DCC 不是 OpenHands / SWE-agent 的简单复制品**。吸收它们的 Agent 能力，但保留自己的治理内核：
- 事实控制（GitHub 实际状态优先）
- 双仓库控制（Core = 生产 SoT，DCC = 研发 SoT）
- 权限控制（最小权限，WRITE/COMMIT/MERGE/DEPLOY/EXEC 默认 DENY）
- 变更计划（Change Plan + 状态机）
- 证据链（Evidence Schema + Evidence Bundle）
- 安全门（Security Gate + 凭据扫描 + 权限漂移检测）
- 长期经验（Learning Database + Case Library + Failure Database）
- 影子学习（Shadow Agent：只观察、预测、给第二意见，不拥有写权限）

---

## 2. 三层学习模型

### 2.1 第一层：知识学习（Knowledge Learning）

建立 **DCC Learning Database**，长期保存外部知识与案例。

**内容分类**：
- GitHub 优秀项目案例
- 软件工程 Agent 案例（SWE-agent、OpenHands 等）
- 架构案例（双仓库、Monorepo、Submodule、微服务）
- CI/CD 案例（GitHub Actions、Workflow 设计、多阶段流水线）
- Git 工作流案例（branch strategy、merge vs rebase、release flow）
- 安全门禁案例（凭据扫描、权限最小化、Secret Management）
- 双仓库 / Monorepo / Submodule 案例
- Agent Memory 案例（短期记忆、长期记忆、经验回放）
- 测试与回归案例（单元测试、集成测试、回归测试、测试金字塔）
- 失败案例（专门记录，避免重复错误）
- 自己历史开发案例（DCC 自身的开发经验）

**性质**：知识库 / RAG / Case Library。外部案例需要标注来源、可信度、是否经过实际验证。

### 2.2 第二层：经验学习（Experience Learning）

比普通知识库更重要。学习"什么情况下什么方案有效、什么情况下容易失败"。

**核心机制**：
```
任务 A
  → 方案 X
  → 测试失败
  → 原因 Y
  → 改成方案 Z
  → 最终成功
```

以后遇到类似任务：
```
新任务
  ↓
检索历史相似任务
  ↓
发现方案 X 曾失败
  ↓
降低 X 的优先级
  ↓
优先尝试 Z
```

这就是 **Experience Replay / Case-Based Learning**。它不是简单"记住答案"，而是学习方案与结果之间的因果关系。

**SWE-agent 的启示**：把 Agent 与真实 GitHub repository、任务、工具反馈连接起来，可以形成可评估的软件工程 Agent 工作流；特别强调可复现、可评估的 Agent-Computer Interface。DCC 的 Evidence Schema 正好提供了这种可评估、可复现的数据基础。

### 2.3 第三层：影子学习（Shadow Learning）

Shadow Agent 在正式流程旁边独立分析、预测、给第二意见，但**永远不拥有生产写权限**。

**工作流**：
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

**Shadow Agent 可以做**：
- 预测应该怎么改
- 判断风险
- 推荐测试
- 推荐架构
- 推荐 Git 操作
- 找相似案例
- 预测某个方案可能失败
- 对当前 Change Plan 给第二意见

**Shadow Agent 权限边界（硬锁）**：
```
WRITE      = DENY
COMMIT     = DENY
MERGE      = DENY
DEPLOY     = DENY
EXEC       = DENY
```

Shadow Agent 永远只观察、预测、建议，不执行任何修改操作。

---

## 3. Learning Layer 架构

```
DCC
│
├── Snapshot（已完成 V0.4.0）
├── Remote HEAD Lock（已完成 V0.4.0）
├── Change Plan（已完成 V0.4.0）
├── Evidence（P1 契约完成，P2 实现 Bundle）
├── Security Gate（P3 待实现）
│
└── Learning Layer（P4 定义契约，P5-P6 实现）
     │
     ├── Case Library（案例库）
     ├── Experience Database（经验数据库）
     ├── Failure Database（失败数据库）
     ├── Architecture Patterns（架构模式库）
     ├── Functional Patterns（功能模式库）
     ├── External Research Cases（外部研究案例）
     ├── Outcome Evaluator（结果评估器）
     ├── Similarity Retrieval（相似度检索）
     ├── Shadow Agent（影子代理）
     └── Learning Audit（学习审计）
```

### 3.1 核心模块说明

| 模块 | 职责 | 优先级 |
|---|---|---|
| **Case Library** | 记录外部案例（GitHub 优秀项目、Agent 案例、架构案例等） | 高 |
| **Experience Database** | 记录自己的真实开发经验（任务→方案→结果→原因→修正→最终结果） | 最高 |
| **Failure Database** | 专门记录失败案例。AI 如果只学习"成功案例"，很容易重复错误 | 最高 |
| **Architecture Patterns** | 架构模式库（双仓库、Submodule、Monorepo、微服务等） | 中 |
| **Functional Patterns** | 功能模式库（Snapshot、Change Plan、Evidence、Security Gate 等） | 中 |
| **External Research Cases** | 外部研究案例（SWE-agent、OpenHands 等的可复用设计） | 中 |
| **Outcome Evaluator** | 判断预测 vs 实际，计算 Shadow Agent 的预测准确率 | 高 |
| **Similarity Retrieval** | 相似度检索（新任务 vs 历史任务，找到最相似的经验） | 高 |
| **Shadow Agent** | 只观察、不改变生产。独立分析、预测、给第二意见 | 高 |
| **Learning Audit** | 记录：这个经验从哪里来？为什么被采纳？是否经过实际验证？有没有被人工修正？现在可信度是多少？ | 最高 |

### 3.2 Failure Database 的特殊地位

Failure Database 专门记录失败案例，这是 Learning Layer 中最重要的模块之一。

**为什么需要专门的失败数据库**：
- AI 如果只学习"成功案例"，很容易重复错误
- 失败案例包含了"什么方案在什么情况下会失败"的关键信息
- 遇到新任务时，应该优先检索 Failure Database，避免重蹈覆辙

**失败案例记录内容**：
- 任务描述
- 采用的方案
- 失败的具体表现（测试失败、安全扫描命中、远程冲突、权限漂移等）
- 失败原因分析
- 修正方案
- 修正后的结果
- 关联的 Evidence ID
- 可信度评分

---

## 4. Evidence → Experience 转化规范

P1 定义的 Evidence Schema 目前主要用于审计。Learning Layer 增加一个完全独立的 **Experience Extractor**，把 Evidence 链转化为可学习的经验数据。

### 4.1 转化链路

```
Evidence（P1 Schema）
   ↓ Experience Extractor
Case
   ↓
Outcome
   ↓
Evaluation
   ↓
Learning Record
```

### 4.2 Learning Record 数据模型

```json
{
  "caseId": "CASE-000182",
  "taskType": "submodule-sync",
  "taskDescription": "同步 DCC 新版本到 Core submodule",
  "baseline": "ZB-PROD-2026-08-31-04",
  "dccVersion": "0.4.0",
  "coreVersion": "5.9.9",
  "strategy": "merge",
  "alternativeStrategy": "rebase",
  "expectedOutcome": "PASS",
  "actualOutcome": "PASS",
  "failureAvoided": "submodule SHA invalidation",
  "failureReason": null,
  "correctionApplied": null,
  "evidenceRefs": [
    "EVID-001",
    "EVID-002",
    "EVID-003"
  ],
  "confidence": 0.91,
  "verifiedBy": "actual-github-verification",
  "humanCorrection": null,
  "createdAt": "2026-08-31T08:30:00.000Z",
  "lastUpdated": "2026-08-31T09:00:00.000Z",
  "learningAudit": {
    "source": "evidence-extractor",
    "adoptionReason": "actual test passed + github second verification passed",
    "actualVerified": true,
    "humanCorrected": false,
    "currentConfidence": 0.91
  }
}
```

### 4.3 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| caseId | string | 案例唯一标识，格式 CASE-XXXXXX |
| taskType | string | 任务类型分类（submodule-sync, baseline-sync, feature-implementation, security-fix 等） |
| taskDescription | string | 任务描述 |
| baseline | string | 执行时的 Baseline ID |
| dccVersion | string | 执行时的 DCC 版本 |
| coreVersion | string | 执行时的 Core 版本 |
| strategy | string | 采用的方案 |
| alternativeStrategy | string | 备选方案（如果有） |
| expectedOutcome | string | 预期结果（PASS/FAIL/BLOCKED/NOT_VERIFIED） |
| actualOutcome | string | 实际结果（必须来自实际 Evidence，不得用预期值填充） |
| failureAvoided | string | 避免了什么失败（如果成功） |
| failureReason | string | 失败原因（如果失败） |
| correctionApplied | string | 应用了什么修正方案（如果从失败修正到成功） |
| evidenceRefs | array | 关联的 Evidence ID 列表（至少 1 个） |
| confidence | float | 可信度评分 0.0-1.0 |
| verifiedBy | string | 验证方式（actual-github-verification, test-only, manual-review 等） |
| humanCorrection | string | 人工修正记录（如果有） |
| createdAt | string | 创建时间（ISO 8601） |
| lastUpdated | string | 最后更新时间（ISO 8601） |
| learningAudit | object | 学习审计信息（来源、采纳原因、是否验证、是否人工修正、当前可信度） |

### 4.4 可信度评分规则

| 条件 | 可信度 |
|---|---|
| 实际 GitHub 验证通过 + 测试通过 + 安全扫描通过 | 0.9-1.0 |
| 测试通过 + 安全扫描通过，但未做 GitHub 二次核验 | 0.7-0.89 |
| 仅测试通过，未做安全扫描或 GitHub 核验 | 0.5-0.69 |
| 人工审核通过，但未实际执行 | 0.3-0.49 |
| 仅 AI 推测，未实际验证 | 0.0-0.29 |
| 经过人工修正后成功 | 在基础分上 +0.1（上限 1.0） |
| 重复验证 3 次以上均成功 | 在基础分上 +0.05（上限 1.0） |
| Baseline 升级后未重新验证 | 可信度衰减 50% |

---

## 5. Shadow Agent 设计

### 5.1 定位

Shadow Agent 是一个**只观察、不执行**的 AI 代理。它在正式流程旁边独立运行，对当前任务进行分析、预测、给第二意见，但永远不拥有任何写权限。

### 5.2 能力

Shadow Agent 可以：
1. **预测应该怎么改**：基于历史经验和当前上下文，预测最优修改方案
2. **判断风险**：预测当前方案可能遇到的风险（远程冲突、权限漂移、安全漏洞、回归失败）
3. **推荐测试**：推荐应该运行哪些测试来验证修改
4. **推荐架构**：推荐架构方案（双仓库、Submodule、Monorepo 等）
5. **推荐 Git 操作**：推荐 merge vs rebase、commit message 格式、push 时机
6. **找相似案例**：从 Case Library / Experience Database / Failure Database 中检索最相似的历史案例
7. **预测某个方案可能失败**：基于 Failure Database，预测当前方案在什么情况下可能失败
8. **对当前 Change Plan 给第二意见**：审核 Change Plan 的范围、允许操作、禁止操作、预期测试是否合理

### 5.3 权限边界（硬锁，不可扩大）

```
READ       = ALLOW    （可以读取仓库状态、Evidence、历史经验）
TASK       = ALLOW    （可以生成分析任务）
AUDIT      = ALLOW    （可以审计正式流程的结果）
TEST       = CONTROLLED（可以推荐测试，但不自动执行）
WRITE      = DENY     （不得修改任何文件）
COMMIT     = DENY     （不得执行 git commit）
MERGE      = DENY     （不得执行 git merge）
DEPLOY     = DENY     （不得执行任何部署）
SHELL EXEC = DENY     （不得执行任何 shell 命令）
CODE EXEC  = DENY     （不得执行任何代码）
```

### 5.4 工作流

```
1. 正式流程开始（Change Plan 创建）
      ↓
2. Shadow Agent 接收任务上下文
   - 当前 Change Plan
   - Repository Snapshot
   - Remote HEAD Lock
   - 历史相似案例
      ↓
3. Shadow Agent 独立分析
   - 预测修改方案
   - 预测风险
   - 推荐测试
   - 给第二意见
      ↓
4. Shadow Agent 输出 Shadow Result（不执行任何修改）
      ↓
5. 正式流程执行，产生 Actual Result
      ↓
6. Outcome Evaluator 对比 Shadow Result vs Actual Result
   - 预测准确？
   - 风险预测命中？
   - 测试推荐有效？
      ↓
7. 记录对比结果到 Experience Database
   - Shadow Agent 预测准确率更新
   - 成功/失败案例入库
      ↓
8. 更新 Shadow Agent 的经验权重
   - 预测准确的方案权重提升
   - 预测失败的方案权重降低
```

### 5.5 Shadow Agent 输出格式

```json
{
  "shadowId": "SHADOW-20260831-001",
  "taskId": "TASK-V041-P1-20260831-001",
  "baseline": "ZB-PROD-2026-08-31-04",
  "timestamp": "2026-08-31T08:30:00.000Z",
  "predictedStrategy": "merge",
  "predictedRisk": [
    "remote HEAD may change during execution",
    "Core auto-watch may update pinned SHA"
  ],
  "recommendedTests": [
    "git diff --check",
    "security scan for credentials",
    "verify only allowed files modified"
  ],
  "similarCases": [
    "CASE-000150",
    "CASE-000165"
  ],
  "failurePrediction": "low",
  "secondOpinion": "Change Plan scope is appropriate. Recommend adding remote HEAD re-verification before push.",
  "confidence": 0.85,
  "permissionBoundary": {
    "write": "DENY",
    "commit": "DENY",
    "merge": "DENY",
    "deploy": "DENY",
    "exec": "DENY"
  }
}
```

---

## 6. 核心硬规则

### 6.1 Learning is advisory, never authoritative

**学习层只能提供建议，不能成为事实来源。**

正确流程：
```
Learning
   ↓
Recommendation
   ↓
Change Plan
   ↓
Security Gate
   ↓
Human/Policy Approval
   ↓
Execution
```

禁止流程：
```
Learning
   ↓
自动修改 Core
```

否则辛苦建立的 Baseline / Evidence / Security Gate 会被绕过。

**事实仍然是**：
- GitHub 实际状态
- 实际测试
- 实际扫描
- 实际 Evidence

这与"事实 > 聊天记录 > AI 推测"的优先级完全一致。

### 6.2 学习数据库不能反向修改生产规则

- Learning Record 不得自动修改 config.js / security.js 的权限配置
- Learning Record 不得自动更新 Core pinned SHA
- Learning Record 不得自动修改 Baseline ID
- Learning Record 不得自动删除历史 Evidence
- 任何基于 Learning 的建议必须经过 Change Plan + Security Gate + Human/Policy Approval 才能执行

### 6.3 Shadow Agent 永远无写权限

Shadow Agent 的 WRITE/COMMIT/MERGE/DEPLOY/EXEC 永远为 DENY，不得因为预测准确率高而扩大。

### 6.4 经验必须绑定 Evidence

每个 Learning Record 必须引用至少 1 个 Evidence ID。没有 Evidence 支撑的经验不得入库，可信度标记为 0.0。

### 6.5 失败案例优先检索

遇到新任务时，Similarity Retrieval 必须优先检索 Failure Database，避免重复已知错误。

### 6.6 Baseline 升级后经验可信度衰减

Baseline ID 升级后，旧 Baseline 下的 Learning Record 可信度衰减 50%，需要在新 Baseline 下重新验证才能恢复可信度。

---

## 7. Learning Audit（学习审计）

每个 Learning Record 必须包含 learningAudit 字段，记录：

| 审计项 | 说明 |
|---|---|
| source | 经验来源（evidence-extractor, manual-input, external-research, shadow-evaluation） |
| adoptionReason | 为什么被采纳（实际测试通过、GitHub 验证通过、人工审核通过等） |
| actualVerified | 是否经过实际验证（true/false） |
| humanCorrected | 是否经过人工修正（true/false） |
| currentConfidence | 当前可信度（0.0-1.0） |
| lastVerifiedBaseline | 最后一次验证时的 Baseline ID |
| verificationCount | 重复验证次数 |

**Learning Audit 的目的**：确保每个经验都可追溯、可评估、可修正。不允许"黑箱经验"——不知道从哪里来、为什么被采纳、是否经过验证的经验不得使用。

---

## 8. 与现有模块的关系

| 现有模块 | 与 Learning Layer 的关系 |
|---|---|
| Snapshot | 提供任务开始时的仓库状态，作为 Learning Record 的环境上下文 |
| Remote HEAD Lock | 提供预期 HEAD，作为 Learning Record 的 expectedState |
| Change Plan | 提供任务范围、允许/禁止操作，作为 Learning Record 的任务描述 |
| Evidence（P1 Schema） | Learning Record 的数据来源，每个 Learning Record 必须引用 Evidence ID |
| Evidence Bundle（P2） | 提供结构化的证据包，Experience Extractor 从中提取经验 |
| Security Gate（P3） | Learning 建议必须经过 Security Gate 才能执行；Security Gate 的扫描结果也作为 Learning Record 的输入 |
| Release Candidate（P7） | RC 的测试/安全/审计结果作为高质量 Learning Record 来源 |
| Core Compatibility（P8） | Core 兼容性检查结果作为 Learning Record 的输入，特别是失败案例 |

---

## 9. 外部参考与 DCC 差异

### 9.1 SWE-agent

**核心思路**：让模型通过 Agent-Computer Interface 操作真实 GitHub repository，并通过真实任务结果评价 Agent 能力。强调可复现、可评估的 Agent-Computer Interface。

**DCC 的吸收**：
- Evidence Schema 提供可评估、可复现的数据基础
- Shadow Agent 的预测-实际对比机制类似 SWE-agent 的任务结果评价
- Experience Database 类似 SWE-agent 的任务-结果积累

**DCC 的差异**：
- SWE-agent 专注于单仓库任务解决，DCC 是双仓库治理（Core 生产 + DCC 研发）
- SWE-agent 的 Agent 可以直接操作仓库，DCC 的 Shadow Agent 永远无写权限
- DCC 有完整的 Baseline / Evidence / Security Gate 治理内核，SWE-agent 没有

### 9.2 OpenHands

**核心思路**：AI-driven development 平台，SDK、CLI、Agent 等模块化设计。

**DCC 的吸收**：
- 模块化设计（Snapshot / Change Plan / Evidence / Security Gate / Learning 各自独立）
- Agent 能力可以逐步扩展

**DCC 的差异**：
- OpenHands 是通用开发平台，DCC 是带有治理内核的研发控制平面
- OpenHands 的 Agent 可以直接写代码，DCC 的正式修改必须经过 Change Plan + Security Gate + Approval
- DCC 有双仓库解耦架构，OpenHands 是单仓库模型

---

## 10. P4-P6 阶段规划

### P4 — Learning Database Contract（契约定义，不写代码）

**目标**：定义 Learning 层的数据契约。

**产出**：
- docs/V044-LEARNING-CONTRACT.md
- Case 数据模型精确定义
- Experience 数据模型精确定义
- Failure 数据模型精确定义
- 可信度评分规则精确化
- 去重规则
- 版本绑定规则
- Evidence 引用规则
- Shadow Agent 权限边界精确化

**硬约束**：P4 之前不允许真正写学习代码。

### P5 — Case / Experience Engine（实现）

**目标**：实现案例检索、经验提取、相似度匹配引擎。

**产出**：
- server/case-engine.js
- server/experience-extractor.js
- server/similarity.js
- tests/（对应测试）
- 从 Evidence Bundle 自动提取 Learning Record
- Failure Database 优先检索
- 经验可信度衰减机制

### P6 — Shadow Learning（实现）

**目标**：实现 Shadow Agent，在正式流程旁边独立分析、预测、给第二意见。

**产出**：
- server/shadow-agent.js
- server/outcome-evaluator.js
- tests/shadow-agent.test.js
- Shadow Agent 预测-实际对比机制
- Shadow Agent 预测准确率跟踪
- Shadow Agent 经验权重更新

---

## 11. 禁止事项

1. **禁止** Learning 层自动修改 Core 任何文件
2. **禁止** Learning 层自动更新 Core pinned SHA
3. **禁止** Learning 层自动修改 config.js / security.js 权限配置
4. **禁止** Learning 层自动修改 Baseline ID
5. **禁止** Learning 层自动删除历史 Evidence
6. **禁止** Shadow Agent 拥有 WRITE/COMMIT/MERGE/DEPLOY/EXEC 权限
7. **禁止** 没有 Evidence 支撑的经验入库
8. **禁止** 把 AI 推测标记为实际验证
9. **禁止** 用 Learning 建议绕过 Change Plan + Security Gate + Approval 流程
10. **禁止** 在 P4 之前写学习代码（只允许定义架构基线和契约文档）
11. **禁止** 把 DCC 做成 OpenHands / SWE-agent 的简单复制品（必须保留治理内核）
12. **禁止** 虚构 Learning Record（每个 Learning Record 必须有真实 Evidence 引用）

---

## 12. 当前状态

| 项目 | 状态 |
|---|---|
| 本文档状态 | ARCHITECTURE BASELINE（架构基线已建立） |
| P4 Learning Contract | 待启动（需重新建立 Baseline 并获得授权） |
| P5 Case/Experience Engine | 规划中 |
| P6 Shadow Learning | 规划中 |
| Evidence Schema（P1） | ✅ 已完成，是 Learning 数据的基础 |
| Evidence Bundle（P2） | ⏳ 待启动，提供经验数据来源 |
| Security Gate（P3） | ⏳ 待启动，Learning 建议必须经过 Security Gate |

---

**本文档为 Learning & Shadow Layer 的架构基线。P4 之前不允许写学习代码，只允许基于本文档定义精确的数据契约。任何 Learning 建议必须经过 Change Plan + Security Gate + Human/Policy Approval 才能执行。Learning is advisory, never authoritative.**
