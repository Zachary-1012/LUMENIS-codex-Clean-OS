# LUMENIS UI/UX Master V1.0
## 序境 · 智能操作系统 前端设计总规范

> **文档地位**：LUMENIS Intelligence OS 前端设计唯一总规范。覆盖品牌、IA、Workspace、页面、Token、组件、状态、动效、多端适配、前端文件规划、Visual QA。
> **基准**：LUMENIS-INTELLIGENCE-OS-DUAL-CORE-ARCHITECTURE-v1.0 + LUMENIS-UI-STANDARD-v1.0 + 线上 main 源码事实。
> **职责边界**：本文档仅定义 UI/UX 与前端设计落地。不修改 ZBC/OSAI 后端、数据库、AI Agent、业务规则、权限架构、产品层级。
> **版本**：v1.0 · 2026-09-05 · 状态：CANONICAL · WINDOW-A 交付

---

## 0. 范围与原则

### 0.1 设计原则
- 先结构后视觉，先 IA 后组件，先 Contract 后代码
- 一个工作台，不是几十个菜单
- Command Home 不是 Dashboard——告诉用户发生什么、为什么、下一步做什么
- Data-driven Motion：没有真实数据变化不动画
- 形态融合物理不合并：ZBC (Production Core) + OSAI (Intelligence Core) 共享设计语言，不共享产品 IA

### 0.2 相关文档
| 文档 | 路径 | 关系 |
|---|---|---|
| 双核架构 | `00-GOVERNANCE/LUMENIS-INTELLIGENCE-OS-DUAL-CORE-ARCHITECTURE-v1.0.md` | 产品架构权威 |
| UI Standard | `docs/design/LUMENIS-UI-STANDARD-v1.0.md` | Token/组件/动效详细规格 |
| 本文件 | `docs/design/LUMENIS-UI-UX-MASTER-v1.0.md` | 前端设计总规范 + 落地规划 |

---

## 1. 品牌规范

### 1.1 品牌命名
| 层级 | 中文 | 英文 | 用法 |
|---|---|---|---|
| 母品牌 | 序境 | LUMENIS | 所有产品的根品牌 |
| 平台 | 序境智能平台 | LUMENIS Intelligence Platform | 正式平台名 |
| 系统 | 序境智能操作系统 | LUMENIS Intelligence OS | 产品总称 |
| 生产核 | 序境生产中枢 | LUMENIS Production Core | ZBC 产品层名 |
| 智能核 | 序境智能中枢 | LUMENIS Intelligence Core | OSAI 产品层名 |

**禁止**：Xujing / Xujing Intelligence 作为正式产品名（仅历史仓库名保留）。代码中变量/类名/文件路径可用 `lumenis` / `lm` 前缀。

### 1.2 品牌语言规则
- 中文为产品主语言（UI 文案、用户可见内容）
- 英文为系统/API/代码正式语言（变量、API endpoint、CSS class、文件命名）
- 韩文 서경 为国际化语言包，不进入产品逻辑
- 用户可见术语逐字保留，不自行翻译或改写

### 1.3 品牌视觉签名
- **微光银 (Silver Shimmer)**：品牌标题斜向扫光 + 卡片按真实 status 极淡呼吸。始终浅色高级，不深不艳。
- **芥子纳须弥**：品牌宣言，用于 Command Home Hero 区，Display 34px/700。
- **Logo 处理**：暂用文字标 "序境 LUMENIS"，1.5px 细线 icon 辅助。禁巨型 Logo、禁大字报。

---

## 2. IA 总览

### 2.1 全局结构
```
LUMENIS Intelligence OS
│
├── Global Shell
│   ├── Global Header（Workspace 切换 / Search / Runtime 状态 / User）
│   └── Sidebar（一级导航）
│
├── Command Home（全局首页，六区）
│
├── Intelligence Workspace
│   ├── Overview
│   ├── AI Workspace
│   ├── Agents
│   ├── Skills
│   ├── Evidence
│   ├── Evaluation
│   └── Learning
│
├── Production Workspace
│   ├── Overview
│   ├── Subjects
│   ├── Brands
│   ├── Content
│   ├── Public Opinion
│   ├── Events
│   ├── Risk
│   ├── KOS / KOL / KOC
│   ├── Cases
│   └── Reports
│
├── Research Workspace
│   ├── Research
│   ├── Discoveries
│   ├── Technology
│   ├── Evidence
│   ├── Findings
│   └── Decisions
│
└── Operations（系统级，不做业务一级）
    ├── System
    ├── Runtime
    ├── Tasks
    ├── Logs
    ├── Security
    └── Settings
```

### 2.2 导航层级
- L0：Global Shell（Header + Sidebar）
- L1：Workspace（Intelligence / Production / Research / Operations）
- L2：功能页（每个 Workspace 下的页面）
- L3：详细工作区（页面内的 Detail / Drill-down）
- L4：Drawer / Modal（最深层，不超过 L4）

