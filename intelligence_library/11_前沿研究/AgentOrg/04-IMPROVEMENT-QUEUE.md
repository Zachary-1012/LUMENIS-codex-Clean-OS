# Improvement Candidate Queue（改进候选队列）— P0 Agent Organization 首轮

> 规则：研究结论主动判断是否反哺当前研发系统（不等人类下令）。
> 每项评分：Improvement Score =（Launch Acceleration + Reliability + Closure + Reuse + Maintainability + Performance）−（Risk + Complexity + Regression + Ops Cost）。
> 决策：**PROMOTE**（进最小化工程改造，过 Release Gate）/ **DEFER**（暂缓）/ **REJECT**（否决）。
> 边界：研究侧只产出 Candidate + 建议；生产改动必须走 Release Gate 且不擅自越过 Zero Sequence。

## IC-001 记忆"写路径优先校验"原则 → 舆情/知识库写入
- **来源**：E2/E3（Memory survey：写路径是最易失败处）
- **内容**：任何 agent/采集数据入库前增加写路径校验（去重/一致性/来源标注），而非只优化检索
- **反哺对象**：OSAI Knowledge / ZBC 知识库写入流程（研究侧先验证）
- **评分**：Reliability +3  Closure +2  Complexity −1  ⇒ **PROMOTE（研究侧先原型）**
- **状态**：入队，待原型

## IC-002 Star/Supervisor 拓扑与当前门控一致性确认
- **来源**：E2（拓扑即架构决策，70% 生产首选 Supervisor）
- **内容**：序境当前 ShadowPlanner 门控 = Supervisor 模式 → 记录为**已符合工业共识**，不推翻；未来多领域再评估 Hierarchical
- **反哺对象**：序境架构基线（无需代码改动）
- **评分**：Reuse +3  Risk −0  ⇒ **PROMOTE（仅文档化确认）**
- **状态**：已写入 Research Map T1

## IC-003 ZELL Evaluation 错误归因分层（技能错 vs 执行错）
- **来源**：E3（EmbodiSkill）
- **内容**：ZELL 闭环 Evaluation 阶段失败时先归因"规则/技能内容错误"vs"执行未遵循"，防无效重试
- **反哺对象**：OSAI learning-feed/ZELL 模板 Evaluation 阶段（研究侧）
- **评分**：Reliability +3  Closure +2  Complexity −1  ⇒ **PROMOTE（改 ZELL 模板）**
- **状态**：可立即执行

## IC-004 Skill 生命周期元模型（creation→memory→management→evaluation→refinement）
- **来源**：E3（MUSE-Autoskill）
- **内容**：OSAI Skill Memory 采用该生命周期，与 ZELL skill candidate→sandbox→验证 对齐
- **反哺对象**：OSAI 研究侧 Skill Memory（先建元模型，不碰生产）
- **评分**：Reuse +3  Maintainability +2  Complexity −1  ⇒ **PROMOTE（研究侧元模型）**
- **状态**：入队

## IC-005 AI 日报验证升级为 Critic 双审（Debate 模式）→ **重评（Round 2 证据）**
- **来源**：E3（T3 Debate：HCP-MAD 渐进式 / Wald-SPRT 轮数熔断 / CAIS 三失败模式）
- **内容**：当前 `verify_taikoo_location` 单 AI 校验 → 评估加 adversarial critic 二审
- **Round 2 新证据（决定设计方式）**：盲目同源 Debate 会触发 sycophancy（≤85.5% 从众）+ 共识崩溃（≤32.3 点 oracle gap）+ 2.1-3.4x tokens。**但 HCP-MAD 证明简单任务用异质 pair + early stopping 可低成本获益**；sycophancy 是架构性脆弱（RLHF 修不了，需结构隔离）
- **修正设计（约束条件）**：①Critic 与决策者**异质角色 + 独立初始答案**（防锚定）；②**证据门**——Critic 修正必须引用可核验证据，无证据不采纳；③**early stopping**——pair 快停，不重辩论；④轮数硬上限（Wald-SPRT R_max 思想）；⑤产出先记 trace 不直接改生产
- **评分**：Reliability +3（有证据约束下）Complexity −2 ⇒ **PROMOTE（研究侧原型验证后过 Gate 再议生产）**
- **状态**：已从 DEFER 升级为 PROMOTE（研究侧原型），原型要求=上述 5 约束

## IC-006 记忆分层模型 → OSAI Experience/Skill/Project memory（CoALA 补充）
- **来源**：E3（MemGPT/Letta 分层 + CoALA：working/episodic/semantic/procedural）
- **内容**：OSAI 研究侧按 CoALA 记忆分层组织经验与技能，不混存：episodic（带时间戳经历）/semantic（稳定事实）/procedural（技能=ZELL skill）；working（当前决策上下文）
- **反哺对象**：OSAI research-inbox/learning-feed 组织（研究侧）
- **评分**：Maintainability +2  Reuse +2  Complexity −1  ⇒ **PROMOTE（组织层调整）**
- **状态**：入队

