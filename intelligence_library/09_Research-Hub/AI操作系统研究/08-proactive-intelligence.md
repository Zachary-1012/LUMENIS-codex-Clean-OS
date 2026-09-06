# H｜Proactive Intelligence 技术方案

> 交付物 H · 所属：OSAI P0 三位一体研究体系 · ① AI Frontier Research

## 五阶段 Interruption Policy

```
Signal（信号检测）→ Context（上下文理解）→ Importance（重要性评估）
→ Evidence（证据验证）→ Actionability（可操作性）→ Interruption Decision
```

## 通知分级

| 级别 | 行为 | 示例 |
|------|------|------|
| **P0** | 立即打断用户 | "ZBC Collector 连续 3 次崩溃，根因指向 Session 生命周期，建议立即检查 P0 Auth Recovery" |
| **P1** | 定时汇总（每日/每周） | "本周发现 2 个可优化的架构模式，详见报告" |
| **P2** | 静默记录，用户主动查询时展示 | "记录到 17 个 GitHub 更新（不通知）" |
| **P3** | 忽略 | 低价值噪声 |

## 反模式

- ❌ "今天 GitHub 有 17 个更新"（原始数据，无洞察）
- ✅ "发现 ZBC 最近 3 次 Collector 异常都发生在 Session 生命周期附近，和过去一类故障模式一致，建议优先检查 P0 Auth Recovery"（可操作洞察+证据+历史关联）

---

## 2026-09-02 学习进化更新（Learning Evolution Update）

> 来源：OSAI 持续学习进化摘要 `learning-feed/learning-20260902.md`（commit eda890f）

### Proactive 验证基准落地（RESEARCH_MORE｜P1）

Interruption Policy 从"设计规范"走向"可验证"，新增真实数据基准：

| 基准 | 评估内容 | 对 OSAI Proactive 的价值 |
|------|---------|-------------------------|
| **ProAgentBench**（arXiv 2602.04482） | 真实工作场景 proactive，时序预测 + 干预信号 | 验证 Signal→Context 阶段的触发时机判断 |
| **π-Bench**（2605.14678） | 100 个多轮任务、5 个用户 persona，含隐藏意图、跨会话连续性 | 验证"何时该主动 / 何时该沉默" |
| **YC-Bench**（2604.01212） | 一年期模拟创业，长期一致性执行 | 验证长期规划与渐进式干预 |

### 验证方式

- 用上述基准对 OSAI 的 Interruption Policy 做**真实数据回放测试**：将历史对话/任务序列输入，评估 P0/P1/P2/P3 分级准确率与误报率
- 目标：P0 通知的"可操作洞察 + 证据 + 历史关联"三要素命中率纳入 Proactivity 维度（权重 0.07）评分

### 长期方向参考（MONITOR）

- **PILOT**（arXiv 2608.26530）：supervisor-worker 实时自我改进（live steering + live self-evolution），6 组合中 5 项第一 —— OSAI Proactive L2+ 参考
- **BAO**（2602.11351）：行为 agent 优化，自主性-满意度 Pareto —— 辅助确定"何时应该打扰用户"的边界
