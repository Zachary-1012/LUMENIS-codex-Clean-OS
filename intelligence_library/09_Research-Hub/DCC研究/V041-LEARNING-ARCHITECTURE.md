# DCC V0.4.1 P2 — Learning Store 架构文档

**Baseline ID**: ZB-PROD-2026-08-31-04
**Phase**: P2 — Learning Store Implementation
**Module**: server/learning-store.js
**Status**: IMPLEMENTED
**Core Principle**: Learning is advisory, never authoritative

---

## 1. 模块定位

Learning Store 是 DCC 的长期学习基础设施，负责存储和管理经过事实验证的软件工程经验数据。

它不是训练 AI 的平台，而是持续产生高质量、可验证、可追溯软件工程经验数据的系统。

**三层学习模型**:
```
第一层: 知识学习 (Case Library / External Research)
第二层: 经验学习 (Experience Database / Failure Database / Pattern Extraction)
第三层: 影子学习 (Shadow Learning / 独立模块 server/shadow-learning.js)
```

---

## 2. 核心数据结构

### 2.1 Case（案例）

Case 是学习的基本单元，记录一次完整的开发经历。

| 字段 | 说明 |
|---|---|
| caseId | 唯一标识 |
| caseType | 案例类型（SUBMODULE_SYNC, TEST_FAILURE, SECURITY_BLOCK 等） |
| source | 来源（DCC_ACTUAL / CORE_ACTUAL / EXTERNAL_PUBLIC / AI_ASSISTED） |
| sourceType | INTERNAL / EXTERNAL / AI_ASSISTED |
| generatedByAI | 是否由 AI 生成 |
| repository / baselineId / commitSha | 版本锚点 |
| initialState / change | 变更前后状态 |
| expectedOutcome / observedOutcome | 预期 vs 实际（硬约束：不得混写） |
| result / decision | 结果与决策 |
| failureReason / resolution / lesson | 失败原因、解决方案、经验教训 |
| observations / decisions / outcomes / feedback | 子记录 |

### 2.2 Failure Database（失败数据库）

专门记录失败案例，避免 AI 只学习成功案例而重复错误。

支持的 Failure 类型：
- REMOTE_HEAD_CHANGED
- PUSH_REJECTED
- MERGE_CONFLICT
- TEST_FAILURE
- SECURITY_BLOCK
- CREDENTIAL_DETECTION
- PERMISSION_DRIFT
- UNEXPECTED_FILE_CHANGE
- BASELINE_DRIFT
- DEPLOYMENT_FAILURE
- ROLLBACK
- NOT_VERIFIED

### 2.3 Pattern（模式）

从 Case 中提取的可复用模式，包含：
- triggerConditions（触发条件）
- recommendedAction（推荐操作）
- confidence（置信度 0-1）
- failureAvoided（避免的失败）

### 2.4 Lesson（经验教训）

从 Case 中提取的经验教训，关联 sourceCaseId 和 confidence。

---

## 3. 来源优先级

案例来源按可信度排序（数字越小优先级越高）：

| 优先级 | 来源 | 说明 |
|---|---|---|
| 1 | DCC_ACTUAL | DCC 仓库实际发生 |
| 2 | CORE_ACTUAL | Core 仓库实际发生 |
| 3 | DUAL_REPO_SYNC | 双仓库同步事件 |
| 4 | TEST_FAILURE | 测试失败 |
| 5 | SECURITY_BLOCK | 安全阻断 |
| 6 | REMOTE_HEAD_CHANGED | 远程 HEAD 变化 |
| 7 | RELEASE_ROLLBACK | 发布/回滚 |
| 8 | EXTERNAL_PUBLIC | 外部公开案例 |
| 9 | AI_ASSISTED | AI 辅助生成 |

**硬规则**: AI 生成内容必须标记 `generatedByAI=true, sourceType=AI_ASSISTED`，只能作为 ASSISTED_ANALYSIS，不能作为 OBSERVED_FACT。

---

## 4. 核心功能

### 4.1 Case 管理

- `createCase(options)` — 创建 Case（自动加入 Failure Database 和 Lesson Database）
- `getCase(caseId)` — 获取单个 Case
- `listCases(options)` — 列出 Case（按来源优先级排序，支持过滤）
- `addObservation / addDecision / addOutcome / addFeedback / addRelationship` — 添加子记录

