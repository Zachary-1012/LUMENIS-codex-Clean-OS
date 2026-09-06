# P0 研究地图（Research Map）— Agent Organization

> 依据：`00-GOVERNANCE/AUTONOMOUS-RND-DIRECTIVE-P0-P1-2026-09-04.md`（P0 自主研究总指令）
> Owner：OSAI（研究侧）｜ 状态：ACTIVE / 持续演进 ｜ 首轮：2026-09-04
> 头号轨道：**Multi-Agent / Agent Memory / Agent Debate / Self-Evolution**
> 证据等级：E0 未验证 ｜ E1 单源可复核 ｜ E2 多源一致 ｜ E3 权威/原始 ｜ E4 经系统验证

## 一、轨道总览（Round 1 头号轨道）

| 轨道 | 子方向 | 状态 | 关键问题 | 本轮证据 | 反哺价值 |
|---|---|---|---|---|---|
| **T1 Multi-Agent** | 拓扑/编排/协作/委派/交接/A2A | 🟢 Round3 深挖完成 | 拓扑即架构决策？Supervisor vs Mesh vs Hierarchical 何时用？ | E3：LLM-Based Autonomous MAS Survey；E2：2026 多框架对比 + **编排判据**（Supervisor 3-8 agent 确定性；Hierarchical 15+ agent/异质域/worker>6） | 高：序境生产 70% 场景走 Supervisor 门控，与工业共识一致；**Hierarchical 升级判据已定** |
| **T2 Agent Memory** | Private/Shared/Project/Episodic/Semantic/Procedural/Long-horizon | 🟢 研究中 | write-manage-read 循环？写路径为何最易失败？7 层记忆？ | E3：arXiv 2606.06448（memory 系统分类：long-context/external/memgpt）；E2：write path 是最大失败点 | 高：反哺舆情记忆/知识库的写入校验与分层 |
| **T3 Agent Debate** | Debate/Consensus/Critic/Adversarial/Conflict resolution/Evidence-based decision | 🟢 Round2 深挖完成 | 共识算法怎么选？如何防 sycophancy/共识崩溃？Debate 何时优于自校正？ | E3：Debate vs Vote(2508.17536)；HCP-MAD(2604.09679 渐进式)；Sequential Consensus Wald-SPRT(2605.19193)；**失败模式**：Sycophancy 85.5% 从众/Contextual fragility 70%/Consensus collapse 32.3 点(CAIS 2026)；E3：CoALA 记忆分类 | **高（关键警示）**：盲目加 Debate 可能因同源谄媚更糟；必须异质+证据门+early stopping |
| **T5 Multi-User Agent**（新增 Round 4） | 多用户/多账号/Personal/Shared/Team/用户隔离/共享项目 | 🟢 Round4 首研 | 私人记忆/权限如何不默认共享？多用户共同项目如何协同？ | E3：Collaborative Memory 双级记忆+动态访问控制(2505.18279)；Hierarchical Memory 三层次(privacy-efficiency)；SemaClaw 多租户运行时隔离；Katra Personal/Shared/Hybrid 模式；Memori process_id 记忆分人 | **高（直接对应 P0 第 3 节）**：序境多账号/多身份隔离设计依据 |
| **T6 Agent Identity**（新增 Round 4） | Agent ID/Role/Capability/Permission/Trust/Decision history | 🟢 Round4 首研 | Agent 如何成为一等公民身份？权限如何动态作用域？ | E3：AI identity 三层声明(AI Identity Standards)；Compound Identity=User OBO+Agent Managed(2607.22611)；AIP IBCT 调用绑定令牌；Delegation Without Trust(untrusted-model 假设)；信任等级 L1-L4 | **高**：防 agent 越权 + 审计归属（零号序列 AI 受控红线） |

## 二、轨道拆解（子方向 + 问题清单）

