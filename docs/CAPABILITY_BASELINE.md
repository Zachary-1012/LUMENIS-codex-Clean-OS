# Z-Brand-Core 能力分级基线（Capability Baseline V1.0）

> 2026-08-30 依据 main HEAD 真实源码 / 数据库 / 运行实测归类，落实《全局代码级基线 V1.0》第三、十九节：
> **统一的是能力分类、Contract、事实源与生产入口，不是把源码物理合并成大文件；不删除仍有价值的历史实现。**
> 本文件只做归类与边界声明，不改变任何运行时代码。后续任何模块状态变更，必须先回归再改本表。

## 0. 分级定义

| 级别 | 含义 | 接管生产 |
|---|---|---|
| **Production** | 当前生产主链 / 唯一正式事实源，已实测 | 是 |
| **Compatibility** | 兼容转发 / 历史命名 / 旧入口，保证调用不断裂 | 间接（转发到 Production） |
| **Shadow** | 旁路并行、只记录不裁决，等待回归后灰度 | 否 |
| **Experimental** | 在建 / 默认关闭 / 需逐项验证后启用 | 否 |
| **Rollback** | 备份与回滚资产，只读保留 | 否 |
| **Deprecated** | 计划退役，当前不删、标注清楚 | 否 |

## 1. 启动 / 运行 / 部署

| 模块 | 级别 | 说明 |
|---|---|---|
| `run_production.py` | Production | 正式 WSGI 入口，Waitress `serve(app)`，并启动调度/内存/稳定性线程；Waitress 缺失才回退 Flask dev |
| `run_supervised.py` + `scripts/start_production.ps1` | Production | 8201 幂等守护启动（互斥锁+进程守卫+healthz），并按需拉起 9222 真人 Edge；不触碰 8200 |
| `app.py` | Production | 单体 Flask 应用（13 蓝图 / 303 路由），现网与 v4 统一承载 |

## 2. 采集体系（四代并存，不替换、不新增第三套 Registry）

| 模块 | 级别 | 说明 |
|---|---|---|
| `collector.py` | Production（Legacy 主采集） | 小红书生产事实来源；含 `classify_collect_state` 六态归一 |
| `xhs_cookie_bridge.py` | Production | 任务编排、Cookie 桥接、熔断状态机、动态调度结果回写、影子决策落库 |
| `collector_guard/` | Production | 采集守卫 / Browser Lock / 熔断冷却（真人平台全局串行） |
| `collector_v2/`（24 文件） | Shadow | 下一代管线，`subject_filter` 仅预过滤效率层，**不做最终主体裁决**；未回归不接管 |
| `platform_adapters/` | Production+Shadow 混合 | 统一 Platform Adapter 契约：health_center / scheduling / risk_controller / auth_recovery 为 Production 支撑；`xhs` 边界封装为 Production；`douyin` 等其余 `enabled=False` 为 Shadow/Experimental |
| `v4_upgrade/adapters/` | Shadow/Experimental | sogou/google 已真出数、douyin XHR 主链已真出 10 条、instagram/DOM 已写待回归；均为旁路资产，不替换 `collector.py` |
| `web_monitor.py` / `web_monitor_v570.py` | Compatibility | 全网网页发现辅助源，失败不阻塞小红书主链 |

> 两套 Registry（`platform_adapters.registry` 函数式、`v4_upgrade.adapters.registry` 类式）**均保留**，当前不合并、不新增第三套；后续在 Contract 层对齐调用边界。

## 3. 主体 / 风险 / 事件 / 报告（P0 红线区）

| 模块 | 级别 | 说明 |
|---|---|---|
| `subject_rules.py` | **Production（唯一正式主体裁决）** | `SUBJECT_WORDS/SUBJECT_EXCLUDE_WORDS/subject_hit/_subject_sql_and_values` 唯一事实源 |
| `risk_engine.py` | Compatibility | 仅转发到 `subject_rules` 与 `daily_report`，保留历史命名 |
| `app.py::_subject_sql_and_values / subject_hit_note_safe` | Compatibility | 转调 subject_rules；旧 rednote 路径的 `verify_taikoo_location` 内部首行仍调规则 `subject_hit`，**非 AI 裁决主体** |
| `daily_report.py` / `report_engine.py` | Production | 日报/报告，周期按 `publish_datetime`，主体过滤不绕过 |
| `reprocess.py` / `review_workflow.py` | Production | 再处理、事件构建、复核流 |
| `weekly_events.py` / `topic_campaign.py` | Production | 周报与 15 周年话题监测（独立配额错峰） |

