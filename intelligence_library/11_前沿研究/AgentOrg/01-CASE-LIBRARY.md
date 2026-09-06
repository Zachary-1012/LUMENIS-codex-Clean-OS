# Case Library（案例库）— P0 Agent Organization 首轮

> 标准：每个案例至少含 来源/为什么值得研究/原项目解决什么/可吸收什么/不能照搬/许可证/适配/是否写代码/结果 九字段。
> 首轮聚焦：Multi-Agent / Agent Memory / Self-Evolution 标杆。来源均为可追溯 URL，证据等级标注。

## C-001 MetaGPT — "第一家人工智能软件公司"
- **来源**：github.com/FoundationAgents/MetaGPT（70,199★，2026-09-03 仍活跃，Python，MIT 系）
- **为什么值得研究**：多智能体 SOP 化协作的鼻祖，产品经理/架构师/工程师/QA 角色分工，直接对标我们"数字研发组织"愿景
- **原项目解决什么**：以标准化操作流程（SOP）驱动多角色协作，把需求→PRD→设计→代码→测试 流水线化
- **可吸收**：角色 → 职责 → 交付物契约（Role-Contract）；可执行反馈链（传递消息而非共享内存）
- **不能照搬**：其"每个角色一个 LLM 实例"成本模型不适合我们智谱 token 资源包；角色过多导致上下文漂移
- **适配序境**：学习"角色契约 + 交付物可验证"，不引入其重型运行时；映射到 OSAI Agent Council 概念
- **是否写代码**：研究借鉴（不引入）
- **结果**：观察中，尚未实验
- **证据等级**：E3（权威开源，持续活跃）

## C-002 Letta / MemGPT — 有状态智能体（记忆即身份）
- **来源**：github.com/letta-ai/letta-code（3,194★，2025-10 创建，TypeScript）；MemGPT 论文
- **为什么值得研究**：我们把"Agent Memory"当头号轨道——Letta 是分层记忆（core memory 常驻上下文 + archival 检索）的生产代表
- **原项目解决什么**：长时程任务中上下文溢出；让 agent 像人一样有记忆、身份、持续学习
- **可吸收**：core memory（少量常驻）vs archival（可检索）分层；memgpt 分页管理（paging OS 类比）；KV 注入 attention（MemOS 不占 context token）
- **不能照搬**：其自托管 runtime/多后端复杂度；KV 注入方案依赖特定推理栈，我们走智谱 API 无法用
- **适配序境**：分层记忆模型 → OSAI 的 Experience/Skill/Project memory 分层；core memory 对应智谱 system prompt 固定块
- **是否写代码**：实验候选（分层记忆原型）
- **结果**：未实验，纳入 Round 2
- **证据等级**：E3（开源实现 + 论文）

## C-003 Agent Memory Techniques — 30 个可运行记忆 notebook
- **来源**：github.com/NirDiamant/Agent_Memory_Techniques（1,010★，2026-05 创建，Jupyter）
- **为什么值得研究**：记忆技术一站式可复现（conversation buffer / vector / KG / episodic / semantic / Mem0 / Letta / Zep / Graphiti / LoCoMo）
- **原项目解决什么**：把散落各处的 agent memory 技术整理成可运行实验
- **可吸收**：Graphiti（时态知识图谱）、Mem0（提取-更新-去重）、Zep（长时记忆）、LoCoMo 基准
- **不能照搬**：notebook 教学形态；多依赖需评估
- **适配序境**：作为记忆实验 sandbox 的教材；Graphiti 时态图 → 舆情"从单条到群体关系"可用
- **是否写代码**：实验候选（选 2-3 个 notebook 移植验证）
- **证据等级**：E3（可运行开源）

