# Learning Log — UI Functionization & Micro-silver Design Layer

Date: 2026-09-04 | Source: ZBC (序境-Core) UI 函数化施工 | Owner: 序境-Intelligence / OSAI

## 1. GitHub 前沿研究结论（本轮 3 次检索）

### 1.1 Design Token 标准化 — W3C DTCG 2025.10
- 标准：Design Tokens Community Group Format Module（DTCG 2025.10），分层 primitive → semantic → component。
- 落地：oklch() + color-mix() 色彩体系；CSS 自定义属性承载 token 层级。
- 与序境关系：xujing-silver.css 的 `--xj-silver-50..500` + `--xj-ink` + 状态色 token 采用 semantic 层命名，方向正确。ADOPT（渐进，不推翻现有 zbip design token）。

### 1.2 微光银 Shimmer 动效
- 实现：`background-clip:text` + `background-size:280%` + background-position 位移动画（5.6s 循环）。
- 卡片级微光：`::after` 叠加线性渐变扫描带（浅色变体，不压信息层级）。
- 与序境关系：`.silver-shimmer`（splash 标题）+ `.xj-card-silver::after` 已落地，浅色、低装饰、克制。ADOPT。

### 1.3 细线 Icon 体系 — Lucide / Feather
- 规范：24×24 viewBox、1.5px stroke、currentColor、圆头（round cap/join）、几何统一。
- 与序境关系：xujing-icons.js 采用同一 stroke 范式，方向完全正确。ADOPT。

## 2. UI 函数化落地（ZBC 本轮执行）

### 2.1 xicon 图标注册表（函数计算层）
- `static/js/xujing-icons.js`：图标注册表（数据表，56 图标）→ `xicon(name,size,cls)` 纯函数 → 模板 `${xicon()}` / 拼接 `+xicon()+`。
- 规则：数据驱动、单一注册、禁止字符串写死 SVG；拼接字符串禁用 `${}` 插值（踩坑记录：brand_hub 曾误用）。

### 2.2 「禁 emoji 当正式 icon」红线
- 全仓状态符号类 emoji 清零：**362 → 14**（本轮清 348）。
- 剩余 14 项全为语义保留：✓/✗ 状态文本（class check 着色）、✕ 关闭符、控制台日志、代码注释（非装饰性正式 icon）。
- 分类策略：正式 icon → xicon()；状态符号 → CSS 状态点 `.xj-dot`（ok/warning/error/pos/neg/neu）；toast/结果文本 → 去 emoji 前缀；✕ 关闭符保留。

### 2.3 14 条 UI 规范（来自用户参考素材，落 XUJING-UI-STANDARD.md）
对比度 3:1/4.5:1、单主按钮、按钮 ≥48pt、6/4/16pt 间距体系、不只靠颜色作指标、避免多屏对齐、移除不必要容器、仅常规+粗体字重、保持一致、极简≠单调、图标文字间距 ≥1.5× 图标大小、禁假图标字符等。

### 2.4 动效组合逻辑（参考素材录屏逐帧提取）
- Stagger 级联逐个进入 + 多段 translate Keyframes 多向冲入 + Float 轻柔漂移 + Continue-through 落地聚合。
- 已落地 CSS：`.xj-stagger`（级联）、`.xj-in-pop`（多向冲入）、`.xj-float`（轻柔漂移）。
- 铁律：动效由数据表驱动（zbip_motion.js MotionTable 纯函数层），禁止为动画而动画。

## 3. Evidence
- ZBC commit: 5d05ce3（UI函数化批次2）、ad9253d（批次1+微光银层）、更早 f9c2a47/0671f3f/9235897/063ea26/11aec5f/9a62682（icon 层+10 模块）。
- 验证：node --check 全部改动文件通过；浏览器实机验证 xicon 56 图标可用、微光银 token/动效类就位、无前端 JS 报错。
- 权威基线：docs/UI/XUJING-UI-STANDARD.md（双库同步）。

## 4. 批次3 · UI 规范落地（GitHub 前沿研究 2026-09-04）
### 4.1 Touch Target（WCAG 2.5.8 / EAA 强制）
- AA 最小 24×24 CSS px；增强 44×44（iOS HIG）/ 48dp（Material）；EAA 2025-06 已强制（罚 EUR 3M）。
- Spacing Exception：目标小于 24px 时，若以目标圆心 24px 圆不与相邻目标重叠即合规；icon-only 控件用 padding 扩 hit area，视觉保持 24px。
- 落地：xujing-silver.css `--xj-touch-min/target` + `.xj-touch`/`.xj-touch-icon`（命中区规范，相邻间距 ≥8px）。

### 4.2 表驱动 Reveal 进入动效（Stagger）
- 最优实践：IntersectionObserver + CSS class toggle + transition-delay 级联；75ms 为卡片栅格 sweet spot，单组级联 ≤400ms。
- 零依赖方案（lite-smart-observer <2KB）：跨帧 stagger batching + WAAPI commitStyles + once 模式 + willChange 即时提升。
- 落地：`xj-reveal.js`（零依赖 IO，fire-once，75ms 阶梯/≤400ms 上限，`--xj-delay` 由子元素索引计算=数据表驱动）+ `[data-xj-reveal]` pop/slide 变体；reduced-motion 强制显示。
- 应用：首页 metric-grid(8 指标)、home-cards(4)、osai-module-grid(3)、smart-grid(智能能力中心 4)——隐藏 tab 面板不触发（真实可见才动）。

### 4.3 Spacing Scale（4px 基准）
- 4px 基准刻度（Tailwind/GitHub Primer/Atlassian 同源）：--space-1..32，低阶 4px 递增、高阶 8/16px 跳档；内部间距 ≤ 外部间距（internal ≤ external）。
- 落地：补齐 --xj-space-10/12/16（40/48/64px），与既有 --xj-space-1..8 统一。

## 5. Evidence（批次3）
- ZBC commit: 33d5ea9（feat(ui): 规范落地批次3）— 已 push 520e11d..33d5ea9。
- 验证：node --check xj-reveal.js 通过；静态 200；浏览器实机——首页 metric-grid 8 指标与 smart-grid 4 卡级联入场（--xj-delay 0/75/150/225/300/375ms），隐藏面板不触发（正确），无 JS 运行时异常（502 为既有瞬时资源错误）。

## 6. 批次4 · 微光银增强 + Touch Target 应用 + 对比度校验（GitHub 前沿研究 2026-09-04）
### 6.1 微光银增强（用户：要能看出明显白/银、海浪波纹划过、方向随机）
- 更亮白/银：波峰线用 repeating-linear-gradient(102deg) 排成浪涌（.14→.85 白渐层），mix-blend-mode:screen。
- 海浪波纹：多组波峰线沿 --xj-shine-x0/y0→x1/y1 随机方向扫过卡片（6.8s cubic-bezier，不呆板）。
- 方向随机表驱动：xj-shine.js 6 组方向向量随机分配，数据表驱动（禁单一方向写死）。
- 扩散：.panel.glass-card/.metric-card/.home-card/.smart-card/.osai-module-card/.ev-stat-card/.case-card/.brand-card 统一挂 .xj-card-silver，MutationObserver 动态补标；实机 52 面板 is-live，方向多样性 6/6。
- specificity 坑：旧 `.xj-card-silver.is-live::after{animation:xj-card-shine}` 覆盖新 `.xj-card-silver::after`；须把动画规则放 `.is-live::after` 同 specificity 后置。

