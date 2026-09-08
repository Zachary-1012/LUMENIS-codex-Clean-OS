# LUMENIS AI 总体升级增量落地对照 V1

来源：用户提供的《序境 LUMENIS AI 总体升级指令》
文档结构：1269 个段落、40 个主题章节、无表格、无批注、无修订记录、无图片
状态：`REQUIREMENT ACCEPTED / IMPLEMENTATION NOT AUTHORIZED BY SOURCE DOCUMENT`

## 1. 指令性质

该文档明确规定：

- 它是现有方案的增量升级，不推翻产品边界、Runtime、Database、Data Truth 和 Human Approval。
- 当前阶段为 `PLANNED / DESIGN APPROVED / NOT IMPLEMENTED / NOT EXECUTION AUTHORIZED`。
- 不得打断工程质量审计。
- 目标不是训练通用前沿基础模型，而是建设 L4+ Mature Vertical Agentic AI Workspace。

因此本报告只完成需求归并、源码现状对照和研发路线，不把指令文本当作已实现证据，也不启动大规模代码修改。

## 2. 最终定位

`Models provide foundational intelligence; LUMENIS provides domain intelligence.`

LUMENIS AI 的差异化来自自己的 Context、Evidence、Tools、Memory、Evaluation、Learning 和受控 Action，而不是绑定某一个 Provider 或复制 ChatGPT 品牌与视觉。

目标结构：

```text
User
  ↓
Global AI Interaction Layer
  ↓
Context Engine
  ↓
Orchestrator
  ├─ ASK
  ├─ CREATE
  └─ ACT
  ↓
Retrieval / Agents / Tools / Memory
  ↓
AI Gateway → Model Router → Provider Pool
  ↓
Evidence → Evaluation → Human Approval → Controlled Action
  ↓
Outcome → Learning Asset → OSAI R&D → Versioned Artifact
```

## 3. 产品边界

- Global AI Interaction Layer 是跨 CTH/BMP 的交互能力，不是第四产品线。
- Content Creation 属于 Shared Capability，不是 BMP 或 CTH 独占产品。
- SYSTEM 承载 AI Gateway、Runtime、Security、Settings 和 Audit。
- Agent Groups 是跨产品执行与协作层，不是新产品。
- OSAI 是共享智能研发与增长层，不拥有 LUMENIS Production Truth，不成为生产启动依赖。

## 4. 40 项指令的能力归并

### 交互与体验

要求包括新建聊天、多轮历史、搜索、附件、流式回复、上下文保持、桌面/平板/移动端、工具卡片、Artifact 和审批面板。

当前事实：存在 `/api/ai/chat` 和 SYSTEM AI 页面；接口从客户端接收最近 history，并返回单次 reply/context。未发现可证明 conversation_id、服务端会话持久化、附件、流式响应、跨设备连续性已经完成的统一链路。

判定：`PARTIAL`。

### Global AI Interaction Layer

指令定义 ASK、CREATE、ACT 三种逻辑模式。当前已有查询/分析 API、内容生成、AI Task/Agent/Tool 和受控动作构件，但没有一个经过生产验证的全局入口把三种模式统一编排。

判定：`PARTIAL / NO CANONICAL ENTRY`。

### Context Engine

要求自动组装 Product、Domain、Subject、Brand、Campaign、Page、Entity、Evidence、Time Range、Filters、Identity、Permission、Conversation、Memory 和 Learning Asset，并执行 Context Budget。

当前已有 `ai_domain_context.py`、`context_intelligence.py`、`subject_context.py`、`domain-context.js` 和 function registry 上下文。未发现完整 Context Budget、来源优先级、token 预算和逐项 provenance 的统一运行证据。

判定：`PARTIAL`。

### Knowledge / RAG

要求 Ingest → Normalize → Classify → Metadata → Chunk → Index → Retrieve → Rerank → Filter → Cite → Inject，并区分事实、风格、案例、业务规则、平台规则、偏好、Learning Asset 和历史输出。

