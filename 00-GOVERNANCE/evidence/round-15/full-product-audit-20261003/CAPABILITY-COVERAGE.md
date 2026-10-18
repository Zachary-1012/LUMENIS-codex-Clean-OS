# 全仓覆盖附录｜2026-10-03

全量 Git 路径盘点 + 现有 Owner/入口/调用链核对。不是逐行形式化证明或全部运行验收。下面的设计/绑定状态是现存文件中的声明，保留时间漂移风险，不提升为运行 PASS。

## 全部顶层目录

| 目录 | 跟踪文件数 | 审计归属 |
|---|---:|---|
| `.agents` | 18 | M/既有规则与合同 Owner；历史和当前分层 |
| `[root files]` | 260 | M/C6 按 Source Owner Index；根兼容调用/产物保留，未经行为核对不删除 |
| `.github` | 2 | C6/能力 Owner；验证/工具/CI，不当作用户成果 |
| `.opencode` | 1 | M/既有规则与合同 Owner；历史和当前分层 |
| `00-GOVERNANCE` | 304 | M/既有规则与合同 Owner；历史和当前分层 |
| `02-ARCHITECTURE` | 2 | M/既有规则与合同 Owner；历史和当前分层 |
| `CHANGELOG` | 1 | M/既有规则与合同 Owner；历史和当前分层 |
| `account` | 15 | C1/C6 SYSTEM；账号重构后置，既有安全不可跳过 |
| `account_keepalive` | 3 | C1/C6 SYSTEM；账号重构后置，既有安全不可跳过 |
| `ad_intelligence` | 22 | C1/C3/C5；研究与广告情报，资料存在不代表训练/接入 |
| `agent_adaptive_ui` | 4 | C2；C6 运行边界 |
| `agent_bridge` | 5 | C2；C6 运行边界 |
| `agent_capability` | 6 | C2；C6 运行边界 |
| `agent_focus` | 4 | C2；C6 运行边界 |
| `agent_memory` | 8 | C2；C6 运行边界 |
| `agent_proactive` | 5 | C2；C6 运行边界 |
| `agent_research` | 7 | C2；C6 运行边界 |
| `agent_runtime` | 8 | C2；C6 运行边界 |
| `agent_situational` | 4 | C2；C6 运行边界 |
| `agent_smart_tool` | 4 | C2；C6 运行边界 |
| `alembic` | 4 | C6；配置/DB/运行，data 路径存在不代表本次写入 |
| `app` | 420 | F / C6；对应业务 Owner 提供合同 |
| `config` | 18 | C6；配置/DB/运行，data 路径存在不代表本次写入 |
| `contracts` | 205 | M/既有规则与合同 Owner；历史和当前分层 |
| `core` | 3 | C6；配置/DB/运行，data 路径存在不代表本次写入 |
| `data` | 6 | C6；配置/DB/运行，data 路径存在不代表本次写入 |
| `deployment` | 15 | C6；配置/DB/运行，data 路径存在不代表本次写入 |
| `docker` | 1 | C6；配置/DB/运行，data 路径存在不代表本次写入 |
| `docs` | 145 | M/既有规则与合同 Owner；历史和当前分层 |
| `intelligence_library` | 384 | C1/C3/C5；研究与广告情报，资料存在不代表训练/接入 |
| `lumenis` | 278 | CTH/BMP/Shared/SYSTEM 按现有 Owner 分布 C1-C6 |
| `migrations` | 5 | C6；配置/DB/运行，data 路径存在不代表本次写入 |
| `output` | 5 | M/C6 按 Source Owner Index；根兼容调用/产物保留，未经行为核对不删除 |
| `podcast` | 21 | C4/C5；Shared 产物 |
| `proxy_pool` | 9 | C1/C6 SYSTEM；账号重构后置，既有安全不可跳过 |
| `report_export` | 11 | C4/C5；Shared 产物 |
| `research` | 43 | C1/C3/C5；研究与广告情报，资料存在不代表训练/接入 |
| `scripts` | 84 | C6/能力 Owner；验证/工具/CI，不当作用户成果 |
| `tests` | 491 | C6/能力 Owner；验证/工具/CI，不当作用户成果 |
| `tmp` | 1 | M/C6 按 Source Owner Index；根兼容调用/产物保留，未经行为核对不删除 |
| `vendor` | 67 | 现有第三方登记/许可证及调用方；不整体替换序境 |
| `website` | 19 | F / C6；对应业务 Owner 提供合同 |