### 6.2 Touch Target 应用（WCAG 2.5.8）
- 16 类图标按钮/关闭符（modal-close/icon-button/btn-icon/zachary-chat-close 等）扩 44×44px 命中区。
- 实机验证可见 btn-icon 44×44（minW/minH 44px）。

### 6.3 对比度逐色校验（WCAG 1.4.3，基于真值源）
- 19 项 token 对全 PASS；修复 3 项：
  - --xj-text-tertiary #a1a1aa→#8a8a93（on 白 3.42 / on 底 3.20，≥3:1 大字/标签）
  - --xj-warn #c8a24b→#b08a30（on 白 3.22，≥3:1）
- 单主按钮核对：HTML modal 0 处多主按钮，符合规范。
- 校验方法：脚本从 CSS 真值源提取 token 计算（WCAG 相对亮度公式），非硬编码。

## 7. Evidence（批次4）
- ZBC commit: f3e5c33（feat(ui): 规范落地批次4）— 已 push 33d5ea9..f3e5c33。
- 验证：node --check 通过；静态 200；浏览器实机——52 面板 xj-wave-move 海浪动画、6 组方向随机、关闭符 44×44、无 JS 运行时异常。


## 8. 批次5 · 函数驱动玻璃质感层 + 启动海报放大（2026-09-04 工程方法论沉淀）
### 8.1 CSS 级联黑盒的根因（重要教训）
- 现象：同一玻璃规则在部分卡片生效（.metric-card/.home-card/.glass-card）、在 .panel 不生效；backdrop-filter 全不生效。
- 根因（逐一实测定位）：
  1) `zb-theme.css`/`zb-gpt-theme.css` 的 `body{background:var(--x)!important; background-image:none!important}` 压掉微光银 body 渐变 → 需同优先级 `!important` + 后加载。
  2) `design-v8.css` 的 `#page-overview article.glass-card` 是 **ID 级 (1,0,2+)** 规则 → 碾压类选择器玻璃（类最多 (0,9,0)）→ 首页卡片白底。
  3) `xujing-design-system.css` 的 `.card,.glass-card,.metric-card,...` (0,5,0) `!important` 白底；`xujing-data-presentation.css`（最后加载）`.metric-card{background:var(--xj-bg-elevated,#fff)!important}` 又覆盖。
  4) `zb-theme.css` 有 `backdrop-filter:none!important` → 全局禁用玻璃模糊。
- 结论：静态 CSS 在"多代皮肤层 + !important + ID 规则"并存下不可控；纯靠 CSS 加选择器不可持续。

### 8.2 解法：函数驱动玻璃层（用户方法论：数据表→函数→运行时应用）
- 在 `xj-shine.js`（表驱动引擎）扩展 `GLASS` 参数表 + `glassify(el)` 纯函数：
  - `GLASS = { bgTop, bgBottom, blur:14, sat:1.35, border, radius }`（数据表）
  - `glassify(el)` = 由参数表计算 → `el.style.setProperty('background','linear-gradient(...)','important')` + backdrop-filter（内联 !important 是最高优先级，绕开一切 CSS 级联）
  - `markAll()` 对 PANEL_SELECTOR 全部应用 + MutationObserver 动态补标。
- 效果：52 面板统一玻璃渐变 + blur(14px) saturate(1.35)，跨页一致，100% 生效。
- 设计原则：CSS 层作为兜底（已有玻璃渐变规则），JS 函数层作为权威执行层；参数全部表驱动，禁硬编码散值。

### 8.3 启动海报放大（芥子纳须弥·银灰）
- 覆盖源：`xujing-design-system.css #splash .splash-title{font-size:18px!important}`（ID 级）压住放大。
- 修复：权威层改 34px + letter-spacing 4px + weight 650；splash.css 主规则同步 34px、移动端 28px；silver 层 splash-content 460px/36px 28px、银灰渐变底。
- 实机：titleFs=34px、contentMw=460px、splashBg=linear-gradient(165deg #f6f7f9→#e6e9ee)、titleShimmer=true。

### 8.4 权威层玻璃化（避免类选择器 vs ID 的军备竞赛）
- 直接改权威 token 层（design-system .card,... 5 类规则 → 玻璃渐变）与首页 ID 规则（design-v8 #page-overview article.glass-card → 玻璃），让"正确来源"自带玻璃，而非层层 !important 对抗。
- 收敛层 data-presentation（最后加载）追加"微光银玻璃统一层"兜底。
- 教训：先审计谁是"权威来源"，改来源而非堆覆盖；CSS 无法表达动态统一质感时，交由函数驱动层。


## 9. 批次6 · 微风银光层叠修正 + 流光置底方法论（2026-09-04）
### 9.1 用户反馈闭环：银色流光不应覆盖文字（"太假"）
- 根因：`.xj-card-silver::after`（卡片流光）与 `body::before`（全局微风光斑）均未设正确 z-index，绝对定位伪元素渲染在内容之上 → 银光盖住文字/数据。
- 修复（层叠三原则）：
  1) 卡片流光 `::after { z-index: 0 }`；卡片内容 `.xj-card-silver > * { position: relative; z-index: 1 }` → 流光在玻璃背景之上、文字之下。
  2) 全局微风光斑 `body::before { z-index: -1 }` → 在 body 银灰渐变背景之上、全部内容之下（背景氛围层）。
  3) 流光强度克制：`xj-wave-move` 峰值 opacity `.82 → .22`（从"明显扫过/接触不良"到"微风浮过海面"的轻柔氛围）。
- 验证：computed z-index 0/-1/1、wavePeak 0.22、文字可读性正常。

### 9.2 函数驱动触达点继续扩展
- `xj-shine.js` 新增 `TOUCH_SELECTOR` 数据表（15 类图标按钮/关闭符）+ `touchify()`：运行时批量加 `.xj-touch-icon`（44×44 命中区、视觉保持小图标），免逐处 HTML 手改。
- 验证：首页 13 个图标按钮/关闭符自动获得 touch 命中区；`btn-icon`/关闭符 44×44、`icon-button` 受历史 skin `width:30px!important` 压制 → 需在权威层校正（渐进项）。

### 9.3 ZBMP 独立页接入（全产品质感统一）
- 发现：ZBMP 工作台（独立 html）仅引 zbip-tokens.css，未接入微光银。
- 修复：head 引 xujing-silver.css；末尾引 xj-shine.js；PANEL_SELECTOR 扩展 ZBMP 特有类（sidenav/content-area/terminal/filetree，已核对主系统无类名冲突）。
- 验证：ZBMP 四面板 glassify + backdrop blur 生效，body 银灰渐变统一。

