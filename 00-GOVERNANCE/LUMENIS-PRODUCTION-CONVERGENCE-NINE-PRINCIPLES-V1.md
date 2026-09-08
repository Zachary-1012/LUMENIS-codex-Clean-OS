# LUMENIS Production Convergence Nine Principles V1

> 中文：**序境 · 生产收敛九项准则**
>
> 定位：用于指导历史资产回收、功能归位、数据导入、新 Production Line 映射、UI/UX 重构、AI Learning、Runtime 验证与 Production Acceptance 的固定工程边界。
>
> 原则：**恢复能力，不复活旧产品；当前源码与 Production Truth 永远优先于历史资产。**

---

## 1. 资产回收不是旧产品复活

Heritage Intelligence 的目的，是找回历史研发中仍有价值的：

- 业务能力定义
- Research / Platform Intelligence
- Contract / Schema / Taxonomy
- Metric / Table / Data Presentation
- Evidence
- Decision Memory
- Regression Memory
- Domain Methodology
- AI / Agent / Learning 设计
- UI/UX 设计知识

历史资产不能因为被找到就直接恢复到 Production Runtime。

正确链路：

```text
Historical Asset
→ Source Trace
→ Current Equivalent Audit
→ Semantic Dedup
→ Current Production Line Mapping
→ Capability Promotion
→ Implementation
→ Test
→ Evidence
→ Regression
```

**Do Not Regress：历史能力可以恢复，旧产品结构和旧运行链不能自动复活。**

---

## 2. 当前新 Production Line 是唯一生产承载基线

所有恢复、迁移、重构和新增能力统一映射到：

```text
External Data
→ Evidence
→ Canonical Data
→ Function
→ Metric
→ Truth Table
→ View Model
→ Dynamic Visualization
→ UI / Report / Export
```

业务决策链统一为：

```text
Source
→ Evidence
→ Event
→ Case
→ Finding / Insight
→ Decision
→ Action
→ Outcome
→ Evaluation / Feedback
→ Learning Asset
```

历史功能不能以旧 Production Line、旧 ViewModel、旧页面组合或旧数据入口直接重新接回生产。

---

## 3. 功能缺失优先执行 Historical Capability Recovery Audit

任何发现的功能缺口，不应立即从零开发。

必须先执行：

```text
Capability Gap
→ Heritage Retrieval
→ Historical Implementation / Contract / Evidence Review
→ Current Equivalent Verification
→ Gap Classification
```

分类至少包括：

```text
ALREADY_EXISTS
PARTIALLY_EXISTS
MISSING
SUPERSEDED
NEEDS_REIMPLEMENTATION
PROMOTION_CANDIDATE
```

只有在确认历史能力无法直接映射或当前不存在等价能力后，才进入重新研发。

目标是：**优先找回已经研发过、验证过、纠偏过的能力，避免重复发明。**

---

## 4. 功能恢复、数据导入、新生产线映射、UI承载必须视为同一闭环

不得把以下四项割裂执行：

1. Capability Recovery
2. Data Import / Migration
3. Current Production Line Mapping
4. UI / UX Rebinding

统一恢复流程：

```text
Recovered Capability
→ Data / Schema / Contract Verification
→ Canonical Mapping
→ Function / Metric / Truth Table
→ View Model
→ Current UI / UX
→ Runtime
→ Test
→ Evidence
```

因此：

- 功能找回来但数据链未接通，不算完成；
- 数据导入成功但没有进入 Canonical / Truth Chain，不算完成；
- UI 显示出来但没有真实 API / View Model / Evidence，不算完成；
- 页面能打开但 Runtime 未验证，不算完成。

---

## 5. 旧设计架构与当前 Production Runtime 必须硬隔离

历史设计资产允许作为 Design Intelligence 使用，但以下 Legacy 资产不得成为当前 Runtime 默认来源：

- Legacy IA
- Legacy Template
- Legacy ViewModel
- Legacy Route Composition
- Legacy Static Bundle
- Legacy Page Composition
- Legacy Data Binding
- Legacy Navigation Architecture
- Legacy Frontend State Contract

任何历史 UI / UX 恢复，必须先抽取：

- 有效交互原则
- 信息层级
- 表格/趋势/下钻模式
- 动效模式
- Responsive 模式
- 已验证的业务呈现逻辑

再映射到当前 UI/UX 与 Production Line。

**恢复设计知识，不恢复旧设计架构。**

