# LUMENIS Experience Constitution — CURRENT

> Status: **CANONICAL / SOLE EXPERIENCE DESIGN AUTHORITY**  
> Internal version: **3.2**
> Effective: 2026-09-21
> Stable path: `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md`

This file is the **only human-authored UI / UX / visual / interaction / motion / responsive / presentation design authority in the repository**.

No feature, domain, handoff, audit, research note, reference pack, screenshot pack, design-system document, component registry, motion specification, logo specification, page specification, AI prompt, historical artifact or code comment may create a competing presentation authority.

PDFs, taskbooks, reports, spreadsheets, screenshots, wireframes, Figma frames and
AI-generated visual proposals are non-authoritative working artifacts. They remain
`DESIGN_EXPLORATION` until their applicable screen/page decisions are deliberately
restated in this Constitution or in a reviewed detailed specification governed by it.
No artifact may promote itself or be copied directly into production UI.

Product/runtime/data truth still outranks presentation truth. This Constitution does not authorize changing backend facts, permissions, Evidence, canonical data or runtime semantics merely to make a screen easier to design.

## 0. Full-product scope

This Constitution governs every current and future user-visible or user-operable surface of 序境 / LUMENIS:

- account, authentication, onboarding and access states;
- global shell, navigation, Subject Context, Domain Lens, search, command and context switching;
- CTH / 序境·商业运营;
- BMP / 序境·品牌市场, including KOS / KOL / KOC / UGC workflows;
- Shared Capability, including Content & Creation, Evidence, Research, Evaluation and Learning;
- SYSTEM, including Collector, Runtime, Scheduler, AI Gateway, Database, Security, Permission, Settings, Recovery and Observability;
- AI / Agent workspaces and artifact flows;
- internal browser and evidence-acquisition surfaces;
- reports, exports, notifications, calendars and task surfaces;
- data visualization, tables, forms, editors, logs, status, empty/error/offline/blocked/loading states;
- Public Website, Web Workspace, Desktop App, tablet and Mobile Companion;
- Chinese / English / Korean presentation;
- brand identity in product UI, logo usage and launch/re-entry motion;
- any future surface added to this product.

Feature contracts may define **objects, fields, states, permissions, workflows and truth semantics**. They may not define a separate visual language or page-composition authority.

Historical browser presentation material was removed from `main`. Its templates/static implementations remain forbidden. The approved Public Website and Flutter Web Workspace are new surfaces under this same Constitution; retained contracts under `contracts/experience/` do not grant a second Experience design authority.

Historical design material is recoverable from Git history. It does not belong in the current main tree.

## 1. Authority order

For user-visible Experience work:

```text
Current verified Production Source / Runtime / Data / Permission / Evidence truth
> Production Acceptance and current product governance
> THIS CONSTITUTION
> current product/workflow contracts that define facts and states only
> implementation code / tokens / assets
> external research used temporarily during a task
```

There is no second design authority.

If code comments, old screenshots, component implementation or historical behavior conflict with this Constitution, they are implementation debt, not precedent.

## 2. Product identity

**LUMENIS is a Living Intelligence Space.**

It is not:

- a generic SaaS dashboard;
- an admin template;
- a BI dashboard;
- a CRM skin;
- a card-grid product;
- a Bento dashboard;
- an Apple clone;
- a Linear clone;
- a Notion clone;
- a ChatGPT clone;
- a Korean-brand website clone;
- a generic AI-gradient interface.

External products may be studied for interaction principles, accessibility, motion, hierarchy or engineering technique. They are never the target appearance.

A user should be able to hide the logo and still recognize LUMENIS from its information grammar, Evidence trace, realm behavior, state transitions and workflow structure.

## 3. Philosophy translated into interaction

Brand philosophy: **芥子纳须弥**.

Experience interpretation:

> A small, real and verifiable point can reveal a larger structure; every larger conclusion must still be able to return to the original evidence.

Canonical business chain:

```text
Source → Evidence → Event → Case → Insight → Decision → Action
→ Outcome → Evaluation → Learning Asset
```

Canonical user question order:

```text
What changed?
→ Why does it matter?
→ What proves it?
→ What can I do?
→ What happened after the action?
```

Primary interaction verbs:

```text
Observe · Trace · Open · Compare · Shift · Decide · Act · Evaluate · Return
```

**Trace / Return** is a product signature. Important conclusions expose a natural route back to Evidence.

Metrics support understanding. Metrics are not automatically the page.

## 4. Native spatial grammar

LUMENIS uses:

- **Point**: one real object, fact, signal or Evidence item;
- **Axis**: time, causality, sequence or stable contextual relationship;
- **Trace**: the path from conclusion back to source truth;
- **Field**: an active working context, not a decorative container;
- **Strata**: layers of context, analysis, Evidence and action;
- **Boundary**: a semantic separation such as permission, source, state or workflow stage.

A rectangle is not automatically a Card. Border, radius, shadow and blur must express a real boundary or spatial role.

Default layout behavior must never be “put every object in a rounded rectangle”.

Whitespace is structural. Density is allowed when a task needs it, but density comes from relationships and information, not tile multiplication.

## 5. Typography

Semantic roles:

- modern UI sans: primary interface, controls, body and navigation;
- editorial serif: selective insight, narrative conclusion or interpretive emphasis;
- monospace: Evidence IDs, runtime identifiers, timestamps, traces and technical state;
- custom/handwritten wordmark: brand asset only, never ordinary UI copy.

Hierarchy comes from meaning, scale, rhythm and placement before decoration.

## 6. Color, light and material

Color follows information.

Use neutral fields for truth-bearing content. Semantic colors communicate real state: success, warning, risk, blocked, stale, offline, selected or active.

A restrained luminous accent may identify active context, primary action, selected Evidence or current task. It must not become a decorative blue-purple AI wash.

Material roles:

- **Truth Surface**: Evidence, reports, long text, tables, forms, runtime facts. Stable and predominantly opaque.
- **Structure Surface**: context, toolbar, selector, filter, rail, drawer, popover. Subtle separation and shallow depth.
- **Optical Surface**: small, selective, optional interaction emphasis.

Fallback:

```text
OPTICAL → SOFT DEPTH → OPAQUE
```

No business function depends on blur, WebGL, GPU effects or glass. Glass is never the product theme.

## 7. Composition: reusable primitives, semantic screens

Reuse typography, spacing, icons, Evidence rendering, controls, input behavior, table mechanics, state semantics, accessibility, motion tokens and material roles.

Do **not** reuse a page skeleton merely because reuse is convenient.

Forbidden default ontology:

```text
Header → 4 KPI cards → chart → cards → table
```

Generic implementation sections such as `kpis`, `cards`, `split`, `chart` and `table` may remain during migration, but they are not a design language and may not dictate unrelated workflows.

Workflow-specific composition is expected when the user problem requires it.

## 8. Realm dialects

The realms share one grammar but must not be the same page with different labels or accent colors.

### CTH / Commerce Operations

Spatial idea: **time, event, place and operational change**.

```text
now_stream · event_flow · evidence_trace · case_evolution
decision_path · outcome_loop
```

CTH should feel temporal and causal.

### BMP / Brand & Market

Spatial idea: **network, brand, creator, content and propagation**.

