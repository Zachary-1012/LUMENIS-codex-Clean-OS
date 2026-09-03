# FINAL PRODUCT EXECUTION MASTER DIRECTIVE

**Status: P0 / FINAL / EXECUTION AUTHORITY**
**Date: 2026-09-04**

This document unifies the approved UI/UX hierarchy, deterministic data pipeline, and KOS/KOC/UGC / sentiment / event / note / topic-monitoring / content-production templates into one execution contract.

## 0. Non-negotiable principle

This is an implementation and convergence task, not a redesign task.

**Find → Map → Reuse → Modify → Test → Gate → Release.**

Do not invent parallel Shells, design systems, data-calculation paths, export logic, or duplicate templates when an existing implementation already exists.

If the implementation cannot be located, search the repository by symbol, class, function, route, visible text, API name, or behavior before creating anything new.

---

# 1. SOURCE DISCOVERY — MUST HAPPEN FIRST

Run:

```bash
pwd
find . -maxdepth 4 -type f | sort
rg -n "Shell|sidebar|nav|workspace|popover|drawer|dialog|assistant|evidence|browser|health|智能问答|舆情监测|风险预警|负面监测|笔记|话题监测|话题|KOS|KOC|UGC|事件|案例库|知识库|报告" . --glob '!node_modules/**' --glob '!venv/**' --glob '!data/**'
rg -n "design-system|font-size|border-radius|box-shadow|--.*color|--.*spacing|icon|svg" . --glob '*.css' --glob '*.html' --glob '*.js' --glob '*.jsx' --glob '*.tsx'
```

Before changing code, produce an internal source map:

```text
Approved object → actual path → actual symbol → current behavior → required change → validation
```

Never guess filenames. Never declare a feature missing until repository search has been performed.

---

# 2. UI INFORMATION ARCHITECTURE — LOCKED

```text
L0 Product Shell
├─ L1 Top System Bar
│  ├─ Workspace Switcher
│  ├─ Global Search
│  ├─ Notification
│  └─ Account
├─ L2 Left Navigation
│  ├─ 总览
│  ├─ 监测
│  ├─ 分析
│  ├─ 品牌资产
│  ├─ 产出
│  └─ 系统
├─ L3 Current Workspace
│  ├─ Page Header
│  ├─ Description
│  ├─ Actions
│  ├─ Filter / Query
│  ├─ Primary Content
│  └─ Detail
└─ L4 Overlay
   ├─ Popover
   ├─ Drawer
   ├─ Dialog
   ├─ Full Workspace
   └─ AI Assistant
```

Navigation:

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

Universal interactions:

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

Overlay meanings are fixed:

- Popover = lightweight anchored control.
- Drawer = contextual object detail; preserve page/list context.
- Dialog = consequential confirmation.
- Full Workspace = complex persistent task.

---

# 3. VISUAL SYSTEM — LOCKED

Use the existing unified tokens/components.

Required language:

- black / white / gray dominant
- restrained typography
- small linear icons
- clear hierarchy
- data-first composition
- weak borders
- restrained radius
- light motion

Forbidden:

- giant icons
- giant titles
- giant KPI cards/numbers
- excessive gradients
- generic blue/purple AI-tech styling
- glow-heavy UI
- poster-style dashboard
- page-specific visual systems

Do not create `design-system-v2`, `new-shell`, `new-sidebar`, or parallel CSS/component systems.

---

# 4. DATA TRUST CHAIN — P0

No raw data may be directly bound to final visualization.

Required pipeline:

```text
Raw Data
↓
Schema Validation
↓
Normalization
↓
Deduplication
↓
Deterministic Function Calculation
↓
Canonical Data Table
↓
Data Quality Gate
↓
Visualization Dataset
↓
Visualization Validation
↓
Export Dataset
↓
Export Validation
↓
Release / Export
```

The Canonical Data Table is the single factual source for UI, dynamic tables, charts, reports and exports.

Frontend must not independently calculate business metrics.

Export must not independently recalculate business metrics.

Every metric must carry, where applicable:

```text
metric_id
formula_version
calculation_version
dataset_version
calculated_at
source_record_ids
```

---

# 5. DATA GATES — FAIL CLOSED

```text
GATE 01 Schema
GATE 02 Integrity
GATE 03 Calculation
GATE 04 Canonical Table
GATE 05 Visualization
GATE 06 Export
```

PASS = continue.

FAIL = BLOCK.

UNKNOWN = BLOCK.

Never silently substitute missing values or permit inconsistent output unless the business schema explicitly defines the default.

Golden Dataset tests are mandatory for deterministic calculations.

The following must agree:

```text
Canonical Table = Visualization Dataset = UI = Export
```

Every core number must be traceable:

```text
UI metric
↓
Visualization Dataset
↓
Canonical Table
↓
Calculation Function
↓
Source Record IDs
↓
Raw Data
↓
Evidence / Source
```

---

# 6. BUSINESS OBJECT TEMPLATE SYSTEM

All business objects must use a consistent hierarchy:

```text
Identity
→ Source
→ Classification
→ Metrics
→ Analysis
→ Risk / Value
→ Evidence
→ Actions
→ History / Audit
```

## 6.1 KOS

```text
KOS Identity
→ Account / Creator profile
→ Positioning
→ Content themes
→ Audience
→ Reach / interaction metrics
→ Influence assessment
→ Brand fit
→ Risk
→ Cooperation value
→ Evidence
→ History
```

