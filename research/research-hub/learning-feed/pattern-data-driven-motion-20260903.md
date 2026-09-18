# Engineering Pattern — 数据驱动实时动效（Data-Driven Motion / Table-Driven Binding）

- 日期：2026-09-03
- 类型：ZELL Learning / 可复用前端工程模式
- 来源实例：ZBC 序境-Core `static/js/zbip_motion.js` + `static/css/zbip-motion.css`（commit 758d0be，Evidence：ZBC `序境/08-AUDIT/UI_AUDIT_05_DATA_DRIVEN_MOTION.md`）
- 状态：PRODUCTION-VERIFIED（真实 8201、真实 stats、0 pageerror、纯函数单测 9/9）

## 1. 要解决的问题
- 纯 CSS 无限循环动效（扫光/漂浮/假流光）没有数据来源，是"为动而动"，且容易在无数据时空转、误导。
- 写死的展示数字/文案（如 65%、22 条）与真实数据漂移、互相矛盾，构成假数据残留。
- 散落在各渲染函数里的"取值 + 比对 + 动效"逻辑重复、易漏、难测。

## 2. 模式（Canonical 结构）
```
真实数据源（复用既有数据总线/轮询，禁止为动效另发请求、另建定时器）
  → 声明式绑定表 MotionTable（一行 = 一个数据→视图绑定，"表格转代码"）
  → 纯函数层（toNum / rate / trendOf / compact：归一化、占比、带死区趋势、格式化；无 DOM、可单测）
  → 渲染层（写真实值；仅当值越过死区真实变化才触发"一次性"动效；
           持续状态[在线/运行]按真实 status 挂载循环动效，状态消失即移除）
```

## 3. 关键规则（复用 checklist）
1. **首帧只填值、不动效**：没有"上一帧"就不叫变化，避免加载即闪。
2. **趋势带死区（deadzone）**：小于阈值的抖动判 flat，不反复闪光。
3. **无数据不动、不造假**：null/NaN/缺字段/除 0 → 保留占位，绝不补 0、不编文案。
4. **循环动效只表达持续真实状态**（在线、采集中）；一次性动效只表达真实变化（数值更新、按压、首挂载）。
5. **逐绑定 try/catch + 选择器缺失跳过**：单点失败不影响其它绑定与主流程。
6. **数字 tabular-nums**：更新时不左右抖动；一次性动效用强制 reflow 保证连续更新也能重触发。
7. **语义色与趋势色解耦**：指标本身的语义（正面绿/负面红）不用趋势方向覆盖，避免红绿语义打架；趋势用微光/箭头表达。
8. **prefers-reduced-motion 必须能一键关闭全部动效**。
9. 引擎单例、零新增定时器、对外暴露纯函数与绑定表供单测/审计。

## 4. 反模式（禁止）
- 无数据也一直转的装饰循环；写死的展示数字/环比/结论；用 AI 或假数据填充"看起来在动"的组件；
- 每个组件各自轮询、各自写 diff；趋势颜色覆盖指标语义色；从 scale(0) 入场；连续更新因未 reflow 不再触发。

## 5. 可复用场景（序境其它模块）
趋势图/采集卡/KOS 卡/报告指标/队列与健康状态/跨端（Web·Mobile Web·Mini Program 共用同一绑定表与纯函数，仅渲染器不同）。新增绑定只需在 MotionTable 加一行，不重写引擎。

## 6. 与前沿实践的关系（2026-09 主流一致方向）
- 与 "signal/reactivity + selectors"、"state-driven animation"（如 Framer Motion 的 animate 绑定值、Motion One、Svelte reactivity）同构：视图是状态的函数，动效是状态迁移的派生结果，而非命令式定时器。
- 差异：本模式刻意最小化、无框架依赖、原生可用，契合 Small Footprint / 服务器小型化约束。
