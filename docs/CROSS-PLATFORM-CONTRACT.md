# 跨端能力矩阵与统一 API Contract（P1-E）
> 基线《UNIFIED-ENGINEERING-BASELINE》§13 跨端原则：能力全、不减配；Renderer/信息密度/交互不同。

## 四端能力矩阵
| 能力 | Web（index.html） | App（规划） | Mobile Web（mobile.html） | Mini Program（规划） |
|---|---|---|---|---|
| 总览统计 | ✅ 完整分析 | ✅ 实时状态 | ✅ 核心指标 | ✅ 客户核心指标 |
| 舆情/风险分级 | ✅ 管理/审计 | ✅ 实时风险 | ✅ 风险卡 | ✅ 风险 |
| 事件/时间轴 | ✅ 全量+详情 | ✅ 实时事件 | ✅ 列表+展开 | ✅ 事件 |
| 报告（日/周/月/年/专报） | ✅ 完整 | 🟡 摘要 | 🟡 日报结论 | ✅ 客户报告 |
| 趋势动态可视化 | ✅ 完整 | ✅ 实时 | ✅ SVG 占比/时间轴 | ✅ 核心趋势 |
| Evidence/详情弹窗 | ✅ | 🟡 | ✅ 展开 | 🟡 |
| 采集/管理操作 | ✅ | 🟡 操作 | ❌ 只读 | ❌ 只读 |

原则：**只读轻量端（Mobile/Mini）不持有写操作**；差异化仅在 Renderer/信息密度/交互/导航。

## 统一只读 API Contract（各端共用，真实数据绑定）
| 端点 | 返回 | 用途 |
|---|---|---|
| `GET /api/stats` | `stats{total,positive,neutral,negative,high_risk,medium_risk,low_risk,official_count}` | 总览指标卡 |
| `GET /api/ai/status` | `{enabled,provider,model,runtime,base_url,fallback}` | AI 状态条 |
| `GET /api/event-graph/stats` | `data{total_events,total_relations,events_by_type,relations_by_type}` | 事件占比 |
| `GET /api/event-graph/events?limit=N` | `{count,events:[{event_id,event_type,event_type_name,event_time,created_at,description,source,relations}]}` | 事件时间轴 |
| `GET /api/report/daily` | `{date,report{conclusion,date_range,notes,stats},window}` | 日报结论 |
| `GET /api/metric-trend?entity_type=&entity_key=&limit=` | `{points,trend:[...]}` | 指标趋势折线 |

## 端适配（Renderer 差异）
- Web：完整表格/图表/管理表单
- Mobile Web：卡片式 + SVG 轻量可视化 + 纵向滚动
- App/Mini：原生/小程序组件，核心 KPI + 事件 + 风险

## 约束
- 禁止静态模板 + 假数据；任何端不得硬编码业务数字。
- 无数据时展示真实空态（"暂无数据"），不伪造。
- Mobile/Mini 只读：写操作仅在 Web/管理端。
