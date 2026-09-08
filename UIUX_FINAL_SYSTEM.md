# LUMENIS UI/UX Final System Baseline

状态：BASELINE，未执行大规模视觉重构。

## Token 层

Canonical 入口优先采用现有 `zbip-tokens.css`、`zbip-components.css`、`zbip-motion.css`、`zbip-theme-override.css`。颜色、字号、间距、圆角、阴影、边框、动效和状态不得在新页面另起一套 token。

## Page Contract

```text
Page Header
→ Context / Filter
→ KPI / Summary
→ Trend / Distribution
→ Event / Insight
→ Evidence
→ Action
```

每个页面必须能回答：现在发生什么、为什么发生、影响是什么、证据在哪里、下一步做什么。

## Component Contract

Canonical 组件候选：Metric Card、Insight Card、Evidence Card、Action Card、Runtime Card、Chart Card、Table Card、Status Banner、Empty/Error/Forbidden State。

## State Contract

统一页面和区块状态：`LOADING / SUCCESS / EMPTY / PARTIAL / STALE / ERROR / FORBIDDEN / OFFLINE`。状态必须来自真实 API/View Model，不得以空数组或静态占位伪装成功。

## Motion Contract

只允许克制的刷新反馈、趋势绘制、hover/focus/selection、页面切换和下钻过渡；必须支持 `prefers-reduced-motion`，不得阻塞数据读取或增加核心渲染负担。

## Responsive Contract

验收视口：1440、1024、390。移动端采用分组、抽屉、弹层和合理跳转，不以 `overflow: hidden` 掩盖不可见内容。

## Non-regression

不改变 Backend、Database、API Contract、Collector、Evidence、Runtime、权限和历史数据；不引入 mock/fake 数据。