**禁**：L5 及以下深度。超过说明 IA 需要重组。

### 2.3 Sidebar 结构
```
┌─────────────────────┐
│ 序境 LUMENIS        │  ← Brand Mark
├─────────────────────┤
│ HOME                │  ← Command Home
├─────────────────────┤
│ INTELLIGENCE        │  ← Section Label (11px uppercase)
│ Overview            │
│ AI Workspace        │
│ Agents              │
│ Skills              │
│ Evidence            │
│ Evaluation          │
│ Learning            │
├─────────────────────┤
│ PRODUCTION          │
│ Overview            │
│ Subjects            │
│ Brands              │
│ Content             │
│ Public Opinion      │
│ Events              │
│ Risk                │
│ KOS / KOL / KOC     │
│ Cases               │
│ Reports             │
├─────────────────────┤
│ RESEARCH            │
│ Research            │
│ Discoveries         │
│ Technology          │
│ Evidence            │
│ Findings            │
│ Decisions           │
├─────────────────────┤
│ OPERATIONS          │
│ System              │
│ Runtime             │
│ Tasks               │
│ Logs                │
│ Security            │
│ Settings            │
└─────────────────────┘
```

Sidebar：Regular Glass，240px 宽（compact 200px，折叠 64px 仅图标），当前项用 1.5px 左侧指示条 + text-primary。

---

## 3. Workspace 定义

### 3.1 Command Home（全局首页）
**目的**：告诉用户现在发生什么、为什么发生、下一步做什么。不是数据展示墙。

**六区结构**：
| 区 | 名称 | 内容 | 组件 |
|---|---|---|---|
| 01 | System State | LIVE 状态、采集健康、数据新鲜度、最后更新 | Status Bar + Metric |
| 02 | Intelligence Pulse | AI 活动、研究进展、学习信号 | Card + Timeline |
| 03 | Active Risks | 当前风险预警（≤5，按严重度排序） | Risk Card + Status Dot |
| 04 | Active Tasks | 进行中任务（≤5） | Task Card + Progress |
| 05 | Recent Evidence | 最新证据链（≤5） | Evidence Card + Timeline |
| 06 | Recommended Actions | 系统建议下一步（≤3） | Action Card + Button |

**Hero 区**：品牌宣言 "芥子纳须弥" + Identity Glass 大 Pill 搜索/AI 入口 + 微光银扫光。

### 3.2 Intelligence Workspace
**目的**：AI 工作、Agent 管理、Skill 编排、证据、评估、学习。

| 页面 | 核心结构 | 关键组件 |
|---|---|---|
| Overview | 智能域总览：AI 状态 / Agent 活动 / Skill 使用 / Evidence 流 | Metric + Card + Timeline |
| AI Workspace | Input → Context → Retrieval → Reasoning → Analysis → Evidence → Decision → Action | AI Input + Message + Evidence Chain + Confidence |
| Agents | Agent Center：每个 Agent = Mission → Skills → Permissions → Tasks → Execution → Evidence → Evaluation | Agent Card + Table + Drawer |
| Skills | Skill Hub：All / My / Recommended / Running / Evaluations / Factory | Skill Card + Table + Filter |
| Evidence | Evidence Chain：Task → Requirement → Skill → Agent → Action → File → Data → Test → Result → Evidence → Decision → Commit → Lifecycle | Timeline + Table + Drawer |
| Evaluation | 评估矩阵：Product / AI / Data / Function / UI / UX / Runtime / Stability / Accuracy / Regression | Table + Chart + Metric |
| Learning | 学习闭环：Research → Finding → Evidence → Decision → Product Improvement | Timeline + Card + Knowledge Graph |

### 3.3 Production Workspace
**目的**：调用 ZBC 真实生产能力——主体、品牌、内容、舆情、事件、风险、KOS、案例、报告。

| 页面 | 核心结构 | 关键组件 |
|---|---|---|
| Overview | 生产域总览：采集状态 / 主体命中 / 舆情量 / 风险 / 报告 | Metric + Chart + Status |
| Subjects | 主体管理：主体词表 / 命中统计 / 排除词 / 主体画像 | Table + Badge + Drawer |
| Brands | 品牌情报：Brand Profile / 竞品 / 品类 / 趋势 | Card + Table + Chart |
| Content | 内容库：笔记 / 评论 / 内容类型 / 去重状态 | Table + Filter + Drawer |
| Public Opinion | 舆情监测：情感 / 趋势 / 风险 / 话题 / 来源 | Chart + Table + Timeline |
| Events | 事件中心：营销/传播/舆情三类事件 + 生命周期 + event_relation | Timeline + Card + Graph |
| Risk | 风险预警：风险列表 / 严重度 / 状态 / 处置 | Risk Card + Table + Status Dot |
| KOS/KOL/KOC | 传播主体：六维画像 / 内容能力 / 传播能力 / 品牌关系 | Table + Profile Card + Metric |
| Cases | Case Intelligence：案例 / 品牌 / 账号 / 事件 / 内容 / 关系 / 标签 | Table + Card + Drawer |
| Reports | 报告中心：日报/周报/月报/年报/专题 + 生成链 | Report Card + Table + Timeline |