```text
market_network · creator_constellation · content_cluster
market_movement · evidence_trace · relationship_path
```

BMP reveals relationships and movement, not another KPI overview.

KOS/KOL/KOC/UGC contracts define identity, ownership, states and fields. Their presentation still follows this Constitution.

### Shared Capability

Spatial idea: **transformation from brief/Evidence into artifact and learning**.

```text
creation_flow · brief_to_artifact · artifact_flow
evaluation_loop · learning_trace · research_path
```

Shared behaves like a creation/research workspace, not a reporting dashboard.

### SYSTEM

Spatial idea: **infrastructure truth made understandable**.

```text
runtime_topology · health_trace · collector_flow
permission_boundary · recovery_path · dependency_map
```

SYSTEM may be dense and technical. It exposes machine relationships rather than imitating an admin console.

## 9. Account, authentication and global context

The LUMENIS product account is a post-internal-beta capability. During the current three deliveries, the App opens without a global product-account wall; a protected operation may still show a local, truthful Permission boundary enforced by Product Core. Media-platform Cookie/session/browser authorization is a separate SYSTEM connector state and must not become a LUMENIS login flow.

When post-beta authentication/access surfaces are implemented, they are calm, direct and explicit about identity, permission, blocked state and recovery. They are not marketing landing pages.

Global Subject Context:

```text
Selected Subject → Domain Lens → Scope / Permission
→ Function / Metric → ViewModel → Experience / Report / Export
```

CTH and BMP may interpret the Subject differently but must not create competing subject-context systems.

Navigation follows the current product/domain ownership in `LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`, then the owning module and page. A route's existence alone does not make a destination top-level; keep utility workflows within their owning domain/module or the deliberate SYSTEM context. Navigation reveals current context and the next meaningful move rather than listing backend routes. No fixed rail/dock/sidebar shape is sacred.

## 10. AI / Agent experience

AI is **artifact-first**, not chat-first.

```text
Intent → Task → Runtime → Evidence → Artifact
→ Decision → Action → Evaluation
```

AI Home answers what can be understood or created.
AI Working answers what task is running, with what Evidence/state.
AI Result answers what artifact exists, what supports it and what can happen next.

Conversation history may exist, but chat bubbles do not dominate every task.

No fake thinking, fake progress, fake tool usage, fake confidence or fake success.

## 11. Internal browser / acquisition

The internal browser is an Evidence/acquisition workspace, not a decorative browser demo.

It makes source, identity/session boundary, collection state, provenance, risk and capture result understandable.

It must never imply that a source is authorized, captured, logged in or healthy unless runtime truth proves it.

Acquisition converges toward Evidence/Canonical truth, not a parallel browser-data silo.

## 12. Evidence presentation

Evidence is first-class.

When available, expose source/provider, source identity/URL, capture time, relevant observable fact, freshness, lineage, confidence/rule basis and relationship to Event/Case/Insight/Decision.

Evidence must not be hidden behind generic “Details” when it supports an important conclusion.

Large conclusion → Trace → Evidence → Return without losing context.

## 13. Event / Case / Insight / Decision / Action

These are not equivalent CRUD records.

- **Event**: change over time, participants, propagation and lifecycle.
- **Case**: a working context accumulating Evidence, decisions and actions.
- **Insight**: a supported interpretation with explicit basis.
- **Decision**: a committed choice with owner/status where applicable.
- **Action**: an executable or proposed step with permission/effect boundary.
- **Outcome/Evaluation**: observed result and learning, not success decoration.

UI grammar reflects these semantic differences.

## 14. Data visualization

A visualization answers a question:

```text
Question → metric / relationship → visual form
→ interpretation → Evidence / lineage → possible action
```

Forbidden: decorative charts, rainbow palettes without meaning, “dashboard variety” donuts, duplicated numbers with no additional meaning, or values that cannot trace to canonical data.

Tables are tools for scanning/comparison/audit, not the default answer to every object.

## 15. Reports / exports

Reports are not dashboard screenshots.

Typical narrative:

```text
Conclusion → context → drivers → Evidence → comparison/trend
→ implication → action → evaluation state
```

Interactive UI, export and report derive from the same truth and Evidence lineage.

## 16. Content & Creation

```text
Brief → Context → Research/Evidence → Draft → Artifact
→ Review → Approval → Publish/Export boundary → Evaluation → Learning
```

The artifact is the center of work. Generated content is not published merely because a draft exists.

## 17. Forms / settings / configuration

Configuration makes scope, current value, consequence, validation and effect boundary explicit.

Avoid endless generic settings cards.

High-risk configuration shows permission, pending approval, irreversible effect and recovery where relevant.

## 18. State language

Never collapse:

```text
0 · NULL · UNKNOWN · NOT_AVAILABLE · NOT_COLLECTED · STALE
OFFLINE · ERROR · BLOCKED · PENDING · SCHEDULED · READY
RUNNING · COMPLETED
```

Missing data is not beautified into healthy state.

## 19. Motion

Motion explains relationship/state.

```text
ENTER · EXIT · TRACE · OPEN · SELECT · SHIFT · MORPH
EXPAND · COLLAPSE · DRILL · RETURN · PROGRESS
COMPLETE · WARNING · ERROR · RECOVER
```

Every meaningful animation has Before State → real Trigger → continuity principle → After State.

No state change usually means no animation.

Reduced-motion is mandatory. Brand launch/re-entry never blocks real readiness.

## 20. Responsive recomposition

Validation widths:

```text
1920 / 1440 / 1280 / 1024 / 768 / 430 / 390 / 360
```

Responsive means recomposition, not desktop scaling.

Preserve semantic continuity while changing placement and interaction form.

No screen is accepted because it only works at one zoom or width.

## 21. Accessibility

Keyboard, focus visibility, semantic labels, contrast, touch target, screen-reader structure and reduced motion are part of design.

Hierarchy must survive without color alone.

## 22. Trilingual copy

```text
Machine ID → Semantic Copy Key → Display Value
```

Real Subject names, Brand names, Event titles, Evidence and business records remain data, not locale copy.

Chinese / English / Korean preserve meaning and hierarchy rather than identical string length.

## 23. Brand identity

Product assets may live in implementation directories, but there is no independent logo/design specification outside this Constitution.

Identity should feel precise, restrained, spatial, evidence-led and contemporary without AI-template decoration.

Existing logo/icon assets are assets, not authorities. Future brand changes are decided here first, then implemented.

## 24. Anti-template hard failures

Unless a current product requirement proves a narrow exception, fail review when:

- a Golden Page has a top-level generic `kpis` section;
- a Golden Page uses generic `cards` as its main composition;
- unrelated realms share the same top-level page signature;
- a home/overview opens with a four-column KPI wall;
- CTH can become BMP by changing only labels/data/accent;
- Event/Evidence/Case/Insight become equivalent CRUD objects;
- AI result defaults to chat bubbles instead of Artifact;
- glass becomes the global theme;
- another brand name is used as target style;
- CSS decoration changes but semantic hierarchy does not;
- many pages are declared complete because one generic schema renders them;
- a parallel design/handoff/reference document is committed.

## 25. Golden Pages

