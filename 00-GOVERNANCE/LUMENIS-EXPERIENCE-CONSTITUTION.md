# LUMENIS Experience Constitution — CURRENT

> Status: **CANONICAL / SOLE EXPERIENCE DESIGN AUTHORITY**  
> Internal version: **3.0**  
> Effective: 2026-09-18  
> Stable path: `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md`  
> Machine authority: `00-GOVERNANCE/LUMENIS-EXPERIENCE-AUTHORITY-CURRENT.json`

This file is the **only human-authored UI / UX / visual / interaction / motion / responsive / presentation design authority in the repository**.

No feature, domain, handoff, audit, research note, reference pack, screenshot pack, design-system document, component registry, motion specification, logo specification, page specification, AI prompt, historical artifact or code comment may create a competing presentation authority.

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
- desktop, tablet and mobile;
- Chinese / English / Korean presentation;
- brand identity in product UI, logo usage and launch/re-entry motion;
- any future surface added to this product.

Feature contracts may define **objects, fields, states, permissions, workflows and truth semantics**. They may not define a separate visual language or page-composition authority.

The directory name `experience_v2/**` is a compatibility path. It does **not** grant Experience V2 design authority.

Historical design material is non-authoritative provenance. Physical cleanup is a separate next-round task; the V3 convergence round must not continue broad deletion.

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

Authentication/access surfaces are calm, direct and explicit about identity, permission, blocked state and recovery. They are not marketing landing pages.

Global Subject Context:

```text
Selected Subject → Domain Lens → Scope / Permission
→ Function / Metric → ViewModel → Experience / Report / Export
```

CTH and BMP may interpret the Subject differently but must not create competing subject-context systems.

Navigation reveals current context and the next meaningful move. It is not a catalog of backend routes. No fixed rail/dock/sidebar shape is sacred.

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
- a competing design authority is introduced or historical material is treated as current design authority.

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
4. read `experience_v2/AGENTS.md` only as an execution router;
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

## 27. Authority exclusivity and cleanup freeze

V3 is the sole current design authority.

For the **current V3 convergence round**, do not perform additional legacy-design cleanup, archive purges, screenshot/reference-pack deletion, or broad historical-file removal merely to make the tree look clean.

This round is limited to:

```text
V3 authority
→ Codex routing
→ anti-template enforcement
→ implementation migration
→ acceptance
```

Historical material, if still present, is non-authoritative provenance only and must not be normal Codex implementation input.

Physical legacy cleanup is a **separate next-round task** with its own inventory, dependency check, reference repair and regression evidence.

Machine authority registry:

```text
00-GOVERNANCE/LUMENIS-EXPERIENCE-AUTHORITY-CURRENT.json
```

Blocking checks:

```text
python scripts/audit_tools/verify_experience_authority_exclusive.py
python scripts/audit_tools/verify_experience_anti_template.py --strict
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
V3 SOLE AUTHORITY ACTIVE
V3 WHOLE-PRODUCT COVERAGE ACTIVE
ADDITIONAL LEGACY CLEANUP FROZEN FOR THIS ROUND
IMPLEMENTATION MIGRATION REQUIRED
```

Current production CSS/JS/assets may temporarily contain legacy implementation structure until migrated. They are implementation, not design precedent.
