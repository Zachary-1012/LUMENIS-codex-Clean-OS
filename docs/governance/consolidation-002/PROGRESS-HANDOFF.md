# 进度断点与续接交接（PROGRESS & HANDOFF）

> 任务线：ZBC / DCC / SICI 统一生产架构 —— ZBC 资产收敛（Consolidation-002）
> 状态：**①静态扫描 + ②资产身份登记 + ③架构映射 + ④唯一Owner + ⑤Feature总账 + ⑥UI功能地图 均已完成（2026-08-31）；UI 视觉施工(⑨)仍按用户指令暂停**，待三仓库交叉核对后钉死信息架构再一次施工。
> 原则（用户原话固化）：**收敛不是删除**。任何旧代码/旧包/旧 API/旧页面/旧库表结构，在未完成「依赖确认→替代确认→迁移确认→回归验证」前不得删除。源码 / 数据库 / 运行时实测事实 > 基线文档 > 开发记录 > 聊天结论。

---

## 0. 一句话续接

新会话先读本文件 + `docs/PRODUCT_NAMING_BASELINE.md` + 本目录 5 份收敛产物（ASSET-REGISTRY / ARCHITECTURE-MAP / CAPABILITY-OWNERSHIP / FEATURE-REGISTRY / UI-FEATURE-MAP）；**②–⑥ 已完成勿重做、不要重扫、不要先动 UI、不要删任何旧文件、不要碰运行中的 8200/8201/9222 与数据库和采集。** 续接从 §7 剩余项（三系统启动页 → ⑦三仓库交叉 → ⑧IA 锁定 → ⑨UI 一次性施工）起。

## 1. 命名基线（已钉死，文档首次出现须写全称）

**层级（2026-08-31 决议，以 PRODUCT_NAMING_BASELINE 为准）**：最顶层统一平台层 = **Z-Brand Intelligence Platform**（不缩写）；其下 **ZBP / DCC / SICI 并列**、共同属于该顶层；**ZBP 不是最顶层母平台**。ZBP 内部再分 CTH-POMS、ZBMP（下表三行即顶层下三个并列平台）。

| 中文正式名 | English | 简称 | 仓库 |
|---|---|---|---|
| 品牌业务生产平台 | Z-Brand Business Production Platform | ZBP | Zachary-1012/Z-Brand-Core（本仓库） |
| 研发工程治理中枢 | Development Command Console | DCC | Zachary-1012/Development-Command-Console（本仓库以 git 子模块挂于 `tools/development-command-console`，@77dd1e4） |
| 智能研究学习中枢 | Intelligent Research & Learning Hub | SICI | Zachary-1012/SICI-Core |

ZBP 内部两产品：
- **CTH-POMS**：广州太古汇舆情监测系统 / CorTech Lab · Guangzhou Taikoo Hui Public Opinion Monitoring System —— 当前主力生产 / 客户交付入口。
- **ZBMP**：Z-Brand 品牌监测平台 / Z-Brand Monitoring Platform —— ZBP 内部母平台增强能力层，**不是第二套 Core**，与 CTH-POMS 共用同一 Core / DB / Runtime / 安全边界 / Release Gate。

## 2. 运行时与环境事实（实测）

- 项目根：`D:\Taikoo-monitor-new`；Windows + PowerShell；完全访问模式（命令直连真实系统，无需提权）。
- 端口：**8201 = 当前生产旁路 v5.9.9（UP）**；8200 = 现网（本盘点时 down）；9222 = CDP 真人浏览器（UP）。健康检查 `/healthz`。
- VERSION 文件 = `5.9.9`（曾存在代码/文档版本漂移，属 P0 待校准项，见既有治理文档）。
- **生产数据库 = `data/monitor.db`（6.29MB，51 张表）**。注意：根目录 `monitor.db` 只有 1 张 token_stat，是遗留空壳，**不是生产库**；另有 `staging/monitor.staging.db`、`data/cache/*` 5 份快照库、`data/backups/*` 10 份备份库、一个中文名 `你的数据库文件名.db`，均勿动。
- 生产前端唯一入口：`app.py @app.route('/') → send_from_directory('static','index.html')`，即 **`static/index.html`（SPA，817 行）**。`templates/` 下 5 个 Jinja（base/events/index/notes/report）为旧版服务端渲染，需在②中确认是否仍被 render_template 使用后再定状态。
- 自动提交：存在计划任务定时 `git add + commit`（提交信息「v5.8.9 自动保存版本（HH:MM 巡检）」，逻辑见 `scripts/daily_git_sync.py` + `v4_upgrade/version_center/git_manager.py`）。**手动 rebase/push 窗口要短，且只 add 指定路径**，避免与自动提交互相缠绕。
- 推送：直连 GitHub 会被重置，必须走本机代理 `git -c http.proxy=http://127.0.0.1:10808 -c https.proxy=http://127.0.0.1:10808 ...`；**严禁 force push**，远程分叉先 fetch + rebase。