## 全部屏幕规格文件

44 个历史屏幕义务继续保留；屏幕数不限定未来任务布局。新增/现有规格文件均逐项盘点。设计通过与业务绑定通过分开。

| ID | 所属 | 业务设计 | 呈现设计 | 文件声明状态 |
|---|---|---|---|---|
| ACC-01 | SYSTEM / Experience entry | DESIGN_READY | NOT_DECLARED | DESIGN_READY |
| ACC-02 | SYSTEM settings / CTH Subject Registry / BMP BrandFocus | BLOCKED | NOT_DECLARED | BLOCKED |
| ACC-03 | SYSTEM / Shared Capability presentation | DESIGN_READY | NOT_DECLARED | DESIGN_READY |
| ACC-04 | SYSTEM Permission / recovery boundary | DESIGN_READY | NOT_DECLARED | DESIGN_READY |
| AI-01 | Shared Capability / AI Agent Groups | BLOCKED | DESIGN_READY | BLOCKED |
| AI-02 | Shared Capability / AI Agent Groups | BLOCKED | NOT_DECLARED | BLOCKED |
| AI-03 | Shared Capability / Evidence-linked AI analysis | BLOCKED | NOT_DECLARED | BLOCKED |
| AI-04 | Shared Capability / Agent Skills registry | BLOCKED | NOT_DECLARED | BLOCKED |
| AI-05 | SYSTEM AI Gateway / runtime diagnostics | BLOCKED | NOT_DECLARED | BLOCKED |
| BMP-01 | BMP | BLOCKED | NOT_DECLARED | REVIEWED_FOR_SCOPE_BLOCKED_SLICE |
| BMP-02 | BMP | DESIGN_EXPLORATION | NOT_DECLARED | BLOCKED |
| BMP-03 | BMP | DESIGN_EXPLORATION | DESIGN_READY_BOUNDED_SIGNAL_BRIEF_RETURN | BLOCKED |
| BMP-04 | BMP | DESIGN_EXPLORATION | NOT_DECLARED | BLOCKED |
| BMP-05 | BMP | DESIGN_EXPLORATION | NOT_DECLARED | BLOCKED |
| BMP-06 | BMP | BLOCKED | NOT_DECLARED | OWNER_REVIEW |
| BMP-07 | BMP | BLOCKED | NOT_DECLARED | OWNER_REVIEW |
| BMP-08 | BMP | BLOCKED | DESIGN_READY | OWNER_REVIEW |
| BMP-09 | BMP | BLOCKED | NOT_DECLARED | OWNER_REVIEW |
| BMP-10 | BMP | BLOCKED | NOT_DECLARED | OWNER_REVIEW |
| BMP-11 | BMP | BLOCKED | NOT_DECLARED | OWNER_REVIEW |
| CTH-01 | CTH | BLOCKED | NOT_DECLARED | BLOCKED |
| CTH-02 | CTH | BLOCKED | NOT_DECLARED | BLOCKED |
| CTH-03 | CTH | BLOCKED | DESIGN_READY_BOUNDED_READABLE_SOURCE_TIME | BLOCKED |
| CTH-04 | CTH | BLOCKED | NOT_DECLARED | BLOCKED |
| CTH-05 | CTH | BLOCKED | NOT_DECLARED | BLOCKED |
| CTH-06 | CTH | BLOCKED | NOT_DECLARED | BLOCKED |
| CTH-07 | CTH | BLOCKED | NOT_DECLARED | BLOCKED |
| CTH-08 | CTH | DESIGN_EXPLORATION | NOT_DECLARED | BLOCKED |
| CTH-09 | CTH | DESIGN_EXPLORATION | NOT_DECLARED | BLOCKED |
| CTH-10 | CTH / Shared Capability Reporting | DESIGN_READY | NOT_DECLARED | BLOCKED |
| README.md (辅助文件) | NOT_DECLARED | NOT_DECLARED | NOT_DECLARED | NOT_DECLARED |
| <SCREEN-ID> | UNKNOWN | PENDING | NOT_DECLARED | DESIGN_EXPLORATION |
| SH-01 | Shared Capability | BLOCKED | DESIGN_READY_BOUNDED_FOUR_ITEMS | IMPLEMENTED_CATALOG_ONLY_EVIDENCE_SCOPE_BLOCKED |
| SH-02 | Shared Capability | BLOCKED | DESIGN_READY | IMPLEMENTED_SCOPE_GUARDED_BACKEND_SCOPE_UNVERIFIED |
| SH-03 | Shared Capability | BLOCKED | NOT_DECLARED | IMPLEMENTED_SCOPE_GUARDED_BACKEND_SCOPE_UNVERIFIED |
| SH-04 | Shared Capability | BLOCKED | NOT_DECLARED | IMPLEMENTED_SCOPE_GUARDED_EFFECT_UNVERIFIED |
| SH-05 | Shared Capability | BLOCKED | NOT_DECLARED | IMPLEMENTED_SCOPE_GUARDED_PROMOTION_READ_ONLY |
| SH-06 | Shared Capability | BLOCKED | NOT_DECLARED | IMPLEMENTED_SCOPE_GUARDED_OPERATIONAL_READ_ONLY |
| SYS-01 | SYSTEM / RuntimeGuardian | DESIGN_READY | NOT_DECLARED | APPROVED |
| SYS-02 | SYSTEM Collector | DESIGN_EXPLORATION | NOT_DECLARED | DESIGN_EXPLORATION |
| SYS-03 | SYSTEM / Canonical Data | DESIGN_EXPLORATION | NOT_DECLARED | DESIGN_EXPLORATION |
| SYS-04 | SYSTEM Permission | DESIGN_EXPLORATION | NOT_DECLARED | DESIGN_EXPLORATION |
| SYS-05 | SYSTEM Settings | DESIGN_READY | DESIGN_READY | DESIGN_READY |
| SYS-06 | SYSTEM Browser / CDP | DESIGN_EXPLORATION | NOT_DECLARED | DESIGN_EXPLORATION |
| SYS-07 | SYSTEM Security / AI Gateway | DESIGN_EXPLORATION | NOT_DECLARED | DESIGN_EXPLORATION |
| SYS-08 | SYSTEM Observability | DESIGN_EXPLORATION | NOT_DECLARED | DESIGN_EXPLORATION |

