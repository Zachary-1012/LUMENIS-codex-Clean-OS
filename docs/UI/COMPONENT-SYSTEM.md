# ZBIP Shared Component System（共享组件库规格 / 组件地图）

> v1.0（2026-08-31），配套 ZBIP-DESIGN-SYSTEM.md。本文件是组件**规格契约**，不是实现代码；落地在 Staging 用原生 JS/CSS 实现，不引入大型 UI 框架。分层：Atom（原子）→ Molecule（复合）→ Pattern（页面模式）。每个组件统一规定：结构 / 使用 Token / 状态 / 交互 / 尺寸（桌面·移动）/ 禁用与空态。

## 0. 组件总清单（组件地图）
| 层 | 组件 | 职责 | 现状(旧实现) | 落地动作 |
|---|---|---|---|---|
| Atom | Button / IconButton | 操作触发 | 多套按钮样式 | 统一为 token 版 |
| Atom | Input / Select / Textarea / Search | 录入/检索 | 散落 | 统一 |
| Atom | Badge / StatusDot / Tag | 状态/标签 | badge_manager | 状态语义对齐 §9 |
| Atom | Icon / Avatar / Divider / Spinner / Skeleton | 基础元素 | 多套 | 统一 |
| Molecule | Tabs / Segmented / Breadcrumb | 导航切换 | 部分 | 统一 |
| Molecule | Toolbar（Search+Filter+Sort+View+Action） | 列表工具条 | 各页自写 | 抽象复用 |
| Molecule | Table / ListRow / Pagination | 数据集合 | 多套表格 | 统一密度/空态/移动转卡片 |
| Molecule | Metric / Panel / StatTrend | 指标卡 | KPI 卡片海 | 收敛为克制型 |
| Molecule | Timeline / RelationGraph | 时间线/关系 | event_graph | 统一 |
| Molecule | Menu / NavItem / Sidebar / Topbar | 框架导航 | layout* | 统一 |
| Overlay | Modal / Drawer / Popover / Tooltip / Toast | 浮层 | 多套 | z-index 统一 |
| Overlay | CommandMenu（⌘K） | 全局快捷命令 | 无 | 新建 |
| State | EmptyState / LoadingState / ErrorState / ForbiddenState | 状态页 | 缺失/不一致 | 新建，占位必备 |
| Pattern | FilterPanel / DetailHeader / AuthRecoveryModal / AIChatDrawer / StatusCenter | 业务模式 | 部分 | 按页面地图装配 |

## 1. Atom 规格要点
### Button
- 类型：Primary（bg `--zb-brand` 近黑、白字）、Secondary（白底+`--zb-border`）、Ghost（无底，hover stone-100）、Danger（`--zb-danger`，仅破坏性）、Link。
- 尺寸：sm 24高、md 30（默认，高密度）、lg 36；padding 8/12、12/16；radius `--zb-r-md`；字号 13/14。
- 状态：default/hover（bg 降 4%）/active(scale .98,100ms)/focus-visible 焦点环/loading（前置 14px spinner，禁用点击）/disabled（stone-400，**必带 title 原因**）。危险操作（删除/熔断重置/回滚）点击后走 ConfirmDialog 二次确认。
### IconButton：32×32 命中区（视觉图标 16–18），Ghost 底，tooltip 说明，移动端命中 ≥44。
### Input/Select/Textarea
- 高 30（紧凑 26）；border `--zb-border`，focus `--zb-stone-900` 1.5px 环；错误 `--zb-danger`；只读/禁用 stone-100 底。Search 带前置图标、清除按钮、键盘 ↑↓ 选择、⌘K 唤起。
### StatusDot（核心）
- 8px 圆点 + 12px 文字标签；语义取 §2.2；attention/risk 时 `animation:pulse 2s var(--zb-ease-standard) infinite`（opacity .4↔1，极弱）；必须同时输出文字与 `aria-label`，不靠颜色单独表意。
### Badge/Tag：弱底色（语义 bg）+ fg 文字，radius sm，可带关闭；不可点击的纯展示与可点击 Tag 视觉区分（可点击有 hover 边框）。
### Spinner/Skeleton：优先 Skeleton（骨架，stone-200→stone-100 微光 1.4s）；Spinner 14/20 两档；>1s 操作必须给加载态，>10s 给可取消与进度。