## 3. 本轮已完成（① 全量资产盘点 · 静态层）

新增可复用只读扫描器：`scripts/inventory/asset_scan.py`（ast 解析 import / 动态 import / subprocess 调起，算 app.py 可达性与能力簇；可重复运行，不改业务）。

机器产物在 `docs/governance/consolidation-002/raw/`：
- `module_graph.json`：每个 .py 的行数 / 依赖 / 被谁依赖 / app 可达 / 是否独立入口 / 是否测试（全量机器可读）。
- `ASSET-IMPORT-MATRIX.md`：人读依赖矩阵。
- `CAPABILITY-CLUSTERS.md`：同能力多实现初筛聚类。

实测关键数字：
- Python 文件 **400**（业务 220 + tests 180）；从 app.py 静态可达 **84**；不可达且非测试 **136**；完全孤立（无人 import + 不可达 + 无 `__main__` 入口）**61**。
- app.py 路由 **189 个**（4784 行，顶层装配约 40 个本地模块，另有大量函数内 lazy import，扫描器已同时覆盖）。
- 生产库 **51 表**，核心表行数：notes 957、note_review_history 8327、collection_logs 477、topic_campaign_snapshots 325、events 427、event_mentions 562、note_comments 141、ai_filter_log 827、brand_industry_monitor 198、brand_knowledge 103、case_deep_analysis 20、event_graph_events 16、web_topics 96、web_mentions 79。
- 空表（PLANNED/RESERVED 候选）：app_evidence_records、review_tickets、review_samples、review_logs、notification_config、swire_notes。
- v4_* 表（v4_users 1 用户 / v4_sessions 27 / v4_login_attempts 26 / v4_audit_logs 33 / v4_security_questions 2）= 独立登录认证体系，对应 `v4_upgrade/` 包。
- 前端：CSS **22 个 / 16663 行**，index.html 引 **17 个** link；JS **20 个**；requirements **15 个**依赖。
- 子系统包：`platform_adapters/`（薄层适配器 + scheduling 动态调度）、`collector_v2/`（新一代采集，xhs/weibo/pipeline/scheduler/session，**当前 app 不可达**）、`v4_upgrade/`（auth/adapters/ai_hub/collect/console/importer/settings/version_center）、`collector_guard/`、`proxy_pool/`、`report_export/`、`deployment/`、`scripts/`。

## 4. 已识别的重复 / 多版本（这是④唯一 Owner 的输入，先标记不删）

