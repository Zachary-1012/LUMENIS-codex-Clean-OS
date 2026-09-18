# LUMENIS Experience Constitution V3

Status: CANONICAL / P0 EXPERIENCE PRESENTATION AUTHORITY
Effective: 2026-09-18
Scope: all user-visible LUMENIS / 序境 production experience and all Codex/Agent work that changes Experience structure, navigation, visual hierarchy, components, motion, responsive composition, AI workspace, Evidence presentation, CTH, BMP, Shared or SYSTEM surfaces.

## 0. Authority boundary

Production truth still outranks presentation.

Authority order for Experience work:

Current verified source / runtime / data / permission / Evidence truth
> Production Acceptance and current product governance
> THIS CONSTITUTION V3
> current Experience contracts and screen specifications
> older Experience V2 / V2.4 / V2.5 documents
> research references
> legacy UI and historical screenshots

When this V3 conflicts with older Experience presentation rules, V3 wins.

This document does not authorize changing backend truth merely to make a visual composition easier.

## 1. Why V3 exists

The 2026-09-18 audit found a structural source of template drift.

Audit anchor only: main@17570ae142c308cc2446b802170bd4b1d6439148.

Observed facts at that point:

- experience_v2/10_prototype/assets/sections.js stated that 44 screens may only compose registered pattern/component families and disallowed bespoke layout.
- CTH-01, BMP-01 and SYS-01 shared the same top-level signature: head > kpis > split.
- all ten screens using the generic kpis section rendered exactly four metrics.
- thirteen screens shared head > split.
- representative generated screen HTML wrappers were structurally identical across CTH, BMP, SYSTEM and AI.
- visual styling had improved, but the underlying page grammar could still collapse distinct workflows into the same dashboard skeleton.

Therefore the problem is not solved by adding glass, shadows, gradients, Apple-like spacing or Korean visual references. The composition model itself must stop treating component reuse as page sameness.

## 2. Product identity

LUMENIS is a Living Intelligence Space.

It is not:

- a generic SaaS dashboard
- an admin console
- a BI dashboard
- a CRM
- a card-grid application
- an Apple clone
- a Linear clone
- a Notion clone
- a ChatGPT clone
- a Korean-brand website clone
- a Bento dashboard with product data inserted into tiles

External products are research sources, never visual targets.

A user should be able to hide the logo and still recognize LUMENIS from its information grammar, Evidence trace, realm behavior, state transitions and workflow structure.

## 3. Canonical Experience grammar

The product is organized around real objects and their relationships:

Point
→ Evidence
→ Relationship
→ Event
→ Case
→ Insight
→ Decision
→ Action
→ Outcome
→ Evaluation
→ Learning

The user-facing question order is:

What changed?
→ Why does it matter?
→ What proves it?
→ What can I do?
→ What happened after the action?

Metrics support these questions. Metrics are not automatically the page.

Important conclusions must provide a natural Trace / Return path to Evidence.

The brand philosophy 芥子纳须弥 is an interaction rule, not decoration: a large conclusion must be able to return to the smallest verifiable point.

## 4. Composition rule: primitives are reusable, screens are semantic

Reuse components, tokens and interaction primitives aggressively.

Do not reuse page skeletons merely because reuse is convenient.

The old rule “all 44 screens must only compose the same fixed component families” is superseded.

Allowed:

- shared typography, spacing, iconography and state primitives
- shared Evidence renderer
- shared controls, filters, input, table primitives and accessibility behavior
- shared motion tokens and material roles
- shared shell behavior where the shell genuinely stays constant
- realm-specific and workflow-specific compositions built from common primitives

Forbidden:

- forcing distinct workflows through one generic Head + KPI + Chart + Table grammar
- treating kpis, cards, split, chart and table as the default page ontology
- duplicating the same top-level section sequence across unrelated Golden Pages
- converting Event, Evidence, Case, Insight, Runtime or Artifact into generic CRUD cards merely to fit a renderer
- using CSS decoration to disguise an unchanged SaaS skeleton

## 5. Realm dialects

The four realms share one LUMENIS grammar but must not be four color themes on the same page.

### CTH / Commerce Operations

Primary spatial idea: time, event, place, operational change.

Canonical V3 primitives include:

- now_stream
- event_flow
- evidence_trace
- case_evolution
- decision_path

CTH should feel temporal and causal. It should answer what is happening now and how it evolved.

### BMP / Brand & Market

Primary spatial idea: network, content, creator, brand and market relationships.

Canonical V3 primitives include:

- market_network
- creator_constellation
- content_cluster
- evidence_trace
- market_movement

BMP should reveal relationships and propagation, not merely show another set of KPIs.

### Shared Capability

Primary spatial idea: creation, artifact and learning transformation.

Canonical V3 primitives include:

- creation_flow
- artifact_flow
- brief_to_artifact
- evaluation_loop
- learning_trace

Shared should behave like a creation/research workspace, not a reporting dashboard.

### SYSTEM

Primary spatial idea: infrastructure truth made understandable.

Canonical V3 primitives include:

- runtime_topology
- health_trace
- collector_flow
- permission_boundary
- recovery_path

SYSTEM may be denser and more technical, but it must expose machine relationships rather than imitate a generic admin console.

## 6. AI experience

AI is artifact-first, not chat-first.

Canonical flow:

Intent
→ Task
→ Runtime
→ Evidence
→ Artifact
→ Decision
→ Action
→ Evaluation