## 全部现存 Backend Gap 行

以下是现有 54 行合同账本的逐项保留，不是本轮重新执行 54 项 E2E。部分账本仍落后于本地候选/新的开放入口规则，恢复开发后由该行 Owner 与 F/W6 用实际入口校正。不得据此批量制造 API 或把所有状态改绿。

| Gap | Screen / field | Owner | 源码声明 | 前端声明 | 验收声明 |
|---|---|---|---|---|---|
| BACKEND-GAP-001 | ACC-01 / auth | SYSTEM / Account | PARTIAL | DUAL_AUTH_CLIENT_TESTED_LIVE_UNVERIFIED | PENDING |
| BACKEND-GAP-002 | ACC-02 / subjects | CTH / SYSTEM Permission | PARTIAL | CTH_REGISTRY_SELECTION_TESTED_LIVE_UNVERIFIED | PENDING |
| BACKEND-GAP-003 | ACC-03 / launch | SYSTEM | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-004 | ACC-04 / guard | SYSTEM / Account | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-005 | CTH-01 / kpis | CTH | PARTIAL | CTH01_KPI_UI_TESTED_LIVE_UNVERIFIED | PENDING |
| BACKEND-GAP-006 | CTH-01 / events | CTH | PARTIAL | CTH01_EVENT_UI_TESTED_LIVE_UNVERIFIED | PENDING |
| BACKEND-GAP-007 | CTH-01 / insight | CTH | PARTIAL | CTH01_INSIGHT_UI_TESTED_LIVE_UNVERIFIED | PENDING |
| BACKEND-GAP-008 | CTH-02 / brands | CTH | PARTIAL | SELECTION_DIRECTORY_UI_TESTED_FULL_PROFILE_BLOCKED_LIVE_UNVERIFIED | PENDING |
| BACKEND-GAP-009 | CTH-03 / stream | CTH | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-010 | CTH-04 / graph | CTH | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-011 | CTH-05 / calendar | CTH | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-012 | CTH-06 / items | CTH | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-013 | CTH-07 / trend | CTH | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-014 | CTH-08 / cases | CTH | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-015 | CTH-09 / risk | CTH | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-016 | CTH-09 / decision | CTH | ABSENT | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-017 | CTH-10 / report | CTH / Shared Evidence | EXISTS_BUT_UNSCOPED | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-018 | BMP-01 / all | BMP | PARTIAL | BMP01_BRANDFOCUS_FAIL_CLOSED_UI_TESTED_LIVE_UNVERIFIED | PENDING |
| BACKEND-GAP-019 | BMP-02 / brands | BMP | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-020 | BMP-03 / intel | BMP | EXISTS_BUT_UNSCOPED | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-021 | BMP-04 / channels | BMP | EXISTS_BUT_UNSCOPED | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-022 | BMP-05 / creators | BMP | EXISTS_BUT_UNSCOPED | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-023 | BMP-06 / assets | BMP / Shared Evidence | EXISTS_BUT_UNSCOPED | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-024 | BMP-07 / campaign | BMP | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-025 | BMP-08 / podcast | BMP | EXISTS_BUT_UNSCOPED | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-026 | BMP-09 / eval | BMP / Shared Evaluation | EXISTS_BUT_UNSCOPED | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-027 | BMP-10 / risk | BMP | EXISTS_BUT_UNSCOPED | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-028 | BMP-11 / benchmark | BMP | EXISTS_BUT_UNSCOPED | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-029 | AI-01 / composer | Shared Capability / SYSTEM Permission | PARTIAL | AI01_SUBMIT_DISABLED_GUARD_TESTED_LIVE_UNVERIFIED | PENDING |
| BACKEND-GAP-030 | AI-01 / providers | SYSTEM / AI Gateway | PARTIAL | AI01_PROVIDER_UI_TESTED_LIVE_UNVERIFIED | PENDING |
| BACKEND-GAP-031 | AI-02 / task_orchestration | Shared Capability / Agent Groups | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-032 | AI-03 / thread | Shared Capability / AI | ABSENT | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-033 | AI-03 / evidence_jump | Shared Evidence / AI | EXISTS_BUT_UNSCOPED | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-034 | AI-04 / registry | SYSTEM / Agent Groups | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-035 | AI-05 / status | SYSTEM / AI Gateway | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-036 | SYS-01 / health | SYSTEM | PARTIAL | SYS01_STATUS_UI_TESTED_LIVE_UNVERIFIED | PENDING |
| BACKEND-GAP-037 | SYS-02 / collectors | SYSTEM Collector | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-038 | SYS-03 / db | SYSTEM / Canonical Data | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-039 | SYS-04 / perm | SYSTEM Permission | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-040 | SYS-05 / prefs | SYSTEM Settings | LOCAL_ONLY | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-041 | SYS-06 / browser | SYSTEM Browser / CDP | EXISTS_BUT_UNSCOPED | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-042 | SYS-07 / acceptance | SYSTEM Security / AI Gateway | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-043 | SYS-08 / logs | SYSTEM Observability | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-044 | SH-01 / studio | Shared Capability / Content & Creation | PARTIAL | SH01_CATALOG_ONLY_UI_TESTED_LIVE_UNVERIFIED | PENDING |
| BACKEND-GAP-045 | SH-01 / pattern_retrieval | Shared Capability / Research | ABSENT | BLOCKED_NOT_EXPOSED | PENDING |
| BACKEND-GAP-046 | SH-01 / fact_wall | Shared Capability / Evidence | ABSENT | BLOCKED_NOT_EXPOSED | PENDING |
| BACKEND-GAP-047 | SH-01 / publish | Shared Capability / SYSTEM Effect | PARTIAL | BLOCKED_NOT_EXPOSED | PENDING |
| BACKEND-GAP-048 | SH-01 / ai_thread | Shared Capability / AI | ABSENT | BLOCKED_NOT_EXPOSED | PENDING |
| BACKEND-GAP-049 | SH-01 / capability_status | Shared Capability | PARTIAL | SH01_CATALOG_STATE_UI_TESTED_LIVE_UNVERIFIED | PENDING |
| BACKEND-GAP-050 | SH-02 / library | Shared Capability / Evidence | EXISTS_BUT_UNSCOPED | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-051 | SH-03 / canonical | SYSTEM / Canonical Data | EXISTS_BUT_UNSCOPED | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-052 | SH-04 / export | Shared Capability / Reporting | PARTIAL | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-053 | SH-05 / assets | Shared Capability / Learning | EXISTS_BUT_UNSCOPED | NO_FLUTTER_SCREEN | PENDING |
| BACKEND-GAP-054 | SH-06 / tasks | SYSTEM TaskEngine | EXISTS_BUT_UNSCOPED | NO_FLUTTER_SCREEN | PENDING |

