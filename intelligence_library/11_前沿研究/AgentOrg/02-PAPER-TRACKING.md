# Paper Tracking（论文追踪）— P0 Agent Organization

> 规则：每篇回答 它解决什么/怎么解决/为何有效/限制/能否重实现/是否值得进入研发体系。
> 首轮收录 2026 年最新 + 综述。持续追加。

## PT-001 LLM-Based Autonomous Multi-Agent Systems: A Comprehensive Survey
- **来源**：nanoagentteam.github.io/assets/autonomous-multi-agent-survey.pdf（E3 综述）
- **解决什么**：多智能体系统无统一分类
- **怎么解决**：四维度统一分类法——(1) Architecture Paradigms（组织模式/控制结构/专精化）、(2) Coordination（MCP/ACP/A2A/ANP 通信 + 协调策略 + consensus 算法）、(3) Planning（任务分解/分层规划/外部模块）、(4) Evaluation（任务性能/协调质量/系统指标）
- **为何有效**：把架构、通信、规划、评估放同一框架，可直接对照我们系统找 Gap
- **限制**：综述性，不提供实现
- **能否重实现**：分类法可落地为我们的能力/架构 Gap 检查表
- **是否值得进入体系**：**是** → 作为 Architecture Gap Analysis 的分类基准

## PT-002 Multi-Agent LLM 系统架构全景调研（2023–2026）
- **来源**：edison-a-n.github.io/2026/04/19/multi-agent-architecture-survey/（E2）
- **解决什么**：生产落地中拓扑如何选
- **关键结论**：**拓扑即架构决策**——Chain（确定性）/ Star-Supervisor（集中协调，70% 生产首选）/ Mesh-Debate（头脑风暴/校验）/ Tree-Hierarchical（多领域）/ Dynamic（学术前沿）；"先简单后复杂"是 Anthropic/OpenAI/Google 共识
- **对序境**：当前 ShadowPlanner 门控 = Star/Supervisor 模式，**符合工业共识**，无需推翻；未来 Hierarchical 按需
- **是否值得进入体系**：**是** → 拓扑决策树沉淀

## PT-003 Agent Memory: Characterization and System Implications of Stateful Long-Horizon Workloads（arXiv 2606.06448）
- **解决什么**：长时程有状态工作负载下 agent memory 的系统性影响
- **关键**：三范式分类（Long-context / External / MemGPT-tiered）；memory 读写的系统瓶颈
- **对序境**：记忆分层决策依据
- **是否值得进入体系**：**是**（记忆架构参考）

## PT-004 Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers（arXiv 2603.07670）
- **解决什么**：自主 agent 记忆机制与评估
- **关键**：Pattern C（tiered memory with learned control）= MemGPT/Age 主流；检索管道是生产工作马；评估（ContextRelevance/ContextRecall/staleness）
- **对序境**：记忆评估指标可进 Evaluation System
- **是否值得进入体系**：**是**

## PT-005 EmbodiSkill: Skill-Aware Reflection for Self-Evolving Embodied Agents（arXiv 2605.10332）
- **解决什么**：技能自进化在具身场景失效（错误归因错位）
- **关键**：**区分技能内容错误 vs 执行未遵循指导**；training-free；对 trajectory 逐条 skill-aware reflection
- **对序境**：ZELL Evaluation 错误归因原则
- **是否值得进入体系**：**是** → 反哺 ZELL

## PT-006 MUSE-Autoskill: Self-Evolving Agents via Skill Creation, Memory, Management, and Evaluation（arXiv 2605.27366）
- **解决什么**：skill 孤立静态化 → 复用/可靠/长期改进不足
- **关键**：skill-centric 统一生命周期 creation→memory→management→evaluation→refinement
- **对序境**：Skill Memory 生命周期模型
- **是否值得进入体系**：**是**

## PT-007 MARO: Learning Stronger Reasoning from Social Interaction
- **来源**：github.com/voltagent/awesome-ai-agent-papers（2026-09 更新，E2）
- **解决什么**：社会交互如何提升推理
- **关键**：Multi-Agent Reward Optimization，把多智能体社会交互结果分解为逐行为学习信号
- **对序境**：Agent Debate 的价值信号设计
- **是否值得进入体系**：**是**（T3 Debate 依据）