## 2. Molecule 规格要点
### Toolbar（所有列表页统一）
布局：左侧 Search；中部 Filter（筛选 chips，可多选、可清空）；右侧 Sort / View(表格|列表) / 主操作按钮。移动端折叠为「筛选」底部 sheet + 搜索置顶。
### Table
- 表头 stone-100 底、12px muted、行高 36（紧凑 30）、行分隔 1px `--zb-border`、hover stone-50、选中 stone-100；数字列右对齐等宽 tabular-nums；固定首列/操作列；空数据走 EmptyState（区分「无数据」「筛选无结果」「加载中」「异常」**四态**，异常绝不显示成 0 条）。
- 移动 ≤768：高信息表转卡片列表或允许横向滚动并固定关键列；分页转「加载更多/上一页下一页」。
### Pagination：每页 20/50/100；显示总数与区间；URL 同步页码（可分享）。
### Metric（克制指标卡，取代 KPI 海）
结构：标签(12 muted) + 主数值(24–30 等宽) + 同比/趋势(StatusDot+小趋势，语义色) + 可选 1 行说明；卡片用边框不用重阴影；首页同屏指标 ≤7，其余进下钻。
### Panel：surface 白底、border、radius lg、padding16；标题区 16/500 + 右侧操作槽；可折叠。
### Timeline：左轴 2px stone-200、节点为语义 StatusDot、右侧时间(等宽 muted)+事件；支持加载更多。
### RelationGraph（事件关系）：节点=事件（语义色表类型 营销/传播/舆情），边标注关系（触发/衍生/继发/并行）；空图给 EmptyState 说明；不引重型图库，节点量级小可 SVG 自绘。

## 3. 框架层
### Sidebar：宽240/折叠56；NavItem 左 3px 语义条表 active（stone-900）、图标+文字、分组标题 12 muted 大写；底部版本/健康状态小点；≤768 转抽屉，主导航转底部 Tab（≤5 项）。
### Topbar 高56：左面包屑（当前位置）、中全局 Search/⌘K、右 全局状态中心小点集合 + AI 唤起 + 头像/权限。
### Tabs/Segmented：下划线式 Tabs（active 下划 2px stone-900）用于同级页；Segmented 用于视图切换；都支持键盘左右。

## 4. Overlay（z-index 严格按设计系统 §10.4）
- **Modal**：居中、surface、shadow-3、radius lg、最大高 80vh 内滚；标题/内容/操作槽；Esc 关闭、点遮罩询问（有未保存改动则拦截）。
- **Drawer**：右侧 480（移动全屏）、shadow-2，用于详情/编辑，不离开当前列表上下文。
- **Toast**：右上（移动顶部）、4 类语义、自动消失（成功 3s，错误需手动关并可查看详情）、不打断输入。
- **CommandMenu（⌘K / Ctrl K）**：全局搜索页面/操作/数据，键盘可达，分组「跳转 / 操作 / 最近」，是高密度产品快速定位核心。
- **AuthRecoveryModal（业务关键，全局、不跳页）**：字段=平台/当前账号/当前状态/失效原因/任务暂停态/二维码或平台合法验证入口/「我已完成验证」「稍后处理」/恢复进度态；A 登录失效=二维码、B NEED_VERIFY=人工验证提示、C IP_RISK/300012=熔断冷却倒计时（**不伪装成可扫码解决**）；任何页面与手机端都在当前页弹出。

## 5. 四态组件（强制，消灭“假 0 条 / 白屏”）
- EmptyState：图标(stone-300)+一句话+可选行动按钮；区分 无数据 / 筛选无结果 / PLANNED·RESERVED 占位（灰点“规划中”）/ 空表（如 swire）。
- LoadingState：Skeleton 保持布局形状，不让内容跳动。
- ErrorState：错误摘要 + 重试 + 展开技术信息 + 错误码；网络错给退避状态文案。
- ForbiddenState：无权限说明 + 申请路径；Disabled 操作就地给原因。

## 6. AIChatDrawer（Zachary，全局右侧抽屉）
- 三区分：「系统事实」（stone 中性、带数据来源）/「AI 建议」（info 蓝弱底、标模型与置信度，Ollama-only）/「人工判断」（用户操作）。AI 永不覆盖系统事实；Ollama 不可用时整体 gray 降级且业务链路照常。支持对当前页面/选中对象发起分析（上下文注入）。

## 7. 组件验收（每个组件交付即过）
桌面/移动两形态；全状态（default/hover/active/focus/disabled/loading/error/empty）；键盘可达；仅用 Token（grep 无硬编码色值）；六断点无横向溢出；带截图 Evidence 与组件版本号。组件一经登记，页面禁止重复造轮子。
