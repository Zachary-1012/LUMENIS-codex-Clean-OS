# LUMENIS Production Acceptance Master Checklist V1

> 中文：序境 / LUMENIS 当前生产验收总表 V1
>
> 目标阶段：Production Convergence → Production Acceptance → Release Candidate → Production / Operating
>
> 本文件是最终收敛阶段的母清单。每次研发、修复、审计、回归、合并、发布准备前，必须先读取并重新审计当前仓库真实状态，直到最终收敛完成。

## 0. 强制审计循环

每次进入本仓库执行研发任务时，必须先执行：

```text
READ CURRENT REPO → AUDIT CURRENT TRUTH → CLASSIFY GAPS
→ IMPLEMENT / FIX → TEST → VERIFY → EVIDENCE
→ UPDATE STATUS → RE-AUDIT
```

禁止依赖历史报告、旧 README、旧 commit message 或上一次会话结论直接继续。

必须重新确认：
- 当前 branch / HEAD / working tree
- 当前 README / AGENTS / Governance
- 当前 Production Truth 链
- 当前 API / DB / Runtime / UI / Agent / AI / Content 状态
- 当前 P0 / P1 / P2 阻塞
- 当前测试、Runtime、Evidence 与 Release Lineage

每一轮结束后必须再次审计，并将未闭环项保留在 Pending / Blocked / Needs Evidence 中，直到六大 Production Acceptance Gate 全部通过。

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
├─ Local AI
├─ Approved Cloud Provider
└─ Deterministic Rules / No-AI
```

必须验证：
- Provider Health
- Router
- Local Runtime
- ZERO_CLOUD / cloud-off independence
- Structured Output
- Hallucination Guard
- Fallback
- Cost Guard
- Resource Guard
- Trace

AI 不可用时核心生产流程仍必须成立。

## 8. AI 产品闭环六项

最终闭环前必须逐项 VERIFIED：
1. Chat Memory
2. Context Manager
3. Tool Calling Framework
4. Prompt / Skill Registry
5. Evaluation System
6. Model Routing

缺任一项不得声明 AI Chat Experience COMPLETE。

## 9. Skill

必须形成：

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

必须验证 READ / TASK / AUDIT / WRITE / ACTION / RETRY / FAIL / CANCEL / RECOVERY / EVIDENCE / TRACE。

AI / Agent 不得直接绕过权限修改 Production Truth。

## 11. Collector / 多平台数据

```text
Collector → Session / Auth → Fetch → Normalize
→ Evidence → Canonical → Event / Content
```

必须验证：
- Login State / Cookie
- Browser / CDP
- Retry / Cooldown / Circuit Breaker
- Checkpoint / Resume
- Heartbeat / Last Successful Collection
- Failure Trace
- Duplicate handling
- Platform Mapping

## 12. 数据最小化与合规

允许最小字段：标题、发布时间、互动数据、内容分析、链接、必要结构化元数据。
默认不保存原始视频、原始图片和不必要个人信息。
部署地区规则：Mainland China / Hong Kong / Overseas。

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

## 16. Reports

覆盖 Daily / Special Report / Campaign / KOS / Public Opinion / Research / Evaluation / Operations。

每个报告必须满足：

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

必须测试 Crash / Network Fail / DB Lock / Provider Down / Collector Fail / Browser Fail / Partial Data / Restart。

并验证 checkpoint / resume / retry / DLQ / cooldown / circuit breaker / idempotency。

## 21. Heritage Recovery

原则：恢复历史能力 ≠ 恢复旧产品。

```text
Historical Asset → Source Trace → Current Equivalent Audit
→ Semantic Dedup → Current Production Line Mapping
→ Capability Promotion → Implementation → Tests → Evidence
```

旧 IA / 旧模板 / 旧设计不得重新成为默认产品架构。

## 22. Research / Learning

Research Asset ≠ Production Capability。

必须经过：

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

Auto Research / Performance Race / Execution Efficiency / Interaction Model Research 属于研发基础设施。

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

必须真实测量 CPU / RAM / SQLite / Browser / Worker / Agent Concurrency / AI Latency。

优化原则：Quality × Speed × Resource Efficiency。

## 29. Release Lineage

必须建立：

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

任何能力只允许使用：

```text
PLANNED
IMPLEMENTED
TESTED
VERIFIED
RELEASED
OPERATING
```

禁止把页面存在、API 存在、测试文件存在、commit message、AI 文字结论当作完成证据。

完成标准：

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

每一轮必须重新审计当前仓库真实状态、更新状态、保留未完成项并继续下一轮，直到六大硬门全部通过。

> 最终原则：不以文档、页面、测试数量、commit message 或 AI 判断作为完成；只以当前真实 Source、Call Graph、Data/API、Runtime、Tests 与 Production Evidence 为准。
