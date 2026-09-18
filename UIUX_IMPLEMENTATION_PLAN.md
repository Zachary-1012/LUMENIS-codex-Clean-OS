# ZBC UI/UX Implementation Plan

状态：待用户确认；本文件仅为计划，未执行 UI/UX 修改。

## P0：只修骨架一致性与状态真实性

1. 修正移动端 Overview 的死链引用，并补一条路由/导航回归测试。
2. 统一页面状态模型：`LOADING / SUCCESS / EMPTY / PARTIAL / STALE / ERROR / FORBIDDEN`，区分页面级与区块级状态。
3. 处理“数据显示正常但同时显示加载失败”的状态冲突，优先从 View Model/状态映射层收口，不改业务 API。
4. 去重 CTH 报告入口，明确 CTH/BMP 复用页面的只读/主责标识。
5. 为主要 Dashboard、Evidence、Risk、Event 页面建立真实 API 字段对照表。

## P1：Canonical Design System 与组件收口

1. 以 `zbip-tokens.css`、`zbip-components.css`、`zbip-motion.css`、`zbip-theme-override.css` 为唯一新增入口。
2. 兼容类名只保留有调用证据的映射，禁止继续增加第二套视觉 token。
3. 建立 Page Header、KPI、Filter Bar、Chart Card、Table、Evidence Panel、Status Banner、Empty/Error/Forbidden State 组件契约。
4. 统一 Current + Delta + Freshness + Confidence 的指标呈现。
5. 设计克制的刷新、下钻、hover、状态变化动效，并提供 reduced-motion 退化路径。

## P2：体验、响应式与性能深化

1. 按 1440、1024、390 三个视口做内置浏览器只读观感检查。
2. 优化图表、表格、侧栏和弹层的响应式分组，不以简单溢出隐藏代替信息架构。
3. 统计首次加载、JS 体积、重复请求、重复渲染、DOM 数量和核心网络错误。
4. 逐步收口报告/案例/浏览器/系统健康兼容实现，但每项先做依赖扫描和回归。

## 实施闸门

每个变更必须遵循：

`Audit → Design System → Component → Page → Regression`

并保持：

- 不改主体规则、采集规则、Evidence、权限边界和数据库历史数据。
- 不引入 mock/fake 数据。
- 不覆盖当前本地有效修复。
- 不直接复制通用 SaaS 模板。
- 不 push；每阶段保留 Git diff、测试证据和可回滚 checkpoint。

## 验收标准

- Backend/API/Database/Collector/Evidence/Tests 不回归。
- 内置浏览器主要页面可读、可下钻、状态语义一致。
- 核心页面数据来源可追溯到 API/View Model/Evidence。
- Console Error 为 0，核心 Network Error 为 0；已知降级必须显式标记。
