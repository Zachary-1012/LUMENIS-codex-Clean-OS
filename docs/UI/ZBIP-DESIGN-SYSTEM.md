# ZBIP Design System（Z-Brand Intelligence Platform 统一 UI/UX 设计系统）

> 版本 v1.0（2026-08-31，设计工程阶段，**只定规范不写业务页面**）。适用：ZBP（CTH-POMS + ZBMP）为当前落地对象，DCC / SICI 后续对齐。
> 风格坐标：GPT + Codex + Linear + Vercel，侘寂（wabi-sabi）黑白灰为底，语义色仅用于状态与关键操作。关键词：专业 / 极简 / 高密度 / 可信 / 智能 / 工程感。
> 现状根因（实测，本系统要解决的问题）：`static/css` 共 **22 个 CSS、约 1.7 万行**，`static/index.html` 串行 link **17 个**样式（tokens→components→layout→style→design-v8→design-v9-gpt-codex→*-minimal→zb-theme→zb-gpt-theme），多套 token 并存、后加载层覆盖先加载层——这是“新 UI 被旧样式覆盖、风格不统一、显丑”的机制根因。本设计系统是**唯一视觉真相（Single Source of Truth）**。

---

## 1. Design Philosophy（设计哲学）
1. **内容优先、装饰让路**：大面积中性留白，弱边框分隔，信息靠排版层级而非彩色卡片堆叠。禁止传统后台大红大绿卡片海、大面积渐变、无意义阴影、过度圆角、3D/炫光。
2. **高信息密度（Dense）但不拥挤**：紧凑控件、统一 4px 基线栅格、行高与间距量化；一屏内回答“现在状态如何 / 我能做什么 / 数据属于谁”。
3. **状态驱动（State-driven）**：任何对象都有明确状态，状态=「状态点 + 文字 + 图标」三重表达，**颜色永不作为唯一信息载体**（色觉障碍可读、截图黑白可读）。
4. **操作必有反馈**：Idle→Hover→Active/Focus→Loading→Success/Error→Disabled（Disabled 必带原因）；危险操作二次确认。
5. **单页为主、层级跳转**：核心状态首页一屏可达；详情走抽屉/侧滑/二级页，不把用户带到陌生页面（Auth 失效一律当前页全局 Modal）。
6. **一致大于创意**：所有页面只允许使用本系统 Token 与共享组件，不允许页面内私有魔改颜色/圆角/阴影。
7. **动效表达意义**：动画只用于“操作反馈 / 状态变化 / 层级关系 / 注意力引导”，无意义即删除。

## 2. Color Token（三层：基础→语义→组件）
> 采用偏暖中性灰阶（侘寂、长时间盯盘不刺眼）。**禁止在组件里写死色值，只能引用语义 Token。**

### 2.1 基础中性色板（Primitive / Stone 暖灰）
| Token | 值 | 用途 |
|---|---|---|
| `--zb-stone-0` | #FFFFFF | 纯白 |
| `--zb-stone-50` | #FAFAF9 | 画布底 |
| `--zb-stone-100` | #F5F5F4 | 凹陷区/表头 |
| `--zb-stone-200` | #E7E5E4 | 默认边框 |
| `--zb-stone-300` | #D6D3D1 | 强边框/分隔 |
| `--zb-stone-400` | #A8A29E | 禁用 |
| `--zb-stone-500` | #78716C | muted 文本 |
| `--zb-stone-600` | #57534E | 次级文本 |
| `--zb-stone-700` | #44403C | — |
| `--zb-stone-800` | #292524 | 主文本 |
| `--zb-stone-900` | #1C1917 | 标题/最强文本 |

### 2.2 语义色（Semantic，仅状态/关键操作，低饱和）
| 语义 | 前景 fg | 弱底 bg（badge/dot 衬底） | 边框 | 含义 |
|---|---|---|---|---|
| success 正常 | #16A34A | #F0FDF4 | #BBF7D0 | ●green 正常/成功/健康 |
| info 信息 | #2563EB | #EFF6FF | #BFDBFE | ●blue 信息/进行中/链接 |
| attention 关注 | #D97706 | #FFFBEB | #FDE68A | ●yellow 关注/轻度风险 |
| risk 风险 | #EA580C | #FFF7ED | #FED7AA | ●orange 风险升高/告警 |
| danger 严重 | #DC2626 | #FEF2F2 | #FECACA | ●red 严重/熔断/失败 |
| unknown 未知 | #78716C | #F5F5F4 | #E7E5E4 | ●gray 未知/未启用/占位 |