1. **AI-01**: `intent_space + evidence_trace + artifact_flow`
2. **CTH-01**: `now_stream + event_flow + evidence_trace`
3. **BMP-01**: `market_network + evidence_trace`
4. **SH-01**: `creation_flow + artifact_flow`
5. **SYS-01**: `runtime_topology + health_trace`

All five have distinct top-level semantic signatures before broad migration.

Remaining screens migrate by workflow family, not bulk skinning.

## 26. Codex / Agent execution

Before Experience implementation:

1. resolve current `origin/main`;
2. read root `AGENTS.md`;
3. read **this file**;
4. read retained `contracts/experience/` assets only as App binding contracts;
5. inspect current Source / ViewModel / State / Action / Permission / Evidence / Runtime owners;
6. state the user problem and semantic composition before editing CSS.

Implementation order:

```text
User problem → semantic objects/relationships → composition
→ shared primitives → realm behavior → real binding → states
→ responsive → motion/material → acceptance
```

Forbidden order:

```text
choose fashionable style → add cards → add glass → insert data → call it LUMENIS
```

For non-trivial work, the plan names active workflow, truth sources, semantic primitives, generic pattern being retired/avoided and acceptance checks.

## 27. Repository exclusivity

The current main tree must not contain historical UI/UX/visual design authorities, design research packs, Apple/UI reference packs, old visual baselines, old design-system documents, old frontend design handoffs or old page-design specifications.

Those remain recoverable from Git history.

If research is needed:

```text
research externally → extract principle → decide
→ update THIS Constitution only if canonical → implement
```

Do not commit a second design bible.

Blocking checks:

```text
python scripts/audit_tools/verify_experience_authority_exclusive.py
python scripts/audit_tools/verify_experience_anti_template.py --strict
python scripts/audit_tools/verify_experience_screen_blueprints.py
```

## 28. Acceptance

Experience completion is not “page renders”.

```text
Semantic question → ViewModel truth → composition → Evidence trace
→ action → honest state/error → responsive recomposition
→ screenshot regression → ARIA/structure regression → runtime/E2E
```

New screenshot baselines come from **V3-compliant Golden Pages**, never inherited legacy baselines.

Snapshot regeneration is not acceptance by itself.

Anti-template thresholds are ratchet-only.

## 29. Current state

This sole authority does not claim current implementation is already compliant.

Current honest state:

```text
SOLE AUTHORITY ACTIVE
LEGACY DESIGN AUTHORITIES REMOVED FROM MAIN TREE
IMPLEMENTATION MIGRATION REQUIRED
```

Current production CSS/JS/assets may temporarily contain legacy implementation structure until migrated. They are implementation, not design precedent.

## 30. Canonical multi-surface architecture and feature ownership

The product is delivered through an SEO-capable Public Website plus one Flutter implementation for Web Workspace, Desktop App and Mobile Companion. All surfaces share business semantics and contracts while adapting composition and input to browser, Windows, macOS, Linux, Android and iOS. The approved roles and capability boundary are recorded in `LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md`; this Constitution remains the sole design authority.

```text
Flutter composition root
├─ core        transport, typed contract decoding, auth/session, errors, cancellation
├─ account     post-beta product identity/sign-in/recovery; absent as a pre-beta global gate
├─ cth         SubjectContext, commercial operations, events, cases, decisions/actions
├─ bmp         BrandFocus, market signals, creators, campaigns, propagation/evaluation
├─ shared      Evidence, research, creation, evaluation, learning, reports/export
├─ system      permission-gated runtime, collection, security, settings, recovery
└─ navigation  routes, deep links, restored work context
```

The folder map is an implementation boundary, not a second truth owner. Surface state may hold presentation state and a restorable navigation context; it must not become Canonical Data, Evidence, Metric, Permission, Runtime or business-state truth. The Public Website may own public content presentation and acquisition forms only. Agent Groups remain the cross-product execution/collaboration layer and are not a product domain.

Before implementing each screen or action, complete this binding:

```text
ScreenId / ActionId
→ current source and canonical owner
→ API request/response and typed ViewModel
→ actor, target, scope and Permission decision
→ Evidence lineage and write/effect boundary
→ loading / empty / UNKNOWN / stale / blocked / failure / success state
→ action result, evaluation and trace-back behavior
→ widget / integration / runtime acceptance
```

Use `contracts/experience/` as a binding contract, never as proof that an endpoint or action already exists. `UNKNOWN`, `NOT_AVAILABLE`, `NOT_COLLECTED`, `STALE`, `BLOCKED` and `ERROR` must stay distinct. A fixture, optimistic UI state or AI answer cannot fill a backend gap or imply a successful production action.

### Domain invariants

- **CTH** starts from an authorized Subject. Selecting or changing a Subject changes working context and filters only; it never rewrites Evidence, Canonical Data, original ownership or confirmed outcomes.
- **BMP** starts from a Brand/Market focus. The selected brand is the primary focus while competitors, creators, content, consumers and market movement remain visible relationships. BMP is not a CTH subject page with different labels.
- **Shared Capability** preserves `originDomain`, source object and lineage when a capability is opened from CTH or BMP; it does not take over their business ownership.
- **SYSTEM** actions are effect- and permission-gated by the Core. Hiding or disabling a control on any surface is not authorization.

## 31. Cross-surface composition

Responsive acceptance uses the widths in §20 and verifies a semantic recomposition, not a scaled desktop screenshot. Public Website and Web Workspace are distinct products surfaces: the former explains/acquires, while the latter operates real workflows.

| Form factor | Composition contract |
| --- | --- |
| Public Website | SEO-readable product narrative, capability proof, truthful demo/case material, trial/contact/help and a clear login/workspace entry. It cannot resemble or execute the operational workspace. |
| Web Workspace | Browser-first primary operating surface with URL/deep-link semantics, keyboard/pointer access and responsive evidence/workflow composition. Desktop-only capability exposes a truthful handoff/state, never simulated success. |
| Wide desktop (≥1280 logical px) | Persistent product/domain navigation, a compact active-context bar, workflow-specific work surface, and an optional Evidence/inspector region. The inspector may resize but cannot obscure the primary task. |
| Compact desktop/tablet (768–1279 px) | Collapsible navigation rail, one primary work surface, and Evidence/inspector as a reversible panel. Keep keyboard navigation and selected context visible. |
| Mobile Companion / phone (≤767 px) | Notifications, events, AI results, approvals, task state, report reading and bounded quick action. Keep the authorized Subject or Brand focus visible and preserve source context on return. |

The breakpoints guide composition; measured content and platform window size determine the final layout. Desktop favors parallel comparison and precise pointer/keyboard work. Mobile favors a single active task, touch-sized actions and context that remains visible without consuming the work area. Platform-specific navigation must not create different business meaning.

## 32. LUMENIS interaction signature and motion contract

LUMENIS’s distinctive interface is the **Trace / Return** relationship expressed through its existing spatial grammar: Point → Axis → Trace → Field → Strata → Boundary. A conclusion can reveal its evidence lineage along the relevant time, relationship, creation or runtime axis; Return restores the exact prior focus, filters, selection and scroll position. This behavior is implemented in each domain’s own composition, not as a generic detail drawer repeated everywhere.

Every non-trivial motion/action specification records:

```text
user intent → trigger/input → before state → visible change
→ business/data/Evidence cause → cancel/reverse/return
→ keyboard and touch equivalent → reduced-motion equivalent
→ accessibility announcement → device/frame-budget acceptance
```

Motion may clarify causality, selection, progress, successful persistence, blocked effects or recovery. It must not delay readiness, hide a data change, imply an unrecorded write, intercept ordinary scrolling, or be required for meaning. Prefer direct manipulation with bounded, interruptible transitions. Test actual input and resulting state; a screenshot alone is not motion acceptance.

## 33. Inspiration and originality boundary

External creative work, including Korean product-app craft and `motion-web`, may inform general principles such as task clarity, progressive disclosure, crisp response, restrained transitions, accessibility and measurable interaction quality. Product semantics, information architecture, composition and visual identity remain LUMENIS-owned and are derived from real domain objects and workflows.

The approved principle mapping is narrow: Apple informs restraint, content priority, one clear primary action and an uncluttered search entry when an existing workflow is search-led; ChatGPT informs a single intent entry and progressive disclosure of existing complexity; TRAE informs visible **task → execution → result** feedback for existing workflows. These references do not authorize new Chat, Work, Project, recent-content, search, task-platform or account capabilities, and they do not replace any current business function or backend owner.

