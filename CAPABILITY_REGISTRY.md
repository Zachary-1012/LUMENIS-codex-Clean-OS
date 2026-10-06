> **HISTORICAL / SUPPORTING CAPABILITY INVENTORY — NOT CURRENT OWNER OR EXECUTION AUTHORITY.**
> Current ownership and activation are defined by `00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md` and root `AGENTS.md`. Statuses below are dated inventory evidence and must be revalidated against current source/runtime before use.

# LUMENIS Capability Registry

状态：Canonical Ownership Registry V1

## 1. 注册规则

每个 Capability 只能有一个 Production Owner 和一个 Canonical Implementation。其他实现只能是 Adapter、Sub-capability、Compatibility、Legacy 或 Candidate，不能同时拥有同一业务真相。

完整记录必须具备：

```text
Capability ID / Name / Product Owner / Domain Owner
Input / Output / Canonical Implementation / Contract
Database / API / Frontend / Permission
Test / Runtime Evidence / Production Evidence
Status / Legacy Consumers / Migration / Rollback
```

状态必须按证据晋级：

```text
PLANNED → IMPLEMENTED → INTEGRATED → TESTED
→ VERIFIED → RELEASED → OPERATING
```

当前多数能力尚不满足七类证据，因此本表的实现路径是“收敛目标”，不是完成声明。

## 2. 核心注册表

