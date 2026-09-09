# AGENTS.md — 序境 / LUMENIS 工程协作与生产收敛总指令

> Version: V3.0
> Status: Active
> Scope: `Zachary-1012/LUMENIS-codex-Clean-OS`
> Product: **序境 / LUMENIS · Production Core · Production Truth Owner**
>
> 核心原则：**先审计、再修改；先兼容、再重构；先旁路、再切换；先验证、再交付。**

---

# 0. 当前阶段与最高事实基线

当前执行阶段：

```text
PRODUCTION CONVERGENCE
→ Production Acceptance
→ Release Candidate
→ Production / Operating
```

当前优先级：

```text
Capability Closure
→ Runtime Verification
→ Production Acceptance
→ Release Candidate
→ Production / Operating
```

除明确 P0 / P1 或最终生产收敛所需能力外，新功能默认进入 Backlog，不得打断当前收敛。

任何 Codex / Agent / 豆包 / 本地模型 / 人工研发执行前后，都必须执行：

```text
READ CURRENT REPO
→ AUDIT CURRENT TRUTH
→ CLASSIFY GAPS
→ IMPLEMENT / FIX
→ TEST
→ VERIFY
→ EVIDENCE
→ UPDATE STATUS
→ RE-AUDIT
```

事实优先级：

```text
Current Local Worktree / Current Source
> Current Verified Runtime / Test / Data Evidence
> Current README / Governance / Architecture
> Applicable Heritage Asset
> Historical Chat / Old README / Old Commit Message / Superseded Docs
```

禁止依赖历史聊天、旧 README、旧 commit message、旧产品命名或上一次会话结论直接继续研发。

强制读取：

- 当前 `README.md`
- 当前 `AGENTS.md`
- `00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md`
- `CAPABILITY_REGISTRY.md`
- 当前 Governance / Architecture / Audit / Runtime / Test / Evidence
- 与任务域对应的 Heritage 资产

最终六大 Production Acceptance Gate：

1. `P0 Blocking = 0`
2. `Repository Integrity = PASS`
3. `Production Truth = PASS`
4. `Runtime + Critical E2E = PASS`
5. `Security + Recovery = PASS`
6. `Release Lineage + Rollback = VERIFIED`

任意一项未通过，不得声明 Production Ready。

---

# 1. 产品身份与产品结构

正式母产品：

**序境 / LUMENIS**

定位：

**Production Core · Production Truth Owner**

序境不是 AI 产品外壳。AI 是增强能力，不是 Production Truth 本身。

当前产品结构：

```text
序境 / LUMENIS
│
├── 序境·商业运营 / LUMENIS Commerce Operations / CTH
│   └── Subject-first
│
├── 序境·品牌市场 / LUMENIS Brand & Market / BMP
│   └── Brand-first / Primary Focus
│
├── 序境·内容创作 / LUMENIS Content & Creation
│   └── Shared Capability Layer
│
└── Agent Groups
    └── Cross-Product Execution & Collaboration
```

硬规则：

- CTH / BMP 是领域产品，不是两套长期复制维护的 Core。
- Content & Creation 是共享能力，不是第三个独立产品。
- Agent Groups 是跨产品执行与协作层，不是新的产品线。
- `ZBC`、`Z-Brand-Core`、CorTech 等仅作为历史 / Legacy / engineering compatibility 语义，不得覆盖当前正式产品身份。
- 广州太古汇是 CTH 中可选择的 `Subject Profile` / 业务主体，不是母产品永久边界。

---

# 2. Repository 与跨仓边界

当前 Canonical Production Repository：

`Zachary-1012/LUMENIS-codex-Clean-OS`

相关仓库角色：

- `Zachary-1012/LUMENIS-codex-Clean-OS`：序境 / LUMENIS Production Core / Production Truth
- `Zachary-1012/Zachary-OS-AI`：Shared Intelligence Capability
- `Zachary-1012/global-growth-intelligence`：独立 Research / Growth Product
- `Zachary-1012/lumenis-command`：R&D Control / Engineering Evidence Sidecar
- `Zachary-1012/Z-Brand-Core`：Legacy / Historical Engineering Asset

当前唯一主动产品研发优先级是 **序境 / LUMENIS**。

其他仓库不得无具体依赖理由被横向扩张。

跨仓原则：

