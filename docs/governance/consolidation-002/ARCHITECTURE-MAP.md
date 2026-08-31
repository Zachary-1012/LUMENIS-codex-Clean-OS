# ARCHITECTURE-MAP · 架构分层映射（Consolidation-002 / ③）

> 只**映射**现状，不搬目录、不改代码。任何目录搬迁的前置条件：import / route / template / static / test / deployment 全部回归为绿。
> 数据源：`ASSET-REGISTRY.md`（②，400 py / app 可达 84 / app.py 189 路由 / 51 表）+ 运行时实测。命名暂用本地基线 **ZBP（品牌业务生产平台）**，命名冲突见 ASSET-REGISTRY §0。

## 0. 顶层定位（一套 Core，不拆第二套）

```
品牌业务生产平台 ZBP（仓库 Z-Brand-Core，单 Core / 单 DB / 单 Runtime / 单 Release Gate）
├── CTH-POMS  广州太古汇舆情监测系统 —— 当前生产主入口 / 客户交付（ACTIVE）
└── ZBMP      Z-Brand 品牌监测平台 —— Core 内母平台增强能力层（v4_upgrade，共用 Core，非独立服务）
```

硬约束：CTH-POMS 不依赖外部 ZBMP 服务；两者共用同一 Core、数据库治理、Runtime、安全边界、Release Gate；不复制第二套 DB/用户/配置/API/UI/AI。

## 1. 运行时分层（Runtime）

| 层 | ACTIVE 事实 | 状态 / 备注 |
|---|---|---|
| 进程看门狗 | `run_supervised.py`（POLL 2s / HEALTH 10s / 阈值3，探 /healthz） | ACTIVE，拉起 8201 |
| Web 装配 | `app.py`（4784 行，顶层装配约 40 本地模块 + 函数内 lazy import） | ACTIVE，唯一生产入口 |
| 统一对人入口 | `run.ps1`（prod/dev/staging/status） | ACTIVE，prod 转发既有 start_production.ps1 |
| 计划任务 | TaikooMonitor / ZBrand-HealthGuard / GitSync×3 | ACTIVE，运行期不改 |
| 隔离 Staging | 8301 + 独立副本库 + `--no-scheduler`（B 路径已实测） | ACTIVE（轻量）；Docker 路径产物就绪、build 未实测 |
| 浏览器 Runtime | CDP 9222（生产 Edge profile）/ 9223（代理 profile）；Playwright 主、Selenium 0 真 import | Playwright ACTIVE；Selenium DEPRECATED 候选（回归后才准退） |
| 配置 | `config.py`（运行时 override > env > system_config.json > 默认） | ACTIVE；多处 `config.py` 重复见④ |

## 2. Web / 接口层

