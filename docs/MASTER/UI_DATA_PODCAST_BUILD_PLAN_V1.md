# UI × DATA × CONTENT × REPORT × PODCAST
## Construction Plan V1 — 2026-09-04

> 本文件是 `UI_DATA_PODCAST_RESEARCH_SPEC_V2.md` 的施工执行层。目标不是继续讨论概念，而是把已经确定的 UI、窗口、跳转、统一数据链、动态可视化、KOS/KOC/UGC、舆情、内容制作、报告与 Podcast 逐项映射到真实源码并可验收。

## 0. 施工总原则

```text
真实仓库扫描
→ 现有能力盘点
→ 页面/组件/Route/API/DB 映射
→ 数据链映射
→ 模板/报告映射
→ 复用优先
→ 最小改造
→ 实现
→ 单元测试
→ Golden Dataset 回归
→ UI/交互验收
→ Export 一致性验收
→ Audit
→ Commit
→ Push
→ Remote Verify
```

禁止：凭空重建、平行数据计算、页面自行计算业务指标、假数据验收、只改视觉不接真实数据、只做静态图表、只做静态表格、用 Drawer 替代所有窗口、把 Podcast 做成孤立应用。

---

# 1. 施工前 Gate：源码事实盘点

第一阶段不写新 UI。

执行：

```bash
pwd
find . -maxdepth 6 -type f | sort
rg -n "Shell|sidebar|workspace|route|router|popover|drawer|dialog|modal|table|grid|chart|visual|animation|realtime|websocket|SSE|stream|import|upload|parser|CSV|XLSX|PDF|PPT|PPTX|DOC|OCR|video|audio|ETL|normalize|dedup|schema|function|formula|export|evidence|health|KOS|KOC|UGC|podcast|episode|idea|vault|knowledge" . --glob '!node_modules/**' --glob '!venv/**' --glob '!data/**'
```

形成：

```text
SOURCE MAP
功能/页面
→ 文件
→ symbol/component
→ route
→ API
→ DB/table
→ 当前行为
→ 当前数据源
→ 依赖
→ 测试
→ 可复用项
→ 缺口
→ 修改方案
```

验收：任何要改的页面必须先有 SOURCE MAP 记录。

---

# 2. 施工资产分层

建立以下 Registry：

```text
Page Registry
Window Registry
Route Registry
Component Registry
Data Registry
Metric Registry
Formula Registry
Visualization Registry
Interaction Registry
Template Registry
Report Registry
Evidence Registry
Export Registry
Test Registry
```

每条记录必须有稳定 ID 和版本。

---

# 3. UI Shell 施工顺序

先施工平台骨架，再施工业务页面。

```text
L0 Platform Shell
├─ Global Header
├─ Global Navigation
├─ Workspace Switcher
├─ Command / Search
├─ Notification
├─ User / Settings
└─ Global AI Entry

L1 Workspace
├─ Overview
├─ Module Navigation
├─ Filters
└─ Context Actions

L2 Module
├─ Home / Overview
├─ List
├─ Detail
├─ Analysis
└─ Report / Export
```

禁止每个模块单独造 Shell。

---

# 4. 窗口施工矩阵

```text
Popover
→ Filter / Sort / Quick Action / Small Control

Drawer
→ Note / Event / Topic / KOS / KOC / UGC / Evidence / Preview

Dialog
→ Delete / Publish / Permission / Import Conflict / Risk Action / Short Form

Full Page
→ Object Detail / Analysis / Report / Profile / Knowledge

Full Workspace
→ Complex Analysis / Research / Episode Production / Multi-step Creation

AI Panel
→ Current-context assistance

AI Workspace
→ Multi-turn research / cross-object generation / complex creation
```

每个窗口必须定义：

```text
open trigger
parent context
layer level
route/state
data source
actions
close rule
return state
error state
loading state
empty state
permission state
```

---

# 5. Navigation 施工规则

```text
Module Nav
→ Module Page

List Row
→ Context-preserving Drawer

Drawer
→ View Full
→ Full Page

Drawer
→ Related Object
→ Stack / Replace by relation type

Dangerous Action
→ Confirm Dialog

Complex Task
→ Full Workspace

AI Quick Assist
→ AI Panel

AI Research
→ AI Workspace
```

关闭 Drawer 后恢复：