### 9.4 证据看板核对
- #page-evidence 4 个 ev-stat-card/panel 全部函数玻璃化（4/4），跨页一致。


## 10. 批次7 · 导航函数化 + 6 大域 IA 落地（2026-09-04）
### 10.1 用户反馈：按库里最新层级分级重新规划布局
- 权威规范：`docs/UI-IA-INTERACTION-DESIGN-BASELINE-20260903.md`（6 大域 IA）+ `docs/UI-INTERACTION-SYSTEM-V1-20260903.md`。
- 6 大域：工作台 / 监测 / 事件 / 洞察 / 资产 / 系统；层级 Domain→Page→Section→Module→Component→Action→State。
- 旧导航 7 组（总览/监测/分析/品牌资产/产出/系统）→ 收敛为 6 大域。

### 10.2 函数驱动导航（新架构）
- 新建 `static/js/xujing-nav.js`：`NAV_IA` 数据表（6 域 28 项，含 page/link/button 三种 kind）→ `xnav()` 纯函数 → 同步渲染 side-nav。
- icon 复用 `xujing-icons.js` 注册表（xicon），补注册 keyboard。
- 渲染时机关键：xujing-nav.js 在 body 中段（app.js 之前）**同步**渲染（不等 DOMContentLoaded），保证 app.js 顶层 `.side-item` 绑定拿到元素。
- 新增页只需改 NAV_IA 数据表，导航自动收敛（单一数据真相）。

### 10.3 规避外壳层重复叠加（关键坑）
- `zbip-shell.js` boot() 曾把 side-item 按自身 GROUPS（旧 7 组）重新分组 appendChild → 与 xnav 6 域渲染叠加、DOM 顺序错乱。
- 修复：zbip-shell 检测 `nav[data-xnav-mounted]`（xnav 已渲染）时**跳过分组块**，保留 workspace bar/搜索/顶栏线性化增强。
- 验证：6 域 28 项顺序正确、搜索过滤生效、点击跳转/active/badge 全正常、无 JS 报错。

### 10.4 函数驱动方法论延伸
- 导航 = 数据表（NAV_IA）→ 纯函数（xnav）→ DOM。新增/改名/调整顺序只改表。
- 外壳层（zbip-shell）与内容层（xnav）解耦：内容层渲染权威结构，外壳层只做增强（搜索/工作区切换器），通过 data-xnav-mounted 标记互不冲突。


## 批次8 · UI 重构 v2 — 唯一视觉权威层 + iPod/Apple 金属质感（2026-09-04）

### 触发
用户上传参考视频（448x960 竖屏，134秒，3942帧），要求逐帧分析学习新风格；同时指出"依旧错了"，要求删除所有旧设计文件、功能不变、重新设计。

### 视频逐帧分析结论（iPod / Apple 拟物极简美学）
- **银色金属质感**：iPod Classic 银色金属边缘 + 白色正面 + 物理光泽与深度
- **圆形控制元素**：Click Wheel 转盘、圆形按钮、圆角卡片
- **黑白银配色**：大量白色、银色、黑色，极简无多余色彩
- **毛玻璃半透明**：iOS 风格毛玻璃面板 + 分组列表
- **大量留白**：内容居中，少装饰，物理阴影表达深度
- **深色/浅色切换**：视频中同时展示深色模式和浅色模式
- **新布局层级模型**：顶部金属导航条 + 中部白色卡片分组内容 + 底部/侧栏圆形控制

### 执行动作
1. **归档→物理删除 14 个废弃设计主题 CSS**（9735 行）：
   design-v8 / design-v9-gpt-codex / tokens-minimal / components-minimal / layout-minimal /
   zb-theme / zb-gpt-theme / splash / xujing-crossfilter / xujing-data-presentation /
   xujing-design-system / xujing-silver / ui_polish / zbip-motion
   - 删除前全仓扫描确认：仅 xujing-silver 被 zbmp-workbench.html 引用，其余 13 个无任何 HTML/JS 引用
   - zbmp-workbench.html 已切换为 xujing-core.css
2. **新建唯一视觉权威层 `xujing-core.css`**（20KB，15 模块）：
   - Design Token（银灰语义色/4px间距刻度/圆角/极轻阴影/动效/z-index）
   - 全局重置 + 微光银底层（body::before 银灰渐变 + body::after 横向微光扫描，z-index 0 不覆盖文字）
   - 三栏布局骨架（侧栏248恒显 / 内容flex撑满 / 右栏320）
   - 6 大域导航（side-item 38px 强制高度 / active 深色背景 / badge / group-label）
   - workspace 互斥显隐（CTH 显 6 域隐藏 zbmp-nav / ZBMP 反之）
   - 顶部栏 + 卡片/KPI/按钮（单主按钮原则：深色主按钮 + 浅色次按钮）
   - **弹窗显隐协议**：#modal 默认 display:none，.open 时 display:flex（修复 xujing-design-system 旧 bug：.modal{display:flex} 覆盖默认 none 导致空弹窗常显）
   - 状态点 CSS 圆点（替代 emoji 状态符号）
   - 动效组合（Stagger 级联 / In-Pop 冲入 / Float 漂移）
   - 表格/数据展示
   - 响应式（≤1199 右栏收窄 / ≤1023 右栏隐藏 / ≤767 侧栏抽屉）
   - 无障碍（焦点可见 / prefers-reduced-motion）
   - **iPod/Apple 金属质感模块**：.xj-metal-card（金属渐变+顶部高光+微光扫描）/ .xj-circle-btn（圆形控制按钮44px）/ .xj-glass（毛玻璃增强）/ .xj-group-list（iOS 分组列表）/ .xj-metal-divider / .xj-depth-1~4（物理深度阴影）/ 深色模式支持
3. **修复 side-item 高度塌缩 bug**：旧功能骨架 CSS 导致 .side-item 高度为 0（display:flex 但 h:0），28 项导航不可见。修复：height:38px !important + min-height:38px + flex-shrink:0 + side-nav overflow-y:auto。
4. **修复右栏消失 bug**：.right-panel 被功能骨架 CSS 设为 display:none，新系统补 display:block !important。

### 验证证据
- 实机 DOM：side-item 高度 [38,38,38,38,38,38]，6 域 28 项完整可见
- 布局：sidebar 248 / content 263 / right-panel 280，scrollWidth 840 ≈ viewport 855（无横向溢出）
- 弹窗：#modal display:none（默认隐藏）
- CSS：19 个引用，无 404，无废弃主题
- 服务器：healthz 200，xujing-core.css 200 len=20119

