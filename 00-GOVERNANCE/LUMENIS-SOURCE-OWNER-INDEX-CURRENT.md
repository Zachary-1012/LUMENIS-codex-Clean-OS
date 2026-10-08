# LUMENIS Source Owner Index — CURRENT

> 2026-10-09 最新直接 PO：C1 暂停，F/C2-C6 保持暂停；M 仅继续已授权工具/Browser/AgentZero收尾、CURRENT收敛及A0/B0/C0准入准备。基础业务无AI独立运行是全产品要求，AI增强单独验收。下文旧C1恢复/连续执行表述保留其职责，实际执行须等待PO恢复；模型/effort/tier不变。来源：现有AI-OPTIONAL-PREPARATION-C1-PAUSE审批回执。

> 2026-10-08 PO 正式验收策略变更：单元/集成及换名模块自动测试不再是开发、合并、验收或发布条件，Codex 不新建、不执行这些套件；保留历史测试和 FAILED 证据。当前执行真实任务→既有源码→构建运行→实际用户操作→真实结果→保存/修订/重开→恢复→验收→正式集成。适用编译、静态质量、安全/权限、数据一致性及真实产品 E2E 保留；历史材料中的测试命令不构成当前执行义务，真实缺陷仍必须修复。R01–R15/J1–J8/U01–U25 与 Owner/权益/生产数据边界不变；机器合同 v1.2.0 的 verification_policy 记录现行语义。历史同轮恢复/Astra指定已被2026-10-09直接PO暂停及其此前手选GPT-6.1 Sol/ultra取代；M仅继续当前已授权工作，C1/F/C2-C6保持暂停，不改变任何窗口的手选模型、effort或速度。

> Status: **CURRENT EXECUTION INDEX / SIX-ROUND DELIVERY / COMPLETE LEGACY COVERAGE**

> 保留的 C1 完整执行职责（当前暂停，须等待直接PO恢复）：恢复后由C1自行完成真实采集闭环及其必需的既有 Core/Runtime、Scheduler、现有授权服务端绑定修复和受控运行操作，不转交C6。旧“不暂停C1”调度已被2026-10-09暂停回执取代，不是当前执行命令。源码的架构 Owner 不变；本次必要调用链的实际执行者为 C1，沿已有 W6 Shared Reservations 记录有界交接并保护原冻结成果和无关工作。进程归属、在途任务、备份恢复、Permission、账号与零新增费用边界不变。M 负责边界同步、成果审核和正式集成，不代做 C1 普通修复。其余窗口继续暂停；不据此声称任何能力已验收。
>
> 本次 PO 另行指定 M 收敛非 C1 的既有本地候选与未集成源码；沿本索引原 Owner 认领逐项发布，不恢复暂停窗口、不代做 C1。C1 已冻结 F-08/F-09 数据合同作为业务依赖按原哈希吸收，其活动采集源码继续独立保护。源码集成、真实运行和完整用户验收分别记录；入口为既有 Round 15 CURRENT-STATE-REPAIR-20261007.md。
> 最新 PO 增补要求 M 用研究子智能体完整追回并实际研究未完成的本地/线上原始材料、DeepSeek祖先分析和升级规划，按现有 Owner/源码落实能力；材料索引、摘要、蒸馏包与真实产品采用分别核实，未读/未取得不得结项，训练另行准入。
>
> Updated: 2026-10-07; earlier baseline tables remain dated provenance
> Approved ROUND 01 source-audit baseline: `df15a99de6f5ffc3eb85e2c9924afb59c1c3c781` (provenance only; resolve the live `origin/main` before every change)

This file is the fixed repository navigation and delivery index for 序境 / LUMENIS. It classifies current source by owner and tells Codex where to look after the one-time source audit. It is not a second product architecture, Experience authority, progress ledger, or proof that a runtime capability works.

When this index conflicts with current executable source or runtime evidence, current source/runtime wins and this index must be repaired in the same coherent change.

### 最新 PO 当前成果优先级 — 官网 / Web，2026-10-08

后续直接修正：F直接构建真实前端，不先制作独立设计稿，不等待Figma或M逐屏DESIGN_READY；复用既有44屏和视觉规范并随代码更新。后续原生客户端仅Windows/macOS和iOS，Android/Linux原生客户端要求已被PO替换，不留为待交付；历史资料/源码仍保护。Linux服务端/CI和浏览器跨OS运行不受此限制。

沿现有 Owner/源码表先完成 Public Website 与 Web Workspace；Desktop App/Mobile Companion 专项实现、打包和实机验收后置至前两端闭环，保留全部需求/Goal/设计/源码与未完成记录。F 负责当前两端的完整适用屏幕与官网家族；M 按依赖选择唯一 C 窗口，C6 共享集成占用该席位。业务、研究、数据、媒体与 AI 的当前 Web 必需合同及 Core/SYSTEM 继续完整推进，不把桌面客户端后置解释成停后端或改用模拟结果。Shared Flutter 修改保留兼容，不新增无关 native 工作。既有三层 Gate 按表面验收，完整四端 Release 不因本轮验收自动成立。具体顺序归 AGENTS/Multi-Surface Decision，真实验收归 Overlay；无新增 Owner/队列。

## 1. Retained R01–R15 acceptance coverage and historical audit groups

### 2026-10-08 Intelligent UI research adoption routing

The existing Experience Constitution §38 owns this approved later-execution
requirement. Read its exact C1-C6/F table with the existing screen specification
and caller; do not create another Task Card, generic renderer or capability owner.
Status is `RESEARCH_ADOPTED`; mapped implementation is included in the current
F/C1-C6 dispatch and proceeds after fresh owner admission. It is not thereby
IMPLEMENTED.

| Owner | Current source entry | Required relationship |
|---|---|---|
| C1 | `lumenis/system/collector/`; `collector_status_api.py`; existing SourceTarget contract | Native source, time, scope, coverage and honest state for interactive exploration. |
| C2 | `lumenis/system/ai_gateway/`; `agent_runtime/`; `agent_capability/` | Grounded typed presentation/action proposals through current Gateway and authorization. |
| C3 | `cth_cases.py`; `lumenis/bmp/`; existing business workflow locator | Same business task/constraints/Evidence across comparison, scenario and decision. |
| C4 | `lumenis/shared/content_creation/`; `podcast/`; existing Timeline/Artifact owners; `app/lib/features/shared/sh01/` | Editable pitch/video/podcast and stable selected scene/segment/version state. |
| C5 | `lumenis/shared/reporting/`; `lumenis/importer/`; `shared_artifacts.py`; existing Research/SavedWork owner | Source navigation, conflict/revision comparison, save/reopen and correction impact. |
| C6 | `experience_runtime.py`; `lumenis_app_api.py`; current SYSTEM runtime | Version-bound actions, streaming/cancellation/recovery and exact integrated contract. |
| F | `app/lib/`; `website/`; `contracts/experience/screen-specifications/` | Reviewed screen-specific four-surface presentation; read contracts above before implementation. |

The 2026-10-08 clarification covers all 44 existing screens and all four surfaces, including settings, notifications and recovery. The per-screen execution/adoption index is `contracts/experience/screen-specifications/README.md`; each row uses its original spec and the dated amendment in the existing 44-screen text wireframes. No additional task queue or UI implementation state is implied.

Directory navigation is not proof of implementation; resolve exact current
paths through the capability locator before changing source. Research source,
limits and decisions are in
`evidence/round-15/INTELLIGENT-UI-ADOPTION-20261008.md`.

Live dispatch follows the current instruction at the top of AGENTS.md; eligibility/ownership in this index does not assert that a local window is currently running. C1–C6 are the six complete delivery responsibilities; R01–R15 are retained acceptance/dependency requirements mapped into those outcomes. The numbered table below is historical coverage context, not a second execution schedule and not the R01–R15 identifier list. D01–D49 are audit dispositions; their original audit labels are not product requirements. This index does not activate paused windows or create sequential dispatch. Valid evidence may cover multiple IDs. No mapping turns a missing gate into PASS. M accepts complete outcomes; W6 integrates when authorized.

| Historical coverage group | Delivery | Scope | Exit gate |
| --- | --- | --- | --- |
| Legacy group 01 | **Current truth and PDF coverage** | Remote/local/PDF audit, owner map, protection items and the historical 15-group coverage map; read-only. | Three-source comparison and every PDF page/task are accounted for; no source mutation. |
| Legacy group 02 | **Authority, Only-One and multi-surface decision** | Preserve sole authorities, naming, compatibility classification, the approved Public Website/Web Workspace/Desktop/Mobile route and retired-provider placement. | The approved four-surface route stays consistent across current authorities; historical APP ONLY wording cannot suppress it or reopen a resolved decision. |
| Legacy group 03 | **Database and Canonical Truth** | Database paths, migrations, repository, root callers, direct SQLite and isolated test protection. | One canonical business schema/path and protected migration/rollback evidence. |
| Legacy group 04 | **Identity, context, Permission and Evidence** | Actor identity, Subject/BrandFocus, access timing, read/write/approval/effect fences and lineage. | Context cannot grant authorization; decisions/actions trace to Evidence and Return. |
| Legacy group 05 | **Runtime, health and recovery** | Startup, supervisor, honest health, queue/worker/DLQ, logging, recovery and operations stores. | Health represents real dependencies; failure/recovery paths are tested. |
| Legacy group 06 | **Collector, browser and acquisition** | One collector/browser, scheduler/adapters, Cookie/session/CDP, rate limits, provenance and ingestion. | Authorized source → collection → Evidence closes without duplicate runtime or unsafe browser behavior. |
| Legacy group 07 | **AI, Agent and Shared engines** | One AI Gateway, owned weights/training/inference, Agent/skills, reporting, evaluation and learning; retired providers remain inert. | Useful owned inference, tools, recovery and promotion are proven; retired providers stay inactive; AI never owns truth/effects. |
| Legacy group 08 | **Cross-Surface Experience Foundation** | Public Website foundation, Flutter Web Workspace/Desktop/Mobile shells, shared contract/state/accessibility/localization and capability boundary. | Four surfaces have distinct roles over one Product Core; no generic screen template or second truth. |
| Legacy group 09 | **Golden Pages and CTH-02** | AI-01, CTH-01/02, BMP-01, SH-01 and SYS-01 with surface matrix and live binding. | Applicable Web/Desktop/Mobile paths complete real tasks with Permission/Evidence and truthful states. |
| Legacy group 10 | **CTH monitoring and analysis** | CTH-03..07 source-backed monitoring, events, calendar, sentiment, trend and trace. | Real Subject-scoped monitoring/analysis closes with source lineage. |
| Legacy group 11 | **CTH case, risk and decision** | CTH-08..10 Case → Insight → Decision → Action → Outcome plus report/export. | Authorized CTH response loop and Evidence lineage are verifiable. |
| Legacy group 12 | **BMP portfolio, market and propagation** | BMP-02..05 BrandFocus, competitor, market intelligence, propagation and creators. | Brand-first workflows preserve source/evidence and scope semantics. |
| Legacy group 13 | **BMP content, campaign and evaluation** | BMP-06..11 content lifecycle, campaign, podcast, evaluation, risk and benchmark. | Approved action/result/evaluation loop is real and traceable. |
| Legacy group 14 | **Remaining ACC, AI, Shared and SYSTEM Experience** | ACC-01..04, AI-02..05, SH-02..06 and SYS-02..08, respecting pre-beta account timing. | Each applicable surface role is explicit; deferred identity capability is honestly blocked/deferred, not simulated. |
| Legacy group 15 | **Closed-loop internal beta and release** | Cross-surface real-data E2E, PC/mobile, security, accessibility, performance, packaging, clean clone, recovery/rollback and release evidence. | Public → Web → real context/workflow/Evidence → Desktop advanced execution if applicable → Web result → Mobile approval/notification if applicable → Report/Evaluation/Learning passes; unresolved items remain explicit. |

### Historical responsibility coverage map — 2026-10-02

The rows below preserve the approved requirement/role mapping; AGENTS.md owns current activation and environment choice. The former C3/C5 shared continuation relationship and former Cloud handoff are historical provenance only. Under the current AGENTS route, M is the root controller/integrator, while F and C1-C6 are eligible delivery roles. This map assigns ownership and admissible scope; it is not a live scheduler. A role becomes DISPATCHED/RUNNING only under the newest explicit Product Owner instruction for that current/local window and after fresh admission. A Product Owner instruction to wait keeps that role WAITING_DEPENDENCY even though the role remains eligible in this index. Once actually dispatched, no owner waits for unrelated material directories, and dispatch never bypasses real dependencies or shared-writer coordination.

| Existing ID | Responsible delivery / support |
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

The original six urgent exits remain: XHS exact scope/unassigned → C1;
Core8201/FFmpeg/ffprobe/crash recovery → C6+C4; Source Brief/multimodal in real
CTH/BMP → C2/C3/C5/C6; useful Outcome/Evaluation → C2/C3/C4; same-SHA Product/App
hosted → C6; final Product Owner repeated jobs after engineering ready → C6/M/PO.
Counts do not substitute for useful outcomes.

U01–U25 and original 34-section/44-screen coverage remain:
U01–U05 Global/identity/markets/native fields/freshness/tenants → C1;
U06–U12 monitoring/consumer/risk/operations/brand/competitors/creators/campaign → C3;
U13–U15 original pitches, video and podcast (three separate deliverables) → C4;
U16–U17 library/import/citation/report/export → C5 with C2 understanding;
U18–U20 AI, Agent/Skill Store and Evaluation/Learning → C2;
U21–U25 browser, open entry/effects, surfaces, settings/notifications,
runtime/security/release → C1/C5/C6 plus F. No capability is removed by remapping.

### Current J/U job assertions — M clarification, 2026-10-02

This table completes the previously grouped J/U mapping in this same Source Owner
Index. These are current explicit labels/assertions, not purported recovered
historical individual titles. The original R rows, J/C allocations, U groups,
six urgent exits, 34-section/44-screen obligations and approved detailed contracts
remain cumulative. A grouped function appearing in more than one row is not
deleted or duplicated into another owner; the same valid evidence may cover it.
This clarification adds no feature, window, runtime or acceptance authority.

Each row needs an actual normal task: permitted real input -> correct scope and
Evidence -> useful user-visible result -> applicable persistence/version/reopen/
revision/export -> honest failure and bounded recovery -> return. Apply only the
operations promised by that capability; a read-only fact lookup need not invent
an external action. Record exact source/runtime/model/build versions and limits.
Tests, a denial, an empty/unavailable response, a mock, a file, or a model answer
alone cannot complete a promised normal capability. An unavailable dependency
blocks that path without erasing the row or stopping unrelated work.

#### J1-J8 complete user-work packages

