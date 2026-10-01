# LUMENIS Production Acceptance Master Checklist V1

> 中文：序境 / LUMENIS 当前生产验收总表 V1
>
> 目标阶段：Production Convergence → Production Acceptance → Release Candidate → Production / Operating
>
> 本文件是最终收敛阶段的母清单。每次研发、修复、回归、合并或发布准备先解析实时 `origin/main`，再按固定源码 owner 索引审计 active slice；不得把母清单理解为每次重复全仓审计。

## 0. 固定索引与增量审计循环

每次进入本仓库执行研发任务时，必须先执行：

```text
RESOLVE origin/main → READ CURRENT SOURCE OWNER INDEX
→ AUDIT ACTIVE SLICE + CURRENT DIFF → CLASSIFY GAPS
→ IMPLEMENT / FIX → TEST → VERIFY → EVIDENCE
→ UPDATE STATUS / SPEC / INDEX IF CHANGED → RECHECK AFFECTED SLICE
```

禁止依赖历史报告、旧 README、旧 commit message 或上一次会话结论直接继续。

必须重新确认：
- 当前 branch / HEAD / working tree
- `00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md` 中 active slice 的 owner / caller / contract / tests
- active slice 的 Production Truth、API、DB、Runtime、UI、Agent、AI、Content 影响
- active slice 的阻塞、测试、Runtime、Evidence 与 Release Lineage

每一轮结束后复查受影响路径，并将未闭环项保留在 Pending / Blocked / Needs Evidence 中。只有索引 owner 缺失/冲突、跨域 owner 或 DB/API/Auth/Permission/Evidence/Collector 边界改变、引入未分类外部资产、结构校验失败，或产品 Owner 明确要求时，才触发全仓源码重审。

### 三类验收维度（不是三回执行，映射 C1–C6）

1. **App Experience：** UI、布局、PC/移动语义重组、UX 动效和真实现有绑定；不得从 Apple、ChatGPT、TRAE 参考推导新功能或通用 44 屏模板。
2. **Backend / Recovery：** 按现有 owner 找回、适配并接通功能；自有 AI 归 SYSTEM AI Gateway；旧本地模型/智谱/OpenCode 模型调用已停止、接口保留；平台沿用获准 Cookie/session/browser 链；Codex/Cloud 仅作研发。
3. **Closed-loop internal beta：** 用真实授权数据完成 UI Entry → Action → API → Canonical Result → Evidence/Trace → Return/Evaluation → E2E / recovery / release evidence。

LUMENIS 产品账号密码重设计延后至产品工程闭环后；内测前和内测阶段不得以产品账号墙阻断现有产品。平台 Cookie/session 与产品账号是两类身份，后端 Permission 和 effect fence 始终保留。

## 1. 产品结构

- 母产品：序境 / LUMENIS
- CTH：序境·商业运营 / LUMENIS Commerce Operations，Subject-first
- BMP：序境·品牌市场 / LUMENIS Brand & Market，Brand-first / Primary Focus
- Shared Capability：序境·内容创作 / LUMENIS Content & Creation
- Agent Groups：Cross-Product Execution & Collaboration，不是第三产品

## 2. Production Truth 核心链

```text
External Data → Evidence → Canonical Data → Function → Metric
→ Truth Table → View Model → Dynamic Visualization
→ UI / Report / Export
```

业务闭环：

```text
Source → Evidence → Event → Case → Finding / Insight
→ Decision → Action → Outcome → Evaluation / Feedback → Learning Asset
```

任意一环无真实证据时，不得声明 Production Truth 完成。

## 3. CTH 验收

必须验证：
- Subject Selector
- Subject Scope
- SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS / subject_hit() 语义兼容
- Content / Campaign / Public Opinion / Risk
- KOS / KOL / KOC / UGC
- Research / Report / Decision / Export
- 选择 Subject 只改变上下文，不改写 Canonical Data 与历史事实

## 4. BMP 验收

必须验证：
- Primary Brand / Brand Selection
- Competitor / Market / Multi-platform
- Content Analysis / Consumer Demand
- Event / Risk / Benchmark / Report
- 品牌范围与数据归属不串线

