# LUMENIS Experience Design Authority V2

> Status: **CANONICAL / P0 EXPERIENCE DESIGN AUTHORITY**  
> Effective: 2026-09-11  
> Scope: every user-visible and user-operable LUMENIS production experience: Web, responsive desktop/tablet/mobile, navigation, components, data visualization, Evidence presentation, AI workspace, motion, material, brand identity, launch animation, copy and visual handoff.  
> Repository: `Zachary-1012/LUMENIS-codex-Clean-OS`

---

# 0. Authority boundary

This document is the highest current authority for **Experience presentation and interaction execution**.

It does not own or override Production Truth.

Authority order:

```text
Current verified source / runtime / data / permission / Evidence truth
> README / AGENTS / Production Acceptance / applicable product governance
> THIS EXPERIENCE DESIGN AUTHORITY
> current Experience handoff/specification
> research/learning assets
> legacy UI / historical design docs / historical chat
```

When visual/interaction guidance in an older UI/UX document conflicts with this document, this document governs the **new production presentation**.

In particular, older reuse-first UI wording must not be interpreted as permission to inherit legacy visual implementation. Existing capability must be preserved, but new Production Experience must be rebuilt under this authority.

This document does not authorize changing backend/API/DB/Permission/Runtime/Canonical Data/Evidence to make a visual design easier.

---

# 1. Product identity

Mother product:

| Layer | Chinese | English | 한국어 | Stable technical identifier |
|---|---|---|---|---|
| Mother | 序境 | LUMENIS | 서경 | repository / product core |
| CTH | 序境·商业运营 | LUMENIS Commerce Operations | 서경·커머스 운영 | `cth` |
| BMP | 序境·品牌市场 | LUMENIS Brand & Market | 서경·브랜드 & 마켓 | `zbmp` / BMP compatibility |
| Shared Content | 序境·内容创作 | LUMENIS Content & Creation | 서경·콘텐츠 & 크리에이션 | Shared Capability |
| SYSTEM | 系统 | System | 시스템 | `system` |

Only CTH and BMP are business product lines.

Shared Capability, SYSTEM, AI, Agent Groups, Research, Browser and Command are supporting/cross-product capabilities, not new product lines.

---

# 2. Product philosophy and Experience philosophy

Brand philosophy:

**芥子纳须弥**

Experience interpretation:

> A small, real and verifiable point can reveal a larger structure; every larger conclusion must still be able to return to its original evidence.

Experience chain:

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

Production truth remains:

```text
External Data
→ Evidence
→ Canonical Data
→ Function
→ Metric
→ Truth Table
→ View Model
→ Visualization
→ UI / Report / Export
```

Business intelligence remains:

```text
Source
→ Evidence
→ Event
→ Case
→ Finding / Insight
→ Decision
→ Action
→ Outcome
→ Evaluation / Feedback
→ Learning Asset
```

The UI is a view over these chains, never a replacement for them.

---

# 3. New Experience implementation rule

## 3.1 Legacy capability may survive; legacy visual implementation may not

```text
Legacy source
   ↓
Capability Inventory
   ↓
Dependency / State / Permission / Evidence mapping
   ↓
New ViewModel Contract
   ↓
NEW EXPERIENCE
```

Forbidden as the new production visual implementation basis:

- existing `templates/base.html` visual stack
- old page markup copied as a starting layout
- old zbc/xujing/adaptive/lumenis visual CSS imports
- old dashboard/card/table/navigation appearance
- old visual motion engines as design authority
- broad legacy class inheritance
- `!important` overlay strategy to force the new design over old CSS

## 3.2 Isolated Experience zone

Target new Experience root:

```text
experience_v2/**
```

Root namespace:

```text
.lum-app
```

Presentation namespace:

```text
lum-*
--lum-*
```

During Doubao Experience production, `experience_v2/**` is the only write area. The rest of the repository is read-only for capability mapping.

## 3.3 Target prototype stack

```text
HTML
CSS
Vanilla JavaScript / ES Modules
Jinja-friendly component/screen skeletons
```

No React/Vue migration may be introduced solely for design effects.

---

# 4. Global Subject Context

CTH and BMP both use a compatible global **Selected Subject** context.

```text
Selected Subject
→ Domain Lens
→ Scope / Permission
→ Query / Function / Metric
→ ViewModel
→ UI / Report / Export
```

Experience must not build unrelated CTH and BMP subject-selector infrastructures.

