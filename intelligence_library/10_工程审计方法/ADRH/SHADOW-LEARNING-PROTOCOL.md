# Shadow Learning Protocol

> Shadow Learning 固定生命周期。Shadow 状态下不得自动改变生产行为。

## 1. 固定生命周期

```text
Research → Hypothesis → Candidate → Shadow → Evidence → Review → Verify → Promotion Candidate → Reusable Capability
```

每个阶段必须有明确的进入条件和退出条件，不得跳阶段。

## 2. 阶段定义

### 2.1 Research
- **进入**：研究需求提出，分配 Research ID
- **活动**：文献/案例/代码研究，形成研究记录
- **退出**：研究问题明确，形成可检验假设
- **禁止**：直接写生产代码

### 2.2 Hypothesis
- **进入**：研究问题明确
- **活动**：形成可证伪的假设，定义成功标准
- **退出**：假设可检验，成功/失败标准量化

### 2.3 Candidate
- **进入**：假设形成
- **活动**：实现候选方案（在 Hub 隔离环境中），编写测试
- **退出**：候选方案可运行，单元测试通过
- **禁止**：候选代码进入三仓库生产路径

### 2.4 Shadow
- **进入**：候选方案单元测试通过
- **活动**：在 Shadow 模式下运行，与生产行为并行对比，**不改变生产**
- **退出**：收集到足够的 Shadow 运行数据
- **核心约束**：Shadow 输出仅供观察，不得自动影响生产决策

### 2.5 Evidence
- **进入**：Shadow 数据收集完成
- **活动**：整理真实运行 Evidence，区分 AI 输出与真实结果
- **退出**：Evidence 完整、可追溯、非 AI 生成

### 2.6 Review
- **进入**：Evidence 完整
- **活动**：ChatGPT ↔ 豆包互相 Review，三方仓库各自验证
- **退出**：Review 意见记录，分歧 resolved 或明确标注

### 2.7 Verify
- **进入**：Review 完成
- **活动**：三方验证（Z-Brand 业务 + DDC 工程 + SICI 移动）
- **退出**：至少相关方验证通过

### 2.8 Promotion Candidate
- **进入**：Verify 通过
- **活动**：准备晋级材料，定义 Contract/Adapter 接口
- **退出**：晋级材料完整

### 2.9 Reusable Capability
- **进入**：晋级材料完整，DDC 工程验证通过
- **活动**：注册到 Capability Registry，状态为 `reusable`
- **退出**：三仓库可通过 Contract/Adapter 使用

## 3. 禁止行为

| 禁止 | 原因 |
|---|---|
| AI 判断 → 直接生产 | 缺少 Evidence 和验证 |
| Shadow 状态自动改变生产行为 | Shadow 是观察模式，不是执行模式 |
| 跳过 Shadow 直接晋级 | 缺少真实运行数据 |
| 把 AI 输出当作 Evidence | Evidence 必须来自真实运行/测试 |
| 一个仓库验证通过即认为三方通过 | 各方验证维度不同 |
| Shadow 数据包含凭证 | 安全基线 |
| 晋级后绕过 Contract 直接复制代码 | 禁止核心实现复制 |

## 4. Shadow 数据存储

- 位置：`data/shadow/`
- 格式：JSONL，每行一个 Shadow 运行记录
- 必须字段：`research_id`, `shadow_run_id`, `timestamp`, `input`, `expected_output`, `shadow_output`, `diff`, `production_unchanged` (bool)
- `production_unchanged` 必须为 `true` 才允许进入下一阶段

## 5. 与 DDC learning_promote 的关系

DDC `tools/learning_promote.py` 已实现 evidence-gated 晋级逻辑。Hub 参考其设计：
- 晋级是显式决策，不是写记录的副作用
- `verified` / `promoted` 必须有 evidence_refs
- 不自动晋级代码或权限

Hub 不复制 DDC 实现，而是在 Shadow Lifecycle 中引用相同原则。
