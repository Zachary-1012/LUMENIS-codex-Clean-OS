# ZBC 页面级细化设计 V1.1

> 基于 Design System V1.1（芥子纳须弥 · 深青绿 #0F766E · 默认浅色双主题）
> 三域：ZBMP(7入口) / CTH(6入口) / SYSTEM(5入口)
> 所有页面遵循六态：Loading / Empty / Error / Success / Degraded / Permission Denied

---

## 通用布局规范（所有页面共用）

```
┌─────────────────────────────────────────────────────────┐
│  Sidebar(240px)          │  Topbar(56px)                │
│  ┌──────────────────┐    │  [页面标题]  [搜索] [操作]    │
│  │ Logo 序境        │    ├──────────────────────────────┤
│  │ ZBMP|CTH|SYSTEM  │    │                              │
│  ├──────────────────┤    │      Main Content            │
│  │ 域导航(6-7项)    │    │   (KPI卡片 + 图表 + 表格)    │
│  │                  │    │                              │
│  ├──────────────────┤    │                              │
│  │ 用户/设置        │    │                              │
│  └──────────────────┘    │                              │
└──────────────────────────┴──────────────────────────────┘
```

- Sidebar 固定 240px，选中态左侧 3px #0F766E 色条
- Topbar 56px，左侧页面标题(H2 17px/600)，右侧搜索+操作按钮
- 内容区内边距 24px，卡片间距 16px
- 卡片圆角 12px，边框 1px #E8E8E8(浅)/#2F2F2F(深)
- 所有数据卡片必须有：label(11px) + value(24px/700) + change(11px)
- 空数据显示 "暂无数据" + 引导操作，禁止显示 0 冒充

---

## 一、ZBMP · Brand Intelligence（品牌智能域）

### 1. ZBMP Overview（品牌总览）

**页面目标**：一屏回答"品牌现在表现如何？声量/传播/竞争/增长/风险"

**布局**：
- Topbar：Brand Overview + 时间筛选(今日/7天/30天/自定义) + 导出
- 第一行：4 张 KPI 卡片
  - 今日声量（渐变 Teal Glow）+ 环比变化
  - 活跃品牌（156/199）
  - KOS 互动量（渐变 Slate Mist）
  - 风险事件（有风险时红色高亮）
- 第二行：2 列
  - 左(2/3)：声量趋势面积图（近7天，可切换30天）
  - 右(1/3)：业态分布横向条形图（时尚/餐饮/美妆/其他）
- 第三行：2 列
  - 左(1/2)：品牌声量 TOP10 表格（品牌名/声量/环比/风险标签）
  - 右(1/2)：增长机会卡片（AI 生成的增长建议，带 evidence 链接）

**API**：`/api/zbmp/overview`、`/api/zbmp/metrics?range=7d`
**六态**：Loading=骨架屏；Empty=引导"开始采集"；Error=重试按钮；Degraded=部分数据缺失标"数据延迟"

---

### 2. ZBMP Brand（品牌库）

**页面目标**：管理 199 品牌画像、业态映射、增长指标

**布局**：
- Topbar：Brand + 搜索框 + 业态筛选 + "+ 新增品牌"
- 页内 Tab：品牌列表 | 品牌画像 | 增长指标
- 品牌列表 Tab：
  - 表格：品牌Logo/名称/业态/声量/环比/风险状态/操作
  - 支持排序、筛选、分页
- 品牌画像 Tab（点击品牌进入）：
  - 左侧：品牌基本信息（名称/业态/入驻时间/官方账号）
  - 右侧：声量趋势 + 内容分布 + KOS 关联 + 风险历史
- 增长指标 Tab：
  - 品牌增长排名（声量增长率/互动增长率/新客增长）
  - 跨模块聚合，不单独设导航入口

**API**：`/api/zbmp/brands`、`/api/brand-industry`、`/api/zbmp/brands/{id}`
**注意**：199 品牌数据来自 subject_rules.py BRAND_PROFILES，禁止硬编码修改

