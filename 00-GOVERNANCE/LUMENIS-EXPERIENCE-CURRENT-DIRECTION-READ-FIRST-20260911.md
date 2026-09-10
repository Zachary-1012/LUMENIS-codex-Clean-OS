# LUMENIS Experience Current Direction — READ FIRST

> Status: **CURRENT DIRECTION / CODEX READ-FIRST**  
> Effective: 2026-09-11  
> Scope: `Zachary-1012/LUMENIS-codex-Clean-OS`  
> Purpose: record the current Experience-layer direction agreed on 2026-09-11 so later Codex / Agent execution can recover the intended product presentation without relying on historical chat memory.

---

## 0. Truth boundary

This document records the **current Experience direction**, not Production Truth.

Before any implementation, Codex / Agent MUST re-read current:

- `README.md`
- `AGENTS.md`
- `00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md`
- `LUMENIS_NEW_PRODUCT_DESIGN_BASELINE_V1.md`
- current source / route / API / DB / runtime / permission / test evidence

Audit anchor when this file was created:

```text
main = ab67612367c172ced2dff62b44e98de86469d1e6
```

This SHA is an audit anchor only. It does **not** mean Production Ready. `README.md` still defines the current phase as `PRODUCTION CONVERGENCE`.

---

## 1. What was decided in the 2026-09-11 design conversation

### 1.1 New production Experience is rebuilt, not cosmetically repaired

The old product pages are capability evidence only.

```text
Legacy UI / HTML / CSS / Layout / visual motion
                    ↓
            READ-ONLY CAPABILITY EVIDENCE

                    X
                    │ must not be inherited
                    ↓

          NEW PRODUCTION EXPERIENCE
```

Allowed to recover from legacy implementation:

- business functions
- fields
- state semantics
- route/API evidence
- permission requirements
- Evidence relationships
- runtime behaviors
- business workflows
- tests and production constraints

Not allowed as the new visual implementation source:

- old page layout
- old HTML structure as a template
- old CSS stack
- old dashboard composition
- old cards/tables/navigation visual grammar
- old visual motion
- old responsive presentation

Current `templates/base.html` loads multiple historical visual CSS layers; the new Experience must not add another overlay on top of that stack.

### 1.2 New isolated Experience root

The Experience build is expected to be isolated under a new root, e.g.:

```text
experience_v2/**
```

New presentation naming convention:

```text
root: .lum-app
class: lum-*
CSS variable: --lum-*
```

For the Doubao Experience production stage, the repository boundary is stricter:

```text
current repository files = READ ONLY
experience_v2/**         = ONLY WRITE AREA
```

Doubao may read/search/trace/audit existing backend and legacy frontend implementation for mapping, but must not modify them.

### 1.3 Role split

```text
DOUBAO / EXPERIENCE BUILD
Visual + UX + IA + Motion + Interaction + Original Assets
+ Components + Responsive + Copy + Prototype + Contracts
                    ↓
        CODEX-READY EXPERIENCE HANDOFF
                    ↓
CODEX / PRODUCTION INTEGRATION
Current backend re-audit + real API/DB/Runtime/Permission/Evidence
+ adapters + E2E + release acceptance
```

Doubao is not authorized to repair or refactor backend code during this phase.

Codex should not have to redesign colors, spacing, card structures, states, motion, responsive behavior, copy hierarchy or the brand launch experience after receiving the complete Experience handoff.

### 1.4 Backend write prohibition for Doubao

Doubao may only:

```text
READ / SEARCH / TRACE / AUDIT / MAP / DOCUMENT
```

against current backend / runtime / permissions / production data.

If an integration dependency is not verified, it must be recorded as one of:

```text
VERIFIED_EXISTING
VERIFIED_UNAVAILABLE
PARTIAL
UNKNOWN
CODEX_BINDING_REQUIRED
```

Never invent endpoints, fake HTTP 200 responses, fake Evidence, fake runtime progress, fake permissions or fake production data to make a design appear complete.

### 1.5 Technology direction for the Experience handoff

The new handoff/prototype direction is:

```text
HTML + CSS + Vanilla JavaScript / ES Modules
Jinja-friendly
```

Do not migrate the product to React/Vue merely to use visual reference libraries.

Research libraries/sites are reference material only. Production UI code and visual assets are self-developed.

### 1.6 Clean-room originality rule

External references can be used only to learn:

- interaction principles
- motion grammar
- information hierarchy
- geometry/depth
- state transitions
- performance risks
- accessibility risks

The project must not copy/paste external:

- UI source code
- component source code
- SVG/icons
- images/video assets
- shaders
- motion source
- branded visual compositions

Even if an external project license permits copying, the current LUMENIS design rule is stricter: **research only; implementation and assets are original.**

### 1.7 UX organizing model

The product experience is organized by context and decisions, not a historical menu tree:

```text
Context
→ Observe
→ Understand
→ Evidence
→ Decision
→ Action
→ Outcome
→ Evaluation
```

Page-level formation model:

```text
POINT      real object
   ↓
LINE       object relationship
   ↓
SURFACE    understandable UI component
   ↓
SCREEN     one user problem
   ↓
WORKFLOW   continuous task
```

Important conclusions must remain traceable back to Evidence.

### 1.8 Global Subject Context

Current repo authority has converged further than older design text: CTH and BMP both support **Selected Subject** and share one Subject Context semantic model. The Domain Lens changes the analysis, metrics, object relationships and actions.

The Experience layer must therefore present one compatible global Subject Context rather than two unrelated subject-selector systems.

Backend Subject Context remains Codex-owned and must be re-audited before binding.

### 1.9 AI workspace direction

Current GPT-style three-pane Chat UI is capability evidence only.

Target experience:

```text
Intent
→ Task
→ Runtime
→ Evidence
→ Artifact
→ Decision
→ Action
→ Evaluation
```

AI result should be artifact-first, not a long chat bubble by default.

AI Home should be intent-first; AI Working should be task-first; AI Result should be artifact-first.

No fake thinking animation. Runtime visual state must be driven by a real backend state or an explicitly marked `DESIGN_ONLY` fixture.

### 1.10 Material and visual direction

Three material tiers:

```text
A — Truth Surface
Evidence / Table / Report / Analysis / Form / Runtime
Opaque, stable, high-readability

B — Spatial Surface
KPI / Context / Filter / Selector / Popover / Floating panel
Soft depth / controlled glass

C — Optical Surface
AI Composer / active nav-dock bubble / task morph / transient tool dock
Selective self-developed optical material only
```

Liquid/optical glass is a material capability, **not** the product theme.

The optical layer must fail safely:

```text
OPTICAL → SOFT GLASS → OPAQUE
```

No business functionality may depend on GPU effects.

### 1.11 Motion direction

Motion explains a state relationship; it is not decoration.

```text
State A
  ↓ real trigger
Motion
  ↓
State B
```

Core motion registry established in the design package:

```text
M01 App Shell Reveal
M02 Nav Active Travel
M03 Context Change
M04 Card → Workspace Morph
M05 Capability → Task
M06 Task Stage Progress
M07 Artifact Reveal
M08 Evidence Preview → Rail
M09 Drawer / Bottom Sheet
M10 Segmented Travel
M11 Calendar Selection
M12 Upload Pipeline
M13 Success Resolution
M14 Error / Recovery
M15 Composer State
```

Motion source must be reproducible and interruptible; reduced-motion alternatives are mandatory.

### 1.12 Responsive direction

Target validation widths:

```text
1920 / 1440 / 1280 / 1024 / 768 / 430 / 390 / 360
```

Responsive is recomposition, not desktop scaling.

Examples:

```text
Context Rail: desktop right rail → tablet drawer → mobile bottom sheet
Navigation: desktop rail → compact → mobile bottom dock
Table: full table → reduced columns → structured list → data card
Composer: docked/centered → safe-area bottom composer
```

### 1.13 Naming and copy architecture

Visible product naming must be replaceable without changing machine contracts.

```text
Machine ID        stable
      ↓
Semantic Copy Key stable
      ↓
Display Value     replaceable
```

Examples:

```text
cth
→ domain.cth.name
→ 序境·商业运营 / LUMENIS Commerce Operations / 서경·커머스 운영
```

Product labels/buttons/tabs/tooltips/placeholders/errors should be Copy Registry/i18n values.

Real business data such as Subject name, Brand name, Campaign/Event name, post title and Evidence content must **not** be embedded as locale copy.

Current production locale files are read-only during the Doubao phase. Doubao should provide i18n delta/copy registries for Codex to merge after audit.

### 1.14 Experience production scope

The previously provided Experience master plan enumerates the complete experience as:

```text
ACC × 4
CTH × 10
BMP × 11
AI × 5
SYSTEM × 8
Shared × 6
= 44 numbered screens
```

The detailed screen definitions remain in the handoff plan supplied to Doubao; this direction record does not duplicate that plan.

### 1.15 Internal calibration must not create another approval round

Doubao proposed a one-page template anchor before full production. This was changed to an internal dual-calibration step:

```text
AI-01 Home + CTH-01 Overview
            ↓
automated/internal quality review
            ↓
PASS → continue all remaining screens
FAIL → internally repair → retest
```

Do not stop after the anchor and ask the user to approve a new round unless a genuine hard blocker exists.

### 1.16 Brand logo and launch animation direction

The 2026-09-11 conversation added a brand identity/launch requirement built around the philosophy **芥子纳须弥**.

Core visual idea:

```text
point
→ droplet
→ sea / contained world
→ expansion
→ re-convergence
→ final logo
```

Logo concept:

- abstract optical/liquid droplet
- a contained sea/horizon/world inside it
- high quality, restrained, not a generic ocean/water mark
- color is dynamic, not locked to ordinary water-blue or life-green

Preferred dynamic spectrum:

```text
Clear Mist      #F6F8FF / translucent white
Opal Lilac      #B8A8FF
Deep Indigo     #2A2468
Aurora Cyan     #8BE7FF  (small optical accent only)
Pale Gold       #F4D38A  (small warm highlight)
Moon Silver     #DDE3F2
```

Three official logo families:

1. Standard: symbol + Chinese handwritten `序境` + Latin handwritten/script `LUMENIS`.
2. Korean: symbol + independently designed Korean handwritten wordmark.
3. Clean symbol: symbol only, no text.

The logo wordmark may be handwritten/custom; normal product UI text remains a readable modern UI font.

Three launch-animation variants must correspond to those three logo families.

Full launch animation target: approximately 2.1 s.

```text
small transparent droplet appears
→ falls
→ touches surface
→ abstract sea/horizon expands
→ contained world briefly forms
→ sea/world reconverges
→ final logo locks
→ wordmark appears where applicable
→ product shell enters
```

A short 0.6–0.9 s variant is also required for re-entry/lightweight scenarios.

The launch animation must not block real data loading; reduced-motion/low-performance environments must be able to show the static logo directly.

---

## 2. Current work status

### Completed at decision/specification level

- Experience separation strategy
- legacy visual non-inheritance rule
- Doubao write boundary
- Codex integration ownership
- self-developed asset/code policy
- design research method
- material tiers
- motion registry
- responsive target sizes
- naming/copy replaceability
- capability/state/action contract strategy
- 44-screen Experience scope
- brand logo concept
- three logo families
- three launch animation families
- handoff expectations

### Not claimed complete

The following are **not** claimed complete by this document:

- Doubao full `experience_v2` production package
- final logo artwork
- final motion source/video assets
- PSD export
- current real backend binding
- production route switch
- production E2E
- Production Ready / Released / Operating

The user intends to provide the reference images/video directly to Doubao and later upload Doubao-produced Experience assets. Those future assets must be treated as versioned design/experience input, not as proof that the production backend is already integrated.

---

## 3. Required read order for future Codex integration

When the complete Doubao package is later present, Codex should read in this order:

```text
1. README.md
2. AGENTS.md
3. Production Acceptance
4. this CURRENT-DIRECTION file
5. LUMENIS-EXPERIENCE-DESIGN-AUTHORITY-V2-20260911.md
6. LUMENIS-EXPERIENCE-RESEARCH-LEARNING-ASSET-V1-20260911.md
7. Doubao experience_v2/19_handoff/INTEGRATION_START_HERE.md
8. current source / route / API / permission / Evidence / runtime
9. bind adapters
10. critical E2E + Production Acceptance
```

Never use this file, a design screenshot, an MP4, a PSD/SVG, or the Doubao package to override current Production Truth.

---

## 4. Companion documents created from the same 2026-09-11 design session

- `00-GOVERNANCE/LUMENIS-EXPERIENCE-RESEARCH-LEARNING-ASSET-V1-20260911.md`
- `00-GOVERNANCE/LUMENIS-EXPERIENCE-DESIGN-AUTHORITY-V2-20260911.md`

The first is reusable research/learning material. The second is the canonical Experience presentation/design execution authority.