### 3.4 Research Workspace
**目的**：研究、发现、技术雷达、证据、结论、决策。

| 页面 | 核心结构 | 关键组件 |
|---|---|---|
| Research | 研究中心：进行中研究 / 研究队列 / 研究方法 | Card + Table + Timeline |
| Discoveries | 发现列表：新发现 / 已验证 / 已采纳 | Card + Tag + Status |
| Technology | 技术雷达：技术扫描 / 评估 / 采纳建议 | Radar Chart + Table + Card |
| Evidence | 研究证据：来源 / 验证状态 / 可信度 | Table + Evidence Card |
| Findings | 结论：研究结论 / 影响评估 / 建议 | Card + Metric + Timeline |
| Decisions | 决策记录：决策 / 依据 / 执行状态 / 结果 | Timeline + Card + Status |

**铁律**：外部研究必经 Research → Evidence → Finding → Internal Proposal → Human Review → Implementation，禁止网上发现直接进 Core。

### 3.5 Operations（系统级）
**目的**：系统运行、任务、日志、安全、设置。不做业务一级。

| 页面 | 核心结构 |
|---|---|
| System | 系统状态 / 版本 / 服务健康 / 依赖 |
| Runtime | 运行时 / 采集调度 / Auth 状态 / 冷却 |
| Tasks | 任务队列 / 进行中 / 历史 / 失败 |
| Logs | 系统日志 / 审计日志 / 错误日志 |
| Security | 权限 / API Key / 访问控制 / 审计 |
| Settings | 偏好 / 通知 / 主题 / 语言 / 集成 |

---

## 4. 页面结构规范

### 4.1 通用页面骨架
每个功能页统一遵循：
```
Context（当前域/对象/时间范围）
  → Decision（本页支持的判断/动作）
    → Data（关键指标 ≤4 个）
      → Evidence（趋势/分布/对比/事件/告警）
        → Detail（下钻对象/明细，Drawer 优先）
          → Action（基于判断的操作）
```

### 4.2 页面布局模板
```
┌──────────────────────────────────────────────────┐
│ Global Header                                    │
├──────────┬───────────────────────────────────────┤
│          │ Page Header                           │
│          │  Title + Context + Actions            │
│ Sidebar  ├───────────────────────────────────────┤
│          │ Key Metrics（≤4 个 Metric Card）      │
│          ├───────────────────────────────────────┤
│          │ Main Content                          │
│          │ （Chart / Table / Timeline / Card）   │
│          │                                       │
│          ├───────────────────────────────────────┤
│          │ Detail / Evidence（按需，Drawer 优先）│
└──────────┴───────────────────────────────────────┘
```

### 4.3 页面内分区规则
- 首屏：Page Header + Key Metrics（不滚动可见）
- 主体：Main Content（Chart/Table/Timeline），内容有界不无限下滑
- 详情：Drawer 从右侧滑出，不离开当前页
- 操作：Page Header 右侧 Action Bar，单页最多 1 个主按钮

### 4.4 Command Home 专属结构
```
┌──────────────────────────────────────────────────┐
│ Global Header                                    │
├──────────────────────────────────────────────────┤
│ Hero：芥子纳须弥 + Identity Glass AI 入口        │
│ （微光银扫光，Display 34px）                     │
├──────────────────────────────────────────────────┤
│ 01 System State（LIVE + 采集 + 数据新鲜度）      │
├──────────────────┬───────────────────────────────┤
│ 02 Intelligence  │ 03 Active Risks               │
│ Pulse            │ （≤5，按严重度）              │
├──────────────────┼───────────────────────────────┤
│ 04 Active Tasks  │ 05 Recent Evidence            │
│ （≤5）           │ （≤5）                        │
├──────────────────┴───────────────────────────────┤
│ 06 Recommended Actions（≤3，主按钮）             │
└──────────────────────────────────────────────────┘
```

---

## 5. Design Token（摘要）

> 完整规格见 `LUMENIS-UI-STANDARD-v1.0.md` 第 2 章。此处为前端实现必需的核心 Token。

### 5.1 色彩
- 前缀：`--lm-`
- Light Canvas `#F5F4F1` / Surface `#FFFFFF` / Text Primary `#1C1C1E`
- Dark Canvas `#111111` / Surface `#171717` / Text Primary `#F7F7F5`
- 状态色（Apple-style）：Success `#34C759` / Info `#007AFF` / Warning `#FF9500` / Danger `#FF3B30` / AI `#AF52DE` / Unknown `#8E8E93`
- 微光银：`--lm-silver-50..500` + `--lm-shine-band`