---

### 3. ZBMP Content（内容智能）

**页面目标**：笔记/文案/创意/话题活动的内容管理

**布局**：
- Topbar：Content + 平台筛选(小红书/抖音/微博/B站) + 搜索
- 页内 Tab：笔记库 | 创意文案 | 话题活动
- 笔记库：瀑布流/表格切换，显示笔记封面/标题/品牌/互动量/采集时间
- 创意文案：AI 生成的文案列表，带评分和使用状态
- 话题活动：topic_campaigns 数据，活动卡片（名称/时间/参与品牌/声量/状态）

**API**：`/api/notes`、`/api/creative`、`/api/web-topics`、`/api/topic-campaigns`

---

### 4. ZBMP KOS（达人运营）

**页面目标**：KOL/KOS/KOC 全链路管理（最大模块，页内 Tab 拆分）

**布局**：
- Topbar：KOS + 搜索 + 平台筛选 + 批量操作
- 页内 Tab：达人库 | 付费管理 | 执行跟踪 | 归因分析 | 专业号
- 达人库：
  - 达人卡片网格（头像/名称/平台/粉丝量/互动率/报价/标签）
  - 筛选：平台/粉丝量级/业态/报价区间
- 付费管理：kos_paid_plans 数据，计划卡片+状态
- 执行跟踪：kos_executions 数据，任务状态流（待执行/进行中/已完成/异常）
- 归因分析：kos_attribution，**禁止固定公式**，使用 config/kos_platform_rules.json 平台规则驱动
- 专业号：professional_accounts + professional_metrics

**API**：`/api/kos/*`（kos_routes.py 全部路由）
**数据精准性**：粉丝量/互动量必须是采集真实值，缺失标 null/unknown，禁止估算填充

---

### 5. ZBMP Competition（竞品监测）

**页面目标**：对标品牌声量对比、差异化分析（代码待建，定位核心差异化）

**布局**：
- Topbar：Competition + 品牌选择器(最多对比4个) + 时间范围
- 第一行：对比 KPI 行（每个品牌一列：声量/互动/增长率/风险）
- 第二行：声量趋势对比折线图（多品牌叠加）
- 第三行：
  - 左：内容主题对比（各品牌内容分布雷达图）
  - 右：差异化洞察卡片（AI 分析，带 evidence）
- 底部：竞品动作时间线（新品/活动/舆情事件）

**API**：`/api/zbmp/competition`（新建）、`/api/brand-industry`
**状态**：功能骨架已建，数据需从 brand-industry 扩展，标记为 PARTIAL 直到真实数据接入

---

### 6. ZBMP Risk（品牌风险）

**页面目标**：品牌声誉/负反馈/危机预警

**布局**：
- Topbar：Risk + 品牌筛选 + 风险等级筛选
- 第一行：3 KPI（待处理风险/本周新增/已解决）
- 风险列表：表格（风险标题/品牌/等级/来源/时间/状态/操作）
- 点击风险进入详情：事件时间线 + 传播路径 + AI 研判 + 证据链 + 处理记录

**API**：`/api/negative`、`/api/negative-review`、`/api/alerts`
**风险等级**：Critical(红)/High(橙)/Medium(黄)/Low(绿)，unknown 保持 unknown 不伪造

---

### 7. ZBMP Reports（品牌报告）

**页面目标**：品牌报告生成与管理

**布局**：
- Topbar：Reports + 报告类型筛选 + "+ 生成报告"
- 报告列表：卡片（类型/时间范围/品牌/状态/下载）
- 报告类型：Brand Report / Performance / Competitive / Content
- 生成向导：选择类型→选择品牌/时间→确认→生成（显示进度）
- 必须验证：文件存在/大小合理/内容非空/结构正确，禁止接口返回 success 但文件不存在

**API**：`/api/reports`、`/api/special-report`、`/api/weekly`