AI-01 must begin from intent_space, not a dashboard row of four operational KPIs.

Canonical V3 AI primitives include:

- intent_space
- task_runtime
- evidence_trace
- artifact_flow
- approval_path

Conversation history may exist, but long chat bubbles must not become the default product container.

No fake thinking animation, fake progress or confidence unsupported by runtime truth.

## 7. Anti-template hard failures

The following are Experience failures unless an explicit current workflow requirement proves an exception.

- a Golden Page has a top-level kpis section
- a Golden Page has a top-level generic cards section as its main organizing structure
- CTH-01, BMP-01, SYS-01, AI-01 and SH-01 share duplicated top-level signatures
- home/overview screens begin with a four-column KPI wall
- a page can be converted from CTH to BMP by changing only labels, data and accent color
- Evidence is available only as a generic details page instead of a first-class trace action
- Event, Case and Insight are rendered as equivalent CRUD records
- AI result defaults to chat bubbles instead of an Artifact
- glass or optical material becomes the global theme
- “Apple style”, “Korean style”, “Linear style” or another brand name is used as the target design specification
- multiple pages are declared complete because they render from the same schema while their user problems are different

## 8. Material, typography and motion

Apple HIG, Toss and other references remain research inputs.

Material roles remain semantic:

Truth Surface: opaque, stable, high readability.
Structure Surface: restrained separation and depth.
Optical Surface: small, selective, optional interaction emphasis.

Optical effects never rescue weak information architecture.

Motion only explains a real state relationship. If state does not change, animation is not required.

Reduced-motion and weak-device degradation remain mandatory.

## 9. Golden Pages migration

Before broad visual migration, five pages establish the product DNA:

1. AI-01: intent_space + evidence + artifact_flow
2. CTH-01: now_stream + event_flow + evidence_trace
3. BMP-01: market_network + evidence_trace
4. SH-01: creation_flow + artifact_flow
5. SYS-01: runtime_topology + health_trace

These five screens must have five distinct top-level semantic signatures.

They are not mockups detached from production. Each must preserve current ViewModel, permission, runtime and Evidence truth boundaries.

After the Golden Pages pass, remaining pages migrate by workflow family, not by bulk skinning.

## 10. Acceptance model

Experience completion is not “page renders”.

For any meaningful Experience change, verify as applicable:

Semantic question
→ ViewModel truth
→ realm/workflow composition
→ Evidence trace
→ user action
→ honest state/error
→ responsive recomposition
→ visual regression
→ ARIA/structure regression
→ runtime/E2E

Static anti-template gate:

python scripts/audit_tools/verify_experience_anti_template.py --strict

The gate is ratchet-only. Thresholds may be tightened as migration progresses. They may not be weakened merely to make CI green.

Visual acceptance should use deterministic Playwright screenshot baselines for Golden Pages and representative realm screens. Structural accessibility should use ARIA snapshots or equivalent assertions. Snapshot updates require intentional review; regenerating snapshots is not proof that a change is acceptable.

Target widths remain:

1920 / 1440 / 1280 / 1024 / 768 / 430 / 390 / 360

Responsive means semantic recomposition, not desktop scaling.

## 11. Codex execution protocol for Experience work

Before writing code:

1. fetch and resolve current origin/main
2. read root AGENTS.md
3. read this Constitution V3
4. read experience_v2/AGENTS.md
5. inspect current source owner, caller, ViewModel, Evidence, permissions and tests for the active screen
6. state the user problem and semantic composition before editing CSS

Implementation order:

User problem
→ semantic objects/relationships
→ composition
→ shared primitives
→ realm-specific behavior
→ binding
→ states
→ responsive
→ motion/material only where justified

Forbidden implementation order:

choose attractive style
→ add cards
→ add glass
→ insert data
→ call it LUMENIS

For a non-trivial Experience task, Codex must make a plan first and include:

- active screen/workflow
- truth sources
- V3 semantic primitives to use
- which generic pattern is being retired or avoided
- acceptance checks

## 12. Review rules

A reviewer or Codex review must flag:

- new top-level KPI walls
- generic card-grid expansion
- duplicated page signatures across realms
- visual-only “Apple/Korean/Linear” imitation
- new page-level abstractions that erase workflow differences
- CSS-only redesign that leaves the same semantic hierarchy
- missing Evidence trace on important conclusions
- missing responsive recomposition
- weakened anti-template thresholds or skipped visual acceptance

A visually attractive result can still fail V3.

## 13. Research basis

The execution mechanism is aligned with current Codex guidance:

- Codex automatically loads AGENTS.md project instructions.
- instructions closer to the working directory can specialize broader repository rules.
- repeated agent errors should become durable AGENTS.md rules.
- enforceable rules should be paired with CI/checking infrastructure, not prompt text alone.

Reference:
https://developers.openai.com/docs/agent-configuration/agents-md
https://developers.openai.com/guides/best-practices

Visual/structure regression basis:
https://playwright.dev/docs/test-snapshots
https://playwright.dev/docs/aria-snapshots

## 14. Migration honesty

This V3 becoming canonical does not claim that the existing 44-screen implementation is already V3 compliant.

At the audit anchor, it was not.

Until the strict gate passes, describe the current Experience as:

V3 AUTHORITY ACTIVE / MIGRATION REQUIRED

Do not claim V3 COMPLETE from documentation existence alone.
