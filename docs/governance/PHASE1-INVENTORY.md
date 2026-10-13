# Z-Brand Core · Phase 1 统一盘点总册（INVENTORY）

> 治理基线文档，遵循《Unified Production Architecture v1.0》Phase A「先盘点，不修改」。
> 本文只记录**实测事实**与处置判断，不在此阶段改业务代码。

| 项 | 值 |
|---|---|
| 盘点时间 | 2026-08-31（UTC+8） |
| 代码基线 | 盘点起于 `8f4aab4`；G-CLEAN-B 后 `5347f1e` |
| 运行版本 | v5.9.9（VERSION/app.py 实测；文档存在版本漂移，见 §9） |
| 方法 | 全只读：git ls-files / 文件系统统计 / 正则引用扫描 / SQLite `mode=ro` |
| 范围 | 聚焦 **ZBC**；SICI、DCC（tools/development-command-console）按用户要求**不动** |
| 红线 | 不弱化主体口径、不混 publish_datetime/captured_at、不删库、AI 仅增强层 |

---

## 1. 三仓库定位（本次只治理 ZBC）

| 仓库 | 定位 | 本地状态 | 本次动作 |
|---|---|---|---|
| ZBC | Production 生产/交付 | `D:\Taikoo-monitor-new`，remote=Zachary-1012/Z-Brand-Core | **治理对象** |
| DCC | Governance 审计/门禁 | `tools/development-command-console`（嵌套独立 git，Node，41 文件，未用 .gitmodules 注册，主仓库 .gitignore 已忽略 tools/） | 不动 |
| SICI | Research 研究/候选 | 本地缺失 | 不动（用户暂不提供） |

---

## 2. 规模总览（实测）

| 维度 | 数字 | 说明 |
|---|---|---|
| 本地 .py | 664 个 / 126,851 行 | 含 IDE 副本、运行时、临时脚本 |
| Git 跟踪 | 677 文件 / 265 .py | 以 git ls-files 为准 |
| 业务代码主体 | 根 95 py(29,735 行)+v4_upgrade 48+collector_v2 24+platform_adapters 14+scripts 18 | 真正运行面 |
| 路由 | app.py 189 + 蓝图约 105 ≈ **294** | 旧文档写 162，已漂移 |
| 数据库表 | **51** | 见 §6 |
| 前端 | **21 CSS + 21 JS** | 见 §7 |
| 启动入口 | **34**（20 .bat/3 .ps1/3 .vbs/2 run_*.py/中文命名若干） | 待收敛为 1，见 CLEANUP-D |

### 非业务膨胀（均未被 Git 跟踪，不进仓库）
| 目录 | .py/规模 | 实质 | 判断 |
|---|---|---|---|
| `.trae-cn/` | 253 py/67,608 行 | TRAE IDE 工作区数据（含 trae-jwt-token） | 保留原地，.gitignore 已忽略；**不移除**（避免破坏 IDE 状态） |
| `nodejs/` | 58 py/32,956 行 | 便携 Node 运行时，py 全是 npm 自带 node-gyp | 保留原地，已忽略；Python 系统不依赖 |
| `backups/`、`D:\Taikoo-monitor-new-backups` | — | 历史备份 | 保留，已忽略 |
| 根 `app.py.bak-before-v4-*.py` 等 *.bak | — | 升级前本地备份 | 本地保留观察，*.bak 已忽略 |

---

## 3. ARCHITECTURE-MAP（现状 → 目标分层映射，仅映射不搬迁）

| 目标层 | 现状对应（不重写，逐步归位） |
|---|---|
| core/ | config.py、database.py、database_migrations.py、logger.py、models.py、settings_module.py、security_scanner.py、safety_boundary.py |
| domain/ | subject_rules.py、subject_classifier.py、risk_engine.py、event_graph.py、weekly_events.py、report_engine.py、daily_report.py、intelligence.py |
| collectors/ | collector.py（生产）、xhs_cdp_collector.py、collector_v2/、platform_adapters/、v4_upgrade/adapters/、web_monitor*.py、cdp_helper.py、human_browser.py、proxy_pool/、collector_guard/ |
| services/ | monitoring.py、monitor_pipeline.py、stability_monitor.py、system_guardian.py、auto_recovery.py、data_feedback_loop.py、memory_optimizer.py、ai_*.py、auth_recovery_*.py |
| web/ | app.py + 各 *_api.py / 蓝图模块、templates/、static/ |
| jobs/ | collector_automation.py、collector_auto_start.py、topic_campaign.py、scripts/ |
| tests/ | tests/（正式 113）、tests/_archive/（一次性诊断归档） |
| docs/ | docs/、docs/governance/（本目录）、docs/reference/（设计参考） |