**架构融合、协议融合、能力协同；代码、数据库、Truth、Runtime 保持隔离。**

禁止：

- 共享生产数据库
- 共享生产凭据
- 隐藏 Runtime 耦合
- 让 OSAI / GGI / LUMENIS Command 成为序境启动或核心生产流程前置条件
- 未经 Contract / Artifact / Evidence 直接复制另一产品业务代码

跨仓共享只能通过版本化、可追溯、可验证的 Contract / Artifact / Evidence。

---

# 3. Production Truth 与核心生产链

核心生产链：

```text
External Data
→ Evidence
→ Canonical Data
→ Function
→ Metric
→ Truth Table
→ View Model
→ Dynamic Visualization
→ UI / Report / Export
```

业务情报闭环：

```text
Source
→ Evidence
→ Event
→ Case
→ Finding / Insight
→ Decision
→ Action
→ Outcome
→ Evaluation / Feedback
→ Learning Asset
```

任何核心结果必须能够回溯到：

- Source
- Evidence
- 时间
- Subject / Brand Scope
- Function / Rule
- Metric
- 数据版本
- 真实 / 估算 / AI 建议状态

禁止：

- 数据失败静默变成 `0`
- 页面独立重算业务指标
- 报告维护另一套业务真相
- AI 覆盖确定性事实
- UI 伪造指标、Runtime、测试、部署或完成状态

至少区分：

`0 / NULL / UNKNOWN / NOT_AVAILABLE / STALE / ERROR`

---

# 4. Capability 状态与完成定义

Capability 状态必须按真实证据晋级：

```text
PLANNED
→ IMPLEMENTED
→ INTEGRATED
→ TESTED
→ VERIFIED
→ RELEASED
→ OPERATING
```

文件存在 ≠ 功能完成。

测试文件存在 ≠ 测试通过。

测试通过 ≠ Runtime 已验证。

页面能打开 ≠ 数据链路完成。

能力只有具备以下闭环证据才能声明 VERIFIED：

```text
Source
+ Call Graph
+ Data / API
+ Frontend / Consumer
+ Runtime
+ Tests
+ Production Evidence
```

每个 Capability 只能有一个 Production Owner 和一个 Canonical Implementation；其他实现只能是 Adapter / Compatibility / Legacy / Candidate / Sub-capability。

---

# 5. 数据库与数据资产：最高保护级别

任何 `.db/.sqlite/.sqlite3`、migration、SQL、seed、备份、历史数据库、导入导出文件、ORM Model 都属于数据资产。

未经用户明确授权，不得：

- 删除生产数据库
- 清空生产数据库
- 覆盖生产数据库
- 为了测试“修成通过”而改写历史事实
- 因为表空、旧、未引用或名称带 backup/legacy 就直接删除

每张表必须明确：

`Owner / Meaning / Writer / Reader / Canonical ID / Lifecycle / Migration / Retention`

历史表、字段、API、脚本、Provider、Skill、Agent、Collector、UI、Runtime 能力必须先经过：

```text
Inventory
→ Dependency Trace
→ Runtime Verification
→ KEEP / MERGE / MIGRATE / REIMPLEMENT / LEGACY / ARCHIVE / DELETE
→ Regression
→ Evidence
```

`DELETE` 必须有：依赖扫描、替代物、回归验证、运行证据和明确批准。

数据库健康必须分别验证：

```text
Path
→ Process
→ Schema
→ Migration Version
→ integrity_check
→ foreign_key_check
→ Core Data
→ API
→ Page / Consumer
```

`integrity_check=ok` 不等于外键健康，也不等于 Production Ready。

---

# 6. CTH / Subject Authority：P0 生产保护

CTH 采用 Subject-first。

选择 Subject 只改变当前工作上下文和重点范围，不得改写：

- Canonical Data
- Evidence
- 历史事件
- 已确认业务事实

必须保护现有源码中实际存在且仍被使用的主体规则，包括但不限于：

- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `_subject_sql_and_values()`
- `aggregate_events()`
- `build_daily_report()`

是否继续使用、迁移、重构或适配必须由当前源码、调用链和回归证据决定。

不得为了增加采集量弱化主体过滤。

广州太古汇与其他城市、同名主体或相似商业场景必须严格隔离。

---

# 7. BMP / Brand & Market

BMP 采用 Brand-first / Primary Focus。

