# ZBC UI/UX Skeleton Audit

审计日期：2026-09-08
范围：当前本地 HEAD `ff9c31a4b02ab2e7170c89a205cb069ce6ae9b77`，不覆盖本地未提交收敛工作。
远程参考：`origin/main`=`fda599abf5e35aecebe3ff37b0e66060e68c3017`。
本轮状态：只读审计；未修改 UI/UX、后端、数据库、API 或测试。

## PRODUCT SKELETON AUDIT

### 1. 产品与领域

- 母产品：序境 / LUMENIS。
- CTH：序境·商业运营，Subject-first；广州太古汇是 Subject Profile，不是第三产品。
- BMP/ZBMP：序境·品牌市场，Brand-first；ZBMP 是历史兼容标识。
- Shared Capability：内容与创作，跨 CTH/BMP 复用。
- SYSTEM：运行时、采集器、AI Gateway、数据库、安全、内部浏览器、设置。
- Agent Groups：跨产品执行层，不能成为第三产品。

### 2. 一级/二级模块

| 领域 | 一级模块 | 二级页面/能力 |
|---|---|---|
| CTH | 概览 | 运营概览、智能问答 |
| CTH | 主体/品牌 | 主体配置、品牌中心、品牌业态、业态管理 |
| CTH | 内容 | 笔记、官方动态、话题、话题活动、微博、小红书、知识库 |
| CTH | 事件/反馈 | 事件、事件关系、舆情日历、负面监测 |
| CTH | 风险/分析 | 风险预警、实时舆情、Evidence、舆情分析、趋势、案例 |
| CTH | 产出 | 报告、周报 |
| BMP | 概览/品牌 | 品牌市场概览、品牌中心 |
| BMP | 市场/传播 | 市场情报、内容、KOS/KOL/KOC、竞品 |
| BMP | 事件/风险 | 品牌事件复用 CTH 事件、品牌风险 |
| BMP | 产出 | 报告、播客 |
| SYSTEM | 运行时 | Runtime、Collector、AI Gateway、Database、Security、Browser、Settings |

### 3. 页面关系与用户路径

```text
域切换器
  → 模块导航
    → Overview / Page Header
      → KPI / Summary
        → 时间、品牌、主体筛选
          → 趋势/表格/图谱
            → 明细、Evidence、事件、报告或受控 Action
```

CTH 路由为 `/lumenis/cth/*`，BMP 路由为 `/lumenis/zbmp/*`，SYSTEM 路由为 `/lumenis/system/*`；页面层存在 `/system/settings` 兼容入口。

### 4. 数据流与 Evidence

```text
External Source
 → Source/Raw
 → Subject/Product/Scope Filter
 → Dedup/Quality
 → Canonical Data
 → Function/Metric
 → Truth Table/View Model
 → Visualization/UI/Report/Export/AI
```

业务情报链为：`Source → Evidence → Event → Case → Finding/Insight → Decision → Action → Outcome → Evaluation/Learning`。

主体过滤、发布时间口径、风险事实和 Evidence 是生产真值；AI 只能增强解释、分类、摘要与建议。

### 5. API 来源与 Runtime

- CTH 概览/分析主要来自 `/api/domain/*`、`/api/stats`、`/api/viz/*`、`/api/notes/*`、`/api/risk/*`。
- BMP 主要来自 `/api/domain/*`、`/api/brands/*`、`/api/brand-industry/*`、`/api/kos/*`、`/api/v2/global-bil/*`。
- SYSTEM 主要来自 `/api/system/*`、`/api/collector/*`、`/api/ai/*`、`/api/browser/*`、`/api/security/*`。
- Collector、Scheduler、Browser、AI、DB、Queue、Auth 均由 Runtime/Recovery/Evidence 链路约束。

### 6. Agent/AI 位置

AI Gateway/Provider、AI Analyzer/Filter/Learning、Skill、Agent Groups 位于共享执行与增强层；不拥有生产真值。当前 OSAI 通过适配边界接入，Agent 默认旁路/关闭策略仍是治理要求。

### 7. 双领域隔离

代码边界位于 `domain_isolation.py`、`domain_adapter.py`、`api_dual_domain.py`、`subject_context.py`；页面边界位于 `frontend/templates/cth`、`frontend/templates/zbmp`、`frontend/templates/system`；数据以 `domain_id/product_id` 与 Subject/Brand Profile 隔离。

### 8. 设置中心与 Dashboard 层级

设置中心目前由 `/system/settings` 兼容入口承载，SYSTEM 还包含 Runtime、Collector、AI、Database、Security、Browser 页面。Dashboard 采用：域级 Overview → 核心 KPI → 时间/品牌/主体过滤 → 趋势/分布/实时流 → 风险/洞察 → Evidence/报告/Action。

