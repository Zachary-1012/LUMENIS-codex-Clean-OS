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
---

## Cycle B — Spec 驱动 / 自动修复 / 复用判定（2026-09-04）

- **主题**：Coding / Code Generation / Debugging（指令五方向二）
- **研究对象**：Spec-Driven Development、Harness 三层反馈闭环（OpenAI）、复用判定（代码知识库+RAG）、系统化 Debug 方法论、失败案例→eval dataset、多模型互审
- **来源**：51CTO、腾讯、掘金 2026 深度文（E2 多源），来源 URL 见 OSAI 技术雷达 §7
- **核心发现**：
  1. SDD：No Spec No Code / Spec is Truth / Reverse Sync；精炼规格降低代码错误率 50%
  2. 复用判定：开发前先探索已有实现，防重复造轮子——直接支撑 Canonical Capability 的 Reference Scan
  3. Harness 三层反馈闭环：死规矩机器判 / 运行判 / 软标准 AI 判 + 后台 GC 式清理
  4. Debug 铁律：复现→最小化→单变量→回归测试；禁止未确认根因直接改码
  5. 失败案例→eval/回归用例沉淀闭环
  6. 多模型互审规避单模型盲区
- **适用能力**：Canonical Capability Registry（复用判定）；Evidence/回归体系（失败案例沉淀）；AI 层（第二模型 review）
- **与代码库关系**：序境已有 Contract/Gate/Evidence 体系与 SDD 同构；Capability Registry + Reference Scan 已落地；本 Cycle 确认方向正确并补 eval 沉淀/互审
- **实验**：无（研究侧，未改生产代码）
- **决策**：ADOPT（复用判定/失败沉淀——方法论确认）；ADAPT（SDD Reverse Sync、Debug 红线、互审）
- **采用位置**：OSAI 技术雷达 §7（6 项）；改进队列 IC-008/IC-009
- **影响范围**：研发流程（复用判定红线）；Evidence/回归（失败沉淀）
- **风险**：低——研究侧沉淀
- **Evidence**：OSAI 推送（雷达+队列）；本登记簿双库同步
---

## Cycle C — Agent Tool Use / 死循环防护 / 可观测性 / 成本治理（2026-09-04）

- **主题**：Agent / Tool Use / Context / Long-horizon Execution（指令五方向三）
- **研究对象**：Agent 死循环根因与防护（OpenHands/LangGraph/OpenAI Guardrails）、Token 成本爆炸治理（火山引擎）、Agent 可观测性三支柱、零信任 Agent（OWASP）、AI 成本治理（Tokenomics）、Agent 审计玻璃箱（NIST AI RMF）
- **来源**：InfoQ、51CTO、掘金、腾讯 2026 深度文（E2 多源），来源 URL 见 OSAI 技术雷达 §8
- **核心发现**：
  1. 死循环 5 种防护：Max Iteration（RemainingSteps 优雅收尾）/ Loop Detection / Human Approval / Guardrails / 预算早停
  2. Token 成本爆炸：generate_summary 无限循环案例——修复=终止指令+最大迭代围栏+预算早停+失败案例入回归集
  3. 可观测性三支柱：日志（JSON）/ 追踪（Trace session→step→event）/ 指标；动态采样
  4. 零信任 Agent：不信任模型输出/不允许无限循环/不依赖模型自我验收
  5. Tokenomics：总成本=固定前缀+会话历史+检索+工具往返+输出；无效 Token 30-50%；模型分层路由降 18-20%
  6. Agent 审计：唯一身份+最小权限+委托链+统一 trace_id
- **适用能力**：ai_channel 预算早停；采集/报告 Observability trace；成本看板
- **与代码库关系**：ai_channel 已有熔断+HALF_OPEN；HCG 人工门控+采集安全 Gate 已符合零信任共识；智谱/搜索/视觉分层路由已落地（验证策略正确）
- **实验**：无（研究侧，未改生产代码）
- **决策**：ADOPT（零信任/Tokenomics——策略确认）；ADAPT（预算早停、trace 三层、死循环围栏）
- **采用位置**：OSAI 技术雷达 §8（6 项）；改进队列 IC-010/IC-011
- **影响范围**：AI 通道（预算/早停）；Observability（trace）；成本治理（看板）
- **风险**：低——研究侧沉淀
- **Evidence**：OSAI 推送（雷达+队列）；本登记簿双库同步
---

