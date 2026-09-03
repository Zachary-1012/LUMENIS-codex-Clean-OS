# ZBC × Zachary OS AI Naming / Terminology / Comment / Runtime Guardrails V1

Date: 2026-09-03（2026-09-04 按序境 Canonical 基线更新）
> 📌 最新治理基线：Canonical 命名以 [`00-GOVERNANCE/CANONICAL-NAMING-AND-TWIN-SYNC.md`](../00-GOVERNANCE/CANONICAL-NAMING-AND-TWIN-SYNC.md) 为唯一权威源。Zachary 仅保留为研发身份/仓库标识，不作为产品品牌。

Status: normative baseline
Scope: Z Brand Core, Zachary OS AI, DCC, all future modules and all Web/App/PWA/Mini Program surfaces.

## 0. Purpose

Keep the product semantically clean and operationally safe.

No new module may introduce uncontrolled terminology, duplicate names, long comments, duplicate UI systems, or unbounded collection/automation.

## 1. Canonical System Names

### Product family
- Canonical display name: **序境**（中文）/ **TBD**（英文，待最终命名确认）
- 研发身份标识（LEGACY，保留）：Zachary OS / ZOS
- Role: product family / umbrella system

### AI research system
- Canonical display name: **序境-智能**（中文）/ **TBD Intelligence**（英文，待确认）
- 研发身份标识（LEGACY，保留）：Zachary OS AI / ZOSAI
- Role: research, knowledge, AI, architecture, decisions and development intelligence
- Repository identifier（技术标识，保留）: Zachary-1012/Zachary-OS-AI

### Production business system
- Canonical display name: Z Brand Core
- Short form: ZBC
- Role: production monitoring, collection, events, insights, evidence, reports and runtime
- Repository: Zachary-1012/Z-Brand-Core

### Development execution console
- Canonical display name: Development Command Console
- Short form: DCC
- Role: controlled development execution, audit and task bridge
- DCC is not a second business product and must not duplicate ZBC business UI.

## 2. Architecture Naming

Use "Zachary OS" for the product family.
Use "Zachary OS AI" for the AI/research subsystem.
Use "Z Brand Core" for the production subsystem.
Use "DCC" only for the development execution console.

Use "Twin-Repo Architecture" for the repository relationship between ZOSAI and ZBC.
Do not use informal variants such as "双子库", "双子系统", "母库", "子库" in code identifiers or normative documentation unless explaining the architecture in Chinese prose.

## 3. Canonical Domain Terms

- Workspace: 工作空间
- Domain: 业务域
- Page: 页面
- Module: 模块
- Capability: 能力
- Component: 组件
- Action: 操作
- State: 状态
- Route: 路由
- Resource: 资源
- Evidence: 证据
- Event: 事件
- Insight: 洞察
- Asset: 资产
- Monitor: 监测
- Collector: 采集器
- Capture: 采集动作 / 捕获
- Normalizer: 标准化器
- Dedup: 去重
- Subject Rule: 主体规则
- Navigation Resolver: 导航解析器
- Internal Browser: 内置浏览器
- External Browser: 外部浏览器
- AI Context: AI 上下文
- Report: 报告
- Runtime: 运行时
- Health: 健康状态

## 4. Forbidden Terminology Drift

Do not create parallel names for the same concept.

Examples:
- Do not alternate between "舆情监控", "舆情监测", "情报监控" for the same capability. Use "监测" as the domain and specify the capability when needed.
- Do not alternate between "证据库", "素材库", "截图库" when the object is Evidence.
- Do not call an Event a Topic, Campaign or Case unless its schema actually represents that object.
- Do not call a Creator a KOS/KOL/KOC unless the role classification is known.
- Do not use "AI中心" as a generic page name. AI is a capability/context layer unless a dedicated AI workspace is explicitly approved.

## 5. Identifier Rules

Code identifiers use stable English semantic IDs.

Format:
- domain: snake_case
- capability: snake_case
- component: PascalCase
- event/state constants: UPPER_SNAKE_CASE
- route: kebab-case
- CSS token: --z-* prefix
- semantic icon alias: icon.<domain>.<action>

Business code must not depend on vendor-specific icon names or display labels.

## 6. Display Label Rules

One canonical Chinese label and one canonical English label per product concept.

UI labels must be:
- short
- operational
- consistent
- noun for navigation, verb for actions

Avoid marketing language inside operational controls.

## 7. Comment Standard

Comments are required where intent, safety boundary or non-obvious business invariants would otherwise be lost.

Comments must be short and durable.

