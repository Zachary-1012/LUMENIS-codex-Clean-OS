# AGENTS.md — 序境 / LUMENIS Codex Production Execution Rules

> Version: V3.2 — Final Codex Takeover
> Status: Active
> Scope: `Zachary-1012/LUMENIS-codex-Clean-OS`
> Product: **序境 / LUMENIS · Production Core · Production Truth Owner**

核心原则：**先读真实仓库，再改；先复用，再重构；先绑定真实 Production Truth，再传播；先验证，再声明完成。**

---

# 0. 唯一执行入口

```text
Repository: Zachary-1012/LUMENIS-codex-Clean-OS
Canonical Codex Entrypoint: handoff/frontend-gpt-v24-20260911-final
Base: main
```

前端 / Experience 完整交付硬基线：

```text
TOTAL_SOURCE_RECORDS = 1604
NON_MEDIA_EXPECTED   = 682
PACKAGE_A_REQUIRED   = 642
PACKAGE_B_REQUIRED   = 40
MEDIA_EXCLUDED       = 922
WOFF2_REQUIRED       = 56
```

旧 `111-file` 标准已废止，不得再用于完整性判断。

`READY_FOR_CODEX_EXECUTION` ≠ `PRODUCTION_READY`。

---

# 1. 事实优先级

冲突时严格使用：

```text
Current Production Source
>
Runtime Reality
>
Current DB / API / Permission / Evidence Contracts
>
Tests / Production Acceptance
>
Experience V2
>
Current Production UI capability evidence
>
Legacy Evidence
>
Historical Chat / Old README / Old Commit Message / Superseded Docs
```

禁止凭历史聊天、旧设计稿、旧 README、旧 commit、Legacy 或 AI 推测覆盖当前事实。

---

# 2. 不重新造轮子

开始任何实现前，先读取并复用已有：

- contract
- registry
- evidence model
- metric definition
- Experience source
- design token
- API
- permission model
- canonical data model
- runtime capability
- test / acceptance evidence

如果已有能力存在，必须先复用、适配或收敛。

禁止建立第二套：

- Subject Context
- Evidence model
- Metric engine
- Permission model
- Design System
- frontend architecture
- API truth
- DB truth
- Runtime truth

每个 Capability 只能有一个 Production Owner 和一个 Canonical Implementation；其他实现只能是 Adapter / Compatibility / Legacy / Candidate / Sub-capability。

---

# 3. Codex 不重新做前端前期

前端前期已经完成并正式交付。

Codex 第一阶段不是：

```text
Research
→ Re-design
→ New design system
→ New frontend architecture
```

必须是：

```text
Read
→ Verify
→ AI-01 + CTH-01 calibration
→ Backend binding
→ Critical E2E
→ Propagate
```

Codex 可以：

- 阅读 Experience V2
- 核验 Screen Contract / IA / Interaction / Token
- 修复必要实现问题
- 接真实 API / DB / Permission / Evidence / Runtime
- 校准 AI-01 + CTH-01
- 做 Critical E2E
- 验证模式成立后向其余模块传播

Codex 不可以：

- 从零重新设计 Experience V2
- 再研究一次 UI 趋势
- 再建第二套 Design System
- 再做全部前端稿
- 再定义第二套 IA

Legacy UI 规则仅针对 Legacy：Legacy 是能力证据，不是最终 UI 来源；**该规则不得被误解为要求重新推翻已正式交付的 Experience V2。**

---

# 4. Design Language v2.4

必须保持：

- black-silver / white-silver
- metallic monochrome
- editorial serif display
- restrained sans
- Lumen Axis / 序轴
- Strata / 境层
- de-boxed hierarchy
- whitespace
- hairlines
- Icy Cyan only for state / data semantics
- LUMENIS original AI orb
- Evidence / Trace-first
- semantic motion

FAIL：

- generic SaaS
- generic dashboard
- card wall
- purple / indigo AI template
- component-library demo
- 换 Logo 后仍像任何普通 AI SaaS

Motion 只能服务状态、因果、层级、连续性与反馈，不作为装饰。

---

# 5. Production Truth

内部主生产链：

```text
External Data
→ Evidence
→ Canonical Data
→ Function
→ Metric
→ Truth Table
→ View Model
→ Visualization
→ UI / Report / Export
```

业务链：

```text
Source
→ Evidence
→ Event
→ Case
→ Insight
→ Decision
→ Action
→ Outcome
→ Evaluation
→ Learning Asset
```

这些是 backend / contracts / production logic，不是普通业务页面视觉流程。

禁止：