## SKELETON MATCH: PARTIAL

### 已符合最新骨架

1. LUMENIS/CTH/BMP/SYSTEM 四层语义已在 README、治理文档、导航与模板中形成主线。
2. CTH Subject-first 与 BMP Brand-first 已有路由、模板和数据边界。
3. 真实 API/View Model/数据库绑定已覆盖主要概览、风险、事件、报告和系统页。
4. `zbip-tokens.css`、`zbip-components.css`、`zbip-motion.css`、`zbip-theme-override.css` 已形成当前 Canonical Design System 基础。
5. 全量自动化基线通过：3954 passed、53 skipped、0 failed；无后台线程泄漏。

### 偏离骨架页面

1. CTH 报告存在“品牌报告”和“报告”重复入口。
2. 初始扫描曾报告 CTH 首页移动导航引用不存在的 `cth_overview` endpoint；本轮通过 `backend/lumenis_frontend.py` 与 `frontend/templates/base.html` 复核后，CTH 概览路由和移动入口均存在，原结论标记为已关闭。
3. ZBMP/CTH/SYSTEM 的 evaluation、launch、data-center、xiaohongshu 等页面存在路由但无导航入口。
4. CTH 的 Workspace 属于开发工具，却位于业务域系统分组。
5. KOS 同时出现在 CTH 与 BMP，产品归属需要明确只读/主责关系。

P0 已执行：BMP 重复的“传播声量”入口已从当前 `base.html` 导航移除；KOS/KOL/KOC canonical route 保留，生产 endpoint 未删除。

### 旧设计残留

- 旧根目录 `templates/`、`static/`、旧模块路径仍作为 Git 重组的删除/迁移证据存在，不能直接视为可删除资产。
- `ai-assistant.js` 已标记废弃但仍留有注释引用。
- 旧 `zbc-*`、`ld-*`、`lumenis-*` 兼容 token/类名与新 `zbip-*` 并存，后续需按依赖证据归类，不可盲删。
- 报告、案例、权限、浏览器、系统健康存在多套实现或兼容层。

### 缺失模块/层级

- 页面级 Evidence/Action 的统一入口和可回溯关系尚未完全一致。
- CTH/BMP 的错误、延迟、无权限、无数据状态语言仍未完全统一。
- 真实 API 字段、页面显示状态和网络失败状态尚未形成统一状态契约。

### 错误信息层级

既有模板包含“数据加载失败/无权限/部分延迟”等区块状态。由于当前业务页面受认证边界保护，本轮未在未授权状态下证明“真实数据与失败提示同时出现”；该项保留为待运行验证风险。应后续建立：页面级状态 → 区块级状态 → 字段级 freshness/error 的优先级，但本轮不修改。

### 应删除设计 / 应新增设计

- 应删除：重复导航入口、无证据的旧兼容样式、不可达页面的无主引用；必须经过依赖扫描与回归后执行。
- 应新增：统一状态语义、Evidence 回溯入口、页面级 freshness/confidence、明确的 CTH/BMP 只读复用标识。

## 测试与运行证据

- 自动化：3954 passed / 53 skipped / 0 failed。
- 健康接口：`/healthz` 返回 200。
- 目标回归：`tests/test_lumenis_frontend_foundation.py` 与 `tests/test_dual_domain_ui.py` 共 2 passed，无后台线程泄漏。
- 内置浏览器只读观察：CTH 概览、BMP 概览、SYSTEM 设置可打开；页面真实数据可见，但部分区块状态提示不一致。
- 数据库：测试使用外部副本；生产库未删除、未清空、未覆盖。

## 设计参考研究结论

本轮只提取方法，不复制视觉：

- Collect UI：按页面类型筛选真实后台/仪表盘案例，适合建立页面问题清单。
- The Component Gallery：对比真实设计系统中的导航、表格、筛选、状态、组件组合。
- Mobbin：研究已上线产品的完整设置、筛选、空态、错误和任务流，而非只看单张概念图。
- Dribbble/Behance/Awwwards：仅用于视觉趋势参考，不能覆盖产品骨架和生产数据语义。
- UI Movement/60FPS/CodePen：仅用于克制的微交互候选，不能引入影响性能的装饰动画。
- Material Design：用于可访问性、响应式、状态和组件行为的交叉校验，不作为 ZBC 产品风格替代。

## 当前结论

骨架已基本建立，当前主要风险不是缺少 UI，而是导航/状态/兼容层没有完全收口。按用户要求，本轮没有执行 UI/UX 修改；待确认后，下一步应按 P0 → Design System → Component → Page → Regression 小步推进。
