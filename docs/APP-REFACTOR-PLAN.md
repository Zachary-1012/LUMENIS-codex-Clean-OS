# app.py 拆分规划（P1-10）· 2026-09-03

## 施工进度
| 批次 | 蓝图 | 路由 | 状态 |
|---|---|---|---|
| 批1 | `data_query_api.py` | stats/notes/risk-alerts/hot-notes/comments/events/web-mentions/feedback-keywords/hot-topics（9 个纯只读） | ✅ 2026-09-03 完成，app.py 6013→5966 行，362 回归全过，x-route-count 405 不变 |
| 批2 | collection_api.py | 采集控制 | ⏳ 待施工 |
| 批3 | report_api.py | 报告 | ⏳ 待施工 |
| 批4 | ai_api.py | AI | ⏳ 待施工 |
| 批5 | ops_api.py | 系统/运维/代码执行（含权限敏感） | ⏳ 待施工 |
| 批6 | page_routes.py | 页面渲染 | ⏳ 待施工 |
| 批7 | workers/ | 后台线程 | ⏳ 待施工 |

> 现状：app.py 5966 行 / 224 路由。已拆分蓝图 8 个（原 7 + data_query）：
> system_health_api / architecture_api / settings_module / export_report / pr_case_integration /
> system_features_api / auth_recovery_api / data_query_api。
> 目标：把剩余单体按功能域拆分为 Flask Blueprint，消除巨石，保持路由与行为零变更。
> 原则：**只搬不移逻辑**，每个蓝图独立文件，注册点不变，拆分后全量回归必须通过。

## 一、当前 app.py 结构画像

| 维度 | 数值 |
|---|---|
| 总行数 | 6013 |
| 路由数 | 224（含 /api/ 220） |
| 顶层 import 模块 | 50 |
| 已拆蓝图 | 7 |
| 剩余单体 | ~4800 行（估） |

## 二、剩余可拆分域（按路由功能分组）

> 分组依据《04_FUNCTION_RECONCILIATION.md》路由域 + 源码核实。

| # | 功能域 | 典型路由 | 建议模块 | 优先级 |
|---|---|---|---|---|
| 1 | 数据查询 API | /api/notes /api/stats /api/events /api/search /api/hot-notes /api/risk-alerts | `blueprints/data_query_api.py` | P0（最稳定、低风险） |
| 2 | 采集控制 API | /api/collector/* /api/collect /api/rednote/collect /api/xhs/* | `blueprints/collection_api.py` | P0 |
| 3 | 报告 API | /api/report/* /api/digest/* /api/brand-report/* /api/special-report/* | `blueprints/report_api.py` | P0 |
| 4 | AI API | /api/ai/* /api/ark/* /api/ai-filter/* /api/ai-learning/* | `blueprints/ai_api.py` | P1 |
| 5 | 系统/运维/代码执行 | /api/config/run-code /api/dev/run-code /api/workspace/* /api/cache/* /api/stability/* | `blueprints/ops_api.py` | P1（含权限敏感，需谨慎） |
| 6 | 页面渲染 | 非 /api 的页面路由（templates） | `blueprints/page_routes.py` | P1 |
| 7 | 后台线程/worker | 采集调度、日报生成、自动保存 | 抽到独立 `workers/` 模块 | P2 |

## 三、拆分步骤（每步独立验证）

1. **建 `blueprints/` 目录 + 空 `__init__.py`**。
2. 每次拆 1 个域：把对应 `@app.route` 函数整体搬入新蓝图文件，
   蓝图内用 `from flask import Blueprint` + `bp = Blueprint('data_query', __name__)`，
   路由装饰器改为 `@bp.route`。
3. 函数内部依赖（db、collector、intelligence 等）保持 `import` 引用不变——函数体零改动。
4. app.py 中删除已搬函数，新增 `app.register_blueprint(data_query_api.bp)`。
5. **每步后跑全量回归**（`pytest tests -m "not online"`），必须 351+ 全过才能继续下一步。
6. 全部完成后跑 E2E（启动 app 冒烟 + 关键 API probe）。

## 四、风险控制

- **红线**：不触碰 SUBJECT_WORDS / subject_hit / DB Schema / 报告口径权威；
- 不合并路由、不改签名、不改返回结构——纯搬迁；
- 蓝图名与 operationId 相关：OpenAPI 从 url_map 反射，蓝图拆分后 operationId（endpoint 名）会变化，
  **需在拆分后重新生成 OpenAPI**（`openapi_spec.generate`），保持一致；
- 拆完立即验证 `/api/auth/config`（P0 前端 Auth）不受影响。

## 五、验收标准

- app.py 降到 ≤2500 行；
- 拆分后全量回归通过（不降测试数）；
- OpenAPI 重新生成，x-route-count 与拆分前一致（405）；
- E2E 冒烟：/healthz、/api/status、/api/auth/config、/api/notes 全通。

*归属：Z-Brand-Core docs | 状态：规划（未施工）| 关联：04_FUNCTION_RECONCILIATION、openapi_spec.py*
