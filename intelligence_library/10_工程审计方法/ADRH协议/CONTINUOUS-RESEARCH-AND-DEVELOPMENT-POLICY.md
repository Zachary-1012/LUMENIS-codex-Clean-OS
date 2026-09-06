# Continuous Research & Development Policy

> **永久研发规则：每次 Material Change / 优化 / 修复 / 重构 / Release 前，必须先读取当前 GitHub 真实状态并进行深度研究与影响分析。**

## 1. 强制顺序

```text
GitHub Current State
→ Baseline / HEAD / Working Tree
→ Architecture & Contract Deep Read
→ Relevant Historical Cases
→ External Benchmark / GitHub Research
→ Capability Gap Analysis
→ Minimal Change Plan
→ Implementation
→ Tests / E2E
→ Evidence
→ Cross-Repository Verification
→ Capability Delta
→ Review
→ Promotion Candidate
→ Learning / Failure Memory
```

任何步骤无法验证时必须标记 `NOT_VERIFIED`，不得用推测补齐事实。

## 2. 研究不是可选步骤

“链接 GitHub 学习研究”是平台级永久规则，不再依赖人工在每次任务中重复提出。

研究必须优先服务当前任务：
- 当前仓库源码与历史提交
- 同类型高质量开源项目
- 官方工程规范与成熟实践
- 已沉淀成功/失败案例
- 三仓库已有能力与重复实现

外部案例只能作为 `Research Material`，不能直接成为 `observedState`、Evidence 或生产事实。

## 3. 三仓库及其他产品

适用范围不是只限 DCC。所有接入本研发体系的产品均继承本规则。

当前正式范围：
- DCC
- Z-Brand-Core
- SICI-Core
- AI-Development-Research-Hub

后续新增产品默认继承，不需要重新口头授权研发研究规则。

## 4. 优化前必须深度剖析

至少检查：
- 当前 HEAD / Remote HEAD
- Baseline / Version
- 工作区与未提交变化
- 相关源码与测试
- Ownership / Contract / Dependency
- 历史失败与回归案例
- 已有 Research / Shadow / Capability 记录
- GitHub Actions / CI
- 安全边界

目标是避免重复开发、破坏已有功能、遗漏真实依赖和在旧事实基础上修改。

## 5. 优化后必须反哺

每次完成的有效优化都应产生可追溯结果：
- Evidence
- Before / After Metrics
- Capability Delta
- 三方验证结果
- Failure / Lesson（如有）
- Research Case / Learning Record

通过验证的能力才可进入 `Promotion Candidate`；未验证能力保持 Shadow / Review 状态。

## 6. 不自动越权

- AI confidence ≠ Evidence
- Research ≠ Fact
- Shadow ≠ Production
- Promotion Candidate ≠ Promotion
- NOT_VERIFIED ≠ PASS

不得自动修改生产逻辑、自动 Promotion 或扩大权限边界。

## 7. 长期学习

平台持续积累：
- Research Cases
- Failure Memory
- Capability Memory
- Capability Delta History
- Benchmark Registry
- Shadow Patterns

每月进行 4 次不定时深度研究；研究结果必须进入案例/能力生命周期，而不是停留在一次性聊天结论。

## 8. 最高目标

形成稳定的：

**研究 → 开发 → 测试 → 三方验证 → 能力增量 → 反哺 → 再研究**

工程学习闭环，并将成熟方法沉淀为可复用能力。