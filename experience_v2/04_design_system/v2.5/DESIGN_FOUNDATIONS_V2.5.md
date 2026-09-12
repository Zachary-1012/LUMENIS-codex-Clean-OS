# LUMENIS Design Foundations V2.5
基础层：Color · Material · Typography · Grid · Spacing · Radius · Hairline · Iconography · AI Orb · Motion · Accessibility · Responsive。
所有取值以 `DESIGN_TOKEN_SYSTEM_V2.5.json`（从 `assets/tokens.css` 提取）为唯一数值来源，本文只讲语义与用法。

---

## 1. Color — 金属单色，一个终点色
### 1.1 中性金属斜坡 slate（无色相 true silver）
`slate-0 #fff → slate-25 → 50 → 100 → 200 → 300 → 400 → 500 → 600 → 700 → 800 → 850 → 900 #14161b → 950 #0b0c0f`。
冷暖必须一致：禁止在同一面混用暖灰与冷灰。

### 1.2 双主题（精确反相，不是简单反色）
| 角色 | Light 黑银 | Dark 白银 |
|---|---|---|
| canvas 场 | `#EBECEE` 铂金雾 | `#060709` 近黑 |
| S1 实体面 | `#FBFBFC` | `#101115` |
| S0 分组洗 | `#F3F4F6` | `#15171c` |
| S2 抬升面 | `#FFFFFF` | `#1b1d23` |
| 凹陷井 | `#E7E9EC` | `#08090c` |
| 主文字 ink | `#14161B` | `#F2F3F5` |
| 次级/三级 | `#555a64 / #8a8f99` | `#AEB3BD / #7d838e` |
| 主操作 brand-500 | `#16181D` 近黑墨 | `#E9EBEF` 银白 |
| 反相文字 | `#ffffff` | `#0d0e11` |
| 发丝 line | `rgba(16,18,24,.10)` | `rgba(255,255,255,.085)` |

### 1.3 Icy Cyan — 唯一终点色
`icy-100 #E4F8FF … icy-500 #4FC4E8（light）/ #6FD6F2（dark）… icy-600`。
**只允许**：活数据点/线、processing/thinking/running 状态、focus ring、证据 Trace 选中路径、Lumen Core 处理态微混。
**禁止**：按钮底色、导航填充、大面积背景、品牌渐变文字。

### 1.4 语义色（双主题各一套，降饱和）
success / warning / danger / info / neutral + risk-low/med/high/crit。状态色同时配 `*-bg` 柔底；
不得只靠颜色传达状态（必须配图标/文字/形状，见 A11y）。

### 1.5 用色配额
单组件「有意色」≤3（中性不计）；一屏一个主强调；高饱和只留给主操作与关键状态。

## 2. Material — 表面阶梯与金属质感
- **深度 = 阶梯 + 发丝，不是阴影**。`sh-flat/sh-1 = none`；仅 menu/popover/drawer/modal/toast 用 `sh-2/sh-3/float`。
- **1px 顶部捕光** `--lum-edge-hi: inset 0 1px 0 rgba(255,255,255,.7)`（dark 降到 .07）制造金属表面，不用厚渐变。
- **黑铬渐变** brand-grad 只给主操作/核心实体，克制 168deg；**金属扫光** metal-sheen 只在 raised 面顶部 44%。
- **胶片颗粒** grain 用内联 SVG fractalNoise，opacity 极低（材质而非网格）；旧版重复网格背景已移除。
- 玻璃为 Tier B：仅 OPT-01..04 光学面；V2.5 默认冷静金属，WebGL 折射 GL 层在原型中关闭（类名契约保留给 Codex）。

## 3. Typography — 仪器无衬线 + 文学衬线
- 三套可变字体（已 vendor，woff2，拉丁 unicode-range，CJK 回退系统宋/黑）：
  Geist（sans/数字）、Geist Mono（ID/代码/证据号）、Fraunces（display 拉丁）；中文 display 走宋体栈（Songti/STSong/Noto Serif SC），正文走苹方/雅黑。
