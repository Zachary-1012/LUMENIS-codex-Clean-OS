# Three-Repository Validation Matrix

> 任何准备进入正式产品的能力都必须通过三方验证。一个仓库验证成功，不代表另外两个自动成功。

## 0. Global Before / After Rule

本矩阵现在受 `GLOBAL-CROSS-REPOSITORY-BASELINE.md` 约束。

**任何开发、修改、优化、修复、重构、测试、发布、研究或学习任务：**

```text
Before：Hub + DCC + Z-Brand-Core + SICI-Core 全量读取/剖析/对照
        ↓
Change / Experiment
        ↓
Local Verification
        ↓
After：Hub + DCC + Z-Brand-Core + SICI-Core 再次全量读取/剖析/对照
        ↓
Three-Way Verification
        ↓
Capability Delta
        ↓
Shadow Learning / Review
        ↓
Promotion Candidate
```

未完成 Before Gate，不得修改代码；未完成 After Gate，不得宣称能力已正式晋级。

## 1. 验证维度

### Z-Brand-Core：业务/生产适用性

| 检查项 | 说明 |
|---|---|
| 业务正确性 | 能力是否符合品牌业务逻辑 |
| 生产稳定性 | 是否影响 CTH-POMS / ZBMP 生产运行 |
| 数据一致性 | 是否影响业务数据链路 |
| 舆情/市场情报适用性 | 是否适用于品牌传播场景 |
| 回滚影响 | 出问题时对业务的影响范围 |

### DDC：工程、权限、测试、Evidence、Rollback

| 检查项 | 说明 |
|---|---|
| 工程质量 | 代码规范、架构一致性 |
| 权限边界 | 是否越权、是否扩大默认权限 |
| 测试覆盖 | 单元测试 / 集成测试 / E2E |
| Evidence 完整 | 是否有真实运行 Evidence，非 AI 输出 |
| 回滚路径 | 是否有明确 baseline 和恢复方案 |
| 安全 | 是否引入安全风险、凭证泄露 |
| 兼容性 | 是否破坏现有 Contract |

### SICI-Core：手机端、设备约束、真实用户工作流

| 检查项 | 说明 |
|---|---|
| 移动适用性 | 是否适合手机端交互 |
| 设备约束 | 性能、内存、网络、屏幕尺寸 |
| 工作流匹配 | 是否符合真实用户移动工作流 |
| 离线/弱网 | 弱网环境下的行为 |
| PWA 兼容性 | 是否兼容 SICI 的 PWA 架构 |

## 2. 验证矩阵

| 能力类型 | Z-Brand | DDC | SICI | 说明 |
|---|---|---|---|---|
| 纯工程工具（如 Research ID 生成） | N/A | **必须** | N/A | DDC 验证工程质量即可 |
| 业务研究案例 | **必须** | 必须 | N/A | Z-Brand 验证业务适用性 |
| 移动交互实验 | N/A | 必须 | **必须** | SICI 验证设备/工作流 |
| 跨仓库能力 | **必须** | **必须** | **必须** | 三方全部验证 |
| Hub 内部基础设施 | N/A | **必须** | N/A | DDC 验证工程边界 |

## 3. 验证状态枚举

- `pass`：验证通过
- `fail`：验证失败，需修正
- `not_applicable`：不适用（需说明原因）
- `not_verified`：未验证（显式标记，不得冒充 pass）
- `pending`：待验证

## 4. 验证流程

```text
Before Gate
  ↓
Hub + DDC + Z-Brand + SICI 全量理解
  ↓
能力进入 Promotion Candidate
  ↓
Hub 发起三方验证请求
  ↓
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Z-Brand 验证 │ │ DDC 验证    │ │ SICI 验证   │
│ 业务/生产    │ │ 工程/权限   │ │ 移动/设备   │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
       └───────────────┼───────────────┘
                       ↓
             After Gate 全量复核
                       ↓
                Capability Delta
                       ↓
              验证结果汇总到 Research Record
                       ↓
          所有必须方 pass + Delta 通过 → Reusable Capability
          任一必须方 fail / Delta 不成立 → 退回 Shadow/Candidate
```

## 5. 已有验证记录

| Research ID | 能力 | Z-Brand | DDC | SICI | 状态 |
|---|---|---|---|---|---|
| R-2026-0001 | Hub 基础架构 | not_applicable | pass | not_applicable | verified |

## 6. 与 SICI 已有三方验证规则的关系

SICI-Core 最新 commit（`6349682`）已添加 `three-repository validation rules` 和 `three-repository verification gate`。Hub 的验证矩阵与之一致，不创建冲突规则，而是提供集中化的验证记录索引。

## 7. Capability Delta 作为晋级前置条件

三方验证回答“是否验证过”；Capability Delta 回答“验证后是否真的变强”。正式 Promotion Candidate 必须尽可能提供：

- before evidence + metrics
- after evidence + metrics
- measurable improvement
- side effects acknowledged / accepted / mitigated
- DCC + Z-Brand-Core + SICI-Core 的真实验证 Evidence

**AI confidence is not Evidence。**
