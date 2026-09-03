# UI × INTERACTION × UNIVERSAL DATA × PODCAST
## Research / Execution Specification V2 — 2026-09-04

> 本文件升级并覆盖此前关于 UI、窗口、跳转、数据链、KOS/KOC/UGC、舆情、内容生产与播客的执行口径。它不是视觉 Demo，而是源码实施与验收契约。

## 0. 绝对原则

Find → Audit → Map → Reuse → Implement → Test → Gate → Commit。

禁止：凭空重做；平行 UI；平行计算；页面自行计算业务指标；假数据验收；只做静态视觉；把播客做成孤立工具；把 AI 当 Production Truth。

---

## 1. 先审源码，再定 UI

在任何改动前，必须扫描真实仓库：

```bash
pwd
find . -maxdepth 5 -type f | sort
rg -n "Shell|sidebar|workspace|route|popover|drawer|dialog|modal|table|grid|chart|visual|animation|realtime|websocket|SSE|stream|import|upload|parser|CSV|XLSX|PDF|PPT|PPTX|image|video|OCR|ETL|normalize|dedup|schema|function|export|evidence|health|KOS|KOC|UGC|podcast|episode|idea|vault|knowledge" . --glob '!node_modules/**' --glob '!venv/**' --glob '!data/**'
```

必须形成源码映射表：

```text
功能/页面 → 文件 → symbol/component → route → 当前行为 → 数据源 → 依赖 → 测试 → 修改方案
```

若名称不匹配，继续按 symbol、class、route、API、数据库表、visible text 搜索。不能因为路径名称不同就判定不存在。

---

## 2. UI 层级必须由功能决定

不能先规定“所有东西都用 Drawer”，再强行塞功能。

决策顺序固定：

```text
用户任务
↓
对象复杂度
↓
是否需要持续上下文
↓
是否需要编辑/确认
↓
信息密度
↓
功能层级
↓
窗口类型
↓
跳转方式
```

### Window Matrix

```text
Popover
= 快速、轻量、短时控制
= Workspace / Filter / Sort / Notification / Account / Quick Action

Drawer
= 不离开当前上下文查看对象详情
= Note / Event / Topic / KOS / KOC / UGC / Evidence / Preview

Dialog
= 必须作出明确确认或短表单操作
= Delete / Publish / Permission / Import Conflict / Risk Action

Full Page
= 对象本身具有独立信息架构
= Detail / Analysis / Report / Profile / Knowledge

Full Workspace
= 连续、多步骤、高信息密度任务
= Internal Browser / Complex Analysis / Episode Production / Research

AI Panel
= 当前页面上下文辅助

AI Workspace
= 多轮研究、复杂生成、跨对象任务
```

窗口不是装饰；窗口类型必须反映功能层级。

---

## 3. 动态跳转规则

```text
Navigation → Module Page
List Row → Context-preserving Drawer
Drawer → View Full → Full Page
Drawer → Related Object → Replace/Stack according to relationship
Evidence → Evidence Detail
Edit → Inline Edit or Dialog according to complexity
Dangerous Action → Confirm Dialog
Complex Task → Full Workspace
AI Quick Assist → AI Panel
AI Research/Creation → AI Workspace
```

关闭 Drawer 必须恢复原列表的：

```text
route
query
filter
sort
pagination
scroll position
selection
```

浏览器返回、深链 URL、刷新后状态恢复必须按实际技术栈实现并测试。

---

## 4. UI 视觉方向重新升级

不固守旧版视觉。允许重新设计，但必须从已提供的视觉参考资产与源码现实中提炼，而不是复制某个网站。

参考包应先解包并建立 Reference Matrix：

```text
Reference → Layout → Typography → Density → Motion → Interaction → Data Display → Reusable Principle
```

当前参考资产重点吸收：

```text
编辑感 / 内容层级
模块化构图
高信息密度但不拥挤
沉浸式媒体
精细动效
明确状态变化
卡片与表格的组合
时间线 / 进度 / 关系可视化
```

最终视觉语言：

```text
Editorial Intelligence
×
Operational Precision
×
Dynamic Data
×
Quiet but expressive motion
```

禁止 generic AI dashboard、无意义渐变、Glow 堆砌、巨大 KPI 卡片、每页独立设计语言。

---

## 5. Universal Data Ingestion：所有外部数据统一入口