### 4.2 模式提取

- `extractPattern(caseId)` — 从 Case 提取 Pattern
- `getPatterns(options)` — 获取所有 Pattern（按 confidence 排序）

### 4.3 经验与失败

- `getLessons(options)` — 获取所有 Lesson
- `getFailures(options)` — 获取 Failure Database（支持按 failureType 过滤）

### 4.4 相似度检索

- `querySimilarCases(query)` — 按 caseType/repository/baselineId/keywords/failureReason 检索相似 Case
- **硬规则**: 只有实际匹配才返回结果，来源优先级仅作为排序加分不单独产生匹配

### 4.5 Regression Memory

- `regressionCheck(changePlan)` — 检查新变更是否可能触发已知失败模式
- 检查目标文件与失败原因的关联（同时检查完整路径和 basename）
- 检查操作类型与历史失败的关联
- 返回 NONE / LOW / MEDIUM / HIGH 风险等级

### 4.6 AI Provider 接口预留

- `AI_PROVIDER.configure(config)` — 配置 AI Provider（不存储 Token/Secret）
- `AI_PROVIDER.assistedAnalysis(input)` — AI 辅助分析（当前返回 NOT_CONFIGURED）
- `AI_PROVIDER.getStatus()` — 获取配置状态

**硬约束**:
- 第一阶段不绑定具体 AI 模型
- AI 输出只能作为 ASSISTED_ANALYSIS，不能作为 OBSERVED_FACT
- 不存储 Token/Secret/Credential

---

## 5. API 端点

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/api/learning/cases` | 列出 Case |
| POST | `/api/learning/cases` | 创建 Case |
| GET | `/api/learning/cases/:id` | 获取单个 Case |
| GET | `/api/learning/patterns` | 获取 Pattern 列表 |
| GET | `/api/learning/lessons` | 获取 Lesson 列表 |

---

## 6. 安全边界

- 仅内存存储，不写入文件系统
- 不执行 git 命令
- 不修改任何仓库状态
- 不改变权限边界
- 不存储 Token/Secret/Credential
- AI 输出标记为 ASSISTED_ANALYSIS，不作为事实来源
- Learning is advisory, never authoritative

---

## 7. 测试覆盖

测试文件: `tests/learning-store.test.js`

覆盖范围：
- createCase（正常/异常/AI 标记/外部标记/自动入库）
- getCase / listCases（过滤/排序）
- addObservation / addDecision / addOutcome / addFeedback
- extractPattern / getPatterns
- getLessons / getFailures
- querySimilarCases（匹配/无匹配/关键词）
- regressionCheck（无风险/有风险/文件匹配）
- AI_PROVIDER（未配置/配置/输出标记）
- 常量导出验证

---

## 8. 与 Evidence Bundle 的关系

```
Evidence Bundle (evidence-bundle.js)
    │
    │ 收集任务相关 Evidence
    ↓
Experience Extractor (后续 P4 实现)
    │
    │ 从 Evidence 中提取经验
    ↓
Learning Store (learning-store.js)
    │
    ├── Case Library
    ├── Experience Database
    ├── Failure Database
    ├── Pattern Extraction
    ├── Regression Memory
    └── AI Provider (预留)
```

当前 P2 阶段，Evidence Bundle 和 Learning Store 是独立模块，通过 API 或外部逻辑关联。后续 P4 将实现自动的 Experience Extractor。

---

## 9. 已知限制

1. 内存存储，Server 重启后数据丢失
2. 相似度检索基于关键词匹配，不支持语义相似度（后续可扩展 Vector Store）
3. AI Provider 仅预留接口，不实际调用模型
4. 不支持 Case 之间的自动关联（需手动 addRelationship）
5. Pattern 提取基于规则，不使用 ML 算法

---

## 10. 后续阶段

- **P3 Security Gate**: 基于 Learning Store 的 Failure Database 实现自动化安全门禁
- **P4 Learning Database Contract**: 定义持久化存储契约（FileStore / SQLiteStore / FutureVectorStore）
- **P5 Case / Experience Engine**: 实现自动的 Experience Extractor 和 Case 管理
- **P6 Shadow Learning**: 基于 Learning Store 实现 Shadow Agent（当前已在 P2 实现基础版本）