---

## 二、CTH · Taikoo Hui Intelligence（太古汇专项域）

### 1. CTH Overview（舆情总览）

**页面目标**：一屏回答"太古汇现在发生什么？舆情态势/风险事件/待处理"

**布局**：
- Topbar：CTH Overview + 时间筛选 + 品牌/业态 Tab（整合，不独立导航）
- 第一行：6 KPI 卡片
  - 今日笔记数 / 活跃品牌数 / 风险事件 / 待审核 / 采集状态 / 系统健康
- 第二行：2 列
  - 左(2/3)：舆情声量趋势 + 风险叠加标记
  - 右(1/3)：9 业态分布环形图
- 第三行：2 列
  - 左(1/2)：实时舆情流（最新笔记，品牌/业态标签）
  - 右(1/2)：风险事件看板（按严重度排序）

**API**：`/api/cth/overview`、`/api/dashboard`
**红线保护**：subject_rules.py SUBJECT_WORDS/EXCLUDE_WORDS/subject_hit() 绝对保护，UI 不得绕过

---

### 2. CTH Real-time（实时情报）

**页面目标**：小红书流实时监测、事件追踪、传播路径

**布局**：
- Topbar：Real-time + 品牌筛选器 + 业态筛选器（整合，199品牌/9业态是筛选维度）
- 左侧(2/3)：实时笔记流（瀑布流，自动刷新30s，显示封面/标题/账号/互动/采集时间）
- 右侧(1/3)：
  - 热门话题排行
  - 传播路径图（事件→笔记→互动→扩散）
  - 采集状态面板（运行中/已采集/失败重试）

**API**：`/api/xhs/*`、`/api/cth/real-time`、`/api/event-graph`
**时间口径**：publish_datetime（发布时间）vs captured_at（采集时间）分离显示，禁止混用

---

### 3. CTH Events（事件中心）

**页面目标**：传播/营销/舆情事件图谱管理

**布局**：
- Topbar：Events + 事件类型筛选 + 时间范围
- 事件列表：卡片（事件标题/类型/时间/涉及品牌/声量/状态）
- 点击事件进入详情：
  - 事件时间线
  - 关联笔记列表
  - 传播图谱可视化（event_graph）
  - AI 事件分析
  - 证据链

**API**：`/api/event-graph`、`/api/cases`、`/api/case-analysis`

---

### 4. CTH Risk（风险研判）

**页面目标**：太古汇专项风险研判（扩散/安全/歧视/KOC集中传播）

**布局**：
- Topbar：Risk + 风险类型筛选 + 等级筛选
- 第一行：风险态势 KPI（待处理/处理中/已解决/平均响应时间）
- 风险列表：表格（风险标题/类型/等级/涉及品牌/来源/时间/状态）
- 详情：风险时间线 + 传播分析 + AI 研判 + 证据 + 处理记录 + 人工修正记录

**API**：`/api/negative`、`/api/negative-review`、`/api/alerts`、`/api/risk-engine`
**CTH 专项风险策略**：与 ZBMP 风险策略隔离，使用 CTH Risk Policy

---

### 5. CTH Xiaohongshu（小红书专项）

**页面目标**：采集状态管理、笔记/评论/账号管理

**布局**：
- Topbar：Xiaohongshu + 采集控制（启动/暂停）+ Cookie 状态
- 页内 Tab：采集状态 | 笔记管理 | 评论管理 | 账号管理
- 采集状态：
  - 七态状态机显示（STARTING/RUNNING/DEGRADED/FAILED/STOPPING/STOPPED/RECOVERING）
  - 采集质量门禁（5步：Source→Raw→Dedup→Subject Filter→Canonical，每步通过率）
  - 最近采集日志
- 笔记管理：笔记表格（封面/标题/账号/品牌/互动/评论状态/入库时间）
- 评论管理：评论列表，**评论抓取失败不静默丢弃**，显示 failed/partial/timeout 状态
- 账号管理：采集账号列表 + Cookie 状态 + 保活状态

