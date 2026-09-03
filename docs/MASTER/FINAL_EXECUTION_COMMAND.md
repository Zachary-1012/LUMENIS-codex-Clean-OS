# FINAL EXECUTION COMMAND
## UI × DATA × KOS/KOC/UGC × SENTIMENT × CONTENT × PODCAST

STATUS: P0 / FINAL EXECUTION AUTHORITY
DATE: 2026-09-04

你现在执行的不是一次普通 UI 修改，也不是一次页面开发。
这是最终产品系统收口工程：必须在现有源码基础上，把已经确定的 UI 视觉系统、交互层级、数据可信链、业务模块模板、内容生产模板与播客生产系统统一落地。

核心原则只有一句：

**Find → Map → Reuse → Implement → Test → Gate → Commit**

绝不允许：凭空重做、另起一套 UI、另起一套数据计算、另起一套模板、用假数据证明完成、跳过测试后直接标记完成。

---

# 1. 开始前必须完成源码定位

首先：

```bash
pwd
find . -maxdepth 4 -type f | sort
```

然后：

```bash
rg -n "xujing-design-system|design-system|Shell|sidebar|Workspace|workspace|notification|account|popover|drawer|dialog|assistant|evidence|browser|health|智能问答|舆情监测|风险预警|负面监测|笔记|话题监测|话题|舆情分析|事件|事件关系|日历|品牌中心|太古汇|案例库|案例分析|知识库|品牌报告|报告|KOS|KOC|UGC|播客|Podcast|Idea Vault" . --glob '!node_modules/**' --glob '!venv/**' --glob '!data/**'
```

继续定位 CSS / Design Tokens / Components：

```bash
rg -n "font-size|border-radius|box-shadow|--.*color|--.*spacing|--.*radius|icon|modal|drawer|popover|table|chart" . --glob '*.css' --glob '*.html' --glob '*.js' --glob '*.jsx' --glob '*.tsx' --glob '*.vue'
```

如果名称不匹配，按 symbol、class、route、visible text 搜索。不得因为一个文件名不存在就判定功能不存在。

---

# 2. 建立源码映射表

修改之前必须建立：

```text
功能/页面
→ 实际文件路径
→ 实际 symbol/class/function/component
→ 当前行为
→ 当前数据来源
→ 当前路由
→ 需要修改
→ 是否共享组件
→ 测试位置
```

至少定位：

```text
Shell
Top Bar
Sidebar
Workspace Switcher
Global Search
Notification
Account
Design Tokens
Shared Components
Home / 智能问答
List/Table
Detail Drawer
Dialog
AI Assistant
Evidence
Browser Runtime
System Health
Export
KOS
KOC
UGC
舆情事件
笔记
话题监测
风险预警
内容模板
播客模块
Idea Vault
```

---

# 3. UI 最终层级

