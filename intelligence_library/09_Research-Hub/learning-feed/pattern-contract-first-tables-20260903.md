# Engineering Pattern — 契约 Schema 优先的业务表格（Contract-First Canonical Tables）

- 日期：2026-09-03
- 类型：ZELL Learning / 双子库协作 + 前端工程模式
- 来源实例：DFS KOS 三表补齐（ZBC commit a70e8fc；契约 contracts/CTR-KOS-METRICS-P1-01.md；Evidence：Archived screenshot evidence removed; current capability claims require verification against current source and acceptance evidence）
- 状态：PRODUCTION-VERIFIED

## 1. 原则（用户纠偏固化）
研究侧（Intelligence）产出的契约数据 Schema 是业务表格的**唯一 Canonical**；Core 的后端按 Schema 提供接口，前端/展示层**只渲染契约字段，禁止自创业务字段、自定口径、前端硬算业务判定**。

```
Research 契约 Schema（字段/口径/分层规则，标注来源如 DFS Y26 H1）
  → Core 后端纯函数 + 路由（{ok,data}，缺值返回 null + manual_pending，不编 0）
  → 前端结构化表格（字段与 Schema 一一映射；null 显式「待回填/待接入」）
  → 数据驱动动效只负责"值变了怎么呈现"，不决定"值是什么"
```

## 2. 复用 checklist
1. 新增/改任何业务表前，先在契约/Capability Registry 查是否已有 Schema 与后端接口；有则只补渲染，不重写。
2. 前端字段名、分层阈值、计算公式必须与契约一致；判定类逻辑（如 KOC Gold/Silver/Bronze）调后端接口，不在 JS 里复制规则（避免双事实源漂移）。
3. 缺数据显式 pending（null/待回填/待接入），并展示 manual_pending/数据量说明；禁止用 0 或样例值冒充真实。
4. 无数据源支撑的聚合（如没有活动 KOC 明细的 campaign 复盘）不做假聚合，标注触发条件。
5. 多个面板复用同一接口响应（如健康画像复用 /tier），零新增请求；面板顺序在同步阶段固定占位，避免异步 append 乱序。
6. 表格优先结构化（table/Card/Timeline），细线、tabular-nums 数字对齐、分层用灰阶、语义色仅表状态。

## 3. 反模式（禁止）
- 在前端自创业务指标或写死口径/数字；同一判定规则前后端各写一份；缺数据补 0/样例；为"看起来完整"做无数据聚合；动效/装饰反向决定业务字段。

## 4. 与「数据驱动动效」模式的关系
两者分层：Contract-First Tables 决定**数据是什么、字段从哪来**（Canonical Schema）；Data-Driven Motion 决定**真实数据变化后怎么呈现**（纯函数+绑定表）。前者是数据 Truth，后者是表现层，表现层永远不得改写或杜撰 Truth。
