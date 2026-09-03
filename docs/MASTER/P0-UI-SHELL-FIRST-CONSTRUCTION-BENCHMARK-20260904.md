# P0 UI SHELL FIRST — CONSTRUCTION BENCHMARK

Status: LOCKED / ACTIVE
Priority: P0

## 1. Core correction
The global UI layout and interaction shell must be built **before** feature implementation is considered complete. This is not a final cosmetic layer. It is the testable application surface through which every subsequent capability is plugged in.

Daily development must remain testable through a real running interface. A backend capability without an accessible UI route/state is not considered fully testable for the product workflow.

## 2. Construction order
```text
P0 — Global UI Shell / Navigation / Layout / Route State / Window System
                         ↓
P0 — Shared Design Tokens / Responsive Rules / Component Contracts
                         ↓
P0 — Empty-State / Loading / Error / Permission / Data-State surfaces
                         ↓
P0 — Platform Shell contracts (Web / Desktop / Mobile / Mini Program)
                         ↓
P1 — Fill confirmed business functions into the shell
                         ↓
P1 — Connect ingestion / canonical tables / dynamic visualizations
                         ↓
P1 — Connect AI / workflows / reports / exports
                         ↓
P1 — Daily regression and acceptance
```

Feature work does not wait for a “finished visual redesign”; it plugs into the already-running shell through defined routes and components.

## 3. Platform identity
The upper platform name is **序境** (Chinese: 序境; meaning derived from the concepts of order and realm/context). Do not use the old incorrect platform naming in new product-facing UI specifications. Product/module names remain governed by their canonical repository definitions.

## 4. Final parent/child model
```text
序境
└── ZBP / 母系统
    ├── Shared Platform
    ├── CTH / 子系统
    │   └── ALL CONFIRMED CURRENT CTH FUNCTIONS
    ├── KOS / KOC / UGC capability domain
    └── Podcast complete attached system
```

CTH remains a real product surface from the first UI-shell build. It is not a future placeholder. Its existing capabilities must have corresponding routes/pages/states so they can be tested continuously.

ZBP and CTH are developed toward a joint completion state. CTH is the first feature-development/validation environment; ZBP is simultaneously constructed as the parent platform and final integration surface.

## 5. UI shell
Reference the clean workspace structure users already respond well to: persistent left navigation, central work surface, optional contextual right panel. This is a layout principle, not a visual copy of another product.

```text
┌────────────────────────────────────────────────────────────────────┐
│ 序境 Header                                                       │
│ product context | global search | command | tasks | status | user │
├──────────────┬───────────────────────────────────┬─────────────────┤
│ LEFT NAV     │ MAIN WORKSPACE                    │ CONTEXT PANEL   │
│              │                                   │                 │
│ 序境          │ current Product / Domain         │ selected object │
│ ├ ZBP         │ current Module                   │ evidence        │
│ │ ├ CTH       │ current Page                     │ filters         │
│ │ ├ KOS...    │ sections                         │ related objects │
│ │ └ Podcast   │ tables / charts / content        │ actions         │
│ ├ Workspace   │                                   │                 │
│ ├ Data        │                                   │                 │
│ ├ AI          │                                   │                 │
│ └ Settings    │                                   │                 │
├──────────────┴───────────────────────────────────┴─────────────────┤
│ optional task/activity/status strip                               │
└────────────────────────────────────────────────────────────────────┘
```

## 6. Hierarchy
```text
序境 Platform
  ↓
ZBP / Product
  ↓
Domain / CTH / KOS / Podcast
  ↓
Module
  ↓
Page
  ↓
Section
  ↓
Component
  ↓
Window / Drawer / Modal
  ↓
Action
```

Navigation, windows and deep links must preserve this hierarchy.

## 7. Daily-test requirement
Every implemented feature must be testable through the shell:

```text
Feature
 ↓
Route
 ↓
Visible Page State
 ↓
User Action
 ↓
Data / Function
 ↓
Result
 ↓
Evidence / Audit
```

At minimum each route declares loading, empty, success, partial-data, error and permission-denied states as applicable.

## 8. Data remains a plug-in layer
```text
External Data
 ↓
Ingestion
 ↓
Parse / Validate / Normalize
 ↓
Function / Formula
 ↓
Canonical Table
 ↓
(optional) View Model
 ↓
Dynamic Visualization
 ↓
Existing UI shell
```

The UI shell does not calculate business numbers. Data modules plug into it through canonical contracts.

## 9. Multi-platform from day one
The shell is designed once at the interaction-contract level and adapted by surface:

```text
                 序境 Shared Contract
                         │
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
         Web          Desktop         Mobile
      full workspace   deep/local    monitor/act
          │              │              │
          └──────────────┼──────────────┘
                         ↓
                   Mini Program
                   quick task/entry
```

The same domain object, metric, evidence, permission and route intent must remain semantically consistent across surfaces. Presentation density and interaction patterns may differ.

## 10. Functional freeze
UI-first does **not** mean feature redesign.

```text
Confirmed Function → LOCK
Architecture → may optimize with regression
UI → may redesign
Interaction → may improve
Data presentation → may improve
Implementation → preserve unless justified
```

No visual refactor may silently remove or redefine a confirmed function.

## 11. KEEP / ADAPT / REMOVE
```text
Old asset
 ↓
reference/dependency/runtime check
 ├─ compatible → KEEP
 ├─ useful but outdated → ADAPT
 └─ obsolete/conflicting/duplicate → migrate → test → REMOVE
```

No deletion by appearance or filename alone.

## 12. Definition of Done for P0
P0 UI Shell is complete only when:
- global navigation works;
- ZBP/CTH/KOS/KOS/KOC/UGC/Podcast hierarchy is navigable;
- page/section/component/window contracts exist;
- route state and return context work;
- responsive/adaptive rules cover Web/Desktop/Mobile/Mini Program;
- loading/empty/error/permission states are visible;
- at least one real CTH workflow can be run end-to-end daily through the shell;
- data can be plugged into the shell without rewriting the shell;
- visual components have stable contracts;
- UI regression checks exist.

## 13. Non-goals
P0 does not authorize:
- deleting confirmed CTH features;
- replacing business logic with UI logic;
- duplicating backend/domain logic per platform;
- fabricating data for visual demos;
- freezing the visual design before evidence-based iteration;
- postponing the actual interface until after all backend work.

## 14. Final principle
**Build the interface first so the product is continuously testable; then fill the interface with confirmed functions and trusted data.**

序境 = platform identity.
ZBP = parent product architecture.
CTH = child system and first feature-validation surface.
Web / Desktop / Mobile / Mini Program = product surfaces.
Data = canonical truth.
UI = continuously testable presentation and interaction surface.
