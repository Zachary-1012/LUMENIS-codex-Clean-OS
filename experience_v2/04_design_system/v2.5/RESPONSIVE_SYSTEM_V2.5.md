# LUMENIS Responsive System V2.5
Adaptive Layout，不是桌面缩放。字号/架构/组件随设备自适应；信息关系在断点间连续。

## 1. 八个断点（交付截图基线）
| Token | 宽 | 设备心智 | 布局 |
|---|---|---|---|
| xl-1920 | 1920 | 大屏工作站 | 三栏 + content-max 1560 居中，留白外扩 |
| l-1440 | 1440 | 标准桌面（主校准） | rail 252 / content / context 324 |
| ml-1280 | 1280 | 小桌面 | rail 收窄 clamp，context 保持 |
| t-1024 | 1024 | 横屏平板 | context 改为可开抽屉，主区双栏 |
| tp-768 | 768 | 竖屏平板（临界） | rail 折叠为图标 68，context 默认 closed |
| m-430 | 430 | 大屏手机 | 单列，顶部 context 入口，底部 dock |
| m-390 | 390 | 标准手机（必测，球体可见） | 单列，KPI 降阶，composer 堆叠，dock FAB 52 |
| m-360 | 360 | 小屏手机 | 进一步收紧 padding，触控不小于 44 |

断点实现于 `shell.css`（grid-area 切换）与 `tokens.css`（clamp 流体字号/间距/栏宽）。

## 2. 自适应规则（不是 hide，是 reflow）
- **Navigation**：rail（≥1024）→ 图标 rail（768）→ 抽屉 + 底部 dock（≤768）。导航始终「只要名字」，功能组可折叠。
- **Context panel（工作上下文/证据）**：≥1024 常驻右栏；768 收为抽屉；≤430 变为顶部「工作上下文」入口与随叫随到的证据抽屉（Studio 域：Evidence on demand）。
- **Density**：Operational(CTH) 在窄屏从多列降为双列再单列，但保留 Trace 顺序；Editorial(BMP) 窄屏转为开放竖排、放大留白节奏。
- **Table**：优先级 ① 砍到 2–3 关键列、点开展开 ② 包裹层横滚（-webkit-overflow-scrolling:touch）③ 重排为字段卡。禁止静默横向溢出。
- **Chart**：用 `aspect-ratio`，不写死高；多系列在窄屏保留主系列、其余进图例开关。
- **KPI/Metric**：大数字随 clamp 降阶（390 用 fs-3xl），单位保持小号 tabular；sparkline 保留趋势不保留精度。
- **AI Workspace**：composer 在手机堆叠（芯片换行、发送键右下），证据/工具过程收进可展开步骤，不占首屏；Lumen Core 作为 dock 中央 FAB，390 必须可见。
- **Modal/Drawer**：≤768 模态变底部抽屉（全宽、圆角仅顶部），避免小屏居中窄条。
- **Form**：字段在桌面并排、≤480 全宽堆叠；输入框不窄于 ~280 否则全宽。

## 3. 触控与安全区
- 可点目标 ≥44×44（图标按钮 hit-area 用 padding 扩，视觉可小）；dock 高 74（移动）。
- `env(safe-area-inset-*)` 预留刘海/Home 指示条；底部 dock 加 padding-bottom: env(safe-area-inset-bottom)。
- 一拇指热区：高频主操作放屏幕下 2/3；右上只放低频（搜索/主题/通知）。

## 4. 字号自适应
全部走 `clamp()`（见 TOKEN json typography）。body 在 360→1440 近似恒定（13.5–14.5），display 从 34 呼吸到 54；禁止用 vw 单独定 body 字号导致手机过小。

## 5. 验证矩阵（交付 04_VISUAL_BASELINES）
44 屏 × {1920,1440,1280,1024,768,430,390,360}，light/dark 关键屏双主题；每断点检查：无横向溢出、无重叠、触控达标、主焦点唯一、状态完整。捕获脚本 `webstack/batch_capture.mjs`。
