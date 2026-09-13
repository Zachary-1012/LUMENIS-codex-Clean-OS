# LUMENIS / 序境 — Brand Ecosystem & Product Language Increment V1

> Status: **INCREMENTAL RESEARCH / DESIGN-LANGUAGE INPUT / NON-PRODUCTION-AUTHORITY**  
> Effective: **2026-09-11**  
> Repository: `Zachary-1012/LUMENIS-codex-Clean-OS`  
> Audit anchor at commit time: `f548669d82974ea065afb310776ec63935896d7d`  
> Original source document: `LUMENIS_品牌生态与产品语言_增量研究方案_V1_2026-09-11.docx`  
> Intended readers: Codex / Experience producer / Design engineer / Product owner

---

## 0. What this file is

This is an **incremental research asset** for the LUMENIS Experience layer.

It is **not**:

- Product Truth;
- a replacement for `README.md`, `AGENTS.md` or Production Acceptance;
- a replacement for `LUMENIS-EXPERIENCE-DESIGN-AUTHORITY-V2-20260911.md`;
- permission to redesign backend/API/DB/Runtime/Permission/Evidence;
- permission to copy third-party visual assets, UI code, SVGs, shaders, motion source, icons or branded compositions.

Its purpose is narrow:

> Study how brands with strong ecosystems create recognizable product/brand language, then translate the reusable mechanisms into original LUMENIS visual assets, UI grammar, iconography, wallpaper/background systems, motion and communication surfaces.

The intended result is **not a more fashionable SaaS UI**. The goal is for LUMENIS to become recognizable from its product language even when the logo is absent.

---

## 1. Codex read / authority order

When Codex later consumes this file, use the following order:

```text
Current verified source / runtime / data / permission / Evidence truth
> README / AGENTS / Production Acceptance / applicable governance
> LUMENIS Experience Design Authority V2
> Current Experience handoff / current implementation evidence
> THIS INCREMENTAL RESEARCH FILE
> external references / historical design material
```

If this document conflicts with verified Production Truth or newer canonical Experience authority, **the higher authority wins**.

Use this document to improve **how LUMENIS looks, feels, moves and communicates**, not to invent capabilities.

---

# 2. Research objective

LUMENIS should not become a conventional dashboard/SaaS product with a custom color palette.

The target is a system with:

- a recognizable product language;
- a reusable visual grammar;
- original icon and background/wallpaper systems;
- recognizable motion behavior;
- communication symbols that survive across Web, mobile, reports, exports, presentations and future public-facing products;
- an ecosystem feeling where CTH, BMP, AI and Shared Capability are different realms of one product, rather than unrelated applications.

Priority surfaces for this increment:

```text
Product icons
Wallpaper / hero / workspace background
Brand graphics
AI visual identity
Evidence / relationship visualization
Data visualization details
Empty / loading / state graphics
UI motion
Report / export / sharing assets
Public-facing product / marketing surfaces
```

---

# 3. Brand research → LUMENIS translation