## R01–R15 / J1–J8 / U01–U25 全量保留

下列复制当前 Owner Index 中每一映射/能力断言作审计覆盖索引；执行权威仍是原文件与 AGENTS。C3/C5 新本地合并不改变这些职责。所有未达到真实出口者保持 OPEN。

### R 验收与技术依赖

| 原检查点 | 完整范围 | 出口 |
|---|---|---|
| R01 **Current truth and PDF coverage** | Remote/local/PDF audit, owner map, protection items and complete 15-round mapping; read-only. | Three-source comparison and every PDF page/task are accounted for; no source mutation. |
| R02 **Authority, Only-One and multi-surface decision** | Reconcile sole authorities, naming, compatibility classification, approved Public Website/Web Workspace/Desktop/Mobile route and Jev placement. | No App-only conflict or duplicate owner; decisions are enforced by blocking governance checks; no Web/Jev runtime is prematurely created. |
| R03 **Database and Canonical Truth** | Database paths, migrations, repository, root callers, direct SQLite and isolated test protection. | One canonical business schema/path and protected migration/rollback evidence. |
| R04 **Identity, context, Permission and Evidence** | Actor identity, Subject/BrandFocus, access timing, read/write/approval/effect fences and lineage. | Context cannot grant authorization; decisions/actions trace to Evidence and Return. |
| R05 **Runtime, health and recovery** | Startup, supervisor, honest health, queue/worker/DLQ, logging, recovery and operations stores. | Health represents real dependencies; failure/recovery paths are tested. |
| R06 **Collector, browser and acquisition** | One collector/browser, scheduler/adapters, Cookie/session/CDP, rate limits, provenance and ingestion. | Authorized source → collection → Evidence closes without duplicate runtime or unsafe browser behavior. |
| R07 **AI, Agent and Shared engines** | One AI Gateway, owned weights/training/inference, Agent/skills, reporting, evaluation and learning; retired providers remain inert. | Useful owned inference, tools, recovery and promotion are proven; Jev/retired providers stay inactive; AI never owns truth/effects. |
| R08 **Cross-Surface Experience Foundation** | Public Website foundation, Flutter Web Workspace/Desktop/Mobile shells, shared contract/state/accessibility/localization and capability boundary. | Four surfaces have distinct roles over one Product Core; no generic screen template or second truth. |
| R09 **Golden Pages and CTH-02** | AI-01, CTH-01/02, BMP-01, SH-01 and SYS-01 with surface matrix and live binding. | Applicable Web/Desktop/Mobile paths complete real tasks with Permission/Evidence and truthful states. |
| R10 **CTH monitoring and analysis** | CTH-03..07 source-backed monitoring, events, calendar, sentiment, trend and trace. | Real Subject-scoped monitoring/analysis closes with source lineage. |
| R11 **CTH case, risk and decision** | CTH-08..10 Case → Insight → Decision → Action → Outcome plus report/export. | Authorized CTH response loop and Evidence lineage are verifiable. |
| R12 **BMP portfolio, market and propagation** | BMP-02..05 BrandFocus, competitor, market intelligence, propagation and creators. | Brand-first workflows preserve source/evidence and scope semantics. |
| R13 **BMP content, campaign and evaluation** | BMP-06..11 content lifecycle, campaign, podcast, evaluation, risk and benchmark. | Approved action/result/evaluation loop is real and traceable. |
| R14 **Remaining ACC, AI, Shared and SYSTEM Experience** | ACC-01..04, AI-02..05, SH-02..06 and SYS-02..08, respecting pre-beta account timing. | Each applicable surface role is explicit; deferred identity capability is honestly blocked/deferred, not simulated. |
| R15 **Closed-loop internal beta and release** | Cross-surface real-data E2E, PC/mobile, security, accessibility, performance, packaging, clean clone, recovery/rollback and release evidence. | Public → Web → real context/workflow/Evidence → Desktop advanced execution if applicable → Web result → Mobile approval/notification if applicable → Report/Evaluation/Learning passes; unresolved items remain explicit. |