- 数据失败静默变成 `0`
- UI 独立重算业务指标
- 报告维护另一套计算真相
- AI 覆盖确定性事实
- UI 伪造指标 / Runtime / Test / Deployment / Completion 状态

至少区分：

`0 / NULL / UNKNOWN / NOT_AVAILABLE / STALE / ERROR`

---

# 6. 正常业务页面展示红线

正常业务页面禁止把内部生产链、业务链或 Agent Runtime 链做成：

- flow diagram
- decorative stepper
- card chain
- permanent process bar

正常业务页面展示：

- Context
- Facts
- Relationships
- State
- Evidence
- Finding
- Risk
- Decision
- Action
- Outcome
- Controls

---

# 7. 四域与 Subject Context

正式四域：

- CTH｜商业运营
- BMP｜品牌市场
- Shared Capability
- SYSTEM

CTH / BMP 都支持 Selected Subject，共享统一 Subject Context 语义，但不能合并领域模型、Metric Pack、Relationship、Capability Set 与 Action Chain。

Subject Context 至少贯穿：

```text
Subject Selector
→ Router / URL Context
→ API Context
→ Permission Validation
→ Query / Function Scope
→ Cache Key
→ Evidence / Trace
→ Report / Export Snapshot
```

前端传入 `subject_id` 不构成授权；后端必须重新验证。

保护当前仍被真实调用的主体规则，包括但不限于：

- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `_subject_sql_and_values()`
- `aggregate_events()`
- `build_daily_report()`

迁移前必须做 Dependency Trace + Shadow Comparison + Regression Evidence。

---

# 8. Experience V2 Authority Boundary

Experience V2 负责：

- IA
- Experience
- Interaction
- Screen Contract
- Visual Language
- Design Token
- Responsive behavior
- Motion semantics

Experience V2 不能伪造：

- backend
- API
- DB
- permission
- runtime
- evidence
- metrics
- production status

前端必须成为 Production Truth 的真实 View，而不是独立静态展示层。

---

# 9. Legacy

Legacy 永久定义：

```text
READ ONLY
EVIDENCE
CAPABILITY REFERENCE
```

Legacy 可用于：Inventory / Dependency Trace / Capability Recovery / Regression / Migration Evidence。

Legacy 不得覆盖：Current Production Source / Runtime / DB / API / Permission / Evidence / Tests / Experience V2 formal source。

---

# 10. AI Conversation 安全规则

允许展示：

- retrieval status
- evidence citation
- source
- tool status
- action status
- permission
- approval
- artifact
- provenance
- confidence
- limitation

禁止展示：

- private chain-of-thought
- system prompt
- developer prompt
- credentials
- cookie
- token
- browser session
- CDP internals
- security internals

不得为了“可解释”而暴露内部私密推理。

---

# 11. ChatGPT / MCP Boundary

正式公共访问链：

```text
ChatGPT
→ MCP / App Adapter
→ Allowlisted Schema
→ Auth
→ Subject Context
→ Domain
→ Permission
→ Provenance / Policy
→ Versioned Internal Contract
→ LUMENIS Production Truth
```

公共 ChatGPT 不得直接访问：

- Collector
- Cookie
- Browser Session
- CDP
- raw DB
- privileged hidden tools

---

# 12. DB / Permission / Security

数据库属于最高保护级资产。

未经明确批准不得：删除、清空、覆盖生产 DB，不得为了让测试变绿而改写历史事实。

修改 DB / Migration / ORM 前必须验证：

```text
Path
→ Process
→ Schema
→ Migration Version
→ integrity_check
→ foreign_key_check
→ Core Data
→ API
→ Consumer
```

安全原则：least privilege / fail-close / no secrets in Git / server-side permission validation / Action Firewall / Effect Fence / Audit / Trace / Evidence。

---

# 13. Collector / Browser / Social Account

自动采集对登录账号永久只读。

允许：打开页面、读取公开内容、合法会话状态、滚动、展开、检测登录状态。

禁止自动：关注、取关、点赞、收藏、评论、私信、发布、转发、改资料、退出登录、切换账号或任何等价社交写操作。

遇到验证码 / 安全验证 / IP 风险：

```text
Detect
→ Stop Risky Requests
→ Record
→ Circuit Break
→ Cooldown
→ Health Check
→ Resume only after legitimate verification
```

不得破解验证码或规避平台风控。

---

# 14. Capability 完成定义

Capability 状态：

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

只有具备：

```text
Source
+ Call Graph
+ Data / API
+ Frontend / Consumer
+ Runtime
+ Tests
+ Production Evidence
```

才能声明 VERIFIED。

---

# 15. Codex 正式执行顺序

