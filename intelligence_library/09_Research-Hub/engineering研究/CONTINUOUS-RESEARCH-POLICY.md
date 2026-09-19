# DCC Continuous Research Policy

> **永久规则：每次 Material Change、优化、修复、重构或 Release 前，必须先读取 GitHub 当前真实状态，并进行深度源码、架构、历史案例与同类型工程研究。**

## 强制闭环

```text
Current GitHub State
→ Baseline / HEAD / Scope
→ Deep Architecture Audit
→ Historical Failure / Success Cases
→ GitHub / Industry Research
→ Capability Delta / Gap
→ Minimal Change Plan
→ Code
→ Test / E2E
→ Evidence
→ Three-Repository Verification
→ Capability Delta
→ Review
→ Promotion Candidate
→ Learning / Failure Memory
```

## 永久约束

1. 不以历史报告代替当前事实。
2. 网络失败必须标记 `NOT_VERIFIED`。
3. 外部研究是 `Research Material`，不是事实。
4. AI confidence 不能替代 Evidence。
5. Shadow 不得自动进入生产。
6. Promotion Candidate 不等于 Promotion。
7. 不删除既有能力，不无理由重写架构。
8. 不扩大权限边界。
9. 三仓库验证必须保持 DCC / Z-Brand-Core / SICI-Core 的职责边界。
10. 每次有效优化必须沉淀 Evidence、Capability Delta，并在适用时沉淀 Failure / Learning Case。

## GitHub 持续研究

研究 GitHub 同类型高质量工程、官方规范、成熟开源实践以及本组织历史实现，是研发流程的一部分，不再需要每次任务单独提醒。

研究结果必须经过：

`Research → Hypothesis → Experiment → Evidence → Verification → Capability Delta`

才能进入能力候选。

## 长期学习

持续维护 Research Cases、Failure Memory、Capability Memory、Benchmark Registry 与 Shadow Patterns。每月 4 次不定时深度研究，研究结果必须可追溯、可验证、可复用。

**目标：研究 → 开发 → 测试 → 三方验证 → 反哺 → 再研究。**