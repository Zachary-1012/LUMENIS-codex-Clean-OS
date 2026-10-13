# LUMENIS Product Convergence Master V1

> **SUPERSEDED / HISTORICAL ONLY（2026-10-13 标注）**：文中“Zhipu + Local AI 并行”、ARK 等运行面已退役，不得调用、探测或回退；产品 AI 只经唯一 SYSTEM AI Gateway 调用自有模型。 当前执行规则以 `AGENTS.md`、`LUMENIS-CODEX-TAKEOVER-CURRENT.md` 与 `LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md` 为准；本文件的“最高/权威/CANONICAL”表述不再有效。

日期：2026-09-06  
状态：最高执行基线 / EXECUTION AUTHORITY  
范围：Z-Brand-Core（序境生产核心）

## 1. 目的

本基线不是新增一套孤立架构，而是把此前已经完成且仍有效的生产能力、数据能力、AI/Skill/Agent能力、Runtime/Security能力、UI/UX约束与治理规则统一纳入一次最终产品收口。

核心原则：

- 以当前源码、真实调用链、真实数据、测试与运行证据为事实来源。
- 历史文档不得覆盖当前源码事实。
- 已有有效功能不得因重构而丢失。
- 旧代码、旧API、旧Provider、旧Skill、旧Agent、旧UI、旧表、旧配置、旧脚本不得直接删除，必须先做依赖与影响分析。
- 删除决策只能来自 KEEP / MERGE / MIGRATE / REFACTOR / LEGACY / ARCHIVE / DELETE 分类。
- DELETE 必须有依赖扫描、替代物、回归验证与提交证据。

## 2. 完成定义

任何功能只有依次达到以下状态才允许标记完成：

`PLANNED → IMPLEMENTED → INTEGRATED → TESTED → VERIFIED → RELEASED → OPERATING`

文件存在、测试文件存在或静态扫描通过，不等于功能完成。

## 3. 全产品覆盖域

覆盖产品/主体边界、采集、Source Library、Raw、过滤、去重、质量、Canonical、Schema/Function Registry、Event、Case、Risk、Alert、Metric、Dashboard、Search、KOS/KOL/KOC、Campaign、Report、Import/Export、Notification、AI Gateway/Provider、AI Analyzer/Filter/Learning、Skill、Agent、Orchestrator、Engineering Loop、Harness、Permission、Action Firewall、Effect Fence、Identity、Delegation/OBO/JIT、Evidence、Evaluation、Trace/Observability、Checkpoint/Resume/Recovery、Memory/Learning Asset、Browser/CDP/Auth、Frontend/UI/UX、API、DB/Migration、Security/Audit、CI/CD/Release、Production Runtime。

## 4. 产品边界

序境是独立生产产品。OSAI是独立 Intelligence/Capability Core；GGI是独立 Research/Growth 产品；LUMENIS Command 是独立研发控制侧车。不得形成跨产品运行时硬依赖，不共享生产数据库，不复制另一产品业务代码。共享能力只能通过明确、版本化、可追溯的 Contract / Artifact 边界交换。

## 5. 数据真相链

`External Source → Source Library → Collector → Raw → Subject/Product/Scope Filter → Dedup → Quality Gate → Canonical Data → DB → Event → Case → Risk → Metric → Finding/Insight → Decision → Action → Outcome → Evaluation → Feedback → Learning Asset`

数据展示链：

`Source → Evidence → Canonical Data → Function → Metric → Truth Table → View Model → Dynamic Visualization → UI/Report/Export`

任何核心数字必须能够回溯来源、函数、规则、时间、Subject、Evidence、置信度及真实/估算状态。

## 6. Agent / AI 执行链

`Human Intent → Task → Agent Identity → Permission → Plan → Skill → Tool → Action Firewall → Effect Fence → Execution → Evidence → Evaluation → Trace → Outcome → Learning`

Agent、User、Task、Run、Step、Credential、Resource必须保持独立身份语义。

