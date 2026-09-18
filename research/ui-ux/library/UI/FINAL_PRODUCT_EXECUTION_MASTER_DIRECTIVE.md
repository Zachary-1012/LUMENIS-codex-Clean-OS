# FINAL PRODUCT EXECUTION MASTER DIRECTIVE

**Status: P0 / FINAL / EXECUTION AUTHORITY**
**Date: 2026-09-04**

This directive unifies the approved UI/UX hierarchy, deterministic data pipeline, business object templates, and content-production templates. It is an execution contract for the existing product, not permission to redesign from scratch.

## 1. Mandatory execution order

**Find → Map → Reuse → Modify → Test → Gate → Release.**

Before writing UI code, search the repository for the actual Shell, navigation, design tokens, components, routes, data functions, tables, visualization adapters, KOS/KOC/UGC modules, event/note/topic/risk modules, content templates and existing AI/evidence/runtime implementation.

Run:

```bash
pwd
find . -maxdepth 4 -type f | sort
rg -n "Shell|sidebar|nav|workspace|popover|drawer|dialog|assistant|evidence|browser|health|智能问答|舆情监测|风险预警|负面监测|笔记|话题监测|话题|KOS|KOC|UGC|事件|案例库|知识库|报告" . --glob '!node_modules/**' --glob '!venv/**' --glob '!data/**'
rg -n "design-system|font-size|border-radius|box-shadow|--.*color|--.*spacing|icon|svg" . --glob '*.css' --glob '*.html' --glob '*.js' --glob '*.jsx' --glob '*.tsx'
```

Do not guess filenames. If an exact term fails, search by shorter symbols, visible text, class, function, route or behavior.

## 2. UI hierarchy — locked

```text
L0 Shell
├─ L1 Top Bar
│  ├─ Workspace Switcher → Popover
│  ├─ Global Search → grouped navigation results
│  ├─ Notification → Popover → direct object/detail
│  └─ Account → Popover
├─ L2 Sidebar
│  ├─ 总览
│  ├─ 监测
│  ├─ 分析
│  ├─ 品牌资产
│  ├─ 产出
│  └─ 系统
├─ L3 Current Workspace
│  ├─ Header
│  ├─ Description
│  ├─ Actions
│  ├─ Filter / Query
│  ├─ Primary Content
│  └─ Detail
└─ L4 Overlays
   ├─ Popover
   ├─ Drawer
   ├─ Dialog
   ├─ Full Workspace
   └─ AI Assistant
```

Navigation is:

```text
总览 / 智能问答
监测 / 舆情监测 / 风险预警 / 负面监测 / 笔记 / 官方 / 话题监测 / 话题
分析 / 舆情分析 / 事件 / 事件关系 / 日历
品牌资产 / 品牌中心 / 太古汇 / 案例库 / 案例分析 / 知识库 / 品牌报告 / Evidence
产出 / 报告
系统 / 系统健康 / 内部浏览器 / Evidence / 设置
```

Universal interaction contract:

```text
Navigation → Page
List item → Right Detail Drawer
Full view → Detail Page
Evidence → Evidence Drawer/Page
Edit → Edit State/Dialog
Dangerous action → Confirm Dialog
Complex task → Full Workspace
AI → AI Panel
AI complex task → AI Workspace
```

## 3. Visual language — locked

Use the existing unified design system. Black/white/gray dominant, restrained typography, small linear icons, clear hierarchy, weak borders, restrained radius, light motion and data-first composition.

Forbidden: giant icons, giant titles, giant KPI cards, excessive gradients, generic blue/purple AI styling, glow-heavy UI, poster dashboards, or page-specific visual systems.

Do not create a parallel design system.

## 4. P0 data trust pipeline

```text
Raw
↓ Schema Validation
↓ Normalization
↓ Deduplication
↓ Deterministic Functions
↓ Canonical Data Table
↓ Data Quality Gate
↓ Visualization Dataset
↓ Visualization Validation
↓ Export Dataset
↓ Export Validation
↓ Release / Export
```

Canonical Data Table is the factual source for tables, charts, pages, reports and exports.

The frontend and export layer must not independently recalculate business metrics.

Every core metric should retain metric_id, formula_version, calculation_version, dataset_version, calculated_at and source_record_ids where applicable.

## 5. Data gates

```text
GATE 01 Schema
GATE 02 Integrity
GATE 03 Calculation
GATE 04 Canonical Table
GATE 05 Visualization
GATE 06 Export
```