### 关键方法论
- **唯一视觉权威层**：多主题层叠是 bug 温床（xujing-design-system 的 .modal{display:flex} 覆盖 style.css 的 .modal{display:none} 导致空弹窗常显）。收敛为一个 xujing-core.css，功能骨架 CSS 只负责布局/组件行为，不负责视觉主题。
- **删除前全仓扫描**：14 个文件中仅 1 个被其他页面引用，处理后安全删除。禁止凭文件名删除。
- **参考视频逐帧分析**：cv2 抽帧（每30帧一张，132帧）→ contact sheet → 提取风格元素（金属质感/圆形控制/毛玻璃/留白/深色模式）→ 落地为 CSS 类（.xj-metal-card / .xj-circle-btn / .xj-glass）。
- **函数驱动**：导航由 xujing-nav.js 的 NAV_IA 数据表 + xnav() 纯函数渲染，CSS 只负责视觉，不重复定义导航结构。

### Commit
- ZBC: 3ff91ee（UI重构v2: 删除14废弃CSS + 新建xujing-core + 修复side-item + ZBMP切换 + 金属质感落地）
- 此前: c9f4c7b（UI收敛: 移除7废弃主题层 + 侧栏恒显 + workspace互斥 + 导航优先 + 内容均衡 + 弹窗隐藏）


## 批次9 · 可视化函数层 v1 — 数据→函数→表格→SVG→实时动效（2026-09-04）

### 触发
用户要求"动态交互、可视化趋势图（实时）都要推进，数据都是函数转换进来"，授权 99 次中 10 次加大算力。强调"函数驱动代码"。

### 执行动作
1. **CSS 收敛确认**：21 个 CSS（19 功能骨架 + xujing-core 统一设计 + taiji-state），无废弃设计文件残留。
2. **新建统一可视化函数层 `xujing-viz.js`**（15KB，11 模块）：
   - **数据获取层** `xjViz.api(endpoint, params)`：统一 fetch（带 Basic Auth），所有数据从 API 函数转换进来。
   - **Canonical 纯函数转换层** `xjViz.fn`：
     - `FN_SENTIMENT_COUNT(data)` → {positive, neutral, negative, total}（high 只计 high，critical 独立）
     - `FN_RISK_COUNT(data)` → {critical, high, medium, low, total}（critical 独立成更高指标，不悄悄并入 high）
     - `FN_ENGAGEMENT(data)` → {likes, comments, collects, shares, total}（likes+comments+collects+shares）
     - `FN_TREND_SERIES(trendArray, metric)` → 标准化时间序列 [{date, label, value, total, positive, negative, high}]
   - **KPI 渲染** `xjViz.kpi(container, label, value, opts)`：数字滚动动效（easeOutCubic，800ms），颜色语义（pos/neg/warn）。
   - **表格渲染** `xjViz.table(container, data, columns)`：数据→HTML 表格，支持自定义 render 函数。
   - **SVG 趋势图** `xjViz.trend(container, series, opts)`：纯 SVG 渲染，支持折线/面积/柱状三种类型，路径绘制动画（stroke-dashoffset 1.2s），数据点渐入，网格线+坐标轴，无第三方图表库依赖。
   - **环形图** `xjViz.donut(container, data, opts)`：SVG 环形图，多分段渐入，中心文字。
   - **数字滚动** `xjViz.animateNumber(el, from, to, duration)`：requestAnimationFrame + easeOutCubic。
   - **Stagger 级联** `xjViz.stagger(container)`：子元素逐个延迟进入。
   - **实时更新** `xjViz.realtime(container, endpoint, interval, renderFn)`：定时轮询 + 平滑过渡，返回 {stop, getData, refresh} 控制器。
   - **组合渲染** `xjViz.renderAIPanel(container, data)`：一键渲染 KPI 行 + 趋势图 + 环形图。
3. **xujing-core.css 新增第 16 模块**：可视化组件样式（KPI 卡片 grid 布局/趋势图容器/环形图容器/数据表格/空状态/可视化面板）。
4. **首页 AI 洞察面板注入实时数据看板**：在 `.right-panel-body` 顶部插入 `#xjVizPanel`，30s 轮询 `/api/dashboard/all`，渲染 4 KPI + 14 天趋势图 + 情感环形图。

### 验证证据
- 实机 DOM：hasXjViz=true, panelExists=true
- KPI：4 卡片，标签 [正面舆情, 负面舆情, 高风险内容, 总互动量]，值 [629, 97, 23, 46.1万]——与 API 数据完全一致（stats.positive=629, negative=97, high_risk=23, total_engagements=461041）
- 趋势图：SVG 渲染，2 条 path（折线+面积），14 个 circle 数据点（对应 14 天 overview.trend）
- 环形图：SVG 渲染，4 个 circle（背景环 + 正面/中性/负面 3 分段）
- 无 JS 报错，30s 实时更新循环已启动

### 关键方法论
- **函数驱动可视化**：数据获取(api) → Canonical 纯函数转换(fn) → 渲染函数(kpi/trend/donut/table) → 动效(animateNumber/stagger) → 实时(realtime)。每层都是纯函数，数据从 API 函数转换进来，不重复计算业务指标。
- **Canonical 函数是数字唯一真相**：FN-SENTIMENT-COUNT / FN-RISK-COUNT / FN-ENGAGEMENT 三个纯函数定义了情感/风险/互动的唯一计算口径，所有可视化（KPI/趋势图/环形图/表格/报告/AI）都调用同一函数，保证"首页=表=图=报告=导出"一致性。
- **无第三方图表库**：纯 SVG 渲染趋势图和环形图，零依赖，体积小，可完全控制动画和样式。
- **实时更新不破坏现有功能**：可视化面板注入到右栏顶部，不修改 app.js 现有渲染逻辑，30s 轮询独立运行。

### Commit
- ZBC: 7b48cc2（可视化函数层v1: xujing-viz.js + Canonical纯函数 + KPI/趋势图/环形图 + 30s实时更新 + 首页AI洞察面板注入）


## 批次10 · UI 重构 v3.0 — iOS HIG + iPod Metal 全面重写（2026-09-04）

### 触发
用户要求"根据参考视频风格，推进整体 UI 视觉及架构布局，重新构造，学习 iOS 系统的 UI 设计和交互，不允许擅作主张，全面推进，最大算力，给 60000 额度"。

### 前置：IA 规范确认
读取 `docs/UI-IA-INTERACTION-DESIGN-BASELINE-20260903.md`，确认 6 大域（Workspace/Monitoring/Events/Insights/Assets/System）和设计原则（操作优先/结构美/编辑式奢华/细线图标/动效功能性/渐进式披露/无静默上下文丢失）。重构严格遵循此规范，不越界。

