# ZBMP Page Map（Z-Brand Monitoring Platform · 页面地图）

> v1.0 2026-08-31。定位：**品牌智能分析工作台**（品牌资产·市场洞察·竞品·AI 分析）。布局型：Analysis Workspace（多面板工作区，区别于 CTH 的驾驶舱，但共用同一 Design System / 组件 / Token）。ZBMP 是 ZBP 内增强能力层，**不是第二套 Core**，与 CTH 共用数据库治理、API、Runtime、权限。Feature 状态以验证矩阵为准。

## 工作台框架
- 工作区层级（左侧树）：Workspace → Brand → Project → Campaign（WS-001 层级未建，IA 先占位、gray「规划中」，不影响现有页面）。
- 主区：可切换面板（概览 / 品牌资产 / 案例库 / 竞品与外部采集 / AI 分析 / 导入），顶部全局品牌/项目切换器（Segmented + 下拉）。
- 权限沿用 Guest/Member/Admin/Owner；跨品牌数据按品牌归属隔离。

## Z1 品牌智能概览 `/v4/brand/overview`
- 目标：当前品牌的资产健康、声量/情感/话题趋势、待办洞察。
- 数据：brand_knowledge、case_deep_analysis、聚合 notes/events。组件：Metric×≤6、Panel 网格、趋势图（语义描线）、AI 洞察列表（区分 AI 建议/系统事实）。
- 交互：切换品牌/项目；面板可重排（不改数据）；点洞察下钻。状态：数据更新时间 unknown/正常；空品牌走 EmptyState 引导新建。关联 BRAND-001/002、AI-001。

## Z2 品牌资产管理 `/v4/brand/library`
- 目标：品牌档案、主体词、知识库、太古/怡和专题。
- 组件：品牌 Table/卡片切换、品牌编辑 Drawer（档案字段/主体词/排除词，**主体词为红线，改动需二次确认并记录**）、专题 Tab。
- 交互：增删改（Admin）、查看关联内容；swire 专题空表走 EmptyState（BRAND-003 DEVELOPING，占位空态）。
- 状态：启用/归档 StatusDot。关联 BRAND-001/003。

## Z3 营销案例库 `/v4/brand/cases`
- 目标：案例沉淀、深度分析、可复用打法。
- 组件：案例卡片墙（克制、边框型）+ 案例详情 Drawer（背景/策略/内容/效果/标签/AI 提炼）+ 新建案例 Modal。
- 交互：检索/标签筛选/下钻；AI 一键提炼结构（AI 建议，可人工覆盖）。状态：草稿/已沉淀。关联 BRAND-002。

## Z4 竞品与多平台采集 `/v4/brand/collect`
- 目标：统一查看抖音/Instagram/Google/未来平台采集，平台 Adapter 化、Core 不感知平台内部。
- 组件：平台 Adapter ListRow（enabled 开关、健康点、最近结果/条数/状态）、采集结果表、适配器策略 Drawer。
- 交互：未验证平台开关 disabled 并说明「未接管生产」（抖音 COLL-001/IG COLL-002 DEVELOPING、Google COLL-003 EXPERIMENTAL、未来 FUT-001 RESERVED 全灰点占位）；不允许用 0 条掩盖失败。
- 状态：与统一采集八态一致，平台独立 Session/冷却互不连坐。关联 COLL-001..004、FUT-001、MON-003/005。

## Z5 AI 分析工作台 `/v4/brand/ai`
- 目标：内容理解、主体/内容分类、事件聚类、消费者需求、报告润色；AI 仅增强、不参与平台风控决策。
- 组件：AIChatDrawer 增强页、分析任务表、结果面板（模型/版本/置信度/人工覆盖 Human Override）、本地 Ollama 状态。
- 交互：对选中品牌/内容发起分析；结果可采纳/编辑/驳回；云端历史模型为 Legacy 默认关闭（不删除、不依赖）。
- 状态：AI 可用=info、降级=gray（业务链路照常）、分析失败=error 给原因。关联 AI-001，AI-002 Web Worker 占位。

## Z6 外部数据导入 `/v4/brand/import`（IMP-001 PLANNED 占位）
- 目标：PDF/Word/Excel 外部资料导入。现状：importer 3 个后端 py 存在，无前端/API/专表。
- IA：页面占位 EmptyState「规划中」，列出计划支持格式与流程；在 API/专表补齐前不开放上传，避免假完成。关联 IMP-001、GAP-21。

## Z7 工作区/项目/活动层级（WS-001 PLANNED 占位）
- 目标：Workspace/Brand/Project/Campaign 多级归属。IA 在侧栏树与切换器预留层级结构与禁用态，后端未建前灰点「规划中」，不为它重排现有导航。关联 WS-001。

## 差异化与一致性边界
- 与 CTH **视觉一致**（同 Token/组件/状态/动效），**架构略不同**：CTH=实时驾驶舱（首屏风险与状态优先），ZBMP=分析工作台（多面板、对象切换、知识沉淀优先）。
- 移动端：面板转纵向堆叠、品牌切换器置顶、分析抽屉全屏；六断点逐页 Evidence。
- 禁止：为 ZBMP 另起一套 CSS/组件/API/用户体系；禁止复制第二套数据库与 AI 栈。
