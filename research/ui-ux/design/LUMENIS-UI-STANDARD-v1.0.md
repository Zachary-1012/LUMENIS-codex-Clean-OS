# LUMENIS UI Standard v1.0
## 序境 · 智能操作系统 视觉与交互规范

> **文档地位**：LUMENIS Intelligence OS 唯一视觉权威。取代此前 XUJING-UI-STANDARD、ZBC_UI_UX_LANGUAGE_V2、ZBIP-DESIGN-TOKENS 中的视觉部分。
> **基准**：LUMENIS-INTELLIGENCE-OS-DUAL-CORE-ARCHITECTURE-v1.0 + 线上 main 源码事实。
> **适用**：Production Core (ZBC) + Intelligence Core (OSAI) 全部前端，中/英/韩同一视觉语言。
> **版本**：v1.0 · 2026-09-05 · 状态：CANONICAL

---

## 0. 设计哲学

- **品牌**：序境 LUMENIS（不再使用 Xujing 作为正式产品名）
- **哲学**：芥子纳须弥——小即大，克制中的丰盈
- **美学**：Apple-inspired × 微光银 × 专业情报工作台 × Liquid Glass restrained
- **核心公式**：Complexity → Simplicity
- **参考品味**：Prada/MiuMiu 克制、LeLabo 质感、观夏架构、Apple Liquid Glass、Safari 页面架构

---

## 1. 设计 DNA（10 条）

| # | 原则 | 说明 |
|---|---|---|
| D01 | Complexity → Simplicity | 复杂能力转化为简单操作 |
| D02 | AI First | AI 是工作入口，不是装饰 |
| D03 | Information First | 信息理解优先于视觉装饰 |
| D04 | Real-time | 数据状态实时更新，真变才动 |
| D05 | Minimal & Professional | 简约克制，专业环境，不做可爱化 |
| D06 | Spatial Layer | 适度空间层次玻璃感，不满屏特效 |
| D07 | Light Motion | 动效服务交互，感知得到但不等待 |
| D08 | No Infinite Scroll | 禁止无止境滚动，内容有界 |
| D09 | No Permanent Right Context | 不设永久右侧 Context 面板 |
| D10 | One Design Language | Web/App 共用设计语言，形态融合物理不合并 |

---

## 2. Design Token

> 三层架构：primitive → semantic → component。组件只消费 semantic层，不得硬编码。
> Token 前缀统一 `--lm-`（取代旧 `--xj-`）。

### 2.1 中性色（侘寂黑白灰）

| Token | Light | Dark | 用途 |
|---|---|---|---|
| `--lm-canvas` | `#F5F4F1` | `#111111` | 页面背景 |
| `--lm-surface` | `#FFFFFF` | `#171717` | 卡片/面板实色 |
| `--lm-surface-elevated` | `rgba(255,255,255,0.82)` | `rgba(28,28,30,0.72)` | 悬浮/磨砂层 |
| `--lm-surface-input` | `rgba(118,118,128,0.12)` | `rgba(44,44,46,0.8)` | 输入框 |
| `--lm-border` | `rgba(60,60,67,0.18)` | `rgba(84,84,88,0.35)` | 默认边框 |
| `--lm-border-strong` | `rgba(60,60,67,0.36)` | `rgba(84,84,88,0.6)` | 强调/Focus |
| `--lm-text-primary` | `#1C1C1E` | `#F7F7F5` | 主文字 |
| `--lm-text-secondary` | `#636366` | `#B8B7B2` | 辅助文字 |
| `--lm-text-tertiary` | `#8E8E93` | `#777771` | 三级/占位 |

### 2.2 语义状态色（Apple-style，仅用于状态点+文字，禁大面积）

| Token | Light | Dark | 状态 |
|---|---|---|---|
| `--lm-status-success` | `#34C759` | `#30D158` | 成功/Online/Pass |
| `--lm-status-info` | `#007AFF` | `#0A84FF` | 主要操作/Active/信息 |
| `--lm-status-warning` | `#FF9500` | `#FF9F0A` | 警告/Pending/处理中 |
| `--lm-status-danger` | `#FF3B30` | `#FF453A` | 错误/Risk/Fail/Offline |
| `--lm-status-ai` | `#AF52DE` | `#BF5AF2` | AI/指令/研究/思考中 |
| `--lm-status-unknown` | `#8E8E93` | `#636366` | 未知/未连接 |

### 2.3 微光银（Silver Shimmer，品牌签名）

