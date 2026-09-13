# LUMENIS Experience Research & Learning Asset V1

> Status: **RESEARCH / LEARNING ASSET**  
> Effective: 2026-09-11  
> Scope: reusable learning for LUMENIS UI/UX, visual design, motion, content creation, AI interface, branding and future product presentation.  
> Rule: **Research Asset ≠ Production Capability.** Research cannot override current source, runtime, permission, Evidence or Production Truth.

---

## 0. Why this file exists

The 2026-09-11 design work produced more than one product-specific UI plan. It also produced reusable methods for:

- turning abstract product philosophy into visual language;
- translating screenshots/video into interaction principles without copying them;
- generating a design system from product truth rather than decoration;
- turning state changes into motion grammar;
- separating visual material from business information;
- converting design outputs into contracts that engineers and AI systems can consume;
- building a clean-room research pipeline where external references inform learning but final code/assets remain self-developed;
- using the same methods later in LUMENIS content creation, AI learning and other product experiences.

This file preserves those methods as a learning asset.

---

# 1. Research doctrine

## 1.1 Clean-room rule

All external websites, repositories, screenshots, videos and product cases are **study references only**.

Allowed:

```text
observe
→ decompose
→ identify the problem being solved
→ extract principle
→ identify state model
→ identify motion/material model
→ identify accessibility/performance risks
→ design a LUMENIS-native equivalent
→ prototype from a blank implementation
→ benchmark
→ adopt/reject
```

Forbidden:

```text
download code
→ rename class
→ recolor
→ ship
```

Forbidden assets include:

- third-party UI source
- third-party SVG/icon
- third-party shader
- screenshots cropped into product UI
- third-party motion clips
- branded design compositions
- code copied because its license technically allows it

LUMENIS currently follows a stricter internal rule: **code and product-visible assets are self-developed.**

## 1.2 Research promotion chain

```text
REFERENCE
→ OBSERVATION
→ PRINCIPLE
→ LUMENIS HYPOTHESIS
→ ORIGINAL PROTOTYPE
→ TEST
→ EVIDENCE
→ DESIGN DECISION
→ IMPLEMENTATION CONTRACT
```

A reference does not become a production capability by being attractive or technically impressive.

---

# 2. External research sources and what was learned

## 2.1 MotionSites

Source:

- https://motionsites.org/

Research use:

- page and section composition
- how interaction-heavy interfaces maintain hierarchy
- Cards / Forms / Navigation / Loader / Glassmorphic surface references
- high-level visual direction for real-software interfaces rather than pure portfolio art

Reusable learning:

1. A surface should solve one recognizable user problem.
2. Motion quality depends on hierarchy and pacing before it depends on effects.
3. The most useful references are decomposed into layout, focus, transition and interaction affordance — not copied as whole screenshots.

Do not use its prompts or downloadable assets as LUMENIS production content.

## 2.2 Showreel.design

Source:

- https://showreel.design/

Research use:

- UI/UX motion narrative
- sequencing of state changes
- minimal/clean versus futuristic/tech motion language
- understanding how one object remains identifiable while changing state

Reusable learning:

A useful motion description requires four fields:

```text
Before State
Trigger
Continuity Principle
After State
```

Example:

```text
Before State:
AI Capability Card

Trigger:
User selects a capability

Continuity Principle:
The card identity remains spatially continuous

After State:
Task Workspace Header
```

This is more reusable than labels such as “fade”, “slide” or “zoom”.

## 2.3 React Bits

Source:

- https://reactbits.dev/

Observed pattern categories during research included concepts such as:

- Fluid Glass / Glass Surface
- Dock
- Gooey navigation
- Staggered menu
- Stepper
- morphing controls

Reusable learning:

- study geometry, selection behavior and state continuity;
- separate the interaction pattern from the framework implementation;
- do not migrate a Flask/Jinja/Vanilla system to React only to obtain a visual effect;
- reimplement the useful principle in the native LUMENIS stack.

## 2.4 Anime.js

Source:

- https://animejs.com/

Research focus:

- timeline positions
- labels
- absolute/relative sequencing
- staggered timing

Reusable learning:

Motion should be modeled as a deterministic timeline with named events, not a pile of unrelated CSS transitions.

LUMENIS equivalent mental model:

```text
scene
├── trigger
├── from_state
├── to_state
├── label
├── start_offset
├── duration
├── easing
├── interrupt
├── reverse
└── reduced_motion
```

This learning does not require Anime.js as a runtime dependency.

## 2.5 Aceternity UI

Source:

- https://ui.aceternity.com/

Research focus:

- Floating Dock
- File Upload
- Expandable Cards
- shader-backed effects
- modal/tooltip compositions
- component interaction grammar

Reusable learning:

- a visual effect is useful only when it improves affordance or spatial hierarchy;
- one component should expose a clear state contract;
- visual composition can be studied independently of React/Tailwind/Motion source;
- LUMENIS implementation remains original HTML/CSS/Vanilla JS / self-developed optical code.

## 2.6 Uiverse

Source:

- https://uiverse.io/

Research focus:

- micro-interaction variety
- buttons/inputs/loaders/switches
- community exploration of interaction feedback

Reusable learning:

Use community examples as a broad sample set to understand:

```text
what changes on hover?
what changes on focus?
what communicates pressed?
what communicates selected?
what survives when animation is disabled?
```

Do not import component code into LUMENIS.

## 2.7 Liquid Glass research

Sources:

- https://github.com/ybouane/liquidglass
- https://liquid-glass.ybouane.com/

Research observations:

The reference implementation is materially different from ordinary CSS `backdrop-filter` glass. Its approach includes concepts such as:

- background sampling/capture
- blur
- optical displacement/refraction
- chromatic aberration
- Fresnel/specular lighting
- dynamic content recapture
- GPU/WebGL context cost

Reusable learning:

1. “Liquid Glass” should be understood as an **optical interaction material**, not a global theme.
2. High-cost optical surfaces should be small, selective and transient.
3. Text and semantic controls should remain HTML/UI layers; optical drawing should sit behind or around them.
4. Fallback must be designed first-class:

```text
OPTICAL
→ SOFT GLASS
→ OPAQUE
```

5. Do not build a universal DOM-rasterization/refraction engine merely because a research demo does so. A product-specific, smaller original implementation is preferable.

---

# 3. User-provided visual reference methodology

The user is supplying 11 reference images (`IMG_8970`–`IMG_8980`) and one AI-interface motion video directly to the Experience production stage.

These references are not stored in this repository by this document.

The correct analysis process for each asset is:

```text
ORIGINAL FILE
→ HASH / METADATA
→ CONTACT SHEET / KEYFRAME
→ OBJECTS
→ LAYERS
→ MATERIAL
→ INTERACTION
→ MOTION
→ PROBLEM SOLVED
→ RISK
→ LUMENIS ORIGINAL EQUIVALENT
```

Do not perform screenshot tracing.

## 3.1 Extracted visual-language family

The combined references pointed toward a shared visual family:

```text
Background / Ambient Field
        ↓
Base Surface
        ↓
Spatial Surface
        ↓
Content
        ↓
Interactive Control
        ↓
Active State
        ↓
Floating / Overlay
```

Qualities:

- soft spatial depth
- rounded but restrained geometry
- selective active color
- high information legibility
- shallow shadows
- muted borders
- motion based on transitions between states
- optical material reserved for special controls

The important reusable lesson is **layer discipline**, not glass everywhere.

---

# 4. From point to workflow — reusable experience-generation method

This became a central design-learning model.

```text
POINT
one real object
Subject / Brand / Metric / Creator / Content / Event / Evidence / Task

        ↓ relationship

LINE
Metric → Evidence
Event → Content
Finding → Evidence
Decision → Action
Action → Outcome

        ↓ understandable composition

SURFACE
Metric Card
Trend
Timeline
Evidence Preview
Artifact
Action

        ↓ one user problem

SCREEN
Context + Decision + Analysis + Evidence + Action

        ↓ continuous work

WORKFLOW
Observe → Understand → Decide → Create/Act → Measure → Evaluate → Learn
```