| ID | Current explicit user job | Retained deliveries | Required outcome |
|---|---|---|---|
| J1 | Establish, select and continuously maintain the real data universe | C1 C6 | Real Add Subject/BrandFocus, country/market and venue/tenant identities, approved platform-native acquisition and time series, signed Source/Evidence/Canonical, GLOBAL/Focus/Clear, due-only refresh, idempotence and actual scheduled recovery without a Codex/CUA/developer trigger; representative samples do not imply coverage. |
| J2 | Complete a commercial Subject operating decision | C3 C1 C2 C5 | Exact venue/tenant and time scope; monitoring/events, consumer/market/risk analysis, Case -> supported insight -> internal decision -> authorized action where promised -> actual outcome/evaluation and saved result; useful owned analysis, task budget/resource feasibility where costs apply, recovery and return. |
| J3 | Complete a BrandFocus market/content/campaign decision | C3 C1 C2 C5 | Brand/market/competitor/creator/propagation inputs with comparable metrics, grounded analysis, editable Brief and content/campaign lifecycle through creation owners, actual result/evaluation, task budget/resource feasibility where costs apply, saved/reopened output and recovery. |
| J4 | Produce and revise an original professional pitch | C4 C2 C5 F | Real Brief and materials -> original reasoned concept/strategy and budget/resource-feasible alternatives -> editable customer-ready proposal -> review/revision/export/reopen and evaluation; manual and owned-AI paths both work where approved. |
| J5 | Produce and revise an editable video | C4 C2 C5 F | Real permitted media and actual budget/resource constraints -> editable Timeline -> preview/edit/render -> verified playable result and editable project -> review/revision/export/reopen/cancel/recovery; retain approved audio, subtitle, transition and quality requirements. |
| J6 | Produce and revise a usable podcast | C4 C2 C5 F | Research/script/interview-or-story intent with actual budget/resource constraints -> actual audio and complete editable episode -> edit/mix/transcript/chapter/derivative work -> review/export/reopen/evaluation, with script changes distinguished from actual recorded/generated sound. |
| J7 | Turn real materials and goals into reusable knowledge and useful owned-AI work | C2 C5 | Supported file/media intake and precise citations -> actual understanding/research/analysis, extensible case/method combination and task-relevant Discover recommendations -> saved searchable versioned result; actual owned Gateway/Agent/Skills/Memory work and Outcome -> Evaluation -> reviewed Learning -> held-out promotion/rollback. Public discovery and saved examples alone are not training; case mechanisms remain extensible, not a fixed creative template. |
| J8 | Continue and recover the work across approved surfaces and release it | C6 F | Website/Web/Desktop/Mobile roles operate over one Core and saved context/task/result, with required packaging/security/accessibility/performance, same-SHA hosted Product/App, restart/rollback and engineering-ready bundle. PO repeats only when engineering ready; RELEASED and OPERATING need their own evidence. |

#### U01-U25 retained capability assertions

| ID | Current explicit capability | Existing responsible delivery / support | Required normal result and distinguishing constraint |
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
| U21 | Product browser and acquisition continuity | C1 / C6 F | Approved product browser/profile context supports real permitted navigation/acquisition and source return with honest login/challenge/offline/recovery states. SYS-06's current bounded reader uses the existing SYSTEM Browser owner, a server-issued local-workspace principal and target/revision-bound read-only frames; it never opens a personal browser or exposes a profile/session. Protect the workstation Mainland personal account and preserve official interfaces. Runtime source reading, acquisition and return acceptance remain separate. |
| U22 | Open product entry, scope, Permission and effect control | C6 / C1 C2 C5 F | Existing product work remains accessible without a new account/password wall; server actor/scope/effects remain enforced. Focus/Clear preserves stored task scopes and original-source rights; final PO account redesign remains explicitly deferred. |
| U23 | Four-surface Experience and work continuity | C6 F / all owning deliveries | Approved Website/Web/Desktop/Mobile roles execute their actual tasks with task-specific layouts, Chinese/English/Korean localization, accessibility, saved context/result continuity and recovery; approved mobile role is not a duplicate desktop. |
| U24 | Settings, shared preferences and notifications | C5 C6 F / relevant source owners | Real preferences/settings persist and affect their intended behavior, status/notifications open the correct scoped task/result, and denial/offline/retry remain accurate without a second settings or event truth. |
| U25 | Runtime, security, packaging, release and operation | C6 / all owning deliveries M PO | Core8201, FFmpeg/ffprobe, supervisor/owned-child cleanup, queue/restart/recovery, protected DB/backup/rollback, required builds and same-SHA real Gate pass; separate engineering, PO repeat, RELEASED, scheduled OPERATING and future commercial/market evidence. |

The U assertions are a minimum traceability layer for the original groups, not a
replacement for their deeper source/Screen/Experience/business contracts. Attach
additional retained sub-capabilities to these same rows without silently narrowing
them. Maintain every unresolved detailed obligation in its current delivery card.
Approval of this mapping does not mark any capability TESTED, VERIFIED or accepted.

W6 uniquely writes app.py, lumenis_app_api.py, experience_runtime.py and
experience_screens.py composition and executes formal DB changes. W2 owns
ai_task_engine.py and Agent execution. W1 serializes actual Collector writes;
other windows use explicit disposable DBs. F exclusively changes app/ and
website/ interface code. These writer assignments do not create new owners.

## 2. Product preservation contract

These are blocking requirements for C1–C6 and mapped checkpoints:

1. Inspect the current owner, callers, contract, tests and runtime path before changing code. `UNKNOWN` and `BACKEND_GAP` are investigation states, not instructions to create an API.
2. Preserve existing product position, functions, business rules, data sources, object meanings and workflow outcomes. Work may strengthen or adapt an approved capability; it may not invent, expand or replace product scope.
3. Media platforms continue through the existing SYSTEM Cookie/session/browser collection chain. Do not add a platform-login step, a second collector or a new account model.
4. Product account and password design remains deferred until product closure reaches 100%, followed by Product Owner redesign. Browsing and existing product use before that decision must not be blocked by a LUMENIS account wall. Public Website trial/contact and workspace entry do not authorize a second identity store. This decision does not remove server-side Permission, effect fences or platform-session safety.
5. Platform Cookie/session authorization and a future LUMENIS product account are separate identities. Never migrate, display, log or commit platform credentials as product-account data.
6. Apple contributes restraint, content priority and clear primary actions. ChatGPT contributes a single intent entry and progressive complexity. TRAE contributes the visible rhythm “task → execution → result”. These are Experience principles only; they do not authorize new search, chat, project, task or account features.
7. The frontend presents business intent, state, progress, result and recovery. Collection, routing, tool execution, model selection, Evidence creation and other processing remain in their current backend/runtime owners.
8. Each of the 44 screen blueprints keeps its own task, information hierarchy, composition and interaction path. PC and mobile share business truth but use purpose-built semantic recomposition; neither is a scaled copy of the other.
9. A local problem may change only its bounded owner/callers. It may not trigger a global auth, database, naming, architecture or design-system rewrite. Remove a path only after its unique behavior is preserved and accepted in the current owner.
10. Every change proves the requested improvement and preservation of affected behavior with applicable build/static/security/data checks and, for user-visible workflows, real runtime/E2E evidence; unit/integration suites remain prohibited. A build, fixture, HTTP 200, screenshot or document alone is insufficient.
11. The approved ROUND 01 PDF/report/register are evidence and coverage indexes only. Their sketches remain `DESIGN_EXPLORATION`; implementation proceeds directly from current Experience and actual screen contracts, with records updated alongside code; separate design drafts/M DESIGN_READY are not prerequisites. Direct PDF/sketch implementation is `REWORK` when it merely copies an artifact into generic or unbound behavior; direct construction under current contracts remains authorized without a separate design phase.
12. Product Skill Store is a named P0 capability under Shared Agent Skills and AI-04. Preserve discovery, trust/license, input/output, Permission, enablement, verified run, history, update, disable and uninstall semantics; do not reduce it to the historical `FUNCTION_MAP`.
13. ROUND 02–15 cannot close on source, tests or governance evidence alone. Route each dispatched Owner Task Card and M acceptance decision through `LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md`, including its real-user E2E, `REAL DELIVERY CARD` and Section 23 `COMMERCIAL OVERLAY IMPACT`; a commercial gap sets `COMMERCIAL_READY=NO` without falsely failing unrelated engineering work.
14. Route every context/data-related round through `LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md`. The product default is `GLOBAL / ALL`; Subject/BrandFocus selection changes focus only and never grants Permission or controls background execution. Report `Global Commercial Coverage`, `Global Brand Coverage` and `Guangzhou Taikoo Hui Reference Coverage` as three acceptance dimensions of the same internal full-universe edition. They must not create separate products, releases or truth stacks. All three `YES` is required for `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=YES`.
15. Every related round runs the contract's `RANDOM ENTITY DATA ACCEPTANCE` with rotating stratified non-fixture samples and preserves seed/list/version/request/surface/Evidence/result evidence. A covered/mature blank or fabricated sample forces `REWORK`/`BLOCKED`; an unavailable registry is reported as sample count zero and assigned to its owning round, never postponed silently to ROUND 15.
16. An accepted Batch is not an online delivery until its reviewed source, Round evidence and CURRENT status are coherently committed, pushed and verified against live `origin/main` in the same delivery cycle under `AGENTS.md` §2. Preserve unaccepted work as `LOCAL_ONLY`; a documentation-only push does not make its source visible to GitHub readers.
17. Six complete C1-C6 delivery responsibilities use six separate local Codex delivery windows. Independent frontend F owns Experience across all six deliveries and executes only when dispatched; controller M retains review/integration/acceptance; W6 retains shared integration/runtime/release ownership. C2 alone owns product GPU training. Historical combined C3/C5 and Cloud W3/W5 handoffs remain provenance only and do not create a second queue. No ten-worker target. Report actual capacity/activity, preserve explicit pauses and genuine dependencies.
18. Chinese, English and Korean are product-surface commitments, not merely Public Website copy. Apply the sole Experience Constitution's per-screen three-language and responsive/accessibility gate to every promised operational surface; unverified Korean UI is an explicit gap, never a silently dropped requirement.

### Product Owner requirement routing check

This table routes the Product Owner's durable requirements into existing sole
authorities. It is a completeness index, **not** another architecture, design
system, product scope, source-status claim or release approval. At each Round
Charter and final release review, mark every applicable row covered by current
source and evidence or assign its unresolved gap to the owning Round; a document
mention alone cannot be marked implemented.

| Requirement family | Sole content owner / execution gate |
| --- | --- |
| One product, CTH/BMP/Shared/SYSTEM jobs, preserved legacy capability and no duplicate truths | Product Architecture and Product Positioning; `AGENTS.md` §§4–6; exact caller row below |
| Current remote/local truth, protected work, PDF page/task coverage and historical audit-group provenance | `AGENTS.md` §§1–3; this index §§1 and 11; approved ROUND 01 evidence. R01–R15 are retained acceptance/dependency requirements mapped into C1–C6, not another schedule. |
| Current manual account/model/effort/speed selection, controller M, no automatic window/model dispatch | `AGENTS.md` current execution instruction; active Task Card and Product Owner's current selection |
| Accepted source + retained guards/real E2E + Round evidence + CURRENT online status + verified push | `AGENTS.md` §2 online-publication gate; current Round evidence and CURRENT takeover |
| Business end-state, industry logic, real job and deliverable outcome before adding a feature | Product Positioning; `AGENTS.md` §3 business-work selection; Real Delivery Overlay |
| Public Website versus Web Workspace, Desktop advanced capabilities and Mobile Companion | approved Multi-Surface Decision; Product Architecture; Experience Constitution |
| Business-job frontend reconstruction; historical 44-screen capability inventory is not a fixed page count; PC/mobile behavior, accessibility and `DESIGN_READY` | sole Experience Constitution including 2026-09-24 Product Owner direction; detailed `contracts/experience/screen-specifications/` |
| Chinese, English and Korean on every promised user-visible surface | sole Experience Constitution §22 and executable localization thresholds; active screen/round evidence |
| `GLOBAL / ALL`, focus-only Subject/BrandFocus, internal full-universe data and honest permission-limited commercial views | sole Global Universe Context/Data Maturity contract; Shared DB/Evidence and SYSTEM Permission owners |
| Global commercial, global brand and Guangzhou Taikoo Hui maturity plus rotating non-reference entity tests | sole Global Universe Context/Data Maturity contract; relevant Round `REAL DELIVERY CARD` |
| Collector/Browser/authorized sessions, public sources and approved HK/international XHS development identities | SYSTEM Collector/Browser owners; `AGENTS.md` §§8–10; Real Delivery Overlay ROUND 06 |
| One AI Gateway and owned inference/training | C2, Product Architecture, SYSTEM AI owner and R07 gates; stopped interfaces retained inert |
| Product Skill Store discovery, trust/license, guarded run, history, update/disable/uninstall | Shared Agent Skills owner; this index §2 item 12; Real Delivery Overlay ROUND 07 and AI-04 |
| Creation, reporting, evaluation, learning and per-round frontier research/controlled capability upgrades | Product Architecture chain; `AGENTS.md` §§3–4; Real Delivery Overlay research and workflow gates |
| Real permitted user E2E, operable page, Evidence Trace/Return and honest failure/recovery every related Round | sole Real Delivery Overlay; Experience Constitution; current Round Charter |
| Data/source legality, secrets, version compatibility, backup/restore/deletion, tenant lifecycle and commercial operations | Real Delivery Overlay §23; `COMMERCIAL_READY=NO` until its six gates pass |
| Windows/macOS/iOS native targets after Website/Web closure, clean clone, cross-surface return, rollback, internal beta and release | this index ROUND 15; Real Delivery Overlay release matrix; platform-specific runtime evidence |
| Codex role defaults: M/F Astra ultra; C1–C6 Sol 6.1 ultra; task Subagent Luna max; Product Owner manual window/spawn selection overrides defaults; M idle waits | Current AGENTS + `.codex/model-routing.toml`; historical workstation/model routing is superseded |

### 2026-10-09 data-to-business upgrade: existing owners, one C1 executor

Global §10 holds the complete direct PO requirement and source/function targets;
this mapping is navigation, not a second architecture or new window dispatch.

| Actual responsibility | Existing owner / callers and bounded execution |
|---|---|
| Authorized acquisition and raw retention | SYSTEM Collector/Browser: acquisition_plan, secondary_collection and current platform adapters; C1 preserves legal observations even before business relevance/entity confirmation. |
| Source validity and immutable reopening | Existing Shared/Source intake and importer/documents reader; C1's exact pending-observation reader region is handed off in original W6 reservations, preserving formal Source validation and UNASSIGNED/PENDING state. |
| Access/use/derived-write authorization | SYSTEM Permission, real actor/maintenance plan and current source-use owners; import, analysis, commercial use and model learning remain separate grants. |
| Identity candidates versus confirmed facts | Existing Registry/Canonical and CTH/BMP scope/relationship owners; pending raw records stay locatable without false subject/venue/brand binding or another store. |
| Business analysis and user result | Existing CTH/BMP, Shared Research/SourceBrief/Reporting/SavedWork/Evaluation, SH-01 Discover and actual Web callers; no final business rule moves into Collector/UI/Controller. |