```text
L0 Product Shell
├─ L1 Top System Bar
│  ├─ Workspace Switcher → Popover
│  ├─ Global Search → Search Results
│  ├─ Notification → Popover
│  └─ Account → Popover
├─ L2 Left Navigation
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

导航固定：

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

---

# 4. UI 交互硬规则

```text
Navigation → Page
List Item → Right Detail Drawer
Full View → Detail Page
Evidence → Evidence Drawer/Page
Edit → Edit State/Dialog
Dangerous Action → Confirm Dialog
Complex Task → Full Workspace
AI Entry → AI Panel
AI Complex Task → AI Workspace
```

Popover 只做轻量控制；Drawer 做对象详情；Dialog 做有后果的确认；Full Workspace 做复杂持续任务。

Drawer 关闭必须尽可能恢复原页面、筛选、搜索、滚动上下文。

---

# 5. UI 视觉硬规则

统一使用现有 Design System。

目标语言：

```text
黑 / 白 / 灰主导
克制字体
小型线性 Icon
清晰层级
数据优先
弱边框
克制圆角
轻动效
```

禁止：

```text
巨大 Icon
巨大标题
巨大 KPI
巨大 Card
大量渐变
蓝紫 generic AI 风格
Glow
过度阴影
海报式 Dashboard
页面各自设计语言
第二套 Design System
第二套 Shell
```

---

# 6. P0 数据可信链

所有数据必须走：

```text
Raw
↓
Schema Validation
↓
Normalization
↓
Deduplication
↓
Deterministic Function
↓
Canonical Data Table
↓
Data Quality Gate
↓
Visualization Dataset
↓
UI
↓
Export Dataset
↓
Export Validation
↓
Release
```

前端不得重新计算业务指标。

导出模块不得重新计算业务指标。

所有核心指标必须有：

```text
metric_id
formula_version
calculation_version
dataset_version
calculated_at
source_record_ids
```

---

# 7. 六级数据 Gate

```text
GATE 01 Schema
GATE 02 Integrity
GATE 03 Calculation
GATE 04 Canonical Table
GATE 05 Visualization
GATE 06 Export
```

任一：

```text
FAIL
UNKNOWN
MISSING
MISMATCH
```

均必须：

```text
BLOCKED
```

不得默认通过。

页面数字、动态表数字、图表数字、导出数字必须与 Canonical Table 一致。

建立 Golden Dataset：代码修改后必须自动回归已知 Expected Output。

---

# 8. KOS 模块执行模板

KOS 不是简单的“达人列表”。

对象链：

```text
Creator Identity
↓
定位
↓
内容能力
↓
内容表现
↓
传播表现
↓
互动质量
↓
受众匹配
↓
影响力
↓
风险
↓
合作价值
↓
历史表现
↓
推荐动作
```

必须至少支持：

```text
KOS Profile
内容记录
传播数据
互动数据
内容主题
受众画像（以现有可用数据为准）
合作记录
风险记录
历史趋势
Evidence
```

所有评分必须可解释、可复算、可追溯。

---

# 9. KOC 模块执行模板

```text
KOC Identity
↓
真实体验
↓
内容质量
↓
互动质量
↓
口碑价值
↓
扩散能力
↓
品牌匹配
↓
风险
↓
合作建议
```

不要把 KOC 简化为粉丝量排序。

---

# 10. UGC 模块执行模板

```text
UGC Record
↓
作者
↓
发布时间
↓
内容
↓
主题
↓
情绪
↓
互动
↓
传播
↓
关联品牌
↓
关联事件
↓
风险
↓
Evidence
```

UGC 是用户真实表达的数据层，不得被 AI 摘要替代原始内容。

---

# 11. 舆情事件模板

事件必须从“单条笔记”提升到事件对象：

```text
Event
├─ Event ID
├─ Event Name
├─ First Seen
├─ Latest Seen
├─ Related Notes
├─ Related Topics
├─ Related Creators
├─ Sentiment
├─ Volume
├─ Interaction
├─ Spread
├─ Peak
├─ Trend
├─ Risk
├─ Status
├─ Timeline
├─ Evidence
└─ Action
```

事件生命周期：

```text
发现
→ 聚合
→ 判断
→ 追踪
→ 峰值
→ 扩散
→ 风险判断
→ 处置
→ 复盘
```

---

# 12. 笔记模板

每条笔记至少形成：

```text
Note Identity
↓
Source
↓
Author
↓
Publish Time
↓
Title
↓
Content
↓
Media
↓
Topic
↓
Brand
↓
Sentiment
↓
Interaction
↓
Risk
↓
Event
↓
Evidence
```

原始内容必须保留，AI 只能生成辅助分析层。

---

# 13. 话题监测模板

```text
Topic
↓
Topic Identity
↓
Volume
↓
Discussion
↓
Growth
↓
Velocity
↓
Related Notes
↓
Related Creators
↓
Sentiment
↓
Event
↓
Risk
↓
Trend
↓
Evidence
```

必须支持时间窗口比较。

---

# 14. 风险预警 / 负面监测

风险对象：

```text
Risk Signal
↓
Source
↓
Trigger
↓
Severity
↓
Confidence
↓
Related Object
↓
Evidence
↓
Recommended Action
↓
Status
↓
Resolution
```

AI 可以辅助判断，但不得绕过已有确定性规则和人工最终判断机制。

---

# 15. 内容生产模板系统

内容模板必须结构化，而不是一堆 Word 文案。

## 小红书笔记

```text
标题
↓
Hook
↓
场景
↓
事实 / 体验
↓
细节
↓
情绪 / 用户价值
↓
自然转折
↓
品牌 / 活动信息
↓
CTA
↓
Tags
```

## 视频

```text
Hook
↓
Scene
↓
Core Information
↓
Emotional Turn
↓
Brand / Event
↓
Ending
```

每个镜头：

```text
画面
字幕 / 台词
时长
信息目的
素材来源
```

## 海报

```text
主标题
副标题
核心信息
时间
地点
参与方式
注意事项
CTA
```

## 评论回复

```text
Original Comment
↓
Intent
↓
Emotion
↓
Risk
↓
Reply Strategy
↓
AI Draft
↓
Human Review
↓
Final Reply
↓
Outcome
```

必须支持自动监测、自动生成草稿、人工审核、最终回复与结果记录。

---

# 16. 内容模板质量 Gate

每份 AI 生成内容必须记录：

```text
template_id
template_version
prompt_version
model_version
input
output
AI confidence
human modification
final output
```

不得让 AI 生成内容直接覆盖最终发布内容。

---

# 17. 播客模块：完整生产系统

播客不是一个“内容发布页面”。

它必须是长期认知生产闭环：

```text
发现
→ 记录
→ 筛选
→ 研究
→ 选题
→ 结构
→ 讨论
→ 录制
→ 编辑
→ 发布
→ 反馈
→ 复盘
→ 知识沉淀
→ Idea Vault
```

---

# 18. 播客 Idea Vault 三级体系

必须保留：

```text
Daily
Weekly
Monthly
```

## Daily

记录当天发现的：

```text
社会热点
人的情绪
日常观察
有争议的问题
值得追问的现象
```

## Weekly

从 Daily 中筛选、聚合、研究。

输出：

```text
候选选题
为什么值得讨论
相关背景
核心问题
潜在讨论方向
```

## Monthly

形成月度主题资产：

```text
主题趋势
重复出现的问题
社会情绪
人物 / 事件
长期观察
知识沉淀
```

---

# 19. 播客单期模板

每期至少包含：

```text
Episode Title
↓
Description
↓
Core Question
↓
Why Now
↓
Research
↓
Discussion Route
↓
Segment Structure
↓
Time Allocation
↓
Opening
↓
Host / Co-host Roles
↓
Key Questions
↓
Emotional / Cognitive Turns
↓
Ending
↓
Editing Notes
↓
Publishing Copy
↓
Feedback
↓
Review
↓
Knowledge Extraction
```

播客核心不是“说完一个主题”，而是形成可持续的认知资产。

---

# 20. 播客与知识库连接

```text
Daily Idea
↓
Weekly Candidate
↓
Research
↓
Episode
↓
Transcript / Key Points
↓
Knowledge
↓
New Ideas
↓
Idea Vault
```

因此播客不能成为孤立模块。

---

# 21. AI 在所有模块中的边界

AI 可以：

```text
分析
分类
聚类
摘要
生成草稿
发现关系
提出建议
```

AI 不可以未经验证直接：

```text
覆盖数据库事实
修改 Evidence
覆盖确定性指标
自动执行危险操作
绕过人工最终判断
```

---

# 22. 所有模块统一对象关系

最终必须形成：

```text
Brand
├─ Note
├─ Topic
├─ Event
├─ KOS
├─ KOC
├─ UGC
├─ Risk
├─ Evidence
├─ Report
└─ Content