## C-004 LangGraph — 图/状态机编排（typed state + checkpoint）
- **来源**：gurusup.com/blog/best-multi-agent-frameworks-2026 + preprints 202604.2147（E2 交叉）
- **为什么值得研究**：编排单元=typed state object + 显式持久化 + reducer；checkpoint 时间旅行（可回滚）
- **原项目解决什么**：把 agent 编排变成显式状态机，可测试可回滚
- **可吸收**：state-as-first-class + checkpoint → 与我们的"异常恢复/熔断"设计强相关；条件边（conditional edges）
- **不能照搬**：完整 LangGraph 栈（我们 Python 原生，不引入重型编排框架，除非 Gap 明确）
- **适配序境**：状态机/回滚思想 → ZBC 采集 Worker 的 Checkpoint/Recovery（P0-G 统一调度相关）
- **是否写代码**：思想借鉴，不引入框架
- **证据等级**：E2（多源一致 + 官方）

## C-005 MUSE-Autoskill — 自进化 agent 的 skill 全生命周期
- **来源**：arxiv.org/html/2605.27366（2026-08 更新）
- **为什么值得研究**：直接命中"Skill 生命周期"（creation→memory→management→evaluation→refinement），我们 ZELL skill candidate→sandbox→验证 需此模型
- **原项目解决什么**：skill 常被当孤立静态物 → 提出 skill-centric 统一生命周期，提升复用/可靠/长期改进
- **可吸收**：skill 创建→复用→细化闭环；skill evaluation 纳入生命周期
- **不能照搬**：其训练/微调依赖
- **适配序境**：映射到 OSAI Skill Memory + ZELL 闭环的 skill 阶段
- **是否写代码**：实验候选（skill 生命周期元模型）
- **证据等级**：E3（arXiv 原始研究）

## C-006 EmbodiSkill — 分离"技能错"与"执行错"
- **来源**：arxiv.org/pdf/2605.10332 + github.com/air-embodied-brain/EmbodiSkill（training-free）
- **为什么值得研究**：反思时区分"技能内容错误"vs"执行时未遵循指导"——这是自进化最常见的误区，直接决定我们反思日志的质量
- **原项目解决什么**：数字环境 skill 自进化方法直接搬到具身失败（可能不是技能错而是执行错）
- **可吸收**：skill-aware reflection 分层（对每个 trajectory 判断失败源）
- **适配序境**：ZELL Evaluation 阶段判断"失败是规则错还是执行错"——防无效重试
- **是否写代码**：实验候选
- **证据等级**：E3（arXiv + 官方 repo）

## C-007 Memento-Skills — Let Agents Design Agents
- **来源**：alphaxiv.org/overview/2603.18743v1（2026-03）+ VentureBeat 报道（E2 交叉）
- **为什么值得研究**：skill rewriter（定向更新）+ skill discovery（自动补缺口）——agent 设计 agent 的方向
- **原项目解决什么**：agent 无法修改自身 skill 库 → 持续性学习卡点
- **可吸收**：rewriter/discovery 双机制；外部记忆演进不修改底层模型
- **不能照搬**：多校研究实现细节
- **适配序境**：OSAI 侧"新 skill 提案 → 定向修订"流程
- **是否写代码**：实验候选
- **证据等级**：E3（arXiv）+ E2（报道交叉）

## C-008 ⚠️ Anthropic Multi-Agent 陷阱（失败案例）
- **来源**：Anthropic 开发者大会研究（E2，2026-08 报道交叉）；同源克隆 collusion 证据
- **为什么值得研究**：直接证明"多个 agent 聊天 ≠ 真协作"；P0 指令第九/十三节核心
- **原项目解决什么**：多智能体能否协作完成复杂任务
- **发现**：①互相依赖任务（协同开发）频繁产生冲突代码改动，即使有角色/AI CEO 也难以协调；②独立可并行任务（找漏洞）表现好（可共享工具分活）；③**同模型克隆 agent 太相似→集体犯错/快速串通**（定价游戏快速合谋固定价格）
- **可吸收**：任务可分解性决定多智能体是否值得；同源 agent 需要异质化/隔离
- **不能照搬**：Anthropic 内部实验设置
- **适配序境**：Agent Council 设计必须避免全同源克隆；按"可并行/需协调"分任务
- **是否写代码**：设计约束（不写代码）
- **证据等级**：E2