> 状态升级路径（采集/风险）：gray 未知 → green 正常 → yellow 关注（呼吸）→ orange 风险 → red 严重；用**颜色+点形态+文案**同时表达，不弹窗轰炸。

### 2.3 语义别名（组件只引用这一层）
```
--zb-bg:var(--zb-stone-50); --zb-surface:#fff; --zb-surface-sunken:var(--zb-stone-100);
--zb-border:var(--zb-stone-200); --zb-border-strong:var(--zb-stone-300);
--zb-text:var(--zb-stone-900); --zb-text-secondary:var(--zb-stone-600);
--zb-text-muted:var(--zb-stone-500); --zb-text-disabled:var(--zb-stone-400); --zb-text-inverse:#fff;
--zb-brand:var(--zb-stone-900);          /* 品牌主操作用近黑，而非彩色 */
--zb-success/--zb-info/--zb-attention/--zb-risk/--zb-danger/--zb-unknown: 见 2.2
```
暗色主题预留 `[data-theme="dark"]` 覆盖层（本期不施工，先留 Token 位，不散落硬编码）。

## 3. Typography（字体排版）
- 字体栈：`-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif`；等宽（数据/代码/ID）：`ui-monospace,"SF Mono",Consolas,"Courier New",monospace`。**不引入远程字体/大字体包（性能红线）。**
- 字号阶梯（px / line-height / weight）：12/16/400（辅助标注）、13/20/400（密集表格正文，桌面默认正文 13–14）、14/22/400（正文）、16/24/500（小标题）、18/26/600（区块标题）、20/28/600（页标题）、24/32/600、30/38/700（仅首页关键数字）。
- 字重只用 400/500/600/700；数字与英文用等宽 + `font-variant-numeric:tabular-nums`（表格/计数对齐不跳动）。
- 行长：长文本每行约 60–70 字符；标题不占屏，页标题区高度 ≤56px。

## 4. Layout Grid（布局栅格）
- 桌面 12 栏、gutter 16；内容最大宽 1440 居中。左侧导航宽 **240**、折叠 **56**；顶栏高 **56**；全局右侧抽屉宽 480（大屏）/ 100%（≤768）。
- 断点（必验六档）：390 / 430（手机）、768（平板）、1024（小笔电）、1280、1440（桌面）。移动端不是缩放桌面：导航转底部 Tab 或抽屉、表格转卡片或横向滚动、Modal 转全屏 sheet。
- 页面骨架统一：`Sidebar + Topbar(面包屑/全局搜索/状态/头像) + Content(页头→工具条→内容区)`。

## 5. Spacing（间距，4px 基线）
只允许：4 / 8 / 12 / 16 / 24 / 32 / 40 / 48（对应 `--zb-sp-1..8`）。控件内边距：紧凑 4/8、默认 8/12、宽松 12/16；卡片内边距 16，卡片间距 16，区块间距 24。禁止任意奇数像素值。

## 6. Radius（圆角，偏小以提密度）
`--zb-r-sm:4px`（Badge/小标签/输入）、`--zb-r-md:6px`（按钮/控件默认）、`--zb-r-lg:8px`（卡片/弹窗）、`--zb-r-xl:12px`（大面板，少用）、`--zb-r-pill:999px`（状态点容器/胶囊，仅状态用）。行业经验：中后台更小圆角减少视觉细节、提升阅读效率，故不采用大圆角。

## 7. Shadow（阴影，极弱、边框优先）
侘寂以边框分层为主、阴影为辅，仅浮层用轻阴影，共 3 级：
- `--zb-shadow-1:0 1px 2px rgba(28,25,23,.06)`（悬停卡片/下拉）
- `--zb-shadow-2:0 4px 12px rgba(28,25,23,.08)`（Drawer/Popover）
- `--zb-shadow-3:0 12px 32px rgba(28,25,23,.12)`（Modal/Command Menu）
禁止彩色发光、重投影、长阴影；平面区块一律用 `--zb-border` 分隔。

## 8. Icon（图标）
- 线性为主、stroke 1.5–2px、统一 16/20/24 三档；优先一套开源线性图标（如 Lucide，MIT，落地时锁定版本、按需引入，不整包加载）。
- 不用 emoji 充当功能图标；状态图标与状态点同色但不替代文字。触控目标 ≥44×44（移动端）/ 24（桌面鼠标最小命中 24，视觉可更小）。

