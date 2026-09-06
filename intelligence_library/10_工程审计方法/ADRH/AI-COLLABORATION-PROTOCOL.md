# AI Collaboration Protocol — ChatGPT ↔ 豆包互相 Review

> 两个 AI 不是互相信任，而是互相 Review。

## 1. 原则

- **互不信任，互相验证**：ChatGPT 和豆包各自独立分析，交叉 Review
- **Research ID 唯一**：每个研究任务拥有唯一标识，可追溯
- **Evidence 优先**：AI 输出不是 Evidence，真实运行/测试结果才是
- **分歧可见**：两个 AI 的不同意见必须记录，不得静默统一

## 2. Research ID 规范

格式：`R-YYYY-NNNN`

- `R`：固定前缀
- `YYYY`：年份（如 2026）
- `NNNN`：四位序号，从 0001 开始

示例：`R-2026-0001`

**分配规则：**
- 由 Hub `tools/research_id.py` 生成，读取 `data/research/` 现有记录递增
- 每个研究任务一个 ID，子任务用 `R-2026-0001.1` 形式
- ID 一旦分配不可复用

## 3. Research Record 字段

每个研究记录必须包含：

| 字段 | 说明 | 必填 |
|---|---|---|
| `research_id` | 唯一 Research ID | 是 |
| `ai_agent` | 执行 AI（ChatGPT / 豆包 / 两者） | 是 |
| `timestamp` | ISO 8601 UTC 时间 | 是 |
| `source` | 研究来源（需求仓库/触发事件） | 是 |
| `repository` | 关联仓库 | 是 |
| `observed_sha` | 研究时观察到的 commit SHA | 是 |
| `research_question` | 研究问题 | 是 |
| `hypothesis` | 假设 | 否 |
| `findings` | 发现 | 否 |
| `implementation` | 实现说明 | 否 |
| `tests` | 测试引用 | 否 |
| `evidence` | Evidence 引用（非 AI 输出） | 否 |
| `review` | 对方 AI 的 Review 意见 | 否 |
| `status` | 状态（见生命周期） | 是 |
| `learning_result` | 学习成果 | 否 |

## 4. 互相 Review 流程

```text
AI-A 发起研究（记录 research_id, ai_agent=A）
  ↓
AI-A 提交 findings + hypothesis
  ↓
AI-B 独立 Review（记录 review 字段，ai_agent=B）
  ↓
  ├── 一致 → 进入 Experiment
  ├── 分歧 → 记录双方观点，进入 Evidence 收集
  └── AI-B 发现事实错误 → 退回 AI-A 修正
```

**Review 要求：**
- Review 方必须独立验证关键事实（SHA、文件存在、测试结果）
- Review 意见必须具体，不得只写"同意"或"不同意"
- 分歧必须记录，不得由一方静默覆盖另一方

## 5. 当前研究记录

| Research ID | 研究问题 | 状态 | AI Agent |
|---|---|---|---|
| R-2026-0001 | Hub 仓库创建与基础架构搭建 | completed | 豆包 |

## 6. 禁止行为

- 禁止一个 AI 冒充另一个 AI 签署 Review
- 禁止跳过 Review 直接进入实现
- 禁止把 AI 输出当作 Evidence
- 禁止在 Research Record 中存储凭证
