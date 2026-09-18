# UI Design Research（标杆设计系统研究 · ZBIP 适配）

> Research Set：UI-20260831，2026-08-31。只学设计思想/组件与交互模式，**不复制任何第三方代码/资源**。下列为各产品公开设计方法的提炼与 ZBIP 取舍；具体 star/版本以官方与 GitHub 实时为准，本文不固化易变数字。参考来源为各官方设计站与公开文档（见每条 Reference）。

## 总览结论
共同规律：**Token 三层（基础→语义→组件）→ Components → Patterns → Product**；高密度、弱边框、状态驱动、键盘优先、动效克制成熟工程产品的共性。ZBIP 全部采用这套方法，视觉落为侘寂黑白灰。

## 1. GitHub Primer（primer.style，开源设计体系）
- 思想：Design Tokens 驱动、functional color（功能色独立于品牌色）、间距 4/8 倍数、组件与可访问性一体。
- 模式：语义色 token（success/attention/danger/done/sponsors）、密度可控（comfortable/condensed）、统一 focus 环。
- ZBIP 适配：**采用**——正是本系统“中性灰 + 六语义状态 + 密度档”的依据；functional color 与品牌色分离，保证状态语义稳定。Reference: https://primer.style/foundations/color

## 2. Linear（linear.app，高密度 SaaS 标杆）
- 思想：极简、键盘优先（⌘K 命令面板）、紧凑列表、极快微交互、弱分割强排版。
- 模式：Command Menu、列表密度高、悬停才显露次要操作、状态用小 dot+文字、弹层多用侧滑而非跳页。
- ZBIP 适配：**采用**——⌘K 全局命令、高密度表格、次要操作 hover 显形、详情走 Drawer，均写入组件系统。Reference: https://linear.app/docs（公开产品方法）

## 3. Vercel / Geist（vercel/geist-design）
- 思想：黑白灰高对比、Geist 字体阶梯、克制的边框与阴影、工程感。
- 模式：近黑主按钮、1px 边框分层、Skeleton 加载、极简 toast、严格间距尺度。
- ZBIP 适配：**采用**——主操作用近黑而非彩色、边框优先于阴影、骨架屏，奠定侘寂基底。Reference: https://vercel.com/geist/introduction

## 4. OpenAI 产品（ChatGPT/Platform）
- 思想：对话与工作区融合、留白、单一主行动、AI 输出与系统内容分区。
- 模式：AI 面板区分“模型生成 / 用户 / 系统”，生成态流式反馈，空态引导。
- ZBIP 适配：**部分采用**——AIChatDrawer 三分区（系统事实/AI 建议/人工判断）、流式/加载态；不采用其大留白营销风（B 端要密度）。

## 5. Anthropic Console（console.anthropic.com）
- 思想：工程控制台、可信、低噪音、密钥/用量/日志的安全呈现。
- 模式：密钥脱敏显隐、用量与状态清晰、危险操作确认、文档与控制台同语言。
- ZBIP 适配：**采用**——设置页密钥脱敏、危险 run-code 收口与二次确认、可信工程语气。Reference: https://docs.anthropic.com/

## 6. Stripe Dashboard
- 思想：复杂金融数据的清晰分层、表格与细节抽屉、图表克制。
- 模式：列表→详情抽屉不丢上下文、数字 tabular-nums 对齐、筛选 chips、分步向导。
- ZBIP 适配：**采用**——笔记/事件/报告列表 + Drawer 详情、数字等宽对齐、报告生成向导。Reference: https://stripe.com/blog/connect-front-end-experience（公开工程博客类）

## 7. Datadog（监控可观测标杆）
- 思想：监控驾驶舱、状态时间线、告警分级、图与表联动。
- 模式：健康状态总览、时间窗切换、告警分级点、下钻到原始事件。
- ZBIP 适配：**采用其信息结构**（CTH 驾驶舱、状态中心、时间窗、下钻），**不采用**其高饱和多色仪表盘（改黑白灰+语义点）。Reference: https://docs.datadoghq.com/dashboards/

## 8. Sentry（错误监控/事件流标杆）
- 思想：问题→事件→堆栈证据链、严重度分级、状态流转（Unresolved/Resolved 等）。
- 模式：Issue 流、严重度 Badge、生命周期状态、证据折叠面板。
- ZBIP 适配：**采用**——事件生命周期（Detected→…→Archived）、严重度、Evidence 折叠，映射到事件中心与 DCC Evidence。Reference: https://docs.sentry.io/product/issues/

## 横向：动效与密度（行业公开经验，已交叉验证）
- 人对 <100ms 变化近无感、>1s 易不耐烦；微交互 100–150ms、状态 200–300ms、转场 300–400ms 是 B 端常见区间（与本系统 Motion 取值一致）。
- 4/8pt 栅格、Token 三层（基础→语义→组件）、更小圆角提升中后台信息密度、颜色不可作为唯一信息载体——均为公开设计共识，已写入 Design System。
- 参考（中文工程社区公开整理，作交叉佐证，非一手）：掘金《从手写组件到设计系统》Token 三层；Ant Design 4.0 圆角由 4→2 以提密度；人人都是产品经理 B 端动效时长。

## 采用结论
ADOPT：Primer token/功能色、Linear ⌘K/密度/抽屉、Vercel 黑白灰/边框优先、Stripe 列表-抽屉、Datadog 驾驶舱结构、Sentry 事件生命周期、Anthropic 密钥安全呈现。REFERENCE-ONLY：OpenAI 对话分区（仅 AI 区）。REJECT：高饱和仪表盘配色、营销式大留白、拟物/重阴影/炫技动效。
