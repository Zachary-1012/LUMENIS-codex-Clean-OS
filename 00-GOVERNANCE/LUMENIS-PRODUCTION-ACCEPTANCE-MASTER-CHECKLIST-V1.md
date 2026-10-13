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

LUMENIS 产品账号体系（免费邮箱验证码、Google 登录；Apple 登录待开发者账号开通后启用）闭环内实现；任何阶段不得以产品账号墙阻断现有产品。平台 Cookie/session 与产品账号是两类身份，后端 Permission 和 effect fence 始终保留。

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

### 21.1 Developer Settings / 两类开发者模式（闭环内）

账号体系、两种开发者模式、六项商业能力、视觉、Logo和角色均纳入当前工程闭环，不设置账号墙。仅真实用户验证及付费/授权来源后置；源码、真实操作、安全、保存和恢复的工程验收不得后置。六项商业能力逐一覆盖：数据治理与合规、密钥凭据治理、合同与版本兼容、保留/备份/灾难恢复、租户/工作区生命周期、商业运营。

- **用户开发者模式**：默认关闭；开启前明确风险、经审核的条款、版本化同意与备份。用户可关闭并停用扩展、恢复官方状态，保留修改与备份；未登录也能进行允许的本地备份。未经审核的免责草案不能被当作有效法律结论或启用凭据。
- **创始人内部开发者模式**：限制角色与服务端权限，代码包/分支输入可追溯；构建、适用测试、安全与真实运行要求通过才允许发布；签名、分批更新、暂停及可验证回滚均有真实路径。需求纳入不构成本轮部署、购买账号或费用授权。
- **复用与恢复**：先追踪已有入口、调用者、配置、权限、版本与历史有效行为，复用现有Owner。没有入口不能据此删除原能力；已经有当前等价实现则合并语义，不新建系统。
- **安全**：密钥/会话不进入客户端、日志或仓库；开发者模式不能绕过服务端Permission、Effect Fence、业务域隔离及源码权益。危险操作保持确认、幂等、审计与失败恢复。
- **体验**：设置分区结构可参考成熟产品，视觉与资产为序境原创；Desktop、Web、iOS按现有合同表达操作差异，中/英/韩及无障碍齐全。

验收链：现有能力与调用追踪 → 当前Owner/合同 → 有界实现 → 构建/适用回归/权限安全 → 实际操作 → 保存/关闭/重开/恢复 → Evidence。未验收为OPEN，不能以历史保护、页面存在或CI通过代替VERIFIED；某项缺口不阻断无依赖工作。

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
