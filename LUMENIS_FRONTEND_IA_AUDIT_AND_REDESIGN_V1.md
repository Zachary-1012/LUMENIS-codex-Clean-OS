# LUMENIS 前端产品重构与信息架构审计 V1

状态：第 7 类“前端产品重构与真实页面 IA 审计”交付物  
审计基线：`78c469d81905568350338f9d01e2ce5baf3c6c67`  
设计约束：采用新的 LUMENIS 产品方案，不复制旧页面结构，不按普通 SaaS 后台重排。

## 1. 真实前端事实

当前清洁仓库直接读取结果：

| 资产 | 数量/事实 |
|---|---:|
| `lumenis_frontend.py` 蓝图路由 | 60 |
| HTML 模板 | 55 |
| 静态 JS | 28 |
| 静态 CSS | 10 |
| 页面域 | `/zbmp/*`、`/cth/*`、`/system/*` |
| 数据可视化 API | `/api/viz/*` |
| Domain API | `/api/domain/*` |
| 根入口 | `/` 重定向到 `/lumenis/`，再进入 CTH overview |

### 当前路由事实

CTH 页面实际包含 overview、realtime、topics、events、risk、brands、industries、xiaohongshu、kos、reports、evidence、trend、topic-campaign、weekly、weibo、workspace、data-center、qa、negative、official、event-graph、calendar、analysis、cases、case-analysis、knowledge、notes、launch 等多页面。

BMP 当前实际使用 `/zbmp/*` 路径，包含 overview、intelligence、brand、content、podcast、kos、competition、risk、reports、evaluation、launch。

SYSTEM 当前实际使用 runtime、collector、browser、ai、database、security、evaluation、adaptive-demo 等页面。

## 2. 当前前端问题

### 产品语义问题

1. 当前前端继续使用 `ZBMP`、`Z-Brand Monitoring Platform`、`Brand Intelligence` 等历史语义；目标方案要求正式名称为“序境·品牌市场”，BMP 仅保留为内部兼容标识。
2. CTH 导航仍混合品牌、业态、采集平台、KOS、报告、知识等入口，未按 Subject-first 的生产决策链组织。
3. SYSTEM、AI、Evidence、Evaluation 在页面层既像产品入口，又像系统能力，容易形成隐含第四产品线。
4. “解锁 ZBMP”采用产品密钥隐藏域的旧交互；目标方案要求产品归属清晰、权限控制与产品命名分离。

### 信息架构问题

1. 页面数量多于用户决策任务，顶级导航不能直接表达“我正在判断什么”。
2. 事件、主体、内容、风险、报告之间存在路由并列，但没有统一的双向回溯模型。
3. CTH 与 BMP 页面存在同名 risk、reports、kos 等能力，尚未通过统一 Capability Contract 保证消费者一致。
4. `feature-modules.js` 将 CaseAnalysis、PRCase、SwireGroup、TopicCampaign、AppEvidence、Architecture、SystemControls、ZBMPWorkbench 等功能以接线方式叠加，存在页面与能力归属漂移风险。
5. `domain-context.js` 当前使用 `zbmp / cth / system` 三域切换，并根据 URL 推断产品；它能改变 context、metrics、data、permissions、reports，但不能证明下游真实数据都随域切换。

### 数据真实性问题

1. `viz_api.py` 定义了 function registry → provider → View Model 的标准路径，但当前全量页面是否都使用该路径尚未证明。
2. CTH 真实页面与 API 当前均显示 0 数据，但第 6 类已确认服务读取 MAIN_AUDIT 数据库，不能把页面空态解释为工作区数据为空。
3. 模板中存在大量直接刷新、渲染和旧 API 调用，必须继续建立 Page → API → Data Source → Evidence 映射。

## 3. 新的产品信息架构

新的前端不以“功能菜单”作为主骨架，而以生产判断链作为主骨架：

`Context → Signal → Evidence → Event/Case → Risk → Decision → Action → Outcome`

### LUMENIS 工作台层

母产品层只负责：

- 当前 Domain 与 Subject/Brand Focus
- 需要关注的变化
- 待确认的证据
- 正在演化的事件与风险
- 待作出的决策
- 已执行行动及反馈

它不是第四产品，也不是传统总后台；它是跨 CTH/BMP 的生产上下文入口。

### CTH / 序境·商业运营

页面组织：

1. Subject Context：当前合法商业主体、业务范围、主体规则和数据新鲜度。
2. Operating Signals：主体下的变化、异常、热点、风险和证据缺口。
3. Event & Case：事件生命周期、案例、事件关系和主体回溯。
4. Risk & Decision：风险解释、规则依据、人工确认、决策记录。
5. Action & Report：行动建议、执行状态、反馈、日报/周报/专题报告。