当前有案例库、品牌知识库、research search、resources、intelligence library 和检索函数；没有证据证明所有资产完成 chunk/index/rerank/citation，也不能把文件存在视为 AI 已学习。

判定：`ASSETS EXIST / RAG NOT VERIFIED`。

### Content Creation Engine

当前 `content_generation.py` 已有 typed generation、人工 feedback、Evidence 查询、研究检索、广告策略、视频分析、品牌报告、播客研究和话题快照。

缺口：统一 Brief、Brand/Subject Profile、平台规则、Case/RAG、Style/Fact/Compliance Evaluation、人工编辑版本、Human Edit Distance、Learning Admission 尚未形成一条 canonical 流程。

判定：`IMPLEMENTED COMPONENTS / END TO END PARTIAL`。

### Model Router 与 Provider Independence

当前 `ai_channel.py`、`provider_registry.py` 已有 provider chain、重试、Circuit Breaker、健康、fallback 和切换 trace；智谱与 Ollama 均有实际工具调用证据。

缺口：统一 Provider Contract 尚未完整覆盖 generate、stream、tool_call、structured_output、context_limit、health、cost、latency、error_type 和 capability；前端/Agent Runtime 是否完全不感知 Provider 仍未证明。

判定：`PARTIAL`。

### Fallback 与 Degradation

要求区分 AUTH、QUOTA、RATE_LIMIT、TIMEOUT、NETWORK、MODEL_UNAVAILABLE、INVALID_REQUEST、CONTENT_BLOCK 和 PROVIDER_INTERNAL，并公开 FULL、FALLBACK、DEGRADED、BLOCKED、UNAVAILABLE 状态。

当前有错误分类、retry、breaker、fallback 和 provider switch log；生产业务任务的能力兼容检查、结果验证和 UI 降级展示尚未完整验证。

判定：`CONTROL EXISTS / PRODUCTION FAILOVER NOT VERIFIED`。

### Memory

当前存在 working、episodic、semantic、task、skill、learning memory、memory optimizer 和 memory governance，专项测试通过。

缺口：Conversation、Preference、Business Context、Task、Learning Asset、Production Truth 的强制隔离，以及 Candidate → Evaluation → Feedback → Validation → Generalization → Admission 的生产链未证明。

判定：`IMPLEMENTED COMPONENTS / ADMISSION PARTIAL`。

### Tool Calling 与 Agent Orchestration

当前存在 Task Parser、Task Engine、Agent Boundary、Skill Registry、Skill Execution Chain、Permission、Firewall、Effect Fence、Evidence、Evaluation、Trace。

缺口：所有工具的 identity、permission、scope、input/output schema、timeout、error contract、trace 尚未形成单一注册表；所有任务进入唯一 Orchestrator 的事实未证明。

判定：`CONTROL DESIGN EXISTS / CANONICAL ORCHESTRATOR NOT VERIFIED`。

### Evidence First AI

指令要求 FACT、METRIC、INFERENCE、AI INTERPRETATION、RECOMMENDATION 分离，并返回 source、evidence_id、timestamp、freshness、confidence、verification_state。

当前 EvidenceChain、View Model、AI call logs 和 production evidence contract 已有相关字段，但存在 `zbc_evidence`、`app_evidence_records`、Browser Evidence 等多套载体。

判定：`PARTIAL / EVIDENCE STORE CONVERGENCE REQUIRED`。

### Evaluation 与 Learning

当前有 evaluation system、dimensions、recorder、runner、badcase、golden case、regression、learning persistence 和 feedback API。

缺口：Chat、Reasoning、Content、Fact、Evidence、Retrieval、Tool、Agent、Fallback、Memory、Hallucination、Latency、Cost、Safety 的统一 benchmark family 及持续生产运行证据；Human Edit Distance 未成为正式指标。

判定：`EVALUATION ASSETS EXIST / CONTINUOUS GATE PARTIAL`。

