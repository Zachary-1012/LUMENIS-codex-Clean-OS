# 深度学习 Cycle 登记簿（Deep Learning Cycle Log）

> 依据《序境/00-GOVERNANCE/AI_CONTINUOUS_DEEP_LEARNING_V1.md》（AI 持续深度学习与研发增强指令）。
> 规则：每天至少 3 次独立 Deep Learning Cycle；学习成果按模板登记；验证有效沉淀为 Capability；
> 外部方法必须过 Compatibility/Architecture/Security/Performance/Product Boundary 检查，只允许 KEEP/ADAPT/MERGE/EXPERIMENT/REJECT。
> 本登记簿为双库共享规范（ZBC 生产侧 / OSAI 研究侧），OSAI 研究区保留详细雷达与改进队列。

---

## Cycle A — Context Engineering / 长任务收敛 / Harness（2026-09-04）

- **主题**：Reasoning/Planning（指令五：长任务 Agent 收敛与上下文管理）
- **研究对象**：Anthropic Context Engineering、Chroma Context Rot 研究、CMU/耶鲁/Amazon Agent Harness Engineering Survey（ETCLOVG）、LangGraph Persistence、微软 ACE 框架、Nous Hermes Agent、AI 原生多仓库协作
- **来源**：51CTO、掘金、腾讯新闻 2026 深度文（E2 多源），来源 URL 见 OSAI 技术雷达 §6
- **核心发现**：
  1. Context Rot 是架构性衰减（非容量问题），换大模型/长窗口不解决；对策=JIT 检索+Compaction+结构化笔记+子 Agent 隔离
  2. 长任务单步 99%×100 步=36.6% 成功率；需 Planner/Checkpoint/Compaction/Human-in-the-loop/业务验证器
  3. Harness Engineering > 模型：换模型收益 < 改 Harness（ETCLOVG 七层：E/T/C/L/O/V/G）
  4. 状态外化：进度放文件不放上下文（feature-list.json/progress.txt 恢复现场）
  5. ACE 框架（Generator/Reflector/Curator 上下文自进化）+ Hermes 双驱（后台 Reviewer 提炼 Skill）——与序境"学习→沉淀→反哺"指令高度同构
- **适用能力**：长任务推进（多轮研发/采集/报告）上下文治理；Checkpoint 断点续跑；Observability 对照自检
- **与代码库关系**：kos_ops HCG 门控状态机已符合"长任务收敛+人工介入"共识；双库+KOS 台账已是状态外化；可补 Checkpoint
- **实验**：无（研究侧，未改生产代码）
- **决策**：ADAPT（方法论借鉴，IC-006 Context 治理三原则 / IC-007 Checkpoint 入改进队列，研究侧先原型）
- **采用位置**：OSAI 03-RESEARCH/P0-AGENT-ORG/03-TECHNOLOGY-RADAR.md §6（5 项）；04-IMPROVEMENT-QUEUE.md IC-006/IC-007
- **影响范围**：研发流程（Context 治理）；未来采集/分析任务（Checkpoint）
- **风险**：低——研究侧沉淀，未触碰生产 Truth
- **Evidence**：OSAI 推送 `8cc2df2`（雷达+队列 42 行）；本登记簿 ZBC 推送