| 层 | 事实 | 状态 |
|---|---|---|
| 生产前端 | `static/index.html`（SPA 单页，主入口 `/`） | ACTIVE |
| app.py 路由 | **189** 条（与盘点对齐） | ACTIVE |
| v4 子蓝图 | `v4_upgrade/*/templates`（console/collect/settings/version_center）+ 蓝图路由，全仓路由合计 363 | ACTIVE（ZBMP 增强层） |
| 旧服务端渲染 | `templates/`（base/events/index/notes/report 5 个 Jinja） | NOT_VERIFIED，待核实是否仍 render_template |
| 认证 | HTTP Basic（/、/api/*）+ v4 独立 Token 体系（v4_users/sessions/login_attempts） | ACTIVE，双轨待④收敛 |

## 3. 业务域层（Domain）—— 红线集中地

| 域 | ACTIVE Owner（现状事实） | 红线 / 备注 |
|---|---|---|
| 主体识别 | `subject_rules.py`（SUBJECT_WORDS/EXCLUDE、subject_hit）、`subject_classifier.py`（subject_type/content_type 枚举） | 🔴 主体口径唯一来源，不得弱化；双维度落库未贯通=DIM 工单 |
| 风险 | `risk_engine.py`（根，8 行薄封装）+ 实际判定逻辑 | 🔴 风险核心口径；与 collector_guard/risk_engine.py 重复，见④ |
| 事件 | `event_graph.py`（v5.9.9 已 DB 持久化，16 事件/1 关系） | 🔴 事件核心；三类事件+四关系未完成=EVT 工单 |
| 报告 | `daily_report.py` / `build_daily_report` 链 | 🔴 build_daily_report / aggregate_events 口径唯一；12 路由多实现见④ |
| 品牌知识 | `brand_knowledge_base.py` / `swire_group.py` / `case_deep_analysis.py` / `public_opinion_cases.py` | ACTIVE，多文件待④定 Owner |

## 4. 采集层（Collectors / Adapters）

| 代际 | 模块 | 状态 |
|---|---|---|
| 生产事实来源 | `collector.py`、`xhs_cdp_collector.py`、`xhs_cookie_bridge.py`（7层账号防护）、`topic_campaign.py`（15周年专题，窗口 08-28~10-07）、`cdp_helper.py`、`human_browser.py`（拟人层） | ACTIVE（小红书当前按用户指令暂停） |
| v4 平台适配器 | `v4_upgrade/adapters/`：cookie_vault、douyin（XHR拦截已出数）、instagram（DOM）、google（代理）、sogou、registry 11 适配器 | ACTIVE/EXPERIMENTAL 混合，逐个真实出数后才接生产 |
| 新一代采集 | `collector_v2/`（xhs/weibo/pipeline/scheduler/session，23 文件） | **DEVELOPING，app 不可达，未接管生产** |
| 平台抽象 | `platform_adapters/`（含 scheduling 动态调度、health_center） | 调度=影子模式（SCHED 工单未门控） |
| 代理 | `proxy_pool/`、`network_adaptive.py`、`browser_discovery.py`、`tunnel_guardian.py`（临时公网 cloudflare） | ACTIVE/EXPERIMENTAL；固定公网未固化 |

主链数据流（AI 仅旁路增强，不参与风控决策）：
`发现→获取→解析→标准化→质量检查→主体过滤(subject_hit)→去重→事件(event_graph)→风险→统计→报告`。

## 5. 服务层（Services）

| 服务 | ACTIVE | 重复 / Legacy（详见④） |
|---|---|---|
| AI | `intelligence.py`（规则引擎兜底，**Ollama-only 为正式**，无 AI 全链仍可跑） | ai_analyzer / ai_filter / ai_gateway_v570 / ai_learning_engine / ark_llm / local_ai_client 六套并存（云端 Legacy 默认关） |
| Auth 恢复 | `auth_recovery_center.py` + `auth_recovery_api.py` + `v4/adapters/auth_recovery.py` + `static/auth_global.js`（已挂 4 个 v4 子页，**主 SPA 未挂=AUTH 工单**） | 三套后端待④定唯一 Owner |
| 守护/恢复 | `system_guardian / auto_recovery / stability_monitor / system_watchdog / safety_boundary` | 17 文件簇，待④ |
| 版本/部署 | `v4_upgrade/version_center/git_manager.py`、`scripts/daily_git_sync.py`（一日3次） | 有 current_version 漏括号 bug（P0-FIX-1） |
| 导出 | `report_export/` | 与根报告模块重复，见④ |
| 通知 | `wechat_notifier.py` | ACTIVE，凭证未配 |

## 6. 数据层

- 唯一生产库 `data/monitor.db`（51 表，只读核查）；`database.py` 已支持 `ZBC_DB_PATH` 覆盖（Staging 隔离，默认路径不变，向后兼容）。
- 核心表：notes 957 / note_review_history 8327 / events 427 / collection_logs 477 / event_graph_events 16 / v4_* 认证五表。
- 空表（PLANNED/RESERVED）：app_evidence_records、review_tickets/samples/logs、notification_config、swire_notes。
- 非生产库勿混：根 `monitor.db`（仅 token_stat 空壳）、`staging/*` 副本、`data/cache/*`、`data/backups/*`、中文名库。
- 时间口径红线：publish_datetime=真实发布时间，captured_at/collected_at=采集时间，不得互替。

## 7. 横切：状态机 / 安全 / AI 边界

- 采集六态（SUCCESS/NO_NEW_DATA/RISK_WARNING/NEED_VERIFY/BLOCKED/SESSION_EXPIRED 等）平台独立隔离；300012/验证码/IP 风险只识别→停→熔断→冷却→人工合法验证→恢复，不破解、不伪装 0 条。
- AI 为增强层：可做理解/分类/聚类/报告润色；不得决定是否请求平台、不得改主体口径/真实时间/统计/最终风险。
- 安全：Cookie/token/.env/*.db/profile 绝不入库；运行代码高危入口 3 套（/api/developer/run 等）待④收敛。

## 8. 目标分层（仅方向，不在本轮搬迁）

```
core(config/database/security/runtime) · domain(subject/risk/events/reports) ·
collectors(platform/web/adapters) · services(monitoring/reporting/analysis/ai) ·
web(routes/templates/static) · jobs(scheduler) · tests
```
现状文件不移动；待④唯一 Owner 钉死、Staging 回归全绿后，才按"一次一层 + 全绿才搬"推进，且每个搬迁都是独立 TASK / commit / 可回滚。