### T1 Multi-Agent（Round 3 深挖完成）
- 拓扑：Chain（确定性 pipeline）/ Star-Supervisor（集中协调，70% 生产首选）/ Mesh-Debate（头脑风暴/校验）/ Tree-Hierarchical（多领域）/ Dynamic（学术前沿）
- 协调：MCP（工具）× A2A（Agent 协调）为 2025-2026 标准栈（互补非竞争）
- 状态单元：LangGraph typed state + checkpoint 时间旅行 vs CrewAI role-based vs OpenAI handoff vs AutoGen GroupChat
- 交接：OpenAI handoff 传"精简 recap"而非全历史 → 上下文污染控制
- 统一分类（Survey）：Architecture Paradigms / Coordination Mechanisms / Planning Strategies / Evaluation Metrics
- **编排选型判据（Round 3）**：
  - Supervisor：下一步依赖上一步结果（think between turns）；3-8 agent 确定性工作流；同质 agent 池（如并行处理）
  - Hierarchical：15+ agent 企业级；异质领域（每域专用工具/推理，如 legal/finance/tech）；worker>6 或同域 worker 需共享上下文（避免污染顶层 state）；**核心收益=隔离性**（Microsoft）
  - 序境现状：任务调度层（非多 Agent 编排）——PlatformSchedulePlanner 每平台 decider + ShadowPlanner 建议门控；**升级 Hierarchical 触发条件**=agent>6 或出现明确异质域（舆情/营销/合规/工程），否则不升级；已同步 ZBC TWIN_EXECUTION_GATE
- **编排落地深化（Round 4）**：
  - **有向树 + 状态隔离**：Hierarchical 通信仅 parent↔child；每域 supervisor 拥有子树 state（分层作用域隔离）；root orchestrator 路由到域 supervisor，每域 3-5 specialist workers（Augment Code）
  - **域自治闭环**：每自治域保留独立闭环管理；Orchestrator 只做跨域任务分发/状态同步/进程调度（IETF cross-domain）
  - **subagent 严格隔离**：local memory/state、mission-scoped、用完即弃，防污染父级（SubAgenticAI FLA）
  - **健康指标**：Supervisor:Worker token 比健康区 **0.2-0.3**；>0.4 = router 退化（在做 worker 该做的推理）→ 下放任务（channel.tel 2026）——可落地为序境编排监控指标
  - **实现参考**：LangGraph 多级=compile supervisor 嵌套 / subagents flatten-or-nest；CrewAI hierarchical=manager 动态分配
- Capability Discovery 趋势（2026）：agent 从"全装所有工具"转向"从批准 catalog 搜索-选择-验证所需能力"——与序境 capabilities registry 方向一致

### T2 Agent Memory
- 三范式（arXiv 2606.06448）：Long-context（上下文即记忆）/ External（外部检索注入）/ MemGPT 分层（context+DB+vector+cold archive + 学习控制）
- 读写特性：write 突发且上下文相关（工具调用后整合/去重/重写摘要）；read 预测性（query embedding 预取）；consistency 语义性
- **写路径是最易失败处**（检索再好，存储已污染仍答错）→ 写路径工程投入 > 读路径
- 七层记忆（temporal edges）：session/work/episodic/semantic/procedural/user profile/org
- Event-sourced memory（MAN+ESM）：state = append-only event log 投影，不可变/可审计/可回滚
- Privacy：隐私保护的多智能体记忆 + Bayesian Trust Defense（arXiv 2603.02240）