Brand Selection 代表当前主要观察焦点，但不得阻止系统继续处理：

- 多品牌
- 竞品
- 市场
- 内容
- 传播主体
- 用户反馈
- 趋势
- Campaign
- Event / Case / Risk
- Benchmark
- Report / Evaluation

必须保证 Brand Scope、Subject Scope、数据归属、报告、搜索、Agent Context 不串线。

---

# 8. Content & Creation / Podcast / Research

内容创作属于 Shared Capability Layer。

目标生产链：

```text
Brief
→ Fact Contract
→ Research
→ Scene / Audience
→ Story / Interview / Content Strategy
→ Draft
→ Platform Adaptation
→ Evaluation
→ Revision
→ Human Approval
→ Publish
→ Performance
→ Learning
```

覆盖并持续扩展：

- Xiaohongshu Content Intelligence
- Narrative / Documentary Methodology
- Deep Interview Methodology
- Human Meaning / Emotion Layer
- Episode Reverse Engineering
- Viral Intelligence
- Failure Intelligence
- Platform Adaptation
- Content Evaluation
- Podcast Production

红线：

- 不编造时间、价格、规则、活动事实
- 未经批准不得自动发布
- 不大段复制研究案例
- AI 文案不得覆盖 Fact Contract

Podcast 是内容生产能力的一部分，不是独立第三产品。

---

# 9. KOS / KOL / KOC / UGC 与传播主体

统一支持并区分：

- KOS
- KOL
- KOC
- 普通用户
- 媒体
- 官方
- 机构

主体身份与内容属性必须分开。

例如：

```text
subject_type = KOS / KOL / KOC / USER / MEDIA / OFFICIAL / ORG
content_type = UGC / COMMERCIAL / OFFICIAL / REVIEW / EXPERIENCE / COMPLAINT / CAMPAIGN / ...
```

禁止把 UGC 当作账号身份类型。

识别可使用规则 + AI 辅助，但必须保留：

- Evidence
- Confidence
- 人工修正
- 修正历史

---

# 10. Event / Case / Risk / Campaign / Decision / Action

事件至少区分并支持当前业务语义中的：

- Marketing / Campaign Event
- Propagation Event
- Public Opinion Event

事件、案例与风险不得成为孤立列表，应支持生命周期、关系和溯源。

目标链：

```text
Content / Brand / Subject / Campaign
→ Event
→ Case
→ Risk / Finding
→ Insight
→ Decision
→ Action
→ Outcome
→ Evaluation
```

Decision / Action 涉及生产影响时必须经过权限、Action Firewall、Effect Fence / Idempotency 与 Evidence。

---

# 11. Collector / 多平台 / Browser / Auth

采集目标不是高频暴力抓取，而是稳定、低风险、可解释、可恢复。

目标链：

```text
Collector
→ Session / Auth
→ Fetch
→ Normalize
→ Evidence
→ Canonical
→ Event / Content
```

必须验证：

- Login State
- Cookie / Session
- Browser / CDP
- Retry
- Cooldown
- Circuit Breaker
- Checkpoint / Resume
- Heartbeat
- Last Successful Collection
- Failure Trace
- Duplicate Handling
- Platform Mapping

### 社交平台账号永久只读保护

所有自动采集、登录保活、浏览器自动流程对登录账号一律只读。

允许：

- 打开页面
- 读取合法会话状态
- 读取公开内容
- 展开页面
- 滚动浏览
- 检测登录状态

永久禁止自动执行：

- 关注 / 取关
- 点赞
- 收藏
- 评论
- 私信
- 发布 / 转发
- 修改资料 / 设置
- 退出登录
- 切换账号
- 任何等价社交写操作

登录 / 验证只能走平台正常流程，并由用户本人完成必要人工验证。

遇到验证码、安全验证、IP 风险、登录验证页或平台限制：

```text
Detect
→ Stop Risky Requests
→ Record
→ Circuit Break
→ Cooldown
→ Health Check
→ Resume only after legitimate verification
```

不得破解验证码、绕过安全验证或规避平台风控。

多平台 Adapter 应共享上层业务逻辑，不得为每个平台复制整套系统。

---

# 12. 时间、数据质量与 Evidence

必须区分：

- `publish_datetime`：真实发布时间
- `captured_at`：系统采集时间

日报、周报、月报、活动周期、舆情日历默认按真实发布时间语义计算，除非具体业务 Contract 明确另有定义。