CTH and BMP differentiation comes from:

- Domain Lens
- metrics
- object relationships
- capability composition
- decision/action chain

The UI may define a normalized presentation contract, but real SubjectContext fields and permission behavior remain backend-owned and must be re-audited by Codex.

---

# 5. Information architecture

## 5.1 Point → Line → Surface → Screen → Workflow

```text
POINT
Subject / Brand / Metric / Creator / Content / Event / Evidence / Task

        ↓ relationship

LINE
Metric → Evidence
Event → Content
Finding → Evidence
Decision → Action
Action → Outcome

        ↓ representation

SURFACE
Metric Card / Trend / Timeline / Evidence Preview / Artifact / Action

        ↓ one primary question

SCREEN
Context + Decision + Analysis + Evidence + Action

        ↓ continuous work

WORKFLOW
Observe → Understand → Decide → Create/Act → Measure → Evaluate → Learn
```

## 5.2 Maximum information depth

Default hierarchy:

```text
L0 Context
L1 Decision View
L2 Analysis
L3 Evidence / Detail
```

Use 2–4 levels depending on task complexity. Do not add navigation depth merely because more data exists.

## 5.3 First-screen priority

Every main workspace should answer:

```text
What happened?
→ Why?
→ What proves it?
→ What can I do?
```

Do not create KPI walls that lack explanation and action.

---

# 6. Global application shell

## 6.1 Desktop

```text
┌─────────────────────────────────────────────────────────────────┐
│ Context Bar: Subject · Domain · Time · Freshness · Selection   │
├────────┬──────────────────────────────────────────┬─────────────┤
│ Nav    │ Main Workspace                           │ Context Rail│
│        │ Context → Decision → Analysis → Evidence │ on demand   │
└────────┴──────────────────────────────────────────┴─────────────┘
```

Navigation defaults to a compact rail and may be pinned expanded. Avoid involuntary full-layout expansion on casual hover.

## 6.2 Context Rail

The right side is contextual, not a permanent Browser column.

Possible rail content:

- Evidence
- Browser / source research
- Trace
- Properties
- AI detail
- comments/metadata if later verified

If no contextual rail is useful, the workspace may occupy the width.

## 6.3 Mobile

```text
Workspace
+ Bottom Dock
+ Bottom Sheet
+ Safe-area Composer when applicable
```

Mobile is a recomposed interface, not a scaled desktop.

---

# 7. Responsive authority

Validation widths:

```text
1920
1440
1280
1024
768
430
390
360
```

Required semantic recompositions:

```text
Context Rail:
right rail → drawer → bottom sheet

Navigation:
rail → compact → bottom dock

Table:
full table → reduced columns → structured list → data card

Composer:
centered/docked → bottom safe-area composer

Filters:
inline → condensed control → sheet
```

Text must be tested with Chinese, English, Korean and approximately 130% text expansion.

---

# 8. Naming and copy authority

## 8.1 Three-layer naming

```text
Machine ID        stable
Semantic Copy Key stable
Display Value     replaceable
```

Example:

```text
cth
→ domain.cth.name
→ 序境·商业运营
```

Changing the visible product name must not require changing:

- routes
- API identifiers
- DB fields
- permission keys
- Agent contracts
- machine IDs

## 8.2 Product copy vs business data

Product copy goes through the copy/i18n registry:

- navigation
- page titles
- buttons
- tabs
- labels
- tooltips
- placeholders
- empty/error/status messages
- accessibility labels
- fixed AI UI prompts/controls

Business data does not belong in locale files:

- Subject display name
- Brand name
- Campaign name
- Event name
- post/content title
- Evidence content
- user input

Current production locales are not modified by Doubao; Experience V2 provides deltas/registries for Codex integration.

---

# 9. Typography authority

## 9.1 Product UI typography

Product UI prioritizes readability and multilingual stability.

Recommended runtime stack:

```text
system-ui,
-apple-system,
BlinkMacSystemFont,
Segoe UI,
PingFang SC,
Microsoft YaHei,
Apple SD Gothic Neo,
Malgun Gothic,
sans-serif
```

Code/trace:

```text
ui-monospace, SFMono-Regular, Consolas, Liberation Mono, monospace
```

Suggested hierarchy:

