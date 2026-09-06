# J｜OSAI Evaluation Framework

> 交付物 J · 所属：OSAI P0 三位一体研究体系 · ① AI Frontier Research

## 12 维评估矩阵

| 维度 | 权重 | 评分方法 | 数据来源 |
|------|------|---------|----------|
| **Safety** | 0.15 | 安全事件数+注入防御成功率（硬门槛<30阻断） | 安全测试、红队评估 |
| **Capability** | 0.12 | 任务成功率（SWE-bench/GAIA/WebArena） | Benchmark + 实际任务 |
| **Reliability** | 0.10 | 一致性+恢复率+故障率 | 持续运行监控 |
| **Evidence** | 0.10 | 证据覆盖率+证据强度+可追溯性 | Evidence Layer 审计 |
| **Learning** | 0.10 | Learning Lift（经验学习前后能力对比） | A/B 测试+经验命中率 |
| **Recovery** | 0.08 | 失败恢复率+恢复时间+回滚成功率 | 故障注入测试 |
| **Human Collaboration** | 0.08 | 用户满意度+干预率+建设性分歧采纳率 | 用户反馈+交互日志 |
| **Proactivity** | 0.07 | 通知准确率+行动转化率+误报率 | 通知日志+用户反馈 |
| **Cost** | 0.06 | 单任务成本+Token 效率+API 成本 | 成本监控 |
| **Regression** | 0.05 | 回归检测通过率+能力退化率 | 持续回归测试 |
| **Latency** | 0.05 | 端到端延迟+首响应时间 | 性能监控 |
| **Maintainability** | 0.04 | 代码质量+文档覆盖率+架构健康度 | 静态分析+评审 |

## 核心原则

- **Safety 硬门槛**：Safety 评分 <30 直接阻断该能力上线，不可被其他维度高分覆盖
- **超越 Benchmark**：Benchmark 仅占 Capability 维度的一部分，实际任务表现权重更高
- **Learning Lift**：经验学习前后的能力对比是 OSAI 的核心评估指标
- **持续评估**：所有维度持续测量，趋势追踪，回归自动检测

---

## 2026-09-02 学习进化更新（Learning Evolution Update）

> 来源：OSAI 持续学习进化摘要 `learning-feed/learning-20260902.md`（commit eda890f）

### 安全维度评测项扩充（ADOPT｜P0）

在 **Safety** 维度（硬门槛 <30 阻断）基础上，纳入 2026 年最新 Agent 安全基准作为红队评测项：

| 评测项 | 衡量内容 | 优先级 |
|--------|---------|--------|
| **StakeBench** | 直接/间接注入攻击成功率的阻断能力（当前 GPT-5/Gemini web agent 无一致阻断） | P0 |
| **StepJack** | 多步间接注入（子步骤分散在导航链）防御 | P0 |
| **ClawSafety** | Chat safety ≠ Agent safety；间接注入下合规率 | P0 |
| **ClawsBench** | 生产力 agent 不可逆有害动作负分惩罚 | P1 |

**安全维度评分方法更新**：不再仅看"输入过滤成功率"，改为**红队评测通过率 + 沙箱逃逸次数 + 权限越界事件数**三合一。

### 记忆评估维度扩充（ADAPT｜P1）

在 **Learning** 维度新增记忆效果评估：
- **Agent Memory Leaderboard**（2026-08 首批公开：136 支队伍、69 个记忆系统）—— OSAI Experience Engine 的记忆系统对标
- **MemoryArena**（ICML 2026）—— 多会话真实场景记忆基准

**Learning Lift 评分**：经验学习前后能力对比，结合记忆基准结果综合评价。

### 新增验证基准（RESEARCH_MORE｜P1）

Proactive 维度可用 **ProAgentBench**（arXiv 2602.04482）、**π-Bench**（2605.14678）、**YC-Bench**（2604.01212）做真实数据验证（含隐藏意图、跨会话连续性、长期一致性）。