- **角色**：display/H1/H2 用衬线（文学、品牌、页面主标题）；body/dense/label/caption 用 sans；KPI 数字用 `--lum-font-num` + tabular-nums；证据号/ID/时间戳用 mono。
- **流體字号**：`fs-2xs … fs-5xl` 全部 `clamp()`，360 手机到 1440+；body 近似恒定，display 随宽度呼吸。
- 字重 400/500/600/680；display 字距 -0.028em，eyebrow 0.24em 大写间距；行高 tight1.12 / snug1.34 / normal1.58 / relaxed1.72。
- 度量：正文每行 45–75 字符；KPI 大数字 + 小单位（`1,284` 大、`%` 小）。
- 标题 `text-wrap:balance`、段落 `pretty`；禁止孤字（orphan）。

## 4. Grid · Spacing · Radius · Hairline
- 间距 4px 基准：sp-1…sp-16（4/8/12/16/20/24/32/40/48/64）；页面 padding、section gap 用 clamp 流体。
- 布局：rail `clamp(212px,15.6vw,252px)`、context 324px、topbar 62、dock 74、content-max 1560。
- 半径封顶：xs3 / sm6 / md10 / lg14 / xl18 / pill999；**内层半径 < 外层**（内=外-间距）。
- Hairline：`--lum-line` 发丝是第一分隔手段；Lumen Line 签名（墨→石墨，终点一丝 icy）只用于 page-head。
- 阴影/边框二选一；数据密集面用发丝，浮层才用阴影。

## 5. Iconography — 原创 lum-icon 族
- 24×24 网格、1.5 stroke、round cap/join、`currentColor`、无填充块、无第三方品牌外形。
- 运行时 `icons.js` 内联 SVG；交付另出 `icons-sprite.svg` + `icons-manifest.json`（见 05_components）。
- 去「小方块」：图标默认无盒底，仅在 action-item 等需要时给极淡洗底。

## 6. AI Orb — Lumen Core（原创，非素材）
- 零依赖原生 WebGL1 GLSL：全屏四边形 + Ashima simplex snoise + fbm 域扭曲，球内沿序轴混沌流转；
  左上定向光 diff/spec + fresnel 金属边；light 黑铬 / dark 白银精确反相；**无星星、无粒子贴图**。
- 状态机：idle(0) / processing·thinking·running(1，加速+微混 icy) / done·ok·complete(2) / error·fail(3)。
- 兼容性硬约束：WebGL1 禁用 `fwidth`（用固定像素 AA）；DPR≤2；ResizeObserver/IntersectionObserver；reduced-motion 出单帧；无 GL 时径向金属兜底。
- API 契约稳定：`window.LumOrb={mount,mountAll,setStatus,_instances}`，绑定 `canvas.lum-orb[data-status]`，由 Codex 驱动 setStatus。

## 7. Motion（详见 MOTION_SYSTEM_V2.5.md）
只动 opacity/transform；时长 token instant120/fast200/base320/slow480/morph520；
微交互 100–200、内容 200–300、布局 250–400；按压缩放 .97；标准/强调/退出/弹簧四条曲线；全局 reduced-motion 降到 1ms。

## 8. Accessibility（详见 ACCESSIBILITY_RULES_V2.5.md）
正文对比 ≥4.5:1、大字/UI ≥3:1；触控 ≥44px；可见 focus ring（icy/中性）；语义化 HTML；
状态不只靠颜色；`prefers-reduced-motion`；label 不得用 placeholder 代替；完整状态集（hover/focus/active/disabled/loading/empty/error）。

## 9. Responsive（详见 RESPONSIVE_SYSTEM_V2.5.md）
8 断点：1920 / 1440 / 1280 / 1024 / 768 / 430 / 390 / 360。Adaptive Layout（重排非缩放）：
桌面三栏 → 平板 context 折叠为抽屉 → 手机单列 + 底部 dock（中央 Lumen Core 球体 390 可见）。表格在窄屏降级为字段卡或横滚，绝不静默溢出。