**API**：`/api/xhs/*`、`/api/collector`、`/api/cookies`、`/api/collect`
**去重**：content_hash + platform_id 复合键，UI 显示去重前后数量对比

---

### 6. CTH Reports（舆情报告）

**页面目标**：太古汇专项报告生成

**布局**：
- Topbar：Reports + 报告类型 + "+ 生成报告"
- 报告列表：日报/周报/月报/事件专报/风险专报/太古汇情报报告
- 生成向导 + 预览 + 下载
- 报告必须真实生成文件，验证存在性

**API**：`/api/reports`、`/api/special-report`、`/api/weekly`、`/api/daily`

---

## 三、SYSTEM · Runtime Control（系统控制域）

### 1. SYSTEM Runtime（运行时）

**页面目标**：Worker/Lease/Heartbeat/Guardian/Checkpoint/DLQ 全链路监控

**布局**：
- Topbar：Runtime + 域筛选(全部/ZBMP/CTH)
- 第一行：4 KPI（活跃Worker/待处理任务/DLQ数/Guardian状态）
- Worker 列表：表格（worker_id/task_id/domain/product/lease到期/last_heartbeat/状态）
- 任务列表：表格（task_id/domain/product/状态/retry_count/next_retry_at/checkpoint）
- DLQ 面板：死信队列列表，支持重试/查看错误
- Guardian 状态：4 模块启用状态 + 最近 Reaper 执行记录

**API**：`/api/system/runtime`、`/api/system/workers`、`/api/system/dlq`
**防止**：僵尸Worker(心跳超时标红)、假运行(有worker无task)、无限retry(retry_count超限标红)

---

### 2. SYSTEM Collector（采集管理）

**页面目标**：多平台采集器管理、账号/Cookie/代理池/质量门禁

**布局**：
- Topbar：Collector + 平台筛选
- 采集器状态卡片：小红书/抖音/微博/B站/知乎（每个显示状态/最近采集/成功率）
- 账号管理：各平台账号列表 + Cookie 状态 + 保活
- 代理池：代理列表 + 延迟 + 可用性
- 质量门禁：5步通过率趋势 + 失败记录查询

**API**：`/api/system/collectors`、`/api/proxy`、`/api/cookies`
**全平台精准**：每个平台数据必须真实采集，缺失标 BLOCKED，禁止估算

---

### 3. SYSTEM AI（AI 网关）

**页面目标**：Provider/Model/调用日志/治理/评估/Trace

**布局**：
- Topbar：AI + Provider 筛选
- 第一行：Provider 状态卡片（Zhipu glm-5.3[ACTIVE] / glm-4.5-air[ACTIVE] / ARK doubao-lite[ACTIVE] / Ollama[AVAILABLE]）
- 调用日志：表格（时间/provider/model/prompt_version/tokens/耗时/confidence/domain/trace_id）
- AI 治理：OWASP Top10 安全门状态 + 敏感数据拦截记录
- 评估面板：AI 输出评估记录 + 人工修正对比（human_correction）

**API**：`/api/system/ai`、`/api/ai-resource-packs`、`/api/ai/*`
**AI 记录**：provider/model/prompt_version/input/output/confidence/timestamp/task_id/trace_id/final_decision/human_correction 全字段
**AI 不得替代规则**：Rule→AI辅助→Evidence→Evaluation→Final Decision 链路在 UI 中可见

---

### 4. SYSTEM Database（数据库）

**页面目标**：62 表监控/迁移/锁/索引/数据质量

**布局**：
- Topbar：Database + 表搜索
- 数据库状态：SQLite WAL 模式 + 连接数 + 最近迁移
- 表列表：62 张表（表名/记录数/大小/域/状态），空表标 KEEP/DEPRECATE
- 点击表：Schema 预览 + 索引 + 最近查询
- 数据质量：缺失值统计 + 重复检测 + 时间口径一致性检查