- 报告导出 12 个路由/多实现：`/api/report/daily`、`/api/report/<type>`、`/api/report/generate`、`/api/report/v2/*`、`/api/report/verify`、`/api/report/export`、`/api/v2/report/export`、`/api/report/special/export`、`/api/special-report/*`、`/api/reports*`；文件层 `daily_report.py / export_report.py(626) / report_engine.py(71) / report_filter.py / report_export/report_engine.py / report_export/app_report_api_patch.py / scripts/export_report.py`。
- 负面确认两套：`/api/negative/*` 与 `/api/negative-review/*`（+ events 的 `/api/event-review/*`）。
- AI 六套并存：`ai_analyzer / ai_filter / ai_gateway_v570 / ai_learning_engine / ark_llm / local_ai_client / intelligence / adaptive_engine`，路由 `/api/ai/* /api/ark/* /api/intelligence/* /api/ai-filter/* /api/ai-learning/*`。
- 采集五套：`collector.py / collector_automation.py / collector_v2/（不可达）/ xhs_cdp_collector.py / web_monitor*.py / topic_campaign.py / rednote_collector.cjs / xhs_*.js`，路由 `/api/collect* /api/collector/* /api/xhs/* /api/rednote/*`。
- 运行代码（高危）三套：`/api/developer/run`、`/api/dev/run-code`、`/api/config/run-code`。
- 健康检查 5 个：`/healthz`、`/api/system/health`、`/api/platform-health`、`/api/stability/*`、`/api/collect-health`；文件 `system_health_api / stability_monitor / system_guardian / system_watchdog / auto_recovery / platform_adapters/health_center`。
- 同名重复文件：根 `risk_engine.py`(仅 8 行) 与 `collector_guard/risk_engine.py`；根 `report_engine.py` 与 `report_export/report_engine.py`；多处 `config.py`（根 / v4_upgrade / platform_adapters / proxy_pool）；根 `check_system.py` 与 `scripts/check_system.py`。
- `deployment/` 存在中英双份脚本与一层**重复嵌套** `deployment/deployment/`（中文名在 utf-8 下显示 mojibake，实际为「健康检查.py / 数据库备份.py」等）。
- 根目录臃肿：约 150 个根级文件，含 18+ 个 start_*.bat/一键*.bat、prod_err1–9/prod_out1–9/sys_*/startup_* 等数十份日志、若干截图与视频帧 jpg、`ark_analysis.py.txt` 伪装后缀、`app.py.bak-*`、`app_refactor_blueprint.py`（16 路由零注册，前期已标 DEPRECATED 候选）。
- 能力簇规模（机器初筛）：采集 32、恢复/守护/稳定 17、评测验证 16、AI 13、Cookie/登录 10、品牌案例知识 10、报告导出 10、网络代理隧道 10。

## 5. 资产 10 状态定义（②给每个资产打标时统一用这套枚举）

`ACTIVE`（生产在用）/ `DEVELOPING`（在建未上线）/ `PLANNED`（已规划未做）/ `RESERVED`（预留窗口，先占位）/ `EXPERIMENTAL`（实验/影子）/ `LEGACY`（旧版仍在跑）/ `DEPRECATED`（已弃用待退）/ `DUPLICATE`（重复实现，须指向唯一 Owner）/ `MIGRATION_REQUIRED`（需迁移）/ `NOT_VERIFIED`（事实未核实）。

## 6. 本轮同步到 Git 的素材（视频走 LFS）

- `.gitattributes`（新增）：仅 `docs/reference/ui-research/source-videos/**` 走 LFS；已 `git lfs install --local`，7 段视频 check-attr 全部命中 `filter: lfs`。
- `.gitignore`：新增源视频目录的 `!` 例外（全局 `*.mp4` 仍忽略其它位置）。
- `docs/reference/ui-research/source-videos/`：7 段源视频（约 403MB，LFS），清单/sha256/用途见 `docs/reference/ui-research/VIDEO-SOURCE-MANIFEST.md`。
- `docs/reference/ui-research/reference-images/`：16 张微信参考图（2026-08-31 经 SHA 比对仅新增 01712291、cd9009bc 两张，其余为重发重复）。
- `docs/reference/ui-research/reference-docs/`：需求 Word《z-Brand Core UI视觉&交互逻辑1.0.docx》。
- 2026-08-31 重发 9 段录屏经 SHA256 比对全部=已上 LFS 7 段，零重复上传（详见 MANIFEST §3.6）。
- 既有 `ref_gpt_v2/`（353 文件，普通 Git 跟踪）保留。
- 手机版 ChatGPT 原始录屏已被微信清理、全机未找到；其抽帧留存于 `ref_gpt_v2/frames/`（已在 MANIFEST 如实记录）。

## 7. 下一步（精确续接顺序，一次只做一个 TASK / 一个 commit）

> **②–⑥ 已于 2026-08-31 完成（勿重做）**：②ASSET-REGISTRY（生成器 build_asset_registry.py，400/84/136、app.py 路由189/全仓363、51表）、③ARCHITECTURE-MAP、④CAPABILITY-OWNERSHIP、⑤FEATURE-REGISTRY、⑥UI-FEATURE-MAP。下列②–⑥条目存档；剩余推进顺序见本节末「剩余顺序」。