### 5.2 字体
- 栈：`-apple-system, "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif`
- 层级：Display 34/700 → H1 22/700 → H2 17/700 → H3 15/600 → Body 15/400 → Caption 13/400 → Label 11/700 → Metric 20-28/700
- 仅 400 和 600/700 字重

### 5.3 间距/圆角
- 间距（8px 栅格）：4/8/12/16/20/32/48
- 圆角：8/12/16/20/9999

### 5.4 Liquid Glass
- Regular Glass（导航）：blur(20px) saturate(180%) + elevated surface
- Clear Glass（覆盖层）：blur(30px) + rgba(255,255,255,0.6)
- Identity Glass（AI 入口/品牌）：Regular + 微光银扫光
- 禁 glass-on-glass；内容/列表/表格用实色 Surface

---

## 6. 组件清单与规范

### 6.1 组件总览（40 组件，6 类）

#### Layout（5）
| 组件 | 规格 | 用途 |
|---|---|---|
| Global Header | Sticky，高 48px，Regular Glass | Workspace 切换/Search/Runtime/User |
| Sidebar | 240px，Regular Glass，可折叠 64px | 一级导航 |
| Workspace Container | padding 20px，max-width 自适应 | 页面内容容器 |
| Page Header | Title + Context + Actions | 每页顶部 |
| Breadcrumb | 13px，text-secondary | 层级导航 |

#### Navigation（5）
| 组件 | 规格 | 用途 |
|---|---|---|
| Tab | 下划线式，240ms 切换 | 同级内容切换 |
| Pill Tab | 胶囊，9999 圆角 | 筛选/视图切换 |
| Sidebar Item | 1.5px 左指示条，hover 微亮 | 导航项 |
| Bottom Tab Bar | Mobile，Regular Glass，5 入口 | 移动端导航 |
| Command Bar | ⌘K 触发，Identity Glass | 全局命令/搜索 |

#### Input（9）
| 组件 | 规格 | 用途 |
|---|---|---|
| Button Primary | 16px 圆角，15px/600，bg text-primary | 最重要操作，单页最多 1 个 |
| Button Secondary | 16px 圆角，outline | 次要操作 |
| Button Ghost | 无边框，hover 微背景 | 三级操作 |
| Button Danger | bg Danger，仅破坏性操作 | 删除/重置 |
| Input | 12px 圆角，1.5px Focus 边框 | 文本输入 |
| Select | 12px 圆角，下拉 | 选择 |
| Search | Pill 20px 圆角，Identity Glass（首页）/ 实色（页内） | 搜索 |
| Filter | Pill Tab + Dropdown 组合 | 数据筛选 |
| Toggle / Checkbox / Radio | 系统风格，48px 触控区 | 开关/选择 |

#### Data Display（10）
| 组件 | 规格 | 用途 |
|---|---|---|
| Card | 16px 圆角，实色 Surface，细边框，极淡阴影 | 信息容器 |
| Metric | 大数字 20-28px/700 + 标签 + 趋势微缩 | 单指标 |
| Table | 行高 44px，hover 高亮，Sort/Filter/Search | 结构化数据 |
| List | 行高 48px，左图标+标题+副标题+右状态 | 列表数据 |
| Chart | 一页 ≤3，服务判断 | 趋势/分布/对比 |
| Timeline | 竖向，节点+连线，可点击下钻 | 事件/生命周期/证据链 |
| Badge | 8px 圆角，11px/700 | 标签/分类 |
| Status Dot | 10px 圆点 + 文字，双通道 | 状态指示 |
| Tag | 12px 圆角，可移除 | 标签/分类 |
| Progress | 细条 4px，圆角 | 进度/加载 |

#### Feedback（7）
| 组件 | 规格 | 用途 |
|---|---|---|
| Toast | 顶部滑入，3s 自动消失，z-index 500 | 操作反馈 |
| Modal | 居中，20px 圆角，320ms，禁模态叠模态 | 短任务/确认 |
| Drawer | 右侧滑出，Clear Glass，420ms，宽 480px | 详情/深层信息 |
| Tooltip | 12px 圆角，hover 触发，桌面增强 | 辅助说明 |
| Skeleton | 灰色块脉冲，预留空间不跳版 | 加载中 |
| Empty State | 细线 icon + 一句话 + 主按钮 | 无数据 |
| Error State | 错误码 + 人话解释 + 重试/反馈 | 错误 |

#### AI-specific（4）
| 组件 | 规格 | 用途 |
|---|---|---|
| AI Input | Identity Glass 大 Pill，支持多模态附件 | AI 入口 |
| AI Message | 用户/AI 双气泡，AI 带 Evidence 引用 | 对话 |
| AI Thinking | 六态指示（Processing/Researching/Verifying/Needs Review/Completed/Failed） | AI 状态 |
| Evidence Chain | 横向/纵向链路，节点可点击 | AI 结果溯源 |