## IC-007 Handoff 精简 recap（防上下文污染）
- **来源**：E2（OpenAI Agents SDK：downstream 收精简 recap 而非全历史）
- **内容**：未来 Agent Council/Agent 交接时传递"精简结论 + 引用证据"，不整段倒历史
- **反哺对象**：OSAI 研究侧 Agent 交接约定（远期）
- **评分**：Reuse +2  Performance +1  ⇒ **DEFER**（无当前交接系统，待 Agent Council 落地）
- **状态**：入队，DEFER

## IC-008 多智能体防 Sycophancy 设计原则（Round 2 新增）
- **来源**：E3（CAIS 2026 / arXiv 2604.02668 / 2605.12991）
- **内容**：任何 Agent Council/Debate/Critic 设计必须内建：独立初始答案 → 异质化 → 证据门（无证据不附和）→ 轮数熔断 → 可审计
- **反哺对象**：OSAI 研究侧 Agent 设计规范（先入研究体系，Agent Council 落地时强制）
- **评分**：Reliability +3  Reuse +3  Complexity −1 ⇒ **PROMOTE（写入研究规范）**
- **状态**：入队，随本文件落库

## IC-009 Skill 版本化/回滚（Round 3 新增，同步 ZBC 候选）
- **来源**：E3（Microsoft Foundry skills 不可变版本+default_version+测试后 promote；agent-skills/skill-mcp versions/rollback CLI）
- **内容**：ZBC 能力/技能管理纳入版本化：每次更新建不可变版本→测试→promote default；支持回滚+审计+内容哈希
- **反哺对象**：ZBC（若已有 skill/能力注册则加版本化，否则先研究侧建元模型）
- **评分**：Reliability +3  Maintainability +2  Complexity −1 ⇒ **PROMOTE（评估 ZBC 落点后执行）**
- **状态**：入队，Round 4 评估 ZBC 落点

## IC-010 编排升级判据（Supervisor→Hierarchical 触发条件）（Round 3 新增，同步 ZBC）
- **来源**：E2/E3（Supervisor 3-8 agent 确定性；Hierarchical 15+/异质域/worker>6/隔离性）
- **内容**：ZBC 治理文档固化判据：当前 ShadowPlanner=Supervisor（正确）；**升级条件**=agent>6 或出现明确异质域（舆情/营销/合规/工程）；不满足不升级
- **反哺对象**：ZBC 00-GOVERNANCE（纯文档，低风险）
- **评分**：Reuse +3  Risk −0 ⇒ **PROMOTE（同步 ZBC 执行）**
- **状态**：入队，本轮同步 ZBC

## IC-011 多用户/多账号记忆隔离设计原则（Round 4 新增，T5）
- **来源**：E3（Collaborative Memory 双级记忆+动态权限图；SemaClaw 运行时隔离；Katra 三模式；Memori process_id）
- **内容**：序境多账号/多身份隔离设计原则：① 每账号双级记忆（private 不默认共享 + shared 显式授权共享）；② 隔离=运行时硬约束（context/memory/tool 状态不跨会话泄漏）；③ 记忆共享开关（Personal/Shared/Hybrid 模式）；④ 权限图动态化（角色/账号变化实时生效）
- **反哺对象**：ZBC（多账号采集/多身份隔离落点时执行）+ OSAI 设计层
- **评分**：Security +4  Reliability +2  Risk −1 ⇒ **PROMOTE（设计原则先落库，ZBC 落点待多账号功能排期）**
- **状态**：入队

## IC-012 Agent Identity 复合身份模型（Round 4 新增，T6）
- **来源**：E3（Compound Identity=User OBO+Agent Managed；AIP IBCT；Delegation Without Trust；信任等级 L1-L4）
- **内容**：序境 Agent 身份模型：① 每 agent 自有身份（非共用用户令牌）；② 操作携带复合身份（OBO 责任归属+Agent Managed 审计）；③ 动态作用域权限（per-task/per-context）；④ 验收标准=untrusted-model 假设（被完全注入也不越权）
- **反哺对象**：ZBC AI/Agent 权限边界 + OSAI 设计层
- **评分**：Security +5  Audit +3  Complexity −1 ⇒ **PROMOTE（设计原则先落库；ZBC 落点待 Agent 层排期）**
- **状态**：入队

---