```text
route
query
filter
sort
pagination
scroll
selection
```

必须测试浏览器 Back、Deep Link、Refresh、Direct URL。

---

# 6. Universal Data Ingestion 施工

统一入口覆盖：

```text
Collector
CSV/XLSX/XLS
PDF/PPT/PPTX/DOC/DOCX
TXT/Markdown/JSON
API/Database
Text
Image/Screenshot
Audio
Video
URL（在现有权限与安全范围内）
```

统一：

```text
Input
→ Raw Asset
→ Parser / OCR / Media Extractor
→ Structured Intermediate Data
```

所有输入必须获得：

```text
asset_id
source_type
received_at
checksum
parse_status
extraction_status
```

---

# 7. 数据链施工：两条合法路径

## Path A：需要计算

```text
External Input
→ Raw Asset
→ Extraction
→ Schema Validation
→ Normalization
→ Deduplication
→ Programming Function
→ Deterministic Calculation
→ Canonical Data Table
```

## Path B：已是标准表

```text
External Table
→ Schema Validation
→ Normalization
→ Deduplication
→ Canonical Data Table
```

两条路径不得绕过质量 Gate。

非表格内容：

```text
Image / Video / PDF / PPT / Audio / Text
→ Extraction
→ Structured Data
→ Function（如需要）
→ Canonical Table
```

如果只有 Evidence，没有可计算字段：

```text
Asset
→ Evidence / Structured Data
```

不得伪造计算结果。

---

# 8. Canonical Table 施工

Canonical Table 是唯一标准事实层。

最少记录：

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

核心指标必须可追溯：

```text
Canonical Value
→ Formula
→ Function
→ Source Records
→ Raw Asset
```

业务页面不得重新定义同一指标。

---

# 9. Visualization Adapter 施工

```text
Canonical Table
→ Visualization Dataset / Adapter
→ Dynamic Table
→ Chart
→ KPI
→ Timeline
→ Relation Graph
→ Map
→ Heatmap
→ Live View
→ Report
→ Export
```

前端只负责呈现、交互和状态，不重新计算业务事实。

---

# 10. Dynamic Table 施工

统一支持：

```text
Search
Filter
Sort
Group
Column Visibility
Time Window
Row Selection
Drill-down
Cross-highlight
Pin
Export
```

统一状态：

```text
Loading
Ready
Empty
Partial
Stale
Degraded
Error
```

同一 Canonical Dataset 的表格、图表、KPI 必须口径一致。

---

# 11. 图表施工矩阵

```text
KPI
→ 单一关键指标

Trend
→ 时间变化

Comparison
→ A/B/C 对比

Ranking
→ Top N

Distribution
→ 结构/比例

Timeline
→ 事件时间序列

Relationship
→ 对象关系

Geography
→ 空间分布

Heatmap
→ 密度

Risk Matrix
→ 风险 × 传播强度

Live Stream
→ 增量实时变化
```

每个图表必须记录：

```text
visualization_id
dataset_id
metric_ids
filter_state
time_window
update_mode
render_version
empty_state
error_state
```

---

# 12. 实时数据施工

区分：

```text
Static
Periodic Refresh
Incremental Update
Streaming
Event-driven
```

