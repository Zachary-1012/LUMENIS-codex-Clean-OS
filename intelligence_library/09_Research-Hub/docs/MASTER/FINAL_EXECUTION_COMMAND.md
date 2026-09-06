# FINAL EXECUTION COMMAND

本文件是 UI、数据可信链、KOS/KOC/UGC、舆情、内容生产、播客及知识沉淀的统一执行母指令。

## 绝对原则

Find → Map → Reuse → Implement → Test → Gate → Commit。

禁止凭空重做、第二套 UI、第二套数据计算、第二套模板、假数据验收、跳过测试。

## 1. 源码定位

```bash
pwd
find . -maxdepth 4 -type f | sort
rg -n "xujing-design-system|design-system|Shell|sidebar|Workspace|workspace|notification|account|popover|drawer|dialog|assistant|evidence|browser|health|智能问答|舆情监测|风险预警|负面监测|笔记|话题监测|话题|舆情分析|事件|事件关系|日历|品牌中心|太古汇|案例库|案例分析|知识库|品牌报告|报告|KOS|KOC|UGC|播客|Podcast|Idea Vault" . --glob '!node_modules/**' --glob '!venv/**' --glob '!data/**'
```

找不到精确文件名时，继续用 symbol/class/route/visible text 搜索，不得直接宣布不存在。

修改前必须建立：功能 → 实际路径 → symbol/class/function → 当前行为 → 数据来源 → 路由 → 需要修改 → 测试位置。

## 2. UI

层级：

```text
L0 Shell
├─ L1 Top Bar
│  ├─ Workspace Switcher → Popover
│  ├─ Global Search → Search Results
│  ├─ Notification → Popover
│  └─ Account → Popover
├─ L2 Sidebar
├─ L3 Page
│  ├─ Header
│  ├─ Description
│  ├─ Actions
│  ├─ Filter/Query
│  ├─ Primary Content
│  └─ Detail
└─ L4 Overlay
   ├─ Popover
   ├─ Drawer
   ├─ Dialog
   ├─ Full Workspace
   └─ AI Assistant
```

导航：总览/智能问答；监测/舆情监测、风险预警、负面监测、笔记、官方、话题监测、话题；分析/舆情分析、事件、事件关系、日历；品牌资产/品牌中心、太古汇、案例库、案例分析、知识库、品牌报告、Evidence；产出/报告；系统/系统健康、内部浏览器、Evidence、设置。

交互：Navigation→Page；List→Right Drawer；Full View→Detail Page；Evidence→Evidence Drawer/Page；Edit→Edit/Dialog；Dangerous Action→Confirm Dialog；Complex Task→Full Workspace；AI→AI Panel；复杂 AI→AI Workspace。

视觉：黑白灰主导、克制字体、小型线性 Icon、弱边框、克制圆角、轻动效、数据优先。禁止巨大 Icon/标题/KPI/Card、蓝紫 generic AI 风格、Glow、过度渐变、第二套 Shell/Design System。

## 3. P0 数据可信链

```text
Raw → Schema → Normalize → Deduplicate → Deterministic Function → Canonical Table → Data Gate → Visualization Dataset → UI → Export Dataset → Export Gate → Release
```

前端、图表、导出均不得自行重新计算业务指标。核心指标必须有 metric_id、formula_version、calculation_version、dataset_version、calculated_at、source_record_ids。

六级 Gate：Schema / Integrity / Calculation / Canonical Table / Visualization / Export。FAIL 或 UNKNOWN 都 BLOCKED。

建立 Golden Dataset；代码、公式、聚合、Schema、数据库查询变更必须跑回归。页面、动态表、图表、导出必须与 Canonical Table 一致。所有核心数字必须可追溯到函数、记录和 Evidence。

## 4. KOS

Identity → 定位 → 内容能力 → 内容表现 → 传播 → 互动质量 → 受众匹配 → 影响力 → 风险 → 合作价值 → 历史表现 → 推荐动作。

评分可解释、可复算、可追溯；不得简化成粉丝量排名。

## 5. KOC