## 5. CTH × BMP 双领域隔离

P0：
- Route Isolation
- Permission Isolation
- Scope Isolation
- DB Ownership
- Report Isolation
- Search Isolation
- Agent Context Isolation
- Shared Capability 不改变 Ownership

## 6. Content & Creation 共享能力

属于 CTH / BMP 共享能力，不是独立第三产品。

当前知识与方法资产包括并持续扩充：
- Xiaohongshu Content Intelligence
- StoryFM → Narrative Documentary Engine
- 凉子访谈录 → Deep Interview Engine
- Positive Psychology / Happier → Human Meaning / Emotion Layer
- Episode Reverse Engineering
- Viral Intelligence
- Failure Intelligence
- Platform Adaptation
- Content Evaluation

生产链目标：

```text
Brief → Fact Contract → Research → Scene / Audience
→ Story / Interview / Content Strategy → Draft
→ Platform Adaptation → Evaluation → Revision
→ Human Approval → Publish → Performance → Learning
```

红线：不得编造时间、价格、规则、活动事实；不得未经审批自动发布；不得大段复制研究案例。

## 7. AI Runtime

```text
Production Truth → Intelligence Router
├─ Approved owned weights / training / inference
├─ Retired interfaces (inactive)
└─ Deterministic functions / explicit failure recovery
```

必须验证：Owned Runtime / Router / 外部模型 API 关闭后的独立完成 / Structured Output / Grounding / Recovery / Cost Guard / Resource Guard / Trace。不得回退到停用 provider；Codex Cloud 不证明产品推理服务已部署。

AI 不可用时确定性流程和恢复仍须成立；必需分析的 Job 不能用不可用或摘录过关，C2 必须产出有用的自有推理结果。

## 8. AI 产品闭环六项

最终闭环前必须逐项 VERIFIED：Chat Memory、Context Manager、Tool Calling Framework、Prompt / Skill Registry、Evaluation System、Model Routing。

缺任一项不得声明 AI Chat Experience COMPLETE。

## 9. Skill

```text
Skill Registry → Skill Contract → Permission → Execution
→ Evidence → Evaluation → Trace
```

文件存在不等于 Skill 可用。

## 10. Agent Runtime

```text
Task → Permission → Action Firewall
→ Effect Fence / Idempotency → Execute
→ Evidence → Evaluation → Trace
```

必须验证 READ / TASK / AUDIT / WRITE / ACTION / RETRY / FAIL / CANCEL / RECOVERY / EVIDENCE / TRACE。AI / Agent 不得直接绕过权限修改 Production Truth。

## 11. Collector / 多平台数据

```text
Collector → Session / Auth → Fetch → Normalize
→ Evidence → Canonical → Event / Content
```

必须验证 Login State / Cookie / Browser / CDP / Retry / Cooldown / Circuit Breaker / Checkpoint / Resume / Heartbeat / Last Successful Collection / Failure Trace / Duplicate handling / Platform Mapping。

## 12. 数据最小化与合规

允许最小字段：标题、发布时间、互动数据、内容分析、链接、必要结构化元数据。默认不保存原始视频、原始图片和不必要个人信息。部署地区规则：Mainland China / Hong Kong / Overseas。

## 13. Database / Schema

每张表必须明确：Owner / Meaning / Writer / Reader / Canonical ID / Lifecycle / Migration / Retention。

旧表、字段、API、脚本、UI 必须经过：

```text
Inventory → Dependency Trace → Runtime Verification
→ KEEP / MERGE / MIGRATE / LEGACY / ARCHIVE / DELETE
→ Regression → Evidence
```

## 14. API

```text
Route → Auth → Permission → Input Contract
→ Service → DB → Output Contract → Frontend Consumer
```

重点审计：orphan API / UI drift / API drift / duplicate blueprint / legacy endpoint / hidden fallback / fake 200。

## 15. UI / UX

要求：PC / Tablet / Mobile 自适应；2–4 层信息架构；Drill-down；Trend / Cards / Tables / Evidence / Insight / Action；动态模块与动效。

