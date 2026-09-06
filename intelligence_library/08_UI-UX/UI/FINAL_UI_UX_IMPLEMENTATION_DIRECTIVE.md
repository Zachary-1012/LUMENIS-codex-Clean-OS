# Final UI/UX Implementation Directive

**Status:** FINAL / cross-repository implementation directive
**Date:** 2026-09-04
**Purpose:** Tell the coding agent exactly how to locate and reuse the existing UI implementation instead of inventing a parallel UI.

## Mission

Implement the approved UI/UX specification in the existing product. **Do not redesign from scratch. Do not create a second Shell. Do not create a second design system. Do not guess filenames. Find the existing implementation by repository search, inspect it, then modify the nearest existing abstraction.**

## Repository discovery protocol

Start by identifying the actual repository structure and active frontend entry points:

```bash
pwd
find . -maxdepth 4 -type f | sort
find . -type f \( -name '*.html' -o -name '*.css' -o -name '*.js' -o -name '*.jsx' -o -name '*.tsx' -o -name '*.vue' \) | sort
```

Then search for the actual implementation using symbols and visible strings:

```bash
rg -n "xujing-design-system|design-system|Shell|sidebar|Workspace|workspace|notification|account|popover|drawer|dialog|智能问答|舆情监测|风险预警|品牌中心|案例库|知识库|系统健康|内部浏览器|Evidence|assistant" . --glob '!node_modules/**' --glob '!venv/**' --glob '!data/**'
rg -n "font-size|width:.*px|height:.*px|border-radius|box-shadow|--.*spacing|--.*color|svg|icon" . --glob '*.css' --glob '*.html' --glob '*.js' --glob '*.jsx' --glob '*.tsx'
```

If the exact terms do not match, search shorter terms: `sidebar`, `nav`, `shell`, `panel`, `modal`, `drawer`, `popover`, `icon`, `assistant`, `evidence`, `browser`, `health`.

**Never claim a component/file does not exist until these searches and the repository tree have been checked.**

## Source-of-truth priority

When implementing UI, use this order:

1. Existing production Shell and route/navigation code
2. Existing unified design-system/token CSS
3. Existing shared components
4. Existing page-specific implementation
5. New code only where a required capability is genuinely missing

If multiple historical CSS files exist, identify which stylesheet is actually loaded by the active HTML/template and which one wins in the cascade before editing.

## Required final information architecture

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

Do not flatten or duplicate this navigation.

## Global Shell

```text
L0 Shell
├─ L1 Top Bar
│  ├─ Workspace Switcher → Popover
│  ├─ Global Search → Function navigation results
│  ├─ Notification → Popover → direct object/detail
│  └─ Account → Popover
├─ L2 Sidebar → fixed IA above
├─ L3 Current Page
│  ├─ Header
│  ├─ Description
│  ├─ Actions
│  ├─ Filter/Query
│  └─ Primary Content
└─ L4 Overlays
   ├─ Popover
   ├─ Drawer
   ├─ Dialog
   ├─ Full Workspace
   └─ AI Assistant
```

## Overlay rules

**Popover:** workspace switcher, notifications, account, quick controls. Small and anchored.

**Drawer:** ordinary object details. Default right side. Preserve the page/list behind it.

**Dialog:** consequential confirmation, deletion, regeneration, permission, dangerous actions.

**Full Workspace:** only genuinely complex work such as Browser Runtime or other persistent task environments.

## Universal navigation rules

```text
Navigation click → Page
List item → Right Detail Drawer
Full view → Detail Page
Evidence → Evidence Drawer/Page
Edit → Edit state/Dialog
Dangerous action → Confirm Dialog
Complex task → Full Workspace
AI entry → AI Panel
AI complex task → AI Workspace
```

Do not use a new page for a detail that can be handled by a Drawer. Do not open ordinary details in a new browser tab.

## Page-level construction

Every page:

```text
Page Header
  title
  one-line description
  actions
Filter / Query
Primary Content
Detail interaction
```

The Home page is **智能问答**, not a KPI dashboard. The AI response hierarchy is:

`Conclusion → Key Evidence → Data → Evidence → Action`

## Existing implementation mapping task

Before coding, produce an internal mapping table with these fields:

```text
Approved UI element
Existing file/path
Existing symbol/class/function
Current behavior
Required change
Shared abstraction or page-local
Validation method
```

At minimum map:

- Shell
- top bar
- workspace switcher
- global search
- notification popover
- account popover
- sidebar/group navigation
- Home/overview/智能问答
- list/table component
- detail drawer
- generic dialog
- AI assistant
- evidence view
- Browser Runtime
- System Health
- design tokens
- icon sizing rules

Do not start visual implementation until this map has been established.

## Visual implementation rules

Use the existing design system. The final language is restrained, data-first and low-decoration:

- black / white / gray dominant
- restrained typography
- small linear icons
- clear hierarchy
- weak borders
- restrained radius
- light motion

Forbidden:

- giant icons
- giant titles
- giant KPI cards/numbers
- excessive gradients
- blue/purple generic AI-tech styling
- glow-heavy UI
- poster-style dashboards
- page-specific design languages

Do not add arbitrary pixel values when an existing token/component covers the need. Do not create another `design-system.css` merely to override an older one.

## Compatibility rule

If legacy CSS causes a visual conflict, first identify the cascade and active stylesheet. A temporary `!important` compatibility rule is acceptable only when necessary, but the preferred fix is to converge on the existing unified token/component layer.

## Context preservation

Opening a Drawer must preserve:

- current page
- current filters
- current search
- current list position where technically feasible

Closing the Drawer returns the user to the same context.

## Do not break product logic

UI work must not alter:

- production truth rules
- subject hard filter
- collection logic
- risk/business decision logic
- evidence semantics
- existing runtime contracts
- authentication/session behavior
- existing routes unless a route is demonstrably broken

If a UI requirement appears to conflict with business logic, stop at the UI boundary and integrate through the existing contract rather than rewriting the business layer.

## Completion gate

Do not report “UI completed” merely because the page renders.

Verify:

```text
[ ] Existing Shell reused
[ ] Existing design system reused
[ ] Navigation hierarchy correct
[ ] Every primary click has a deterministic destination
[ ] List → Drawer behavior works
[ ] Popovers close correctly
[ ] Dialog confirmation works
[ ] AI entry does not dominate every page
[ ] Evidence can be reached from applicable objects
[ ] Browser/System Health use existing Runtime views
[ ] No duplicate CSS/component system created
[ ] No giant icon/title/card regression
[ ] Desktop verified
[ ] Mobile verified
[ ] Existing business logic unchanged
```

## Final instruction to coding agent

**Find first. Map second. Reuse third. Modify fourth. Validate fifth.**

Do not interpret this document as a request to invent a new UI. The desired result is the existing product converged onto the approved hierarchy and interaction language. If an equivalent implementation already exists, improve and reuse it. If something is missing, add the smallest shared abstraction that fits the existing architecture.