“外部数据”包含一切：

```text
采集器结果
CSV
XLSX
XLS
PDF
PPT
PPTX
DOC/DOCX
TXT/Markdown
JSON
API
数据库
复制粘贴文本
用户直接输入文字
图片
截图
音频
视频
网页/链接（在现有安全与权限范围内）
```

无论输入形式如何，必须先进入统一 ingestion pipeline。

---

## 6. 数据生产链：必须保留“两条合法路径”

这是本次最重要的修正。

### Path A — 需要计算的数据

```text
External Input
↓
Raw Asset
↓
Parser / OCR / Media Extractor / Connector
↓
Schema Validation
↓
Normalization
↓
Deduplication
↓
Programming Function
↓
Deterministic Calculation
↓
Canonical Data Table
↓
Visualization Adapter Code
↓
Dynamic Table / Chart / UI / Report / Export
```

### Path B — 已经是标准表格的数据

有些输入本身已经是可信、结构明确的表格，且不需要业务再计算：

```text
External Table
↓
Schema Validation
↓
Normalization / Deduplication
↓
Canonical Data Table
↓
Visualization Adapter Code
↓
Dynamic Table / Chart / UI / Report / Export
```

**不能为了形式而重复计算。**
但 Path B 也必须经过 Schema / Integrity Gate，不能绕过验证。

### 非表格输入

```text
Image / Video / PDF / PPT / Text / Audio
↓
Extraction
↓
Structured Intermediate Data
↓
Function（需要计算时）
↓
Canonical Table
```

如果抽取结果只是原始内容而没有形成可计算字段，则允许停在 Structured Data / Evidence 层，不得伪造“已经计算完成”。

---

## 7. Canonical Data Table 的定义

Canonical Table 是系统的**唯一标准事实数据层**，不是普通展示表。

每个核心数据集必须记录：

```text
 dataset_id
 dataset_version
 schema_version
 source_type
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

业务指标必须可追溯到：

```text
Raw Record
→ Function
→ Formula
→ Canonical Value
```

---

## 8. Visualization Adapter

Canonical Table 之后才进入可视化代码。

```text
Canonical Table
↓
Visualization Dataset / Adapter
├─ Dynamic Table
├─ Chart
├─ KPI / Metric
├─ Timeline
├─ Relation Graph
├─ Map
├─ Heatmap
├─ Trend
├─ Stream / Live View
└─ Report / Export
```

前端只负责呈现与交互，不重新定义业务事实。

图表更新应由数据状态驱动，而不是手工刷新页面。Apache ECharts 的动态数据机制也体现了“数据变化驱动图表更新”的工程模式。citeturn2search7turn2search10

---

## 9. 实时动态架构

实时不是“每秒刷新一次页面”。

需要区分：

```text
Static
Periodic Refresh
Incremental Update
Streaming
Event-driven Update
```

每个模块先声明 freshness contract：

```text
source_updated_at
received_at
processed_at
visualized_at
latency
freshness_status
```

UI 状态：

```text
LIVE
UPDATING
STALE
DEGRADED
OFFLINE
ERROR
```

数据更新必须尽量做增量更新；大数据集禁止无条件全量重绘。

实时趋势必须显示时间窗口、更新状态、最后更新时间，而不是让用户猜数字是否最新。

---

## 10. 数据 Gate

```text
G01 Input Integrity
G02 Extraction / Parsing
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

都必须进入：

```text
BLOCKED / NEEDS_REVIEW
```

不得静默使用旧数据冒充新数据。

---

## 11. Golden Dataset

建立最小但覆盖关键业务的 Golden Dataset。

任何以下变化都必须回归：

```text
schema
parser
normalizer
dedup
function
formula
query
aggregation
visualization adapter
export
```

验收：

```text
Canonical Table == Expected
Dynamic Table == Canonical
Chart == Canonical
UI Metric == Canonical
Export == Canonical
```

---

## 12. KOS / KOC / UGC

### KOS

```text
Identity
→ Positioning
→ Content Ability
→ Content Performance
→ Distribution
→ Interaction Quality
→ Audience Fit
→ Influence
→ Risk
→ Cooperation Value
→ History
→ Recommendation
→ Evidence
```

### KOC