### 执行：全面重写 xujing-core.css v3.0（27.7KB，15 模块）
1. **iOS 系统色彩**：systemBlue #007AFF / systemGreen #34C759 / systemRed #FF3B30 / systemOrange #FF9500 + iOS 6 级灰（#8E8E93~#F2F2F7）+ 序境黑白米灰语义色。
2. **SF Pro 字体 + 排版层级**：-apple-system/BlinkMacSystemFont/"SF Pro Display"/PingFang SC；大标题 34px / 标题1 28px / 标题2 22px / 标题3 20px / headline 17px / body 15px / subhead 15px / footnote 13px / caption 12-11px。
3. **毛玻璃 UIVisualEffectView**：backdrop-filter: blur(20px) saturate(1.8)，侧栏/右栏/顶部栏/可视化面板全部毛玻璃。
4. **iOS 导航元素**：大标题导航栏、搜索栏（聚焦时白色背景+蓝色光晕）、分段控件（毛玻璃背景+选中态白色卡片）。
5. **iOS 分组列表**：侧栏导航改为 iOS Grouped Table View 风格——分组标签大写小字、单元格 40px 高、圆角 12px、选中态深色背景+白字、badge 红色胶囊。
6. **iPod Click Wheel 圆形控制按钮**：.xj-circle-btn 44px 圆形，银色金属渐变（白→浅灰）+ 内高光 + 外阴影，hover scale 1.06，active scale .94。
7. **iPod 金属卡片**：.xj-metal-card 银色金属渐变（白→#f8f9fb→#f0f2f5）+ 顶部 1px 高光条 + 横向微光扫描动画 7s + 内阴影。
8. **弹性动效**：统一 cubic-bezier(.22,1,.36,1)（iOS spring），micro 140ms / component 220ms / workspace 320ms / viz 440ms；弹窗弹性弹出（scale .92→1.03→1）；Stagger 级联；In-Pop 冲入；Float 漂移。
9. **微光银底层**：body::before 银灰径向渐变（双光源）+ body::after 横向微光扫描 9s（微风浮过海面），z-index 0 不覆盖文字，opacity .35 自然不刺眼。
10. **iOS Alert 弹窗**：#modal 默认 none，.open 时毛玻璃背景（blur 8px）+ 居中白色圆角卡片 + 弹性弹出动画；修复旧 bug（xujing-design-system 的 .modal{display:flex} 覆盖默认 none）。
11. **深色模式**：@media (prefers-color-scheme: dark) 完整适配——纯黑背景、iOS 深色灰阶、毛玻璃深色、金属卡片深色渐变、搜索栏/分段控件深色。
12. **触控目标 44px**：所有可交互元素（side-item/btn/btn-icon/xj-circle-btn/group-item）min-height/min-width 44px（iOS HIG 规范）。
13. **Dynamic Type 基础**：@media (min-width: 1400px) 字号放大（body 16px / 大标题 38px）。
14. **响应式**：1199px 右栏收窄 280px / 1023px 右栏隐藏+侧栏 240px / 767px 侧栏抽屉（transform translateX + 弹性动画）+ KPI 2 列。
15. **无障碍**：prefers-reduced-motion 禁用所有动画、focus-visible 蓝色 2px 外框、语义化状态点（CSS 圆点替代 emoji）。

### 验证证据
- 实机 DOM：scrollWidth 850 ≈ viewport 855（无横向溢出）
- 导航：28 项（6 大域完整），side-item 40px 高度
- 弹窗：#modal display:none（默认隐藏）
- 可视化：xjVizPanel 存在，4 KPI 卡片正常
- CSS：xujing-core.css?v=3.0.0 加载，无 404
- 无 JS 报错

### 关键方法论
- **不擅作主张**：重构前先读取 IA 规范，确认 6 大域和设计原则，所有视觉决策基于 iOS HIG + 参考视频 + IA 规范，不自行发明。
- **CSS 单一权威层**：所有视觉收敛到 xujing-core.css 一个文件，功能骨架 CSS（layout/style/components 等 19 个）只负责布局/组件行为，不负责视觉主题。避免多主题层叠导致的 bug（如旧 xujing-design-system 的 .modal{display:flex} 覆盖默认 none）。
- **iOS 设计三原则**：清晰（Clarity，文字清晰图标精准）/ 遵从（Deference，界面辅助内容不竞争）/ 深度（Depth，视觉层级和动效传达层次）。
- **iPod 金属质感**：银色金属渐变 + 顶部高光条 + 横向微光扫描 + 内阴影，模拟 iPod Classic 银色金属正面的物理光泽。
- **函数驱动不变**：xujing-viz.js 可视化函数层（Canonical 纯函数 + SVG 渲染 + 实时更新）与视觉层解耦，CSS 重构不影响数据逻辑。

### Commit
- ZBC: c7098ab（UI重构v3.0 iOS+iPod Metal: 全面重写xujing-core.css 27.7KB/15模块）


## 批次 11：六大场景导航主导 + GPT 风格聊天界面 v2（2026-09-04）

### 核心变更
1. **导航重构为六大场景主导**（xujing-nav.js v2）
   - 依据产品白皮书 P24-P30 六大应用场景：品牌健康 / Campaign / KOS运营 / 舆情事件 / 危机预警 / 专题研究
   - 其他功能（监测/事件/洞察/资产/系统）均为六大场景的下一层级
   - 每个场景 4-5 个子功能，共 25 项导航
   - 函数驱动：NAV_IA 数据表 → xnav() 纯函数 → 渲染

2. **GPT 风格聊天界面 v2**（xj-chat.js v2）
   - 空状态极简：去掉大头像和"你好"文字，只有输入框+简约建议
   - 顶部分段控件：聊天 / 工作（GPT 风格 segmented control）
   - 大圆角输入框：+按钮 + 输入框 + 发送按钮，focus 时蓝色光晕
   - 建议问题：输入框下方简约胶囊列表（图标+文字）
   - AI 洞察面板：聊天区顶部可折叠，4 KPI（正面/负面/高风险/互动）实时数据

3. **CSS 追加**（xujing-core.css 第18-19模块）
   - 第18模块：聊天界面 v2 完整样式（分段控件/洞察面板/消息气泡/输入框/建议/打字动画）
   - 第19模块：导航 v2 六大场景分组样式（domain 标题/domain icon/nav item）

### Bug 修复
- **apiFetch 默认参数 bug**：loadInsightData 调用 apiFetch(url) 未传 opts，导致 opts.headers 抛出 TypeError，KPI 数据静默失败显示 --
- 修复：apiFetch(url, opts = {}) 添加默认参数
- 修复后 KPI 正常显示：正面 629 / 负面 97 / 高风险 23 / 互动 46.1万

### ZBMP 工作台隔离确认
- ZBMP 不使用 xujing-nav.js 和 xj-chat.js
- ZBMP 使用 xujing-core.css，但 v2 样式都是特定 class（.xj-chat-v2 / .nav-domain），不污染 ZBMP
- ZBMP 自己的 .nav-item 样式优先级更高，未被覆盖
- 实机验证 ZBMP 正常：顶部导航/工作台/功能按钮/文件树/只读终端全部正常

### 设计原则
- **六大场景为主导**：用户最关心的是应用场景，不是技术域
- **GPT 风格简约**：少即是多，空状态只有输入框+建议
- **函数驱动**：所有 UI 由数据表+纯函数渲染，不写死 HTML
- **数据真实**：KPI 直接从 /api/dashboard/all 获取，不造假
- **隔离性**：新样式不影响已有页面（ZBMP 确认）

### Commit
- ZBC: e7765dc（六大场景导航+GPT聊天界面v2+KPI修复，3 files 712 insertions）