| Style | Size / Line height | Weight | Use |
|---|---:|---:|---|
| Display | 40 / 48 | 650 | rare AI/brand hero |
| H1 | 28 / 36 | 650 | workspace title |
| H2 | 22 / 30 | 650 | major section |
| H3 | 18 / 26 | 600 | component group |
| Body L | 16 / 24 | 400 | artifact summary |
| Body | 14 / 22 | 400 | default text |
| Dense | 13 / 20 | 450 | table/data |
| Label | 12 / 18 | 600 | controls |
| Caption | 11 / 16 | 450 | metadata |
| KPI | 32 / 38 | 650 | primary metrics |

## 9.2 Brand wordmark exception

The **logo wordmark**, unlike product UI text, should use custom/original handwritten forms:

- Chinese `序境`: refined handwritten mark; fluid, restrained, recognizable; not wild calligraphy or nostalgic brush styling.
- English `LUMENIS`: refined Latin handwritten/script mark; elegant and flowing; not wedding-script sweetness or ornate retro lettering.
- Korean: separately designed Korean handwritten wordmark, preserving Korean legibility and the same family rhythm rather than imitating Chinese strokes literally.

Brand wordmark art should be original vector lettering rather than relying on a redistributable font file.

---

# 10. Color authority

## 10.1 Experience UI base palette

Working semantic palette for Experience V2:

| Token | Light | Dark | Role |
|---|---|---|---|
| canvas | `#F5F7FB` | `#0D1117` | page field |
| surface | `#FFFFFF` | `#141A23` | Truth Surface |
| surface.subtle | `#EFF2F7` | `#1A2230` | secondary zone |
| surface.raised | `#FBFCFE` | `#202A38` | elevated zone |
| text.primary | `#131722` | `#F4F7FB` | primary text |
| text.secondary | `#586174` | `#B3BECE` | secondary text |
| text.tertiary | `#7A8498` | `#8893A6` | metadata |
| border | `#DDE3EC` | `#2A3443` | structural border |
| accent.primary | `#5B4FE9` | `#8D83FF` | primary active/AI accent |
| accent.secondary | `#0F766E` | `#45C7B7` | secondary emphasis |
| positive | `#16835D` | `#43C68B` | positive state |
| warning | `#A86300` | `#F0B45B` | warning |
| critical | `#C33F4A` | `#FF7A85` | critical/error |
| info | `#2E64C7` | `#79A7FF` | information |
| unknown | `#6D778A` | `#9BA6B8` | unknown |

Color must communicate only:

```text
Identity / State / Data / Emphasis
```

Do not add gradients/glow merely to fill visual emptiness.

## 10.2 Brand/logo dynamic spectrum

The brand identity is deliberately more fluid than ordinary product UI color.

Approved working spectrum:

```text
Clear Mist      #F6F8FF / translucent white
Opal Lilac      #B8A8FF
Deep Indigo     #2A2468
Aurora Cyan     #8BE7FF  limited optical accent
Pale Gold       #F4D38A  limited warm highlight
Moon Silver     #DDE3F2
```

The logo/launch color may shift through this spectrum dynamically. It must not be reduced to generic ocean blue or ecological green.

---

# 11. Spacing, shape and elevation authority

Recommended spacing scale:

```text
4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64 px
```

Control heights:

```text
32 compact
40 default
48 touch-primary
```

Radius:

```text
control 10
card 16
panel 20
hero/optical 24
pill 999
```

Rounded geometry is a system, not permission to make every surface a pill.

Shadows remain shallow. Depth should come from hierarchy, spacing, surface separation and controlled material before large drop shadows.

---

# 12. Material authority

## 12.1 Tier A — Truth Surface

Use for:

- Evidence
- table
- report
- analysis
- long text
- editor
- form
- audit
- runtime

Properties:

- opaque
- stable
- highly readable
- no optical distortion behind content

## 12.2 Tier B — Spatial Surface

Use for:

- KPI
- Context
- filters
- selectors
- popovers
- summary cards
- floating support panels

Properties:

- controlled transparency
- subtle blur/depth
- shallow shadow

## 12.3 Tier C — Optical Surface

Use only for:

- AI Composer
- active navigation/dock bubble
- capability/task morph surface
- transient tool dock
- rare special selector/control

Optical rendering must be self-developed for LUMENIS. External liquid-glass code/shaders are research only.

Text/icons remain semantic HTML/SVG layers; optical Canvas/WebGL should be behind them rather than rasterizing critical text.

Fallback:

```text
Optical → Soft Glass → Opaque
```