---

## 7. 状态系统

### 7.1 数据状态
| 状态 | 视觉 | 规则 |
|---|---|---|
| Loading | Skeleton 预留空间 | 不跳版，不转圈 |
| Empty | Empty State 组件 | 说明为什么空 + 下一步 |
| Error | Error State 组件 | 错误码 + 人话 + 重试 |
| Success | Toast + 状态更新 | 不弹大 Modal |
| No Data | 区分"真的没有"和"采集失败" | 采集失败显式标记，不伪装成 0 |

### 7.2 AI 六态
| 状态 | 颜色 | 指示 |
|---|---|---|
| AI_PROCESSING | Info 蓝 | 处理中 |
| AI_RESEARCHING | AI 紫 | 研究中 |
| AI_VERIFYING | Warning 橙 | 验证中 |
| AI_NEEDS_REVIEW | Warning 橙 | 需人工复核 |
| AI_COMPLETED | Success 绿 | 已完成 |
| AI_FAILED | Danger 红 | 失败 |

### 7.3 实时状态
```
● LIVE          Last Update: 00:00:03
Collection      RUNNING
Data            FRESH
```
状态必须明确：LIVE / 最后更新 / 采集状态 / 数据新鲜度。

### 7.4 采集状态（ZBC 生产）
SUCCESS / NO_NEW_DATA / RISK_WARNING / NEED_VERIFY / BLOCKED / SESSION_EXPIRED / COLLECT_ERROR / COOLING_DOWN

每个状态有对应 Status Dot 颜色 + 文字标签，不仅依赖颜色。

---

## 8. 动效规范

### 8.1 模式
- **Stagger**：多元素级联进入，小延迟瀑布式
- **Multi-translate**：多段 translate 沿不同方向冲入
- **Float**：轻柔持续漂移（品牌区/AI 状态）
- **Continue-through**：部件持续移动后聚合落位

### 8.2 时长
| 档位 | 时长 | 用途 |
|---|---|---|
| Instant | 120ms | Hover / Press / 状态点 |
| Fast | 180ms | Panel / Card |
| Tab | 240ms | Tab 切换 |
| Page | 320ms | 页面进入 |
| Modal/AI | 420ms | Modal / Drawer / AI 思考 |

### 8.3 铁律
- **Data-driven Motion**：没有真实数据变化不动画
- 真变才动一次；持续状态按真实 status 呼吸
- 禁写死循环（微光银品牌签名除外且极淡）
- 禁假实时/假绿色/假增长/视觉欺骗
- 超过 420ms 必须可跳过
- `prefers-reduced-motion` 全部关闭
- 数据更新用 opacity 200ms 淡入 + FLIP 动画 + count-up，不跳版

---

## 9. 响应式与多端适配

### 9.1 断点
| 断点 | 宽度 | 导航 | 工作区 |
|---|---|---|---|
| Desktop Wide | ≥1440px | Sidebar 240px | 多列 |
| Desktop Standard | 1024–1439px | Sidebar 240px | 双列/自适应 |
| Desktop Compact | 768–1023px | Sidebar 折叠 64px | 单列 |
| Tablet | 481–767px | 顶部导航 + 抽屉 | 单列 |
| Mobile | ≤480px | 底部 Tab Bar | 单列全宽 |

### 9.2 Web 端
- 完整功能：分析/管理/审计/配置
- Sidebar + Header + Workspace 三栏
- Command Bar (⌘K) 全局可用
- 多列布局 flex-wrap，禁写死固定列数

### 9.3 Desktop App（Windows / macOS）
- 复用 Web 技术栈（Electron/Tauri 或 PWA），不做原生 UI 重写
- 窗口适配：最小宽度 1024px，支持 resize
- Windows：标题栏系统风格，内容区 Web
- macOS：交通灯按钮左侧，内容区 Web，支持原生拖拽
- 全局快捷键：⌘K (Command Bar) / ⌘1-4 (Workspace 切换) / ⌘, (Settings)
- 系统托盘：最小化到托盘，实时状态通知
- 不做平台特定 UI 分叉，同一套 Design Token

### 9.4 Mobile 端
- 不是重做手机版产品，是 LUMENIS Mobile 体验层
- 底部 Tab Bar（Regular Glass）：Home / Intelligence / Production / Research / More
- 中央 AI 入口可 Identity Glass 凸起
- 主要做：查看 / 查询 / 分析 / 启动任务 / 审批 / 查看 Evidence / 查看风险
- 不做：Git 操作 / 复杂配置 / 批量编辑
- 触控目标 ≥48px，正文 ≥14px
- Drawer 从底部滑出（Bottom Sheet），非右侧
- 列表默认折叠，复杂图表拆分查看

