# UI × DATA × CONTENT × REPORT × PODCAST
## Construction Plan V1 — 2026-09-04

> 本文件是平台级施工规划。它把统一数据链、Canonical Table、可视化、UI 层级/窗口/跳转、内容制作、KOS/KOC/UGC、舆情报告与 Podcast 的既定设计转化为可执行、可测试、可审计的施工顺序。生产 Truth 仍以代码、数据、测试和审计证据为准。

## 1. 总施工链

```text
源码扫描
→ Source Map
→ Registry
→ 复用判断
→ 数据链施工
→ UI Shell
→ Window / Route
→ Dynamic Table / Visualization
→ 业务模块
→ Content Templates
→ Reports / Export
→ Podcast Workspace
→ Cross-link
→ Golden Dataset
→ Regression
→ Audit
→ Commit
→ Push
→ Remote Verify
```

## 2. 源码施工前置 Gate

```bash
find . -maxdepth 6 -type f | sort
rg -n "route|router|shell|sidebar|workspace|drawer|dialog|modal|table|chart|visual|realtime|websocket|SSE|stream|import|upload|parser|CSV|XLSX|PDF|PPT|OCR|video|audio|normalize|dedup|schema|formula|export|evidence|KOS|KOC|UGC|podcast|episode|idea|vault|knowledge" . --glob '!node_modules/**'
```

必须建立：

```text
功能/页面
→ 文件
→ symbol/component
→ route
→ API
→ data source
→ DB/table
→ tests
→ reuse candidate
→ gap
→ change plan
```

名称不同不能直接判定功能不存在；继续按 symbol、route、API、DB、visible text 查找。

## 3. Registry

```text
Page
Window
Route
Component
Data
Metric
Formula
Visualization
Interaction
Template
Report
Evidence
Export
Test
```

所有 ID、schema、版本稳定可追踪。

## 4. UI Shell

```text
Platform Shell
├─ Header
├─ Global Navigation
├─ Workspace Switcher
├─ Search / Command
├─ Notification
├─ Settings
└─ Global AI
```

业务 Workspace 不创建第二套平台 Shell。

## 5. 功能 → 层级 → 窗口 → 跳转

```text
User Task
→ Object Complexity
→ Context Requirement
→ Edit / Confirm Requirement
→ Information Density
→ Function Level
→ Window Type
→ Navigation
```

窗口规则：

```text
Popover  = 快速控制
Drawer   = 保留上下文的对象查看
Dialog   = 明确确认/短操作
Full Page = 独立对象信息架构
Workspace = 连续复杂任务
AI Panel = 当前上下文辅助
AI Workspace = 多轮复杂任务
```

跳转规则：

```text
List → Drawer
Drawer → View Full → Full Page
Related Object → Stack / Replace
Dangerous Action → Dialog
Complex Task → Workspace
```

返回必须尽量恢复 route/query/filter/sort/pagination/scroll/selection。

## 6. Universal Data Ingestion

覆盖：

```text
Collector / CSV / XLSX / XLS / PDF / PPT / PPTX / DOC / DOCX
TXT / Markdown / JSON / API / Database / Text / Image / Screenshot
Audio / Video / URL（受现有安全权限约束）
```

统一：

```text
Input
→ Raw Asset
→ Parser / OCR / Media Extractor
→ Structured Intermediate Data
```

资产必须记录：

```text
asset_id
source_type
received_at
checksum
parse_status
extraction_status
```

## 7. 两条数据路径

### A：需要计算

```text
External Input
→ Raw Asset
→ Extraction
→ Schema
→ Normalize
→ Dedup
→ Programming Function
→ Deterministic Calculation
→ Canonical Table
```

### B：已经是标准表

```text
External Table
→ Schema
→ Normalize
→ Dedup
→ Canonical Table
```

不得为了形式重复计算；但不能跳过完整性验证。

非表格内容：

```text
Media / Document / Text
→ Extraction
→ Structured Data
→ Function（需要时）
→ Canonical Table
```

纯素材/Evidence 可以停在 Evidence / Structured Data，不伪造数据。

## 8. Canonical Table

它是唯一事实数据层。

```text
dataset_id
dataset_version
schema_version
source_asset_id
source_record_ids
transformation_version
calculation_version
formula_version
created_at
calculated_at
quality_status
evidence_refs
```

指标追溯：

```text
Canonical Value
→ Formula
→ Function
→ Source Records
→ Raw Asset
```

## 9. Visualization Adapter

```text
Canonical Table
→ Visualization Dataset
├─ Dynamic Table
├─ KPI
├─ Trend
├─ Ranking
├─ Comparison
├─ Distribution
├─ Timeline
├─ Relationship
├─ Geography
├─ Heatmap
└─ Live View
```

前端禁止重新计算业务事实。

## 10. 动态表施工

统一：