| Brand / system | Mechanism worth learning | LUMENIS translation | Priority surfaces |
|---|---|---|---|
| **Apple** | Ecosystem consistency across devices; hierarchy, interaction and motion behave like one system. Motion is purposeful, concise, cancellable and supports reduced motion. | Create one cross-surface grammar for Web / mobile / reports / export / AI rather than separate visual systems. | Global layout, navigation, sheet/modal behavior, responsive rules, motion pacing, reduced motion |
| **Tesla** | UI continuously exposes real machine/system state. Visuals are coupled to actual state and control instead of being decorative. | Collector, Runtime, Evidence, Agent Task, Permission and Risk should have a real system-state language rather than generic SaaS status icons. | Runtime, monitoring, task state, status iconography, system pages |
| **Nothing** | Glyph is not decoration; it acts as a cross-device communication language using light/sound/haptics. | Build LUMENIS cross-interface symbols from `Point / Axis / Boundary / Trace`, repeated across iconography, wallpaper, Evidence and motion. | Icons, wallpaper, notifications, state symbols, mobile, transitions |
| **GitHub / Primer** | Product system and brand system remain distinct but coherent. Motion is categorized by why it exists rather than only by effect type. | Connect product, documentation, demonstrations and communication assets. Every motion pattern must have a semantic/business reason. | Design system, motion registry, iconography, documentation, demo/share assets |
| **IBM Carbon** | Enterprise design language is implemented through tokens, components, data viz, accessibility and engineering rules. | LUMENIS distinctiveness must be represented in executable tokens / components / DataViz / motion rules, not only in visual boards. | Tokens, component system, DataViz, A11y, engineering handoff |
| **Toss** | A design system serves an ecosystem by standardizing patterns, behavior and usability rather than merely visual style. | Different LUMENIS domains may have different density/character while controls, state, feedback and behavior remain one system. | Foundation components, forms, feedback, mobile, system governance |
| **Gentle Monster** | Brand world-building through spatial experience, scale, material, silhouette and deliberate asymmetry. The environment itself becomes part of the brand story. | LUMENIS wallpaper/background should feel like entering a “realm,” not a generic AI gradient. Different domains become different spaces in one world. | Wallpaper, login/launch, BMP, campaign/special pages, public site, large-screen presentation |
| **Tamburins** | Converts something invisible (scent) into spatial, sensory and narrative form. | Convert abstract LUMENIS concepts such as Evidence, Context and Insight into visible spatial/relational metaphors rather than relying only on tables. | Evidence UI, empty states, AI result, report covers, special experiences |
| **ADERERROR** | Post-minimal base with a controlled unexpected element: offset, scale break or unusual relationship. | Permit at most one intentional deviation per major workspace to create memory without reducing operational clarity. | Overview, Campaign, BMP, signature visual assets, high-impact transitions |
| **29CM** | Editorial and commerce coexist: narrative hierarchy and dense product metadata are not forced into the same card language. | Use two information densities: narrative/insight layer + factual/evidence layer. Reduce generic dashboard/card repetition. | BMP, Content Creation, reports, case library, major headings |
| **Teenage Engineering** | Color, graphic language and controls map directly to function. Brand character comes from interaction itself, not skinning. | LUMENIS icons, geometry and color must carry state/control meaning. Selection, trace, risk and running states should be structurally distinct. | Icon family, status controls, DataViz, AI tool surfaces, system pages |

---

# 4. LUMENIS visual-asset increment

This increment should primarily change the **asset layer and presentation language**, without forcing a product-architecture rewrite.

## 4.1 Wallpaper / workspace background

### Move away from

- generic AI nebula;
- generic aurora/glow;
- large decorative gradients;
- stock “futuristic” textures;
- unrelated decorative hero artwork.

### Move toward

A LUMENIS-native spatial field built from:

```text
Point
Axis
Boundary
Strata
Trace
Whitespace
Controlled deviation
```

Each major domain should feel like a different **realm** of the same world.

External learning:

- Gentle Monster → world-building / spatial identity;
- Tamburins → translating abstract concepts into sensory/visual space;
- ADERERROR → controlled unexpected detail.

Do not copy their specific spatial compositions or assets.

---

## 4.2 Product icon family

Build an original LUMENIS icon family.

Baseline system rules may remain conventional enough for usability:

```text
24 × 24 viewBox
consistent stroke family
consistent optical alignment
consistent corner and cap language
currentColor where appropriate
```

But core LUMENIS object icons may share one subtle signature feature:

- a `Point`;
- a `Boundary break`;
- a `Trace node`;
- a controlled axial relation.

Do not over-brand ordinary action icons such as Close/Search/Download.

External learning:

- Nothing → signature symbol can communicate state/function;
- Teenage Engineering → graphic form and function can map directly;
- GitHub → coherent product/brand icon families.

---

## 4.3 AI visual identity

Avoid converging toward the generic AI visual formula:

```text
orb + galaxy + aurora + constant glow
```