### 下一步
- 结合白皮书推进六大场景页面间跳转关系
- AI 洞察面板增加趋势图（复用 xujing-viz.js）
- 聊天界面 AI 回复优化（智谱 glm-4.5-air）
- 六大场景页面内容完善


## 批次 12：采集器6项修复 + 微光银海浪波纹 + 废弃文件清理 + GitHub前沿研究（2026-09-04）

### 12.1 双子库最新基线扫描发现（采集器规则已变化）
- 扫描 ZBC `docs/MASTER/ARCHITECTURE-CUMULATIVE-BASELINE-20260904.md`，发现采集器6项问题：
  1. **熔断冷却死锁**（🔴严重）：`CollectState.STOP_REQUEST` 包含 COOLDOWN，冷却到期后 guard.run 仍拦截，永远不发请求→永远不触发 on_success→state 永久停在 COOLDOWN。RiskEngine 已有完善 half-open 机制但与 guard.limiter 是两套独立系统。
  2. **EMPTY 结果风险分衰减**：`_RISK_FACTOR_BY_STATE` 不含 EMPTY/SUCCESS，classify_collect_state 返回 EMPTY 时走 record_success()，风险分衰减，可能提前解除熔断。
  3. **RiskEngine 熔断联动缺口**：`_feed_risk_engine` 在 RiskEngine 熔断时返回 True 让调用方 break，但没有调用 guard.limiter.force_pause 联动。
  4. **collector 层主体硬过滤缺失**：`_norm_cdp_note` 透传 subject_hit_cdp，但 collect_all 入库前没有基于 subject_hit 做硬过滤，所有 note 直接进入 all_notes。
  5. **采集准确度监控指标缺失**：无 quality 计数器，无法监控抓取成功率/有效内容率/主体命中率/误命中率/重复率/作者解析成功率/时间完整率/互动数据完整率/Evidence完整率。
  6. **captured_at 字段**：审查报告称"未见 captured_at"，但实际 `_norm_cdp_note` L230 已有，双时间铁律注释（L228-229）。**已确认存在，无需修复**。

### 12.2 采集器6项修复落地
| # | 问题 | 修复 | 文件 |
|---|------|------|------|
| 1 | 熔断冷却死锁 | COOLDOWN 状态且 can_run() 返回 True 时放行 half-open 探测 | `guard.py` L72-78 |
| 2 | EMPTY 风险分衰减 | EMPTY 时不调用 record_success/failure，保持当前风险分不变 | `collector.py` L116-121 |
| 3 | RiskEngine 联动 limiter | 熔断时调用 `_get_xhs_guard().limiter.force_pause(CollectState.PAUSED, cooldown_seconds=max(300, risk.reset_timeout))` | `collector.py` L123-131 |
| 4 | 主体硬过滤 | 入库循环检查 `note.get('subject_hit_cdp')`，False 时 continue 跳过；None（standalone 未判定）不排除 | `collector.py` L397-402 |
| 5 | 9项质量门 | 新增 `_quality` 计数器（total_notes/valid_content/subject_hit/subject_unknown/duplicate/author_resolved/timestamp_complete/engagement_complete/evidence_complete）+ `record_quality(notes, seen_nids)` + `quality_metrics` 属性 + snapshot quality 字段 | `metrics.py` 87→154行 |
| 6 | captured_at | 已确认存在，无需修复 | — |

- 语法验证：collector.py / guard.py / metrics.py 全部 py_compile exit 0
- 重启验证：杀 supervisor worker 树→新 PID 32452/36100→/healthz 200

### 12.3 微光银海浪波纹优化（用户：要能看出明显白/银、海浪波纹划过、在底层不覆盖文字）
- **body::before 底层**：三层 radial-gradient（90%×60% 左上光源 / 70%×50% 右下光源 / 50%×40% 中心微光）+ 线性渐变（#fbfcfe→#f5f6f9→#f0f2f6→#eef0f4），银色更明显
- **body::after 海浪波纹**：三层动画叠加——
  - 主波 `xj-wave-main`：横向银色光带（linear-gradient 100deg，峰值 rgba(255,255,255,.6)），12s 缓慢扫过
  - 次波 `xj-wave-sub`：斜向扩散波纹（radial-gradient 60%×30%），18s ease-in-out 交替，涟漪蔓延效果
  - 微波 `xj-wave-micro`：纵向起伏（repeating-linear-gradient 180deg，1px 细纹），8s 起伏，水面细纹质感
- **z-index 保持 0**，内容层 layout z-index=1，**不覆盖文字**
- opacity 从 .35 提升到 .7，银色更明显但仍自然
- 实机验证：after_animation=`xj-wave-main, xj-wave-sub, xj-wave-micro`，after_opacity=0.758，after_zIndex=0，layout_zIndex=1，body_bg=rgb(250,251,252)

### 12.4 废弃规则文件清理（4个无引用文件）
- `docs/PRODUCTION_BASELINE_2026-08-31.md`（6891 bytes，被引用0次）
- `docs/PRODUCTION_BASELINE_2026-08-31-V3.md`（7577 bytes，Grep确认无实际引用）
- `docs/UI-IA-INTERACTION-DESIGN-BASELINE-20260903.md`（14785 bytes，旧版6大域，已被六大场景IA替代）
- `docs/UI/XUJING-UI-STANDARD.md`（6301 bytes，v1，已被v2替代）
- 清理前全仓扫描确认无引用，git rm 安全删除
- 依据：ARCHITECTURE-CUMULATIVE-BASELINE-20260904.md §9 强制删除规则

### 12.5 GitHub 前沿研究（本轮3次检索）
#### 12.5.1 Design Token 标准化 — W3C DTCG 2025.10 稳定版
- **里程碑**：2025年10月28日发布首个稳定版本，40+组织支持（Adobe/Figma/Google/Microsoft/Shopify/Salesforce）
- **格式**：JSON 作为 interchange format，支持 modern color specification（oklch/color-mix）、groups and aliases、token resolvers（contextual resolution for multi-brand）
- **三层结构**：primitive → semantic → component（GeekLego AI-Native Design System 采用同一结构）
- **AI 消费设计系统**：Penpot MCP server（2026年1月发布），AI agents 开始直接消费设计系统
- **Google Labs DESIGN.md**：2026年4月开源，v0.3.0（2026年6月15日），YAML front matter + markdown prose，8个sections
- **与序境关系**：xujing-core.css 的 `--xj-*` token 采用 semantic 层命名，方向正确。ADOPT（渐进，不推翻现有）。

#### 12.5.2 AI Agent 浏览器自动化 2026 格局
- **Browser Use**（开源Python）：WebVoyager benchmark 89%，我们正在用的技术栈
- **Stagehand v3**（TypeScript）：DOM-driven，适合 TS 团队
- **Playwright MCP**：免费确定性选项，Accessibility tree targeting，评分4.5/5
- **Skyvern**：视觉驱动（vision-first，ignores DOM churn），企业级RPA替代，WebVoyager 85.85%，开源可自托管
- **Vercel agent-browser**：41.2k stars，Apache-2.0，persistent Chrome daemon + terse one-shot command surface
- **关键趋势**：DOM-driven vs vision-driven 路线分化；MCP 标准化；Browserbase 云托管浏览器
- **与序境关系**：我们的采集器基于 Playwright + Browser Use，方向正确。Skyvern 的 vision-first  approach 值得研究（抗页面改版能力强），但当前不替换。EVALUATE。