> 结论：**不做大搬家**。后续新增模块按目标层落位，旧模块在被替换并回归通过后才归位/标 Legacy，符合「引用分析→依赖分析→替代验证→回归→Evidence」。

---

## 4. MODULE-MATRIX · 重复实现族（DUPLICATE，登记待收口，本轮不碰）

| 族 | 并存实现 | 生产事实来源 | 收口方向 |
|---|---|---|---|
| 采集 | collector.py ‖ xhs_cdp_collector.py ‖ collector_v2/ ‖ platform_adapters ‖ v4_upgrade/adapters | **collector.py** | platform_adapters 为统一方向；v2/v4 旁路 Shadow，未验证不切 |
| AI | intelligence.py(规则兜底·正式) ‖ ai_analyzer/ai_gateway_v570/ai_filter/ai_learning_engine/ark_llm/local_ai_client ‖ v4 ai_hub | intelligence.py | 统一 AIProvider；云端 Legacy 默认关闭；Ollama 为正式方向（当前未运行） |
| 监控/Web | monitoring/monitor_pipeline/web_monitor/web_monitor_v570/web_topic_discovery 等 8 个 | monitoring 主链 | 逐模块引用分析后收敛 |
| Auth 恢复 | auth_recovery_center+auth_recovery_api ‖ v4/adapters/auth_recovery | 两套并存 | 统一 Contract（接业务工单 ZBC-AUTH-01） |
| 启动 | 34 个入口 | run_supervised/run_production | 收敛为唯一 run.ps1（G-LAUNCH） |

**死代码候选（引用扫描=0）**：`app_refactor_blueprint.py`（定义 16 路由，全项目 0 import/0 注册）→ 标 DEPRECATED，观察一版+回归后再删，不在本轮直接删。

---

## 5. ROUTE-MATRIX（路由分布，实测）

| 文件 | 路由数 |
|---|---|
| app.py | 189 |
| architecture_api.py | 22 |
| system_features_api.py | 16 |
| topic_campaign.py | 16 |
| app_refactor_blueprint.py（**未注册=死代码**） | 16 |
| app_evidence.py / swire_group.py / settings_module.py | 各 8 |
| export_report.py / auth_recovery_api.py | 7 |
| collector_v2_integration.py / system_health_api.py | 3 |

> API 统一 `/api/v1/` 契约、统一错误/分页/鉴权列为后续 G-API 工单，当前不批量改旧接口。

---

## 6. DATABASE-MATRIX（51 表，只读核查关键项）

- 总量：notes 957（空 content **253**，待补抓）、events 427、topic_campaign_notes 120、swire_notes 0、v4_users 1（仅 owner）。
- 时间双字段 `publish_datetime`/`captured_at` 齐备；脏相对时间已清零（0）。
- **缺口（业务工单，不在治理阶段做）**：
  - `subject_type`（KOS/KOL/KOC…）全库无任何表承载 → ZBC-DIM-01；
  - 主 events 表无 `event_type`，三类事件仅 event_graph_events(16)/relations(1) 初建 → ZBC-EVT-01；
  - 无 import 专用表（外部导入链路未通）。
- 保护红线：不删表/不清数据/向后兼容迁移；任何结构变更先备份。

---

## 7. UI-MATRIX（21 CSS + 21 JS）

- 权威：`static/css/zb-theme.css` 为最终主题覆盖层（侘寂黑白灰 + GPT 式彩色小圆点）。
- 现状：head 仍层叠加载旧换皮 CSS（design-v8/v9、tokens(-minimal)、layout(-minimal)、ui_modern/dashboard 等）。
- 策略：**引用扫描→标记→回归→摘除**，禁止再加 fix-final-new-v2 类层；本轮不摘（避免影响在跑页面），列 G-UI 工单。
- 已具备：手机底部 Tab、⌘命令面板；待做：右 Inspector「点对象不跳页」。

---

## 8. DEPENDENCY-MATRIX（requirements.txt 实测引用面）