## 队列状态汇总
| 编号 | Candidate | 决策 | 阶段 |
|---|---|---|---|
| IC-001 | 写路径校验 | PROMOTE | 研究侧原型 |
| IC-002 | Supervisor 拓扑确认 | PROMOTE | 已文档化 |
| IC-003 | ZELL 错误归因分层 | PROMOTE | 已落地模板 |
| IC-004 | Skill 生命周期元模型 | PROMOTE | 研究侧 |
| IC-005 | AI 日报 Critic 双审 | PROMOTE | 研究侧原型（5 约束） |
| IC-006 | 记忆分层组织 | PROMOTE | 已落地 COALA-INDEX |
| IC-007 | Handoff 精简 recap | DEFER | 待 Agent Council |
| IC-008 | 防 Sycophancy 设计原则 | PROMOTE | 已落库 |
| IC-009 | Skill 版本化/回滚 | PROMOTE | ✅ 已同步 ZBC（LEARNING-REGISTRY 版本化规则） |
| IC-010 | 编排升级判据 | PROMOTE | ✅ 已同步 ZBC（TWIN_EXECUTION_GATE） |
| IC-011 | 多用户记忆隔离原则 | PROMOTE | 设计层落库 |
| IC-012 | Agent Identity 复合身份 | PROMOTE | 设计层落库 |

**本轮（Round 4）**：IC-009 同步 ZBC（LEARNING-REGISTRY 版本化/回滚规则）；IC-010 已同步 ZBC（编排判据）；IC-011/IC-012 新增（T5/T6 首研）；新轨道 T5 Multi-User Agent + T6 Agent Identity 建立。
## IC-006 Context Engineering 反哺（2026-09-04 Cycle A）
- **来源**：E2（Chroma/Anthropic/CMU-耶鲁-亚马逊 ETCLOVG/2026 Agent 复盘）
- **内容**：长任务推进采用 Context 治理三原则：① JIT 检索（不整库塞入上下文，只带路径/句柄）；② 结构化笔记外置（阶段结论写笔记文件，防上下文腐烂）；③ 子任务隔离（复杂子任务独立分析，主流程只收结论）
- **反哺对象**：双库研发流程 + KOS 采集/分析长任务 + 报告生成
- **评分**：Reliability +3  Closure +2  Reuse +2  Complexity −1  ⇒ **PROMOTE（研究侧先落地笔记外置）**
- **状态**：入队，待原型

## IC-007 Checkpoint 断点续跑（长任务收敛）
- **来源**：E2（LangGraph Persistence/METR 长任务）
- **内容**：采集/分析/报告长任务增加 Checkpoint：关键步骤落盘状态（last_success_at/进度），失败从最近成功点恢复，配合现有熔断/冷却
- **反哺对象**：collector_automation + kos_ops 任务（研究侧先验证可行性）
- **评分**：Reliability +3  Closure +2  Risk −1  ⇒ **PROMOTE（研究侧原型）**
- **状态**：入队，待原型
## IC-008 失败案例→eval/回归用例沉淀闭环
- **来源**：E2（DORA/GitLab/Sonar 2026、AI Coding 下半场）
- **内容**：每次生产失败/回归失败，按 Production failure→Trace→Failure pattern→Add eval/regression case 沉淀为可复用测试用例，而非只看日志
- **反哺对象**：序境 Evidence/回归体系（已有 test_dual_run_stability 等可纳入统一闭环）
- **评分**：Reliability +3  Closure +2  Reuse +2  ⇒ **PROMOTE（研究侧先设计模板）**
- **状态**：入队，待原型

## IC-009 软标准 AI 互审（第二模型 review）
- **来源**：E2（AI 编码工作流）
- **内容**：关键产出（报告结论/代码 diff/合同要点）用第二模型做 review（对应智谱主力豆包最少策略），输出差异报告供人工裁决
- **反哺对象**：序境 AI 层（已有多模型路由能力，可加 review 场景）
- **评分**：Quality +3  Reuse +2  Cost −1  ⇒ **PROMOTE（研究侧先验证）**
- **状态**：入队，待原型
## IC-010 Agent 任务级 Token 预算 + 早停（智谱通道）
- **来源**：E2（火山引擎/Tokenomics/米哈游事故）
- **内容**：AI 任务加每任务 Token 预算 + 最大迭代次数上限，超支/超限强制终止并登记失败原因；防无限循环烧钱（参考 generate_summary 事故）
- **反哺对象**：ai_channel.py（已有熔断）+ AI 调用点
- **评分**：Cost +3  Reliability +3  Closure +2  ⇒ **PROMOTE（研究侧先评估）**
- **状态**：入队，待原型