This model can later be reused in:

- UI design
- report design
- AI response structure
- content planning
- campaign storyboarding
- research synthesis
- agent task decomposition

---

# 5. Information hierarchy learning

## 5.1 The 2–4 layer rule

Do not force every page into maximum complexity.

Recommended hierarchy:

```text
L0 Context
L1 Decision View
L2 Analysis
L3 Evidence / Detail
```

Simple workflows may use two layers. Complex workflows may use four.

The page should normally answer in this order:

```text
What happened?
→ Why?
→ What proves it?
→ What can I do?
```

## 5.2 Dashboard lesson

Avoid KPI walls.

Better pattern:

```text
Question
→ Core metric/change
→ Trend
→ explanation/driver
→ Evidence
→ Action
```

This preserves decision value and avoids decorative data density.

---

# 6. Material design learning

Three reusable material roles were established.

## Tier A — Truth Surface

Use for:

- Evidence
- tables
- reports
- long text
- editors
- forms
- audits
- runtime details

Properties:

- opaque
- stable
- high readability
- low optical distraction

## Tier B — Spatial Surface

Use for:

- KPI summaries
- Context
- filters/selectors
- popovers
- toolbars
- floating support panels

Properties:

- subtle transparency
- controlled blur
- shallow elevation
- helps separate layers without becoming the content itself

## Tier C — Optical Surface

Use only for high-value interaction:

- AI Composer
- active nav/dock bubble
- task morph surface
- transient tool dock

Properties:

- self-developed optical effect
- optional
- small area
- fallbacks mandatory

Reusable principle:

> Material must explain spatial role. It is never a substitute for information architecture.

---

# 7. Motion grammar as reusable AI/design learning

## 7.1 Motion priority

```text
business state
> data state
> interaction state
> decoration
```

## 7.2 Motion levels

```text
Micro          ~80–180 ms
Component      ~180–280 ms
Layout         ~260–420 ms
Workspace      ~320–520 ms
Special        normally <=650 ms
```

## 7.3 Core verbs

```text
ENTER
EXIT
PRESS
LIFT
SELECT
MOVE
MORPH
EXPAND
COLLAPSE
REORDER
DRILL
RETURN
PROGRESS
COMPLETE
WARNING
ERROR
```

## 7.4 State-driven motion rule

```text
No state change
→ no animation needed
```

A task progress indicator must not move unless the task state actually changes.

An upload indicator must not manufacture fake progress.

An AI interface must not display endless “thinking” motion when the runtime cannot verify what stage it is in.

## 7.5 Reproducible motion asset pattern

For future content/interaction production, motion should be source-reproducible:

```text
motion-scene.json
source.mjs / source code
fixture-events.json
capture script
preview.mp4
preview.gif
reduced-motion preview
fallback preview
```

A video-only handoff is not a motion system.

---

# 8. AI interface learning

The reference AI-video analysis led to a general pattern:

```text
Blank / low information
→ Identity
→ Greeting
→ Capabilities
→ Composer
→ Task Workspace
→ Artifact
```

This was refined into a product state model:

```text
BOOT
→ INTENT_HOME
→ COMPOSING
→ TASK_ACCEPTED
→ EXECUTING
→ ARTIFACT_READY
→ APPROVAL
→ ACTION
→ EVALUATION
```

Reusable learning:

- AI home should answer “what can I do here?”
- AI working view should answer “what task is running and what evidence/state exists?”
- AI result should answer “what artifact did I get and what action can I take?”
- conversation history is useful, but should not dominate every AI task
- AI visual confidence must not exceed backend confidence

This pattern can also guide future LUMENIS content creation workflows:

```text
Brief
→ Context
→ Research/Evidence
→ Draft
→ Artifact
→ Review
→ Approval
→ Publish/Export
→ Evaluation
```