### Artifact System

当前有 report artifact、content evidence、报告和导出实现。未发现可证明 Chat → Artifact → Edit → AI Revise → Version → Save 的统一可编辑 Artifact 工作空间。

判定：`PARTIAL`。

### Mobile 与多语言

当前存在响应式模板、移动端测试/截图、i18n JS 和中英韩产品命名治理。未证明移动端新建聊天、历史抽屉、附件、语音准备、工具卡、Artifact 和审批 Bottom Sheet 全部可用。

判定：`FOUNDATION EXISTS / FIRST CLASS MOBILE AI NOT VERIFIED`。

### Observability 与 Cost

AI call logs 已包含 provider、model、prompt_version、input/output hash、confidence、latency、token usage、failure、task_id、trace_id 等字段。

缺口：conversation_id、完整 context_sources、retrieval_refs、tool sequence、标准 cost、fallback lineage 和 human feedback 尚未在每个任务中强制齐全。

判定：`PARTIAL`。

## 5. 与现有审计的兼容性

新增指令不改变以下结论：

- 当前运行数据库与工作区数据库分裂。
- Evidence/Canonical 尚未统一。
- Agent 控制构件存在，但生产准入未全链验证。
- 前端应为结构化 UI + Conversational AI，不能退化为纯聊天机器人。
- AI 不能拥有 Production Truth、业务规则或数据所有权。
- CTH、BMP、Shared Capability、SYSTEM 的产品边界保持不变。

## 6. 实施路线

### P0 架构冻结前

1. 固定 Global AI Interaction、Context Envelope、Provider、Tool、Evidence Citation、Conversation、Artifact、Evaluation Contract。
2. 明确唯一 Orchestrator、唯一 Tool Registry 和统一任务状态。
3. 统一 Production Truth 与 AI Interpretation 的数据隔离。
4. 修复工程质量 P0：认证凭据、权限旁路、迁移、CI 和运行基线。
5. 建立 L4+ 20 项 Gate，初始状态全部从 `NOT VERIFIED` 开始。

### P1 旁路实现

1. Global Chat MVP：conversation、history、stream、attachment、context inheritance。
2. Context Engine：预算、来源、裁剪、Evidence 注入和权限过滤。
3. RAG：知识类型、索引、rerank、citation 和 freshness。
4. ASK/CREATE/ACT 编排，ACT 默认 staged，强制审批。
5. 可编辑 Artifact、内容评测、Human Edit Distance 和反馈候选。
6. Provider capability routing 与可见降级状态。

### P2 产品化

1. 桌面、平板、移动端一等体验。
2. 跨设备会话连续性。
3. 持续 benchmark、成本路由、长稳和故障注入。
4. 经验证 Learning Asset 通过版本化 Artifact 供给 OSAI，再回流产品。

## 7. 本轮验证

AI channel、failover、Context、Domain Context、Evaluation、Learning、Prompt、Skill Invoke、Memory 和 Content Production 共 187 项专项测试通过。

这些测试证明已有组件可测试，不证明 Global Chat、完整 RAG、统一 Orchestrator、Artifact 编辑、移动端和真实 L4+ 场景已经完成。

## 8. L4+ 当前判定

文档定义的 20 项 L4+ Gate 当前不能判定任何一项为完整生产 `VERIFIED`。部分能力已有源码与测试，但 Runtime、Database、Page、Production Evidence 未全部闭环。

最终状态：`L4+ TARGET ACCEPTED / CURRENT L4+ NOT VERIFIED / IMPLEMENTATION AWAITS ARCHITECTURE FREEZE AND HUMAN APPROVAL`。

## 9. 文档读取限制

原 DOCX 正文和结构已完整提取，并确认无表格、批注、修订和图片。打包文档运行时缺少 LibreOffice，无法完成页面 PNG 渲染，因此本轮没有对分页、字体和视觉排版作通过声明；该限制不影响正文需求提取，但保留为文档视觉验收未完成项。