Podcast
├─ Idea
├─ Research
├─ Episode
├─ Transcript
├─ Knowledge
└─ Idea Vault
```

对象之间必须通过明确 ID / relation 连接，不允许靠页面文本“猜关系”。

---

# 23. 实施顺序

严格执行：

```text
P0-1 源码盘点
P0-2 UI 映射
P0-3 数据链映射
P0-4 模块映射
P0-5 模板映射
P0-6 测试映射

P1 UI 收口
P1 数据 Canonical Table
P1 Data Gates
P1 KOS/KOC/UGC
P1 舆情事件/笔记/话题/风险
P1 内容模板
P1 播客

P2 集成
P2 Evidence
P2 AI
P2 Export
P2 Regression
```

不要因为某个 P1 页面漂亮就绕过 P0 数据门禁。

---

# 24. 最终验收标准

必须同时满足：

```text
[ ] 所有 UI 元素有源码定位
[ ] 所有页面有层级
[ ] 所有主要操作有确定跳转
[ ] Popover / Drawer / Dialog / Full Workspace 正确
[ ] UI 使用统一 Design System
[ ] Raw → Function → Table → Visualization → Export 链完整
[ ] 六级 Data Gate 存在
[ ] Golden Dataset 存在
[ ] 数据可复算
[ ] 数据可追溯
[ ] KOS 模板完成
[ ] KOC 模板完成
[ ] UGC 模板完成
[ ] 舆情事件模板完成
[ ] 笔记模板完成
[ ] 话题模板完成
[ ] 风险模板完成
[ ] 内容生产模板完成
[ ] 评论回复模板完成
[ ] 播客完整闭环完成
[ ] Daily / Weekly / Monthly Idea Vault 完成
[ ] 播客与知识库连接
[ ] Evidence 连接
[ ] AI 边界明确
[ ] Export 与 Canonical Table 一致
[ ] Golden Dataset PASS
[ ] Regression PASS
[ ] 无重复 UI 系统
[ ] 无重复业务计算
[ ] 无虚假完成状态
```

---

# 25. 最重要的执行命令

你现在不要问“要不要重写”。

你必须：

**找到 → 对照 → 复用 → 修正 → 补齐 → 测试 → Gate → Commit。**

如果已经存在：复用。

如果部分存在：修正。

如果只是缺少连接：连接。

如果真正不存在：建立最小共享实现。

不要创造平行系统。

不要破坏已有业务逻辑。

不要跳过数据验证。

不要用静态假数据证明功能完成。

不要只做视觉 Demo。

最终目标不是“看起来完成”，而是：

**源码真实存在 + 数据真实流动 + 计算可复算 + UI 与数据一致 + 所有交互可执行 + Evidence 可追溯 + 测试可验证。**

只有达到这个标准，才能标记 DONE。