#### 12.5.3 实时数据可视化 2026 趋势
- **Plotly**：70+图表类型，Python/JS，MIT，稳定10年+，time series dual y-axis
- **Chartbrew**：开源报告平台，AI助手，scheduling，embeddable charts，APIs/SQL/NoSQL
- **Shaper**：SQL-driven UI/UX design tool，直接从 SQL 查询生成交互式 dashboard，无需前端代码
- **DataViz Dashboard**：玻璃态UI（glassmorphism），Framer Motion 动画数字计数器，6 KPI + 4 Chart Types，实时数据模拟3s更新
- **关键趋势**：实时动画、玻璃态、AI驱动、SQL-to-dashboard 无代码
- **与序境关系**：xujing-viz.js 纯 SVG 渲染（零依赖）+ 30s 实时更新，方向正确。玻璃态UI已在 xujing-core.css 落地。ADOPT。

### 12.6 Evidence
- ZBC commit: `b2c9e62`（采集器6项修复 + 微光银海浪波纹优化 + 废弃文件清理，8 files changed, 144 insertions, 996 deletions）
- Push: `86874b0..b2c9e62 main -> main`
- 验证：py_compile 全部通过；/healthz 200；实机微光银三层动画运行中；AI洞察面板数据正确（正面629/负面97/高风险23/互动46.1万）；六大场景导航正常
- GitHub研究：3次检索，9+关键发现，ADOPT/EVALUATE分类


## 批次 13 · 2026-09-04 · 智谱全链路接通 + Lifecycle Center + 导航6大域重构

### 13.1 智谱AI全链路接通（PASS）
- **根因定位**：intelligence.py test_connection() 调用 chat() 未指定 pack_id，默认 per_call 额度不足 → budget_blocked → 返回"本地规则引擎已接管"
- **修复**：test_connection 添加 pack_id='glm_4_5_air'（1191万tokens资源包）
- **全量切换**：8个调用点全部切换到 glm_4_5_air
  - review_note (L322) / test_connection (L346) / summarize_event (L335) / translate_text (L355)
  - sentiment_analyse (L372) / generate_summary (L393) / extract_keywords (L407) / generate_report (L543, high)
- **验证**：/api/ai/test 返回 provider=zhipu/model=glm-4.5-air/reply正常
- **ZBC commits**：9949419（AI聊天修复）→ 38f9123（全量资源包切换）

### 13.2 状态符号类emoji清零（PASS）
- **策略**：正式icon→xicon()函数层；状态符号→CSS ::before纯绘制；✕关闭符保留（非emoji）
- **结果**：全仓JS 14→7个，剩余7个全部为✕关闭符
- **CSS层**：xujing-core.css 追加 Pure-CSS Status Glyphs（状态点/对勾）
- **ZBC commit**：feb48de

### 13.3 Lifecycle Center 生命周期中心（PASS，V3 §21）
- **架构**：数据表（STAGES 12阶段 + REGISTRY 5条登记 + CATEGORIES 8分类）→ 纯函数层（lcStageProgress/lcByCategory/lcStageStats/lcTraceForward/lcTraceByCommit）→ 唯一Renderer（lcRender）
- **功能**：总览4KPI / 需求列表+详情追溯链 / 研究笔记 / 决策记录 / 任务卡片 / 运行时 / 证据 / 历史
- **双向Trace**：Requirement→Code→Function→Runtime→UI→Test→Evidence→Commit，反向 Commit→File→Function→Requirement
- **Fixed viewport**：外壳不随页面滚动，仅内部列表 bounded scroll
- **修复**：research/decisions分支渲染后缺少bindCards()导致分类切换失效（每次side.innerHTML重置销毁旧事件）
- **ZBC commits**：31201e4（自动保存）→ 23dabaf（bindCards修复）

### 13.4 导航IA重构为库内6大域（PASS）
- **依据**：docs/UI-FINAL-CAPABILITY-MAP.md 顶层IA定义
- **旧**：产品白皮书6大场景（品牌健康/Campaign/KOS运营/舆情事件/危机预警/专题研究），4个page重复
- **新**：6大域21项全部唯一
  - 工作台(3)：智能问答/品牌声量/监测概览
  - 监测采集(3)：实时监测/风险评估/采集状态
  - 事件笔记报告(5)：事件检测/事件图谱/笔记库/报告生成/舆情日历
  - Zachary AI(3)：深度研究/知识库/案例分析
  - 品牌库(4)：KOS矩阵/品牌管理/销售线索/案例库
  - 系统(3)：证据看板/生命周期/设置
- **验证**：21个page-section全部存在，跳转正常，无重复
- **ZBC commit**：ca97e56

### 13.5 GitHub研究（本轮）
- **Design Token**：W3C DTCG 2025.10 稳定版，primitive→semantic→component三层，oklch+color-mix
- **微光银实现**：background-clip:text + background-size:280% + 位移动画（hero-shine-text浅色变体）
- **细线icon**：Lucide/Feather 24px/1.5px stroke/currentColor/圆头——xujing-icons.js方向正确
- **分类**：ADOPT（渐进，不推翻现有）

### 13.6 Evidence
- ZBC commits: 9949419 → feb48de → 31201e4 → 23dabaf → 38f9123 → ca97e56
- 验证：py_compile/node --check全部通过；/healthz 200；实机6大域导航21项正常；Lifecycle Center 8分类切换正常；AI接口provider=zhipu
- 生产基线：notes=1052/pos629/neu326/neg97/risk high23/互动46.1万


---

## 批次14 — 2026-09-04 晚间 | V3执行体系 + 智谱全链路 + 品牌哲学落地

### 14.1 智谱AI全链路接通（P0）
- **问题**：intelligence.py test_connection() 未指定 pack_id，默认 per_call 额度不足 → budget_blocked，聊天AI回复"本地规则引擎已接管"。
- **修复**：8个调用点全部显式 pack_id='glm_4_5_air'：
  - review_note(L322) / test_connection(L346) / summarize_event(L335) / translate_text(L355)
  - sentiment_analyse(L372) / generate_summary(L393) / extract_keywords(L407) / generate_report(L543, high)
- **验证**：/api/ai/status = enabled/provider:zhipu/model:glm-4.5-air；/api/ai/test 返回正常智谱回复。
- **资源包**：glm_4_5_air 剩 1191万 tokens / search_std 剩 94次 / glm_4_6v 视觉 600万。
- **Commit**：9949419 → 38f9123