### 职责映射

| ID | 负责 / 支持 |
|---|---|
| R01 | M W6 |
| R02 | M W6 |
| R03 | C1 C6 |
| R04 | C1 C2 C5 C6 |
| R05 | C1 C2 C6 |
| R06 | C1 C6 F |
| R07 | C2 C4 C5 |
| R08 | C6 F |
| R09 | C1 C2 C3 C5 C6 F |
| R10 | C1 C3 |
| R11 | C2 C3 C4 C5 |
| R12 | C1 C2 C3 |
| R13 | C2 C3 C4 C5 |
| R14 | C1 C2 C5 C6 F |
| R15 | C6 M Product Owner |
| J1 | C1 C6 |
| J2 | C3 C1 C2 C5 |
| J3 | C3 C1 C2 C5 |
| J4 | C4 C2 C5 F |
| J5 | C4 C2 C5 F |
| J6 | C4 C2 C5 F |
| J7 | C2 C5 |
| J8 | C6 F |

### J 用户工作包

| ID | 用户工作 | Owner | 完整要求 |
|---|---|---|---|
| J1 | Establish, select and continuously maintain the real data universe | C1 C6 | Real Add Subject/BrandFocus, country/market and venue/tenant identities, approved platform-native acquisition and time series, signed Source/Evidence/Canonical, GLOBAL/Focus/Clear, due-only refresh, idempotence and actual scheduled recovery without a Codex/CUA/developer trigger; representative samples do not imply coverage. |
| J2 | Complete a commercial Subject operating decision | C3 C1 C2 C5 | Exact venue/tenant and time scope; monitoring/events, consumer/market/risk analysis, Case -> supported insight -> internal decision -> authorized action where promised -> actual outcome/evaluation and saved result; useful owned analysis, task budget/resource feasibility where costs apply, recovery and return. |
| J3 | Complete a BrandFocus market/content/campaign decision | C3 C1 C2 C5 | Brand/market/competitor/creator/propagation inputs with comparable metrics, grounded analysis, editable Brief and content/campaign lifecycle through creation owners, actual result/evaluation, task budget/resource feasibility where costs apply, saved/reopened output and recovery. |
| J4 | Produce and revise an original professional pitch | C4 C2 C5 F | Real Brief and materials -> original reasoned concept/strategy and budget/resource-feasible alternatives -> editable customer-ready proposal -> review/revision/export/reopen and evaluation; manual and owned-AI paths both work where approved. |
| J5 | Produce and revise an editable video | C4 C2 C5 F | Real permitted media and actual budget/resource constraints -> editable Timeline -> preview/edit/render -> verified playable result and editable project -> review/revision/export/reopen/cancel/recovery; retain approved audio, subtitle, transition and quality requirements. |
| J6 | Produce and revise a usable podcast | C4 C2 C5 F | Research/script/interview-or-story intent with actual budget/resource constraints -> actual audio and complete editable episode -> edit/mix/transcript/chapter/derivative work -> review/export/reopen/evaluation, with script changes distinguished from actual recorded/generated sound. |
| J7 | Turn real materials and goals into reusable knowledge and useful owned-AI work | C2 C5 | Supported file/media intake and precise citations -> actual understanding/research/analysis, extensible case/method combination and task-relevant Discover recommendations -> saved searchable versioned result; actual owned Gateway/Agent/Skills/Memory work and Outcome -> Evaluation -> reviewed Learning -> held-out promotion/rollback. Public discovery and saved examples alone are not training; case mechanisms remain extensible, not a fixed creative template. |
| J8 | Continue and recover the work across approved surfaces and release it | C6 F | Website/Web/Desktop/Mobile roles operate over one Core and saved context/task/result, with required packaging/security/accessibility/performance, same-SHA hosted Product/App, restart/rollback and engineering-ready bundle. PO repeats only when engineering ready; RELEASED and OPERATING need their own evidence. |