Preferred:
- "平台链接默认进入内置浏览器。"
- "主体规则是生产判断真相。"
- "仅用户主动操作允许外部打开。"
- "失败后进入熔断，不自动重试。"

Avoid:
- long essays inside code
- comments that restate obvious syntax
- historical chat transcripts
- temporary debugging explanations
- speculative claims

One comment should normally explain one invariant.

## 8. Documentation Standard

Normative documents use this order:
1. Purpose
2. Scope
3. Definitions
4. Rules
5. Interfaces
6. States
7. Failure handling
8. Acceptance criteria

Use one authoritative document per contract. Other documents link to it rather than copying competing versions.

## 9. Hard Runtime Safety Rules

### Default state for a new module
NEW MODULE = SAFE / DRY-RUN / SHADOW

No new collector, automation or scheduled task may begin production collection merely because a UI module was enabled.

Activation requires:
- explicit capability registration
- platform scope
- collection mode
- rate/concurrency budget
- cooldown
- dedup policy
- subject-rule validation
- stop condition
- audit record

### Collection boundary
A UI action must never silently create an unbounded collector loop.

Every collection job has:
- job_id
- source
- scope
- requested_by
- start_at
- max_items or time budget
- concurrency limit
- request rate limit
- cooldown
- retry limit
- circuit breaker
- last_success_at
- stop reason

### Safety priority
Safety > existing production rules > data integrity > task completion > speed.

Never increase collection speed or concurrency merely to satisfy an execution-speed request.

### Automatic recovery
Recovery may restart a failed worker only within configured retry and cooldown limits.
Repeated failure opens the circuit and requires explicit review.

### Kill switch
Every collector and automation capability must have a visible and programmatic stop path.

STOP must prevent new work and allow in-flight work to terminate safely.

## 10. Platform Risk Rules

For monitored platforms, default automation mode is conservative.

The system must not:
- spawn uncontrolled parallel sessions
- repeatedly refresh or retry without a limit
- switch accounts automatically to evade a restriction
- rotate IPs automatically to evade a platform control
- continue collection after an explicit platform risk signal
- turn a newly added module into a new collector without registration

Platform risk signals enter a circuit breaker state.

## 11. Internal Browser Rules

Monitored-platform links -> Internal Browser by default.
External Browser is explicit only.

No domain module may directly call window.open for monitored-platform resources.

Internal Browser does not imply collection.

Browser != Collector != Evidence != AI.

## 12. Subject and Data Integrity Rules

Existing subject rules remain authoritative.

The following must not be bypassed by UI or new modules:
- SUBJECT_WORDS
- SUBJECT_EXCLUDE_WORDS
- SUBJECT_HARD_FILTER
- subject_hit()

Any change to subject logic requires a dedicated rule review and regression tests.

## 13. AI Rules

AI is an assistive capability unless a contract explicitly grants decision authority.

AI must not silently override deterministic safety or subject rules.

For important decisions retain, where applicable:
- model_version
- prompt_version
- input_reference
- output
- confidence
- final_result
- human_correction

## 14. UI Rules

New modules inherit the existing IA and Design System.

Reuse > extend > create.

A new top-level navigation item requires IA review.
A new component requires registry review.
A new icon requires semantic alias registration.
A new visualization requires a decision question.

No parallel CSS/JS system may be created for a new module without an explicit architecture decision.

## 15. Visualization Rules

Every visualization must define:
- decision question
- primary metric
- comparison baseline
- data timestamp
- interaction
- drill-down target
- loading state
- empty state
- error state
- stale state

Motion must communicate change or state. No continuous decorative animation.

## 16. Change Control

Any new module follows:

Request -> Capability Registry -> IA mapping -> Safety Review -> Interaction design -> Implementation -> Test -> Shadow/Dry-run -> Controlled activation -> Production

A module is not production-ready because its page renders.

## 17. CI / Static Audit Rules

Reject or flag:
- unregistered top-level routes
- direct monitored-platform window.open
- direct vendor icon imports in business code
- unbounded collector loops
- missing rate/concurrency limits
- missing stop conditions
- missing circuit breaker
- missing subject-rule validation
- duplicated navigation definitions
- duplicate component systems
- visualizations without explicit state handling
- comments containing obsolete or conflicting terminology

## 18. Definition of Done

The system is considered standardized only when:
- product names are canonical
- repository names and product names are distinguishable
- every domain term has one owner
- every capability has one owner
- every route has one owner
- comments are concise and durable
- safety rules are enforced in code, not only documentation
- new modules start in safe/shadow mode
- collection is bounded and stoppable
- platform risk signals trigger circuit breaking
- existing subject rules remain authoritative
- UI inherits the design system
- visual and behavioral regression tests protect the contract
