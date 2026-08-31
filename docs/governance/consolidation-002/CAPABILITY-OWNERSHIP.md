# CAPABILITY-OWNERSHIP · 唯一能力 Owner 裁定（Consolidation-002 / ④）

> 目标：解决"多套历史实现互相覆盖"。本文件**只裁定归属与打状态，不删除/不改写代码**。
> 状态：当前源码事实下的**初判 Owner**，需人工最终签字；任一非 Owner 实现退出前必须走完
> 「引用扫描→调用链→运行依赖→替代确认→回归测试→Evidence」，不能 100% 证明无用就保留。
> 状态枚举同 ASSET-REGISTRY；DUPLICATE=重复实现须指向唯一 Owner，LEGACY=旧版仍在跑待退。

## 0. 红线能力 Owner 锁（口径唯一，禁止改动）

| 能力 | 唯一 Owner（锁） | 其他实现 | 红线 |
|---|---|---|---|
| 主体识别/过滤 | `subject_rules.py`：SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS / `subject_hit()` / `_subject_sql_and_values()` | `collector_v2/pipeline/subject_filter.py` 仅新一代内部、不得另立口径；`subject_classifier.py` 只做主体类型分类 | 🔴 不得弱化/改口径 |
| 事件聚合 | `aggregate_events()`（主链） | event_graph 仅做关系图谱持久化，不改聚合口径 | 🔴 |
| 报告生成 | `daily_report.py` · `build_daily_report()` | 其余 report/export 实现不得另算统计口径 | 🔴 publish 时间口径 |
| 风险判定 | 根 `risk_engine.py` + 主链判定 | `collector_guard/risk_engine.py` 仅采集端局部风控，不得改写全局风险结论 | 🔴 |
| 时间口径 | publish_datetime=发布；captured_at/collected_at=采集 | 全链不得互替 | 🔴 |

## 1. AI 能力（正式 Ollama-only；规则引擎永远保底）

| 角色 | Owner / 成员 | 初判状态 |
|---|---|---|
| 智能编排/兜底 | `intelligence.py` | **ACTIVE（正式 Owner，无 AI 全链仍可跑）** |
| 内容分析执行器 | `ai_analyzer.py`（被 app/daily_report/report_engine 等 import，主链在用） | ACTIVE（intelligence 的分析执行，不重复造） |
| 过滤 | `ai_filter.py` | ACTIVE（职责=质量/主体过滤，非第二套大脑） |
| 云厂商网关 | `ark_llm.py`、`ai_gateway_v570.py`、`local_ai_client.py` | LEGACY/OPTIONAL，默认关闭，不删 |
| 学习引擎 | `ai_learning_engine.py` | EXPERIMENTAL（影子） |
| 自适应 | `adaptive_engine.py` | ACTIVE（调度策略，不属内容 AI） |

契约：业务层只经统一入口调用 analyze/summarize/classify；AI 不决定采集风控、不改主体/时间/统计/最终风险。后续 Provider 化工单统一收口，不在本轮改码。

## 2. 采集能力（生产事实来源唯一，新一代旁路）

| 代际 | Owner / 成员 | 初判状态 |
|---|---|---|
| 小红书生产事实来源 | `collector.py` + `xhs_cdp_collector.py` + `xhs_cookie_bridge.py` | **ACTIVE（唯一生产 Owner）** |
| 专题(15周年) | `topic_campaign.py`（复用主采集锁，独立配额） | ACTIVE（短期，窗口至 10-07） |
| 浏览器/拟人 | `cdp_helper.py`、`human_browser.py` | ACTIVE |
| 自动化编排 | `collector_automation.py`、`collector_auto_start.py` | ACTIVE（编排，不重写采集） |
| 全网搜索采集 | `web_monitor.py` / `web_monitor_v570.py` / `web_topic_discovery.py` / `monitor_pipeline.py` | Owner=`web_monitor.py`；v570=LEGACY 候选 |
| 新一代管线 | `collector_v2/*`（23） | DEVELOPING（**未接管前不得标 dup 删除**，验证+灰度后才议接管） |
| v4 平台适配器 | `v4_upgrade/adapters/*`（douyin/instagram/google/sogou…） | EXPERIMENTAL→逐个真出数后升 ACTIVE |
| 旧 JS 实现 | `rednote_collector.cjs`、`xhs_*.js` | LEGACY 候选（Playwright 替代回归后退） |

## 3. 报告/导出（12 路由多实现）