Identity → 真实体验 → 内容质量 → 互动质量 → 口碑价值 → 扩散能力 → 品牌匹配 → 风险 → 合作建议。

## 6. UGC

Record → 作者 → 时间 → 内容 → 主题 → 情绪 → 互动 → 传播 → 品牌 → 事件 → 风险 → Evidence。

原始用户表达必须保留，AI 摘要不能替代原文。

## 7. 舆情事件

Event → ID/名称 → 首次/最近出现 → Related Notes/Topics/Creators → Sentiment → Volume → Interaction → Spread → Peak → Trend → Risk → Status → Timeline → Evidence → Action。

生命周期：发现 → 聚合 → 判断 → 追踪 → 峰值 → 扩散 → 风险 → 处置 → 复盘。

## 8. 笔记 / 话题 / 风险

笔记：Identity → Source → Author → Time → Title → Content → Media → Topic → Brand → Sentiment → Interaction → Risk → Event → Evidence。

话题：Identity → Volume → Discussion → Growth → Velocity → Notes → Creators → Sentiment → Event → Risk → Trend → Evidence，并支持时间窗口比较。

风险：Signal → Source → Trigger → Severity → Confidence → Related Object → Evidence → Action → Status → Resolution。

## 9. 内容生产模板

小红书：标题 → Hook → 场景 → 事实/体验 → 细节 → 情绪/用户价值 → 转折 → 品牌/活动信息 → CTA → Tags。

视频：Hook → Scene → Core Information → Emotional Turn → Brand/Event → Ending；每镜头记录画面、字幕/台词、时长、信息目的、素材来源。

海报：主标题 → 副标题 → 核心信息 → 时间 → 地点 → 参与方式 → 注意事项 → CTA。

评论：原评论 → 意图 → 情绪 → 风险 → 回复策略 → AI 草稿 → 人工审核 → 最终回复 → 结果。

内容资产记录 template_id、template_version、prompt_version、model_version、input、output、confidence、human modification、final output。

## 10. 播客完整模块

播客是长期认知生产系统，不是单一发布页面。

```text
发现 → 记录 → 筛选 → 研究 → 选题 → 结构 → 讨论 → 录制 → 编辑 → 发布 → 反馈 → 复盘 → 知识沉淀 → Idea Vault
```

Idea Vault 固定三级：Daily / Weekly / Monthly。

Daily：社会热点、人的情绪、日常观察、有争议的问题、值得追问的现象。

Weekly：从 Daily 筛选聚合并研究，形成候选选题、为什么值得讨论、背景、核心问题、讨论方向。

Monthly：主题趋势、重复问题、社会情绪、人物/事件、长期观察、知识沉淀。

单期模板：Episode Title → Description → Core Question → Why Now → Research → Discussion Route → Segment Structure → Time Allocation → Opening → Host/Co-host Roles → Key Questions → Emotional/Cognitive Turns → Ending → Editing Notes → Publishing Copy → Feedback → Review → Knowledge Extraction。

播客与知识库必须连接：Daily Idea → Weekly Candidate → Research → Episode → Transcript/Key Points → Knowledge → New Ideas → Idea Vault。

## 11. 对象关系

Brand：Note / Topic / Event / KOS / KOC / UGC / Risk / Evidence / Report / Content。

Podcast：Idea / Research / Episode / Transcript / Knowledge / Idea Vault。

所有关系使用明确 ID，不允许靠页面文字猜关系。

## 12. AI 边界

AI 可做分析、分类、聚类、摘要、草稿、关系发现、建议；不得未经验证覆盖数据库事实、确定性指标、Evidence、Canonical Table 或危险操作。

## 13. 执行与验收

顺序：P0 源码盘点/映射/数据链/模块/模板/测试 → P1 UI/Canonical/Data Gates/KOS/KOC/UGC/舆情/内容/播客 → P2 集成/Evidence/AI/Export/Regression。

完成标准：源码真实存在、数据真实流动、计算可复算、UI 与数据一致、交互可执行、Evidence 可追溯、测试可验证。

任何 FAIL/UNKNOWN 必须阻断 Merge/Release/Export。

最终只允许在全部 Gate 通过后标记 DONE。