| ID | Capability | Owner | Canonical 候选 | 输入 → 输出 | DB / API / UI | Permission | 当前状态 |
|---|---|---|---|---|---|---|---|
| CAP-CORE-001 | Subject Authority | Production Core；CTH 主消费 | `subject_rules.py` + Subject Context Adapter | Source/Profile → subject decision | rules/config → domain query → CTH | 生产保护；Agent 不可绕过 | TESTED / Runtime partial |
| CAP-CORE-002 | Brand Focus | BMP | Brand Profile + request domain context | Brand selection → scoped context | profile/brand data → BMP API/UI | Brand scope permission | IMPLEMENTED / UI blocked |
| CAP-DATA-001 | Evidence Ingestion | Shared | `evidence_chain.py` 候选 | raw source → immutable evidence | Evidence tables/API/view | write gate + lineage | MULTIPLE / P0 |
| CAP-DATA-002 | Canonical Data | Production Core | `canonical_data.py` 候选 | evidence → canonical record | canonical tables/API | deterministic writer only | MULTIPLE / P0 |
| CAP-DATA-003 | Metric Engine | Production Core | `canonical_metrics.py` 候选 | canonical set + time scope → metric | metric/truth API/UI | read-only compute | MULTIPLE / P0 |
| CAP-DATA-004 | Truth Table / View Model | Shared | `ui_view_model.py` | metric/evidence/state → consumer model | viz API → pages/reports | consumer scoped | IMPLEMENTED / partial integration |
| CAP-COL-001 | Collection Orchestration | SYSTEM | 待从 `collector.py/collector_v2` 验证 | schedule/task → collection result | logs/evidence/status UI | Collector Guard | MULTIPLE / NO_RUN |
| CAP-COL-002 | Platform Adapter | SYSTEM | `BasePlatformAdapter` 方向 | platform query/session → raw records | platform tables/API | read-only account boundary | PARTIAL |
| CAP-COL-003 | Browser/CDP | SYSTEM | Browser Surface + Runtime Adapter 待定 | authorized session → page evidence | browser status/API/UI | 永久只读社交操作 | MULTIPLE |
| CAP-COL-004 | Auth Recovery | SYSTEM | Auth Recovery Center | expired session → pause/verify/resume | recovery task/API/modal | user manual verification | PARTIAL |
| CAP-CTH-001 | Event | CTH domain；Shared infra | Event Graph 与 events 需合并 Contract | evidence → event lifecycle | event DB/API/page | domain write + review | MULTIPLE |
| CAP-CTH-002 | Case | CTH/BMP domain | 待从 case implementations 选定 | evidence/events → case | case DB/API/page | reviewer approval | MULTIPLE |
| CAP-CTH-003 | Risk | CTH/BMP domain | `risk_engine.py` + rule registry | canonical facts → risk finding | risk DB/API/page/report | rules own final boundary | PARTIAL |
| CAP-CTH-004 | Decision | CTH/BMP | Decision Record Contract | finding/risk → decision candidate | decision store/API/UI | human approval | PARTIAL |
| CAP-CTH-005 | Action/Outcome | CTH/BMP | Action Firewall + Effect Fence | approved decision → effect/outcome | action/evidence/trace | highest protection | PARTIAL |
| CAP-BMP-001 | Campaign | BMP | Topic Campaign/Propagation Contract 待定 | brand/content/event → campaign state | campaign DB/API/UI | brand scope | MULTIPLE |
| CAP-BMP-002 | Content Intelligence | BMP | Content analysis contract | content/evidence → attributes/findings | content DB/API/UI | fact/AI separation | PARTIAL |
| CAP-BMP-003 | Audience Identity | BMP | KOS identity/attribution contract | account/content/interactions → identity | KOS DB/API/UI | manual correction | MULTIPLE |
| CAP-BMP-004 | Brand Evaluation | BMP | Shared Evaluation Contract | campaign/content/outcome → evaluation | evaluation DB/API/UI | evidence required | MULTIPLE |
| CAP-SHR-001 | Content Creation | Shared | `content_generation.py` 候选 | brief/context/evidence → asset candidate | content store/API/workspace | approval before publish | PARTIAL |
| CAP-SHR-002 | Podcast Production | Shared | Podcast routes/entities pipeline | research/entity/brief → episode asset | podcast DB/API/UI | rights + approval | PARTIAL |
| CAP-SHR-003 | Evaluation | Shared | `evaluation_system.py` 候选 | result/evidence → score/badcase | evaluation store/API | independent evaluator | MULTIPLE |
| CAP-SHR-004 | Learning Asset | Shared | Learning Contract + Heritage Registry | evaluation/feedback → candidate asset | artifact registry | verify before adoption | PARTIAL |
| CAP-AI-001 | AI Gateway | SYSTEM | `ai_channel.py` + Provider Registry 候选 | advisory task → model result/trace | ai logs/API/status | no Production Truth write | TESTED / Runtime disabled |
| CAP-AI-002 | Orchestrator | Cross-product execution | 待收敛唯一入口 | user intent → execution plan | task API/workspace | permission context | MULTIPLE |
| CAP-AI-003 | Skill/Tool Execution | Cross-product execution | Canonical registries 待合并 | plan → bounded tool result | registry/API/trace | allowlist + effect class | MULTIPLE |
| CAP-SEC-001 | Permission | SYSTEM | `permission_gate.py` 候选 | identity/action/context → decision | policy API/audit | fail-close | MULTIPLE |
| CAP-SEC-002 | Action Firewall | SYSTEM | firewall + effect fence | proposed write → allow/deny/effect | evidence/trace | human approval + idempotency | PARTIAL |
| CAP-RUN-001 | Runtime Guardian | SYSTEM | `runtime_guardian.py` 候选 | heartbeat/lease/queue → runtime state | runtime tables/API/UI | operational role | MULTIPLE / UNKNOWN |
| CAP-RUN-002 | Observability | SYSTEM | structured log/metric/trace contract | execution signals → correlated evidence | telemetry/API/UI | sensitive-field policy | PARTIAL |
| CAP-DB-001 | Database Ownership | SYSTEM | `database.py` | canonical write/read → production data | SQLite current / future adapter | migration gate | BASELINE SPLIT |
| CAP-DB-002 | Migration | SYSTEM | 待统一 Alembic/database migrations | schema N → N+1 | migration manifest | backup + human approval | MULTIPLE / bootstrap blocked |
| CAP-API-001 | API Contract | SYSTEM | 待建 machine-readable canonical API | request → typed result/state/error | all consumers | auth + domain scope | PARTIAL |
| CAP-UI-001 | LUMENIS Experience | CTH/BMP | 新 Context-first Design System | view model → decision workspace | Web/Desktop/Mobile | same state contract | DESIGN READY |
| CAP-REP-001 | Report Orchestration | Production Core | 待从 report paths 选唯一入口 | truth table + period → report artifact | reports DB/API/export | deterministic facts + AI advisory | MULTIPLE |
| CAP-REL-001 | Release Lineage | SYSTEM | Release Manifest pipeline | source/profile/schema/tests → artifact | CI/CD/runtime attestation | human release approval | NOT IMPLEMENTED |
| CAP-XR-001 | Shared Intelligence Export | Shared | local outbox + versioned contract | verified asset → contribution | artifact/ACK | no shared DB | PARTIAL / no E2E |

## 3. Canonicalization 判定方法

每个 MULTIPLE 能力必须完成：

```text
Inventory
→ producer/consumer call trace
→ data write/read comparison
→ runtime traffic observation
→ semantic equivalence/difference
→ KEEP / MERGE / ADAPTER / LEGACY decision
→ parallel read or shadow
→ regression
→ migration
→ archive/delete approval
```

不得把“importer=0”“没有页面”“名称带 old/backup”直接判为 DEAD。

## 4. Capability Release Gate

每个 Capability 的 Release Record 至少包含：

- source commit 与 implementation digest；
- input/output/error schema；
- DB owner、读写者与迁移版本；
- API 与 Frontend consumer；
- permission/effect class；
- unit/integration/E2E/security/performance 测试；
-真实 Runtime trace 和生产证据；
- known limits、rollback 与 owner approval。

## 5. 当前结论

Registry 的产品归属已经收敛为 CTH、BMP、Shared、SYSTEM；Canonical Implementation 尚未完成。当前状态为 `OWNERSHIP DEFINED / IMPLEMENTATION RECONCILIATION PARTIAL / PRODUCTION NO-GO`。