```text
Identity
→ Real Experience
→ Content Quality
→ Interaction
→ Word of Mouth
→ Spread
→ Brand Fit
→ Risk
→ Recommendation
→ Evidence
```

### UGC

```text
Original Record
→ Author
→ Time
→ Content
→ Topic
→ Emotion
→ Interaction
→ Spread
→ Brand
→ Event
→ Risk
→ Evidence
```

原始内容必须保留。AI 只能增加分析层。

---

## 13. 舆情 / Note / Topic / Risk

所有对象均遵循：

```text
Identity
→ Source
→ Raw / Original
→ Structured Fields
→ Analysis
→ Relations
→ Risk
→ Evidence
→ Action
```

Event 额外具备：

```text
First Seen
Latest Seen
Timeline
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

Topic 具备时间窗口比较；Risk 必须具备 Trigger / Severity / Confidence / Evidence / Status。

---

# 14. 播客：平台内部的完整附属系统

播客不是外置工具，也不是一个“发布页”。它作为平台内的独立 Workspace，和 KOS 等业务能力处于同级模块地位，同时共享平台 Shell、数据层、Evidence、AI、Knowledge 与 Export 能力。

```text
PLATFORM
├─ Brand / Intelligence Modules
│  ├─ KOS
│  ├─ KOC
│  ├─ UGC
│  ├─ Monitoring
│  ├─ Analysis
│  └─ Reports
│
└─ Podcast Workspace
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

Podcast 有自己的内部层级，但不能创建第二套平台 Shell。

---

## 15. Podcast UI 层级

```text
Podcast Workspace
├─ L1 Program
│  ├ Overview
│  ├ Positioning
│  ├ Audience
│  └ Seasons
│
├─ L1 Idea Vault
│  ├ Daily
│  ├ Weekly
│  └ Monthly
│
├─ L1 Research
│  ├ Topic
│  ├ Person
│  ├ Event
│  ├ Case
│  └ Evidence
│
├─ L1 Episodes
│  ├ Episode List
│  ├ Episode Detail
│  └ Episode Workspace
│
├─ L1 Production
│  ├ Pre-production
│  ├ Recording
│  ├ Editing
│  └ Publishing
│
├─ L1 Content
│  ├ Clips
│  ├ Xiaohongshu
│  ├ Video
│  ├ Poster
│  └ Social Copy
│
├─ L1 Audience
│  ├ Growth
│  ├ Engagement
│  ├ Feedback
│  └ Questions
│
├─ L1 Knowledge
│  ├ Episode Knowledge
│  ├ Research Knowledge
│  └ Cross-reference
│
└─ L1 Review
   ├ Performance
   ├ Feedback
   ├ What Worked
   ├ What Failed
   └ Next Experiment
```

---

## 16. Podcast 动态交互

### Idea

```text
Daily Idea
→ Open Drawer
→ Inspect / Edit
→ Promote
→ Weekly Candidate
→ Research Workspace
```

### Research

```text
Research Item
→ Evidence Drawer
→ Add to Research Set
→ Generate Insight
→ Attach to Episode
```

### Episode

```text
Episode List
→ Detail Drawer
→ View Full
→ Episode Workspace
```

### Production

```text
Episode
→ Pre-production
→ Recording
→ Editing
→ Publishing
→ Performance
```

### Audience

```text
Audience Question
→ Intent / Topic
→ Save to Idea Vault
→ Candidate Episode
```

### Review

```text
Performance / Feedback
→ Review
→ Knowledge
→ New Idea
```

形成闭环：

```text
Idea
→ Research
→ Episode
→ Production
→ Publish
→ Audience
→ Review
→ Knowledge
→ New Idea
```

---

## 17. Podcast Episode Workspace

复杂任务采用 Full Workspace，而不是巨型弹窗：

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Episode Header | Status | Save | Preview | Publish                         │
├───────────────────────┬─────────────────────────────────────────────────────┤
│ Structure             │ Current Section                                    │
│                       │                                                     │
│ Core Question         │ Editor / Research / Script / Outline               │
│ Why Now               │                                                     │
│ Research              │                                                     │
│ Discussion Route      │                                                     │
│ Segment 01            │                                                     │
│ Segment 02            │                                                     │
│ Segment 03            │                                                     │
│ Opening               │                                                     │
│ Ending                │                                                     │
├───────────────────────┴─────────────────────────────────────────────────────┤
│ Evidence | AI Assist | Notes | Version | Knowledge                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