## IC-011 Agent Trace 三层建模（session→step→event）
- **来源**：E2（智能体质量飞轮/火山引擎/AI Coding 可观测性）
- **内容**：采集/分析/报告长任务增加 session→step→event 三层 trace（trace_id/event_type/status/latency/cost/approval），失败可回放，动态采样控制开销
- **反哺对象**：序境 Observability（Cycle A 已提出对照自检）
- **评分**：Reliability +3  Closure +2  Ops +1  ⇒ **PROMOTE（研究侧先设计协议）**
- **状态**：入队，待原型
## IC-012 评估基线：简单 rubric + 强 backbone（不堆 judge 链）
- **来源**：E2（MOBILEJUDGEBENCH arXiv 2608.11434）
- **内容**：自建 Eval 时用"简单明确 rubric + 强 LLM 主干"，不做复杂 judge pipeline；评估区分保守/宽松失败画像；评估对象含轨迹级（配合 IC-011 trace）
- **反哺对象**：序境 Eval 体系（研究侧）+ ai_channel 输出质检
- **评分**：Reliability +3  Cost -1（省去复杂链）  Closure +2  ⇒ **PROMOTE（研究侧先设计）**
- **状态**：入队，待原型

## IC-013 代码库持久索引：符号/引用 + 意图向量检索
- **来源**：E2（Codebase Insights / CocoIndex）
- **内容**：为双库建轻量持久索引——符号/引用（SQLite）+ 意图向量检索（按"哪个函数负责X"搜索），AST-aware 分块 + 增量更新，服务 Reference Scan / Capability Discovery / 复用判定
- **反哺对象**：Canonical Capability Convergence（参考扫描提速）
- **评分**：Reuse +3  Cost +2  Closure +1  ⇒ **PROMOTE（研究侧先做原型）**
- **状态**：入队，待原型

## IC-014 知识资产渐进式披露 + 持久记忆文件
- **来源**：E2（Hermes Agent）
- **内容**：研究区知识资产借鉴渐进式披露（概要/完整/参考三级），避免全文搬运；延续"技术雷达+改进队列+Cycle 登记簿"持久记忆模式，任务完成自动提炼可复用 Capability
- **反哺对象**：OSAI 研究区结构 + Capability Registry
- **评分**：Reuse +2  Cost +1  Closure +1  ⇒ **PROMOTE（研究侧优化）**
- **状态**：入队，待原型

## IC-015 MCP/Tool Schema 体积治理
- **来源**：E2（MCP schema bloat tax：每 server 每轮 2000-4000 token）
- **内容**：工具/协议注册评估 schema 体积成本；成本敏感流程只挂必要 server；避免 schema 膨胀拉高每轮固定前缀成本（Tokenomics：固定前缀是成本大头）
- **反哺对象**：工具注册/ai_channel 前缀治理
- **评分**：Cost +3  Ops +1  ⇒ **PROMOTE（研究侧先评估）**
- **状态**：入队，待原型
## IC-016 多模型路由增强：least-cost + prompt 缓存 + 用量配额
- **来源**：E2（LiteLLM/Azure Model Router）
- **内容**：在 ai_channel 现有分级路由（智谱/搜索/视觉）基础上补——least-cost 自动降级（能满足任务的最便宜模型）、重复系统提示词缓存复用、每任务用量配额（与 IC-010 预算早停联动）；87% 企业调用浪费的三大根因对照检查
- **反哺对象**：ai_channel.py（研究侧先评估，不直接改生产）
- **评分**：Cost +3  Reliability +2  ⇒ **PROMOTE（研究侧设计）**
- **状态**：入队，待原型

## IC-017 回归测试自动生成评估（Diffblue 模式）
- **来源**：E2（Diffblue：人工 50% 后收益递减 vs AI 80%+）
- **内容**：评估为关键模块（ai_channel/kos/udip/报告）自动生成回归用例，突破 50% 覆盖率瓶颈；低成本模型（Gemma 4 类）做视觉/渲染断言
- **反哺对象**：tests/ 回归体系（研究侧评估）
- **评分**：Reliability +3  Closure +2  ⇒ **PROMOTE（研究侧评估）**
- **状态**：入队，待原型

## IC-018 知识资产"过滤-合并-更新"整理机制
- **来源**：E2（State-Aware RAG 工作记忆思路）
- **内容**：研究区知识资产（雷达/队列/登记簿）定期做过滤（去重复/过时）-合并（同主题收敛）-更新（新结论覆盖），防资产膨胀；不建向量库
- **反哺对象**：OSAI 研究区结构
- **评分**：Reuse +2  Closure +1  ⇒ **PROMOTE（研究侧优化）**
- **状态**：入队，待原型
## IC-019 AI 输出过滤（应用代码层安全边界）
- **来源**：E2（arXiv 2604.23887：唯一守住的是应用代码输出过滤，15,000 攻击零泄漏）
- **内容**：ai_channel 输出侧加应用代码层校验/过滤——不依赖模型自律；结合 HCG 门控（高风险动作本就需人工确认）；避免密钥嵌入 prompt
- **反哺对象**：ai_channel.py（研究侧先评估）
- **评分**：Security +3  Reliability +1  ⇒ **PROMOTE（研究侧设计）**
- **状态**：入队，待原型