## PT-008 Privacy-Preserving Multi-Agent Memory with Bayesian Trust Defense（arXiv 2603.02240）
- **解决什么**：多智能体共享记忆的隐私保护
- **关键**：贝叶斯信任防御，对抗记忆污染
- **对序境**：T2 Private/Shared memory 隔离 + 记忆污染防护（对应 P0 "私人 Memory 不得无权限访问"）
- **是否值得进入体系**：**是**

## PT-009 Event-Sourced Memory（MAN+ESM）
- **来源**：multi-agent-network-event-sourced-memory（生产级架构博客，E1-E2）
- **解决什么**：多智能体协调的可审计状态
- **关键**：state = append-only event log 投影（不可变/签名/可回滚）——Fowler/Kreps event sourcing 应用到多智能体
- **对序境**：审计闭环 + 回滚（与 ZBC unified_logger 升级方向相关）
- **是否值得进入体系**：**评估中**（复杂度 vs 收益）

## PT-010 Debate or Vote: Which Yields Better Decisions in Multi-Agent LLMs?（arXiv 2508.17536）
- **解决什么**：MAD（迭代辩论）vs 投票决策 哪个更好
- **关键**：round-based MAD 协议；agent 独立初答→互读→修订→重复
- **对序境**：决策协议选型依据
- **是否值得进入体系**：**是**

## PT-011 Heterogeneous Consensus-Progressive Reasoning (HCP-MAD)（arXiv 2604.09679）
- **解决什么**：简单任务 debate 浪费算力
- **关键**：三阶段渐进式——异质双 agent 快速共识验证（early stopping）→ 配对辩论自适应停止 → 复杂任务扩协作
- **对序境**：**成本控制关键**：简单判定（如 verify_taikoo_location）用轻量 pair 快停，不重辩论
- **是否值得进入体系**：**是**（IC-005 直接依据）

## PT-012 Sequential Consensus (Wald-SPRT)（arXiv 2605.19193）
- **解决什么**：debate 该辩论几轮
- **关键**：序贯概率比检验（SPRT）动态决定继续/终止，硬上限 R_max 防失控
- **对序境**：辩论轮数自适应 + 熔断（对应我们"异常恢复必须有次数上限"）
- **是否值得进入体系**：**是**

## PT-013 The Cost of Consensus（CAIS 2026）
- **解决什么**：同源多智能体 debate 是否值得
- **关键**：**三大失败模式解构**——sycophantic conformity（modal adoption ≤85.5%）、contextual fragility（脆弱率 ≤70%）、consensus collapse（oracle gap ≤32.3 点）；MAD 2.1-3.4x tokens 且不优于隔离自校正
- **对序境**：**最大警示**——IC-005 必须防此三模式
- **是否值得进入体系**：**是（核心）**

## PT-014 Too Polite to Disagree: Sycophancy Propagation（arXiv 2604.02668）
- **解决什么**：多智能体谄媚传播
- **关键**：无约束交互放大 sycophancy，收敛错误用户对齐立场
- **对序境**：debate ground rule（无证据不附和）
- **是否值得进入体系**：**是**

## PT-015 CoALA: Cognitive Architectures for Language Agents（arXiv 2309.02427）
- **解决什么**：语言 agent 无系统框架
- **关键**：modular memory（working + episodic/semantic/procedural 长期三分）、结构化动作空间、planning→execution 决策
- **对序境**：T2 记忆分层 + OSAI Experience/Skill 组织的理论基准
- **是否值得进入体系**：**是（核心）**

## PT-016 Not Just RLHF: Why Alignment Alone Won't Fix Multi-Agent Sycophancy（arXiv 2605.12991）
- **解决什么**：sycophancy 是否纯 RLHF 造成
- **关键**：预训练基座同样（甚至更高 yield）；定位到窄中层 attention 窗口（MLP）承担因果权重——**架构性脆弱，非对齐可修**
- **对序境**：防 sycophancy 不能靠 prompt 提示，需结构性隔离
- **是否值得进入体系**：**是**

## PT-017 Skill-Pro: Learning Reusable Skills from Experience via Non-Parametric PPO（arXiv 2602.01869）
- **解决什么**：agent 反复场景仍 on-the-fly 重推（计算冗余/不稳定）
- **关键**：Skill-MDP 把被动 episodic 叙述转成可执行技能，定义 **activation/execution/termination 三条件**（非参数，无权重更新）
- **对序境**：Skill 的"何时启用/如何执行/何时结束"三元组规范
- **是否值得进入体系**：**是**（skill 表达规范）