**API**：`/api/system/database`、`/api/system/tables`
**禁止**：删除表/破坏历史数据，UI 不提供删除操作

---

### 5. SYSTEM Security（安全权限）

**页面目标**：认证/授权/域隔离/审计日志/敏感数据脱敏

**布局**：
- Topbar：Security
- 权限矩阵：user × role × product × domain × action × resource
- 域隔离状态：ZBMP/CTH/SYSTEM 隔离验证结果
- 审计日志：操作记录（谁/何时/什么操作/结果）
- 敏感数据脱敏：6 类敏感数据正则过滤状态 + 拦截记录
- 认证恢复：auth_recovery_tasks 状态

**API**：`/api/system/security`、`/api/workspace`、`/api/v4/*`
**deny by default**：所有危险操作默认拒绝，UI 显示权限不足而非隐藏按钮

---

## 四、通用组件规范

### KPI 卡片
```
┌─────────────────────┐
│ label (11px 灰)     │
│ value (24px/700)    │
│ change (11px 绿/红) │
└─────────────────────┘
```
- 渐变卡片仅用于核心指标（声量/互动），普通指标用纯色卡片
- 缺失值显示 "—" 而非 0，tooltip 说明"数据采集中"

### 表格
- 表头 12px/600 灰底，行高 44px
- 状态列用标签（tag-high/tag-medium/tag-low/tag-info）
- 操作列最多 2 个图标按钮

### 图表
- 趋势图：面积图，渐变填充 #0F766E→透明
- 对比图：折线图，多品牌用不同色
- 分布图：环形图/横向条形图
- 所有图表支持 hover 显示精确值，禁止图表上直接标估算值

### 六态处理
| 状态 | 显示 |
|------|------|
| Loading | 骨架屏（灰色脉冲动画） |
| Empty | 图标 + "暂无数据" + 引导操作按钮 |
| Error | 错误信息 + 重试按钮 + 错误详情可展开 |
| Success | 正常数据展示 |
| Degraded | 黄色横幅"部分数据延迟" + 已加载数据正常显示 |
| Permission Denied | 锁图标 + "无权限访问" + 申请权限按钮 |

---

## 五、字体使用划分

| 用途 | 字体 | 字重 | 字号 |
|------|------|------|------|
| 页面标题 H1 | Inter + Noto Sans SC | 600 | 22px |
| 区块标题 H2 | Inter + Noto Sans SC | 600 | 17px |
| 卡片标题 H3 | Inter + Noto Sans SC | 600 | 15px |
| 核心数据 Data | Inter | 700 | 24px |
| 正文 Body | Inter + Noto Sans SC | 400 | 13px |
| 辅助说明 Caption | Inter + Noto Sans SC | 400 | 11px |
| 代码/ID/trace_id | JetBrains Mono / SF Mono | 400 | 12px |
| 数字/百分比 | Inter (tabular-nums) | 600 | 13px |

- 不使用 Urbanist 作为正文字体（过于几何化，长时间阅读舒适度不足）
- Urbanist 可用于大标题/Logo 等展示性文字（可选）
- 中文统一 Noto Sans SC，与 Inter 混排时基线对齐

---

## 六、实施优先级

1. **P0**：base.html 主题系统（浅色/深色变量）+ Sidebar 三域导航 + Topbar
2. **P0**：ZBMP Overview + CTH Overview（两个首页先落地新设计）
3. **P1**：SYSTEM Runtime + AI + Database（系统页面）
4. **P1**：ZBMP KOS + Brand（核心业务页面）
5. **P2**：CTH Real-time + Events + Xiaohongshu
6. **P2**：Reports + Risk + Competition
7. **P3**：细节打磨（动效/微交互/响应式）

每个页面完成后必须：浏览器实测六态 + API 真实数据 + 无死按钮 + 无 mock 数据