No capability may disappear when GPU/optical rendering is unavailable.

---

# 13. Component authority

The component system must cover at least:

## Foundation controls

- Button
- Icon Button
- Link
- Input
- Textarea
- Search/Combobox
- Select / Multi-select
- Checkbox / Radio / Switch
- Date / Range
- Segmented Control / Tabs
- Tooltip / Popover / Menu
- Dialog / Confirm
- Drawer / Sheet
- Toast / Banner
- Dropzone / File queue

## Business/data surfaces

- Context Card
- Metric Card
- Event Card
- Risk Card
- Evidence Card
- Case Card
- Creator Card
- Campaign Card
- Artifact Card
- Action Card
- Timeline
- Progress
- Table/List/Grid
- Visualization containers
- Report sections
- Upload pipeline

## AI

- Capability Cards
- Composer
- Context chips
- Task Header
- Task Stage Progress
- Approval state
- Artifact workspace
- Evidence rail integration
- Trace view on demand

Every applicable component must define:

```text
Default
Hover
Focus Visible
Pressed
Selected
Loading
Disabled
Empty
Updating
Partial
Stale
Degraded
Blocked
Error
Offline
Permission Denied
```

N/A states require an explicit reason rather than silent omission.

---

# 14. Icon authority

Formal interface icons:

```text
24 × 24 viewBox
1.5–2px stroke family
round cap / round join
currentColor
optically aligned
```

Families:

- object: Subject / Brand / Event / Evidence / Report / AI / Collector / Database / Task
- action: Search / Filter / Add / Export / Open / Close / Send / Refresh / Download
- status: Positive / Warning / Critical / Blocked / Partial / Running / Unknown

No emoji as formal product-control icons.

Final visual icon assets must be self-developed for the new Experience or deliberately promoted original internal assets after review; do not import reference-library icons as a shortcut.

---

# 15. Motion authority

Motion priority:

```text
business state
> data state
> interaction state
> decoration
```

Motion levels:

```text
Micro          80–180 ms
Component      180–280 ms
Layout         260–420 ms
Workspace      320–520 ms
Special        normally <=650 ms
```

Canonical motion IDs:

| ID | Meaning |
|---|---|
| M01 | App Shell Reveal |
| M02 | Nav Active Travel |
| M03 | Context Change |
| M04 | Card → Workspace Morph |
| M05 | Capability → Task |
| M06 | Task Stage Progress |
| M07 | Artifact Reveal |
| M08 | Evidence Preview → Rail |
| M09 | Drawer / Bottom Sheet |
| M10 | Segmented Travel |
| M11 | Calendar Selection |
| M12 | Upload Pipeline |
| M13 | Success Resolution |
| M14 | Error / Recovery |
| M15 | Composer State |

Motion requirements:

- event/state driven
- interruptible/cancellable
- reduced-motion supported
- no fake business/runtime progress
- no constant glow merely to signal “AI”
- source must be reproducible; MP4/GIF preview is not sufficient by itself

---

# 16. Data visualization authority

Visualization hierarchy:

```text
Primary Metric
→ Trend
→ Composition / Driver
→ Detail
→ Evidence
```

Interactions as appropriate:

- hover nearest datum
- click select/filter
- drill-down
- brush/range
- legend filter
- cross-highlight
- Evidence jump

Selection must propagate through a shared Selection Context where the product capability supports it.

Charts must communicate without relying on color alone.

Visualization is a View + Controller, not a static image.

---

# 17. Evidence and artifact authority

Evidence is a first-class experience object.

Presentation chain:

```text
Claim
↔ Evidence Marker
↔ Evidence Preview
↔ Evidence Detail
↔ Canonical/Original Source
```

Important findings and consequential actions should be traceable.

AI/analysis results should form real artifacts where appropriate:

```text
Artifact
├── Summary
├── Metric
├── Visualization
├── Finding / Drivers
├── Evidence
├── Recommendation
└── Actions
```

Artifact claims and Evidence should support bidirectional highlighting/jump where possible.

---

# 18. AI Experience authority

Current GPT-style three-pane UI is not the future visual authority.

Target states:

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

## AI Home

- current Context visible
- identity/greeting restrained
- 4–6 highest-value contextual capability cards
- Composer

Capability suggestions should ultimately resolve from real:

- domain
- selected subject
- current page
- Evidence
- recent events
- pending actions
- user permission