左侧是结构导航，中间是工作区，底部是证据/辅助/版本关系；不是把所有内容塞进一张长卡片。

---

## 18. 内容生产模板

统一模板对象：

```text
Template ID
Version
Input Schema
Prompt Version
Model Version
Output Schema
Human Review
Final Output
Performance
```

覆盖：

```text
Xiaohongshu Note
Video
Poster
Comment Reply
Podcast Publishing Copy
Podcast Clips
```

AI 草稿必须与最终人工确认结果分离。

---

## 19. 动态可视化多元化原则

不是所有数据都画折线图。

根据对象与任务选择：

```text
时间 → Timeline / Area / Line
排名 → Bar / Dot Plot
结构 → Treemap / Stacked
关系 → Network Graph
事件 → Timeline + Event Cluster
风险 → Matrix / Severity Map
传播 → Flow / Network
空间 → Map
密度 → Heatmap
实时 → Streaming / Incremental Chart
文本 → Topic Cluster / Sentiment Distribution
对象详情 → Table + Mini Trend + Evidence
```

交互必须支持合理的：

```text
hover
focus
filter
brush
zoom
drill-down
compare
time-window
pin
cross-highlight
```

但禁止为了“动态”加入无业务意义的动画。

---

## 20. Evidence Everywhere

所有重要事实都可以追溯：

```text
UI Metric
→ Canonical Value
→ Calculation
→ Source Record
→ Evidence
```

点击 Evidence 不应把用户带离上下文；优先使用 Evidence Drawer，必要时进入 Evidence Full Page。

---

## 21. AI 边界

AI：分析、分类、聚类、摘要、关系发现、草稿、研究辅助、建议。

确定性系统：

```text
Raw
Schema
Function
Formula
Canonical Table
Evidence
Final Metric
```

AI 不得未经验证覆盖这些事实层。

---

## 22. 最终验收

```text
[ ] 源码全部完成映射
[ ] 功能决定窗口类型
[ ] 功能决定跳转方式
[ ] Drawer 保留上下文
[ ] Dialog 只承担确认/短表单
[ ] Complex Task 使用 Workspace
[ ] UI 视觉完成升级而非机械沿用旧风格
[ ] 参考资产已转化为设计原则
[ ] 所有外部输入进入统一 ingestion
[ ] 文件/表格/文字/图片/视频/采集结果均有明确处理路径
[ ] Path A 计算链存在
[ ] Path B 直接标准表路径存在
[ ] Canonical Table 是唯一事实层
[ ] Visualization Adapter 独立
[ ] 动态表/图表/UI/导出统一读取 Canonical
[ ] freshness / realtime 状态可见
[ ] Golden Dataset 存在
[ ] 10级 Data Gate 存在
[ ] KOS/KOC/UGC 结构化
[ ] Note/Topic/Event/Risk 有对象关系
[ ] Evidence 可追溯
[ ] Podcast 与平台同 Shell、同数据、同 Evidence、同 AI
[ ] Podcast 是独立 Workspace
[ ] Daily/Weekly/Monthly Idea Vault
[ ] Research → Episode → Production → Publish → Review → Knowledge 闭环
[ ] 内容模板结构化
[ ] 评论回复有人审机制
[ ] 所有关键交互真实可执行
[ ] 无假数据验收
[ ] 无重复业务计算
[ ] 无第二套平台 Shell
[ ] 全部 Gate PASS 后才能 DONE
```

## 23. 外部研究原则

本规格参考并吸收成熟开源工程的通用思想，而非复制实现：

- Apache ECharts：异步加载、数据驱动动态更新、加载状态与增量更新思路。citeturn2search7turn2search10
- shadcn/ui：Drawer 的 Header/Content/Footer 结构、嵌套、snap points、响应式 Dialog/Drawer、Scrollable Body 等交互工程细节；Dialog 强调覆盖层内的明确任务与内容结构。citeturn2search1turn2search4turn2search5
- 数据表格实践：排序、筛选、分页、行选择、可见性与可复用组件应按具体业务行为组合，而不是把所有表格强行做成同一组件。citeturn2search13

所有外部学习只进入 Research → Evidence → Contract → Implementation Specification → Core Implementation → Test → Audit 流程，不直接改变生产真相。