UI 必须只是 Production Truth 的真实 View，状态来自真实 API / State Contract，禁止假完成、假指标、假 Runtime、假测试、假部署状态。

**历史功能恢复时，本节优先于历史 UI。Legacy code is a capability source, not a UI source.**

## 16. Reports

覆盖 Daily / Special Report / Campaign / KOS / Public Opinion / Research / Evaluation / Operations。

```text
Metric → Evidence → Finding → Risk / Insight → Action
```

## 17. Evidence

```text
Source → Evidence ID → Canonical Object
→ Finding → Decision → Action
```

必须支持 timestamp / provenance / identity or hash / source / relation / trace / audit。

## 18. Runtime

必须验证 Process / Worker / Queue / Lease / Scheduler / DB / Collector / Browser / Provider / Agent / Recovery 的真实状态。

## 19. Security

```text
Edge → Application → Auth → Permission
→ Agent Tool Firewall → Data → Runtime → Supply Chain
```

至少验证 auth / permission / injection / malicious input / path traversal / secret exposure / unsafe agent action / rollback / audit log。

## 20. Reliability / Recovery

必须测试 Crash / Network Fail / DB Lock / Provider Down / Collector Fail / Browser Fail / Partial Data / Restart，并验证 checkpoint / resume / retry / DLQ / cooldown / circuit breaker / idempotency。

## 21. Heritage Recovery / 历史功能找回与 UI 重设计

原则：**恢复历史能力 ≠ 恢复旧产品；恢复功能 ≠ 恢复旧界面。**

历史仓库、历史分支、旧源码、旧数据库结构、旧 API、旧测试和旧文档可以作为“能力证据源”，用于找回曾经真实存在但当前缺失或退化的功能；不得因为当前 Clean OS 没有某个入口就直接判定该能力从未存在。

功能找回必须执行：

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

允许优先找回和迁移的对象包括：
- 业务逻辑 / Functions / Services
- API / Route Contract 的业务语义
- Data Model / Schema / Migration Knowledge
- Algorithm / Rules / Subject Logic
- State Machine / Permission / Runtime Logic
- Collector / Report / Evaluation / Evidence Logic
- Tests / Fixtures / Acceptance Criteria
- 能证明历史业务意图的页面流程信息

**默认禁止把以下历史 UI 直接恢复为当前最终产品：**
- 旧页面布局与旧导航结构
- 旧 Dashboard / 卡片 / 表格 / 弹窗
- 旧视觉语言、颜色体系、组件外观
- 旧交互流程与旧响应式实现
- 不符合当前 2–4 层信息架构的页面
- 仅因“以前能用”而复制回来的历史模板

旧 UI 只能用于识别：缺失业务入口、信息需求、用户任务、状态与功能语义；**不能作为最终视觉实现来源。**

所有找回功能的最终 UI / UX 必须在当前 LUMENIS Design System 下重新设计，并满足：

```text
Real Business Hierarchy
→ 2–4 Layer Information Architecture
→ Drill-down
→ Trend / Card / Table / Dynamic Visualization
→ Evidence
→ Insight
→ Action
→ Runtime State
→ Motion / Interaction
→ PC / Tablet / Mobile Responsive
```

同时必须满足：
- UI 只消费当前真实 API / State Contract；
- UI 不得改变 Canonical Data / Production Truth；
- CTH / BMP 的 Domain、Scope、Permission、Data Ownership 必须保持隔离；
- Shared Capability 可以复用能力，但不得导致 UI、数据或权限串线；
- 不复制外部产品 UI，也不机械复制历史 LUMENIS UI；
- 页面、API、Data Model、Runtime State 必须同步演进；
- 找回功能必须通过当前 E2E、响应式、交互、数据真实性与 Evidence 验收后才可晋级 VERIFIED。

**硬规则：Legacy code is a capability source, not a UI source. Historical UI/UX may only be used as evidence of missing business intent. Final UI/UX must be redesigned under the current LUMENIS design system and current information architecture.**

### 21.1 Developer Settings / 开发者功能恢复保护（Post-Launch Upgrade）