C1 executes the existing full data-to-result task; M reserves only genuinely affected
cross-owner regions and integrates frozen accepted source. Other paused roles do
not resume. M retains its original non-C1 candidate/material convergence. Scope,
source version/use, native time, state and error semantics pass through actual
interfaces; no parent DATA_IMPORT receipt or name hit substitutes for later use.
Only changed Web consumers are repaired; original 44-screen scope remains intact.
Source/runtime/DB/user acceptance remain separate from this published routing.

## 3. Fixed source lookup map

After bootstrap, locate work here. Root-level compatibility callers remain classified as callers until their behavior is safely absorbed; their location does not make them a second owner.

| Concern | Canonical authority or owner | Current callers/contracts/tests to inspect |
| --- | --- | --- |
| Agent execution | `AGENTS.md`; `00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md`; this index | `scripts/audit_tools/verify_codex_takeover_governance.py`; `.github/workflows/platform-verify.yml` |
| Product/domain architecture | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`; `00-GOVERNANCE/PRODUCT-POSITIONING-CURRENT.md` | Exact CTH/BMP caller and contract for the active slice; do not infer ownership from a filename |
| Experience authority | `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md` | `contracts/experience/README.md`; `contracts/experience/screen-specifications/<SCREEN-ID>.md`; direct construction follows current screen contracts; update specifications with code; no separate draft/M DESIGN_READY prerequisite; Experience validators |
| Multi-surface decision | `00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md` under the sole Product Architecture and Experience Constitution | Surface capability matrix, deployment boundary and blocking validators; never treat the decision as implementation evidence |
| Public Website | `website/` presentation/acquisition root; trilingual foundation committed at `77648c3b`, commercial destinations still unconfigured | Product copy, demo/case truth, trial/contact/help and workspace entry only; no business workflow/data/Permission/Evidence owner |
| Flutter operational surfaces | `app/lib/product/`, `app/lib/shell/`, `app/lib/features/` | Flutter Web Workspace, Desktop and Mobile targets; `app/lib/core/`; matching `app/test/`; `app/README.md` |
| Screen truth binding | `contracts/experience/lumenis_app_binding_registry.json`; `contracts/experience/screens/<SCREEN-ID>/` | `actions/`, `permissions/`, `evidence/`, `states/`, `viewmodels/`; current API owner and tests |
| Product Core composition/API | `app.py`; `lumenis_app_api.py`; current registered routes | `experience_runtime.py`; `experience_screens.py`; exact route/service/repository tests |
| CTH/BMP business callers | Current root/domain modules such as `subject_context.py`, `subject_registry.py`, `api_dual_domain.py`, `cth_cases.py`, campaign/brand/event/case/risk modules | Trace each caller to its actual data, Permission, Evidence and test owner before moving or renaming it |
| Function/Metric and time-series consumers | Existing canonical Function/Metric definitions in `canonical_metrics.py`, CTH/BMP domain metric owners, and Shared Database observation persistence | `trend_api.py` is a compatibility Product Core/API caller; W6 composes routes, W3 retains domain meaning and W1 supplies native observations. Legacy Subject word filters and absent-day zero filling require scope/coverage repair before Discover reuse; no new trend owner or second metric truth. |
| Shared Evidence | `lumenis/shared/evidence/` | Evidence APIs, migrations, lineage and affected domain tests |
| Shared Database | `lumenis/shared/database/` | `data/monitor.db` contract, migrations and isolated persistence tests |
| Schema/migrations | Shared Database migration owner; existing `migrations/`/Alembic paths | Schema callers, rollback/compatibility and isolated migration tests; never mutate the protected runtime DB merely to classify a file |
| Shared Content & Creation | Existing Shared Capability in `lumenis/shared/content_creation/`, with Product Core and Artifact/Reporting/Evaluation bindings | `content_generation.py` and `podcast/`; legacy proposal callers `scripts/pitch_parser.py`, `scripts/pitch_export.py`, `scripts/campaign_plan.py`, `scripts/perspective_adapter.py` require validation before reuse; the current Content & Creation learning-source contract; video, podcast and pitch research as historical input only; matching API, Permission, Evidence, media, artifact, user-review and return-path tests. Video, podcast and general content creation remain distinct workflows that reuse Shared capability. |
| Shared Evaluation/Learning/Reporting | `lumenis/shared/evaluation/`; `lumenis/shared/learning/`; `lumenis/shared/reporting/`; existing C5 `lumenis/importer/` intake | Current root callers and domain regression tests; `agent_memory/base.py` remains a compatibility interface used by `lumenis/shared/learning/memory.py`; Shared Learning retains memory capability authority and Shared Database retains persistence authority |
| Shared skills/agent execution | `lumenis/shared/agents/skills/` | `account/api.py`; `agent_runtime/`; `agent_capability/`; `agent_smart_tool/`; `ai_api.py`; `ai_task_engine.py`; `agent_memory/working.py` remains a compatibility working-memory execution caller |
| SYSTEM Permission/effects | `lumenis/system/security/` | Active API/action callers; permission, denial, approval and effect-fence tests |
| SYSTEM AI runtime | lumenis/system/ai_gateway/ | C2 owns inference/training; `app.py` translation, `local_ai_client.py`, `ai_api.py`, `ai_task_engine.py`, `lumenis/ai_hub/service.py`, `content_generation.py`, the C5 `lumenis/importer/analyzer.py`, C4/C5 `lumenis/shared/reporting/media_brief.py`, and `browser_surface.py` are callers of the single Gateway boundary. The public legacy `core.vision_chat` interface fails closed with `provider_disabled`; user-facing `/api/translate`, `/api/ai/chat`, `/api/ai/test`, `/api/ai/analyze-v570`, `/api/ark/*`, mounted AI Hub chat/module-analysis routes, and the core legacy connection/sentiment/summary/keyword wrappers use the owned Gateway and do not turn unavailable output into success. TaskEngine calls `run_owned_analysis` and fails AI-dependent jobs rather than marking them succeeded without a model result. Status/capability responses report the owned runtime without local-provider discovery or implicit retired-provider fallback. The v4 importer exposes unavailable analysis and table-only `NOT_RUN` without fabricated labels. Report-media and Browser Hybrid Vision use the owned multimodal entry and honestly stay unavailable until a vision executor is service-bound; historical local-provider Evidence is read-only compatibility. `lumenis/importer/service.py` now delegates v4 whole-source confirmation to the Shared Document Import owner with exact actor/scope, declared rights, source hash and replay receipt; it no longer writes notes directly. The old v4 importer has no in-repo UI caller, so packaged UI-to-import operation remains open. The existing owned-training path retains an exact-approval remote source-pin preflight that starts no worker/model/GPU; actual training, checkpoint, inference and promotion gates remain separate. At pinned main `560c4f3f`, production source has no external caller of `owned_inference.load_owned_inference`, `load_owned_production_runtime` or `owned_speech.transcribe_audio`: their historical candidate source is preserved, while actual serving and Media task binding remain OPEN. This source observation does not authorize training, a runtime load, or a paused C2/C4 window to resume. |
| SYSTEM collection | `lumenis/system/collector/` and `lumenis/system/browser/runtime/` | Canonical adapters/guard/runtime/Scheduler/Evidence tests. Compatibility call paths that require consolidation are `app.py` → `lumenis/blueprint.py` `/v4/adapters/collect` → `lumenis/adapters/collector_service.py` / `persist.py`, and `/api/experience/cth/platform-collection/search` → `secondary_collection.py`. They are callers, not separate owners; preserve unique task/polling/risk/platform behavior while converging on one collector/task/status/write contract. |
| SYSTEM browser/session | `lumenis/system/browser/runtime/` | `xhs_cookie_bridge.py`; `xhs_p0_orchestrator.py`; `xhs_cdp_collector.py`; Cookie/path/HK-policy/lineage tests |
| Engineering AI | Codex selected model; historical .opencode/opencode.json | No retired local-model/Zhipu/OpenCode calls; engineering resources never own Product Truth. |
| Startup/runtime | `scripts/start_production.ps1`; `app.py`; `run_supervised.py`; `runtime_preflight.py`; existing `lumenis/blueprint.py` → `lumenis/version_center/` compatibility startup caller | `/healthz`; required initialization; critical API/App runtime evidence. Preflight uses Shared Database's registered data path and reports platform capability LIVE_NOT_VERIFIED; directory/module discovery is not a running user outcome. Version-center background saving must default off; it is not a second mainline acceptance/publishing authority. Manual version actions remain separately authorized. |
| Operations/deployment | Existing `scripts/`, `deployment/` and environment manifests | Use only the launcher/deployment artifact named by the active acceptance gate; scripts do not become product owners |
| Tests and release evidence | `tests/`; `app/test/`; `tests/CI_TEST_TIERS.md` | `.github/workflows/`; exact release/production acceptance artifact for the current commit |
| Historical/provenance material | Dated handoff/audit/archive and `intelligence_library/` | Read only when the active owner trace needs provenance; never use it as current runtime truth |
| Real delivery and commercial gates | `00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md` under the sole Product Architecture and Experience Constitution | Per-round real-delivery constraints, `REAL DELIVERY CARD`, E2E evidence and Section 23 commercial-readiness gaps; not a source/API/data/design owner |
| Global universe, focus context and data maturity | `00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md` as a subordinate contract; current execution remains in `subject_context.py`, registry, Shared Database/Evidence, Permission and Product Core owners | One internal full-universe edition; default `GLOBAL / ALL`; Global→Focus→Return; honest states; three supporting coverage dimensions; no second owner, product, release or test-Subject default |
| Third-party code/assets | Registered dependency manifests, `vendor/` when present, and `THIRD-PARTY-COMPONENT-REGISTER.md` | License, version, adapter boundary and replacement direction; never absorb it into LUMENIS ownership silently |

The three retired disk-wide discovery scripts are recorded at fixed Git history in the approved-convergence evidence. Normal work uses the existing capability locator and this index, never the old hard-coded D-drive or historical repository paths. The locator is not an equivalent full asset-graph generator.

### File placement rule

New production code goes into the canonical owner above. New Flutter code goes into the owning `app/lib/features/<owner>/<screen>` slice, with stable cross-feature primitives promoted only after proven reuse. New Experience contracts go into the existing `contracts/experience/` family. The approved `website/` root is restricted to Public Website presentation/acquisition; its committed foundation does not pass the ROUND 08 business-entry or release gate and cannot own operational product logic. Do not add any other top-level frontend, collector, AI gateway, database, permission system, evidence store or design authority.

## 4. Fixed per-task inspection route

Do not repeat a full-repository audit for normal work. Use this route:

```text
live origin/main
→ this index row
→ active screen/workflow specification or contract
→ exact canonical owner
→ direct callers
→ direct tests
→ required runtime/E2E evidence
→ update the same row/specification if ownership changed
```

For a screen task, the fixed route is:

```text
Experience Constitution
→ contracts/experience/screen-specifications/<ID>.md
→ contracts/experience/screens/<ID>/ + binding registry
→ app/lib/features/<owner>/<ID>
→ app/test/<matching owner>/<ID>
→ current Product Core route/owner/tests
```

A repository-wide re-audit is allowed only when one of these triggers occurs:

- a canonical owner in this index is missing or has split into competing implementations;
- a change adds a top-level product surface, database, runtime, collector, AI gateway, Permission or Evidence owner;
- current source and this index disagree about a business owner or read/write path;
- a blocking Only-One, Experience or takeover validator detects structural drift;
- the product owner explicitly changes product architecture or requests a new full audit.

Routine commits, runner/DNS failures, stale historical documents and a single `UNKNOWN` binding are not full-audit triggers.

## 5. Historical source-audit disposition (not current capability status)

The table below records the earlier audit baseline, not live source status. The current Public Website foundation is committed under `website/`; the Flutter Web Workspace build and host have local evidence but protected CTH/BMP browser access remains blocked. Use the current owner matrix above and dated Round 08 evidence for present status, without treating either source presence as release acceptance.

| Area | Source-backed finding | Status for execution |
| --- | --- | --- |
| Multi-surface Experience | The “Website/Web Workspace/deployment absent” statement is the frozen historical audit baseline, not present status. Current route: committed Public Website foundation under `website/`; Flutter Web Workspace, Desktop and Mobile use `app/` and the shared Core (`/workspace` host); Product Architecture, README and CURRENT §1 describe each role. | **PARTIAL / LIVE_NOT_VERIFIED**. The website foundation is not a deployed commercial entry; Web build/configuration, protected browser access and complete four-surface real-user operation remain unaccepted. Use current source and runtime evidence; never repeat the historical “absent” statement as current. |
| Product account | The accepted pre-beta Flutter launch reads Product Core runtime identity without `/v4/auth/login`, `/v4/auth/logout`, or a startup Subject Registry fetch. Loopback-only Core transport bootstrap remains separate; CTH-02 calls the existing account-protected registry only when opened and contains 401/403 locally. Media Cookie/session state remains in SYSTEM. | **TESTED SOURCE / LIVE BACKEND CONTRACT VERIFIED / PACKAGED UI UNVERIFIED** at that source checkpoint. Product account/password design is deferred until 100% product closure and subsequent Product Owner redesign; the observed 401/403 remains a pre-closure access gap. Focused Flutter tests and 75 isolated Python Auth/API regressions passed at that checkpoint; the live repository DB was not opened or altered for testing. |
| OpenCode | Historical configuration retained | RETIRED / DO NOT CALL OR PROBE. |
| Ollama and Jev | Interfaces/history retained, C2 follows owned-model milestone | RETIRED / INACTIVE; no calls, probes, auto-discovery, fallback or reactivation. |
| Media Cookie collection | SYSTEM collector/browser owners, XHS/RedNote bridges, HK-policy checks, Cookie path and lineage tests exist. Secrets are runtime-only and excluded from Git. | **IMPLEMENTED SOURCE / LIVE SESSION UNVERIFIED IN THIS AUDIT**. Preserve existing Cookie flow and verify only through authorized runtime acceptance. |
| Backend gaps | The registry retains 54 fail-closed binding rows; current backend capability remains distributed across canonical and compatibility callers. M's 2026-10-06 repair gives `/api/ai/tasks` one GET/POST owner while preserving TaskEngine and Skill Execution dispatch; `/api/ai/analyze` and its legacy compatibility routes call the owned Gateway and truthfully return unavailable until the promoted runtime is bound. `canonical_data.py` is the sole business Canonical writer; `zbc_canonical_data` is retained as legacy derived analysis history. KOS `/collect` delegates to `secondary_collection` with actor, exact BrandFocus and approval; four direct CLI `persist_live` callers remain compatibility paths still awaiting transaction/scope convergence. Shared Database note upsert now leaves absent sentiment/risk/relevance/scores UNKNOWN/NULL for new rows and preserves existing assessments when refresh omits them; unknown topic sentiment is no longer folded into neutral. Existing historical rows are not rewritten. The legacy v4 importer now delegates whole-source confirmation to Shared Document Import with rights, exact scope and Evidence/Canonical lineage; no notes rows are written, while the packaged UI caller remains absent. Direct notes-table compatibility writers in `lumenis/adapters/persist.py`, `lumenis/system/collector/runtime/pipeline/persist.py` and historical import/migration tools remain open for exact owner convergence before claiming every ingestion route follows the unknown-state contract. The real owned-runtime binding and other Skill/Cookie callers remain open. | **PARTIAL SOURCE REPAIR / PRODUCT CLOSURE OPEN**. The route contracts, OpenAPI map, unique Canonical/evidence linkage, and unknown-state writer are covered by targeted tests; remaining rows still require their own source and real-outcome evidence. Preserve unique behavior and existing owners; do not manufacture 54 APIs or a third execution path. |
| Legacy-looking root callers | Root modules still carry active compatibility/caller behavior. | **CLASSIFIED, NOT DELETION-READY**. Move/delete only after call graph, behavior, data and tests converge on the canonical owner. |

This disposition freezes where work starts; it does not freeze code. Each delivered slice updates its own specification, evidence and affected index row so future work resumes from the fixed path rather than rediscovering the repository.

### Current Collector platform-convergence ownership — Product Owner 2026-10-07

2026-10-08定向DDD执行补充：本索引的Owner行和既有caller/contract就是限界上下文与上下文映射入口；不建立新的DDD台账。仅对当前任务实际暴露的名称/身份、规则、映射、越界调用或状态/来源传递问题，由当前唯一业务窗口修复原Owner/兼容层，保留Permission/Evidence/Canonical及全部功能。F消费合同，不在界面重定义业务；M处理跨Owner冲突。正向操作、越界拒绝、身份/版本/来源连续性及不退化沿原Gate验证；无当前成果收益则DEFER。

The current platform program is not capped at the six primary acceptance platforms. C1 owns universal platform acquisition through the existing one Collector; C6 owns shared runtime/integration/release; F owns the single platform-recovery Experience; M accepts the cross-owner result. The absence of official/partner API authorization before investment/product closure is an explicit current condition and does not lower the required data capability. Product-Owner-authorized owned R&D accounts and managed read-only sessions remain valid development sources under current safety/Permission rules. Future official/partner APIs are provider upgrades behind the same connector.

Mandatory convergence IDs:

| ID | Owner(s) | Required result |
|---|---|---|
| COLLECTOR-P0-01 | C1 C6 | Production XHS/RedNote recovery can resolve only the approved HK/International identity/current endpoint; protected Mainland/9222 cannot be selected. |
| COLLECTOR-P0-02 | C1 C6 | Queue ack/fail/checkpoint/heartbeat are fenced to the active server-issued attempt/lease/run; stale workers cannot mutate a newer attempt. |
| COLLECTOR-P0-03 | C1 C6 | Server-authored durable task/result receipt; terminal replay never re-executes completed work; native pagination remains separate from query continuation. |
| COLLECTOR-P0-04 | C1 C6 | `/api/collect` and all retained compatibility callers use the one Collector/Permission/Source/Evidence/Canonical transaction instead of notes-only production success. |
| COLLECTOR-P0-05 | C1 C6 | `canonical_data` remains sole business Canonical truth; tests/gates reject required legacy dual-write restoration. |
| COLLECTOR-FND-01 | C1 C6 | One PlatformManifest owns/validates aliases, native fields, capabilities, providers, runtime registration, recovery needs and maturity projections. |
| COLLECTOR-FND-02 | C1 C6 | One PlatformSession owner projects auth/verify/risk/runtime/recovery truth; Cookie/CDP/status-file details are implementations, not competing truth. |
| COLLECTOR-FND-03 | F C6 C1 | One LUMENIS recovery sheet handles QR, controlled login, VERIFY and cooldown states, health-readback and exact-task resume across applicable operational surfaces. |

Do not scale the platform count by cloning independent login managers, status files, route families, hard-coded platform lists or UI modals. A new platform must prove runtime registration, truthful capability/state, Source/Evidence/Canonical admission, recovery/retry semantics and a useful consumer result.

## 6. Historical ROUND 02 Root Caller convergence snapshot

`LUMENIS-ROOT-PYTHON-CALLER-INVENTORY-ROUND-02.md` is the accepted LUNA-004 evidence inventory for baseline `c3036aa714ff3236e1267d33cbfb9d2aa33ed000`. SOL-005 independently verified its 191/191 tracked-root coverage, unique rows, path existence, status/disposition enums, current SHA and blocking validators. The inventory remains evidence; this index owns the decision below.

| Historical ROUND 02 disposition | Count | Recorded decision | Historical exit condition |
| --- | ---: | --- | --- |
| KEEP | 131 | Keep the current executable owner/caller. A later owner-specific round may adapt it, but location or legacy spelling is not a removal reason. | Current contract/tests preserved; owner change requires explicit task and affected regression. |
| ABSORB WITH PARITY GATE | 37 | Send to its named canonical owner in the scheduled DB, Permission/Evidence, Runtime, Collector/Browser or AI/Agent round. `ABSORB-CANDIDATE` is not deletion approval. | Direct and dynamic callers, API/CLI/data behavior, Permission, Evidence, migration/rollback and tests are proven on the canonical path. |
| PROVENANCE / LAST REVIEW | 20 | Retain until dynamic import, CLI, workflow, manual-operation and reproducibility dependencies are checked. | Historical retirement required a separate decision; current disposition follows AGENTS.md and the exact active owner, not this dated queue. |
| OWNER UNKNOWN / BLOCKED | 3 | `evaluate_system_timing.py`, `review_workflow.py` and `topic_monitor_policy.py` stay in place. They are excluded from migration/removal until an owner and runtime scope are proved. | Owner, callers, contract, data/Permission/Evidence effects and tests are explicit. |

`domain_adapter.py` remains KEEP as the only proved current implementation, although its higher-level owner family still needs domain review. No root Python file is approved for retirement or deletion in ROUND 02. Destructive cleanup remains closed until the sole behavior has migrated and passed its owner-specific gate.

The historical caller-cleanup dependency order preserves Database/Permission/Evidence before dependent Runtime/Collector/AI/API work and provenance-only removal last. It does not create a serial dispatch queue: current C1-C6 owner contracts and actual dependencies govern execution. Jev and the legacy local/Zhipu provider routes are retired; retained source and history stay inert and are not a pending ROUND 07 activation or comparison requirement.

## 7. Cross-round capability gap register

This table is a dated owner/dependency lead, not a scheduling or activation queue. Current live dispatch comes from the top of `AGENTS.md` plus the newest explicit Product Owner instruction for the specific window. M, F and C1–C6 are eligible roles there, not an assertion that all are running; before each dispatched task, the owning window still resolves fresh `origin/main`, protected dirty work, owner/callers, runtime/DB/Permission/Evidence and external dependencies. A dated live check below is evidence, not a durable availability promise.

| Gap / verified lead | Historical lead and current disposition | Current C owner and retained R acceptance input | Boundary |
| --- | --- | --- | --- |
| Ollama durable startup | Historical LUMENIS-Ollama-Autostart, qwen3:1.7b, bge-m3, qwen2.5-coder:7b-agent references remain provenance | SUPERSEDED by retirement; C6 proves Core/approved owned-runtime durability | No re-enable or probe. |
| Engineering and canonical Zhipu routes | Historical successes retained | SUPERSEDED; C2 proves owned-model business outcomes | No calls/probes/fallback or credential publication. |
| Retired local-provider references | Historical `local_ai_client.py`, qwen and local-provider references are provenance and compatibility artifacts, not an available inference route. | **C2/W2; retained R07/R15**: bind approved LUMENIS-owned foundation-weight training and inference through the sole SYSTEM AI Gateway, preserve explicit unavailable states, and prove useful results and recovery. Inspect retired references as source only when a current caller gap requires it. | Do not call, auto-discover, probe, fall back to or reactivate a retired provider; changing a model string or registering a provider is not owned-AI acceptance. |
| LUMENIS-owned AI with retired Jev history | The Product Owner has already retired Jev. Preserve its compatibility interfaces and historical artifacts inert; no Jev comparison or reactivation is a prerequisite to the owned-model milestone. | **C2/W2; retained R07/R15**: use the single Gateway and approved open base weights/materials to prove actual training, checkpoint/resume, reload/inference, pinned contract and source lineage; assess accuracy, calibration, multilingual and low-confidence behavior, latency, failure/recovery, shadow evaluation, trace, controlled promotion/rollback and useful real user outcomes. Missing owned inference remains an unfinished milestone to solve. | AI never owns Permission, Evidence, Product Truth or effects. Codex model configuration and Cloud development are engineering resources, not deployed product inference. Do not call/probe/fall back to Jev or revive retired providers; retained output is not approved training data without its own material/use approval. |
| Legacy topic campaign identity path | At `15ece66f`, `topic_campaign.py` fences its former 9222/profile collector, health, recovery, scheduler and backfill entries before collection I/O. Missing or hostile endpoints are blocked; even the explicit HK 9223 route returns `CANONICAL_COLLECTOR_BINDING_REQUIRED` because the old workers still target the Mainland site. App registration still initializes existing storage. This is source and isolated-test evidence, not live HK collection. | **ROUND 06 Collector / Browser**: bind campaign and detail callers to the existing HK/international allowlist and `lumenis/system/collector/` owner; prove manual, automatic and recovery paths with real authorized source/Evidence and hostile 9222/profile tests. | Until the canonical binding passes, collection stays unavailable. Isolated Core acceptance continues to use the no-collect staging gate. Never probe, launch or use the personal Mainland account, port or profile. |

## 8. Business end-state to current implementation — 2026-09-23 local delta

This is a Task Card input derived from the Product Owner's business calibration, not another Product Architecture or evidence of round acceptance. It was mapped against local `main` at `5ba1aefc53a1babc293e990c23c62f841724c843` with protected, uncommitted work. Local source presence is not a released user outcome; recheck the active source and evidence at each owning round. At that historical mapping, ROUND 02 still needed coherent executable-source integration; the later committed [ROUND 02 Charter](LUMENIS-ROUND-02-CHARTER-CURRENT.md) records a bounded `PASS` for its actual Windows SYS-01 job. Neither status enlarges acceptance to the App or business rows below.

| Real user / job / deliverable | Need | Existing owner and local implementation | Current evidence limit | Owning rounds and required complete exit proof |
| --- | --- | --- | --- | --- |
| Commerce operator: verify a venue's actual brand, store, event and on-site resources; deliver an actionable content or operations plan | REQUIRED | CTH Subject/workflow plus Shared `content_generation.py`, `lumenis/shared/reporting/`; `experience_runtime.py` and Flutter CTH/Shared screens are local consumers | `PARTIAL / LOCAL_ONLY`: one official public Source→Evidence→Canonical→report slice was run in isolation. Store availability, on-site exclusivity, internal resources, approval and outcome were not established | ROUND 06, 10–11, 14–15: distinguish brand-wide launch, local stock, store priority and unconfirmed claims; carry verified resources into a plan, human confirmation, action and outcome with trace |
| Brand lead: relate consumer need, market and competitors to positioning, content, channel and creator choice; deliver a decision basis and Brief | REQUIRED | BMP domain in `experience_screens.py`, local Flutter BMP screens, Shared creation/reporting, canonical Evidence/Permission | `PARTIAL / LOCAL_ONLY`: screen/source presence and tests do not prove real creator fit, channel results or a completed brand job | ROUND 12–13, 15: real authorized brand/competitor/creator input, comparable alternatives, approval, artifact and measured feedback; no popularity-only recommendation |
| Research or content lead: move a finding into a plan, Brief, draft, review, report and later evaluation without re-entering its context | REQUIRED | Shared `content_generation.py`, `lumenis/shared/reporting/`, `lumenis/shared/evaluation/`, `lumenis/shared/learning/`; Product Core ViewModels | `PARTIAL`: individual endpoints and persistence paths exist; a cross-artifact, user-visible return path is not live verified | ROUND 07, 09, 11, 13–15: trace the same authorized scope and source IDs through artifact versions, approval, result, evaluation and a reviewable learning asset |
| Content creator: obtain a proposed video cut, revise it manually, or begin with an empty timeline and export a final film | REQUIRED | Existing Shared Content & Creation and Artifact/Reporting/Evaluation owners; one Product Core and approved Shared surface | `LOCAL CANDIDATE / NOT PRODUCT VERIFIED`: twelve separate source videos have twelve locally rendered candidate cuts and a learning card, but the untracked timeline engine, render integration, product API, permission/evidence binding and real user review are not accepted mainline capability | ROUND 07, 14–15: source rights and identity → versioned automatic proposal or empty timeline → user trim/split/reorder/delete and review → real render/export → reopen/adjust → Evidence/Permission/Artifact/evaluation and failure recovery; prove both automatic and manual paths with real media and user-visible E2E, without a second media owner |
| Operator or brand lead: enter GLOBAL / ALL, add or focus any permitted Subject/BrandFocus, then return without changing acquisition ownership | REQUIRED | `subject_registry.py`, `subject_context.py`, `lumenis/system/security/permission.py`, Flutter shell and canonical database | `PARTIAL / LOCAL_ONLY`: focus APIs and UI code exist; real global discovery, non-reference samples and commercial visibility are not mature or accepted | ROUND 03–08, 09–15: exact actor/scope authorization, real entity coverage and honest uncollected states; rotated non-reference CTH/BMP samples and background independence |
| Team member: discover an applicable product Skill, understand scope/risk, execute and inspect the actual result | REQUIRED | One persisted Skill owner `lumenis/shared/agents/skills/{registry,lifecycle,execution}.py`; compatibility caller `account/skills.py`; `/api/experience/shared-skills` and `/run` | `PARTIAL / LOCAL_ONLY`: catalog and guarded execution exist; this does not prove a complete user-facing Skill collection/store or all Skills usable end to end | ROUND 07, 14–15: catalog→permission→execution→artifact/Evidence→history and failure recovery on an actual page, without a second registry |
| Web worker, desktop power user and mobile reviewer: resume one task across surfaces | REQUIRED | One Flutter `app/` for Web/Desktop/Mobile, one Product Core API; local `website/` pages are presentation only | `PARTIAL / LOCAL_ONLY`: builds and page files exist; cross-surface identity, state continuity, device operation and commercial entry are not released | ROUND 08–15: one task/scope/Permission/Evidence contract and actual Web→Desktop→Mobile return path; Public Website owns no business truth |
| Product owner: know which industries and entities have trustworthy depth and which are only supported for basic research | REQUIRED FOR CLAIMS | Canonical registry, Collector, Evidence, reporting and Global Universe maturity contract | `PARTIAL`: isolated public-source proof is not global commercial or brand maturity; no universal coverage claim follows from it | ROUND 06, 10–13, 15: disclosed population, source rights, freshness, completeness, lineage, random entity samples and role-specific work outcomes |
| Additional industry presets, one composite success score, or replacement of POS/member/finance/property systems | OPTIONAL / NOT NOW | No new owner authorized | No real-job baseline or integration contract establishes necessity | Do not add a dashboard, screen or owner. Reconsider only from real role evidence within an existing round and approved source/permission boundaries |

Acceptance language for these rows follows the existing real-delivery overlay: show the user a task, relevant content, a defensible result and an available next operation. Facts, assumptions, unknowns and causal claims remain distinct. AI, external research and copied designs cannot supply missing business truth. No sixteenth round or new Core/Database/Evidence/Permission/AI/Agent/Context/Experience owner is created.

### 2026-09-23 business calibration decision

The 2026-09-23 product evaluation was accepted as a sharper **user-work acceptance test**, not as proof that local screens or source reports already complete a professional job. At that historical checkpoint Round 03 still owned safe storage, scope and lineage prerequisites. Its isolated official-source report proves a traceable source could be saved and reopened; it does not prove a store has stock, an operator has a plan, or a brand lead has a defensible Brief.

- **CTH, ROUND 10–11 and ROUND 15:** an operator must be able to tell why an authorized fact matters to the selected Subject and job, what remains unverified, which legitimate next operation is available, and what happened after an approved action. Do not infer a store-level claim, priority or recommended action from source presence or popularity alone.
- **BMP, ROUND 12–13 and ROUND 15:** a brand lead must use real, comparable consumer/market/competitor/creator evidence to make a bounded choice and carry its rationale into a Brief, approval, result and feedback. Popularity alone is not creator or channel fit.
- **Shared and surfaces, ROUND 08–15:** preserve scope and source IDs as a user moves among research, plan, draft, report and review. Public Website copy may describe the intended role and task but must not present fictional examples, one local source report or an unconfigured entry as delivered customer outcomes.
- **Already covered / defer:** the existing CTH, BMP, Shared and SYSTEM owners, GLOBAL / ALL focus, Evidence/Permission chain and 15 checkpoints remain. Additional industry presets, a composite success score and replacement of POS/member/finance/property systems stay `OPTIONAL / NOT NOW` until a real job and owner contract justify them.

## 9. Dated full-repository audit coverage — 2026-10-03

The Product Owner requested this capability audit during an earlier product pause. The [dated audit](evidence/round-15/full-product-audit-20261003/SIX-ROUND-CLOSURE-REPORT.md) covers the tracked roots, source/caller slices, dated DB/runtime snapshots, 54 binding rows, R01–R15/J1–J8/U01–U25 and six urgent exits; it is not today's runtime or user status. It did not recover the complete historical user/material universe. The 191-row Material Owner Manifest is a direct-reference assignment snapshot, not that complete universe and not proof that assigned bodies were read. Current source/runtime status follows a fresh check; no capability is accepted by inventory inclusion.

## 10. User requirement and research recovery — 2026-10-03 correction

The earlier audit inventories source and contracts, not the complete historical
user requirement corpus. Do not claim all M/C1-C6/F requirements are captured
until their actual user messages and material manifests have been reconciled.
Keep every unretracted requirement with source thread/date/attachment, C/R/J/U
owner, four-surface applicability, adoption, implementation and acceptance state.
Historical100-200 reference and12 editing-exercise corpora remain distinct archives.
The latest explicit F scope is two new plus earlier five videos, existing analysis
and OpenAI/current product material; further exhaustive old-video study is superseded.
The exact accessible inventory is measured, with missing/duplicate references
recorded rather than invented or silently excluded.

Research enters both product-capability improvement and separately authorized
AI training/learning. Books, courses, papers, open-source work, user videos/images
and official product/support/release material remain traceable to actual changes.
Each dispatched/RUNNING owning window corrects narrowed rules inside its scope and owns its
authorized work through real outcome verification; M resolves cross-window rule,
architecture, integration and acceptance conflicts. An audit finding alone is not
resolution. Current execution state, account/model selection and resource
authorization come only from current `AGENTS.md` and direct Product Owner
instructions. M, F and C1–C6 are eligible delivery participants; live activity is determined by the current dispatch state, and capability-specific
Permission, runtime/session/resource and paid-effect boundaries still apply.
Existing/free compute is preferred; no historical budget authorizes payment.

## 11. Material accountability and missing-entry requirements

The Product Owner assigned video/material work to existing outcome Owners. Use
[Material Owner Contract](evidence/round-15/full-product-audit-20261003/MATERIAL-OWNER-CONTRACT.md)
and [per-reference manifest](evidence/round-15/full-product-audit-20261003/MATERIAL-OWNER-MANIFEST.json)
as evidence and lookup, not another authority. F/C4 own their reference corpora;
C5 owns cross-material intake, source/rights/citation/research transfer and the
receiving-owner handoff record; C3 consumes accepted research/business inputs for
CTH/BMP outcomes. C1/C2/C6 own their respective data/AI/runtime inputs. Every recovered and newly discovered
item gets a primary Owner; unread/missing remains an obligation. These are
responsibility assignments, not activation. The latest direct PO instruction also
authorizes M's research assistants to recover and read all unfinished originals,
including local DeepSeek/ancestor materials and F/C4 references, and to converge
existing non-C1 work. This does not resume paused delivery windows or transfer
their architectural ownership. Reuse actual pinned readings; summaries, directory
counts and unverified authorship do not close the original-material obligation.

Retained video/podcast timeline horizontal interaction maps to C4/F/C6 and J5/J6,
U14/U15/U23. Developer mode maps to existing SYSTEM settings/security/runtime,
C6/F and U22/U24/U25; source settings_module.py still registers its flag and routes
through app.py. The Product Owner now marks developer mode DEFERRED_BY_USER; preserve its
requirement and source but do not implement or make it a current closure blocker.
Actual AI training remains a P0 capability obligation under C2/C6. Readiness,
resource authorization and execution state require current proof under AGENTS.

2026-10-04 execution correction: every current C window keeps its full result
scope and continuously closes it under AGENTS, rather than stopping at a minimum
function/file slice or repeating unchanged handoff checks. Owner boundaries do
not shrink outcomes. C2 prioritizes existing/free compute; no GPU SKU is
preselected by this index. Paid compute requires current explicit cost
authorization; historic 4090/5090 proposals are evidence only. The named
responsibilities remain; M handles actual decisions/acceptance and otherwise
stands by when no actionable work remains. Historical goal receipts preserve
prior states; current execution comes only from AGENTS, not a resumed old goal.


## Current combination acceptance — 2026-10-04

These are cumulative result assertions mapped into current owners/C/R/J/U, not
new rounds, stores or a separate queue. Input current-status claims in the user's
table are hypotheses to check, not a live completion declaration.

| Combination | Existing owner / complete C responsibility | Required actual result |
| --- | --- | --- |
| Collection + entity + Evidence + transaction | SYSTEM Collector/Browser/Scheduler, subject_registry.py, Shared Database/Evidence; C1+C5+C6 | Purpose/topic-semantic query yields exact scoped, topic/task-derived Source/Evidence/Canonical with optional requested time constraints and a useful answer; relevance, formal intake, transaction, refresh and independent continuous recovery work. |
| Task + Word + SavedWork | existing Shared Content/Artifact/Task composition, internal_pitch.py, current Core binding; C4+C3+C5+C6 | Actual task/DOCX/saved version connects; repeat is idempotent, cancellation cannot commit, revision keeps parent, independent reopen/recovery preserves bytes and source versions. |
| Research inputs + multiple creation formats | existing Importer/Research/SourceBrief/domain workflow + Shared Content/Artifact; C3+C5+C4+C2+C6 | One real Brief/evidence/context enters useful text/video/podcast alternatives; changed constraints continue without repeated input, false AI/source use or lost versions. |
| Training + permission + remote process + Artifact | SYSTEM AI Gateway/owned training, existing Permission/effects/runtime and Artifact; C2+C6 | Actual remote load/step/loss, physical checkpoint bytes, reload, cancellation/disconnect recovery, independent held-out and normal owned inference; controlled promotion/rollback. |
| Edit + replace + render + save | Shared Timeline/content_creation/rendering + podcast + Artifact; C4+C6; F responsibility | Local edits/replacements do not corrupt the full work; render/save remain consistent and final editable projects reopen with versions and meaningful recovery. |
| Source correction + judgment + result versions | Shared Evidence/Trace/Research/Artifact/SavedWork/Evaluation, domain consumers; C1+C3+C5+C4+C6 | Locate every linked affected conclusion/artifact, explicitly adopt correction, revise affected parts, preserve unaffected content and old results/reasons/rollback; no rewritten Evidence. |

| Current priority | Existing complete owner package | Actual acceptance |
| --- | --- | --- |
| Remote training normal chain | C2+C6 | GPU load, optimizer step/loss, checkpoint bytes, reload, cancellation and disconnect results. |
| Training/business recipe consistency | C2+C3+C5+C6 | Same accepted model/recipe/token budget in actual normal Gateway business task; candidate/main/runtime/evaluation do not silently mix. |
| Research→creation source transfer | C3+C5+C4+C6 | Same real nonempty Brief/source refs inherit, change constraints, save/reopen/export through current use permissions; an internal no-source craft is not AI research completion. |
| Purpose query→actual collection | C1+C5+C6 | Six major-platform actual task queries, precise scope/relevance, formal Evidence/Canonical, refresh and recovery. |
| Same-version integration/reproduction | C6+related owners | Main, overlay, build, loaded process/model/recipe, DB and actual task outputs/evidence align; reproduced environment and recovery. |
| Real operation on approved surfaces | F+C4+C6 responsibility | Actual four-surface AI submit, horizontal timelines, source/editing/result/save/reopen under current Experience; execution state is solely AGENTS. |

Full source/API callable bindings are resolved within these existing owner roots
and current contracts; a row above is not proof that a missing binding exists.
C1 also owns source-backed presentation text/image examples for F, not a new
layout/renderer. The complete brand/commercial material→budget/resources→editable
outcome→affected-only revised version→old work/reason/rollback path is accepted
through Real Delivery, including semantic and same-budget peer comparisons.


User-reviewed100-term foundation input: C1 owns topic/query/entity binding; C5 existing Source/Importer contracts and C6 formal storage/deployment coordinate. Global§10 retains immutable originals, additive effective versions, all original evidence/null/time fields and runtime admission;100 terms across4 named subjects is not100 subjects, a verified hotlist or global/platform coverage. Existing permission and model-training use remain distinct.


## APPROVED D1–D5 historical-package convergence — 2026-10-06

This section records the Product Owner-approved disposition of the historical revision package after fresh local/origin/runtime/source review at audit base `73ca4b962bab45aacac6429d7dea3b7858f56c89`. It is an execution/acceptance map inside the existing owners, not a new architecture, round, queue, product, database, collector, AI gateway, Permission plane or design authority.

| Decision | Approved current meaning |
| --- | --- |
| D1 | Preserve platform-native facts and lineage, present them through task-specific LUMENIS composition, provide governed `Trace → Open Original → Return`, and keep ordinary source opening separate from SYS-06 controlled capture. |
| D2 | The package's 51 rows converge into **EIGHT OWNER RESULT PACKAGES** below; never restore them as 51 parallel features or a historical product. |
| D3 | Historical notes/comments/brands/relations/cases/web mentions remain immutable evidence, parser/regression, reconciliation or reacquisition inputs. **Production admission = 0** until current rights, source, identity, Scope, Permission, freshness and complete-field gates pass. |
| D4 | Dependency order is Truth/Safety → Collector/durable task → CTH/BMP business → SourceTarget/Open Original → Shared result continuity → Owned AI → same-SHA release. M selects one business Owner at a time by actual dependency; W6 integration consumes that slot. F proceeds independently within shared-region reservations. This does not change the six outcome owners or impose numeric round order. |
| D5 | Update only the existing Product Architecture, Experience, Source Owner Index, Real Delivery/CURRENT, screen/binding/action contracts and blocking validators. AGENTS remains the sole router and the current Only-One architecture is unchanged. |

### EIGHT OWNER RESULT PACKAGES

| Result package | Primary current owner | Required participating owners | Complete result / acceptance exit |
| --- | --- | --- | --- |
| 1. Source / Collector / Durable Task | C1 | C5 source/rights; C6 API/runtime; C3 consumer; F operation | Purpose-bound query and authorized source produce native records, continuation/native pagination, durable task receipt and fenced attempts, Source/Evidence/Canonical, truthful partial/failure/recovery and a useful business result. |
| 2. SourceTarget / Open Original / Return | C5 Shared Evidence/Research contract + F Experience + C6 transport | C1 source fields; C3 CTH/BMP meaning | The same authorized record carries `lumenis.source-target/v1`; LUMENIS renders it without copying platform chrome; user-gesture HTTPS handoff reports honest launch state and Return restores exact context. |
| 3. CTH business loop | C3 | C1, C2 when bound, C5, C6, F | Monitoring/event/calendar/feedback/trend/case/risk/decision/action/outcome/evaluation use exact Subject, source and time; save/revise/reopen/recover and source trace work. |
| 4. BMP / Entity / Official Source | C3 | C1 entity/source, C5 research, C2 when bound, C6, F | Exact BrandFocus/market/competitor/creator/content/propagation/campaign flow, canonical identity/relations and official-source handling produce a useful result without CTH/default-Subject leakage. |
| 5. Shared / Reporting / Settings / Recovery | C5 | C3/C4 consumers; C6; F | Import/library/search/citation, SavedWork/Artifact/report/export/notification/preferences and source-correction continuity preserve rights, versions, parents, rollback and honest states. |
| 6. Owned AI / Agent / Learning | C2 | C3/C4/C5 consumers; C6; F | Real training step/loss/checkpoint/reload/resume, held-out evaluation, normal Gateway business inference, Agent/Skills/Memory, reviewed learning, promotion/rollback; unbound runtime stays unavailable. |
| 7. Historical Intake / Quarantine | C5 | C1 identity/reacquisition; C6 storage/migration | Immutable package/hash, field-presence and rights/scope decisions, duplicate/current-vs-observation reconciliation and explicit reacquisition; no direct Production/metric/report/training admission. |
| 8. Four-surface Integration / Release | F + C6 | M acceptance and every owning C window | One same-SHA Core/DB/API/build contract across Website/Web/Desktop/Mobile roles, real task/state/recovery/Return, Product/App/Critical E2E, packaging and rollback; no source/build/HTTP-only release claim. |

### Fresh verified repair targets from this approval

These are current owner targets, not completion claims:

1. CTH-03 backend already returns `source_url` plus verified Canonical/Evidence projection, while the Flutter DTO drops that target; bind the shared SourceTarget contract rather than adding a one-off raw URL button.
2. Generic `bound=true` is route wiring, not screen acceptance. At the audited source only CTH-03 and BMP-01 receive exact scoped read binding in the generic screen route; every other consumer must obtain its own exact owner/scope/projection contract.
3. CTH calendar/trend helper failure can currently collapse dependency error into `0 / ready / live`; missing, failed and measured zero must be separated before business use.
4. SYSTEM task completion needs active-attempt fencing across ack/fail/heartbeat/checkpoint; an old worker must not complete a re-leased task.
5. Collector query checkpoints need authenticated durable task/result receipt binding and must remain separate from native platform cursors.
6. `case_ai_evaluate.py` still bypasses the Owned Gateway and converts invalid scores to `5.0`; it must fail unavailable/unknown and never create a synthetic overall.
7. The legacy special-report route contains fixed propagation and business-impact assumptions; migrate useful rules into evidence-bounded Observed/Inferred/Hypothesis/Unknown outputs and current report owners.
8. SH-03 calls the Canonical connection helper with the wrong signature and can display offline while Canonical data exists; repair the caller, not the database.
9. Historical package candidates remain `0 admitted`; current source/rights/scope/freshness and complete data must be re-established before any Current view, report, metric or training use.

`contracts/experience/source-target-contract-v1.json` is the subordinate machine contract for package 2. Every relevant screen specification maps its own task-specific composition and Return behavior; the shared contract does not authorize a generic copied feed, generic drawer or second source browser.

### Configuration and Flutter toolchain drift control

C6 owns the current runtime/configuration/toolchain composition; F consumes the pinned Flutter SDK; C1/C2/C3/C4/C5 own only their domain inputs. `.env.example` is documentation and must never become a runtime environment. Local `.env`, C2 private endpoint references, Cookie/session files and Production DB paths stay untracked. `app/toolchain.json` is the sole machine-readable Flutter SDK pin used by the App Gate and local verification. `config.py` is a compatibility adapter only: its defaults must remain 8201, owned-Gateway, no cloud fallback and no default Basic account. Historical `TAIKOO_*`/`ZBC_*` names may remain while callers exist, but no default query, login, provider, email channel or test Subject may be activated by absence of local configuration. The blocking owner is `scripts/audit_tools/verify_current_configuration.py`; passing it proves source/config consistency only, not Runtime, device or Release acceptance.

## Complete outcome cards and owner routing after the six closure red lines

The cards below specify full user outcomes, not competing work queues. Current
live dispatch, pause/wait state, model/account selection and allowed effects come from
the top of `AGENTS.md` plus the newest explicit Product Owner instruction for the
specific local window. Under the current route M is controller/integrator, while F
and C1–C6 are eligible owners rather than a live process list. Each dispatched window
continues its complete card after task admission until acceptance, an explicit wait
condition or a real blocker; dispatch never bypasses owner/effect/resource boundaries. Do not create parallel task-card files: each row links its existing
source routes in §3 to J/U/R coverage, the existing material manifest, and the
Real Delivery Card/acceptance fields in the Overlay.

### Research inputs consumed by the existing owners

The retained RC identifiers below locate the existing research corpus, not new
work queues or completed adoption. Original locators, actual read intervals and
rights remain in MATERIAL-OWNER-MANIFEST and each source receipt. The precise
product path below is the implementation destination; summaries alone cannot
close it. Current live dispatch comes from AGENTS.md plus the newest explicit Product Owner
instruction for the relevant local window. Only dispatched/RUNNING roles execute;
eligible or WAITING_DEPENDENCY roles do not self-start. C1–C6 retain their complete
outcome responsibilities, F retains the separate Experience scope, and M reviews
cross-window completeness/integration rather than replacing those owners.

For direct materials, the manifest's `primary_owner` is the reading and
capability-adoption owner; `source_owner_paths` is the existing product route,
not proof of implementation. Supporting-owner transfer requires receiver ACK.
The current 199 direct-reference rows are explicitly not the complete material
universe; secondary references and unrecovered originals stay open under their
existing owner rather than being silently omitted. The latest explicit PO research
assignment allows M's assistants to read F-owned originals while F remains paused;
it does not grant a second Experience authority or automatic frontend acceptance.

Verified improvements are applied promptly through the existing Architecture and
detailed capability contracts. For the running C1 outcome, Global §10 is the
single detailed route for original/partial coverage, source-preserving deduplication,
native time/role/metric facts and downstream source continuity. C1 implements its
own closure and necessary runtime dependencies without a C6 slot switch. M sends
one exact published delta for a relevant changed rule, not per-function approvals.
Do not wait for all research or training before adopting a justified current fix.
Latest direct C1 instruction is subject-led batch acquisition → immediate existing Source/Evidence/Canonical processing → post-intake term analysis, with at most one native cover image per post. Global §10 owns its exact bounded order; full vocabulary/media processing is not a prerequisite, and current owner/identity/rights/coverage/recovery remain enforced. C1 also implements the necessary existing SYSTEM Permission/maintenance-principal internal READ/ANALYZE binding for that post-intake purpose. DATA_IMPORT alone is insufficient; pin each source/hash/version/scope, recheck revocation, preserve original rights, and use existing derived-version/write gates. Reporting/SavedWork business source-use checks are separate consumers and must not be weakened or fed a fabricated user identity. No C6 slot switch or per-function approval is required for this already assigned bounded chain.

Local C2 material-helper corrections are reading/admission preparation only;
the existing current-context/one admission entry selects inputs, while its old
pytest receipts and old provider policy are historical and never runnable
instructions. Preserve exact original identity/hash and reading-unit evidence;
near-duplicate relations do not remove sources. Product use stays routed through
the existing Importer/Research/Evidence owners and separately approved Learning.
The retained C4 main handoff is byte-identical in its three production paths;
consume main, not the old source tree. Media source Artifact binding already
exists, while inherited business Brief/Evidence and actual rights/user outcomes
must be checked through its higher-level owner, not by removing the low-level
editor's rejection of untrusted caller-supplied Evidence.

| Existing research input | Current code/contract destination | Required product behavior and remaining evidence |
| --- | --- | --- |
| RC-01 OpenAI/Codex/ChatGPT/Claude/Muse | `agent_runtime/loop.py`, `lumenis/shared/agents/skills/lifecycle.py`, `lumenis/system/ai_gateway/`, Shared Learning | Continue goals with versioned tool identity and fresh Permission on resume; actual grounded result, cancellation and recovery. Public documentation is not proprietary reasoning or executable model weights. |
| RC-02 user supplements/capability adoption | This index's J1-J8/U01-U25 rows and existing `lumenis/importer/documents.py` | Preserve each requirement, original and unsupported field; bind to a real consumer/result. An extracted document or coverage table does not close its behavior. |
| RC-03 acquisition OSS/public sources | `lumenis/system/collector/adapters/`, `lumenis/system/browser/runtime/` | Exact permitted source, native time/metrics/media, idempotence and bounded recovery; distinguish challenge/auth/outage/parser errors; keep protected personal identity untouched. |
| RC-04 communication/journalism/network | `analysis.py`, `api_dual_domain.py`, `lumenis/shared/reporting/source_brief_job.py`, Shared Evaluation | Separate issuer claim, framing, audience response and observed behavior. Preserve alternatives, sample population/channel/window and uncertainty; attention or sentiment alone cannot prove demand/causality. Existing selective article readings do not mean all textbooks were read. |
| RC-05 advertising law/professional code | Existing content/decision/Fact Wall and Source/Evidence use checks | Keep jurisdiction, effective time, substantiation and advertising recognition attached to claims; corrections propagate to affected content. Current legal applicability needs its primary source; no automatic legal verdict or publishing permission. |
| RC-06 SNU courses and approved statistical-method reading | Existing Research/SourceBrief/Reporting, C3 business decisions, C4 creation and Shared Evaluation task criteria | Use the real business question to choose the existing method, observed unit, scope/time and available data; retain measurement/selection bias, actual count/proportion denominators and comparability. Separate source facts, observed audience response, theoretical interpretation, prediction and causal claims; campaign objectives/strategy/creative recommendations are not executed actions or measured outcomes. Present useful results with source locators, limitations and same-task/version save/reopen/revision. PPDAC is a reasoning method, not a new workflow, mandatory page template or state machine. The MOE standard, read SNU course attachments and publisher's statistical sample inform methods only; course/full-book coverage, source rights, model learning and runtime acceptance remain separate. Unread lectures/textbooks stay open. |
| RC-07 Baseten inference | `lumenis/system/ai_gateway/owned_training_runtime.py`, `owned_training_ssh.py`, `owned_training_checkpoints.py`, `owned_inference.py` | One current recipe and bounded resource/transport/load process; real step/loss/checkpoint/reload, latency/cost and recovery. Missing book sections or device measurements cannot be filled with assumptions. |
| RC-08 audiovisual/V2/editing | `lumenis/shared/content_creation/rendering.py`, existing Timeline and `podcast/intelligence/episode_runtime.py` | Actual changed frame/audio segment, preserved unaffected tracks, editable save/reopen, actual visual/audition review. Retain 12 editing exercises separately from F's reference videos. |
| RC-09 Chinese/English/Korean audio/music emotion | Existing AI Gateway multimodal path, `lumenis/shared/evaluation/multimodal.py`, podcast owner and existing MediaAsset/TimelineClip/Artifact resolver | Preserve sample rate, channel count, `time_base`, `start_pts` and piecewise time mapping through the existing resolver. Read actual media; distinguish transcript/language/speaker/acoustic observation from emotion interpretation; retain timecodes/confidence and human listening. Proposed models and device fit remain unverified until run. |
| RC-10 official sites/support/guides/logs | Experience Constitution; `website/`, `app/lib/features/`; Agent/Gateway owner for engineering behavior | Adopt task entry, return, recovery and truthful availability in appropriate surfaces. Read coverage is per actual article, not a completed entire site; no copied vendor layout or second runtime. |
| RC-11 retained public/Aberdeen sources | `lumenis/importer/documents.py`, Shared Evidence, `source_brief_job.py` | Real source/use/actor/scope admission then locatable citations consumed by an actual task. Original 95,570-byte tar remains NOT_RECEIVED; do not silently reconstruct it. |
| RC-12 source continuity/local revision | `lumenis/shared/reporting/saved_work.py`: `save_work`, `reopen_work`, `revise_work`, `export_work`; `api_dual_domain.py` | Reuse published v3 composition; real nonempty citations, parent/ACK recovery, targeted edits and rollback. Former local-only reports are historical; live normal task and automatic cross-result impact remain open. |
| RC-13 brand/commercial/topic seeds | `subject_registry.py`, `lumenis/system/collector/acquisition_plan.py`, existing Scheduler and Global contract | Versioned additive terms from evidence and task semantics; six-platform topic/task-driven rotation without a universal date cutoff, fresh observations and continuity. Four seeded subjects/100 terms are not global coverage or platform hotlists. |
| RC-14 governance/outcome research | AGENTS, this index, existing Real Delivery and Evaluation | Use the one current implementation and pinned receipts; actual effect and environment/user fidelity separately. Do not create a research registry, permission system or alternate acceptance authority. |
| OpenAI Math / semantic calibration supplement (2026-10-07; within RC-02/06/14) | C1 `acquisition_plan.py`/queue/Evaluation; C2 existing Memory/Gateway/Evaluation; C3 current graph/decision services; C5 Research/Source Brief; C6 Permission/dispatch/gates; F existing ViewModel states | [Pinned original-paper research and Adoption Cards](evidence/round-15/OPENAI-MATH-ADOPTION-20261007.md) distinguish feasibility, optimization, counting and sampling; sampling assumptions and actual population coverage; memory/context experiments; seven existing-owner invariants. Complex algorithms without a demonstrated current workload remain DEFER. Executable adoption now includes strict domain/focus identity, qualified Collector/Provider status, and promoted-only Learning consumption with independent counterexamples. Reuse the published source/test pins; C windows do not repeat M's repair. Research is not training admission or dispatch. [47-term semantic ledger](evidence/round-15/SEMANTIC-CALIBRATION-20261007.md) maps current meanings, compatibility IDs, repaired behavior and separate live-verification limits; no second semantic authority. |

Existing source-owner rows above remain the precise path/contract authority. These complete outcomes retain all prior mapped requirements. Research must change a named existing capability, its quality/credibility criteria or its demonstrated outcome; a matrix alone is insufficient. The ownership map preserves complete responsibilities; it does not independently activate C windows.

The shared `REAL DELIVERY CARD` fields remain in the Overlay; the card rows
below bind complete outcomes to exact existing source families and J/U/R
acceptance. Under the current AGENTS route, F and C1-C6 are eligible delivery
roles and M is the controller/integrator; live execution requires explicit dispatch. These rows are complete outcome
contracts, not permission to bypass real dependencies or create parallel owners.

| Window | User input and canonical source routes | Dependencies, deliverable, recovery and acceptance |
| --- | --- | --- |
| M | Inputs: current AGENTS/CURRENT/Product Architecture/Owner Index, exact cross-window deltas, dirty ownership and integration evidence. | Root controller/integrator: freeze current truth, resolve architecture/Owner/interface conflicts, review complete outcomes, coordinate W6 shared integration, accept or return work, and verify local/GitHub/runtime alignment. M does not replace F or C1-C6 implementation duties. Product closure requires the owning windows complete their mapped R/J/U outcomes and the Product Owner human gates where required. |
| C1 | Inputs: the four C1 manifest rows (one collection-OSS comparison and three user-reviewed XLSX/CSV/JSON seed representations), additive Subject/BrandFocus/aliases, six-platform authorized sources and task semantics. Source: `subject_registry.py`, `lumenis/system/collector/`, `lumenis/system/browser/runtime/`, `lumenis/shared/evidence/`, `lumenis/shared/database/`, `lumenis/system/collector/acquisition_plan.py` and Scheduler. | Deliver actual authorized topic/task-semantic acquisition, explicit requested publication/event windows where supplied, and ongoing rotation for Instagram, Facebook, WeChat Official Accounts, RedNote/XHS, Douyin and X; ingest body/author/native time/metrics/comments/permitted media to Source/Evidence/Canonical and answer a CTH/BMP task. Provide sourced text/image examples for F without copying platform UI. Preserve exact scope/use/identity, personal Mainland XHS exclusion, cursor/idempotency, UNKNOWN, challenge/outage and restart recovery. Acceptance J1/U01–U05/R03–R06; no seed-as-coverage claim. Before actual collection, close the source-audited Facebook result-contract failure, honest status/readiness and alias/manual-capability mismatch, and durable task continuation/native pagination through these same owners; do not blanket-enable platforms or call a file-level cookie check a live session. |
| C2 | Inputs: the two C2 manifest materials (`LUMENIS_AI_capability_audit_20261003.txt` and `声音识听_中英韩与音乐情绪_Codex接入增补.md`), approved open foundation/recipe, the existing MODEL_TRAIN grant and only the already approved 8 training + 4 independent evaluation samples. Source: `lumenis/system/ai_gateway/owned_training*.py`, checkpoint/runtime/SSH owners, `owned_inference.py`, `owned_evaluation.py`, existing Agent/Skills/Memory/Learning; research routes RC-01/07/09. | C2 is eligible when dispatched. Validate the existing exact grant against the same input/resource; do not repeat approval for unchanged scope. Existing/free compute first; no historical payment instruction authorizes a rental and no paid fallback is implicit. Deliver actual load/optimizer step/loss, checkpoint bytes, reload/resume, held-out semantics, normal Gateway business inference, cancellation/disconnect recovery, Agent/Skills/Memory continuity, Evaluation/Learning evidence and controlled promotion/rollback. Acceptance J7/U18-U20/R07 on real CTH/BMP/creation work; samples/preflight/model files are not quality or deployment evidence. |
| C3 | Inputs: real Subject/BrandFocus Briefs, C1 formal source/actor/scope, applicable research/citation outputs from C5, and owned analysis from C2 only when bound. Source: existing CTH/BMP domain owners, Case/Insight/Decision/Action/Outcome/Evaluation objects, `api_dual_domain.py` and mapped business services. | Deliver complete CTH/BMP business work: monitoring/events/calendar, consumer/media/trend/risk, market/competitor/creator/propagation intelligence, cases and decisions, campaign/content lifecycle, authorized actions where promised, actual outcomes and Evaluation. Preserve exact market/unit/time/denominator/source boundaries, uncertainty and recovery; save/reopen/revise the useful result. Acceptance J2/J3, U06-U12 and mapped R gates; a report or proposal is not an executed business outcome. |
| C5 | Inputs: direct C5/importer/research/shared manifest rows plus second-level references assigned through the material route, approved files/web/audio/video, permitted source refs and versioned constraints. Source: `lumenis/importer/documents.py`, `lumenis/shared/reporting/source_brief_job.py`, `saved_work.py`, `artifact.py`, citation/research/reporting/notification/shared-preference owners and research routes RC01-RC14. | Deliver material import/library/search/precise citation, article-by-article research intake, useful research/report results, versioned Artifact/SavedWork, notifications/preferences and save/revise/reopen/export/rollback with exact source/rights/parent/digest/revocation lineage. The current 199-row manifest (191 original plus 8 supplements) is not the full corpus; official-site 4,797 URL inventory and dated 723+18 unread-body entries remain obligations until actually read/adopted or explicitly disposed. Dependencies: C1 source truth, C2 owned analysis only when bound, C3/C4 consumers and C6 shared Core/API/DB. Acceptance J7, U16/U17/U24 and mapped R gates; unread/unknown-rights/unadopted material remains explicit and cannot be called absorbed. |
| C4 | Inputs: 71 direct C4 manifest materials, real Brief/inherited Evidence, permitted media and actual resource constraints; keep 12 editing exercises separate. Source: `lumenis/shared/content_creation/`, Timeline/Artifact/render owners and `podcast/`; research routes RC-08/09. | Deliver separate editable pitch, genuinely rendered/editable video and playable/listenable podcast. Read assigned V2/audio/media methods with exact visual/audio read intervals and rights. Verify timeline pan vs seek, ruler/track/playhead, edit/replace/render, save/export/reopen/cancel/recovery, human review and unaffected-part integrity. Dependencies: C3/C5 source inheritance and C6 runtime/FFmpeg/player; F interface work remains F-owned. Acceptance J4–J6/U13–U15, separate normal results for all three. |
| C6 | Inputs: exact accepted C-owner deltas, source/runtime/DB/API/build/Artifact identity and existing test/runtime receipts. Source: `app.py`, `lumenis_app_api.py`, `experience_runtime.py`, `collector_status_api.py`, `lumenis/blueprint.py`, `lumenis/adapters/collector_service.py`, Shared Database/Evidence, FFmpeg/supervisor and deployment/release owners in §3. | Dependencies: real owner contracts and exact path reservations; preserve dirty/untracked work. Deliver one same-SHA integrated runtime/package with actual API/surface operation, failure/cancel/restart/rollback recovery, required gates and final evidence. For collection, converge existing canonical and V4 callers on one Collector/Task/status/write contract while preserving unique legacy behavior; bind task checkpoints through HTTP and distinguish task query checkpoints from platform-native page cursors. F-reported API-to-Flutter projection/POST issues remain F-owned and were not inspected by M. Developer mode remains user-deferred and recorded, not a blocker. Acceptance J8/U21–U25 and mapped R gates; code/build/health alone cannot prove operation or release. |
| F | Independent four-surface Experience responsibility; detailed front-end source/input remains F-owned. Sole contract: Experience Constitution section 38 and screen-specific contracts maintained alongside direct implementation. F owns Experience across all six deliveries and, when dispatched, owns existing Flutter/Website implementation, real API binding, screen/interaction/state behavior, responsive composition, zh-CN/en/ko localization and accessibility. | Deliver the complete approved Website/Web/Desktop/Mobile experience for every mapped capability, including loading/empty/error/denied/offline/cancel/retry/recovery states, saved-work continuity and user-operable flows. F does not redefine backend truth, Owner, Permission or business acceptance; its complete output and acceptance remain separately owned and feed M/W6 integration. |

### C1/C6 collector source audit — verified repair target, not a new owner

M rechecked these findings against the pinned source `52cd770cde458f73f99e4073014c90a9d850c3f4` at 2026-10-05 23:36 +08. They are source-level findings only; this preparation did not call platform services, inspect the live DB or recheck runtime. The exact implementation belongs to the existing C1/SYSTEM Collector owner, with C6 integrating the existing API, task, status and persistence callers:

| Finding in pinned source | Existing source evidence | Required complete repair and receiving owner |
| --- | --- | --- |
| Facebook adapter did not supply required `CollectionResult.platform` on search, exception, delegated detail/comments/creator, or local health results. | Historical pinned evidence: [`base.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/system/collector/adapters/base.py#L24-L34); [`facebook.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/system/collector/adapters/facebook.py#L69-L119). | **Repaired in the historical M-only source repair batch (execution topology later superseded by current M+F+C1–C6):** every result path includes `platform=self.platform`; `tests/test_facebook_x_adapter.py` covers successful search/delegation plus errors and passes. This is an adapter contract fix only; no normal live Collector/job or platform request was run. C1 owns the adapter; C6 owns composition. |
| Cookie-file/proxy configuration was represented as live readiness; the status API synthesized `ACTIVE`, a request-time `last_check` and an active count without a connectivity check; cached state had no freshness distinction. The same generic loop could inspect the protected XHS identity and trust an unscoped cached XHS row. | Historical pinned evidence: [`facebook.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/system/collector/adapters/facebook.py#L105-L119); [`collector_status_api.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/collector_status_api.py#L51-L66); [`get_all_status`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/collector_status_api.py#L102-L138). | **Repaired in the historical M-only source repair batch (execution topology later superseded by current M+F+C1–C6):** file metadata maps to `NEED_VERIFY`; a metadata check generates neither a connectivity timestamp nor a parsed-record count; cached status/time remain historical (`last_verified_status`) with historical counts in `summary.last_verified`, while current status is `UNKNOWN`; and the generic status route ignores cached XHS state and skips its cookie-vault call because no identity-scope binding exists. Six status tests mock credential metadata and write only to a temporary cache. **OPEN:** `update_platform_status` has no checked-in production caller; a real owner-bound verification producer and its freshness contract must be integrated before any current/active status is returned. C1 owns source status; C6 owns the read model. |
| Facebook/X lacked `manual_collection_enabled`; registry/config lookup did not route all XHS/RedNote aliases through the shared naming contract. CookieVault retains historical `xhs`/`xiaohongshu` keys and the status API has a separate canonical list. | Historical pinned evidence: [`config.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/system/collector/adapters/config.py#L142-L173); [`registry.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/system/collector/adapters/registry.py#L22-L35); [`platform_naming.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/system/collector/adapters/platform_naming.py#L23-L32); `collector_status_api.py` | **Repaired in current main candidate:** Facebook/X are manual, read-only and still background-disabled; registry and capability lookup normalize only the XHS alias family into the existing `xhs` adapter/config key. Canonical source identity and stored history are unchanged; the two existing CookieVault compatibility keys still point at the same runtime paths/auth names, and generic status now reports XHS UNKNOWN without reading them. **OPEN:** no real status producer/caller is bound in this repository, and CookieVault direct `rednote` writes/reads are not newly authorized or migrated. Preserve the existing protected identity boundary; do not blanket-enable platforms or infer live access from flags. |
| The business route did not carry a task-plan checkpoint into `collect_business_queries`; that executor already validates the query-plan fingerprint and completed-key shape. Its checkpoint remains query-level; `collect_search` calls one adapter `search` and does not traverse native page/detail/comment/reply/creator continuations. | [`experience_runtime.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/experience_runtime.py#L847-L909); [`secondary_collection.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/system/collector/adapters/secondary_collection.py#L2186-L2271) | **Repaired in current main candidate:** the business HTTP route accepts and forwards the typed query checkpoint and rejects it on the single-source path; route tests prove both. **OPEN:** caller-supplied query checkpoints are not bound to a durable authenticated task/result receipt, and they do not contain platform-native cursors. The normal executor still does not traverse native pagination or detail/comment/reply/creator continuations; build this on the existing Task/Collector owner, preserve partial results, cancellation/revocation/idempotency, and prove no lost/duplicated pages. C1 owns collection semantics; C6 owns the shared request/response and durable binding. |
| The canonical user-triggered `/api/experience/cth/platform-collection/search` and registered `/v4/adapters/collect` plus `/v4/adapters/task/<id>` use distinct orchestration/status/persistence callers. | [`experience_runtime.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/experience_runtime.py#L825-L919); [`app.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/app.py#L6267-L6270); [`blueprint.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/blueprint.py#L254-L275); `lumenis/adapters/collector_service.py:119+`; `lumenis/adapters/persist.py:590+` | Preserve unique task IDs, polling, risk and platform behavior while delegating to one canonical Collector/Task/Permission/Source/Evidence/Canonical write owner. Retire a legacy entry only after behavior is mapped and accepted; do not mass-delete V4 or create a second queue. C1/C6 share this existing integration contract. |
| A supplied audit reports Flutter decoding/POST gaps and historical rows with incomplete native fields/media references. M did not inspect F-owned source or read the live DB in this preparation. | Backend projection: [`experience_screens.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/experience_screens.py#L377-L439). Supplied audit: `C:\Users\28049\.codex\attachments\d30e7dc6-911d-4606-b95d-c809e736ef0b\已粘贴的文本.txt`; its DB assertions remain report-snapshot evidence, not current DB truth. | F independently resolves its UI/API binding report under the Experience owner. C1/C6 first define the canonical response contract. Any DB repair waits for a separate approved read-only source-row evidence path and exact record/source version; never infer loss from counts or fabricate missing bodies/media. |


当前执行事实只见CURRENT。source-bound/v3曾在`be347f03`发布；该SHA只作历史出处，不是当前基线，其隔离验证不代表Owned AI或真实用户验收。批准后的规则、研究采用与副本处置见 `00-GOVERNANCE/evidence/round-15/APPROVED-CONVERGENCE-20261004.md`。未合入的独有工作继续受保护，不再复制平行实现。


### 2026-10-08 前端审计与工具维护增补

按最新PO直接构建真实前端，依既有Experience/ScreenSpec/Owner合同随源码更新设计决定与验收证据；不等待独立设计稿/Figma或M逐屏设计审批。原DESIGN_EXPLORATION/DESIGN_READY保留为真实设计审核记录，不再作为强制编码阶段；实现与验收据实记录，不建立第二设计真相。已有Figma可编辑工程和局部节点有本地收据，当前云端版本未核；免费受限时沿Experience§38采用可编辑源码，不等待付费。Product Owner 已授权 M 与独立 F，以及 M 按现有依赖选择的唯一业务窗口继续完整既有成果；其余 C 窗等待并保留源码/Goal，W6集成占用同一业务席位；各窗 fresh admission 后执行既有完整成果，本轮仅同步派工规则，不提升运行或用户验收状态。

工具维护保护现有模型/effort/tier、登录方式、权限、网络/代理及会话；只更新核实的稳定兼容版本，开发插件不变成产品依赖。需要中断桌面/会话、重启、扩大权限或新增登录/费用时等待精确批准。既有未发布源代码、私有配置及生产DB保持原边界。

### 2026-10-08 成熟能力复用与竞品机制：原任务的执行定位

两份已全文读取的增补在既有材料清单新增两行；不取代原RC01–RC14研究、原件、有效分析及原窗口完整责任。后续窗口读取其原完整任务、当前源码和本表对应差距，不重新开展无关全仓审计。本表补充原Owner的输入/动作，不新建任务队列。

| 接收方 | 必须复用/核对的源码与输入 | 后续直接执行与退出证据 |
| --- | --- | --- |
| C1 | 现有SYSTEM Collector/Browser、`subject_registry.py`、`lumenis/shared/evidence/`、query/session/runtime合同 | 完成J1基础检索/过滤/原文/分页/增量/恢复；多源趋势与事件资料进入正式真相链，给C3/C5/F真实字段及可用操作，持续采集和六平台边界不变 |
| C2 | AI Gateway、Agent/Skills/Memory/Evaluation及C4转录真实缺口 | 只在需要时评估离线ASR，经现有模型/权重/设备/zh-en-ko质量准入；whisper.cpp音频适配不激活被停用的llama.cpp/Ollama等LLM路径。AI不可用不阻止确定性编辑，研究资料产品采用与训练准入分开 |
| C3 | 当前CTH/BMP服务、事件/Case/Decision/Action/Outcome | 完成真实可比指标、趋势/事件/Campaign、竞品创作者分析、保存导出和效果；吸收Meltwater/Brandwatch/数说故事/识微的适用机制，回到实际任务，不以外部宣传证明序境可用 |
| C4 | `lumenis/shared/content_creation/{video_editing,rendering}.py`、`shared_artifacts.py`、`podcast/intelligence/episode_runtime.py`、原音视频研究材料 | J4提案、J5视频、J6播客分别交付；连已有trim/split/reorder/delete/undo/mix/fade/transition/caption/FFmpeg；核单视频轨限制；播客按播放/真波形/录音/混音→降噪转录/脚本声音关联。与F协调原SH-01/BMP-08；不另建Timeline或Runtime |
| C5 | Importer/Research、`lumenis/shared/reporting/saved_work.py`、Artifact/引用/材料清单 | 资料全文和方法采用进入产品能力；J4/J7现有编辑/审核/预算/版本/重开/导出，提供C4有rights的素材/原文时间码和版本合同；承接GenStudio式审阅修订复用，保持原文及父版本 |
| C6 | 当前Core/API/experience_runtime、FFmpeg/FFprobe、Artifact/DB/恢复集成 | 关闭Flutter→API→既有Owner断链；每种预览/导出/保存/重开有对应真实版本；按目标OS核二进制与媒体许可/资源。App/Product Gate故障继续修复，不因新规则延后；没有真实效果不可通过 |
| F | Experience§38，既有44ScreenSpec及可编辑设计映射；本次仅SH-01/BMP-08增加具体媒体规则 | 普通操作可发现、可直接控制、反馈与撤回；横向时间轴/真实播放器/波形/触控键盘/完整状态；先基础可用再增强智能呈现，保留四端角色和手绘水彩。完整F成果按当前派发执行，fresh admission 后进入 RUNNING |
| M | 同一Blueprint/Experience/Overlay、两增补及现有有效研究、精确Main/dirty/Owner/CI | M 每30分钟轻量核对有变化的完整成果、共享冲突、CI/风险；解决跨窗冲突并审查完整成果；无实际可处理事项立即待命 |

复用方案必须经过第三方登记册的当前版本/许可/平台/性能/安全/回退准入。FFmpeg现有优先；OTIO仅交换；RNNoise仅有降噪缺口；whisper.cpp仅有ASR缺口；播放器/录音组件仅现有工程不足时；OpenShot/MLT须证明现有renderer不能合理满足原批准功能。未选择/未验证的库不能登记为产品已接入。

已有能力观测、两层用户验收及最终证据字段见Real Delivery Overlay“2026-10-08 双层正常成果验收”；状态未测保持真实未验证，不因本表收录升级为已完成。

### 2026-10-08 日期与缺值更正的后续落实

C1沿`acquisition_plan.py`和`adapters/scheduling/prelaunch_baseline.py`移除全局固定起点校验/默认/seed生成，复用原时间和计划版本Owner，保留用户显式范围及旧receipt可回读、不重放。C5/Shared Evidence负责原始时间和缺值原因；C3/Metric负责维度定义、单位、范围与可比性；F界面保留维度并显示“—”及可理解原因/最后核验；C2不能据缺值补造事实。这些架构责任不自动恢复暂停窗口。当前C1完成其获准闭环及必要调用方修复，跨Owner区域沿既有M/W6预约交接，M审阅与集成；F/C2–C6保持暂停。具体合同和已定位源码缺口见Global§10；源码、运行和验收仍须各自证据证明。

### 2026-10-08 逐步交付与逻辑接续定位

详细呈现合同唯一归Experience §38；源码取证和J/U覆盖见 `evidence/round-15/PRODUCT-LOGIC-REVIEW-20261008.md`。后续C2/C6/F先接`ai01_repository.dart`/AI-01真实提交与`ai_gateway/core.py`已有服务执行缺口，再沿同一Task增加语义分段和取消/恢复；不能把body收齐后打字动画当作流式结果。C2负责表现提案与准确度，F复用原生组件，C6按实际合同补齐run/块/版本与顺序；不新造组件注册表或运行时。

C3/C5/C4原职责复用已有SourceBrief/creation-upstream/SavedWork，补业务决策成果到制作的固定版本入口和逐条引用；C4补编辑Timeline→实际渲染→Artifact→重开，C5补引用影响与各自Owner的回滚衔接。当前C1自己改旧日期并接持久采集receipt/原生cursor/兼容入口，M只按既有预约处理跨Owner交接、审阅与集成，不切换C6。这些是原完整成果的依赖顺序，不增加另一组任务编号。具体源码行和未验证范围在同一审阅记录；实际派工依AGENTS最新PO路由，当前F/C2–C6仍暂停，架构归属与历史复工记录不构成当前复工。原合并本地窗口现承接C3，新建本地窗口承接C5，精确身份只依AGENTS当前绑定。

### 2026-10-08 受控电脑与内置浏览器接续

| Owner | 本次应完成的既有路径 | 精确源码/合同与验收 |
|---|---|---|
| C6 / SYSTEM Browser与Runtime | 既有session/action/observe/verify/capture/stop复用；安全远端actor/session绑定、输入与画面revision、独占接管/停止恢复、设备执行适配与共享API | `ai_browser_api.py`、`ai_browser_runtime.py`、`lumenis/system/browser/runtime/`；协调F的`app/lib/core/lumenis_core_client.dart`，不能只删loopback guard |
| C2 / Agent与typed tools | 实际Agent调用上述浏览动作；授权OS电脑任务的真实executor适配既有Runtime/Permission/Effect链；观察/规划/动作/验证/checkpoint/撤权恢复 | `agent_runtime/`、`agent_capability/`、`agent_smart_tool/`、现有SYSTEM security；浏览器能力不等于OS能力；无人值守外部写入未获授权 |
| C1 / Collector | 复用同一会话与当前允许身份，只读采集、受控验证恢复和Source→Evidence→Canonical；继续其他正常平台 | 既有Collector/PlatformSession；`VERIFY`不绕过，个人大陆小红书不触碰 |
| F / Experience | SYS-06手机任务→电脑/浏览器视口→接管→停止→Return；Desktop/Web产品内真实浏览；外部打开可选，SourceTarget模式和调用者一致 | `sys06_screen.dart`、`sys06_browser_repository.dart`、core client、现有SourceTarget/CTH-03/SH-02；既有纯预览不是目标终态 |
| C3/C4/C5 | 同Task/来源/版本消费操作结果与真实资料，不新建执行器 | 已有业务/创作/Artifact引用和回执；研究与训练准入分开 |

基线409e6d2c：浏览器服务已有click/input/select/scroll/keyboard等动作，但Flutter只调用navigate/reload/frame，远端Core受loopback限制；未找到通用OS桌面executor。本次是源缺口与执行标准，不是runtime通过。逐项取证见 `evidence/round-15/BROWSER-COMPUTER-CONTINUITY-20261008.md`；新视频已进入现有材料清单，非训练素材批准。

### 2026-10-08 用户只读审计：当前修复责任与后置边界

材料 `MAT-3a0307e5d044554c7be4` 原报告基线为 `e42f0246568b5a6c9f41e2cfb29ec549b3e14672`；M逐项核对的接续发布基线为 `6a1db538abceffd3059aa6eac48b9a4f81bf9095`。下表 `Audit-20261008/F-01` 至 `F-12` 只表示该报告原编号，不与前端审阅的同号条目混用。报告作者的clean状态不代表本机受保护dirty工作树。静态风险不是运行实例已被利用的证明；不读取生产凭据/数据库来复现。

这些修复加入原Owner完整目标，不建立新队列、第二权威或全局暂停。正常授权结果、拒绝反例和失败恢复共同构成验收；W6按共享路径预约集成，M接收完整修复包。

| 原审计编号 | 当前负责人/优先级 | 既有源码及直接执行边界 |
|---|---|---|
| F-01 | C6 / P0 | `app.py` 的 `/api/auth/config` 不得匿名返回可还原Basic凭据；协调F现有core client bootstrap，保留非敏感状态及正常受控访问，不新增账户墙。 |
| F-02 | C6 / P0 | `docker-compose.yml`、启动配置的默认网络暴露收敛到本机/明确受控边界；空认证不等于获准公网开放。实际公网部署、费用不在本次授权内。 |
| F-03 | C6 / P0 | `app.py` 的V4会话回退限定真实允许路由/方法；`GET /api/weibo/cookies`不可将登录当作秘密读取权限。写请求PermissionGate不能保护GET。 |
| F-04 | C5主责、C6整合 / P0 | `lumenis/shared/evidence/manual.py` 已注册旧读取入口须复用现有scoped Evidence owner，精确actor/domain/focus；保留必要兼容能力，不能只删旧入口或新增Evidence库。 |
| F-05 | C5主责、C6协调DB / P0 | 同一Evidence生命周期中修复先删文件后删记录、引用保护、原因/actor及补偿恢复；`cth_cases.py:58`、`entity_relations.py:109`确有FK引用。全局DATA_DELETE审批不替代记录范围/文件事务。只用隔离库验证失败。 |
| F-06 | C6 / P0 | `.dockerignore` 与 `Dockerfile` 排除`.env.*`、顶层`work/`及私有运行输入，精确保留必要模板；用无秘密哨兵验证构建上下文，不读取真实秘密。 |
| F-07 | C6 / P1 | `lumenis/auth/{service,security}.py` 修复`__access_key__`哨兵不计锁定的问题，复用既有安全记录，不创建虚构用户。`hmac.compare_digest`已存在。 |
| F-08 | C1主责、C6整合 / P1 | `canonical_data.py`构造/持久化及入站caller明确拒绝未知/矛盾product/domain；保留明确CTH兼容默认和BMP/ZBMP存储映射，不猜身份、不盲删默认。 |
| F-09 | C1主责、实际消费者配合 / P1 | `CanonicalRecord.engagement_total`全缺测不转0、部分和有覆盖语义、真实0保留；沿实际caller核对`ui_view_model.py`同名聚合及F缺值呈现。未发现直接生产caller不等于可以保留错误公共合同，也不证明所有页面受影响。 |
| F-10 | C6 / P0 | `scripts/backup_db.py`及现有HTTP/deployment caller统一Shared Database call-time路径、一致快照、验证和受控恢复；移除WAL raw-copy/未经确认覆盖行为，临时库演练。`deployment/backup.py`实际调用root `database.backup_database`，支持绝对路径，不能照报告误改成仅basename。 |
| F-11 | C6 / P1 | 现有Docker/Compose打包明确非root/WSGI及卷权限与启动诊断；属于准备可靠产品包，不是新增公网部署。 |
| F-12 | C6 / P1 | 现有Python部署依赖与镜像采用可复现的已验证解析/哈希和受控更新；不顺带全量升级，不宣称未核实CVE或已实测构建漂移。 |

账户密码整体重设计、Realtime实时语音、开发者模式等明确后置项维持原决定；现有认证/权限、Evidence完整性、备份恢复不是这些后置项。已批准本地Read Aloud不因Realtime后置而停工。各Owner继续既有完整结果，C2/C3/C4/F不因该报告另开重复审计。

报告中的WeChat旧断言已随`6a1db538`接受发布，复用受影响证据。该SHA的App Gate `37706227173`已成功；Product Gate `37706227134`在两项Agent Memory learning-loop断言失败，C6协调C2修复，不重置旧WeChat修复为未完成、不把新失败写成PASS。此处仅为2026-10-08观察，运行加载/完整用户验收仍按CURRENT独立记录。

## 2026-10-09 existing-owner AI-optional/source adoption delta

| Existing owner / source | Current bounded adoption | Exact remaining operation |
|---|---|---|
| M engineering tools; `.codex/local_workflow.py`, `scripts/local_development.ps1`, `.vscode/` | Deterministic Tasks, scoped static/build/format/recovery and real private receipts | Four-language local completion, syntax/type diagnostic recovery and real Dart definition navigation OBSERVED; editor path/PS host/Dart exclusions repaired; historical App test-source errors retained; tools do not close a product Job |
| SYSTEM Browser / C6 and F SYS-06; `ai_browser_runtime.py`, `ai_browser_api.py`, existing Core client/repository/screen | Exclusive short lease and frame/target/revision/viewport binding; manual navigate/history/reload/scroll | Server-authored Task/Run and source-use binding, safe remote authenticated Web, result SavedWork/Artifact save/reopen/recovery; no click/input implemented |
| Same Browser owner; `lumenis/system/browser/runtime/browser_use_adapter.py` | Disabled optional readiness boundary only; no provider/model fallback | Existing owned BaseChatModel/action bridge and enforced DNS/private-IP/redirect/WebSocket egress; currently no intelligent execution |
| Existing Agent/Task Runtime; `ai_task_engine.py`, `agent_runtime/agent_zero_gui_executor.py` | Disabled optional injected GUI executor contract; no parallel queue/database/runtime | Real isolated worker protocol/startup binder, exact Permission/Scope/Gateway/Artifact/Outcome readback and resource admission; no Docker/GUI runtime accepted |
| SYSTEM Gateway / C2; `lumenis/system/ai_gateway/core.py` | Explicitly authorized M cleanup: signatures/history retained, retired execution inert; owned functions unchanged | Owned model still NOT_BOUND; no new model/API/training authorization |
| C2 Task analysis; `_execute_analysis`, `_owned_ai_failure_code` in `ai_task_engine.py` | V2 source-only preparation confirms AI-optional label/failure-gate mismatch; no repair claim | On explicit Owner restoration, implement real deterministic/manual analysis result separately from typed source-aware AI enhancement; verify actual task/save/reopen/recovery, not fabricated rule-based text |
| C1/C3/C4/C5/C6/F existing contracts | Seven-domain normal-business no-AI requirement added to Architecture/Real Delivery/Experience | Each existing normal user chain must demonstrate permitted real inputs and results without inference; then separately measure AI gains; preserve all R/J/U scope |

Original research, user references, model candidates, source/Artifact history and
failure receipts remain protected. These rows are an existing-owner implementation
and dependency index, not a new plan, dispatch or acceptance authority. V2 provider
and dataset statements remain preparation inputs until exact current official
license/version/rights are verified; no external corpus or API was accessed here.
Evidence: `evidence/round-15/M-20261009-TOOLS-BROWSER-AI-OPTIONAL-DELIVERY.md`.

### A0/B0/C0 preparation source readback — 2026-10-09

Official provider/dataset sources and fixed foundation-license hash evidence are
in `evidence/round-15/M-20261009-TOOLS-BROWSER-AI-OPTIONAL-DELIVERY.md` section 8.
M preparation does not activate C2 or external routes. C5 owns original/source
metadata and rights intake; C2 owns the separate MODEL_TRAIN/model admission;
C3/C4/F consume the preserved deterministic/manual business contracts. Existing
training_review/training_cases require their exact reviewed source/rights/actor
Evidence; a dataset label, teacher name, this research or read-only count cannot
become training eligibility. Preserve unknown upstream/teacher/PII/benchmark and
dataset revision/hash as REVIEW_REQUIRED/HOLD. No new table/API/provider or
ordinary paused-owner production modification is granted by this record.