### U 能力断言

| ID | 能力 | Owner | 完整要求 |
|---|---|---|---|
| U01 | GLOBAL universe, country categories and continuous entity addition | C1 / C6 F | Versioned approved China/global inclusion rules, retained country candidates/categories and Add Subject/BrandFocus operate; honest coverage/freshness states; no fabricated completed inventory or sample-to-universe promotion. |
| U02 | Exact entity identity, aliases and venue/tenant relations | C1 / C3 | Stable deduplicated Brand/Subject/store identities, exact venue membership and typed Evidence-backed time relations; in-venue monitoring cannot silently expand to every store of the brand. |
| U03 | Headquarters/origin/jurisdiction/operating/marketing/location context | C1 / C3 F | Distinct relation meanings with evidence, dates and review state support market selection; multiple markets preserved without conflating headquarters, legal company, venue or campaign. |
| U04 | Approved platform acquisition and native observations | C1 / C6 | Single-platform requests and approved public/official/session paths ingest real content, authors, times, native metrics/comments/media and provenance into existing truth; unsupported fields remain unavailable, never invented; preserve future official API integration and product-owned operation independent of Codex. |
| U05 | Historical metrics, freshness and incremental maintenance | C1 / C6 | Append actual observations, retain publication/capture/event/derived-time distinctions, refresh only due sources, deduplicate unchanged work and recover failures with lineage; product AUTO remains opt-in except explicitly approved baseline maintenance. |
| U06 | Commercial monitoring, events and calendar | C3 / C1 C5 F | Subject-scoped real monitoring results and source-backed event/calendar work can be inspected and continued; planned versus happened remains distinct. |
| U07 | Consumer, media/social and sentiment/trend intelligence | C3 / C1 C2 C5 | Task-relevant, place/time/platform-matched evidence produces supported interpretations and stated sampling limits; observed posts do not fabricate population satisfaction or causal demand; distinguish measured trends, corpus hotspots, actual platform ranks and source-grounded related works in the existing SH-01 Discover view. |
| U08 | CTH/BMP risk detection and response | C3 / C1 C2 C5 | Traceable risk evidence, context and prioritization enter the existing response/case workflow; uncertainty, false positives, decisions and actual effects stay distinguishable. |
| U09 | Commercial operations, cases, decisions and outcomes | C3 / C2 C5 | Existing Case/Insight/Decision/Action/Outcome/Evaluation objects complete real operating work, retain human/model/source separation, persistence and recovery; a proposal is not an executed action. |
| U10 | Brand portfolio, market and competitor intelligence | C3 / C1 C2 C5 | Exact BrandFocus/market comparison and benchmark use compatible unit/currency/period/denominator, disclose gaps and produce useful decisions; unrelated financial/navigation material cannot pass marketing research. |
| U11 | Creator, channel and propagation intelligence | C3 / C1 C2 C5 | Actual creator/content/channel/native observations and their time relations support decisions; likes, reach, sales attribution and causal lift remain separate claims. |
| U12 | Brand content/campaign lifecycle and evaluation | C3 / C2 C4 C5 F | Editable Brief/content/campaign review, authorized action, observed result and evaluation persist and reopen; actual external publishing needs its existing approval/integration, and an internal stage label is not a campaign result. |
| U13 | Original pitch creation | C4 / C2 C5 F | J4's separate professional proposal result passes factual support, originality, editable delivery, actual revision/recovery and usefulness checks. |
| U14 | Video creation | C4 / C2 C5 F | J5's separate editable project and rendered result pass approved feature coverage, visual quality, audio synchronization, captions, revision/cancel/recovery; a demo clip cannot substitute for the complete promised normal workflow. |
| U15 | Podcast creation | C4 / C2 C5 F | J6's separate playable episode and complete project preserve script/audio identities, segments, chapters, transcripts/corrections, loudness and editing/recovery; text correction alone does not synthesize speech. |
| U16 | Material import, library, search and precise citation | C5 / C2 C1 | Approved files/web/audio/video enter existing Source/Evidence with source purpose, pages/paragraphs/frames/timecodes and scope; material is locatable, understandable, searchable and reopenable without a second truth store. |
| U17 | Research, reports, versioned Artifact and export | C5 / C2 C3 C4 | Actual useful result saves, revises, reopens and exports through current owners; retain per-source permissions, citations, parent/digest, revocation and recovery. Owned/permitted material has a normal path; unknown use rights do not become licensed. |
| U18 | LUMENIS-owned model, inference and multimodal understanding | C2 / C3 C4 C5 C6 | Approved open foundation weights, real admitted training, durable reload and canonical service independently produce useful grounded text/file/media outcomes; held-out semantic quality and runtime performance are measured. Codex Cloud development and offline loader registration are not deployed inference. |
| U19 | Agent, Skills lifecycle, tool discovery and Memory | C2 / C6 | Real goal/tool work runs through the existing chain with origin/version-bound capability formation, progressive retrieval, context/memory/checkpoint continuity, interruption/resume/cancel and uncertain-effect reconciliation; discovery/skills gain no independent authority. |
| U20 | Evaluation, feedback and controlled learning | C2 / C3 C4 C5 | Actual outcomes, corrections and negatives produce derivative versioned learning assets, shadow/held-out comparison, approved promotion and rollback; preserve source truth and distinguish effect fidelity from simulated/user/environment shortcuts. |
| U21 | Product browser and acquisition continuity | C1 / C6 F | Approved product browser/profile context supports real permitted navigation/acquisition and source return with honest login/challenge/offline/recovery states; protect personal workstation accounts and preserve official interfaces. |
| U22 | Open product entry, scope, Permission and effect control | C6 / C1 C2 C5 F | Existing product work remains accessible without a new account/password wall; server actor/scope/effects remain enforced. Focus/Clear preserves stored task scopes and original-source rights; final PO account redesign remains explicitly deferred. |
| U23 | Four-surface Experience and work continuity | C6 F / all owning deliveries | Approved Website/Web/Desktop/Mobile roles execute their actual tasks with task-specific layouts, Chinese/English/Korean localization, accessibility, saved context/result continuity and recovery; approved mobile role is not a duplicate desktop. |
| U24 | Settings, shared preferences and notifications | C5 C6 F / relevant source owners | Real preferences/settings persist and affect their intended behavior, status/notifications open the correct scoped task/result, and denial/offline/retry remain accurate without a second settings or event truth. |
| U25 | Runtime, security, packaging, release and operation | C6 / all owning deliveries M PO | Core8201, FFmpeg/ffprobe, supervisor/owned-child cleanup, queue/restart/recovery, protected DB/backup/rollback, required builds and same-SHA real Gate pass; separate engineering, PO repeat, RELEASED, scheduled OPERATING and future commercial/market evidence. |

## 覆盖限制与保护

基线 a6844a98032ed1ffa0be8f99c40f7b99ba14d453；跟踪文件 2918；非忽略未跟踪路径 35090，其中大量 work 冻结源码/材料副本。未跟踪数不等于待开发功能数。
本轮未全量读取全部材料正文、未执行全库回归/每屏 E2E、未读取秘密、未启动采集/模型/渲染。对实际未执行的能力保留 NOT_VERIFIED。全仓路径归属覆盖与具体业务完成度分别报告。