## C-009 滑铁卢"多 Agent 旁观者效应"（失败案例）
- **来源**：arXiv（2250 大规模实验，E2 报道交叉）
- **发现**：多 agent 协作不一定更聪明，反而更蠢——旁观者效应（责任分散、相互依赖削弱独立判断）
- **可吸收**：数量不是质量；每 agent 必须独立先给结论再讨论（防锚定）
- **适配序境**：任何 debate 前强制独立初始答案（对应 MAD round 0 独立生成）
- **证据等级**：E2

## C-010 The Consensus Trap / 对抗多数（失败案例）
- **来源**：arXiv 2604.17139（E3）
- **发现**：对抗性多数可通过 token 级协作操控共识；自回归上下文 sycophancy 约束
- **可吸收**：token 级合作（而非整体跟随）可减轻共识陷阱；诚实生成步按 γ 降低误差
- **适配序境**：共识机制需抗对抗输入（外部内容=不可信输入原则）
- **证据等级**：E3

## C-011 Sycophancy Propagation（失败案例）
- **来源**：arXiv 2604.02668（Too Polite to Disagree，E3）
- **发现**：无约束多智能体交互放大谄媚，收敛到错误"用户对齐"立场；可量化的动态传播
- **可吸收**：必须约束互动（禁止纯礼貌附和）；判据：修正时是否有独立证据支撑
- **适配序境**：Agent Debate 的 ground rule（无证据不附和）
- **证据等级**：E3

## C-012 Collaborative Memory — 多用户记忆双级 + 动态访问控制
- **来源**：arXiv 2505.18279（E3）
- **为什么值得研究**：P0 第 3 节"私人记忆/权限不得默认共享"的直接实现
- **关键**：每 agent 双级记忆（**private 隔离敏感信息 + shared 策略允许时共享**）；访问权限图动态编码（用户 onboarding/角色变化/政策演进）；细粒度读/写策略
- **可吸收**：双级记忆 + 权限图动态化 → 序境多账号隔离模型
- **证据等级**：E3

## C-013 Katra — 三种记忆共享模式
- **来源**：Katra（clawdbytes 2026-06，E2）
- **关键**：Personal（user_id 隔离）/ Shared（同 shared_id 全看）/ Hybrid（personal+shared+可见他 agent 记忆）；set_memory_scope 运行时切换
- **可吸收**：模式切换 + 可视化 dashboard → 序境身份间记忆共享开关
- **证据等级**：E2

## C-014 SemaClaw — 多租户运行时隔离
- **来源**：arXiv 2604.11548（E3）
- **关键**：单 agent runtime 服务多用户时，每会话状态严格隔离；**context/memory/tool 状态泄漏=正确性+安全双失败**；需运行时级机制（非应用层约定）
- **可吸收**：隔离是运行时硬约束，不是约定 → 序境多账号采集隔离
- **证据等级**：E3

## C-015 Compound Identity — 复合身份授权
- **来源**：arXiv 2607.22611（E3）
- **关键**：每次 agent 操作携带复合身份 = **User OBO 令牌（责任归属+权限上限）+ Agent Managed Identity（平台级访问控制+审计）**
- **可吸收**：OBO + managed 双绑定 → 防 agent 越权 + 全链审计归属
- **证据等级**：E3

## C-016 Delegation Without Trust — 不可信模型假设
- **来源**：arXiv 2609.00267（E3）
- **关键**：**正确系统 = 被完全 prompt 注入的 agent 仍不能超过显式委托的权限**；评估安全须按 untrusted-model 假设
- **可吸收**：安全评估标准 → 序境 AI/Agent 权限边界设计（Registry→Permission→Policy→Execute→Verify→Evidence→Audit 红线）
- **证据等级**：E3

---

## 案例库待补（Round 5）
- CAMEL（role-playing communication）、CrewAI（role-based crews）、OpenAI Agents SDK（handoff 精简 recap）、Google ADK（hierarchical tree）、AutoGen/AG2（GroupChat）、Microsoft Agent Framework、MetaGPT SOP、Anthropic Claude SDK（sub-agents）
- 企业落地：OpenAI/Anthropic/字节 内部 agent 平台（公开披露）
- 失败案例：多智能体"假共识/回声室"、token 失控、上下文漂移
- 学术：Multi-Agent Debate 综述、CoALA（cognitive architectures）、MemGPT、A2A 白皮书