每个实时模块记录：

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
LIVE
UPDATING
STALE
DEGRADED
OFFLINE
ERROR
```

大数据集优先增量更新，禁止无条件全量重绘。

---

# 13. 数据一致性 Gate

```text
G01 Input Integrity
G02 Parse / Extraction
G03 Schema
G04 Normalization
G05 Deduplication
G06 Function / Calculation
G07 Canonical Table
G08 Visualization Dataset
G09 UI Consistency
G10 Export Consistency
```

任何：

```text
FAIL / UNKNOWN / MISSING / MISMATCH
```

均不得进入 PASS。

---

# 14. Golden Dataset 施工

建立覆盖以下能力的最小 Golden Dataset：

```text
Raw Input
Table Import
Text Input
Image Extraction
Event
Note
Topic
KOS
KOC
UGC
Risk
Report
Podcast
```

回归链：

```text
Input
→ Canonical
→ Dynamic Table
→ Chart
→ UI
→ Report
→ Export
```

要求：

```text
Canonical == Table
Canonical == Chart
Canonical == UI Metric
Canonical == Report
Canonical == Export
```

---

# 15. KOS 施工

页面：

```text
KOS Overview
→ KOS List
→ KOS Drawer
→ KOS Profile
→ KOS Analysis
→ KOS History
→ KOS Recommendation
```

字段：

```text
Identity
Positioning
Content Ability
Content Performance
Distribution
Interaction Quality
Audience Fit
Influence
Risk
Cooperation Value
History
Recommendation
Evidence
```

---

# 16. KOC 施工

```text
KOC Overview
→ List
→ Drawer
→ Profile
→ Experience
→ Word of Mouth
→ Recommendation
```

重点字段：

```text
Real Experience
Content Quality
Interaction
Word of Mouth
Spread
Brand Fit
Risk
Evidence
```

---

# 17. UGC 施工

```text
UGC Overview
→ Feed / Table
→ Note Drawer
→ Event Relation
→ Risk
→ Evidence
```

必须保留：

```text
Original
AI Analysis
Human Correction
Final Result
```

AI 不得覆盖 Original。

---

# 18. 舆情 / Note / Topic / Event / Risk

统一对象模型：

```text
Identity
→ Source
→ Original
→ Structured Fields
→ Analysis
→ Relations
→ Risk
→ Evidence
→ Action
```

Event：

```text
First Seen
Latest Seen
Peak
Volume
Velocity
Spread
Related Notes
Related Topics
Related Creators
Status
Resolution
```

Risk：

```text
Trigger
Severity
Confidence
Evidence
Status
Action
Resolution
```

---

# 19. 内容生产中心

统一工作流：

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

---

# 20. 内容模板 Registry

必须落地以下模板：

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

每个模板必须记录：

```text
template_id
template_version
input_schema
output_schema
required_fields
optional_fields
validation_rules
review_rules
```

---

# 21. 小红书笔记模板

```text
TITLE
→ HOOK
→ SCENE
→ EXPERIENCE / FACT
→ DETAIL
→ EMOTION
→ TURN
→ BRAND / EVENT
→ CTA
→ TAGS
```

---

# 22. 视频模板

```text
0–03s  HOOK
03–10s SCENE
10–25s INFORMATION
25–40s EMOTIONAL TURN
40–55s BRAND / EVENT
55–60s ENDING / CTA
```

镜头字段：

```text
shot_id
duration
visual
dialogue
subtitle
audio
purpose
emotion
asset_source
```

---

# 23. 评论回复施工

```text
Original Comment
→ Intent
→ Emotion
→ Risk
→ Response Strategy
→ AI Draft
→ Human Review
→ Final Reply
→ Outcome
```

支持：

```text
Auto Monitor
Auto Suggest
Configurable Auto Reply
Manual Approval
```

---

# 24. Report Registry

正式报告类型：

```text
Daily
Weekly
Monthly
Annual
Special /专题
Campaign
Risk Alert
Event Report
```

统一母结构：

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

---

# 25. 日报施工

```text
今日摘要
→ 关键变化
→ 重要事件
→ 风险
→ 机会
→ 核心证据
→ 建议行动
```

必须支持自动生成、人工修订、证据追溯和 PDF/表格导出。

---

# 26. 周报施工

```text
Overview
→ Trend
→ Event
→ Content
→ Creator
→ Risk
→ Opportunity
→ Benchmark
→ Next Week
```

---

# 27. 月报施工

```text
Executive Summary
→ Performance
→ Trend
→ Campaign
→ Creator
→ Content
→ Risk
→ Benchmark
→ Insight
→ Next Month
```

---

# 28. 专题报告施工

```text
Question
→ Context
→ Evidence
→ Analysis
→ Finding
→ Recommendation
```

每个 Finding 必须有 Evidence。

---

# 29. 导出施工

```text
Canonical Data
→ Report Definition / Export Definition
→ Renderer
→ CSV / XLSX / JSON / PDF
```

禁止页面截图式“假导出”。

---

# 30. Podcast Workspace 施工

Podcast 是平台内部完整 Workspace：

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

共享：

```text
Platform Shell
Data
Evidence
AI
Knowledge
Export
```

不创建第二套平台 Shell。

---

# 31. Podcast Program

```text
Overview
Positioning
Audience
Voice
Seasons
Episode Map
Assets
```

---

# 32. Idea Vault

```text
DAILY
→ Hot Topic / Observation / Emotion / Question / Raw Idea