## 9. Status System（统一状态系统）
### 9.1 业务状态六语义：success / info / attention / risk / danger / unknown（见 2.2）。
### 9.2 三种载体
- **StatusDot 状态点**：8px 圆点；正常静态、关注/风险用极弱呼吸（2s，见 §10）、严重常亮；点旁必须有文字标签。
- **Badge 标签**：弱底 + fg 文字 + 可选图标，小字号 12、`--zb-r-sm`、内边距 2/8。
- **趋势线/迷你图**：只用语义色描线，不填充大面积色块。
### 9.3 平台采集状态（与后端状态机一一对应，前端不得把异常显示成“0 条”）
SUCCESS=success；NO_NEW_DATA=unknown（文案“暂无新数据”，不是 0 舆情）；RISK_WARNING=attention；NEED_VERIFY=risk；BLOCKED/IP_RISK/300012=danger（熔断冷却，非扫码可解）；AUTH_FAILED/SESSION_EXPIRED=danger→触发全局 Auth Modal；NETWORK_ERROR=info（退避中）；COOLING_DOWN=attention（显示 resume 时间）。

## 10. Animation System（动效系统，目的优先）
### 10.1 时长（ms）与缓动
- 微交互 Hover/Press：**100–150**；状态变化（开关/选中/点变色/Badge）：**200–300**；页面/路由/抽屉转换：**300–400**。
- 标准缓动：`--zb-ease-standard:cubic-bezier(.16,1,.3,1)`（减速出场，Linear/Vercel 式）；进入用 ease-out、退出用 ease-in；按压 `transform:scale(.98)` 100ms。
- Token：`--zb-dur-micro:120ms;--zb-dur-state:220ms;--zb-dur-page:320ms;`
### 10.2 允许的动效（必须有意义）
Hover 抬升/描边变深、Click 按压、Loading（骨架屏优先于转圈）、展开折叠、状态点呼吸、Drawer/Modal 进出、列表增量插入高亮、路由淡入位移 4–8px。
### 10.3 禁止
无意义循环动画、大面积背景动效、视差/3D 翻转、弹跳果冻、自动轮播轰炸、>400ms 的阻塞转场。**必须支持 `@media (prefers-reduced-motion:reduce)` 一键关闭非必要动效。**
### 10.4 z-index 层级（统一，杜绝互相遮盖）
base 0 / sticky 100 / dropdown 1000 / sticky-topbar 1100 / drawer 1200 / modal 1300 / toast 1400 / command-menu 1500。

---

## 11. 旧 UI 收敛迁移策略（对接 22 CSS 现状，本轮只定策略不删文件）
1. 新增**唯一** `zbip-tokens.css`（基础+语义 Token）与 `zbip-components.css`（共享组件），作为最终单层真相；施工期在 index.html **最末**引入以获得确定性优先级，但目标是**回退删除旧层**而非长期叠加。
2. 旧 22 CSS 逐个打标：ACTIVE（保留）/ DUPLICATE（与新层重复）/ LEGACY（历史）；每退役一个先做引用扫描 + 六断点视觉回归 + 截图 Evidence，再移除 link（不直接删文件，先注释/记录，一个 PR 一件事）。
3. 同步收敛重复 JS（zachary_robot / enhanced / 3d / png_face 等多套）：同法打标、引用分析后再退。
4. 任何页面禁止新增 fix-final-v2 式私有层；新增样式必须走 Token/组件。

## 12. 无障碍 / 性能 / 落地门槛
- 对比度：正文 ≥4.5:1、大字/图标 ≥3:1；键盘可达（focus-visible 可见焦点环 `2px solid --zb-stone-900`）、语义化 HTML、ARIA 仅在原生不足时补；颜色非唯一信息。
- 性能：不引远程字体/大动画库/巨型图片；优先原生 JS + CSS；首屏关键 CSS 内联或单文件；动效只改 transform/opacity（避免 layout/paint 抖动）。
- 每个页面/组件交付需带 UI Evidence（见 `docs/UI/UI-EVIDENCE-PROCESS.md`）：六断点截图 + 状态矩阵截图 + commit + 性能指标。

## 13. 开发顺序（铁律：先设计系统→页面地图→组件→最后代码）
本文件 = 设计系统；随后 `COMPONENT-SYSTEM.md`（组件地图与规格）、四份 PAGE-MAP；评审冻结后才允许在 Staging(8301) 写组件与页面，生产 8201 与业务后端在 UI 施工期冻结、不改业务逻辑。