```text
README
→ AGENTS
→ CODEX TAKEOVER
→ Experience V2 formal source
→ Contracts / Registries
→ Current backend / API / DB / Permission / Evidence / Runtime
→ Current Tests / Production Acceptance
→ AI-01 + CTH-01 calibration
→ real backend binding
→ Critical E2E
→ validated propagation
→ remaining modules
→ GPT / MCP public adapter
→ Security / Regression / Recovery
→ Production Acceptance
```

不要在正式生产实现前重复前端前期研究。

---

# 16. 测试与交付

按变更范围至少执行：

- Unit
- Integration
- DB Migration
- API / Contract
- Permission / Security
- Runtime
- Browser / Critical E2E
- Subject / Domain isolation
- Cache isolation
- Report truth
- Recovery / Rollback

测试失败必须报告真实错误。禁止删除测试、跳过失败、屏蔽异常、制造假数据让状态变绿。

每次交付必须报告：

1. 审计内容
2. 修改内容
3. 修改原因
4. 文件
5. DB/API/Runtime 是否变化
6. 测试与结果
7. Evidence
8. Blocked / Needs Evidence
9. 风险
10. commit / push 状态

禁止只回复“完成”。

---

# 17. 最终不可违反原则

> **真实源码与真实运行证据优先于历史印象。**
>
> **Production Truth 优先于 AI 输出。**
>
> **不重复造轮子。**
>
> **不让 Codex 重做已完成的 Experience V2 前期。**
>
> **能力可以共享，Truth / DB / Runtime / Ownership 不得模糊。**
>
> **主体选择只改变上下文，不改写 Production Truth。**
>
> **没有 Source + Call Graph + Data/API + Consumer + Runtime + Tests + Production Evidence，就不能声明 VERIFIED。**

---

# 18. 2026-09-13 当前进度与新增隔离红线（追加，不覆盖 #0–#17）

> 本节为追加条款，#0–#17 全部继续有效；冲突时以当前真实源码 + 运行证据为准。

## 18.1 当前进度快照（HEAD `0efd15e`，分支 `codex/production-experience-wiring`）

- Experience V2 → Flask 可运行接线已完成：38/44 屏真实只读绑定，AI-01/CTH-01 为生产样板；前端复用既有栈，未引入 React/Vue，未建第二套 Contracts/Registry。
- 本切片 28 测试全过；隔离全量 app 真实 HTTP 集成、深色/浅色 1440 + 真 390 CDP 遍历全绿。
- 4 屏保持 BLOCKED_BY_EXTERNAL_DEPENDENCY（BMP-05/BMP-11/SH-01/SYS-06），2 屏 N/A（ACC-01/04）；禁止为追求数字造假。
- 剩余工作按 `00-GOVERNANCE/handoff/CODEX_REMAINING_WORK_20260913.md` + `CODEX_RESUME_PACK_20260913.json` 的 DAG 执行，**FIRST TICKET = P0-DBISO-01**。

## 18.2 新增红线：DB 隔离三环境变量（来自真实运行，不是推测）

- 写库连接的覆盖变量并不统一：
  - `ZBC_DB_PATH`：canonical，25 处；
  - `ZBC_EVIDENCE_DB_PATH`：仅 `evidence_chain.py:38`（`zbc_evidence` 写入方）；
  - `ZBC_RUNTIME_GUARDIAN_DB`：仅 `runtime_guardian.py:41`；
  - `ai_task_engine.py` / `app_evidence.py` / `ark_llm.py` 无 env 覆盖、硬编码 `data/monitor.db`。
- 因此：**任何测试 / Staging / 隔离运行，必须同时设置上述三个 env 到临时库**；在 P0-DBISO-01 统一为单一 canonical override 之前，不得假设只设 `ZBC_DB_PATH` 即隔离。
- 隔离运行结束必须核对真实库 mtime 与关键表行数不变；若误写，只能用带行数断言的事务精确回滚自己产生的合成行，禁止删真实业务数据。

## 18.3 接手协议（避免重复发现）

- 接手先跑 `git status` / `git branch --show-current` / `git rev-parse HEAD`，与 `CODEX_RESUME_PACK_20260913.json` 的 work_head 比对；一致则禁止重新全仓扫描、禁止重读全部 DB、禁止重做五仓关系与前端前期，直接按 DAG 开工。
- 连续闭环：TICKET → IMPLEMENT → SCOPED TEST → NEIGHBOUR REGRESSION → REQUIRED RUNTIME/E2E → EVIDENCE → ONE-PURPOSE COMMIT → UPDATE STATE → NEXT；无真实 blocker 不得逐票等待确认。