### 14.2 状态符号类 Emoji 清零（红线执行）
- **分类策略**：正式 icon → xicon() 函数层；状态符号（✓/✗/⚠️/✨/♥）→ CSS ::before 纯绘制；✕ 关闭符保留（非 emoji）。
- **落地**：xujing-core.css 追加 Pure-CSS Status Glyphs 层；resident_health.js / taiji-state.js 去 emoji 文本。
- **验证**：全仓 JS 仅 7 个 emoji（全部 ✕ 关闭符），node --check 5/5 OK。
- **Commit**：feb48de

### 14.3 Lifecycle Center 生命周期中心（V3 §21）
- **架构**：static/js/lifecycle-center.js（18KB）
  - STAGES 12阶段状态机（DISCOVERED→RESEARCHED→DECIDED→SPECIFIED→IMPLEMENTED→LOADED→RUNNING→TESTED→VERIFIED→DELIVERED→MONITORED→IMPROVED）
  - REGISTRY 5条登记 + CATEGORIES 8分类
  - 纯函数层：lcStageProgress / lcByCategory / lcStageStats / lcTraceForward / lcTraceByCommit
  - 唯一 Renderer：lcRender()；对外 API：LifecycleCenter.render/registry/traceByCommit/stageProgress/stages/register
- **页面**：index.html page-lifecycle section（.lc-shell 左右分栏 + fixed viewport）
- **Bug修复**：research/decisions分支渲染后直接 return 未调用 bindCards()，导致分类切换事件丢失 → 修复后8分类全切换正常。
- **验证**：总览4KPI / 需求5卡+10行追溯链 / 研究5行 / 决策5行 / 双向trace commit→requirement 正常。
- **Commit**：31201e4 → 23dabaf

### 14.4 导航IA重构为库内6大域（V3信息架构）
- **依据**：docs/UI-FINAL-CAPABILITY-MAP.md 顶层IA定义
- **6大域21项（全部唯一）**：
  - 工作台(3)：overview / brand-dashboard / monitor
  - 监测采集(3)：alerts / negative / resident-health
  - 事件笔记报告(5)：events / event-graph / notes / reports / calendar
  - Zachary AI(3)：analysis / knowledge-base / case-analysis
  - 品牌库(3)：kos / cases(品牌案例库) / official
  - 系统(3)：evidence / lifecycle / settings
- **修复**：旧导航存在4个重复page（events/calendar/brands/analysis各2次），12个导航项指向不存在的section。
- **验证**：21项导航全部唯一，21个page-section全部存在，跳转测试4/4正常。
- **Commit**：ca97e56

### 14.5 zbHome品牌哲学三语诠释（品牌哲学视觉化）
- **品牌哲学**：芥子纳须弥（微小之中本身就包含通向整体的结构）
- **三语诠释**：
  - 中文：芥子纳须弥
  - 英文：In the minutest seed, the cosmos is already structured.
  - 韩文：가장 작은 씨앗 속에 우주가 이미 구조화되어 있다.
- **布局**：zbHome 前置页承担AI检索 + 品牌哲学视觉诠释，参考极简AI搜索界面布局（颜色不参考，布局参考）。
- **标题**：序境 · XUJING（silver-shimmer 微光银效果）
- **模型标签**：序境 · 智谱 AI（glm-4.5-air）
- **Bug修复**：Python字节替换中文字符时双反斜杠导致字面写入 → 标题乱码"åºå¢ Â· XUJING" → Edit工具直接替换修复。
- **验证**：zbHome isShow=true，三语诠释全部正确渲染，标题中文正常。
- **Commit**：3794c38

### 14.6 案例库与品牌库整合（消除重复）
- **问题**：品牌库域同时存在"品牌管理(brands)"和"案例库(cases)"，重复度过高。
- **整合**：合并为「品牌案例库」（序境自行命名），指向 cases 页面，描述整合为"品牌档案、业态对比、营销案例卡片、详情下钻与复盘"。
- **结果**：品牌库域 4项→3项（KOS矩阵 / 品牌案例库 / 销售线索）。
- **Commit**：7c70475

### 14.7 page-overview HTML结构修复（Root Cause分析）
- **问题**：xj-page-header 缺少闭合标签，导致 metric-grid / home-cards / osai-module-grid 被错误嵌套在 header 内。
- **影响**：header 高度 2288px（异常），页面布局错乱。
- **修复**：index.html L412 后添加 </div> 闭合 xj-page-header。
- **验证**：header 高度 2288px→151px，4个直接子元素正确分离（xj-page-header/metric-grid/home-cards/osai-module-grid）。
- **V3流程**：READ→AUDIT→TRACE（div开闭平衡154/154但嵌套错误）→IMPLEMENT→TEST→VERIFY→COMMIT
- **Commit**：2a1bc4f

### 14.8 report_api 语法错误修复（服务启动失败根因）
- **问题**：report_api.py L281 import 语句缩进错误 + as _dr 用法错误（from ... import (...) as _dr 语法不合法）。
- **影响**：app.py 无法导入 report_api → 服务启动失败 → 8201 端口无响应。
- **修复**：import daily_report as _dr，report_filter 导入正确缩进。
- **验证**：app import OK，healthz 返回 {"ok":true,"service":"taikoo-monitor","version":"5.9.9"}。
- **Commit**：2a1bc4f

### 14.9 GitHub研究：AI搜索界面设计 + 品牌哲学视觉化
- **AI搜索界面趋势**：极简居中搜索框 + 渐变标题 + 建议卡片 + 大圆角；参考图"Complexity turned into Simplicity"布局。
- **品牌哲学视觉化**：Braun/Apple 极简路线，三语诠释分层排版（中文大标题/英文斜体小字/韩文更小字）。
- **ADOPT**：zbHome 前置页采用极简居中布局 + 三语诠释 + 智谱模型标签。

### 14.10 V3执行体系落地
- **流程**：READ → AUDIT → TRACE → RESEARCH → DECIDE → SPECIFY → IMPLEMENT → TEST → VERIFY → REGRESSION → LIFECYCLE TRACE → EVIDENCE → COMMIT → REMOTE VERIFY → REPORT
- **状态机**：DISCOVERED → RESEARCHED → DECIDED → SPECIFIED → IMPLEMENTED → LOADED → RUNNING → TESTED → VERIFIED → DELIVERED → MONITORED → IMPROVED
- **原则**：ONE AUTHORITY + CLEAR CONTRACTS + EXPLICIT OWNERSHIP + CANONICAL DATA + DETERMINISTIC RENDERING + LIFECYCLE TRACE + MACHINE VERIFICATION
- **禁止**：不得把代码存在当成完成；不得把 GitHub 已同步当成 Runtime 已执行；不得把 UI 显示出来当成 UI 正确。

### 验证证据（批次14）
- 智谱AI：/api/ai/status = enabled/zhipu/glm-4.5-air，/api/ai/test 正常回复
- Emoji清零：全仓JS仅7个emoji（全部✕关闭符）
- Lifecycle：8分类全切换正常，双向trace正常
- 导航：21项全部唯一，21个page-section全部存在
- zbHome：三语诠释正确渲染，标题中文正常
- HTML结构：header高度151px，4子元素正确分离
- 服务：healthz 200，v5.9.9
- 7个关键页面：无横向溢出，导航切换正常