- **② 资产身份登记**：以 module_graph.json + 189 路由 + 51 表为底，给每个资产补「系统/产品/业务域/模块/解决什么/谁调用/调用谁/依赖/重复/旧版本/被谁替代」并用 §5 十状态打标；产出 `ASSET-REGISTRY.md`。
- **③ 架构收敛**：落「系统→产品→业务域→模块→功能→服务→API→数据→UI→Runtime」的 `ARCHITECTURE-MAP.md`（只映射不搬目录；如要搬迁必须 import/route/template/static/test/部署全绿才做）。
- **④ 唯一能力 Owner**：对 §4 每簇重复判定唯一 Owner，其余标 DUPLICATE 并指向 Owner（主体过滤/风险/事件聚合/报告生成尤其只能一个 Owner）；产出 `CAPABILITY-OWNERSHIP.md`。**核心红线函数不得改口径**：`SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS / subject_hit() / _subject_sql_and_values() / aggregate_events() / build_daily_report()`，以及 publish_datetime / captured_at 时间口径、历史数据。
- **⑤ UI 功能地图（不画视觉）**：产品→域→模块→功能→页面→页面状态→交互，已完成/未完成/PLANNED/RESERVED 全部入图（例：风险总览 ACTIVE / 风险趋势 PLANNED / 风险预测 RESERVED / AI 风险解释 EXPERIMENTAL），为后续新增功能预留导航窗口。
- **功能资产注册表**：`FEATURE-CTH-XXX-NNN / FEATURE-ZBMP-XXX-NNN`，字段含 系统/产品/模块/Owner/UI/API/DB/Status/Evidence；以后改代码前先查 Feature ID，不存在先登记。
- **三系统启动页（用户已要求，独立不启用）**：ZBP/DCC/SICI 各做网页版+手机版启动页，启动后为居中密码登录弹窗，系统名缩小居中于最底部；**当前不启用，单独放一个独立文件夹并附 README 说明如何启用**。注意 DCC/SICI 是独立仓库，本仓库只做 ZBP 侧或静态原型，不写入其仓库。
- UI 视觉/交互施工：**继续暂停**，等 GPT 侧源码审计回来交叉核对、UI 信息架构一次钉死后再做；既定 GPT/Codex + iOS + 侘寂黑白灰方向与 token 见 `ref_gpt_v2` 与本目录 MANIFEST §6，不推翻。

**剩余顺序（②–⑥已完成后续接这里）：**
1. 三系统启动页（ZBP/DCC/SICI 网页+手机静态原型，独立文件夹、默认不启用、附 README；DCC/SICI 独立仓不写入）。
2. ⑦ 三仓库交叉审计（与 GPT 侧源码审计交叉核对，校准 Owner/Feature）。
3. ⑧ UI 信息架构最终锁定（以 UI-FEATURE-MAP + MANIFEST 素材为底，交叉核对后一次钉死）。
4. ⑨ UI 一次性施工（侘寂黑白灰+语义小状态点+统一 Token/组件，390/430/768/1024/1280/1440 全断点，含修复手机/网页显示不全；先 Staging 后灰度）。
5. ⑩ Runtime / L0–L10 E2E → ⑪ 生产验收 Release Gate。
6. 并行业务工单（不阻塞收敛）：AUTH-01 主 SPA 挂 auth_global、SCHED-01 影子转门控(待签字)、DIM-01 双维度落库、EVT-01 三类事件四关系、P0-FIX-1 daily_git_sync 版本号漏括号。

## 8. 边界红线（每步自检）

不改业务代码口径、不删旧资产（只标记/归档且可 git 恢复）、不碰运行中的 8200/8201/9222 进程、不写生产库、不重启生产、不改临时公网、暂停小红书采集、不动 DCC/SICI 仓库内容；不提交 .env / *.db / cookies / 浏览器 profile / *.log / *.exe（.gitignore 已挡，add 时仍只指定路径双保险）；小步提交，推送走 10808 代理、禁 force。

## 9. 续接自检清单

1. `git status` 干净、`git log --oneline -5`、`git rev-list --left-right --count origin/main...HEAD` 应为 `0 0`（本地=远程）。
2. `git lfs ls-files` 能看到 7 段视频指针。
3. 重跑 `python scripts/inventory/asset_scan.py` 应稳定得到 400/84/136/61（数字漂移说明代码变了，要先查原因）。
4. 只读校验生产库：`data/monitor.db` 仍 51 表、notes 仍 957 行附近（采集暂停下应基本不变）。
5. 浏览器开 `http://127.0.0.1:8201/healthz` 仍返回 version 5.9.9。