---

# 9. Responsive learning

Responsive design is not `desktop × scale`.

It is a change in **information placement while preserving semantic continuity**.

Examples:

```text
Evidence
Desktop: Context Rail
Tablet: Drawer
Mobile: Bottom Sheet
```

```text
Navigation
Desktop: Rail
Tablet: Compact navigation
Mobile: Bottom Dock
```

```text
Dense data
Wide: Table
Medium: Reduced columns
Narrow: Structured list
Very narrow: Data Card
```

This model should be reusable in any later LUMENIS module.

---

# 10. Naming and copy learning

An important product-design lesson from the session is that **brand naming must not be coupled to machine behavior**.

Three layers:

```text
Machine ID      stable
Semantic Key    stable
Display Value   replaceable
```

Example:

```text
cth
→ domain.cth.name
→ 序境·商业运营
```

If the visible product name changes later, the route/API/DB/permission identifier should not need to change.

This same method can be applied to:

- navigation labels
- report labels
- AI capability labels
- content templates
- campaign terminology
- status messages
- multilingual brand naming

Real business data must remain data, not localization copy.

---

# 11. Capability negotiation learning

A design system should not imply that every designed button already has backend support.

A reusable capability state model:

```text
VERIFIED_AVAILABLE
VERIFIED_UNAVAILABLE
PARTIAL
UNKNOWN
BLOCKED
CODEX_BINDING_REQUIRED
```

This allows Experience design to remain complete without falsifying the implementation state.

Future AI/UX systems should use the same discipline:

- show what is available;
- explain what is blocked;
- hide or mark what is unknown;
- never invent a backend capability to satisfy a screenshot.

---

# 12. State-source learning

Every visible state should have a declared origin:

```text
backend
frontend-derived
user-input
fixture / simulation
```

Example:

```text
AI execution stage      → backend
current KOC selection   → frontend-derived
composer text           → user-input
prototype success demo  → DESIGN_ONLY fixture
```

This makes it possible to reuse Experience prototypes without confusing them with Production Truth.

---

# 13. Brand philosophy → logo → motion learning

The brand work introduced a reusable creative method for translating philosophy into motion.

Brand philosophy:

**芥子纳须弥**

Abstract meaning:

```text
small truth
→ larger relationship/world
→ whole understanding
→ return to the original point
```

Visual translation chosen for LUMENIS:

```text
point
→ droplet
→ sea / horizon
→ contained world
→ reconvergence
→ final droplet/symbol
```

This is not “water branding”. It is a metaphor for:

- local fact → system
- small signal → contextual world
- complexity → structure
- whole → traceable origin

## 13.1 Logo family learning

A useful identity system can separate **symbol** and **wordmark**.

LUMENIS direction:

1. Standard logo: abstract droplet/world symbol + handwritten Chinese `序境` + refined Latin handwritten/script `LUMENIS`.
2. Korean logo: same symbol + independently designed Korean handwritten wordmark.
3. Clean symbol: symbol only.

Important distinction:

- brand wordmark may be expressive/handwritten;
- product UI typography remains highly readable and modern.

## 13.2 Dynamic color learning

The brand color is not locked to ordinary ocean blue or “eco green”.

Research-driven direction:

```text
transparent / clear mist
→ opal lilac
→ deep indigo
→ small cyan optical refraction
→ small pale-gold highlight
→ return to transparent/indigo core
```

Working palette:

```text
Clear Mist    #F6F8FF / translucent white
Opal Lilac    #B8A8FF
Deep Indigo   #2A2468
Aurora Cyan   #8BE7FF
Pale Gold     #F4D38A
Moon Silver   #DDE3F2
```

Reusable principle:

> A dynamic brand palette should have a stable semantic spectrum but can change emphasis across motion/context.

## 13.3 Short launch-motion learning

The full startup animation target is intentionally short, around 2.1 seconds:

```text
0.00–0.10  quiet field
0.10–0.35  small transparent droplet appears
0.35–0.72  droplet falls / gathers subtle color
0.72–1.02  impact / sea-horizon forms
1.02–1.38  contained world expands
1.38–1.78  world reconverges
1.78–2.10  logo locks / wordmark appears
2.10–2.30  optional handoff to product shell
```

The principle is reusable for content/video production:

```text
setup
→ transformation
→ peak
→ convergence
→ identity/action
```

Short product motion should communicate one idea, not become a showreel.

---

# 14. Reusable design-production pipeline

For future AI design/content work, the following process is recommended:

```text
CURRENT TRUTH
      ↓
REFERENCE RESEARCH
      ↓
CLEAN-ROOM ABSTRACTION
      ↓
DESIGN REGISTRIES
      ↓
COMPONENTS / MOTION / COPY
      ↓
INTERNAL CALIBRATION
      ↓
GENERATOR / TEMPLATE SYSTEM
      ↓
MULTI-SCREEN / MULTI-FORMAT OUTPUT
      ↓
AUTOMATED QUALITY CHECK
      ↓
ENGINEERING HANDOFF
      ↓
PRODUCTION BINDING
```

The goal is to spend human/AI attention on the **source of truth**, not manually reproduce 1,000 near-identical output files.

---

# 15. Reusable learning schema for LUMENIS AI

If these design studies are later turned into internal learning assets, store each learning unit with explicit fields such as:

```text
LearningAsset {
  id
  topic
  source_type
  source_url_or_internal_ref
  observed_problem
  observed_pattern
  extracted_principle
  state_model
  motion_model
  material_model
  accessibility_risk
  performance_risk
  legal_or_originality_boundary
  lumenis_equivalent
  prototype_evidence
  decision: ADOPT | REJECT | EXPERIMENT
  version
  reviewer
}
```

Do not train or teach an internal AI that “a successful design means copying the reference”. Teach it to recover the problem and design an original equivalent.

---

# 16. Research topics that can later support content creation

The same research can be reused beyond UI:

| Research concept | Content-creation equivalent |
|---|---|
| Point → Line → Surface → Screen | Detail → relationship → theme → narrative |
| Context → Evidence → Decision | Brief → source → point of view |
| Motion state transition | Story beat transition |
| Material hierarchy | Visual hierarchy in posters/video |
| Dynamic palette | Campaign mood progression |
| Artifact-first AI | Deliverable-first content workflow |
| Selection Context | Audience/topic/context filter |
| Evidence traceability | Claim/source linkage |
| Short launch animation | Short-form branded opener |
| Brand philosophy expansion/convergence | Campaign narrative arc |

This is why the asset is preserved as a research/learning file rather than only as a one-time UI specification.

---

# 17. Research source registry

Primary sources used in the 2026-09-11 Experience research:

```text
https://motionsites.org/
https://showreel.design/
https://reactbits.dev/
https://animejs.com/
https://ui.aceternity.com/
https://uiverse.io/
https://github.com/ybouane/liquidglass
https://liquid-glass.ybouane.com/
```

Internal source-of-truth references used alongside research:

```text
README.md
AGENTS.md
LUMENIS_NEW_PRODUCT_DESIGN_BASELINE_V1.md
00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md
00-GOVERNANCE/UNIFIED_UI_UX_INFORMATION_ARCHITECTURE_V1.md
templates/base.html
static/locales/zh-CN.json
static/locales/en.json
static/locales/ko.json
current templates/cth/**
current templates/zbmp/**
current templates/system/**
```

---

# 18. Final learning rule

```text
Research gives vocabulary.
Product truth gives constraints.
Design gives structure.
Motion gives continuity.
Evidence gives trust.
Engineering gives reality.
```

Never collapse those layers into one another.

Companion current-direction file:

- `00-GOVERNANCE/LUMENIS-EXPERIENCE-CURRENT-DIRECTION-READ-FIRST-20260911.md`

Companion canonical Experience design authority:

- `00-GOVERNANCE/LUMENIS-EXPERIENCE-DESIGN-AUTHORITY-V2-20260911.md`