### 9.5 多语言
- 中文主语言，英文系统语言，韩文语言包
- 切换自动适配文字长度，禁溢出挤压
- 日期/数字/货币按 locale 格式化

---

## 10. 前端文件规划

### 10.1 目录结构
```
templates/                          # Jinja2 模板（Flask 渲染）
├── base.html                       # Global Shell（Header + Sidebar + 容器）
├── home/
│   └── command_home.html           # Command Home
├── intelligence/
│   ├── overview.html
│   ├── ai_workspace.html
│   ├── agents.html
│   ├── skills.html
│   ├── evidence.html
│   ├── evaluation.html
│   └── learning.html
├── production/
│   ├── overview.html
│   ├── subjects.html
│   ├── brands.html
│   ├── content.html
│   ├── public_opinion.html
│   ├── events.html
│   ├── risk.html
│   ├── kos.html
│   ├── cases.html
│   └── reports.html
├── research/
│   ├── research.html
│   ├── discoveries.html
│   ├── technology.html
│   ├── evidence.html
│   ├── findings.html
│   └── decisions.html
├── operations/
│   ├── system.html
│   ├── runtime.html
│   ├── tasks.html
│   ├── logs.html
│   ├── security.html
│   └── settings.html
├── components/                     # 可复用 partial
│   ├── _header.html
│   ├── _sidebar.html
│   ├── _metric_card.html
│   ├── _status_bar.html
│   ├── _empty_state.html
│   ├── _error_state.html
│   └── _skeleton.html
└── errors/
    ├── 404.html
    └── 500.html

static/
├── css/
│   ├── lumenis-tokens.css          # Design Token（CSS Variables，Light/Dark）
│   ├── lumenis-reset.css           # Reset + base typography
│   ├── lumenis-layout.css          # Shell/Sidebar/Header/Workspace 布局
│   ├── lumenis-components.css      # 40 组件样式
│   ├── lumenis-pages.css           # 页面专属样式
│   ├── lumenis-motion.css          # 动效 keyframes + transition
│   └── lumenis-responsive.css      # 断点 + Mobile 适配
├── js/
│   ├── lumenis-core.js             # 核心：env/API client/state/router
│   ├── lumenis-components.js       # 组件行为（Tab/Drawer/Modal/Toast/Toggle）
│   ├── lumenis-navigation.js       # Sidebar/Header/Command Bar/Bottom Tab
│   ├── lumenis-ai-workspace.js     # AI Workspace 交互
│   ├── lumenis-charts.js           # 图表封装（ECharts 或轻量方案）
│   ├── lumenis-motion.js           # 数据驱动动效引擎
│   └── lumenis-icons.js            # 细线 SVG icon 注册表（licon 函数）
├── assets/
│   ├── icons/                      # 24x24 SVG line icons（1.5px stroke）
│   └── fonts/                      # （如自托管字体）
└── index.html                      # PWA manifest / Service Worker（如需要）
```

### 10.2 命名规范
- CSS 类：`lm-` 前缀，BEM 变体 `lm-card__title--large`
- JS 模块：`lumenis-*.js`，IIFE 封装，不污染全局
- 模板：`snake_case.html`，partial 用 `_` 前缀
- Token：`--lm-` 前缀，semantic 命名 `--lm-text-primary` 非 `--lm-color-gray-800`
- 数据属性：`data-lm-*` 用于 JS 钩子

### 10.3 CSS 加载顺序
```
lumenis-tokens.css → lumenis-reset.css → lumenis-layout.css
→ lumenis-components.css → lumenis-pages.css → lumenis-motion.css → lumenis-responsive.css
```

### 10.4 JS 加载策略
- `lumenis-core.js` 首屏必需，同步加载
- 其余模块 defer，按页面按需加载
- 图表库（如 ECharts）CDN 加载，失败回退静态表格
- 无构建依赖（零 Webpack/Vite），纯 HTML/CSS/JS，Flask 直出

---

## 11. 页面清单（30 页）