## IC-020 舆情危机告警阈值 + 情感调优
- **来源**：E2（AI Brand Monitoring 2026：提及+200%/情绪-20pt/季度校准）
- **内容**：舆情系统加可配置危机告警阈值（提及暴涨/情绪骤降/负面数）、反讽检测、情感模型季度校准；告警走即时通知+升级流程（对应 HCG 门控）
- **反哺对象**：舆情模块（ZBC 生产侧，需走 Contract/Test/Gate）
- **评分**：Business +3  Reliability +2  ⇒ **PROMOTE（生产候选，先 Contract）**
- **状态**：✅ **IMPLEMENTED**（2026-09-04，P1 告警配置表+状态机已实施：alert_engine.py + /api/ic/alert/* + 8 测试；历史审计文件已清理；当前实现状态须按当前 HEAD 源代码和本功能验收结果核对）

## IC-021 earned media value + agentic 监测闭环
- **来源**：E2（AI Brand Monitoring 2026：EMV 替代 AVE / Year3 agentic 闭环）
- **内容**：报告系统补 earned media value 指标（替代 AVE 口径），纳入报告模板；长期目标=agentic 品牌监测自主检测→情感→危机告警→达人触达→ROI 报告（与 KOS 闭环融合）
- **反哺对象**：报告系统/METRIC_REGISTRY（生产侧，需 Contract）
- **评分**：Business +3  ⇒ **PROMOTE（生产候选，先 Contract）**
- **状态**：✅ **IMPLEMENTED**（2026-09-04，emv.py FUNC-CONTENT-04 + MET-CONTENT-04 登记 + 报告接入 + 4 测试；历史审计文件已清理；当前实现状态须按当前 HEAD 源代码和本功能验收结果核对）

## IC-022 内容跨媒介转译 + 个性化叙事（播客/品牌内容）
- **来源**：E2（《万里茶道》AI 衍生剧 / Computational Creativity）
- **内容**：播客/内容矩阵借鉴——单一形态内容做跨媒介转译（音频→短视频/图文/短剧）+ 支线延展 + 个性化交互式叙事，保持品牌情感一致性；对接播客项目与内容矩阵
- **反哺对象**：Content Intelligence / Podcast（业务向，研究侧）
- **评分**：Business +3  Reuse +1  ⇒ **PROMOTE（研究侧方法）**
- **状态**：入队，待原型
## IC-023 多 Agent 有状态图模式评估（不引框架）
- **来源**：E2（LangGraph 基准：有状态图+故障韧性最强）
- **内容**：若未来多 Agent 协作，采用"有状态图+checkpoint"模式（与 HCG 状态机同构）；不引入第三方框架/不建第三库；工具接入与 Agent 协作分离（MCP/A2A 思路）
- **反哺对象**：编排层（研究侧）
- **评分**：Reuse +2  Reliability +2  ⇒ **PROMOTE（研究侧评估）**
- **状态**：入队，待原型

## IC-024 推理预算最优分配（何时停止思考）
- **来源**：E2（测试时计算最优分配/Overthinking）
- **内容**：按任务复杂度给推理预算（简单任务低预算/复杂任务高预算）；与 IC-010 预算早停联动——"何时停止思考"= 预算内推理深度分配；避免 Overthinking 浪费（已答对却继续想）
- **反哺对象**：ai_channel 分级路由（研究侧）
- **评分**：Cost +2  Quality +2  ⇒ **PROMOTE（研究侧设计）**
- **状态**：入队，待原型

## IC-025 播客视频化 + 推荐流分发 + 留存指标（业务向）
- **来源**：E2（视频播客最快增长/推荐流发现 30-60%/留存地理指标）
- **内容**：播客项目优先视频化（YouTube/小红书/抖音分发）；用推荐流算法获取发现；核心指标=听众留存/地理/跨平台订阅；每集互动（提问/语音留言）+社区建设；推广素材（波形/封面/引用图）
- **反哺对象**：Content Intelligence / Podcast（业务向）
- **评分**：Business +3  ⇒ **PROMOTE（业务方案）**
- **状态**：入队，待原型
## IC-026 情感浓度文案手法库（创意引擎文案生成）
- **来源**：E2（韩剧对话张力公式/三层意/强情绪三招/金句四公式）
- **内容**：建立可调用文案手法库——反话/细节/留白/句式匹配四件套；一句话三层意；强情绪三招（动作痕迹/选择之痛/克制轻写）；金句四公式（对比反转/排比升华/悖论/结论宣言）；反模板化原创（用户否决模板 slogan 的直接解法）
- **反哺对象**：创意引擎文案生成（业务向）
- **评分**：Business +3  Originality +3  ⇒ **PROMOTE（业务手法库）**
- **状态**：入队，待原型

## IC-027 文学叙事技巧库（内容创作/播客）
- **来源**：E2（冰山理论/魔幻现实/意识流/叙事四功能）
- **内容**：内容创作手法库——冰山理论（subtext+留白）、魔幻现实主义（超现实融入日常，对接"物语/魔幻现实"需求）、意识流（心理亲密）；品牌叙事对齐"定义/记忆/解释/生存"四功能
- **反哺对象**：内容创作/播客/品牌叙事（业务向）
- **评分**：Business +2  Originality +3  ⇒ **PROMOTE（业务手法库）**
- **状态**：入队，待原型

## IC-028 营销日历节点库增强（marketing_nodes + hotspot）
- **来源**：E2（SocialBeta 报告：节日占 41%/节点分级/时令反套路搭子三趋势）
- **内容**：marketing_nodes 增强——节点分级（核心/节气/新兴高增长）、传播周期（长线预热 vs 短期爆发）、行业适配、六大趋势（时令叙事/反套路/搭子文化）驱动 hotspot 自动增强创意
- **反哺对象**：marketing_nodes / 创意引擎 hotspot（业务向）
- **评分**：Business +3  ⇒ **PROMOTE（生产候选，先 Contract）**
- **状态**：✅ **IMPLEMENTED**（2026-09-04，P1 字段建模已实施：marketing_calendar.py priority/lead_days/burst + 5 测试；历史审计文件已清理；当前实现状态须按当前 HEAD 源代码和本功能验收结果核对）


| IC-029 | Cycle S | KOS/内容运营引入 NPS（推荐意愿）与 DRI（问题直接责任人）式评价维度，报告新增用户推荐度与问题闭环率视角 | 商业成长与品牌理论（库克/苹果） | 中 | ✅ **RESEARCH-DONE**（2026-09-04，05-IC-029-NPS-DRI-EVALUATION.md） | KOS 运营/报告 | ADAPT | 需先定口径与数据源，避免新增重复计算 |
| IC-030 | Cycle T | 播客/深度访谈八步 SOP 资产化（约人-明线暗线提纲-开场-叫停-追问-结束-卡段剪辑）+ 嘉宾甄选三标准 Gate + 故事-情绪-观点框架 | 深度访谈方法论（凉子访谈录） | 中 | ✅ **RESEARCH-DONE**（2026-09-04，05-IC-030-PODCAST-8STEP-SOP.md） | Podcast/内容创作 | ADOPT | 方法论需人工现场验证，不模板化套路 |
| IC-031 | Cycle U | AI Semantic Layer 参考 Unity AI Gateway：对 AI/Agent 的 Canonical 数据访问做运行时拦截与裁决（读查允许、改禁），并入现有 ai_channel 研究侧设计候选 | 数据治理/Agentic 数据架构 | 中 | ✅ **RESEARCH-DONE**（2026-09-04，05-IC-031-AI-SEMANTIC-LAYER.md） | AI/Canonical 体系 | ADAPT | 研究侧候选，先评估再设计，不新建重型平台 |


| IC-032 | Cycle V | 研究侧评估模型压缩候选（EdgeRazor 混合精度/KV cache 量化/Muon 蒸馏）用于 ai_channel 轻任务降本；先 Benchmark 验证精度与收益再决策 | 推理效率/模型压缩 | 中 | ✅ **RESEARCH-DONE**（2026-09-04，05-IC-032-MODEL-COMPRESSION-EVAL.md） | ai_channel/降本 | ADAPT | 不直接换生产模型，先评估再设计 |
| IC-033 | Cycle W | KOS/内容评估新增"情绪唤醒度"维度（高唤醒=愤怒/敬畏/焦虑/惊喜，低唤醒=悲伤抑制分享），报告可呈现内容情绪传播力分层 | 情绪与传播心理学 | 中 | ✅ **RESEARCH-DONE**（2026-09-04，05-IC-033-EMOTIONAL-AROUSAL.md） | KOS/内容/舆情 | ADOPT | 需先定情绪分类口径与数据源，防重复计算 |
| IC-034 | Cycle X | 用 VLM-2026 类基准做视觉分级模型选型评估（静态识别优先，明确不扩展时序/规划高门槛能力），复核现有 ZHIPU_VISION_MODEL 分级 | 多模态/视觉理解 | 低 | ✅ **RESEARCH-DONE**（2026-09-04，05-IC-034-VISION-MODEL-SELECTION.md） | ai_channel 视觉分级 | ADAPT | 评估为主，不自动替换已落地视觉分级 |


| IC-035 | Cycle Y | 将 OWASP Agentic Top 10 + 分层安全架构（输入护栏→身份权限→执行沙箱→输出护栏→可观测审计）纳入 AI/Agent 安全检查清单，复核现有 HCG 与 ai_channel 权限边界 | AI 安全/对齐/治理 | 高 | IMPLEMENTED（2026-09-04） | AI 治理/审计 | ADOPT | 原则复核为主，先对照清单盘点再决定改动 |
| IC-036 | Cycle Z | 将品牌命名评估方法论（声义学/文化母体/跨语言负面排查/商标与域名筛查/AI 发散+人类筛选）形式化为英文 Canonical Brand TBD 候选评估管线 | 品牌命名学/语言学 | 中 | ✅ **RESEARCH-DONE**（2026-09-04，05-IC-036-BRAND-NAMING-PIPELINE.md） | 英文 Canonical Brand 研究 | ADAPT | 命名决策权在用户，方法论只作筛选工具 |
| IC-037 | Cycle AA | 研究侧沉淀记忆架构参考（事件分割粒度 episode + 扩散激活检索 + 预测-校准学习），对接自进化 Agent 记忆资产整理 | 认知科学/记忆机制 | 低 | ✅ **RESEARCH-DONE**（2026-09-04，05-IC-037-MEMORY-ARCHITECTURE.md） | 自进化 Agent/研究资产 | ADAPT | 实验性强，仅研究侧沉淀，不进入生产 |


| IC-038 | Cycle BB | 奖励设计参考沉淀（奖励信号三分层 verifiable/observable/latent + token 级奖励分配 + 持续反馈闭环）用于 OSAI 自研 AI 评估/精调；与 HCG 人工门控同构（reward 由人持续校准） | 强化学习/奖励设计 | 低 | ✅ **RESEARCH-DONE**（2026-09-04，05-IC-038-REWARD-DESIGN.md） | OSAI 自研 AI 评估 | ADAPT | 序境不自训模型，仅取评估与奖励设计思想研究侧沉淀 | 
| IC-039 | Cycle CC | 跨文化本地化框架（灵魂全球统一+表达本地适配）+ 文化禁忌/数字符号/平台行为库（广告法/清真/王室/绝对化用语）对接序境中英韩与内容出海 | 跨文化营销/本地化 | 中 | ✅ **IMPLEMENTED**（2026-09-04，localization_guard.py+8 测试） | 内容出海/三语体系 | ADOPT | AI 只做变体生成与初译，本地母语者把关 | 
| IC-040 | Cycle DD | KOS/内容运营转向兴趣图谱信号（完播率/停留时长/DM 分享/搜索命中）而非粉丝数；小红书式内容资产化+平台差异适配策略 | 内容推荐/分发算法 | 中 | ✅ **IMPLEMENTED**（2026-09-04，interest_signal+3 测试） | KOS/内容/播客分发 | ADOPT | 只做认知与策略适配，不碰黑产刷量/绕过风控 | 

| IC-041 | Cycle EE | 达人分层运营策略参考：nano/micro 高互动率（nano IG 互动约 4.5% vs mega 1.2%；micro 评论/赞比高 60%）→ KOS 分层给腰部达人更高权重；达人渠道预算占比 10-30% 参考 | 红人营销/达人经济 | 中 | ✅ **RESEARCH-DONE**（2026-09-04，05-IC-041-TALENT-TIERING-STRATEGY.md） | KOS 分层/达人合作 | ADOPT | 行业口径仅作策略参考，不作生产指标输入 | 
| IC-042 | Cycle FF | 创意内容"定制说服故事线"（人设+卖点+痛点-场景-说服闭环）替代模板化 slogan；agentic 创意生产参考（Publicis Leona 思路）但序境不引框架不新建平台；数字人/agentic 互动走 HCG 门控 | 生成式 AI 品牌创意 | 中 | ✅ **RESEARCH-DONE**（2026-09-04，05-IC-042-CUSTOM-PERSUASION-STORYLINE.md） | 创意引擎/IC-021 闭环 | ADAPT | 生成≠执行；落地前合规评审 | 
| IC-043 | Cycle GG | 长任务可靠性方法论：持久化工作记忆（scratchpad）/多步端到端成功率评测/多 judge 集成避免偏差/评测环境隔离；不因新基准自动换生产模型 | Agent 长程评测 | 中 | ✅ **RESEARCH-DONE**（2026-09-04，05-IC-043-LONG-HORIZON-RELIABILITY.md） | 自研 AI/测试回归 | ADOPT | 只学习方法思想，不引评测框架不建三库 | 

| IC-044 | Cycle HH | 舆情危机期"耸动/合成内容风险信号"（AI 生成视频/旧素材重发/情绪激发 vs 事实冲突）纳入告警维度，与 IC-020 联动（危机期阈值收紧）；处置参考官方源核验+分级响应 | 舆情传播动力学/危机沟通 | 中 | IMPLEMENTED（2026-09-04） | 舆情模块/告警 | ADAPT | 危机期语义需先定口径，防误报 | 
| IC-045 | Cycle II | 品牌叙事世界建设（AI Brand Drift 应对）：权威源 Entity Home+结构化数据+跨平台一致内容语料+社区信号，让 AI 正确重建品牌叙事；内容矩阵 Core→Hero→Derivatives→Distribution 多层栈+保护叙事脊线 | 跨媒介叙事/AI 品牌漂移 | 中 | ✅ **RESEARCH-DONE**（2026-09-04，05-IC-045-BRAND-NARRATIVE-WORLD.md） | 品牌/内容/播客 | ADOPT | 播客/内容转译衔接 IC-022；不承诺搜索排名 | 
| IC-046 | Cycle JJ | 复杂系统/涌现视角的体系设计观沉淀（局部简单规则→全局涌现复杂；临界/级联失效健康预警视角），作为"芥子纳须弥"品牌哲学学理支撑与研究资产 | 复杂系统/涌现/自组织 | 低 | ✅ **RESEARCH-DONE**（2026-09-04，05-IC-046-COMPLEXITY-EMERGENCE.md） | 产品哲学/Health 设计 | ADOPT | 仅思维框架不改变生产架构 | 

| IC-047 | Cycle KK | 免税/私域深度运营参考：海南离岛免税=KOS 高价值承接点；"种草-转化-复购"三段闭环与 KOS 运营同构；VIC+年轻入门双轨=KOS 分层+腰部达人承接年轻客佐证；私域会员数据中枢=留资/会员资产方向 | 奢侈品牌中国市场策略 | 中 | ✅ **IMPLEMENTED**（2026-09-04，kos_scenarios.py 场景标注+4 测试；见 IC020_028_047_IMPLEMENTATION_EVIDENCE_20260904.md §三） | KOS/海南中免/留资 | ADOPT | 市场数据仅策略参考，不作生产指标 | 
| IC-048 | Cycle LL | 可视化/仪表盘质量门补充：每图绑定待回答问题、零基线防误导、CVD-safe 色彩+多通道表达、role-based 信息架构、empty/error 状态同等设计 | 数据可视化/设计系统 | 中 | IMPLEMENTED（2026-09-04） | VISUALIZATION_REGISTRY/UI 基线 | ADOPT | 沉淀为检查清单，不引新框架 | 
| IC-049 | Cycle MM | 关键文档 Agentic 知识图谱检索参考（引用爬取+有效性图谱，CFR 基准 +70%）：先高价值窄切片试点（KOS 规则/合约/契约文档），测 token 与准确率再推广 | RAG/知识图谱 | 低 | ✅ **RESEARCH-DONE**（2026-09-04，05-IC-049-AGENTIC-KNOWLEDGE-GRAPH.md） | 自研 AI 知识体系/Evidence | ADAPT | 需先 Benchmark 验证，不建第三库 | 

| IC-050 | Cycle NN | AI-Native App 架构参考（Agent-Native/One Shared Action Model/分层记忆/LangGraph interrupt 人机中断）沉淀为独立 App 与平台演进研究基线；当前独立 App 降级不着急 | AI Agent/应用架构 | 低 | ✅ RESEARCH-DONE（2026-09-04，05-IC-050-AI-NATIVE-APP-ARCHITECTURE.md） | 未来独立 App/Agent 组织 | ADAPT | 只取架构思想，不引第三方框架、不建第三库 |
| IC-051 | Cycle OO | AI 浏览器/Browser Agent 前沿（Browser Use/BrowserOS/Webwright/Steel/Nanobrowser）：Vision+DOM hybrid、recovery loop、stateful session、approval gate | Browser Agent/Computer Use | 中 | ✅ RESEARCH-DONE（2026-09-04，05-IC-051-AI-BROWSER-AGENT-FRONTIER.md） | 序境平台内置浏览器 | ADAPT | 开源借鉴仅限 Safari/Chrome 原生能力，不引 Agent 框架 |
| IC-052 | Cycle PP | 平台内置浏览器能力层落地：对标 Safari/Chrome 的 Tab 管理/Reader 内容提取/书签/历史/多源搜索，strict-allowlist-open 三模式导航门 + SSRF + 危险协议硬拦截，平台内不跳站外 | 内置浏览器/CDP/安全 | 高 | ✅ IMPLEMENTED+TESTED（2026-09-04，05-IC-052-...-CONTRACT.md；ZBC browser_surface.py/browser_surface_api.py +34 测试 +真实 CDP 验证） | 平台内置浏览器表面 | ADOPT | 不改采集身份链路；UI 表面列下一阶段 P2 |
| IC-053 | Cycle QQ | Vision+DOM Hybrid 表面 Contract：文本重站点 DOM 优先(零AI)、canvas/动态回退 glm_4_6v 视觉、冲突标记人工审核；受 AI Gate/HCG/Prompt Injection 检测治理，先 Contract 不实现 | AI 浏览器/视觉/多模态 | 中 | ✅ CONTRACT-SPECIFIED（2026-09-04，05-IC-053-VISION-DOM-HYBRID-CONTRACT.md） | 平台内置浏览器/AI 增强 | ADAPT | 依赖智谱 24h 稳固通道(Track B)；不绕过验证码、不引第三方框架 |