| Token | 值 |
|---|---|
| `--lm-silver-50` | `#FAFAFA` |
| `--lm-silver-100` | `#F0F0F0` |
| `--lm-silver-200` | `#E4E4E4` |
| `--lm-silver-300` | `#D1D1D1` |
| `--lm-silver-400` | `#A3A3A3` |
| `--lm-silver-500` | `#737373` |
| `--lm-shine-band` | `linear-gradient(110deg, transparent 30%, rgba(255,255,255,0.55) 50%, transparent 70%)` |

规则：品牌标题斜向扫光 + 卡片按真实 status 呼吸；始终浅色高级；`prefers-reduced-motion` 时关闭。

### 2.4 字体

```css
--lm-font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text",
  "PingFang SC", "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
--lm-font-mono: "SF Mono", Menlo, Consolas, monospace;
```

| Token | 字号 | 字重 | 用途 |
|---|---|---|---|
| `--lm-text-display` | 34px | 700 | 品牌宣言/Command Home Hero |
| `--lm-text-h1` | 22px | 700 | 页面主标题 |
| `--lm-text-h2` | 17px | 700 | 区域标题 |
| `--lm-text-h3` | 15px | 600 | 卡片/子区域标题 |
| `--lm-text-body` | 15px | 400 | 正文 |
| `--lm-text-caption` | 13px | 400 | 辅助说明 |
| `--lm-text-label` | 11px | 700 | 标签（大写，letter-spacing 0.8px） |
| `--lm-text-metric-lg` | 28px | 700 | 关键大数字 |
| `--lm-text-metric` | 20px | 700 | 卡片指标 |
| `--lm-text-button` | 15px | 600 | 按钮 |

字重规则：仅 400（常规）和 600/700（粗体）。行高：正文 1.5，标题 1.3，大数字 1.1。

### 2.5 间距（8px 栅格）

`--lm-space-xs` 4 / `--lm-space-sm` 8 / `--lm-space-md` 12 / `--lm-space-lg` 16 / `--lm-space-xl` 20 / `--lm-space-2xl` 32 / `--lm-space-3xl` 48

布局规则：主间距 8px 垂直重复；分组用 4px 次级分隔；按钮间 16px；图标与文字间距 ≥1.5× 图标大小。

### 2.6 圆角

`--lm-radius-sm` 8 / `--lm-radius-md` 12 / `--lm-radius-lg` 16 / `--lm-radius-xl` 20 / `--lm-radius-full` 9999

### 2.7 边框与阴影

边框：1px 默认，1.5px Focus。优先细边框+低对比度 Surface 表达层级，减少厚重阴影。

阴影：`--lm-shadow-sm` 0 2px 8px rgba(0,0,0,0.06) / `--lm-shadow-md` 0 4px 24px rgba(0,0,0,0.08) / `--lm-shadow-lg` 0 20px 60px rgba(0,0,0,0.15)。禁多层堆叠、禁彩色发光（主按钮除外）。

---

## 3. Liquid Glass

三变体：

| 变体 | 参数 | 用途 |
|---|---|---|
| Regular Glass | blur(20px) saturate(180%) + elevated surface | 侧边栏/顶部 Bar/底部 Tab |
| Clear Glass | blur(30px) + rgba(255,255,255,0.6) | 覆盖层/搜索弹出 |
| Identity Glass | Regular + 微光银扫光 + 极淡品牌 tint | AI 入口/品牌区/Hero |

Interactive Glass：Press scale(0.97) + 亮度微降；Hover 微光增强；触点扩散 200ms。

铁律：
1. 只用于 Navigation / Floating Layer / Transient Context
2. 内容/列表/表格/图表用实色 Surface，不用玻璃
3. **禁 glass-on-glass**（玻璃套玻璃）
4. 玻璃上文字对比度 ≥4.5:1
5. `prefers-reduced-transparency` 降级实色；`prefers-reduced-motion` 关动效
6. 一个页面玻璃元素 ≤3 个

---

## 4. 动效

模式：Stagger（级联进入）/ Multi-translate（多方向冲入）/ Float（轻柔漂移）/ Continue-through（部件持续移动后聚合落位）

时长：120ms（hover/press）/ 180ms（panel/card）/ 240ms（tab）/ 320ms（页面进入）/ 420ms（modal/AI）

缓动：`cubic-bezier(0.32, 0.72, 0, 1)`

铁律：
- **Data-driven Motion**——没有真实数据变化，不动画
- 真变才动一次；持续状态按真实 status 呼吸
- 禁写死循环（微光银品牌签名除外且极淡）
- 禁假实时/假绿色/假增长/视觉欺骗
- 超过 420ms 必须可跳过
- `prefers-reduced-motion` 全部关闭

---

## 5. 图标

- 24×24 viewBox / 1.5px stroke / currentColor / 圆头线帽
- 实现：注册表 → `licon(name, size, cls)` 函数 → 模板调用
- 状态用 `.lm-dot`（10px CSS 圆点）+ 文字标签，双通道
- **禁 emoji 作为正式 UI icon**（用户生成内容除外）