| # | Workspace | 页面 | 模板路径 | 优先级 |
|---|---|---|---|---|
| 1 | Global | Command Home | `home/command_home.html` | P0 |
| 2 | Intelligence | Overview | `intelligence/overview.html` | P1 |
| 3 | Intelligence | AI Workspace | `intelligence/ai_workspace.html` | P0 |
| 4 | Intelligence | Agents | `intelligence/agents.html` | P1 |
| 5 | Intelligence | Skills | `intelligence/skills.html` | P1 |
| 6 | Intelligence | Evidence | `intelligence/evidence.html` | P1 |
| 7 | Intelligence | Evaluation | `intelligence/evaluation.html` | P2 |
| 8 | Intelligence | Learning | `intelligence/learning.html` | P2 |
| 9 | Production | Overview | `production/overview.html` | P0 |
| 10 | Production | Subjects | `production/subjects.html` | P1 |
| 11 | Production | Brands | `production/brands.html` | P1 |
| 12 | Production | Content | `production/content.html` | P1 |
| 13 | Production | Public Opinion | `production/public_opinion.html` | P0 |
| 14 | Production | Events | `production/events.html` | P1 |
| 15 | Production | Risk | `production/risk.html` | P0 |
| 16 | Production | KOS/KOL/KOC | `production/kos.html` | P1 |
| 17 | Production | Cases | `production/cases.html` | P1 |
| 18 | Production | Reports | `production/reports.html` | P1 |
| 19 | Research | Research | `research/research.html` | P2 |
| 20 | Research | Discoveries | `research/discoveries.html` | P2 |
| 21 | Research | Technology | `research/technology.html` | P2 |
| 22 | Research | Evidence | `research/evidence.html` | P2 |
| 23 | Research | Findings | `research/findings.html` | P2 |
| 24 | Research | Decisions | `research/decisions.html` | P2 |
| 25 | Operations | System | `operations/system.html` | P1 |
| 26 | Operations | Runtime | `operations/runtime.html` | P1 |
| 27 | Operations | Tasks | `operations/tasks.html` | P1 |
| 28 | Operations | Logs | `operations/logs.html` | P2 |
| 29 | Operations | Security | `operations/security.html` | P2 |
| 30 | Operations | Settings | `operations/settings.html` | P1 |

**P0（6 页）**：Command Home, AI Workspace, Production Overview, Public Opinion, Risk, System
**P1（14 页）**：Intelligence Overview/Agents/Skills/Evidence, Production Subjects/Brands/Content/Events/KOS/Cases/Reports, Operations Runtime/Tasks/Settings
**P2（10 页）**：Intelligence Evaluation/Learning, Research 全部, Operations Logs/Security

---

## 12. 组件清单（40 组件）

| 类别 | 组件 | CSS 类 | JS 模块 | 优先级 |
|---|---|---|---|---|
| Layout | Global Header | `.lm-header` | navigation | P0 |
| Layout | Sidebar | `.lm-sidebar` | navigation | P0 |
| Layout | Workspace Container | `.lm-workspace` | — | P0 |
| Layout | Page Header | `.lm-page-header` | — | P0 |
| Layout | Breadcrumb | `.lm-breadcrumb` | — | P1 |
| Navigation | Tab | `.lm-tab` | components | P0 |
| Navigation | Pill Tab | `.lm-pill-tab` | components | P1 |
| Navigation | Sidebar Item | `.lm-sidebar__item` | navigation | P0 |
| Navigation | Bottom Tab Bar | `.lm-bottom-tab` | navigation | P1 |
| Navigation | Command Bar | `.lm-command-bar` | navigation | P1 |
| Input | Button Primary | `.lm-btn--primary` | components | P0 |
| Input | Button Secondary | `.lm-btn--secondary` | components | P0 |
| Input | Button Ghost | `.lm-btn--ghost` | components | P1 |
| Input | Button Danger | `.lm-btn--danger` | components | P1 |
| Input | Input | `.lm-input` | components | P0 |
| Input | Select | `.lm-select` | components | P0 |
| Input | Search | `.lm-search` | components | P0 |
| Input | Filter | `.lm-filter` | components | P1 |
| Input | Toggle/Checkbox/Radio | `.lm-toggle` | components | P1 |
| Data | Card | `.lm-card` | — | P0 |
| Data | Metric | `.lm-metric` | — | P0 |
| Data | Table | `.lm-table` | components | P0 |
| Data | List | `.lm-list` | components | P1 |
| Data | Chart | `.lm-chart` | charts | P0 |
| Data | Timeline | `.lm-timeline` | components | P1 |
| Data | Badge | `.lm-badge` | — | P0 |
| Data | Status Dot | `.lm-dot` | — | P0 |
| Data | Tag | `.lm-tag` | components | P1 |
| Data | Progress | `.lm-progress` | components | P1 |
| Feedback | Toast | `.lm-toast` | components | P0 |
| Feedback | Modal | `.lm-modal` | components | P0 |
| Feedback | Drawer | `.lm-drawer` | components | P0 |
| Feedback | Tooltip | `.lm-tooltip` | components | P2 |
| Feedback | Skeleton | `.lm-skeleton` | — | P0 |
| Feedback | Empty State | `.lm-empty` | — | P0 |
| Feedback | Error State | `.lm-error` | — | P0 |
| AI | AI Input | `.lm-ai-input` | ai-workspace | P0 |
| AI | AI Message | `.lm-ai-msg` | ai-workspace | P0 |
| AI | AI Thinking | `.lm-ai-thinking` | ai-workspace | P0 |
| AI | Evidence Chain | `.lm-evidence` | ai-workspace | P1 |

