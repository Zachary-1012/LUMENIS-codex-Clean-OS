# LUMENIS 动态化与决策反馈审计 V1

状态：第 8 类“动态化方案审计”交付物  
审计基线：`78c469d81905568350338f9d01e2ce5baf3c6c67`  
原则：动态只服务业务决策，不以动画制造“实时”“完成”“成功”假象。

## 1. 真实动态实现

当前源码已存在以下动态能力：

| 动态能力 | 当前实现 | 真实数据/状态依据 |
|---|---|---|
| 域切换 | `static/js/domain-context.js` | URL、Domain API、context/metrics/data/permissions/reports 重载逻辑 |
| 可视化刷新 | `viz_api.py`、`viz_data_provider.py` | DB Provider → `ui_view_model` → current/delta/freshness/confidence/evidence_refs |
| 趋势 | `trend_api.py`、`viz_data_provider.py`、`ui_view_model.py` | 按时间范围聚合，存在 `collected_at` 与快照路径 |
| 风险变化 | `risk_engine.py`、风险 API、View Model | 风险等级、规则和记录；全链路需绑定 Evidence |
| 事件演化 | `event_graph.py` | 营销/传播/舆情事件、关系、生命周期字段、confidence/evidence |
| Runtime 状态 | `runtime_guardian.py`、`runtime_preflight.py` | worker、checkpoint、lease、DLQ、状态转换 |
| 全局健康轮询 | `templates/base.html` | `/healthz`，30 秒轮询 |
| Auth 恢复轮询 | `templates/base.html` | `/api/auth-recovery/summary`，任务状态和暂停/恢复 |
| AI Evidence 面板 | `static/js/browser.js`、`ai-assistant.js`、SYSTEM AI 页面 | AI task、Evidence、Verification、Trace 展示 |

## 2. 当前动态链路事实

### 标准可视化链

代码路径明确声明：

`/api/viz/<function> → registry → viz_data_provider → ui_view_model → response`

`ui_view_model.py` 为指标定义了五个核心事实字段：

`current_value / delta / freshness / confidence / evidence_refs`

它还实现 `TruthTable`、缺失状态、时间边界、置信度和 Evidence 引用。这是新产品动态体系可以继承的基础，但必须确认实际页面全部使用该链，不能只看模块存在。

### 事件演化链

`event_graph.py` 支持：

- `marketing_event`
- `propagation_event`
- `public_opinion_event`
- `event_graph_relations`
- relation evidence 与 confidence
- 从既有 `events` 导入
- 自动关系重算时保留手工关系

但当前仍存在 `events` 与 `event_graph_events` 两类事件承载，不能直接宣称已形成唯一事件真相表。

### 行动反馈链

当前存在 Agent/Action、Review、Permission、Firewall、Evidence 和 Trace 模块；但本轮源码盘点没有证明每一类业务行动都具备：

`Decision → Permission → Action → Execution → Evidence → Outcome → Evaluation`

因此行动反馈只能标记为 `PARTIAL`，不能用 AI 对话完成或页面按钮存在来替代执行证据。

## 3. 动态化设计收敛

### LUMENIS 工作台

动态入口只呈现三类变化：

1. 当前 Subject/Brand Focus 的信号变化。
2. 证据支持的事件和风险变化。
3. 已批准行动产生的新结果和反馈。

### CTH 动态

`Subject → Signal → Evidence → Event/Case → Risk → Decision → Action → Outcome`

页面应优先显示主体相关性、事件阶段、风险变更原因、待确认项和行动结果，不显示与业务无关的装饰动效。

### BMP 动态

`Brand Focus → Market Signal → Campaign/Content → Audience/Influence → Evaluation → Learning Asset`

重点显示传播主体变化、Campaign 扩散、内容表现、消费者需求与品牌影响；所有结论必须能回溯到内容和 Evidence。

### SYSTEM 动态

只显示可验证运行状态：

- collector 状态
- worker heartbeat
- lease/checkpoint/DLQ
- Browser/Auth 状态
- AI provider 健康与调用记录
- database integrity / migration 状态

SYSTEM 不得用心跳动画代表业务完成。

## 4. 动态状态契约

任何动态模块必须同时返回：

```text
status
value
delta
changed_at
freshness
confidence
evidence_refs
source
error
next_action
```

状态语义：

- `OK`：有真实值且证据链可追溯。
- `NO_DATA`：查询成功但当前集合为空。
- `STALE`：有数据但超过 freshness 阈值。
- `UNKNOWN`：无法判断来源或置信度不足。
- `ERROR`：读取或计算失败，必须显示错误。
- `BLOCKED`：权限、Auth、风控或运行条件阻断。

禁止将 `NO_DATA`、`STALE`、`ERROR` 和 `BLOCKED` 渲染为 0、静止或绿色成功。

## 5. 动态风险

1. `domain-context.js` 的域切换机制存在，但前端切换不等于后端数据、权限和报告已经完成真实切换。
2. `viz_data_provider.py` 的部分趋势使用 `collected_at`；第 5 类已确认生产统计要求区分 `publish_datetime` 与 `captured_at`，动态趋势必须统一时间口径。
3. 事件图谱与既有 events 表并存，事件动态可能重复展示或重复计数。
4. 全局健康轮询只证明健康接口能返回，不证明采集、事件分析或报告已完成。
5. 动态页面如果只读取 DB 聚合而不携带 Evidence 引用，会出现“有变化、无依据”。
6. AI assistant 页面能够展示执行链路，但 UI 展示不等于 Action 已获批、执行或产生 Outcome。

## 6. 七项验收

| 验收项 | 结果 | 依据 |
|---|---|---|
| Source | PASS | domain-context、Viz、View Model、事件图、Runtime、模板动态逻辑已读取 |
| Call Graph | PARTIAL | Viz 链和事件链明确；动态页面全量接线未完成证明 |
| Data / API | PARTIAL | 动态契约字段存在，但数据源分裂和时间口径问题仍在 |
| Frontend / Consumer | PARTIAL | 动态组件和轮询存在；真实页面生产数据源受运行基线阻断 |
| Runtime | FAIL | 当前运行实例与清洁审计基线不一致，动态状态不可发布确认 |
| Tests | PASS / PARTIAL | Viz、View Model、Runtime 相关测试通过；缺少行动反馈全链路测试 |
| Production Evidence | FAIL | 尚未证明趋势、风险、事件和行动反馈全部由统一生产真相驱动 |

## 7. 本类结论

第 8 类动态化审计完成，状态：`DESIGN READY / PRODUCTION DYNAMIC BLOCKED`。

新的动态设计已经明确：动态不是“页面动起来”，而是让用户看到真实变化、变化依据、可信程度、下一步决策和行动结果。后续实现必须先锁定数据基线，再以契约驱动动态组件；不添加无意义动画，不用 AI 输出替代事实或行动结果。