无法可靠归一化的相对时间必须保留不确定状态。

Evidence 必须支持：

```text
Source
→ Evidence ID
→ Canonical Object
→ Finding
→ Decision
→ Action
```

以及 timestamp / provenance / identity or hash / relation / trace / audit。

Raw / Evidence 原则上不可被派生结果静默覆盖；派生数据应创建版本化结果。

---

# 13. AI / Skill / Agent

AI 架构遵循：

```text
Production Truth
→ Intelligence Router
├─ Approved Cloud Provider
├─ Local AI
└─ Deterministic Rules / No-AI
```

Provider ACTIVE 状态必须由当前真实调用链、健康检查和测试证据证明，不能由历史配置证明。

禁止隐藏 fallback、死 Provider 或未验证 Provider 进入生产路径。

系统生命线不能绑定单一 AI Provider。

AI 不可用时，核心生产流程必须继续成立。

AI 可用于：

- 发现
- 分类
- 摘要
- 解释
- 推理
- 建议
- 内容辅助
- 工程辅助

AI 不得单独决定：

- 原始事实真实性
- Production Truth
- 确定性业务规则最终结果
- 核心统计数量
- 最终主体归属
- 未经证据支持的风险结论
- 未经权限批准的生产写入

Skill / Agent 运行链：

```text
Task
→ Identity
→ Permission
→ Plan
→ Skill / Tool
→ Action Firewall
→ Effect Fence / Idempotency
→ Execute
→ Evidence
→ Evaluation
→ Trace
→ Outcome
```

AI / Agent 不得绕过权限直接修改 Production Truth。

---

# 14. Runtime / Recovery / Observability

生产 Runtime 覆盖：

- Process
- Worker
- Queue
- Lease
- Scheduler
- DB
- Collector
- Browser
- Provider
- Agent
- Auth / Session
- Recovery
- Audit / Trace / Evidence

关键 Worker 目标链：

```text
Worker
→ Lease
→ Heartbeat
→ Checkpoint
→ Failure Detection
→ Reaper
→ Retry
→ DLQ
→ Resume
→ Evidence
```

`overall healthy` 不得掩盖 Worker、Reaper、Collector、Queue 等子系统未运行。

健康状态必须表达真实粒度。

---

# 15. API / Frontend / UI / UX

API 链：

```text
Route
→ Auth
→ Permission
→ Input Contract
→ Service
→ DB / Function
→ Output Contract
→ Frontend Consumer
```

重点审计：

- orphan API
- UI drift
- API drift
- duplicate blueprint
- legacy endpoint
- hidden fallback
- fake 200

前端是 Production Truth View，不是独立静态展示层。

所有页面状态必须来自真实 API / State Contract。

统一体验要求：

- PC / Tablet / Mobile 自适应
- 2–4 层信息架构
- Drill-down
- Trend / Cards / Tables
- Evidence / Insight / Action
- Dynamic Visualization
- Motion 用于表达因果、状态与连续性，不是装饰
- Current + Delta + Freshness + Confidence
- 时间序列可回溯 Evidence / Event / Case

### Heritage UI 硬规则

**Legacy code is a capability source, not a UI source.**

历史 UI/UX 只能用于证明旧业务意图、缺失功能或信息关系，不能作为最终 UI 来源。

历史功能恢复链必须为：

```text
Historical / Legacy Asset
→ Inventory
→ Source / Dependency Trace
→ Current Equivalent Audit
→ Semantic Dedup
→ Current Production Line Mapping
→ KEEP / MERGE / MIGRATE / LEGACY / ARCHIVE / DELETE
→ Capability Recovery / Reimplementation
→ Current API / State Contract Integration
→ NEW UI / UX DESIGN
→ Runtime / E2E
→ Tests
→ Evidence
→ Re-Audit
```

最终 UI 必须按当前 LUMENIS Design System 与当前信息架构重新设计。

---

# 16. Report / Search / Import / Export / Notification

报告覆盖并逐步统一：

- Daily
- Weekly / Monthly（若当前 Contract 支持）
- Special Report
- Campaign
- KOS / Audience
- Public Opinion
- Research
- Evaluation
- Operations

报告链：

```text
Metric
→ Evidence
→ Finding
→ Risk / Insight
→ Decision Context
→ Action
→ Report Artifact
```