## 4. 数据 / 持久化 / 迁移

| 模块 | 级别 | 说明 |
|---|---|---|
| `database.py` / `models.py` | Production | SQLite 访问与模型；45 表，禁 DROP/清空/重建 |
| `database_migrations.py` | Production | 版本化迁移（MIGRATIONS + MIGRATION_HISTORY + 迁移前自动备份，向后兼容） |
| `data/monitor.db` | Production | 唯一生产库；每次改动前复制到 `data/backups/` |
| `backups/`、`data/backups/` | Rollback | 历史快照与回滚资产，只读保留 |

## 5. AI（Local-first / Ollama-only，AI 永远是增强层）

| 模块 | 级别 | 说明 |
|---|---|---|
| `local_ai_client.py` | Production | 正式本地 Ollama 客户端 |
| `ai_analyzer.py` | Production（规则为主） | 分类/主体校验，主体判定走规则；AI 仅增强 |
| `ai_filter.py` / `function_registry.py` | Production | AI 过滤与 Function Registry（取真实系统数据，不编造） |
| `ai_learning_engine.py` | Experimental | 运行经验/审计/反馈样本体系（非自动训练权重） |
| `ai_gateway_v570.py` / `ark_llm.py` / `intelligence.py` | **Legacy/Optional（默认关闭）** | 历史云端 AI 入口，保留并标注，生产不依赖；无 AI 时主链照常运行 |

## 6. Recovery / Safety / Network

| 模块 | 级别 | 说明 |
|---|---|---|
| `safety_boundary.py` | Production | 最终安全闸门（Adaptive 提动作、Boundary 裁决） |
| `platform_adapters/auth_recovery.py` + 全局 `auth_global.js` | Production | 统一 Auth Recovery（A 登录/B 验证/C 风控三类分清，不跳页） |
| `network_adaptive.py` | Production | 网络异常退避/可解释，不伪装 0 条 |
| ProxyPool（可插拔补丁） | Experimental | `enabled=False mode=direct`，付费海外节点接入后再启用 |
| `auto_recovery.py` / `system_guardian.py` / `data_feedback_loop.py` | Experimental | 需逐项验证后再启用（以运行实测为准） |
| `stability_monitor.py` / `memory_optimizer.py` | Production | 进程守护/心跳/OOM 防护（生产启动时拉起） |

## 7. 认证 / 前端 / API

| 模块 | 级别 | 说明 |
|---|---|---|
| `v4_upgrade/auth/` | Production | token/密钥登录、三级权限、安全问答、审计；Bearer 或同名 session cookie |
| `app.py::_basic_auth` | Production+统一 | HTTP Basic 兜底保留；V1.0 起同时认可 v4 有效会话（未登录仍 401，安全不降） |
| 15 SPA + 话题独立页 / v4 四主页面 | Production | 桌面+移动适配；全局健康小点与 Auth Modal 已在 collect/console/settings/version-center 注入 |
| `system_watchdog.py` | Compatibility（已整改） | 进程看门狗；硬编码凭证已移除，改读 `TAIKOO_AUTH_*` 环境变量 |

## 8. DCC（研发治理平面）

| 模块 | 级别 | 说明 |
|---|---|---|
| DCC（Development-Command-Console） | **Experimental（尚未建设）** | 规划 READ/TASK/AUDIT ALLOW、TEST CONTROLLED、WRITE/DEPLOY DENY；当前无代码，不成为生产运行时依赖 |

## 9. 收口原则（对应基线第三、十九节）

1. 一个能力只保留**一个正式事实源**（主体=subject_rules；生产采集=collector.py；生产库=monitor.db）。
2. 多代实现先统一 Contract 与调用边界，确认完整调用链+测试+回滚后才做最小合并，不物理大合并。
3. 新 Collector / Adapter / AI 默认 Shadow，真实回归通过并经批准才灰度进生产。
4. 本表随每次发布更新；级别下调（Production→Deprecated）必须有替代回归证据与回滚路径。