CTH 不再以“品牌、业态、平台、报告”等平行菜单作为第一层；这些作为 Subject 下的分析维度和下钻路径。

### BMP / 序境·品牌市场

页面组织：

1. Brand Focus：当前主要品牌与竞品/市场范围。
2. Market Signals：传播变化、消费者需求、品牌对标与异常。
3. Campaign & Content：Campaign、内容资产、传播主体和内容创作。
4. Audience & Influence：KOS/KOL/KOC、媒体、官方和普通用户的六维画像。
5. Evaluation & Growth：传播效果、品牌影响、内容评估、学习资产和下一步行动。

内容创作不再归属于 BMP 页面专属能力，而从 Shared Capability 调用。

### Shared Capability

不作为顶级产品导航，按当前任务上下文被调用：

- Evidence View
- Content Creation
- Evaluation
- Learning Asset
- AI Enhancement

### SYSTEM

仅承载系统运行控制与可验证状态：

- Runtime
- Collector
- Browser / CDP
- Database
- AI Gateway
- Security / Permission
- Settings
- Evaluation / Audit

SYSTEM 页面不得呈现为业务产品，也不得以 AI 对话页代替生产任务状态。

## 4. 统一页面模板

所有生产页面采用以下结构，但每个领域的内容和决策动作必须不同：

`Context → KPI/State → Change/Trend → Analysis → Evidence → Decision → Action → Outcome`

每个模块至少要表达：

- 数据状态：真实数值、空、未知、失败、过期。
- 时间语义：`publish_datetime`、`captured_at`、freshness。
- 证据引用：Evidence ID、来源、原始 URL、置信度和验证状态。
- 业务动作：可执行动作、权限、审批、幂等和审计轨迹。
- 回溯关系：事件 ↔ 主体 ↔ 内容 ↔ 风险 ↔ 报告。

## 5. 个性化动态设计

动态只用于业务判断，不使用装饰性动画。

### CTH 动态

- Subject signal stream：显示主体相关性、数据新鲜度和变化量。
- Event lifecycle rail：发现→形成→增长→爆发→扩散→分化→衰减→结束。
- Risk transition：风险由规则、证据和人工确认驱动，不能由动画状态代替。
- Action feedback：行动后的新证据、风险变化和结果评估形成闭环。

### BMP 动态

- Brand propagation graph：传播主体、内容、事件和品牌影响的关系变化。
- Campaign pulse：Campaign 到传播事件、舆情事件的演化。
- Audience movement：KOS/KOL/KOC 与普通用户的参与、扩散和品牌关系变化。
- Content learning loop：内容产出→评估→修正→学习资产。

### 全局动态红线

- 不显示虚构的实时运行、完成、成功或增长。
- 没有 Evidence 的趋势只能显示为未知/不可确认。
- 数据库、API、View Model、页面状态必须同源。

## 6. 前端收敛验收规则

一个页面只有同时具备以下证据，才可标记为 `VERIFIED`：

`Page Route → Component → API Contract → Data Source → Evidence/Metric → Permission → Runtime → Browser Test`

旧页面不直接删除，按以下顺序处理：

`Inventory → Consumer Trace → Runtime Check → New Page Contract → Parallel Read → Regression → Archive/Delete Decision`

## 7. 七项验收

| 验收项 | 结果 | 依据 |
|---|---|---|
| Source | PASS | 路由、模板、JS/CSS、View Model、Viz API 已读取 |
| Call Graph | PARTIAL | 已确认路由和关键接线；全量 Page→API→DB 仍需逐页验证 |
| Data / API | PARTIAL | `/api/viz/*` 标准链存在，但页面全量接入未证明 |
| Frontend / Consumer | PASS（事实盘点） | 60 路由、55 模板、28 JS、10 CSS 已盘点 |
| Runtime | FAIL | 当前服务数据库与清洁审计基线不一致，页面数据源不能发布确认 |
| Tests | PARTIAL | 前端基础与 Viz 测试资产存在；浏览器全量回归受运行基线阻断 |
| Production Evidence | FAIL | 尚未形成每页可追溯、同数据库、同版本的生产证据 |

## 8. 本类结论

第 7 类前端产品重构与 IA 审计完成，状态：`DESIGN BASELINE READY / IMPLEMENTATION BLOCKED BY RUNTIME BASELINE`。

新设计的核心不是换颜色或重排卡片，而是把前端从“功能目录”重构为“围绕主体和证据做决定的生产界面”。在数据库与运行基线未统一前，不实施大规模页面切换，避免把旧数据源问题包装成新体验。