## Cycle D — LLM-as-a-Judge / 轨迹级评测体系（2026-09-04）

- **主题**：Evaluation / Benchmark / LLM-as-a-Judge（指令十一方向补充）
- **研究对象**：MOBILEJUDGEBENCH（arXiv 2608.11434）、Vertex AI Agent-as-a-Judge、智能体质量飞轮
- **来源**：arXiv、Google Discuss（E2），URL 见 OSAI 技术雷达 §9
- **核心发现**：
  1. 简单 baseline judge + 强 backbone 优于复杂 judge pipeline（LLM 主干是主要驱动）
  2. 评估从最终 Output 扩展到轨迹级（计划/工具选择/权限/中间状态/成本延迟）
  3. 不同后端失败画像相反（保守 vs 宽松），源于 precision-recall 特性
- **适用能力**：自建 Eval 基线；ai_channel 输出质检
- **与代码库关系**：与 IC-011（trace 三层）联动——评估消费 trace
- **实验**：无（研究侧）
- **决策**：ADAPT
- **采用位置**：雷达 §9；队列 IC-012
- **风险**：低
- **Evidence**：OSAI 推送；本登记簿双库同步

---

## Cycle E — 代码库理解 / 意图检索 / Capability Discovery（2026-09-04）

- **主题**：Repository Understanding / Code Search / Capability Discovery（指令十一方向补充）
- **研究对象**：Codebase Insights（MCP）、CocoIndex Code / SymDex / GitNexus
- **来源**：GitHub、Codex CLI 深度文（E2），URL 见 OSAI 技术雷达 §10
- **核心发现**：
  1. 文本搜索在知道名字时有效，但智能体通常不知道——需按职责/意图搜索
  2. 四层索引：LSP 导航 + SQLite 持久符号/引用 + LLM 摘要 + 意图向量检索
  3. AST-aware chunking 降 70% token；增量 re-index 秒级
  4. MCP schema bloat tax：每 server 每轮 2000-4000 token
- **适用能力**：Reference Scan / Capability Discovery / 复用判定（Canonical Capability）
- **与代码库关系**：直接支撑"先盘点再映射、能复用不重建"；双库可建轻量索引
- **实验**：无（研究侧）
- **决策**：ADAPT
- **采用位置**：雷达 §10；队列 IC-013/IC-015
- **风险**：低
- **Evidence**：OSAI 推送；本登记簿双库同步

---

## Cycle F — 自进化 Agent / 持久记忆 / 技能沉淀（2026-09-04）

- **主题**：Self-Evolving Agent / Self-Correction / Memory / Skill（指令十一方向补充）
- **研究对象**：Hermes Agent（Nous Research）、Self-Evolving AI Agents Survey
- **来源**：Hermes 官方中文站、HundredTabs、Survey（E2），URL 见 OSAI 技术雷达 §11
- **核心发现**：
  1. GEPA 自我进化：类反向传播优化 prompt，100-500 次策略迭代（vs 传统 RL 上万次）
  2. 持久记忆：MEMORY.md（事实+教训）+ USER.md（偏好），SQLite FTS5 + LLM 摘要 + 注入安全扫描
  3. 技能自动沉淀：完成复杂任务自动提炼技能文件，渐进式披露 Level 0/1/2
  4. 进化三定律：Endure（稳）→ Excel（优）→ Evolve（自主）
  5. 安全：指令审批/Docker 沙箱/路径防护/SSRF 缓解/凭证管理，0 CVE
- **适用能力**：我们的"学习→沉淀→反哺"闭环（已同构）；Prompt/策略版本管理；知识资产披露
- **与代码库关系**：技术雷达/改进队列/Cycle 登记簿即持久记忆+技能沉淀；与 Contract/Gate 体系同构
- **实验**：无（研究侧）
- **决策**：ADOPT（方法论确认：三定律、学习闭环）；ADAPT（渐进披露、GEPA 迭代思路）
- **采用位置**：雷达 §11；队列 IC-014
- **风险**：低
- **Evidence**：OSAI 推送；本登记簿双库同步