| 包 | import 文件数 | 分类 | 处置 |
|---|---|---|---|
| Flask | 30 | CORE | 保留（不换框架） |
| playwright | 33 | CORE/BROWSER | 保留，升为唯一浏览器栈 |
| requests | 11 | CORE | 保留 |
| psutil | 6 | CORE | 保留（内存/稳定性/CDP） |
| python-dotenv | 1 | CORE | 保留 |
| Werkzeug | 0 直接 | CORE(transitive) | Flask 传递依赖，保留 |
| openpyxl | 2 | 功能(Excel) | 保留 |
| python-docx | 1 | 功能(Word 导入/导出) | 保留 |
| reportlab | 3 | 功能(PDF) | 保留 |
| pandas | 1 | 功能(importer/parser) | 保留（仅导入解析用） |
| **selenium** | **0** | LEGACY/UNUSED | **REMOVE 候选**：全项目无真实 import（human_browser 命中的是 JS 反检测字符串），Staging 验证后从 requirements 移除 |
| **httpx** | **0** | UNUSED | REMOVE 候选，Staging 验证 |
| **xlsxwriter** | **0** | DUPLICATE（openpyxl 已覆盖 Excel） | REMOVE 候选 |
| **colorama** | **0** | UNUSED | REMOVE 候选 |
| **tqdm** | **0** | UNUSED | REMOVE 候选 |

> 根 package.json 版本漂移 5.6.2，其 scripts 指向的 xhs_search.js/xhs_login.js/inject_cookies.js 已不存在 → 列 G-LAUNCH/G-DEP 修正或移除（DCC 有自己的 package.json，互不影响）。

### 技术栈决策（ADR，对照 UPA §5/§6）
- **保留**：Flask、SQLite、原生 JS + 统一 CSS 层（不换 FastAPI/Django/React/Vue）。
- **退出**：Selenium（0 使用）→ Browser 统一 Playwright Adapter。
- **待定**：Docker/Compose（本机当前未安装 Docker）用于 Staging 隔离；未安装前以「独立端口+独立 venv+独立 DB+XHS_PRODUCTION=false」做轻量 Staging。
- **AI**：Provider 化，业务只调 analyze/summarize/classify；当前正式 Runtime=序境自有模型（未训练前 AI 结果为 UNAVAILABLE，不调用第三方、不兜底）。

---

## 9. CLEANUP-MATRIX 台账

| 编号 | 类别 | 对象 | 处置 | 状态 |
|---|---|---|---|---|
| G-CLEAN-A | 本地未跟踪 | .trae-cn / nodejs / backups | 保留原地 + .gitignore 已覆盖，不移除（保护 IDE/Node/备份） | ✅ 判定保留 |
| G-CLEAN-B | Git 跟踪垃圾 | video_frames 97、tests 一次性产物 33、apple-ui-reference 13 | 97 移出版本库（历史可恢复）、33 归档 tests/_archive、13 归位 docs/reference，补 .gitignore | ✅ 完成 `5347f1e` |
| G-CLEAN-C | 治理文档 | 本盘点总册 + 矩阵 | 新增 docs/governance，不改业务源码 | ⏳ 本提交 |
| G-CLEAN-D | 启动入口 | 34 个 → 唯一 run.ps1 | 旧入口标 DEPRECATED 不删 | ⏳ G-LAUNCH |
| 后续 | 死代码/冗余依赖 | app_refactor_blueprint、selenium 等 5 包、deployment 乱码文件名、根 package.json | 引用分析+Staging 回归后处理，不直接删 | 待 G-DEP |

### 敏感泄露审计（安全）
- git ls-files 全量扫描：**无 .env / *.db / 明文 cookie json / 浏览器 profile / 密钥** 被跟踪。
- 命中 cookie/token 字样的均为「处理 cookie 的代码」或 .env.example 模板、tokens.css 设计变量，非凭证。
- data/cookies/、data/private/、edge-cdp-*/、chrome-cdp-*/ 均已被 .gitignore 覆盖。

---

## 10. 后续工单顺序（严格一 TASK 一 commit，先旁路后切换）

1. G-LAUNCH：唯一 run.ps1 [staging|prod]，旧入口标废弃。
2. G-STAGE：轻量 Staging（Docker 待用户授权后替换），端口/DB/.env/profile/任务开关全隔离，XHS_PRODUCTION=false。
3. G-BASE：L0–L10 原样运行基线 + /health + Evidence。
4. G-DEP：依赖矩阵落地、Selenium 退出验证、Browser/AI/Collector Adapter Contract。
5. 治理 PASS 后接业务：ZBC-AUTH-01（全局 Auth 弹窗挂主 SPA）→ ZBC-SCHED-01（调度影子转门控）→ ZBC-DIM-01 / ZBC-EVT-01（双维度、事件关系）。

> 每步交付固定字段：改了什么 / 文件 / 为什么 / DB 是否变 / 迁移 / 测试与真实结果 / E2E / 遗留 / 回滚 / commit SHA；未实测一律标「未实测」。