报告不得独立维护业务计算逻辑。

Search、Import、Export、Notification 必须遵守：

- Scope / Permission
- Production Truth
- Evidence
- Data Minimization
- Domain Isolation
- Error State

不得通过导入或搜索绕过 Subject / Brand / Permission 边界。

---

# 17. 数据最小化与合规

允许的业务最小字段应以当前产品 Contract 为准，原则包括：

- 标题
- 发布时间
- 互动数据
- 内容分析
- 链接
- 必要结构化元数据

默认不保存：

- 原始视频
- 原始图片
- 不必要个人信息

部署地区规则必须按 Mainland China / Hong Kong / Overseas 的实际合规要求切换。

任何地区配置都不得成为绕过平台规则或安全边界的手段。

---

# 18. Security

安全分层：

```text
Edge
→ Application
→ Auth
→ Permission
→ Agent Tool Firewall
→ Data
→ Runtime
→ Supply Chain
```

必须：

- 默认最小权限
- fail-close
- 敏感字段脱敏
- API Key / Token / Cookie 不进入 Git
- 危险操作需要明确权限与审计
- Agent 写入需要 Action Firewall / Effect Fence
- 重要结果保留 Evidence / Trace

任何 API Key 只允许通过本地 `.env` / 系统密钥 / 合法 Secret 管理注入。

严禁写入源码、前端、Git、模板、数据库初始化脚本、日志或测试样例。

---

# 19. Developer Settings：Post-Launch Backlog

`系统设置 → 开发者 / Developer` 属于历史能力保护项，但当前调度状态为：

```text
POST_LAUNCH_BACKLOG
Target Phase: POST_LAUNCH_UPGRADE
```

在当前：

```text
Production Convergence
→ Production Acceptance
→ Release Candidate
→ first Production
```

阶段：

- 保护历史资产
- 不删除、不覆盖
- 不把 Developer Settings 作为当前发布前置条件
- 不让其创建新的 Runtime prerequisite

**Developer Settings 不是当前六大 Production Acceptance Gate 的阻塞项。**

其缺失或尚未恢复不得阻止 Production Acceptance、RC 或首个 Production。

首个生产版本上线并完成稳定性观察后，再执行完整恢复链：

```text
Current Source Audit
→ Historical Inventory
→ Feature Source Trace
→ Route / API / Service / DB / Config / Permission / Runtime Trace
→ Historical Behavior & Acceptance Evidence
→ Current Equivalent Audit
→ Capability Matrix & Gap Classification
→ KEEP / MERGE / MIGRATE / REIMPLEMENT / LEGACY / ARCHIVE
→ Current Architecture Mapping
→ Security / Permission Boundary Design
→ Current API / State Contract Integration
→ System Settings IA Integration
→ NEW Developer Settings UI / UX Design
→ PC / Tablet / Mobile Responsive
→ Runtime Integration
→ Tests / Critical E2E
→ Evidence
→ Re-Audit
```

硬规则：

- 不丢功能
- 不盲目复活
- 不恢复旧 UI
- 不暴露生产秘密
- 不绕过权限
- 不伪造状态
- 不破坏领域隔离
- 不制造 Runtime 前置依赖
- 危险操作必须受控
- 默认最小权限

---

# 20. Heritage Intelligence Retrieval Gate

Heritage 是历史能力与知识证据，不是当前 Production Truth。

执行任何涉及产品功能、数据、平台、UI/UX、AI/Agent、Runtime、安全、测试、架构或重构任务前，必须定向读取：

1. `heritage_intelligence/README.md`
2. `heritage_intelligence/ASSET_REGISTRY.md`
3. `heritage_intelligence/ASSET_GOVERNANCE.md`
4. `heritage_intelligence/SOURCE_MAP.md`
5. 与当前任务域对应的 Heritage Asset / Decision Memory / Regression Memory

任务域映射：

- UI/UX → Product/UX + Data Presentation + Decision Memory
- 数据/指标/表格 → Data/Metrics + Evidence/Contracts + Decision Memory + Regression Memory
- 平台 → Platform Intelligence + Domain + Compliance/Contract
- 内容/i18n → Language & Content Intelligence
- KOS / Podcast / 舆情 / Campaign / Research / Operations → Domain Methodology + Data + Contract
- AI/Agent → AI & Agent Intelligence + Engineering Governance
- Runtime/Security/Release → Engineering Governance + Regression Memory