For Korean product-app craft, study public product-engineering documentation such as the [Toss Design System component guide](https://developers-apps-in-toss.toss.im/landing-page/landing-page-en/design/components) for consistency, clear component guidance and task-focused implementation. Its UI Kit terms restrict use of Toss materials to the Apps in Toss service, so LUMENIS does not adopt the UI Kit, components, assets or visual patterns. Extract only general, non-visual principles, then test those against LUMENIS workflows.

Do not copy another product's assets, source code, signature layout, visual identity, interaction sequence or implementation recipe. The supplied [motion-web repository](https://github.com/Zachary-1012/motion-web) is a fork of `feitangyuan/motion-web`; its [LICENSE](https://github.com/Zachary-1012/motion-web/blob/main/LICENSE) identifies CC BY-NC 4.0 and expressly restricts commercial integration of its Skill, prompts, cases and derived workflows. No code, case, asset, parameter set or derivative workflow from it is admitted into this commercial product. Inspiration is not a runtime dependency or a competing design authority.

## 34. Ordered cross-surface delivery and acceptance

This section supports the approved 15-round dependency program in `LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md`. Cross-surface foundations belong to ROUND 08; workflow surfaces are accepted in ROUND 09–14; complete cross-surface internal-beta evidence belongs to ROUND 15. Do not implement a future surface or provider before its owner, contract and entry gate are approved.

Do not build all screens from a generic template. Work in this order, with a capability-parity gate between phases:

1. **Bind truth:** classify each Experience screen/action by owner, endpoint, ViewModel fields, permission, Evidence, read/write effect and known gaps. Resolve unknown owners from source before creating a new API.
2. **Make the shell real:** implement Product Core connectivity, current context, routing, error/offline/retry states, keyboard/focus behavior and restorable navigation. The LUMENIS product account is deferred until after internal beta and must not block pre-beta browsing or existing product use. Keep server Permission/effect fences intact, and keep media Cookie/session authorization entirely inside the SYSTEM collector/browser chain. Keep CTH SubjectContext separate from BMP BrandFocus.
3. **Prove the five Golden Pages:** AI-01, CTH-01, BMP-01, SH-01 and SYS-01 each use their semantic signature in §25 and bind to live owners. Do not mark a fixture-backed page complete.
4. **Migrate by workflow family:** bind remaining contract screens only after their source/API/Permission/Evidence owner is verified. Preserve established behavior before removing any migrated surface.
5. **Reach surface parity:** run applicable Web Workspace, Desktop and Mobile interaction, accessibility, responsive, error/recovery and screenshot checks at §20 widths. Verify Public Website acquisition/workspace-entry separately; do not require identical layouts.
6. **Release evidence:** require widget and repository tests, affected Python/API integration tests, critical runtime/E2E, clean-clone acceptance and current-main CI evidence. Record unavailable infrastructure as `UNVERIFIED`, never as PASS.

For each domain, acceptance must include its invariant in §30, real ViewModel truth, permission response, Evidence trace and return, honest missing/error states, keyboard/touch operation, reduced motion, persistence or explicit non-persistence, and the result after a real action. A screen is complete only when its user task completes end to end.

## 35. Product module map and end-to-end delivery standard

The 44 screen IDs and 54 binding records (`BACKEND-GAP-001..054`) define the scope to be designed and verified. The machine-readable binding registry constrains only data/API/actor/permission/evidence truth; it is not a layout system. Legacy `sectionTypes`, card lists and generic ViewModel shapes are inventory clues only. They must not dictate layout, flow or component placement. No shared renderer may turn these 44 IDs into one template with substituted titles and fields. Every screen below has a distinct question, visual composition and primary interaction. Existing ledgers may be used as evidence inputs, but their owner/status labels do not override current source or establish that an API exists. Any conflict stays visible as `CONFLICT` until source inspection resolves it. `UNKNOWN` is an explicit delivery gap.

### Product capability map

| Capability family | Product owner and scope | Required product outcome | Truth boundary |
| --- | --- | --- | --- |
| Runtime and work context | SYSTEM runtime/permission; future product account after internal beta | Open the pre-beta product without an account wall, restore safe local work context, and expose a truthful local restriction only where a protected operation requires it | UI context is not proof of authorization; every protected server operation still enforces Permission/effect boundaries; media platform Cookie/session state is separate |
| Commercial operations and subject intelligence | CTH | Start from a Subject; read its commercial signals, event stream, cases, risk, decisions, actions, schedules and reports; trace each decision to source and follow-up outcome | Subject ownership, CTH metrics and confirmed outcomes remain CTH-owned |
| Brand and market intelligence | BMP | Start from Brand/Market focus; connect category movement, competitors, audience, creators, content, channels, campaigns, brand risk and evaluation | Brand focus and BMP metrics remain BMP-owned; competitor and creator data are relationships, not interchangeable subjects |
| Analytics and decision support | Shared analytical capability with CTH/BMP-owned metric definitions | Cohort, compare, segment, trend, attribute, detect anomaly, explain change and export an auditable view | Shared computation keeps source domain, definition/version, scope, window, freshness, confidence and lineage; it cannot relabel a metric or combine incompatible scopes silently |
| Business operations | CTH for commercial cases/actions; BMP for brand campaigns/marketing workflows | Convert a signal into an owned decision, accountable task, due date, status, approval and measurable follow-up | Each action is written by its source-domain owner; Shared provides orchestration/trace, not a replacement workflow truth |
| Brand marketing and growth | BMP | Plan positioning, audience, campaign, creator/channel mix, content variants, launch calendar, budget/goal and evaluation | Proposed, approved, scheduled, published and measured are separate states; no simulated metric is presented as actual reach or ROI |
| Media creation and propagation | Shared creation capability, with BMP or CTH owning business intent | Create/version assets, attach rights and provenance, adapt channel variants, route approval, prepare/publish through authorized adapters, capture delivery result and return to source campaign/subject | Asset lineage and source intent persist end-to-end; a queued/published adapter result is not proof of business impact |
| Media platforms and connectors | SYSTEM integration adapters; product context remains CTH/BMP | Inspect existing Cookie/session connector health, quota, capability, schema mapping, sync status and recoverable errors; use the current authorized operational import/replacement path when recovery is needed | No new platform account/login flow is inferred; connector state is operational truth only; platform metrics retain source/time/definition and map into the originating product scope |
| AI and Agent Groups | Shared capability operating within the caller's CTH/BMP context | Research, draft, explain, delegate or execute an explicitly permitted action with cited sources and reviewable trace | Model output is a proposal until independently grounded, authorized and, where needed, explicitly approved |
| Evidence, evaluation, learning and reporting | Shared Capability | Preserve the evidence chain; evaluate source-backed outcomes; learn from reviewed feedback; produce reproducible reports/exports | Preserve `originDomain`, source IDs, actor, timestamp, policy/model/version and transformation lineage |
| Runtime, security, collection and recovery | SYSTEM | Show health, collection/platform state, permissions, configuration, audit, backups and recovery actions | SYSTEM is infrastructure truth only; it must not acquire CTH/BMP business objects or metrics |

### Required interaction patterns by form factor

- **Web Workspace:** primary browser entry for real workflows; optimize for URL/deep-link restoration, keyboard/pointer work and responsive evidence inspection over the same canonical contracts.
- **Desktop:** optimize for dense, multi-source decisions and approved local capability: context remains pinned; comparisons can be viewed side by side; timelines, tables and graph relationships support keyboard sorting/filtering; an inspector exposes lineage without obscuring the task; bulk actions preview impact and require the owning product's authorization.
- **Mobile Companion:** optimize for timely review and a single owned action: keep Subject or Brand focus visible; provide a compact signal feed, prioritized alerts and a one-task action sheet; allow capture/review/approval and source trace; restore the exact originating campaign, case, filters and scroll position on Return. Dense analysis can be summarized, but its definition, uncertainty and source remain inspectable.
- **Public Website:** optimize product comprehension, credible capability demonstration and low-friction trial/contact/workspace entry. It never presents marketing fixtures as live production results.
- **Shared UI:** loading, no data, not collected, stale, blocked, permission denied, offline, partial result and failure have distinct copy and recovery actions. Charts, AI summaries and status badges always disclose the selected scope and time window.
- **Signature behavior:** Trace / Return follows a signal or creative through source → interpretation → decision → authorized action → observed result, then returns to the same working context. This causal continuity, coupled with the Point → Axis → Trace → Field → Strata → Boundary spatial grammar, is the LUMENIS-owned interaction signature. Visual novelty must follow this workflow and must never disguise missing data or authorization.

### Executable design and accessibility thresholds

- **Tokens:** define semantic foreground/background/status colors, type roles, spacing, density, focus, elevation and motion as named tokens before composing screens. Color expresses meaning and never carries status alone. Text and interactive states meet WCAG 2.2 AA contrast; standard text contrast is at least 4.5:1, large text at least 3:1, and keyboard focus is visible against adjacent colors.
- **Input and size:** interactive touch targets are at least 44 × 44 logical px where the platform permits. Keyboard-only users can reach, operate and leave each control in logical order; pointer, touch and keyboard actions produce the same authorized business result.
- **Text and localization:** the production shell supports Chinese and English; Korean remains a planned/verified locale before claiming Korean support. Test short/long translations, mixed CJK/Latin numerals, wrapping, font scaling to 200%, right-sized desktop windows and screen reader names. Never bake translated labels into metric/API identifiers.
- **Responsive navigation:** desktop uses a persistent or collapsible domain rail plus restored work context; tablet uses a compact rail and reversible detail panel; phone uses one primary task surface with a clear back path. Test portrait and landscape, desktop narrow-window transitions, keyboard shortcuts and hardware back. Return restores selected Subject/Brand, filters, tab, selection, scroll and originating route.
- **Motion:** establish named duration/easing tokens and use motion only where it explains causality, progress or a reversible transition. Every transition is interruptible and has a reduced-motion path; reduced motion removes spatial travel/parallax and keeps state-change feedback immediate. Motion must not be the only status signal.
- **Performance:** target 60 fps on supported reference devices and keep p95 frame work within 16.7 ms during defined Golden Page interactions. Defer non-visible work, virtualize long lists and provide a no-motion/low-cost rendering fallback on constrained devices. Record the reference device, build mode and measured interaction; a simulator screenshot is not a performance result.
- **Assistive technology:** verify WCAG 2.2 AA flows for VoiceOver/TalkBack or the target desktop screen reader, semantic headings/landmarks, chart text equivalents, dynamic status announcements, focus restoration and error recovery. A critical task must remain operable at 200% text scaling without clipping or loss of controls.

These are acceptance thresholds for implementation, not claims that the current bootstrap already meets them.

### Roles, top tasks and release scenarios

Prioritize work by real user task and authorized role, not by the size of a screen inventory:

| Role / context | Top task | End-to-end scenario to prove |
| --- | --- | --- |
| Commercial operator (CTH) | Detect a subject-level change and close the response loop | Select authorized Subject → inspect current and historical signals → open source evidence → create/assign a case or decision → confirm authorized result → revisit measured outcome → Return to the same Subject context |
| Brand / growth operator (BMP) | Move from market signal to measured campaign | Select Brand/Market focus → compare category/competitor/creator signals → inspect source and freshness → plan creative/channel/campaign → obtain required approval → record delivery result → evaluate against a defined baseline → Return to the campaign |
| Analyst (CTH or BMP) | Explain a KPI change without mixing scopes | Select product-owned metric → inspect definition/window/denominator → segment or compare compatible cohorts → distinguish actual, estimated and unavailable data → export with lineage → reopen the same view |
| Media / content operator | Adapt an approved asset to an authorized platform | Open asset from owning campaign/Subject → review rights and provenance → create channel variant → preview and approve → submit through the platform adapter → inspect real adapter status/error → trace back to campaign and evidence |
| SYSTEM operator | Diagnose and safely recover an integration | Inspect connector/auth/quota/runtime health → distinguish platform outage from business-data gap → inspect audit trail → request permission/approval where required → apply bounded recovery → verify operational result without changing CTH/BMP business truth |
| Executive / reviewer | Trust a summary and inspect its basis | Open role-authorized cross-product summary → see owner, metric definition, time window and freshness → open supporting Evidence → distinguish confirmed outcome from model suggestion → return without changing source state |

Korean product-app research is a research method, not a visual dependency: record a named public flow and source, extract only the underlying principle, map it to a LUMENIS task, then test that principle with LUMENIS objects and users. No borrowed palette, signature composition, interaction sequence or source implementation becomes a LUMENIS standard.

Initial public references reviewed 2026-09-20:

| Source flow | Principle to study | LUMENIS question and boundary |
|---|---|---|
| [Toss Shopping discovery](https://toss.im/en-us/service/shopping) | Reduce search effort and connect discovery to a useful next step. | In BMP, can a market or brand insight open a low-friction, evidence-backed next step? Show source, freshness and why it is relevant; do not add opaque personalization or copy Toss's recommendation/checkout sequence. |
| [KakaoTalk Channel business home and updates](https://business.kakao.com/info/kakaotalkchannel/) | Keep business identity, updates and response paths connected to the audience relationship. | For BMP/Shared, investigate whether verified campaign/content owners can trace approved publication to real platform response and evaluation. This is a product-contract question, not a promise that publishing, chat or analytics already works; never clone Kakao's home, feed or chat composition. |
| [Toss Design System component guidance](https://developers-apps-in-toss.toss.im/landing-page/landing-page-en/design/components) | Make component purpose and usage guidance explicit for consistent implementation. | Apply the documentation discipline to LUMENIS-owned components and states only. The Toss UI Kit materials are limited to Apps in Toss; do not reuse its components, assets, tokens or visual patterns. |

The supplied [`motion-web` repository](https://github.com/Zachary-1012/motion-web) is a creative-web research reference only. Its [CC BY-NC 4.0 license](https://github.com/Zachary-1012/motion-web/blob/main/LICENSE) bars commercial integration of its Skill, prompts, cases and derivative workflows. No code, case, asset, parameter set, verification recipe or derivative workflow from it is admitted into LUMENIS; define motion and acceptance independently from verified LUMENIS state transitions and user tasks.

### Implementation sequence and release gates

1. **Freeze product semantics:** validate CTH Subject-first, BMP Brand/Market-first, Shared lineage and SYSTEM infrastructure boundaries against the current owner map. Reject a screen proposal that merges or changes these starts.
2. **Resolve all 54 bindings:** one registry row per `BACKEND-GAP-001..054`; inspect code and live contracts, assign the canonical owner, record exact callable/route and typed fields, actor/scope, permission operation, evidence fields, side effects, truth status and test. Unknown remains blocked with an explicit next action.
3. **Implement foundations:** typed API clients, session and context boundaries, deep links, cancellation/retry, offline/error handling, accessibility, event logging without sensitive content, state restoration and explicit surface capability state. Establish browser/desktop keyboard and mobile touch baselines before screens.
4. **Deliver workflow slices:** for each capability, finish read → explain → decide → authorize → act → observe → Trace/Return before moving on. Prioritize AI-01, CTH-01, BMP-01, SH-01 and SYS-01 as distinct Golden Pages, then migrate by shared interaction/workflow family while preserving parity.
5. **Optimize analytical and operational modules:** measure decision completion time, signal-to-action time, evidence coverage, freshness, false-positive rate, campaign delivery/impact attribution quality, workflow SLA and recovery success. Each metric has a canonical definition, owner, denominator and freshness; do not optimize engagement at the cost of trust or business outcomes.
6. **Prove cross-surface parity:** exercise applicable Web Workspace, Desktop, tablet and Mobile Companion paths with real endpoints; test pointer, keyboard, touch, screen reader, reduced motion, localization, slow/offline connection, empty/stale/partial/error states, permission denial, persistence and return. Verify Public Website entry/demo truth separately. Compare screenshots only after semantic and functional checks pass.
7. **Release by evidence:** attach the binding ID and test/runtime evidence to every completed capability. A package import, generic renderer, fixture, screenshot or CI pass alone does not make a user workflow complete. Mark unavailable platform accounts, device coverage or production data as `UNVERIFIED` with an owner and follow-up.

### Definition of done per capability

```text
user problem and product owner are explicit
AND canonical definition/source and version are traceable
AND actor, scope, permission and effect are verified server-side
AND read/write path preserves domain ownership and Evidence lineage
AND success, partial, empty, stale, blocked, offline and error states are truthful
AND each approved operational surface completes its assigned part of the business task with suitable composition
AND keyboard, touch, screen reader and reduced motion have equivalent paths
AND a real action result can be inspected and returned to its origin
AND focused tests plus affected integration/runtime regressions pass
```

The binding registry is an implementation and acceptance ledger. It is not evidence that every planned module has shipped; completion is reported only for rows whose source, runtime behavior and acceptance are verified.

## 36. The 44 screen-specific UX blueprints

These blueprints are product design decisions, not claims that the App, endpoints, or data have shipped. The matching screen ID is retained only for navigation and contract traceability. Each composition must be built and accepted as its own workflow. A common header, typography scale, evidence citation treatment and input behavior may recur; layout grammar, primary visualization and task choreography may not be copied blindly between screens.

### Mandatory per-screen specification gate before implementation

Do not begin feature implementation for any screen until its screen-specific specification is reviewed and accepted. The specification must link the ScreenId and applicable binding IDs, and record:

1. Intended role, user task, entry route/context, exit paths and Trace/Return restoration behavior.
2. Key fields and their visual priority, with each field tied to its verified source/ViewModel contract; unresolved fields remain `UNKNOWN` and block implementation of dependent behavior.
3. A state matrix for loading, empty, not collected, stale, partial, offline, blocked, permission denied, error and success, with truthful copy and recovery action for each applicable state.
4. A surface matrix covering Public Website (explanation/demo only), Web Workspace (primary/available), Desktop (enhanced/exclusive) and Mobile Companion (view/notify/approve/light action), plus separate applicable layout anatomy, navigation, responsive transition, interactions, keyboard/touch behavior and screen-reader order.
5. Every read/write action's owner, actor/scope, permission decision, side effect, idempotency/reversal behavior and Evidence lineage; UI affordances are never authorization.
6. Stable test IDs and executable acceptance cases covering the real task, state/error paths, responsive behavior and Trace/Return; include widget, API/integration and runtime/E2E cases as applicable.

The design review records pass/fail per screen in `contracts/experience/screen-specifications/<SCREEN-ID>.md`, using `SCREEN_SPEC_TEMPLATE.md`. These detailed specifications are a post-plan, pre-implementation gate: the current 44 rows below are distinct UX blueprints, not proof that every field, route, state and action is implementation-ready. A screen with unresolved owner/API/permission/lineage or missing acceptance evidence can proceed only as a clearly labeled `DESIGN_EXPLORATION`; it cannot be marked `DESIGN_READY`, implementation-ready or shipped. `DESIGN_READY` requires a Sol-reviewed detailed specification with its authority basis, artifact disposition, surface matrix, anti-template check and executable acceptance complete. Reusable tokens and accessible behaviors are allowed, but this gate does not permit a shared renderer or substituted-title template.

| Screen | Purpose-built information composition and visual language | Primary interaction and result | PC → mobile recomposition |
| --- | --- | --- | --- |
| ACC-01 Authentication entry | Quiet, focused identity surface with one clear account form, provider choices only when actually supported, and a compact trust/status rail; no analytics shell. Auth behavior stays `UNKNOWN` until bound. | Enter credentials or select a supported sign-in method; show validation, pending, rejected and recovered states distinctly. | Centered form with help/status pane → single-column form with touch-safe fields and explicit return. |
| ACC-02 Subject and lens selection | Two-stage chooser: authorized Subject list first, then CTH or BMP lens; subject identity and lens are visually separate so selecting a view cannot imply changing ownership. | Search/select an authorized Subject, then confirm an available lens; server response controls the destination. | Searchable split list/detail → searchable full-screen list then focused subject confirmation. |
| ACC-03 Workspace launch | A spatial launch map of recent work, CTH/BMP entry points and the central AI task entry; runtime health is a small truthful indicator, not another dashboard. | Resume a restorable work context or start a named product task. | Persistent domain rail plus recent-work canvas → compact destinations and one prominent resume/start action. |
| ACC-04 Access recovery and guard | A boundary/recovery screen explains which step is blocked, what scope is missing and how to recover; no fictional credentials, roles or access grant. | Retry, switch to authorized account/context, or request access through a real flow once verified. | Diagnostic steps beside the attempted destination → sequential recovery cards with clear back path. |
| CTH-01 Commercial operations overview | Subject-anchored operating desk: metric spine, chronological signal ribbon, event/evidence focus and a decision/action queue. Avoid BMP's brand network composition. | Scrub a change on the timeline, inspect its source, open/create a case or decision and trace the follow-up. | Parallel metrics + timeline + action queue → one active signal with swipeable evidence and a contextual action sheet. |
| CTH-02 Subject / business-unit profile | Ownership map showing Subject → business unit → brand/format relationships, with source/owner labels and a separate context selector. | Expand a relationship and inspect its provenance; switch the selected Subject only through the authorized context control. | Hierarchical tree and relationship table → compact breadcrumb hierarchy with focused relationship cards. |
| CTH-03 Real-time monitoring | Live pulse strip with freshness clock, confirmed-vs-live distinction, source lanes and collector health band; the update rhythm is the main visual. | Pause/resume viewing, pin an event, open source evidence; health actions remain permission-gated. | Multi-source live board with filters → prioritized single stream and persistent freshness/connection badge. |
| CTH-04 Event relationships | Causal event constellation paired with a time axis; nodes encode event/case links and evidence anchors, not generic cards. | Select a node to reveal linked evidence, navigate to its case, then Trace/Return to the same graph position. | Interactive graph + synchronized timeline → vertical event path with evidence nodes and saved zoom/focus. |
| CTH-05 Sentiment calendar | Calendar heatfield where each date shows event/sentiment density with a clear scale and data-availability legend; selected date drives a linked evidence strip. | Choose a day/range to inspect events and sources; switch to list view for precise keyboard access. | Month heatmap beside date detail → week/day agenda with density marks and a slide-up evidence list. |
| CTH-06 Negative monitoring and feedback | Triage queue differentiates public opinion, customer feedback and confirmed incidents; the active item opens a source-first reading pane. | Verify original Source, classify or link to a Case, and preserve the source wording and lineage. | Dense triage table with source inspector → stacked review cards with filters and full-screen source reader. |
| CTH-07 Trend analysis | Aligned time-series canvas with metric-definition rail, comparison overlays and a decomposition panel for what changed; every axis states units/window. | Add/remove a compatible metric or cohort and inspect the contribution/evidence behind a delta. | Resizable synchronized charts and formula table → one primary chart, horizontal metric switcher and tappable delta explanation. |
| CTH-08 Case and knowledge library | Lifecycle columns for open cases and a separate verified-knowledge shelf; case timeline remains distinct from reusable lessons. | Move a case through an authorized state transition; promote a reviewed conclusion to knowledge without overwriting facts. | Board/list toggle with case timeline inspector → prioritized case inbox and step-by-step timeline. |
| CTH-09 Risk and decision board | Risk register on one axis, decisions on another, with evidence and action ownership aligned row-by-row; high-risk states are never represented by color alone. | Inspect basis, assign/record a decision, request approval and confirm the resulting action. | Risk matrix plus decision ledger → ranked risk feed with focused decision detail and explicit confirmation. |
| CTH-10 Reports and weekly brief | Report storyboard separates metric narrative, evidence citations and methodology; preview is a paged artifact with scope visible. | Select a period and verified blocks, inspect source list, preview and export with a recorded definition/window. | Outline + live page preview + evidence rail → report sections list, one-page preview and share/export sheet. |
| BMP-01 Brand and market overview | Brand-centered relationship field: brand health at center, audience/creators/channels/competitors as connected market forces; do not reuse CTH's timeline-first dashboard. | Focus a brand, inspect a relationship's evidence and jump into its market, propagation or campaign path. | Rich network canvas with linked channel and KPI strips → brand pulse summary with navigable relationship carousel and source trace. |
| BMP-02 Brand portfolio and competitors | Portfolio constellation distinguishes owned brands from competitor entities; category and identity sit around each brand, not in a CTH Subject table. | Compare or focus one brand; context switch is explicit and retains the previous focus for Return. | Multi-brand canvas and comparison columns → searchable portfolio list with focused brand profile and competitor chips. |
| BMP-03 Market intelligence | Opportunity radar plots category themes by momentum and evidence confidence, with a source brief beside the selected signal. | Filter a market/category window, inspect source provenance and mark a lead for review without calling it confirmed. | Radar/landscape with evidence dossier → ranked opportunity feed and source-reader drill-in. |
| BMP-04 Media propagation analysis | Propagation river maps channel → content → exposure → response with conversion stages and comparable time windows; no unsupported reach estimates. | Trace a campaign/content item through the funnel and inspect each platform's source, metric definition and freshness. | Flow visualization plus channel matrix → vertical funnel with channel selector and explicit metric/source details. |
| BMP-05 Creator ecosystem | Creator graph segments KOS/KOL/KOC/UGC by audience fit, authenticity, contribution and risk; transparent comparison table supports audit. | Open a creator dossier, compare verified contributions, note collaboration risk or attach to an authorized campaign. | Graph plus sortable roster and dossier → creator cards with fit/risk summary and dossier detail. |
| BMP-06 Content center | Editorial production board separates brief, draft, review, approved, scheduled and delivered assets; rights/provenance stays attached to each version. | Upload/version content, review lineage and approval, then request an authorized publish handoff. | Swimlane board with asset preview inspector → production queue with version stack and bottom approval actions. |
| BMP-07 Campaign workspace | Campaign control room arranged by objective → audience → channel mix → milestones → outcome; goals and actual results occupy separate visual tracks. | Build or revise a plan, assign owners/dates, request approval, record delivery and evaluate against its baseline. | Timeline and channel allocation side-by-side → guided milestone sequence with compact objective and status header. |
| BMP-08 Podcast studio | Audio-first editing stage: waveform and timecoded script align with research sources and speaker cues; keep this distinct from the general content studio. | Draft from an approved brief/evidence set, edit transcript against audio, review source claims and export a versioned cut. | Large waveform + script/source side panel → transcript-first editor with scrub controls and a source drawer. |
| BMP-09 Brand evaluation | Brand scorecard shows dimension, period-over-period movement, confidence and evidence coverage; narrative conclusions sit below the measured values. | Select a brand/period, inspect a dimension's definition and evidence, then compare only aligned baselines. | Score matrix with dimension trend small multiples → prioritized dimension list and one selected evidence-backed trend. |
| BMP-10 Brand risk and events | Brand incident field groups by severity, spread and recency; active event timeline leads into response ownership and evidence. | Triage an incident, assign a response, record approval/effect and revisit verified impact. | Incident map plus response timeline → urgent queue with a focused incident detail and action ladder. |
| BMP-11 Benchmark and competitor analysis | Normalized comparison workbench with metric definitions, side-by-side brand/competitor columns and an evidence strip; incomparable values are visibly withheld. | Select comparison set and time window, inspect normalization, identify a supported gap and export a traceable finding. | Multi-column benchmark grid and small multiples → swipeable comparison cards with sticky metric definitions. |
| AI-01 AI intent entry | Intent composer beside a preview of which product context and evidence will be used; suggested tasks are grounded in available capabilities. | State a task, confirm authorized context, inspect evidence/capability plan and start only when an executable route exists. | Composer and evidence preview in parallel → single prompt field with context chip and expandable plan preview. |
| AI-02 Capability task workbench | Task represented as cancellable stages with input/output artifacts between stages; stage transitions reveal evidence and permission requirements. | Start, pause/cancel, retry a safe stage or review a gated action before it runs. | Stage graph with artifact inspector → vertical progress path with persistent cancel and expandable evidence. |
| AI-03 Evidence-anchored analysis thread | Conversation claims are grouped by conclusion; each claim has inline evidence anchors, uncertainty labels and a provenance rail. | Open a cited source at the relevant passage, challenge/refine a claim or create an owned follow-up task. | Thread plus source inspector → claim cards with inline citations and full-screen source return. |
| AI-04 Agent and skill catalog | Capability matrix shows owner, supported task, required permissions, health and last verified call; code presence is not shown as availability. | Filter by task, inspect input/output and permission contract, then run a safe verified capability. | Matrix/catalog with capability detail panel → searchable capability list and detail sheet. |
| AI-05 AI Gateway and providers | Provider topology shows availability, latency, policy and fallback path while rules/data remain the core lane. | Inspect provider state or run a diagnostic; fallback must be observable and must not block core operations. | Gateway flow map with health table → provider status list with explicit fallback/last-check details. |
| SYS-01 Runtime health | Runtime topology traces App → API → database → adapters with current health, degradation and check time; avoid product KPI styling. | Open a failing dependency's diagnostic, inspect trace and invoke only an authorized recovery. | Dependency map with health timeline → ordered dependency list and focused diagnostic view. |
| SYS-02 Collector status | Platform lanes show scheduler, rate-limit, retry/backoff, queue and ingestion stage; failures stay outside Canonical until validated. | Inspect a run, retry/stop when allowed, and trace a collected record to its destination state. | Live operations table with per-platform drilldown → platform queue cards with persistent running/retry status. |
| SYS-03 Database and truth chain | Layered schema/version/integrity view links schema → source → canonical → evidence → metric; versions never imply readability or completeness. | Inspect a table/chain validation and open exact integrity errors; recovery is a separately authorized path. | Schema tree with chain timeline and diagnostics → chain stages with integrity summary and error detail. |
| SYS-04 Security and permission | Permission matrix maps actor × product/domain × operation/risk alongside a separate audit trail; policy and decision are inspectable. | Simulate/read an access decision, inspect policy reason, or approve only through a real second-factor/approval contract. | Matrix and audit ledger → searchable role/scope list with explicit decision detail. |
| SYS-05 Settings and appearance | Preference studio previews density, contrast, language and motion on representative CTH/BMP samples without touching business data. | Change a local/account preference, preview, save and restore defaults; announce persisted scope. | Side-by-side preference controls and live preview → grouped settings pages with immediate accessible preview. |
| SYS-06 Internal browser | Controlled evidence-capture workspace splits source page, capture metadata and audit actions; unmistakably separate from personal browsing. | Navigate only within allowed capture rules, pin a snapshot as Evidence and inspect the audit result. | Browser viewport plus evidence inspector → source capture full screen with a compact metadata/trace panel. |
| SYS-07 Evaluation and acceptance | Six-gate acceptance sequence shows owner, required evidence, result and unresolved blockers; PARTIAL/UNKNOWN remain visibly incomplete. | Open a gate's artifact, rerun a permitted check and inspect exact failing criterion. | Gate matrix with evidence detail → sequential gate cards with current blocker and artifact links. |
| SYS-08 Observability and logs | Trace waterfall links requests, runtime spans and structured errors; frontend prototype events are in a separate lane. | Filter by trace/time/component, inspect correlated logs and return to the originating runtime or task. | Waterfall and query facets with detail pane → trace summary followed by scrollable spans and errors. |
| SH-01 Content creation studio | Source-to-artifact canvas: brief and evidence rail, editable creation canvas, version/outcome lane; different from campaign planning and podcast editing. | Create a draft from a real brief, cite evidence, review revisions and hand off for human approval. | Three-zone canvas (sources/work/artifact) → focused editor with source drawer and version/action sheet. |
| SH-02 Evidence library | Search-first evidence atlas organized by source, time, domain and lineage; original snapshot and extracted citation remain adjacent. | Search/filter, compare source with extracted item, inspect freshness and open its owning CTH/BMP origin. | Dense result list with provenance inspector → searchable evidence cards with full-screen source trace. |
| SH-03 Canonical data and metrics browser | Schema/metric explorer places definition, owner, lineage and sample records in distinct panes; derived values are marked as derived. | Inspect a field or metric and traverse lineage; this is read-only exploration, not business fact editing. | Navigable schema tree plus query/result panes → table/metric list with definition and lineage drilldown. |
| SH-04 Report export center | Output queue distinguishes configuration, generated preview, completed artifact and failed export; format-specific preview appears beside provenance. | Choose PDF/Excel/PPT only when supported, set scope, inspect preview, export and retrieve audited artifact. | Export configuration and artifact preview split → guided export steps and a final downloadable artifact view. |
| SH-05 Learning and evaluation assets | Maturity shelf groups verified SOPs, retrospectives, training and evaluation sets apart from drafts; provenance and review date are visible. | Open a learning asset, inspect verification history, propose a revision or use it as a cited task input. | Asset shelves with review timeline → filtered learning library and one-asset reading view. |
| SH-06 Notifications and tasks | Action inbox separates approvals, owned tasks, alerts and informational subscriptions into urgency lanes with source context. | Triage, assign/snooze/resolve only through authorized actions; every item returns to its originating task/evidence. | Multi-lane inbox with detail inspector → prioritized queue and full-screen task action with clear origin/return. |

### Blueprint implementation rules

1. Validate each row's user problem with its intended role; amend composition where a real workflow contradicts the proposal without changing owner semantics.
2. Build each row's applicable Web Workspace, Desktop and Mobile Companion composition as separate layout decisions over the same typed owner contract. Public Website may explain or demo the capability only. Do not equate responsive resizing with mobile UX or browser availability with local capability.
3. Derive screen-specific typography, data density and visualization from its task. Reuse semantic tokens and accessibility behavior, never a universal card grid, generic dashboard or template-based page builder.
4. Keep the design blueprint, binding registry and implementation state separate: the blueprint says how a verified task should work; the binding registry says where truth and authorization come from; tests/runtime evidence say whether implementation works.
5. Complete visual regression only after live binding and action behavior pass. Review each applicable screen in Web Workspace, Desktop, tablet and Mobile Companion contexts with realistic long text, missing data and permission denial; review Public Website pages against their separate commercial-entry contract.
6. Treat audit/taskbook sketches, screenshots, prototypes and Figma output as references with status `DESIGN_EXPLORATION`. If code follows one of those artifacts without a current `DESIGN_READY` specification, or reproduces its repeated frame as a generic template, the Sol acceptance decision is `REWORK`.