Working LUMENIS direction:

**Lumen Core**

Derived only from LUMENIS-native geometry:

```text
Point
+ Axis
+ Boundary curves
+ state density
```

The AI visual should change according to meaningful state rather than remaining an animated decorative sphere.

It may share a geometric ancestor with the LUMENIS brand philosophy, but should not simply paste the logo into the AI workspace.

---

## 4.4 Evidence / relationship visual language

LUMENIS has a product-native advantage: Evidence and traceability are real product concepts.

Use this to create a distinctive visual language:

```text
Claim
→ Trace
→ Evidence
→ Canonical / Original Source
```

Recommended semantic rule:

- neutral relation = silver/structural;
- selected/verified/actively traced relation = restrained Icy Cyan;
- risk/error state uses semantic risk colors;
- AI should not automatically equal cyan.

This turns Evidence traceability into an ownable product signature instead of a generic decoration.

---

## 4.5 Surface model

Reduce the feeling that every object must be inside a card.

Prefer:

```text
Axis
Boundary
Spacing
Typography
Strata
Trace
```

to organize ordinary data groups.

Use stronger physical surfaces for high-responsibility content such as:

- Artifact;
- Evidence;
- Form;
- Modal / Drawer / Sheet;
- Composer;
- high-responsibility editable or auditable content.

This moves LUMENIS gradually from a generic **Card System** toward a more distinctive **Field System** without sacrificing readability.

External learning:

- Apple → hierarchy before decoration;
- 29CM → editorial and factual density coexist;
- Toss → usability remains primary.

---

# 5. Six LUMENIS communication primitives

These primitives are recommended as a reusable LUMENIS visual/motion grammar.

| Primitive | Product meaning | Static expression | Motion expression |
|---|---|---|---|
| **Point · 点** | Minimum real object: Evidence / Event / Metric / Subject | node, selection point, source point | appear, touch, return-to-point |
| **Axis · 序轴** | Context / Time / Workflow order | primary alignment line / structural axis | context converges then unfolds |
| **Boundary · 界** | Scope / Permission / Selection / Context | open boundary / bracket / local contour | touch boundary, open realm, close |
| **Strata · 层** | L0–L3 information depth | whitespace, hierarchy, material/depth progression | detail opens while preserving source continuity |
| **Trace · 迹** | Claim → Evidence → Source | thin silver line / active Icy trace | path draws from conclusion to evidence |
| **Return · 归点** | Completion / convergence / return to source | source node / central marker | expanded artifact/workspace converges back to origin |

These primitives should eventually be recognizable across:

```text
UI
Motion
Data visualization
Evidence
AI
Reports / export
Sharing assets
Public-facing experience
```

---

# 6. Domain dialects: one language, different realms

Do not make each domain a separate design system.

Use one grammar with different dialects:

| Domain | Dialect | Wallpaper / background direction | Primary memory |
|---|---|---|---|
| **CTH — Commerce Operations** | Operational Realm: higher density, stronger order, trace-heavy | structural field + Evidence Trace + minimal optical material | fact → evidence → action path |
| **BMP — Brand & Market** | Editorial Realm: larger whitespace, stronger media/story rhythm | open layout + controlled large-scale graphic + boundary cuts | editorial intelligence + cultural/market feeling |
| **AI** | Intent Realm: intent/state/artifact transition is primary | Lumen Core + state density + controlled boundary opening | intent → task → artifact continuity |
| **Shared Content** | Studio Realm: content owns the stage, tools recede | near-white/open field + editorial axis + contextual Evidence | creation and Evidence coexist without clutter |

Domain differentiation should come from task character and information density, not simply “CTH blue / BMP purple.”

---

# 7. Motion increment

Existing engineering motion IDs may remain.

The design-language increment is to define a recognizable set of **brand verbs** above them:

```text
Touch
Open
Trace
Shift
Settle
Return
```

Suggested semantic behavior:

### Touch

A point/object activates a nearby boundary or relationship.

### Open