---

## 6. 组件系统（LUMENIS Component System）

Button / Input / Select / Tabs / Badge / Status / Card / Table / List / Drawer / Modal / Toast / Timeline / Metric / Chart / Command / Search / Filter / Navigation

核心规则：
- Card：16px 圆角，实色 Surface，细边框，极淡阴影，内容有界不溢出
- Table：行高 44px，hover 高亮，Sort/Filter/Search/Group/Compare/Drill-down/Export
- Drawer：右侧滑出，Clear Glass，420ms，不覆盖 Sidebar
- Modal：居中，20px 圆角，320ms，**禁模态叠模态**
- Metric：大数字+标签+趋势微缩，单指标单卡
- Chart：服务判断，一页 ≤3 图，关键指标→趋势→解释→行动

AI 六态：AI_PROCESSING（info蓝）/ AI_RESEARCHING（ai紫）/ AI_VERIFYING（warning橙）/ AI_NEEDS_REVIEW（warning橙）/ AI_COMPLETED（success绿）/ AI_FAILED（danger红）

---

## 7. IA 与导航

### 7.1 布局

```
┌────────────────────────────────────────────┐
│ Global Header                              │
├──────────┬─────────────────────────────────┤
│ Sidebar  │ Workspace                       │
│          │                                 │
│          │ （不无限下滑，重要信息一屏完成）  │
└──────────┴─────────────────────────────────┘
```

左侧 = 导航；中间 = 当前工作；不设永久右侧 Context。层级上限 L4。

### 7.2 一级 IA

```
INTELLIGENCE  → Overview / AI Workspace / Agents / Skills / Evidence / Evaluation / Learning
PRODUCTION    → Overview / Subjects / Brands / Content / Public Opinion / Events / Risk / KOS-KOL-KOC / Cases / Reports
RESEARCH      → Research / Discoveries / Technology / Evidence / Findings / Decisions
OPERATIONS    → System / Runtime / Tasks / Logs / Security / Settings（系统级，不做业务一级）
```

HOME 为全局入口，位于一级之上。

### 7.3 Command Home（首页，不是 Dashboard）

六区：
1. **System State**——LIVE 状态、采集健康、数据新鲜度
2. **Intelligence Pulse**——AI 活动、研究进展、学习信号
3. **Active Risks**——当前风险预警（≤5 条，按严重度排序）
4. **Active Tasks**——进行中任务（≤5 条）
5. **Recent Evidence**——最新证据链（≤5 条）
6. **Recommended Actions**——系统建议的下一步操作（≤3 条）

核心：告诉用户现在发生什么、为什么发生、下一步做什么。不是数据展示墙。

### 7.4 Intelligence Workspace

Input → Context → Retrieval → Reasoning → Analysis → Evidence → Decision → Action。右侧 Context Panel 按需打开，不永久常驻。

### 7.5 Production Workspace

Subject / Brand / Content / Public Opinion / Event / Risk / Campaign / Report。调用 ZBC 真实生产能力。

### 7.6 Research Workspace

Research → Finding → Evidence → Decision → Product Improvement。外部研究必经 Evidence→Finding→Internal Proposal→Human Review→Implementation，禁止网上发现直接进 Core。

### 7.7 Skill Hub / Agent Center

Skill Hub：All Skills / My Skills / Recommended / Running / Evaluations / Skill Factory。每个 Skill 页统一：Name/Purpose/Input/Output/Permissions/Dependencies/Version/Success Rate/Usage/Cost/Evidence/Lifecycle。

Agent Center：每个 Agent = Mission → Skills → Permissions → Tasks → Execution → Evidence → Evaluation。

---

## 8. 页面骨架（通用）

```
Context（当前域/对象/时间范围）
  → Decision（本页支持的判断/动作）
    → Data（关键指标 ≤4 个）
      → Evidence（趋势/分布/对比/事件/告警）
        → Detail（下钻对象/明细）
          → Action（基于判断的操作）
```

视觉优先级：信息层级 > 留白 > 排版 > 数据可视化 > 状态 > 交互反馈 > 装饰。

---

## 9. 响应式

| 断点 | 宽度 | 导航 | 工作区 |
|---|---|---|---|
| Desktop Wide | ≥1440px | Sidebar 240px | 多列 |
| Desktop Standard | 1024–1439px | Sidebar 240px | 双列/自适应 |
| Desktop Compact | 768–1023px | Sidebar 折叠 64px | 单列 |
| Tablet | 481–767px | 顶部导航+抽屉 | 单列 |
| Mobile | ≤480px | 底部 Tab Bar（Regular Glass） | 单列全宽 |

