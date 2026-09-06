# Global Cross-Repository Baseline — Before/After Three-Repository Audit

> **状态：IMMUTABLE EXECUTION RULE**  
> 适用于 DCC、Z-Brand-Core、SICI-Core，以及未来接入本 Hub 的正式产品。

## 1. 核心原则

> **局部修改，三方理解；局部验证，三方复核；局部成果，全局反哺。**

任何一方进行开发、修改、优化、修复、重构、测试、发布、研究或学习沉淀，都不得只以当前仓库为上下文作决定。

Hub 是共享研发中枢，但不取得任何正式产品的生产控制权。

## 2. Before Gate — 执行前三库全量理解

在任何变更开始前，必须读取并对照：

1. AI-Development-Research-Hub（整合库）
2. Development-Command-Console（DCC）
3. Z-Brand-Core
4. SICI-Core

至少核对：

- 当前 Remote HEAD / Baseline / pinned SHA
- Unified Capability Matrix / Gap Matrix
- Capability Registry
- AI Research Case Library
- Research Benchmark Registry
- Research / Learning / Shadow Learning 状态
- Evidence Contract 与 Evidence Index
- Three-Repository Validation Matrix
- Failure / Lesson / Known Issues
- 当前 Change Plan / 未完成事项
- 仓库边界、依赖关系和可复用能力

**Before Gate 未完成：不得开始修改代码。**

## 3. Change Gate — 增量开发

变更必须遵循现有基线，只允许增量改进，不得借优化之名删除、覆盖或削弱既有能力。

新发现按以下分类沉淀：

- `research`：外部研究材料或待验证假设
- `experiment`：实验及结果
- `failure`：真实失败与根因
- `lesson`：可复用经验
- `capability`：能力增量
- `shadow`：尚未正式晋级的候选模式
- `evidence`：真实验证证据
- `review`：人工审核记录

外部 GitHub、官方文档、开源项目和行业案例只能作为 **Research Material**；不得直接变成事实、Evidence 或 Production Decision。

## 4. After Gate — 完成后三库再次全量复核

变更完成后必须再次执行 Hub + DCC + Z-Brand-Core + SICI-Core 全量对照。

必须检查：

- 能力是否真实提升
- Capability Delta 是否成立（before / after / metrics / improvement / side effects）
- 原有能力是否回归或退化
- 是否产生跨仓库冲突
- 是否产生重复实现
- 是否破坏 Contract / API / 数据链路
- 权限与安全边界是否保持
- Evidence 是否真实且可追溯
- 三方是否实际完成各自验证维度
- 新 Research / Failure / Lesson / Capability / Shadow 是否需要反哺 Hub
- 是否达到下一阶段 Release / Delivery Gate

## 5. Three-Way Verification Gate

跨仓库能力必须同时获得：

- **Z-Brand-Core**：业务正确性、生产稳定性、数据一致性、品牌业务适用性、回滚影响
- **DCC**：工程质量、权限、安全、测试、Evidence、兼容性、回滚
- **SICI-Core**：移动适用性、设备约束、真实工作流、弱网/离线、PWA 兼容性

任何必须验证方为 `fail`，能力不得晋级；无法完成验证必须保持 `not_verified` / `pending`，不得冒充 `pass`。

## 6. Capability Delta Gate

“学习了”或“实现了”不等于“能力提升”。正式 Promotion Candidate 至少需要：

- before evidence
- before metrics
- after evidence
- after metrics
- non-empty measurable improvement
- side effects acknowledged / accepted / mitigated
- DCC + Z-Brand-Core + SICI-Core 三方验证 Evidence

**AI confidence is not Evidence.**

## 7. Shadow Learning Gate

Shadow Learning 用于观察、归纳和验证模式，不得自动改变生产行为。

固定生命周期：

```text
Research → Candidate → Shadow → Evidence → Review → Verify → Promotion Candidate → Reusable Capability
```

禁止：

- Shadow 自动 Promotion
- AI 输出直接作为 Evidence
- 用历史 Evidence 冒充当前 Evidence
- 用本地 HEAD 冒充 Remote HEAD
- 为通过 Gate 而篡改 observedState
- 网络失败写成验证成功

## 8. Global Feedback Loop

每次变更形成闭环：

```text
Before Audit
    ↓
Three-Repository Understanding
    ↓
Change / Experiment
    ↓
Local Verification
    ↓
After Audit
    ↓
Cross-Repository Verification
    ↓
Capability Delta
    ↓
Shadow Learning
    ↓
Human Review
    ↓
Promotion Candidate
    ↓
Reusable Capability
    ↓
Research Case / Failure / Lesson / Capability
    ↓
Hub Global Library
    ↓
下一轮 Before Audit
```

## 9. Scope Inheritance

本规则默认继承到所有未来接入 Hub 的产品。新产品接入时必须建立其：

- Repository Identity
- Baseline
- Capability Matrix
- Verification Dimensions
- Evidence Contract Adapter
- Research / Case Library Adapter
- Shadow Learning Adapter

本规则不能覆盖产品自身更严格的安全、权限或生产基线；只能增加验证强度，不得降低既有安全标准。

## 10. 执行判定

| 阶段 | 条件 | 决策 |
|---|---|---|
| Before | 三库事实未完整读取 | `STOP` |
| Change | 发现基线冲突 | `REPLAN` |
| After | Evidence 不完整 | `REVIEW_REQUIRED` |
| After | 任一必须方 FAIL | `HOLD` |
| After | 三方通过 + Capability Delta 通过 | `PROMOTION_CANDIDATE` |
| Shadow | 未完成人工 Review | `REVIEW_REQUIRED` |

**此规则只建立执行约束，不授予 Hub 生产写权限。**