If capability availability is not verified, the Experience prototype may simulate it only as `DESIGN_ONLY`, while Codex integration must hide/disable/resolve according to the real capability state.

## AI Working

Must show real task state, not entertainment animation.

## AI Result

Artifact-first. Chat history becomes secondary context rather than the only result container.

---

# 19. Capability / State / Action truth rules

## 19.1 Capability state

Allowed statuses:

```text
VERIFIED_AVAILABLE
VERIFIED_UNAVAILABLE
PARTIAL
UNKNOWN
BLOCKED
CODEX_BINDING_REQUIRED
```

Unknown capability must not appear as a guaranteed production action.

## 19.2 State source

Every meaningful state should declare its source:

```text
backend
frontend-derived
user-input
DESIGN_ONLY fixture
```

## 19.3 Action contract

Every consequential interactive action should define:

```text
action_id
display_key
capability_status
permission_requirement
input_context
success_state
failure_state
evidence_effect
binding_owner
```

Designing a button does not grant permission to execute the action.

---

# 20. Screen registry authority

The Experience production specification established 44 numbered experience screens:

```text
ACC    4
CTH   10
BMP   11
AI     5
SYSTEM 8
SHARED 6
TOTAL 44
```

These are Experience specification units, not proof of 44 backend endpoints.

The existing detailed master plan supplied to the Experience producer remains the screen-by-screen implementation blueprint.

This authority controls how those screens are built and how future screens must be added.

---

# 21. Internal calibration rule

Do not create repeated user-approval loops during bulk Experience production.

Internal calibration uses:

```text
AI-01 Home
+
CTH-01 Overview
```

These two screens validate complementary qualities:

- AI-01: Shell / capability cards / Composer / Optical / M05 / M15 / progressive reveal / mobile dock
- CTH-01: Truth surface / KPI / trend / data density / Evidence / Selection / Rail / responsive behavior

If automated/internal quality gates pass, production continues through the remaining screens without waiting for another user design round.

---

# 22. Brand logo authority

## 22.1 Brand concept

The primary logo metaphor is:

**an abstract optical/liquid droplet containing a sea/horizon/world.**

It translates **芥子纳须弥** as:

```text
one small point
→ contains / reveals a larger world
→ expands
→ reconverges
→ returns to one identifiable symbol
```

Do not create:

- a generic water-company droplet
- cartoon waves
- an environmental/eco-leaf identity
- generic blue-green ocean branding
- excessive neon/cyber glow

## 22.2 Logo structure

- outer form: refined liquid droplet / seed / world-container hybrid
- internal horizon: abstract liquid sea/horizon, not literal waves
- small optical nucleus/highlight: origin point / “seed”
- depth: front/mid/back optical layering without sacrificing small-size recognition

## 22.3 Three official logo versions

### A — Standard

```text
Symbol
+
custom handwritten Chinese “序境”
+
custom refined Latin handwritten/script “LUMENIS”
```

This is the primary identity.

### B — Korean

```text
Symbol
+
independently designed Korean handwritten wordmark
```

Do not simply substitute system Korean text inside the Chinese/Latin lockup. The Korean version needs its own typographic balance while preserving the family identity.

### C — Clean symbol

```text
Symbol only
```

Used for app icon, favicon, compact control, icon-only launch/transition and places where the wordmark would be illegible.

## 22.4 Brand color behavior

The brand logo is allowed to be dynamic within the approved spectrum. The structural silhouette stays recognizable while optical color emphasis may move.

Color progression may begin nearly transparent, develop lilac/indigo/cyan/gold optical accents and settle into a controlled final identity.

---

# 23. Launch animation authority

The launch animation begins from the logo philosophy, not from a generic loading spinner.

## 23.1 Full version

Target duration: approximately **2.1 seconds**; acceptable range about **1.8–2.4 seconds**.

Storyboard:

```text
S0  quiet transparent/mist field
S1  tiny optical droplet appears above
S2  droplet falls; subtle spectrum gathers
S3  impact creates abstract sea/horizon
S4  sea/world expands briefly into spatial depth
S5  expanded world reconverges toward the center
S6  final logo symbol locks; wordmark appears where applicable
S7  transition into the product shell
```

Working timing:

| Stage | Approx. time |
|---|---:|
| quiet | 0.00–0.10 s |
| droplet appear | 0.10–0.35 s |
| fall | 0.35–0.72 s |
| impact / horizon | 0.72–1.02 s |
| world expand | 1.02–1.38 s |
| reconverge | 1.38–1.78 s |
| logo lock | 1.78–2.10 s |
| optional shell handoff | 2.10–2.30 s |