- **唯一统计 Owner**：`daily_report.py`（build_daily_report / aggregate_events 口径）。
- 渲染/导出执行：`report_engine.py`（根，薄）、`export_report.py`、`report_export/report_engine.py`、`report_export/app_report_api_patch.py`、`brand_report_generator.py`、`weekly_events.py`、`scripts/export_report.py`。
- 裁定：对外路由最终收敛到一套版本化 `/api/v1/report/*`；现有 `/api/report/*`、`/api/report/v2/*`、`/api/v2/report/export`、`/api/special-report/*`、`/api/reports*` 在前端未切换前全部 LEGACY 保留，**不删**；导出格式实现可多份（pdf/xlsx/docx），但统计数据只能来自 Owner。

## 4. 健康检查 / 守护恢复（区分"对外健康 API"与"内部自愈"，不是纯重复）

| 子能力 | Owner | 其余 |
|---|---|---|
| 存活探针 | `/healthz`（最轻，看门狗/隧道/compose 用） | 保留 |
| 对外系统健康 API | `system_health_api.py`（/api/system/health） | `/api/platform-health`、`/api/stability/*`、`/api/collect-health` 逐步收敛为其下分组，LEGACY 保留到前端切换 |
| 平台采集健康 | `platform_adapters/health_center.py`（六态，v4 采集健康用） | ACTIVE，职责不同不合并 |
| 内部自愈/守护 | `system_guardian.py` / `auto_recovery.py` / `stability_monitor.py` / `system_watchdog.py` / `safety_boundary.py` | ACTIVE（守护≠健康 API），收敛启动编排而非删 |
| Auth 恢复 | 后端 Owner=`auth_recovery_center.py`（+`auth_recovery_api.py` 对外） | `v4_upgrade/adapters/auth_recovery.py` 为适配层；前端唯一入口 `auth_global.js`（主 SPA 未挂=AUTH-01） |

## 5. 高危"运行代码"入口（安全优先，MIGRATION_REQUIRED）

`/api/developer/run`、`/api/dev/run-code`、`/api/config/run-code` 三套可执行代码入口：**只允许保留一个受控 Owner**（建议收口到 settings_module 的沙箱化执行 + 权限 + 审计），其余先在路由层标记 DISABLED/迁移，不直接物理删除；这是安全 P1，单列工单跟踪。

## 6. 负面 / 事件评审

- Owner：事件域统一评审流（events + event_graph）。
- `/api/negative/*` 与 `/api/negative-review/*`（及 `/api/event-review/*`）：保留现网在用的一套为 ACTIVE，另一套 LEGACY，前端统一切换后再退；禁止两套同时写库导致状态不一致。

## 7. 配置分层（不是重复，明确边界）

根 `config.py`=Core；`platform_adapters/config.py`=适配器层；`proxy_pool/config.py`=代理；`v4_upgrade/config.py`=增强层；`settings_module.py`=设置读写。**不合并**，但统一"运行时 override > env > 文件 > 默认"优先级契约，禁止互相覆盖。

## 8. Cookie / 登录

- 统一保险库 Owner：`v4_upgrade/adapters/cookie_vault.py`（解析/落盘/注入，cookie 不进源码/日志/库明文）。
- 平台桥接/导入：`xhs_cookie_bridge.py`（生产 ACTIVE）、`import_cookies.py`/`import_xhs_cookies.py`（一次性导入工具）、`scripts/sync_xhs_cookie_from_cdp.py`（9222 同步）。
- `weibo_login_manager.py`/`bilibili_login_manager.py`=未来平台 RESERVED。统一走 Auth 状态中心，不跳登录页。

## 9. 同名文件 / 依赖 / 浏览器

| 项 | 裁定 |
|---|---|
| 根 `report_engine.py` vs `report_export/report_engine.py` | 统计 Owner 在根；export 下仅做格式渲染，改名空间职责，不删 |
| 根 `check_system.py` vs `scripts/check_system.py` | 运维工具，保留 scripts 版，根版 NOT_VERIFIED 待回归 |
| 浏览器自动化 | Owner=Playwright（human_browser/cdp_helper）；**Selenium 全仓 0 真 import → DEPRECATED 候选**，Staging 回归后才从 requirements 退 |
| 0 引用依赖 | selenium / httpx / xlsxwriter / colorama / tqdm = UNUSED? 候选，**仅登记，本轮不卸不删** |

## 10. 退出（删除/合并）门槛 —— 每个 DUPLICATE/LEGACY 通用

引用扫描 → 调用链扫描 → 运行依赖分析 → 替代实现确认 → Staging 回归（L0-L10）→ Evidence → 独立 TASK/commit → 可回滚。任一环节不能证明安全即保留并改标 NOT_VERIFIED。核心红线簇不参与"为整洁而合并"。