AI不能替代生产事实、确定性业务规则与核心数据边界。AI不可用时，核心生产流程必须继续运行。

## 7. AI Provider

当前目标运行面：Zhipu + Local AI并行。ARK保留为LEGACY，是否继续进入运行时只能由真实调用链和验证证据决定；Qwen/OpenAI/DeepSeek等必须按真实调用关系分类为ACTIVE/LEGACY/DISABLED/DELETE。禁止隐藏fallback、死Provider和未验证Provider进入生产路径。

## 8. Runtime / Recovery

关键Worker必须形成：

`Worker → Lease → Heartbeat → Checkpoint → Failure Detection → Reaper → Retry → DLQ → Resume → Evidence`

覆盖Collector、Scheduler、Browser、AI、Agent、DB、Queue、API、子进程、Tunnel与认证会话。

## 9. UI / UX

UI必须保持序境独立产品语言，不得退化为通用Admin、AI SaaS模板或第三方产品克隆。必须建立统一Typography、Spacing、Shape、Motion、Navigation、Panel、Data Visualization、Evidence与Status Language。

保留既定约束：核心工作空间尽量单页完成、禁止无止境滚动、Progressive Disclosure、Layered/Floating Panel、紧凑导航、动态时间窗口NOW/TODAY/7D/30D/90D/YTD/HISTORICAL、Current+Delta+Freshness+Confidence、时间序列scrub并可追溯到Evidence/Event/Case。

所有UI必须绑定真实View Model/API/Data；不得用假数据掩盖后端缺口。

## 10. 旧系统治理

每一个历史实现必须经过依赖扫描、调用链分析、数据影响、API影响、UI影响与回归测试后分类：

- KEEP：继续使用
- MERGE：并入当前唯一实现
- MIGRATE：迁移后淘汰
- REFACTOR：保留能力并重构
- LEGACY：隔离兼容
- ARCHIVE：归档保存
- DELETE：确认无依赖且有替代后删除

DB表、生产API、Provider、Skill、Agent、Collector、数据、UI、Runtime能力不得仅因“旧”而删除。

## 11. Repository Registry / 硬编码

生产代码不得依赖开发机绝对路径。`D:\Taikoo-monitor-new`、`D:\Zachary OS AI`、`C:\Users\28049`等必须通过Repository Registry / Environment Resolver / Runtime Configuration逐步消除，并以静态、依赖、运行时扫描证明结果。

## 12. README / Architecture / Governance / Changelog

所有架构或能力变更必须同步更新README、Architecture、Governance和Changelog。README只描述当前真实状态；历史方案进入Archive/Changelog，不得继续作为当前能力声明。

## 13. 当前审计事实

截至本轮全域审计：190个模块被覆盖；12个达到IMPLEMENTED级函数验证；177个为PARTIAL；1个STUB；0个MISSING；0个BROKEN。数据库49张表，其中24张有数据、25张为空；另发现39处硬编码路径。上述数字是审计快照，不得解释为产品完成率。

当前明确缺口包括：硬编码路径治理、Raw→Canonical函数级验证、Evidence→DB持久化闭环、Agent Identity实际接入、OSAI模块主链集成、UI真实API接入、空表生命周期分类以及177个PARTIAL的逐项函数级验证。

## 14. 外部工程参考

Agent安全与身份治理应持续对齐2026年OWASP Agentic Applications安全框架、NIST AI Agent Standards Initiative以及OpenTelemetry GenAI/Agent可观测性语义，但仅作为工程参考，不替代本仓库源码、测试与生产证据。

## 15. 最高执行原则

最终目标不是提高模块完成率，而是形成一个前后端、数据、AI、Agent、Runtime、Security、UI/UX与业务功能真正贯通，且每个关键能力均可由源码、调用链、数据、测试和运行证据证明的生产级产品。

任何未验证项目不得标记完成；任何缺失功能必须补齐；任何错误必须修复；任何优化不得破坏已有生产能力、数据、API、Runtime、研究资料与审计证据。
