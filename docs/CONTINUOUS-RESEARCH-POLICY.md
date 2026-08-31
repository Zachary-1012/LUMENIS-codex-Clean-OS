# Z-Brand Continuous Research & Development Policy

> **永久规则：任何优化、修复、重构、功能开发或 Release 前，先读取 GitHub 当前真实状态并进行深度审计与同类型工程研究。**

## 强制流程

```text
GitHub Current State
→ Baseline / HEAD
→ Z-Brand Architecture & Business Boundary
→ Historical Cases / Failures
→ GitHub / Industry Research
→ Capability Gap
→ Minimal Change Plan
→ Implementation
→ Test / E2E
→ Evidence
→ DCC Verification
→ SICI Compatibility Verification
→ Capability Delta
→ Review
→ Release / Promotion
→ Learning Case
```

## Z-Brand 特别规则

CTH-POMS 生产稳定性优先，ZBMP 作为 Core 内受控增强能力层。研究和优化不得破坏现有业务口径、主体过滤、数据质量、安全边界或生产运行能力。

## 研究规则

GitHub 同类型高质量项目、官方工程规范、品牌/舆情/市场情报案例以及本项目历史成功/失败案例都属于持续 Research 输入。外部案例必须标记为 `Research Material`，不得直接当作生产事实。

## 三方反哺

DCC 负责工程治理与 Evidence；Z-Brand 负责真实业务价值与生产验证；SICI 负责移动端/真实交互兼容性。三方不是互相覆盖，而是互相验证。

任何能力进入稳定复用前必须有真实 Evidence 与 Capability Delta。`NOT_VERIFIED` 不得写成 `PASS`，`Promotion Candidate` 不等于自动 Promotion。

## 长期学习

每次有效优化都应沉淀到共享 AI 学习体系：Research Case、Failure Memory、Capability Memory、Capability Delta、Benchmark、Shadow Pattern。每月 4 次不定时深度研究。

**目标：研究 → 开发 → 测试 → 三方验证 → 反哺 → 再研究。**