## 6.2 KOC

```text
KOC Identity
→ Authenticity signals
→ Experience / product context
→ Content
→ Interaction
→ Community influence
→ Sentiment
→ Risk
→ Cooperation potential
→ Evidence
```

## 6.3 UGC

```text
UGC Record
→ User expression
→ Topic / theme
→ Sentiment
→ Entity / brand
→ Event relation
→ Propagation
→ Risk
→ Evidence
```

## 6.4 Note / Post

```text
Note Identity
→ Platform / Author
→ Publish time
→ Content
→ Topic / entities
→ Engagement
→ Sentiment
→ Event relation
→ Risk
→ Evidence
→ Actions
```

## 6.5 Topic Monitoring

```text
Topic
→ Definition / keywords
→ Volume
→ Velocity
→ Trend
→ Sentiment distribution
→ Creator distribution
→ Event relation
→ Risk
→ Top notes
→ Evidence
```

## 6.6 Sentiment / Negative Monitoring

Do not treat sentiment as a decorative badge.

```text
Source content
→ Sentiment classification
→ Confidence
→ Reason / evidence
→ Interaction impact
→ Spread
→ Risk level
→ Human review where required
→ Final judgment
```

## 6.7 Risk Alert

```text
Trigger
→ Detection
→ Rule / score
→ Evidence
→ Severity
→ Scope
→ Suggested action
→ Human confirmation
→ Status
→ Resolution history
```

## 6.8 Event

```text
Event discovery
→ Related records
→ Cluster / relation
→ Timeline
→ Spread / peak
→ Sentiment
→ Impact
→ Risk
→ Response
→ Resolution
→ Review
```

## 6.9 Event Relationship

Nodes and edges must be data-backed. Do not draw decorative relationships without source records.

```text
Entity / Event / Topic / Note
↕
Relationship
↕
Evidence
```

---

# 7. CONTENT PRODUCTION TEMPLATE SYSTEM

Content templates are structured production objects, not free-form AI text boxes.

Every content task must carry:

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

## 7.1 Xiaohongshu Note

```text
Title / Hook
→ Opening context
→ User-relevant experience / fact
→ Scene details
→ Emotional or practical value
→ Brand / campaign information
→ CTA
→ Tags
→ Evidence / source if factual claim
```

## 7.2 Poster

```text
Main title
→ Subtitle
→ Core information
→ Time
→ Location
→ Participation
→ Notes
→ CTA
```

## 7.3 Short Video

```text
Hook
→ Scene 1
→ Scene 2
→ Key information
→ Emotional turn
→ Brand / campaign
→ Ending
```

Each shot must define:

```text
Visual
Voice / subtitle
Duration
Information purpose
Asset source
```

## 7.4 Copy / Campaign Language

Separate:

```text
Brand communication language
≠
Platform-native user language
```

Do not flatten both into generic advertising copy.

## 7.5 Comment Reply

```text
Original comment
→ Intent classification
→ Sentiment
→ Risk
→ Reply strategy
→ Generated draft
→ Human approval
→ Final reply
→ Monitoring / follow-up
```

Automatic generation must never mean automatic publication for consequential/risky replies without the configured approval rule.

## 7.6 Content Review

```text
Accuracy
→ Brand consistency
→ Platform fit
→ Tone
→ Risk
→ Evidence
→ Human approval
→ Publish state
```

---

# 8. AI ROLE

AI may assist with:

- classification
- summarization
- sentiment analysis
- event clustering
- content drafts
- reply drafts
- recommendations

AI must not silently replace deterministic business rules, canonical facts, evidence or human approval requirements.

Record where applicable:

```text
model_version
prompt_version
input
output
confidence
final_result
human_correction
correction_reason
```

---

# 9. PAGE / WINDOW CONSTRUCTION RULE

Every page must be expressible as:

```text
Workspace
→ Navigation Group
→ Page
→ Section
→ Component
→ Detail
→ Action
```

For each component define:

```text
what it is
where it sits
what level it belongs to
what opens when clicked
what closes when dismissed
what state it changes
where the user returns
what evidence it links to
```

If a developer cannot answer these questions, the implementation is incomplete.

---

# 10. ACCEPTANCE GATE

Before declaring completion:

```text
[ ] Existing Shell reused
[ ] Existing design system reused
[ ] Navigation hierarchy correct
[ ] All page/object templates mapped
[ ] Popover/Drawer/Dialog/Workspace semantics correct
[ ] List → Drawer works
[ ] Context is preserved
[ ] Canonical data exists
[ ] Functions are deterministic where required
[ ] Golden Dataset passes
[ ] UI equals Canonical metrics
[ ] Export equals Canonical metrics
[ ] Evidence traceability works
[ ] AI does not silently overwrite truth
[ ] KOS/KOC/UGC templates implemented
[ ] Note/Topic/Event/Risk templates implemented
[ ] Content production templates implemented
[ ] Comment reply workflow implemented
[ ] No duplicate design system
[ ] No duplicate calculation path
[ ] Existing business logic intact
[ ] Desktop verified
[ ] Mobile verified
```

Any P0 failure blocks merge/release/export.

## Final command

**Execute this specification against the existing repository now. Do not create a conceptual mockup and stop. Locate the actual implementation, map it, modify it, test it, and enforce the gates. Reuse before creating. Never guess. Never silently pass an unknown state.**
