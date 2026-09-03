# Final UI/UX Construction Specification

**Status:** FINAL / implementation authority
**Date:** 2026-09-04
**Scope:** Z-Brand-Core production UI

## 0. Purpose

This document converts the approved product UI/UX into an implementation-level construction specification. It is authoritative for visual hierarchy, navigation, windows, drawers, dialogs, transitions and interaction rules. It does **not** authorize a product architecture rewrite.

## 1. First rule: reuse existing implementation

Before changing code, locate and reuse the existing Shell, navigation, design-system CSS/tokens, shared components, page routing, popovers, drawers, dialogs, AI assistant and existing runtime/evidence pages.

Do not create a parallel UI framework or a second visual system.

Repository search targets (run these first):

```bash
find . -maxdepth 4 -type f | sort
rg -n "xujing-design-system|design-system|Shell|sidebar|Workspace|workspace|notification|account|popover|drawer|dialog|assistant|evidence|browser|system-health|智能问答" . --glob '!node_modules/**' --glob '!venv/**' --glob '!data/**'
rg -n "svg|icon|font-size|border-radius|box-shadow|--.*color|--.*spacing" static templates . --glob '*.css' --glob '*.html' --glob '*.js'
```

If a named file is not present, search by **symbol/function/class/visible text**, not by guessing a filename. Preserve the existing implementation when it already satisfies the rule.

## 2. Product Shell hierarchy

```text
L0 Product Shell
├── L1 Top System Bar
│   ├── Workspace Switcher
│   ├── Global Search
│   ├── Notification
│   └── Account
├── L2 Left Navigation
│   ├── 总览
│   ├── 监测
│   ├── 分析
│   ├── 品牌资产
│   ├── 产出
│   └── 系统
├── L3 Current Workspace
│   ├── Page Header
│   ├── Page Description
│   ├── Page Actions
│   ├── Filter / Query
│   ├── Primary Content
│   └── Secondary / Detail Content
└── L4 Global Overlays
    ├── Popover
    ├── Drawer
    ├── Dialog
    ├── Full-screen Workspace
    └── AI Assistant
```

Every page must follow:

`Workspace → Navigation Group → Page → Section → Component → Detail → Action`

## 3. Fixed navigation information architecture

```text
总览
  智能问答

监测
  舆情监测
  风险预警
  负面监测
  笔记
  官方
  话题监测
  话题

分析
  舆情分析
  事件
  事件关系
  日历

品牌资产
  品牌中心
  太古汇
  案例库
  案例分析
  知识库
  品牌报告
  Evidence

产出
  报告

系统
  系统健康
  内部浏览器
  Evidence
  设置
```

Do not flatten these groups into one long menu. Do not invent another navigation system inside a page.

## 4. Top bar interactions

### Workspace Switcher

Top-left. Click opens a small Popover, not a page. It shows the current workspace and available workspaces. Selecting a workspace closes the Popover and preserves the current navigation state where possible; protected workspace entry performs the existing authentication/key flow.

### Global Search

Search is product/function navigation, not unrestricted web search and not an AI chat. Query → grouped result → click → target page.

### Notification

Click opens Popover. Each notification is directly actionable: click notification → corresponding object/detail. Do not force the user through a generic notification page.

### Account

Click opens Popover containing identity, system/settings/help and logout actions.

## 5. Page template

```text
Page Header
  title
  one-line description
  actions

Filter / Query

Primary Content
  table / list / cards / timeline / graph / report

Detail interaction
```

Do not make every page a dashboard. Data density should be controlled by hierarchy, not oversized cards.

## 6. Home / Intelligent Q&A

Home is the AI entry point, not a KPI wall.

```text
序境
你想了解什么？
[ question input ................................ ] [send]
[舆情分析] [风险判断] [品牌分析]
```

AI output hierarchy:

`Conclusion → Key Evidence → Data → Evidence → Action`

AI must not silently mutate production truth.