### T3 Agent Debate（Round 2 深挖完成）
- 流程：提出 → 质询 → 证据 → 验证 → 修正 → 决策（P0 指令核心）
- **决策协议谱系**：Debate（迭代交换修正）vs Vote（投票聚合）；共识层级 majority(>50%)/supermajority(>66%)/unanimity；HCP-MAD 渐进式（简单任务 pair-debate 早期停止，复杂任务扩协作）；Sequential Consensus 用 Wald-SPRT 序贯概率比做自适应轮数/终止；WISE-Dawid-Skene 概率化聚合（按 agent 可靠性加权）
- **⚠️ 三大失败模式（CAIS 2026 解构，直接影响 IC-005 设计）**：
  1. **Sycophantic conformity 谄媚从众**：agent 不加批判采纳多数答案，modal adoption 最高 85.5%
  2. **Contextual fragility 上下文脆弱**：peer 论证破坏原本正确推理，脆弱率最高 70%
  3. **Consensus collapse 共识崩溃**：多数投票丢弃生成池中已有正确答案，oracle gap 最高 32.3 点
  - MAD 消耗 2.1-3.4x tokens，与隔离自校正同等或更低准确率；同源克隆 agent 倾向快速串通/合谋（Anthropic 定价游戏）；无约束交互放大 sycophancy（arXiv 2604.02668）；对抗多数陷阱（2604.17139）
- **反哺结论**：Debate 不是默认更优；**必须 异质模型/角色隔离 + 证据门 + early stopping（Wald-SPRT/HCP-MAD）+ 独立 Critic 不与决策者同源**
- MARO：Multi-Agent Reward Optimization，社会交互结果分解为逐行为学习信号（强化价值信号）

### T4 Self-Evolution（Round 3 深挖完成）
- **Skill 生命周期**：MUSE-Autoskill（creation→memory→management→evaluation→refinement）；EmbodiSkill（skill-aware reflection，区分技能错/执行错）
- **Skill 版本化/回滚（生产实操）**：技能当软件包管——版本号、不可变版本、回滚、内容哈希、审计（Microsoft Foundry skills: 每次更新新建不可变版本→测试→promote default_version；agent-skills/skill-mcp: versions/rollback CLI）
- **Experience→Skill 泛化**：
  - Skill-Pro（Skill-MDP）：把被动 episodic 叙述转成可执行技能，定义 activation/execution/termination 三条件（非参数）
  - SkillComposer：演化三能力 Skill Create（提取）→ Skill Merge（合并相似→泛化）→ Skill Improve（细化任务特定）
  - ERL / Evolving-RL / OPID：反射启发式/跨策略可迁移技能/分层 hindsight skills 路由
  - ProcMEM：episodic→procedural（"下次该怎么做"而非流水账）
- **⚠️ 负迁移警示**：模型生成技能平均提升性能，但造成非平凡负迁移（因 extractor/consumer 而异）→ 需要 meta-skill（提取原则）降低负迁移——**技能必须经测试/评价才成为正式能力**（P0 指令第七节）
- **反哺结论**：skill 管理 = 版本 + 回滚 + 审计 + 测试后 promote + 防负迁移（复用前验证）

### T2 Agent Memory（补 CoALA 认知架构）
- **CoALA（Sumers 2024，E3）**：working memory + 长期记忆三分（episodic 带时间戳经历 / semantic 世界与自身知识 / procedural 技能=权重内隐+代码显式）；结构化动作空间（internal: reasoning/retrieval/learning；external: grounding）；planning→execution 决策循环
- 实践要点：episodic 存"解释后的话语"（语义解释）而非原始日志；LTM 用 vector+RAG；procedural 记忆对应 ZELL 的 skill

## 三、研究地图管理
- 新增高价值方向：加入本表并说明依据（证据等级）
- 降级/关闭方向：说明原因（低价值/无进展/已被替代）
- 每轮产出必须进 `04-IMPROVEMENT-QUEUE.md`（反哺判断）或保留研究层
- 涉及生产：Research → Evidence → Candidate → Impact/Risk → Minimal Impl → Test → Regression → Audit → Release Gate

## 四、下一轮（Round 5）计划
- T5/T6 深挖落地：序境多账号/多身份隔离设计原则（Collaborative Memory 双级 + Compound Identity）
- IC-005 研究侧原型：Critic 双审（5 约束）在 sandbox 验证
- 记忆分层原型（IC-001 写路径校验）
- 新方向候选：Long-Horizon Agent（长时间运行稳定性）、Human Governance（HITL 审计）