移动端：底部 Tab 5 入口，中央 AI 入口可 Identity Glass 凸起；触控目标 ≥48px；正文 ≥14px；多列必须 flex-wrap。

LUMENIS Mobile 主要做查看/查询/分析/启动任务/审批/查看 Evidence/查看风险，不做 Git 操作。

---

## 10. 无障碍

- 文本对比度 ≥4.5:1，非文本 ≥3:1
- 不仅依赖颜色（状态点+文字双通道）
- `:focus-visible` 2px 实线
- `prefers-reduced-motion` 关全部动效（含微光银）
- `prefers-reduced-transparency` 玻璃降级实色
- 中/英/韩切换自动适配文字长度，禁溢出挤压
- 语义化 HTML，ARIA 完整

---

## 11. 防覆盖 Contract

### Z-index 分层

Base 0 / Content 10 / Sticky Header 100 / Dropdown 200 / Drawer 300 / Modal 400 / Toast 500 / AI Overlay 600

铁律：Modal 上不得再弹 Modal；Dropdown 不得超出 Modal 边界。

### Overflow

页面级 `overflow: hidden`（禁无限滚动），内容区内部滚动；卡片 `overflow: hidden` + 截断+展开；表格 `overflow-x: auto` 固定表头。

### 高度

卡片 min/max height 定义；动态内容区预留 skeleton 占位，数据到达不跳版；工作区高度 = 100vh - header - sidebar。

### 实时刷新不跳版

数据更新用 opacity 200ms 淡入；列表更新用 FLIP 动画；数字变化用 count-up；高度变化用 transition 300ms。

---

## 12. 全局禁则（Zero-Sequence）

1. 禁 emoji 当正式 icon
2. 禁假数据/假动画/假绿/双真相
3. 禁大字报/巨型 Logo/巨型 Icon/无意义装饰
4. 禁写死循环动画（微光银除外且极淡）
5. 禁 glass-on-glass
6. 禁无限滚动
7. 禁永久右侧 Context 面板
8. 禁可爱化 UI
9. 禁满屏特效/视觉过载
10. 禁模态叠模态
11. 禁一屏两个主按钮
12. 禁状态色作大面积背景
13. 禁多层阴影堆叠/彩色发光
14. 禁低于 4.5:1 对比度正文
15. 禁未授权修改业务口径/统计规则/报告周期

---

## 13. 验收清单

### Visual QA
- [ ] 10 条 DNA 逐条对照
- [ ] 色值全部来自 `--lm-` Token，无硬编码
- [ ] 字号/字重符合层级表
- [ ] 间距为 4/8/12/16/20/32/48 之一
- [ ] 圆角为 8/12/16/20/9999 之一
- [ ] 玻璃符合 Liquid Glass 铁律
- [ ] 无 emoji icon、无可爱元素、无大字报
- [ ] 无模态叠模态、无内容溢出/遮挡
- [ ] 对比度达标
- [ ] Light/Dark 双主题值已定义

### Functional QA
- [ ] 功能/回归通过
- [ ] 数据口径与后端 API 一致
- [ ] 动效数据驱动，无假动画
- [ ] 实时刷新不跳版
- [ ] 响应式 Desktop + Mobile
- [ ] 无障碍 focus/reduced-motion/reduced-transparency
- [ ] Lifecycle 可追溯
- [ ] 未 push（当前阶段）

---

## 14. 与旧规范映射

| 旧规范 | 本文件吸收 | 冲突处理 |
|---|---|---|
| 设计母表 v1.0 | IA/模块/层级/20规则 | 全部吸收，命名升级 LUMENIS |
| UI_UX_DESIGN_BASELINE | 3 Workspace/页面层级/交互链 | Workspace 升级为 4 域（Intelligence/Production/Research/Operations） |
| UNIFIED_UI_UX_IA_V1 | 交互链/页面骨架 | 全部吸收 |
| ZBC_UI_UX_LANGUAGE_V2 | 侘寂色板/动效/AI状态 | 色值统一 Apple 系+侘寂暖调，token 前缀 --lm- |
| XUJING-UI-STANDARD | 14条逻辑/微光银/细线icon/数据驱动动效 | 全部吸收，命名 XUJING→LUMENIS |
| ZBIP-DESIGN-TOKENS | Apple色系/SF Pro/8px栅格/磨砂玻璃 | 作为 Token 基准，玻璃升级 Liquid Glass |

---

*本文件为 LUMENIS Intelligence OS 唯一视觉权威。修改须 Human Approval 并更新 Lifecycle。*
*下一步：Token CSS 实现 → 组件库 → Shell + Command Home → 逐 Workspace 接入 API。*