---

## 6. AI 持续学习必须保留，但 Learning Memory 与 Production Truth 严格隔离

目标学习闭环：

```text
Interaction
→ Evidence
→ Feedback
→ Evaluation
→ Learning Record
→ Memory / Knowledge
→ Retrieval
→ Next Task
→ Evaluation
→ New Learning
```

AI 可以持续学习：

- 用户纠偏
- 内容创作偏好
- 平台研究
- 中/英/韩语境
- 历史研究
- Product Q&A
- Evaluation 结果
- 任务执行结果
- 失败模式

但 AI Learning 不能直接修改：

- Production Database Facts
- Canonical Data
- Evidence
- Deterministic Business Rules
- Permission
- Security Boundary
- Production Truth

规则：

**Learning Memory ≠ Production Truth。**

AI Learning 的 ACTIVE 状态必须由真实 Runtime、跨会话 Retrieval、Evaluation 与 Evidence 证明。

---

## 7. Heritage 必须持续维护 Coverage 与 Pending Ledger

Heritage 建库完成不代表历史资产已经全部迁移。

所有可发现资产必须进入可追踪状态，不允许“未确认即视为已完成”。

状态至少使用：

```text
DISCOVERED
INDEXED
VERIFIED
DEDUPED
PROMOTED
REFERENCE_ONLY
SUPERSEDED
ARCHIVED
REJECTED_WITH_REASON
```

必须长期维护：

- Asset Coverage
- Pending Verification Ledger
- Missing Source Ledger
- Current Equivalent Status
- Promotion Candidates
- Duplicate / Semantic Duplicate Status

Coverage 必须基于真实 Inventory 计算，禁止凭感觉给出百分比。

---

## 8. 上线只认真实 Production Acceptance，不认“看起来已经完成”

以下任何单项都不能独立证明能力完成：

- 文件存在
- 页面可打开
- API 可返回
- 单测通过
- 文档写成完成
- 历史版本曾经运行

能力完成必须至少具备：

```text
Source
+ Call Graph
+ Data / API
+ Frontend / Consumer
+ Runtime
+ Tests
+ Production Evidence
```

Production 上线前至少满足：

```text
P0 = 0
Core Tests = PASS
Critical E2E = PASS
Production Truth Chain = VERIFIED
Data Migration = VERIFIED
Runtime = VERIFIED
Security Boundary = VERIFIED
Release Lineage = VERIFIED
Rollback = VERIFIED
No Fake Production State
```

统一状态：

```text
PLANNED
IMPLEMENTED
TESTED
VERIFIED
RELEASED
OPERATING
```

禁止为了赶上线把 IMPLEMENTED / TESTED 写成 VERIFIED。

---

## 9. 当前源码、当前 Contract、当前 Evidence 永远优先于历史资产

每次 Codex / Agent 执行涉及历史能力时，必须遵守：

```text
Current Source
+ Current Contract
+ Current Runtime
+ Current Tests
+ Current Evidence
        ↓
Current Production Truth
```

Heritage 的作用是提供：

- 历史研究
- 设计知识
- 业务方法
- Contract 来源
- 用户纠偏
- 失败经验
- Regression Memory
- Capability Recovery 线索

当历史资产与当前真实实现冲突时：

1. 不得自动覆盖当前实现；
2. 必须进行 Current Equivalent Verification；
3. 判断是否发生知识退化；
4. 必要时形成 Promotion Candidate；
5. 通过重新实现、测试、Evidence 与 Regression 后才允许进入 Production。

正确公式：

```text
Historical Knowledge
+ Current Source
+ Current Requirement
+ New Research
→ Current Best Architecture
→ Implementation
→ Verification
```

---

# Canonical Execution Order

当前序境生产收敛的统一执行顺序：

```text
Whole-System Audit
→ Heritage Recovery
→ Capability Reconciliation
→ Data / Schema Reconciliation
→ Legacy Architecture Isolation
→ Current Production Line Mapping
→ UI / UX Rebinding
→ Runtime Integration
→ Optimization
→ Test / E2E / Security / Evidence
→ Release Lineage
→ Production Acceptance
```

---

# One-Line Rule

> **找回过去积累的能力与知识，但只允许它们通过当前 Production Truth、当前架构和真实验证重新进入序境。**

状态：`CANONICAL GOVERNANCE PRINCIPLE / ACTIVE FOR CONVERGENCE`