`系统设置 → 开发者 / Developer` 作为既有产品能力的恢复保护项处理，同时明确调整为 **Post-Launch Upgrade / 上线后升级项**。

**当前 Production Convergence → Production Acceptance → Release Candidate → 首次 Production / Operating 阶段，不要求 Developer Settings 完成恢复，也不得把其未恢复状态视为当前六大 Production Acceptance Gate 的阻塞项。**

当前阶段只执行三件事：保护历史资产、禁止误删、避免新增依赖。不得因为当前源码中没有入口或命名命中，就认定该功能不存在、废弃或允许删除；但也不得为了赶首发强行恢复 Developer Settings，从而打断当前生产收敛主线。

调度标签：`POST_LAUNCH_BACKLOG / POST_LAUNCH_UPGRADE`。该标签仅表示研发调度阶段，**不替代**第 32 节统一能力状态 `PLANNED / IMPLEMENTED / TESTED / VERIFIED / RELEASED / OPERATING`。

首次正式上线并完成稳定性观察后，再启动 Developer Settings 的完整恢复。恢复时不得跳步，完整链路固定为：

```text
Post-Launch Stability Confirmation
→ Current Source Audit
→ Historical Repository / Branch / Commit Inventory
→ Developer Feature Source Trace
→ Route / API / Service / DB / Config / Permission / Runtime Dependency Trace
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
→ Unit / Integration / Permission / Security Tests
→ Critical E2E
→ Evidence
→ Re-Audit
→ VERIFIED only after all gates pass
```

恢复范围必须以真实历史代码审计结果为准，不凭记忆预设功能清单。审计时至少覆盖所有与 Developer / Dev / Settings / System / Debug / Runtime / Provider / Model / Agent / Skill / Tool / API / Collector / Browser / Feature Flag / Experimental / Diagnostics / Logs / Evidence / Test / Environment / Import-Export / Permission 等开发者能力相关的入口、路由、组件、服务、配置、表、脚本、测试和历史调用链，防止因名称变化而漏检。

开发者能力恢复必须遵守以下硬规则：
- **不丢功能**：任何有真实历史 Source / Call Graph / Test / Runtime / Evidence 支撑的能力，在完成依赖追踪前不得删除或忽略；
- **不盲目复活**：历史能力如已有当前等价实现，必须合并语义、去重，不制造第二套并行系统；
- **不恢复旧 UI**：历史设置页仅作为业务意图与入口证据；最终入口统一归入当前 `系统设置 / Settings` 信息架构，Developer UI 必须重新设计；
- **不暴露生产秘密**：API Key、Token、Cookie、Secret、生产凭据不得明文显示、写入前端、日志、测试或仓库；只允许安全注入、掩码显示和受控更新；
- **不绕过权限**：Developer 功能不得成为绕过 Auth / Permission / Agent Tool Firewall / Effect Fence / Human Approval 的后门；
- **不伪造状态**：Provider、Runtime、Agent、Collector、Browser、DB、测试、部署、Feature Flag 状态必须来自真实 State Contract / Health / Evidence；
- **不破坏双领域隔离**：CTH / BMP 的 Scope、Data Ownership、Permission、Report、Agent Context 不得因 Developer 工具串线；
- **不制造 Runtime 前置依赖**：开发者页面不可用、未恢复或处于升级中时，不得导致序境核心生产链停止；
- **危险操作必须受控**：任何写入、重置、迁移、清理、重新索引、重新运行、Provider 切换、实验开关等动作必须具备权限、确认、幂等 / Effect Fence、Audit / Trace、失败恢复；
- **默认最小权限**：普通产品用户不应看到或操作仅面向研发/管理员的 Developer 控件；具体角色与可见性以当前权限模型审计结果为准。

当前首发阶段的验收规则：

```text
Developer historical assets protected
+ no destructive deletion
+ no unresolved dependency that blocks core Production Runtime
+ no secret / permission regression introduced by deferred state
= NON-BLOCKING FOR INITIAL RELEASE
```

上线后恢复完成标准仍然不是“页面重新出现”，而是：