PASS → continue.

FAIL → BLOCK.

UNKNOWN → BLOCK.

Golden Dataset tests are mandatory for deterministic calculations.

The core invariant is:

```text
Canonical Table = Visualization Dataset = UI = Export
```

Traceability:

```text
UI metric → Visualization Dataset → Canonical Table → Function → Source Records → Raw → Evidence
```

## 6. Business object templates

All business objects use:

```text
Identity → Source → Classification → Metrics → Analysis → Risk/Value → Evidence → Actions → History/Audit
```

### KOS

Identity → Positioning → Content themes → Audience → Reach/interaction → Influence → Brand fit → Risk → Cooperation value → Evidence → History.

### KOC

Identity → Authenticity → Experience/product context → Content → Interaction → Community influence → Sentiment → Risk → Cooperation potential → Evidence.

### UGC

Record → User expression → Topic/theme → Sentiment → Entity/brand → Event relation → Propagation → Risk → Evidence.

### Note

Identity → Platform/author → Publish time → Content → Topics/entities → Engagement → Sentiment → Event relation → Risk → Evidence → Actions.

### Topic monitoring

Definition/keywords → Volume → Velocity → Trend → Sentiment distribution → Creator distribution → Event relation → Risk → Top notes → Evidence.

### Sentiment / negative monitoring

Source content → Classification → Confidence → Reason/evidence → Interaction impact → Spread → Risk → Human review where required → Final judgment.

### Risk alert

Trigger → Detection → Rule/score → Evidence → Severity → Scope → Suggested action → Human confirmation → Status → Resolution history.

### Event

Discovery → Related records → Cluster/relation → Timeline → Spread/peak → Sentiment → Impact → Risk → Response → Resolution → Review.

### Event relationship

Only draw relationships backed by actual nodes, edges and source records. No decorative graph relationships.

## 7. Content production templates

Every content task contains:

```text
Objective
Audience
Platform
Topic
Tone
Key message
Facts / Evidence
Forbidden claims
CTA
Output format
Version
Human approval state
```

### Xiaohongshu note

Title/Hook → Opening context → User-relevant experience/fact → Scene details → Emotional/practical value → Brand/campaign information → CTA → Tags → Evidence for factual claims.

### Poster

Main title → Subtitle → Core information → Time → Location → Participation → Notes → CTA.

### Short video

Hook → Scene 1 → Scene 2 → Key information → Emotional turn → Brand/campaign → Ending.

Every shot contains visual, voice/subtitle, duration, information purpose and asset source.

### Campaign copy

Maintain separate brand communication language and platform-native user language.

### Comment reply

Original comment → Intent → Sentiment → Risk → Reply strategy → Generated draft → Human approval → Final reply → Monitoring/follow-up.

### Content review

Accuracy → Brand consistency → Platform fit → Tone → Risk → Evidence → Human approval → Publish state.

## 8. AI boundary

AI may assist classification, summarization, sentiment analysis, event clustering, drafting and recommendations.

AI must not silently overwrite deterministic facts, canonical metrics, evidence or required human approvals.

Record model version, prompt version, input, output, confidence, final result and human correction where applicable.

## 9. Source mapping before implementation

For every approved UI or business object, create an implementation map:

```text
Approved element
→ actual repository path
→ actual symbol/class/function
→ current behavior
→ required change
→ shared/page-local
→ validation
```

At minimum locate and map Shell, Sidebar, Top Bar, Popovers, Drawer, Dialog, AI Assistant, Evidence, Browser Runtime, System Health, design tokens, data calculation functions, canonical table layer, visualization adapter, export layer, KOS, KOC, UGC, Notes, Topics, Events, Risk, Content templates and Comment Reply.

## 10. Release blockers

The following block merge/release/export:

- data mismatch
- unknown calculation state
- missing formula/version
- canonical/UI mismatch
- canonical/export mismatch
- missing evidence where evidence is required
- duplicate calculation path
- duplicate design system
- broken navigation destination
- broken Drawer context preservation
- destructive action without configured confirmation
- business logic regression

## 11. Final execution command

**Do not produce a conceptual mockup and stop. Find the real implementation in the repository. Map it. Reuse it. Modify the smallest appropriate abstraction. Run the data and UI gates. Validate every destination and every data path. Continue until the approved system is actually implemented and verified.**

**Find first. Map second. Reuse third. Modify fourth. Test fifth. Gate sixth. Release last.**