```text
Search / Filter / Sort / Group / Column Control
Time Window / Selection / Drill-down / Cross-highlight / Export
```

状态：

```text
Loading / Ready / Empty / Partial / Stale / Degraded / Error
```

## 11. 实时施工

```text
Static
Periodic Refresh
Incremental Update
Streaming
Event-driven
```

每个实时模块：

```text
source_updated_at
received_at
processed_at
visualized_at
latency
freshness_status
```

UI：

```text
LIVE / UPDATING / STALE / DEGRADED / OFFLINE / ERROR
```

## 12. Data Gates

```text
G01 Input
G02 Extraction
G03 Schema
G04 Normalize
G05 Dedup
G06 Function
G07 Canonical
G08 Visualization Dataset
G09 UI
G10 Export
```

任何 FAIL / UNKNOWN / MISSING / MISMATCH 均 BLOCKED。

## 13. Golden Dataset

覆盖：

```text
Table / Text / Image / Event / Note / Topic / KOS / KOC / UGC / Risk / Report / Podcast
```

必须证明：

```text
Canonical == Dynamic Table
Canonical == Chart
Canonical == UI Metric
Canonical == Report
Canonical == Export
```

## 14. Intelligence Modules

### Monitoring

```text
Overview
Real-time
Notes
Topics
Events
Risk
Platform
Time
```

### Event

```text
Identity
Source
Timeline
Volume
Velocity
Spread
Related Notes
Related Topics
Related Creators
Risk
Evidence
Action
Resolution
```

### Risk

```text
Trigger
Severity
Confidence
Evidence
Status
Action
Resolution
```

## 15. KOS

```text
Overview
→ List
→ Drawer
→ Profile
→ Analysis
→ History
→ Recommendation
```

字段：

```text
Identity / Positioning / Content Ability / Content Performance
Distribution / Interaction / Audience Fit / Influence / Risk
Cooperation Value / History / Recommendation / Evidence
```

## 16. KOC

```text
Overview
→ List
→ Drawer
→ Profile
→ Experience
→ Word of Mouth
→ Recommendation
```

重点：

```text
Real Experience / Content Quality / Interaction / Word of Mouth
Spread / Brand Fit / Risk / Evidence
```

## 17. UGC

```text
Original
→ Author / Time / Content
→ Topic / Emotion / Interaction / Spread
→ Brand / Event / Risk / Evidence
```

AI 只能添加分析层，不覆盖 Original。

## 18. Content Production

统一：

```text
Brief
→ Audience
→ Objective
→ Context
→ Key Message
→ Creative Direction
→ Draft
→ AI Assist
→ Human Review
→ Compliance
→ Final
→ Publish
→ Performance
→ Review
```

Template Registry：

```text
XHS Note
Graphic Post
Short Video
Poster
Campaign Copy
Headline
Hook
CTA
Comment Reply
KOS Content
KOC Content
UGC Response
Podcast Repurposing
```

每个模板记录 input/output schema、required/optional fields、validation、review rules、version。

## 19. 内容模板

### XHS

```text
Title → Hook → Scene → Experience/Fact → Detail → Emotion → Turn → Brand/Event → CTA → Tags
```

### Video

```text
0–03 Hook
03–10 Scene
10–25 Information
25–40 Emotional Turn
40–55 Brand/Event
55–60 Ending/CTA
```

### Comment

```text
Original Comment
→ Intent
→ Emotion
→ Risk
→ Strategy
→ AI Draft
→ Human Review
→ Final Reply
→ Outcome
```

## 20. Report System

类型：

```text
Daily / Weekly / Monthly / Annual / Special / Campaign / Risk Alert / Event
```

母结构：

```text
Context
→ Summary
→ Findings
→ Data
→ Visualization
→ Evidence
→ Interpretation
→ Recommendation
```

### Daily

```text
Summary / Key Changes / Events / Risk / Opportunity / Evidence / Actions
```

### Weekly

```text
Overview / Trend / Event / Content / Creator / Risk / Opportunity / Benchmark / Next Week
```

### Monthly

```text
Executive Summary / Performance / Trend / Campaign / Creator / Content / Risk / Benchmark / Insight / Next Month
```

### Special

```text
Question / Context / Evidence / Analysis / Finding / Recommendation
```

## 21. Export

```text
Canonical Data
→ Report / Export Definition
→ Renderer
→ CSV / XLSX / JSON / PDF
```

禁止截图式伪导出。

## 22. Podcast Workspace

Podcast 是平台内部完整 Workspace，共享 Shell、Data、Evidence、AI、Knowledge、Export。

```text
Podcast
├─ Program
├─ Idea Vault
├─ Research
├─ Episodes
├─ Production
├─ Content
├─ Audience
├─ Knowledge
└─ Review
```

## 23. Podcast Program

```text
Overview / Positioning / Audience / Voice / Seasons / Episode Map / Assets
```