禁止无差别全文灌入上下文；应按任务定向检索。

Heritage → Capability Promotion：

```text
Heritage Retrieval
→ Current Fit
→ Decision
→ Implementation
→ Test
→ Evidence
→ Regression
→ Release Gate
```

可分类：

- DESIGN_ENHANCEMENT
- FUNCTION_ENHANCEMENT
- DATA_ENHANCEMENT
- PLATFORM_ENHANCEMENT
- AI_ENHANCEMENT
- ENGINEERING_ENHANCEMENT
- REFERENCE_ONLY
- NOT_APPLICABLE

禁止：

- 因旧分支落后、文件未被 Runtime 引用而直接判定无用
- 因进入 Heritage 就自动恢复旧代码/旧 DB/旧 API/旧 UI/旧 Provider
- Heritage 绕过 Production Truth、Evidence、测试或 Release Gate
- 未先检索历史资产就重新发明已有且仍有效的 Contract / Metric / Decision / Regression 规则

---

# 21. 修改安全协议

任何修改必须遵循：

```text
Audit
→ Dependency / Impact Check
→ Backup / Rollback Plan where needed
→ Minimal Safe Change
→ Unit / Integration Test
→ API / DB / Runtime Verification
→ Critical E2E where applicable
→ Regression
→ Evidence
→ CHANGELOG / Status Update where applicable
→ Re-Audit
```

禁止：

- 为了“通过”删除测试
- 屏蔽真实异常
- 伪造 Runtime / Test / Production Evidence
- 无依赖分析的大规模重写
- 无替代物的删除
- 直接把历史方案覆盖当前源码

P0 优先保护：

- 启动
- 数据库 / Migration
- Production Truth
- Subject / Brand Scope
- Collector / Auth
- Evidence / Canonical / Metric
- Runtime / Recovery
- Core API
- Core Report
- Security / Permission
- 当前已验证页面与业务能力

---

# 22. Git / GitHub 规则

当前 Canonical Production Repository：

`Zachary-1012/LUMENIS-codex-Clean-OS`

提交前必须检查：

- Cookie / Token / API Key / Credential
- 个人隐私
- 生产数据库
- 测试垃圾 / 临时文件
- 重复 Core
- Governance drift
- 是否需要 CHANGELOG / Evidence / Status 更新
- 是否破坏当前 README / AGENTS / Acceptance Gate

禁止未经授权：

- force push
- reset --hard
- clean -fd
- 改写历史
- 删除生产分支资产

本地工作区存在未提交修改时，任何辅助 Agent 不得用 online main 覆盖本地真实现场。

---

# 23. 测试与验收

修改后按变更范围至少验证：

- Unit Test
- Integration Test
- Database Migration Test
- API Smoke / Contract Test
- Runtime Test
- Permission / Security Test
- Browser / Critical E2E
- Subject / Brand Scope Regression
- Time Semantics Regression
- Collector State / Auth Recovery Regression
- Report Truth Regression
- Rollback / Recovery where applicable

测试失败必须记录真实错误。

不得通过删除测试、跳过失败、屏蔽异常或伪造数据让状态变绿。

---

# 24. 交付输出格式

每次任务完成后必须报告：

1. 审计了什么
2. 修改了什么
3. 为什么修改
4. 修改文件
5. DB 是否变化
6. API / Runtime 是否变化
7. 执行的测试
8. 测试结果
9. Evidence
10. 未完成 / Blocked / Needs Evidence
11. 风险 / 已知限制
12. Git commit / push 状态
13. 下一步建议

禁止只回复“完成”“已修复”。

---

# 25. 最终不可违反原则

> **真实源码与真实运行证据优先于历史印象。**
>
> **Production Truth 优先于 AI 输出。**
>
> **稳定版本优先于漂亮重构。**
>
> **能力可以共享，Truth / DB / Runtime / Ownership 不得模糊。**
>
> **数据失败必须显式，不得静默成 0。**
>
> **历史代码是能力来源，不是最终 UI 来源。**
>
> **任何新能力先旁路验证，再进入主链路。**
>
> **没有 Source + Call Graph + Data/API + Consumer + Runtime + Tests + Production Evidence，就不能声明 VERIFIED。**
>
> **当前唯一主动产品研发优先级是序境 / LUMENIS。**