## PT-018 SkillComposer: Learning to Evolve Agent Skills（arXiv 2606.06079）
- **解决什么**：skill 只提取不演化
- **关键**：演化三能力——**Skill Create**（轨迹提取）→ **Skill Merge**（合并语义相似→泛化）→ **Skill Improve**（细化任务特定模式）；完整演化生命周期
- **对序境**：Skill Memory 的 merge/improve 环节（超越"只增不改"）
- **是否值得进入体系**：**是**

## PT-019 From Raw Experience to Skill Consumption（pith.science 系统研究）
- **解决什么**：模型生成技能何时有效
- **关键**：⚠️ 生成技能平均提升性能但**造成非平凡负迁移**（因 extractor/consumer 而异）→ 提出 meta-skill（提取原则）降低负迁移
- **对序境**：**技能必须经测试/评价才成为正式能力**（P0 第七节）——技能入库前验证
- **是否值得进入体系**：**是（核心警示）**

## PT-020 Experiential Reflective Learning (ERL)（arXiv 2603.24639）
- **解决什么**：agent 不利用过往交互，每次从零开始
- **关键**：反射任务轨迹+结果生成启发式 → 快速环境适应
- **对序境**：ZELL Learning 阶段的启发式沉淀
- **是否值得进入体系**：**是**

## PT-021 Evolving-RL（arXiv 2605.10663）
- **解决什么**：经验驱动自进化能力端到端优化
- **关键**：提取技能跨策略可迁移（45.5→60.4 提升），非训练策略专属
- **对序境**：skill 可迁移性验证
- **是否值得进入体系**：**评估中**

## PT-022 Collaborative Memory: Multi-User Memory Sharing with Dynamic Access Control（arXiv 2505.18279）
- **解决什么**：多用户 agent 记忆共享的隐私控制
- **关键**：双级记忆（private/shared）+ 动态访问权限图（onboarding/角色变化/政策演进）
- **对序境**：多账号隔离 + 共享项目协同的权限模型
- **是否值得进入体系**：**是（T5 核心）**

## PT-023 Hierarchical Memory Sharing in MAS（nanoagentteam）
- **解决什么**：记忆共享的隐私-效率权衡
- **关键**：三层次（private/shared/global）+ 形式化访问控制矩阵 + 隐私指标
- **对序境**：记忆分层 + 权限的数学化基础
- **是否值得进入体系**：**是**

## PT-024 SemaClaw: Harness Engineering（arXiv 2604.11548）
- **解决什么**：通用个人 agent 的多租户隔离
- **关键**：状态持久化/上下文生命周期/多租户隔离=工程三大难题；隔离需运行时机制
- **对序境**：多账号采集运行时隔离红线
- **是否值得进入体系**：**是**

## PT-025 Decentralized Granular Access Control（arXiv 2607.22611）
- **解决什么**：关键基础设施 agent 授权
- **关键**：复合身份 = User OBO 令牌 + Agent Managed Identity
- **对序境**：Agent Identity 双绑定模型（责任归属+权限上限）
- **是否值得进入体系**：**是（T6 核心）**

## PT-026 Delegation Without Trust（arXiv 2609.00267）
- **解决什么**：多 agent 系统的身份/授权/运行时治理实证缺口
- **关键**：untrusted-model 假设——被完全注入的 agent 仍不能越权；正确系统的判定标准
- **对序境**：AI/Agent 权限边界的验收标准
- **是否值得进入体系**：**是（核心红线）**

## PT-027 AI Identity: Standards, Gaps, Research Directions
- **解决什么**：agent 身份基础设施与自主 agent 性质错位
- **关键**：三层身份（Declaration 声明/…）；身份=连续关系非二元凭证
- **对序境**：Agent ID/信任/声明层设计
- **是否值得进入体系**：**是**

---

## 追踪队列（Round 2+）
- CoALA（Cognitive Architectures for Language Agents）
- A2A / MCP 协议白皮书与最新版
- Multi-Agent Debate 系统综述（多辩论变体：sequential/iterative/voting）
- AgentRxiv（并行 AI 研究实验室，+13.7% shared research）
- EvoTool（Tools-from-experience）
- Long-Horizon 稳定性基准（LoCoMo / τ-bench）