## 24. Idea Vault

```text
Daily
→ Hot Topic / Observation / Emotion / Question / Raw Idea

Weekly
→ Candidate / Why Now / Background / Core Question / Discussion Direction

Monthly
→ Theme / Trend / Repeated Question / Social Emotion / Long-term Observation / Knowledge
```

## 25. Podcast Research

```text
Topic / Person / Event / Case / Evidence
```

关系：

```text
Source → Claim → Evidence → Insight → Question
```

## 26. Episode

```text
Title
Description
Core Question
Why Now
Research
Discussion Route
Structure
Time Allocation
Opening
Questions
Emotional Turn
Cognitive Turn
Ending
Production
Publishing
Performance
Review
```

复杂制作进入 Full Workspace。

## 27. Podcast Production

```text
Pre-production
→ Script
→ Recording
→ Timecode
→ Edit
→ Master
→ Publish
```

## 28. Podcast Content

```text
Full Episode
├─ Short Video
├─ Quote
├─ XHS Note
├─ Video
├─ Poster
├─ Social Copy
└─ Comment Response
```

## 29. Podcast Audience / Knowledge / Review

```text
Audience Question
→ Idea Vault
→ Research
→ Episode
```

```text
Episode
→ Transcript
→ Key Points
→ Knowledge
→ New Insight
→ New Idea
```

```text
Performance
→ Feedback
→ What Worked
→ What Failed
→ Why
→ Improvement
→ Experiment
→ Knowledge
```

## 30. AI Boundary

AI：

```text
Extraction / Classification / Summary / Draft / Recommendation / Research Assistance / Pattern Discovery
```

AI 不得成为：

```text
Production Truth
Business Metric Truth
Original Evidence
Final Human Decision
```

记录：

```text
model_version
prompt_version
input
output
confidence
human_edit
final_result
```

## 31. Construction Batches

```text
B00 Baseline Lock
B01 Source Mapping
B02 Data Foundation
B03 UI Foundation
B04 Data Presentation
B05 Intelligence Modules
B06 KOS/KOC/UGC
B07 Content Production
B08 Reports/Export
B09 Podcast
B10 Cross-link / Evidence / Knowledge
B11 Hardening
B12 Audit / Release
```

## 32. P0 / P1 / P2

P0：

```text
Source Map
Canonical Data
Formula / Evidence
Golden Dataset
Shell
Route
Window
State Restoration
```

P1：

```text
Dynamic Table
Visualization
Realtime
Monitoring
KOS/KOC/UGC
Content
Reports
Export
Podcast
```

P2：

```text
Advanced Cross-link
Advanced Realtime
AI Workspace
Historical Pattern Discovery
Experiment System
```

## 33. Page Construction Card

```text
PAGE ID
Parent Module
Route
Purpose
Primary Task
Data Source
Canonical Dataset
Metrics
Visualization
Table
Windows
Actions
Related Objects
Evidence
AI
Realtime
Loading
Empty
Error
Permission
Export
Tests
```

## 34. Metric Construction Card

```text
METRIC ID
Definition
Unit
Formula ID
Function
Dataset
Filter
Time Window
Aggregation
Rounding
Version
Evidence
Test
```

## 35. Visualization Construction Card

```text
VISUAL ID
Type
Dataset
Metrics
Dimension
Time Window
Filters
Aggregation
Update Mode
Interactions
Drilldown
Empty
Error
Export Mapping
```

## 36. Report Construction Card

```text
REPORT ID
Type
Audience
Period
Dataset IDs
Metric IDs
Visual IDs
Evidence IDs
Template Version
Generation Rule
Review Rule
Export Formats
```

## 37. Definition of Done

```text
[ ] 旧实现已找到
[ ] Source Map 已建立
[ ] 复用判断完成
[ ] 数据来源明确
[ ] Canonical Dataset 明确
[ ] Function/Formula 明确
[ ] Window 明确
[ ] Route 明确
[ ] Loading/Empty/Error 明确
[ ] 真实数据已接入
[ ] Visualization Adapter 已接入
[ ] Golden Dataset PASS
[ ] Table/Chart/UI/Report/Export 一致
[ ] Evidence 可追溯
[ ] Audit PASS
[ ] Commit
[ ] Push
[ ] Remote Verify
```

## 38. 最终硬约束

```text
FUNCTION
→ CANONICAL DATA
→ VISUALIZATION
→ UI
→ REPORT
→ EXPORT
```

```text
FEATURE
→ HIERARCHY
→ WINDOW
→ NAVIGATION
→ DATA
→ INTERACTION
```

```text
RESEARCH
→ IMPLEMENTATION
→ TEST
→ EVIDENCE
→ AUDIT
→ RELEASE
```

任何环节不得私自创造第二套事实、第二套指标、第二套 UI 语言或第二套平台 Shell。
