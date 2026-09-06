# I｜AI Safety / Permission Sandbox 技术方案

> 交付物 I · 所属：OSAI P0 三位一体研究体系 · ① AI Frontier Research

## 核心架构：Task-bound Permission

```
Intent → Policy → Permission(Ticket) → Tool → Sandbox → Evidence
```

**Permission Ticket 数据结构**：
- 时效（任务开始-结束，超时自动撤销）
- 范围（可操作的文件/API/网络域白名单）
- 成本上限（API 调用次数/Token/时间）
- 操作白名单（允许的工具和参数范围）

**绝对禁止链路**：
```
LLM → Unlimited Browser → Unlimited Filesystem → Production DB → Secrets  ❌
```

## 沙箱方案

- **代码执行**：E2B Firecracker 微 VM（80ms 冷启动，1B+ 运行量）
- **浏览器**：隔离浏览器实例，Cookie 隔离，网络白名单
- **文件系统**：只读挂载项目目录，临时目录可写，任务结束清理
- **网络**：域名白名单，出站流量审计

## Skeptic 集成

- 高风险决策（生产环境操作、权限提升、数据删除）必须走 **3 Agent 辩论**
- 辩论流程：Proposal → Architect → Security → Skeptic Debate → Tester → Evidence → Decision
- 自我纠错（Self-Refine）仅用于低风险场景，提升约 20% 但有盲区

---

## 2026-09-02 学习进化更新（Learning Evolution Update）

> 来源：OSAI 持续学习进化摘要 `learning-feed/learning-20260902.md`（commit eda890f）
> 触发：Agent 安全实证研究（StakeBench / StepJack / ClawSafety / ClawsBench）

### 核心结论升级：输入过滤已被实证证伪

**新增证据（2026 年中）**：

| 基准 | 关键发现 | 来源 |
|------|---------|------|
| **StakeBench**（NTU/ST Engineering/IBM/UIUC） | 3,160 次攻击，GPT-5/Gemini 驱动的 web agent **无一种攻击场景被一致阻断**；直接注入成功率 >79%，间接注入 42%-68% | cybersecurity-now.co.uk |
| **StepJack**（arXiv 2608.06477） | 新攻击类别：对抗目标被拆解为无害子步骤、分散在导航链上（多步间接注入） | arXiv |
| **ClawSafety** | 120 用例、5 领域；**Chat safety ≠ Agent safety**（间接注入下合规率 40-75%）；**scaffold 选择本身可移动 ASR 达 8.6pp** | github.com/weibowen555/ClawSafety |
| **ClawsBench**（arXiv 2604.05172） | 生产力 agent 安全基准，不可逆有害动作负分惩罚（one-way-door） | arXiv |
| **ICML 2026** | 能力增长远超可靠性增长（"Towards a Science of AI Agent Reliability"） | awesome-auditable-ai |

### 基线更新决议（ADOPT｜P0）

1. **防御层级重排**：`沙箱 + Task-bound 权限 + 人工确认` 升级为**唯一硬防线**；输入/输出层 Prompt 过滤**降级为辅助层**，不得作为独立安全边界（StakeBench 证明不可单独依赖）。
2. **Scaffold 本身是安全边界**：ClawSafety 实证 scaffold 选择可移动 ASR 达 8.6pp —— 安全设计必须**从 prompt 层上移到运行时/工具层**。
3. **新增攻击面认知**：StepJack 多步间接注入要求 OSAI 的浏览器/工作流类 Agent 在**每一步**都做权限校验，而非仅入口校验。
4. **安全验收标准**：任何 Browser/Workflow Capability 上线前，必须以 StakeBench/StepJack/ClawSafety 风格红队评测通过为前置条件。

### 对 Z Brand Core 的 Contract 建议

- **CTR-SEC-P0-01**：OSAI 侧完成安全基线文档升级（本文件）；ZBC 侧需将输入过滤从"安全边界"降级为"辅助层"，沙箱与 Task-bound 权限升级为硬门槛。
- **CTR-SEC-P0-02**：ZBC 在 Collector/Browser Runtime 的每一步操作加入权限校验（应对 StepJack 多步注入）。