One object preserves identity while becoming a larger workspace/detail state.

### Trace

A visible path connects a finding/metric/event to Evidence/source.

### Shift

Old Context converges and new Context unfolds from a shared origin.

### Settle

A completed action loses kinetic energy and locks into a stable state.

### Return

An expanded workspace/artifact converges back to the source point/object.

Rules:

- business/data state > interaction state > decoration;
- one dominant motion at a time;
- no meaningless perpetual loops;
- no fake thinking/progress;
- interruptible/cancellable where applicable;
- reduced-motion support required;
- signature must remain understandable without color.

External learning:

- GitHub → motion has a reason;
- Apple → motion is purposeful, concise and optional/reducible;
- Nothing → recurring behavioral signal becomes part of brand identity.

---

# 8. Controlled deviation

LUMENIS can use a limited “unexpected” device to avoid becoming sterile enterprise software.

Rule:

> Each primary workspace may contain **at most one intentional deviation**.

Examples:

- one off-axis Insight;
- one oversized Evidence identifier;
- one cross-grid Trace;
- one deliberately open/broken Boundary;
- one detached primary metric.

The deviation must have a semantic reason.

Do not use random asymmetry or fashion decoration.

This idea is inspired by the mechanism observed in ADERERROR / Gentle Monster, but the final form must be original LUMENIS work.

---

# 9. External-reference rule

Research references are for mechanism learning only.

Allowed process:

```text
Reference
→ Observation
→ Principle
→ LUMENIS hypothesis
→ Original prototype
→ Test
→ Evidence
→ Design decision
→ Implementation contract
```

Forbidden:

- copying product UI source;
- importing third-party icons/SVGs;
- copying branded wallpaper/backgrounds;
- tracing external brand compositions;
- copying motion source/shaders;
- using external screenshot fragments as production assets;
- renaming/recoloring external code and shipping it.

Current LUMENIS rule remains stricter than normal license permission: **new production-visible design/code/assets should be self-developed.**

---

# 10. Codex implementation interpretation

When Codex later integrates or reviews Experience work, interpret this file as follows.

## Codex SHOULD

- preserve real capability/state/Evidence semantics;
- verify that new visual assets remain original;
- verify that Point / Axis / Boundary / Strata / Trace / Return are used coherently when promoted into production;
- bind Evidence/State/Action visuals to real backend truth;
- preserve responsive, accessibility and reduced-motion requirements;
- treat visual/motion language as reusable system rules instead of one-off screen decoration;
- ensure brand-language changes do not require machine ID / API / DB / permission changes.

## Codex MUST NOT

- invent backend behavior to satisfy the visual concept;
- treat this research file as proof that a feature exists;
- treat an attractive prototype as Production Ready;
- copy third-party brand assets because they appear in the research table;
- redesign Product Truth around this visual language;
- override newer canonical Experience authority.

---

# 11. Success condition

The increment succeeds when LUMENIS can increasingly pass these tests:

### No-logo recognition

Remove the logo/brand name from representative screens. The information hierarchy, geometry, icon family, Evidence relations and motion rhythm should still feel related and recognizable.

### Cross-surface recognition

Web UI, mobile, reports, exports, sharing cards and public-facing presentation should feel like one ecosystem rather than independent graphic projects.

### Domain-family recognition

CTH / BMP / AI / Shared Content may have different density and visual dialect, but should unmistakably belong to one system.

### Truth preservation

Distinctiveness must never weaken Evidence, State Source, Permission, Action Contract, accessibility or production truth.

---

# 12. Final statement

```text
LUMENIS does not need to look like Apple, Tesla, Nothing,
Gentle Monster, Tamburins, ADERERROR, 29CM or Teenage Engineering.

It should learn how those ecosystems turn a small set of principles
into recognizable products, spaces, motion and communication.

For LUMENIS, the ownable source is already inside the product:
Context, Evidence, Boundary, Trace, Decision, Action, Return.

The objective is to turn those truths into a coherent product language.
```
