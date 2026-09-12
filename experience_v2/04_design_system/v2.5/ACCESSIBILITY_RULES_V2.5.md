# LUMENIS Accessibility Rules V2.5 (A11y)
可用性是质量底线，任何设计表盘设置下都不可交易。

## 1. 视觉与对比
- 正文文本对比 ≥ 4.5:1；大字（≥18.66px 粗 / 24px 常规）与 UI 图形边界 ≥ 3:1（双主题分别测，dark 不做简单反色）。
- Icy Cyan 在浅底仅用于细线/数据，不用作小号正文色；状态色配图标+文字。
- 不把 placeholder 当 label；输入始终有可见 label 或 aria-label。

## 2. 键盘与焦点
- 全操作可键盘到达：Tab 顺序符合视觉顺序；可见 focus ring（`--lum-ring` / icy，2px、offset 2px），禁止 outline:none 后不补替代。
- 自定义控件带正确 role/aria：tabs(tablist/tab/tabpanel + aria-selected)、segmented、switch(aria-checked)、accordion(aria-expanded)、nav(aria-current)。
- 浮层：焦点陷阱、Esc 关闭、关闭后焦点回到触发器；aria-modal。
- 图标按钮必须有 aria-label（mystery-meat 禁止）。

## 3. 触控与指针
- 触控目标 ≥44×44 CSS px（视觉可小，hit-area 用 padding 扩）；间距 ≥8。
- hover 才出现的次级操作必须键盘 focus / 触屏长按可达；不隐藏主导航。

## 4. 动效与感官
- 全局 `@media (prefers-reduced-motion: reduce)`：时长降 1ms、orb 出单帧、启动动画静态、Lenis 关闭。
- 不做 >3 次/秒闪烁；错误不只靠颜色/声音，提供文本。
- 触感（haptics）可在设置关闭，且 reduced-motion 时强制关（见 Haptics 规范）。

## 5. 语义与结构
- 语义化 HTML：header/nav/main/section/aside/footer；标题层级不跳级（一个 h1）。
- 表格用 th/scope；图表/Sparkline 提供 aria-label 或就近数据表（sr-only）。
- 图片/图标装饰用 aria-hidden，信息性图标有文本替代。
- 直播/处理中区域用 aria-live=polite（AI 步骤、toast），错误用 assertive 但不打断输入。

## 6. 响应式与缩放
- 支持到 200% 文本缩放不丢内容、不出现双向横滚；360 宽可用。
- 移动端安全区 env(safe-area-inset-*)；dock 不遮挡主内容（padding-bottom 预留）。

## 7. 检查方法（09_QA/a11y）
- 自动化：axe 规则扫描（label/contrast/aria/landmark）输出原始 JSON。
- 手工：纯键盘走查 AI-01 / CTH-01 / 一个表单 / 一个浮层；屏幕阅读器读序抽查；双主题对比抽测。
- 证据：每关键屏 a11y 扫描结果 + 键盘走查记录；UNKNOWN 项保留，不伪造通过。