## 7. Lists and detail behavior

Default rule:

`List item click → right-side Detail Drawer`

Drawer hierarchy:

`Header → Identity → Summary → Analysis → Evidence → Actions`

Use a full Detail Page only when the object requires a larger working context or the user explicitly chooses full view.

## 8. Overlay taxonomy

Only four overlay/workspace types are permitted:

### Popover

For lightweight controls: workspace switcher, notifications, account, quick actions. Small, anchored, closes on outside click.

### Drawer

For object detail, analysis, evidence, brand, case and event detail. Default direction: right side. Preserve list/page context behind it.

### Dialog

For confirmation, deletion, regeneration, permission or other consequential actions. Must explain consequence and provide explicit cancel/confirm actions.

### Full-screen Workspace

Only for genuinely complex work: Browser Runtime, Creative Workbench or other task environments that need persistent working context.

## 9. AI Assistant

Default location: lower-right floating entry. It opens a compact AI Panel. Complex work can escalate to the full AI workspace.

Do not turn every page into a chat application.

## 10. Fixed transition rules

```text
Navigation click → Page
List item → Detail Drawer
Full view → Detail Page
Evidence → Evidence Drawer/Page
Edit → Edit state or Dialog
Dangerous action → Confirm Dialog
Complex task → Full Workspace
AI entry → AI Panel
AI complex task → AI Workspace
```

Avoid full-page reloads for ordinary detail inspection. Preserve filters, scroll position and current context when opening/closing drawers.

## 11. Visual system

Required:

- black / white / gray dominant palette
- restrained typography
- small linear icons
- clear hierarchy
- data-first layout
- weak borders
- restrained radius
- light motion
- consistent spacing and typography tokens

Forbidden:

- giant icons
- giant titles
- giant KPI numbers
- giant cards
- excessive gradients
- blue/purple generic AI-tech styling
- glow-heavy UI
- poster-like dashboards
- page-specific visual languages

Use the existing unified design system and tokens. Do not solve conflicts by endlessly adding new CSS layers. `!important` may be used only as controlled compatibility/override while legacy styles are being retired.

## 12. Existing-code-first implementation procedure

1. Inspect repository tree.
2. Locate current Shell and route/navigation definitions.
3. Locate the active design-system CSS/token file(s).
4. Locate existing shared icon/button/card/panel/popover/drawer/dialog components.
5. Locate current Home/overview implementation.
6. Locate existing business pages and map them to the fixed IA above.
7. Locate existing Evidence, Browser Runtime and System Health implementations.
8. Reuse existing components; refactor only where the final spec requires it.
9. Do not duplicate components with similar names.
10. Do not rename working routes unless required for correctness.
11. Add missing behavior at the nearest existing shared abstraction.
12. Validate desktop and mobile layouts.
13. Verify every click target has a deterministic destination or overlay.
14. Verify drawer close/back preserves context.
15. Verify visual dimensions against the existing design-system registry.

## 13. Acceptance matrix

A page is not complete until all are true:

- [ ] Correct Workspace
- [ ] Correct Navigation Group
- [ ] Correct Page title/description/actions
- [ ] Correct list/detail relationship
- [ ] Correct Popover/Drawer/Dialog/Workspace type
- [ ] Correct destination for every primary action
- [ ] Evidence path is available where applicable
- [ ] No duplicate navigation system
- [ ] No duplicate design system
- [ ] No oversized icon/title/card treatment
- [ ] Existing routes and business logic remain intact
- [ ] Mobile layout remains usable
- [ ] No silent destructive action

## 14. Non-goals

This specification does not authorize:

- redesigning the product architecture
- replacing the current backend/runtime
- replacing the existing browser runtime
- replacing the existing evidence model
- introducing a new UI framework solely for styling
- converting the system into a generic dashboard
- converting the system into a generic chat application

The task is **implementation alignment and UI/UX convergence**, not reinvention.