WEEKLY
→ Candidate / Why Now / Background / Core Question / Discussion Direction

MONTHLY
→ Theme / Trend / Repeated Question / Social Emotion / Long-term Observation / Knowledge
```

---

# 33. Podcast Research

```text
Topic
Person
Event
Case
Evidence
```

关系：

```text
Source
→ Claim
→ Evidence
→ Insight
→ Question
```

---

# 34. Episode Workspace

```text
Episode
→ Core Question
→ Why Now
→ Research
→ Discussion Route
→ Structure
→ Time Allocation
→ Opening
→ Questions
→ Emotional Turn
→ Cognitive Turn
→ Ending
→ Production
→ Publishing
→ Performance
→ Review
```

复杂制作必须进入 Full Workspace。

---

# 35. Podcast Production

```text
Pre-production
→ Script
→ Recording
→ Timecode
→ Edit
→ Master
→ Publish
```

---

# 36. Podcast Content Repurposing

```text
FULL EPISODE
├─ Short Video
├─ Quote
├─ XHS Note
├─ Video
├─ Poster
├─ Social Copy
└─ Comment Response
```

核心原则：One Core Idea → Multiple Assets。

---

# 37. Podcast Audience

```text
Growth
Engagement
Comments
Feedback
Topic Preference
Questions
Audience Insight
```

闭环：

```text
Audience Question
→ Idea Vault
→ Research
→ Episode
```

---

# 38. Podcast Knowledge

```text
Episode
→ Transcript
→ Key Points
→ Knowledge
→ Relationship
→ New Insight
→ New Idea
```

---

# 39. Podcast Review

```text
Performance
→ Audience Feedback
→ What Worked
→ What Failed
→ Why
→ Improvement
→ Experiment
→ Knowledge
```

---

# 40. AI 施工边界

AI 可以：

```text
Classification
Extraction
Summarization
Drafting
Recommendation
Research Assistance
Pattern Discovery
```

AI 不可以成为：

```text
Production Truth
Business Metric Truth
Original Evidence
Final Human Decision
```

所有 AI 输出记录：

```text
model_version
prompt_version
input
output
confidence
human_edit
final_result
```

---

# 41. 页面施工优先级

## P0：底层事实

```text
Source Map
Data Registry
Canonical Table
Formula Registry
Evidence Registry
Golden Dataset
```

## P0：平台交互骨架

```text
Shell
Routing
Drawer
Dialog
Full Page
Workspace
State Restoration
```

## P1：数据表现

```text
Dynamic Table
KPI
Trend
Ranking
Timeline
Risk Matrix
Relationship
Realtime State
```

## P1：核心业务

```text
Monitoring
Notes
Events
Topics
Risk
KOS
KOC
UGC
```

## P1：内容与报告

```text
Content Templates
Comment Reply
Daily
Weekly
Monthly
Special Report
Export
```

## P1：Podcast

```text
Program
Idea Vault
Research
Episode
Production
Content
Audience
Knowledge
Review
```

## P2：高级能力

```text
Cross-module Relationship
Advanced Realtime
Advanced AI Workspace
Historical Pattern Discovery
Experiment System
```

---

# 42. 每个页面的施工卡

任何页面完成前必须填写：

```text
PAGE ID
Page Name
Parent Module
Route
Purpose
Primary User Task
Data Source
Canonical Dataset
Metrics
Main Visualization
Table
Windows
Actions
Related Objects
Evidence
AI Capability
Realtime Mode
Loading State
Empty State
Error State
Permission State
Export
Tests
```

---

# 43. 每个组件的施工卡

```text
COMPONENT ID
Parent Page
Purpose
Input
Data Source
State
Interaction
Open Rule
Close Rule
Navigation
Accessibility
Responsive Behavior
Error Behavior
Test ID
```

---

# 44. 每个指标的施工卡

```text
METRIC ID
Name
Definition
Unit
Formula ID
Function
Source Dataset
Filter
Time Window
Aggregation
Rounding
Version
Owner
Evidence
Test Case
```

禁止出现“页面里临时算一下”。

---

# 45. 每个图表的施工卡

```text
VISUAL ID
Chart Type
Dataset
Metrics
Dimension
Time Window
Filters
Aggregation
Update Mode
Interactions
Drilldown Target
Empty State
Error State
Export Mapping
```

---

# 46. 每个报告的施工卡

```text
REPORT ID
Report Type
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