## 23.2 Three animation variants

1. Standard animation → ends in Standard Chinese + Latin logo.
2. Korean animation → ends in Korean logo.
3. Clean animation → ends in symbol only.

## 23.3 Short version

A **0.6–0.9 s** shortened brand motion should exist for re-entry/lightweight scenarios.

## 23.4 Runtime behavior

- launch animation must not block network/data loading;
- normal product shell preparation can occur in parallel;
- reduced-motion or low-performance mode may show the static corresponding logo and enter directly;
- the animation is brand identity, not proof of runtime readiness;
- no fake loading percentage inside the brand animation.

---

# 24. Originality authority

All new production-visible Experience code/assets produced under this authority must be self-developed.

External sites/repositories are for research only.

Forbidden runtime shortcuts:

- importing React Bits/Aceternity/Uiverse UI code
- copying liquid-glass shaders
- copying external icons or motion assets
- using screenshot fragments as production assets
- using an external brand lockup as a base trace

Maintain research/source provenance separately from production asset provenance.

---

# 25. Experience-to-Codex handoff authority

The Experience producer must give Codex **ports**, not screenshots only.

Required conceptual boundary:

```text
Visual / UX / Motion / Copy / Components
                ↓
      Frontend Contract Ports
      ├── ViewModel Port
      ├── Capability Port
      ├── State Port
      ├── Action Port
      ├── Permission Port
      └── Evidence Port
                ↓
          CODEX BINDING
                ↓
      Current Production Truth
```

Codex must re-audit the repository at integration time.

Unknown backend bindings remain `UNKNOWN` until verified.

Design fixtures must be removed/replaced from the production path.

---

# 26. Experience acceptance gates

A new Experience package cannot be marked complete merely because it looks good.

Blocking Experience gates:

1. new visual implementation does not inherit legacy visual CSS/layout;
2. new production-visible UI code/assets are self-developed;
3. required screens/components/states exist;
4. responsive target widths are validated;
5. zh-CN / en / ko keys and text expansion are checked;
6. meaningful states have explicit source contracts;
7. unknown backend actions are not faked;
8. motion is source-reproducible and reduced-motion compatible;
9. optical rendering has non-GPU fallbacks;
10. accessibility critical issues are resolved;
11. visual regression baselines exist;
12. Design Fixtures are explicitly marked and have a replacement list;
13. Codex integration manifest/bindings exist;
14. Experience build does not modify backend/current production assets outside its authorized write zone.

Experience completion status is:

```text
DOUBAO_FRONTEND_HANDOFF = COMPLETE
```

This is **not** equivalent to:

```text
PRODUCTION_READY
RELEASED
OPERATING
```

Production status remains governed by the repository Production Acceptance system.

---

# 27. Supersession / compatibility note

This document is additive to product/data/security/runtime truth, but it supersedes earlier presentation guidance where those documents would cause the new Experience to inherit or visually reuse legacy UI.

In particular:

- preserve existing capability semantics;
- do not preserve old visual implementation merely for compatibility;
- adapters may be used for real existing backend behavior;
- new UI/CSS/layout/motion should be isolated and rebuilt;
- retire old production routes/UI only after Codex completes real binding, E2E and migration verification.

---

# 28. Companion records

Current direction / process state:

- `00-GOVERNANCE/LUMENIS-EXPERIENCE-CURRENT-DIRECTION-READ-FIRST-20260911.md`

Reusable research/learning:

- `00-GOVERNANCE/LUMENIS-EXPERIENCE-RESEARCH-LEARNING-ASSET-V1-20260911.md`

Existing product constitution remains relevant:

- `LUMENIS_NEW_PRODUCT_DESIGN_BASELINE_V1.md`
- `README.md`
- `AGENTS.md`
- `00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md`

---

# 29. Final canonical statement

```text
Production Truth defines what is real.
The Experience Authority defines how people see, understand and operate it.
Research teaches possibilities but owns neither truth nor design.

Legacy capability may be recovered.
Legacy visual implementation is not the new production UI.

Context makes data meaningful.
Evidence makes conclusions trustworthy.
Motion makes state changes understandable.
AI turns intent into tasks and artifacts.
Design makes the whole chain usable.
```