---

## 13. Visual QA 标准

### 13.1 每页必过清单
- [ ] 10 条设计 DNA 逐条对照
- [ ] 色值全部来自 `--lm-` Token，无硬编码
- [ ] 字号/字重符合层级表
- [ ] 间距为 4/8/12/16/20/32/48 之一
- [ ] 圆角为 8/12/16/20/9999 之一
- [ ] 玻璃符合 Liquid Glass 铁律（仅导航/悬浮/瞬态，禁 glass-on-glass）
- [ ] 无 emoji 当正式 icon
- [ ] 无可爱化元素、无大字报、无巨型 Logo
- [ ] 无模态叠模态
- [ ] 无内容溢出/遮挡/截断
- [ ] 正文对比度 ≥4.5:1
- [ ] 单页最多 1 个主按钮
- [ ] 状态色仅用于状态点+文字，不作大面积背景
- [ ] 页面层级 ≤L4
- [ ] 不无限下滑，重要信息一屏完成

### 13.2 交互 QA
- [ ] 所有按钮/链接有 hover/press 反馈
- [ ] Drawer/Modal 可关闭（ESC + 遮罩点击 + 关闭按钮）
- [ ] Table 支持 Sort/Filter/Search
- [ ] 实时数据更新不跳版（skeleton 预留 + opacity 淡入）
- [ ] 动效数据驱动，无假动画
- [ ] Loading 有 skeleton，不白屏
- [ ] Empty/Error 有明确状态和下一步
- [ ] Command Bar (⌘K) 可用
- [ ] 表单有验证和错误提示

### 13.3 响应式 QA
- [ ] Desktop Wide (≥1440) 布局正常
- [ ] Desktop Standard (1024-1439) 布局正常
- [ ] Desktop Compact (768-1023) Sidebar 折叠正常
- [ ] Tablet (481-767) 顶部导航+抽屉正常
- [ ] Mobile (≤480) 底部 Tab Bar + 单列正常
- [ ] 触控目标 ≥48px
- [ ] 移动端正文 ≥14px
- [ ] 多列 flex-wrap，无固定列数写死

### 13.4 无障碍 QA
- [ ] 文本对比度 ≥4.5:1，非文本 ≥3:1
- [ ] 状态不仅依赖颜色（点+文字双通道）
- [ ] `:focus-visible` 2px 实线
- [ ] `prefers-reduced-motion` 关闭全部动效
- [ ] `prefers-reduced-transparency` 玻璃降级实色
- [ ] 语义化 HTML，ARIA label 完整
- [ ] 键盘可导航（Tab/Enter/Esc）

### 13.5 多端 QA
- [ ] Windows Chrome/Edge 渲染正常
- [ ] macOS Safari/Chrome 渲染正常
- [ ] Mobile iOS Safari 渲染正常
- [ ] Mobile Android Chrome 渲染正常
- [ ] 中/英/韩切换无溢出挤压
- [ ] 日期/数字按 locale 格式化

### 13.6 性能 QA
- [ ] 首屏 LCP <2.5s
- [ ] CSS/JS 无未使用的大块加载
- [ ] 图表库 CDN 失败回退静态表格
- [ ] 无持续高频动画空转
- [ ] 实时刷新有节流（≥3s 间隔）

---

## 14. 实施路径

### P0（地基 + 核心页面）
1. `lumenis-tokens.css`（Design Token 实现）
2. `lumenis-reset.css` + `lumenis-layout.css`（Shell 布局）
3. Global Header + Sidebar 组件
4. Command Home（六区 + Hero + AI 入口）
5. AI Workspace
6. Production Overview + Public Opinion + Risk
7. System (Operations)
8. 核心组件：Card/Metric/Table/Chart/Status Dot/Timeline/Drawer/Modal/Toast/Skeleton/Empty/Error

### P1（生产域完整 + 智能域核心）
9. Production 剩余页面（Subjects/Brands/Content/Events/KOS/Cases/Reports）
10. Intelligence Overview/Agents/Skills/Evidence
11. Operations Runtime/Tasks/Settings
12. 剩余组件 + 动效系统 + 响应式

### P2（研究域 + 完善）
13. Research 全部页面
14. Intelligence Evaluation/Learning
15. Operations Logs/Security
16. Mobile 适配 + Desktop App 封装 + PWA

---

*本文件为 LUMENIS Intelligence OS 前端设计总规范 v1.0。WINDOW-A 交付，不涉及后端/DB/AI/业务规则修改。*
*Token/组件/动效详细规格见 LUMENIS-UI-STANDARD-v1.0.md。产品架构见 LUMENIS-INTELLIGENCE-OS-DUAL-CORE-ARCHITECTURE-v1.0.md。*
*下一步：等用户指令后，从 P0 第 1 步 lumenis-tokens.css 开始实现。*
