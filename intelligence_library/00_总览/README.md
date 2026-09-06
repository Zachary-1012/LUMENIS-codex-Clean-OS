# Zachary OS AI

> **共享智能成长层 / Shared Intelligence Growth Layer**
> **Repository：Zachary-OS-AI**

## 1. 产品角色

Zachary OS AI 当前定位为**共享智能成长层与能力层**，不是序境的生产核心，也不是 Global Growth Intelligence 的子模块。

当前阶段不提前实体化为第三个独立商业产品，不锁定额外品牌命名。

它负责沉淀和成长：

```text
AI Model / Gateway
Agent
Research
Evidence
Memory
Skill
Evaluation
Learning
Planning
Reasoning
Trace
```

## 2. 三仓关系

```text
                  Zachary OS AI
             共享智能成长层 / 能力层
                         ▲
              Contract / Artifact
                         │
          ┌──────────────┴──────────────┐
          │                             │
        序境                  Global Growth Intelligence
      独立产品①                     独立产品②
          │                             │
   Production Truth             Research / Growth Truth
```

硬边界：

1. OSAI 不拥有序境 Production Truth。
2. OSAI 不拥有 Global Growth Intelligence 的产品真相。
3. OSAI 不直接修改两个产品的生产数据库。
4. OSAI 不成为两个产品的启动、采集、分析、报告或核心业务依赖。
5. 两个产品不可因为共享智能而合并。
6. 共享只允许通过明确、版本化、可追溯的 Contract / Artifact 完成。

## 3. 共享智能成长闭环

```text
真实任务
→ Evidence / Result
→ Evaluation
→ Human Feedback
→ Contribution
→ Validation
→ Generalization
→ Admission
→ Learning Asset
→ Skill / Memory / Capability
→ 下一次任务
```

共享智能输入必须经过验证、评价与准入；未经验证的产品数据、AI 输出或研究结论不得直接成为共享能力资产。

## 4. Contribution Lifecycle

统一贡献生命周期：

```text
CANDIDATE
→ VALIDATED
→ GENERALIZABLE
→ ADMITTED
```

只有 `ADMITTED` 的贡献才能进入共享学习资产。

OSAI 接收的是可验证、可追溯、可复用的智能资产，不是产品业务数据库副本。

## 5. 非阻塞原则

OSAI 必须遵循：

```text
OSAI 可用      → 产品可使用共享智能
OSAI 不可用    → 产品继续正常运行
贡献失败       → 产品继续正常运行
贡献被拒绝     → 产品继续正常运行
共享能力升级   → 产品继续正常运行
```

共享智能属于增强层，不属于生产关键路径。

## 6. Intelligence → Production Gate

```text
Research
→ Evidence
→ Contract
→ Implementation Specification
→ Production Implementation
→ Test
→ Verify
→ Release
```

禁止：

```text
AI / Agent
    ↓
直接修改
    ↓
Production Truth
```

涉及生产写入必须经过正式 Permission / Contract / Release Gate，并由生产产品自身完成最终控制。

## 7. Engineering Loop

```text
READ → AUDIT → ANALYZE → PLAN → PATCH PREVIEW
→ TEST → VERIFY → HUMAN APPROVAL → COMMIT → PUSH
```

禁止无限循环、绕过权限、未经批准自动 Merge / Push 或以 AI 输出替代工程证据。

## 8. Runtime / Test 收口状态

**2026-09-05：三仓 Runtime & Test Audit 已完成并收口，相关报告已推送仓库正式留档。**

当前 README 仅记录已经收口的三仓关系与后续研发边界，不重新开启本轮架构收口。

后续只有真实 Bug、安全问题或明确产品需求，才重新打开相关范围。

## 9. 当前研发方向

OSAI 后续研发重点为共享智能能力本身：

- Skill
- Evaluation
- Learning
- Memory
- Evidence
- Agent
- Reasoning
- Trace
- Capability Registry

重点是让能力**可验证、可复用、可追溯、可安全贡献**，而不是把 OSAI 做成两个产品的运行时中间件。

## 10. 状态声明

**Role：Shared Intelligence Growth Layer**

**Runtime Dependency of 序境：None**

**Runtime Dependency of Global Growth Intelligence：None**

**Production Truth Owner：Neither**

**Current Status：Active · Non-Blocking · Architecture Closeout Complete**

后续两个产品继续独立研发、测试、上线与商业化；OSAI 按共享智能能力层持续成长，不阻塞产品研发节奏。