---

# 47. 验收标准

## 数据

```text
同一 Canonical 数据
= 动态表数字
= KPI 数字
= 图表数字
= 报告数字
= 导出数字
```

## UI

```text
正确层级
正确窗口
正确跳转
正确返回状态
正确数据
正确实时状态
```

## 内容

```text
模板字段完整
版本可追溯
AI 与人工边界清晰
原始内容不丢失
```

## 报告

```text
结论有证据
数字可追溯
图表与表格一致
导出与页面一致
```

## Podcast

```text
Idea → Research → Episode → Production → Publish → Audience → Review → Knowledge → Idea
```

闭环必须可实际操作。

---

# 48. 禁止事项

```text
❌ 页面自行计算业务指标
❌ Chart 自己读取另一份数据
❌ Export 自己重新计算
❌ AI 覆盖 Original
❌ 每个页面一套视觉语言
❌ 所有对象都用 Drawer
❌ 所有东西都做成 KPI 卡
❌ 静态图冒充实时
❌ 假数据通过验收
❌ 只测试页面不测试数据链
❌ 新建重复功能而不搜索旧实现
❌ 改结构前不做 Impact Map
```

---

# 49. 施工批次

```text
B00 Baseline Lock
→ 事实基线锁定

B01 Source Mapping
→ 源码资产盘点

B02 Data Foundation
→ Ingestion / Canonical / Formula / Evidence

B03 UI Foundation
→ Shell / Route / Window / State

B04 Data Presentation
→ Table / KPI / Chart / Realtime

B05 Intelligence Modules
→ Monitoring / Note / Topic / Event / Risk

B06 Creator Modules
→ KOS / KOC / UGC

B07 Content Production
→ Templates / Review / Comment / Repurposing

B08 Reports & Export
→ Daily / Weekly / Monthly / Special / Export

B09 Podcast
→ Program / Idea / Research / Episode / Production / Audience / Knowledge / Review

B10 Cross-linking
→ Relationship / Evidence / Knowledge

B11 Hardening
→ Error / Empty / Permission / Performance / Realtime

B12 Audit & Release
→ Golden Dataset / Full Regression / Remote Verify
```

---

# 50. 每批次 Definition of Done

一个批次只有同时满足以下条件才算完成：

```text
[ ] 已找到旧实现
[ ] 已建立源码映射
[ ] 已确认是否复用
[ ] 已定义数据来源
[ ] 已定义 Canonical Dataset
[ ] 已定义窗口层级
[ ] 已定义跳转
[ ] 已定义 Loading/Empty/Error
[ ] 已接真实数据
[ ] 已接 Visualization Adapter
[ ] 已完成测试
[ ] Golden Dataset PASS
[ ] Export PASS
[ ] Evidence 可追溯
[ ] Audit PASS
[ ] Commit
[ ] Push
[ ] Remote Verify
```

---

# 51. 最终系统闭环

```text
EXTERNAL WORLD
      ↓
INGESTION
      ↓
RAW / ASSET
      ↓
EXTRACTION
      ↓
STRUCTURED DATA
      ↓
FUNCTION / VALIDATION
      ↓
CANONICAL TABLE
      ↓
VISUALIZATION ADAPTER
      ↓
┌───────────────┬───────────────┬───────────────┐
│ Dynamic Table │ Chart / Graph │ UI / Workspace│
└───────────────┴───────────────┴───────────────┘
      ↓
CONTENT / INTELLIGENCE / PODCAST
      ↓
REPORT
      ↓
EXPORT
      ↓
EVIDENCE
      ↓
KNOWLEDGE
      ↓
ACTION
      ↓
REVIEW
      ↓
NEXT ITERATION
```

## 最终工程真相

```text
FUNCTION → CANONICAL DATA → VISUALIZATION → UI → REPORT → EXPORT
```

任何环节不得重新定义事实。

```text
FEATURE → HIERARCHY → WINDOW → NAVIGATION → DATA → INTERACTION
```

任何环节不得脱离前一层自行设计。

```text
RESEARCH → IMPLEMENTATION → TEST → EVIDENCE → AUDIT → RELEASE
```

任何研究结论未经实施验证，不得视为生产完成。
