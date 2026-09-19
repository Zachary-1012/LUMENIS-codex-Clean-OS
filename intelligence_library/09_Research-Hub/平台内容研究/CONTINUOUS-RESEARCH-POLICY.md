# SICI Continuous Research & Development Policy

> **永久规则：任何功能开发、优化、修复、重构或 Release 前，必须先读取 GitHub 当前真实状态，并进行深度架构、交互、历史案例与同类型工程研究。**

## 强制流程

```text
GitHub Current State
→ Baseline / HEAD
→ SICI Architecture / Mobile Constraints
→ Historical Cases / Failures
→ GitHub / Industry Research
→ Capability Gap
→ Minimal Change Plan
→ Implementation
→ Test / E2E / Device-oriented Verification
→ Evidence
→ DCC Governance Verification
→ Z-Brand Business Compatibility Verification
→ Capability Delta
→ Review
→ Release / Promotion
→ Learning Case
```

## SICI 特别规则

移动端优先、真实设备约束、PWA/浏览器限制和用户工作流稳定性必须优先于抽象的技术便利。不得为了共享能力复制 Z-Brand 业务逻辑或 DCC 工程控制逻辑。

## 持续 GitHub 研究

GitHub 同类型高质量项目、官方规范、移动端工程案例以及历史成功/失败案例属于研发输入，不需要每次人工重复提醒。外部研究必须标记 `Research Material`，不能直接成为生产事实。

## 三方反哺

DCC 提供工程治理、Evidence 和验证规则；Z-Brand 提供业务/生产验证；SICI 提供移动交互和真实使用反馈。任何一方的结论都不能绕过另外两方的适用验证。

`NOT_VERIFIED` 不得写成 `PASS`；`Promotion Candidate` 不等于自动 Promotion；AI confidence 不等于 Evidence。

## 长期学习

每次有效优化都应沉淀 Research Case、Failure Memory、Capability Memory、Capability Delta 和 Shadow Pattern。每月 4 次不定时深度研究，并将稳定成果反馈到可复用能力。

**目标：研究 → 开发 → 测试 → 三方验证 → 反哺 → 再研究。**