```text
Historical Capability Evidence
+ Current Source / Call Graph
+ Current API / State Contract
+ Permission / Security Boundary
+ Redesigned Settings UI
+ Runtime Integration
+ Tests / Critical E2E
+ Production Evidence
= VERIFIED
```

因此：**Developer Settings 未恢复不得阻塞首次 RC / Production；但任何历史资产在上线前仍不得未经审计删除。上线稳定后必须按本节完整链路恢复、重设计、调试与验收，未完成前不得宣称该能力 VERIFIED / RELEASED / OPERATING。**

## 22. Research / Learning

Research Asset ≠ Production Capability。

```text
Research → Decision → Design → Implementation
→ Test → Evidence → Promotion
```

## 23. Continuous Learning

```text
Interaction → Evidence → Feedback → Evaluation
→ Learning Record → Memory / Knowledge → Retrieval → Next Output
```

Learning Memory ≠ Production Truth。

## 24. Open Source / Local AI

建议独立 external_open_source 区域：registry / adapters / licenses / runtime / health / benchmarks / evidence / tests。

状态：RESEARCH_ONLY / SHADOW / PRODUCTION_CANDIDATE / PRODUCTION_APPROVED / DEPRECATED / BLOCKED。

生产准入必须验证 License / Weight License / Source Trace / Commercial Use / Dependency License / Runtime / Health / Fallback / Resource Guard / Security / Evidence。

## 25. Autonomous Research

```text
Fixed Budget → Baseline → Experiment → Benchmark
→ Compare → Evidence → Human Approval
```

禁止自动修改 Production。

## 26. Import / Export

Import：Upload → Parse → Schema Validation → Canonical Mapping → Conflict Handling → Evidence。

Export 必须与当前 Truth 一致，覆盖 CSV / Excel / Report / Dashboard Snapshot / API。

## 27. Evaluation

至少覆盖：Data Accuracy / Metric Accuracy / Classification Accuracy / AI Quality / Agent Success / Content Quality / Runtime Reliability / UX / Performance / Security。

没有 Evaluation，不得声明 Learning 可信。

## 28. Performance

必须真实测量 CPU / RAM / SQLite / Browser / Worker / Agent Concurrency / AI Latency。优化原则：Quality × Speed × Resource Efficiency。

## 29. Release Lineage

```text
Source SHA → Build → Artifact → Schema → Profile
→ Tests → Canary → Release
```

最终必须能准确回答：当前运行代码是哪一个 SHA。

## 30. Rollback

```text
Current Release → Failure → Rollback Target
→ DB Compatibility → Restore → Verify
```

不能仅依赖 git checkout。

## 31. Production Acceptance 六大硬门

全部通过才能进入 Production Acceptance / Release Candidate：
1. P0 Blocking = 0
2. Repository Integrity = PASS
3. Production Truth = PASS
4. Runtime + Critical E2E = PASS
5. Security + Recovery = PASS
6. Release Lineage + Rollback = VERIFIED

任意一项未通过，不得声明 Production Ready。

## 32. 功能状态统一

任何能力只允许使用：PLANNED / IMPLEMENTED / TESTED / VERIFIED / RELEASED / OPERATING。

禁止把页面存在、API 存在、测试文件存在、commit message、AI 文字结论当作完成证据。

```text
Source + Call Graph + Data / API + Frontend / Consumer
+ Runtime + Tests + Production Evidence
```

## 33. 最终收敛规则

从本文件生效起，研发优先级由“功能扩张”切换为：

```text
Capability Closure → Runtime Verification
→ Production Acceptance → Release Candidate → Production / Operating
```

除非是明确 P0/P1 缺口或最终收敛所需能力，否则新增功能默认进入 Backlog，不得横向扩张打断当前收敛。

每一轮必须复查当前 HEAD、差异和受影响 owner，更新状态并保留未完成项，直到六大硬门全部通过；正常工作不得重复全仓重审。

> 最终原则：不以文档、页面、测试数量、commit message 或 AI 判断作为完成；只以当前真实 Source、Call Graph、Data/API、Runtime、Tests 与 Production Evidence 为准。
