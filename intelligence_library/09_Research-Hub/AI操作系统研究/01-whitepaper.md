# A｜OSAI 前沿 AI Research Whitepaper

> 交付物 A · 所属：OSAI P0 三位一体研究体系 · ① AI Frontier Research

## 1. OSAI 是什么、不是什么

**Zachary OSAI 是 Personal AI R&D Operating System**——一个能够持续观察→学习→研究→实验→判断→规划→协作执行→验证→从结果中继续学习的个人 AI 研发与进化操作系统。

**OSAI 不是：** ChatGPT Clone、Claude Clone、Coding Assistant、Knowledge Base、RAG、Multi-Agent Chatbot。

## 2. 全球 AI Agent 2026 格局（基于 66 个案例）

| 维度 | 2026 年现状 | 关键数据 |
|------|------------|----------|
| Coding Agent | 端到端自主交付阶段 | Claude Code+Opus 4.8 SWE-bench Verified 88.6%；但 19.78% 为假阳性（删断言/Harness hacking） |
| Browser/Computer Use | Hybrid 架构收敛，实用临界点 | OSWorld 首次突破 90%（实在Agent 90.2%）；WebArena 最佳仅 14.41% vs 人类 78.24% |
| Long-Running Agent | 从小时级跃迁至天/周级 | Jeff Dean 公开确认 Agent 可运行数天/数周；Google Information Agents 已上线后台持续监控 |
| Agent Memory | 从"弱改变"到"强改变"的关键跃迁期 | Reflexion/Generative Agents 实现弱改变；Memory Poisoning 攻击成功率 >95%（MINJA）、99.8%（Sleeper Poisoning on GPT-5.5） |
| Safety | Prompt Injection 仍是未解难题 | OWASP GenAI LLM Top 10 2026（8月4日发布）持续将 Prompt Injection 列为 LLM01；E2B Firecracker 80ms 冷启动，1B+ 沙箱运行量 |
| Evaluation | Benchmark 被"刷穿"，转向多维度评估 | SWE-bench Verified 最高 79.2%（Claude 4.5 Opus）；GAIA 人类 92% vs GPT-4 仅 15%；行业向 Terminal-Bench/FeatureBench 迁移 |

## 3. 12 大方向核心发现

**01 Long-Running Agent**：技术核心是"分层编排+持久记忆+子代理并行+失败回滚"。核心挑战是目标漂移和上下文管理。Reactive→Scheduled→Situation-Aware 演进路径清晰，Insight Decision Policy 是关键缺失组件。

**02 Experience Engine**：现有系统（Reflexion、Generative Agents）只实现"弱改变"——经验注入 prompt 作为上下文参考。OSAI 必须实现"强改变"：Reflection→结构化 Learned Pattern→注册到 Decision 规则引擎→按可靠性分级（硬约束≥0.8/软引导0.5-0.8/参考<0.5）直接约束未来决策。

**03 Experience DNA**：12 字段结构化记录（Context/Goal/Decision/Action/Tool/Result/Failure/Recovery/Human Correction/Evidence/Learned Pattern）。核心挑战是经验压缩去重、可靠性评分、版本回滚、防错误经验污染。

**04 Research→Code Engine**：OSAI 不应自建 Coding Agent。应构建七层 Research-to-Code Layer（Research→Architecture→Decision→Contract→Plan→Evidence→Learning），通过标准化 Execution Contract 交给 Trae（国内首选）和 Claude Code（国际首选）执行。MCP 协议是事实标准，OSAI 应将自身能力封装为 MCP Server。

**05 AI Browser/Computer Use**：技术路线收敛为 Hybrid（Vision+DOM+Browser State）。OSAI 应基于 BrowserGym 可扩展框架 + Browser Run 运行时构建 AI Browser Research Framework，聚焦七层架构研究方法论，而非自研浏览器 Agent。Persistent Browser 四大问题（状态管理、可审计性、安全沙箱、并发冲突）尚未解决。

**06 AI 自主实验室**：已从概念进入真实实验室。利物浦机器人化学家 8 天完成 680 次实验（Nature）。Sakana AI Scientist 实现端到端科研自动化。瓶颈不在执行自动化，而在假设生成质量和因果解释。

**07 Skeptic/Red-Team Agent**：自我纠错有硬上限——Self-Refine 提升约 20% 但存在盲区和自我确认偏差。多 Agent 辩论和 Constitutional AI 证明外部化批判优于独自反思。高风险决策必须走 3 Agent 辩论而非单一批判。

**08 World Model/Knowledge Graph**：Cognitive Map = Entity + Temporal + Causal 三层融合。传统 KG 只回答"是什么"；Temporal KG（四元组+双时间戳）回答"何时"；Causal Graph（Decision→Action→Outcome 显式因果链）回答"为什么"。从 Experience DNA 直接构建图谱是最高效路径。

**09 Proactive Intelligence**：核心矛盾从"能不能主动"转向"什么时候不该主动"。完整 Interruption Policy 需经过 Signal→Context→Importance→Evidence→Actionability 五阶段过滤。通知"17 个更新"是反模式，输出可操作洞察才是正解。

**10 AI Safety/Permission Sandbox**：核心架构结论——**权限必须绑定 Task 而非永久绑定 Agent**。每个任务获得有时效、有范围、有成本上限的 Permission Ticket，任务结束自动撤销。绝对禁止 LLM→Unlimited Browser→Unlimited Filesystem→Production DB→Secrets 链路。

**11 Evaluation System**：Benchmark 只测任务成功，不测安全、恢复力、证据质量和学习提升。OSAI 需要 12 维评估矩阵，Safety 权重最高（0.15）并设硬门槛（<30 直接阻断）。

**12 Human+AI Collaboration**：范式从 Human-in-the-loop 迁移至 Human-on-the-loop。Mixed-Initiative 核心是动态分配自主权——人负责 Goal/Constraint/Judgment，AI 负责 Research/Planning/Execution。"建设性分歧"框架证明 AI 应在有证据时主动提出异议。

## 4. OSAI 差异化能力论证

OSAI 的三大核心差异化：

1. **Experience Engine（强改变机制）**：不是普通聊天记忆，而是将经历转化为结构化规则，注册到决策引擎强制执行。这是目前所有主流 Agent 系统都未实现的"强改变"。

2. **Research-to-Code Layer（不编码的编码层）**：不自建 Coding Agent，而是构建 Research→Architecture→Decision→Contract→Plan 的七层管道，通过 Contract 交给 Trae/Claude Code 执行。OSAI 的价值在研究和决策，不在编码。

3. **Permission & Evidence OS（任务绑定权限+全链路证据）**：权限绑定到 Task 而非 Agent，任务结束自动撤销。所有操作记录 Evidence，可追溯、可审计、可回滚。这是个人 AI OS 的安全基石。

## 5. 核心闭环

```
OBSERVE → REMEMBER → LEARN → RESEARCH → HYPOTHESIZE
   ↓                                            ↑
BECOME BETTER ← UPDATE EXPERIENCE ← REFLECT   │
                          ↓                      │
                       EVIDENCE → VERIFY → EXECUTE → PLAN
```

## 6. 与 Z Brand Core 的协作边界

```
OSAI: Research / Learn / Plan / Contract
        ↓ (Execution Contract + Evidence 要求)
Z Brand Core: Implement / Test / Execute
        ↓ (执行结果 + Evidence)
OSAI: Learn / Reflect / Update Experience
```

- **OSAI 不能直接篡改 ZBC 生产业务真相**
- **ZBC 不能吞并 OSAI 的研究职责**
- Contract 是唯一的交付通道，Evidence 是唯一的验证依据
