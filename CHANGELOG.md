# 变更日志

## [5.9.9-t1] - 2026-09-02（双子星B0阶段：README融合12节母体+四库体系术语升级+跨仓SHA锚点回写+首次双仓同步Push）

### 【开工记录 05:03】
- **阶段**：B0 双子星审计收敛（Spec Mode Implement → Review Gate PASS → B0-5 SHA回写 + Push）
- **执行人**：Zachary-OS-AI 总执行师（TRAE Main Window）
- **授权依据**：用户 2026-09-02 指令「好的，执行吧」+「任何时候开工前开工结束都要推送至双子星库仓库里并同步写每回日志」
- **本次施工范围（硬边界 NFR-001）**：
  - 仅 `.md` / `.gitignore` / Spec 辅助文件；**零 .py/.js/.html/.db 业务源码修改**
  - A 仓：仅 `README.md`（43 历史杂改保持未暂存，绝不纳入 commit）
  - B 仓：仅 `README.md` amend（components/ 其余未审计实现文件绝不纳入 commit）
- **前置基线锚（开工前 git log -1）**：
  - A 仓 ZBC main：`39e1ba7`（README 融合 + 矩阵 + 资产清单 + E-001~E-009）
  - B 仓 ZOSAI main：`2fbdfba`（README 12节 + .gitignore + E-008 组件四库术语升级 6md）
- **目标输出**：
  1. NEW_A_SHA / NEW_B_SHA 与 README 内 `last_verified_sha` 双向锚点对齐
  2. 首次两仓同时 git push origin main（开工前 push 次数 = 0）
  3. CHANGELOG 开工/结束双段写入并随本次 push
  4. AGENTS §16 交付 10 要素完整报告
- **硬禁止（违规即 BLOCK）**：不 push 生产 DB / Cookie / Key / 43 历史杂改 / B 仓 components 实现文件

## [5.9.9-t0] - 2026-09-02（Zachary-OS-AI 总执行师 T0 基线锚定 + SEC 加固 + 启动收口 + 首次四层 E2E 实锚）

### T0-1 生产数据库事实基线锁定（只读审计）
- 四候选库对账，锁定真实生产库 = `data/monitor.db`（6.41 MB / 53 表 / notes=957 / events=427 / daily_reports=33 / collection_logs=495 / ai_filter_log=827 / note_review_history=8327）。
- 证伪 CONFLICT-001：原"7 张 models 有/database.py 无"为假阳性（运行时 `CREATE TABLE IF NOT EXISTS` 已全部落地）。
- 根目录 `monitor.db` 仅 12 KB / 1 张 `token_stat` 表 = 废弃壳，不再作为基线。
- 双时间铁律 P0 验证：`publish_datetime IS NULL = 0 / publish_datetime = captured_at = 0`，**零违规**。

### T0-2 SEC-001 HIGH 清零 + 依赖补完
- **`import_cookies.py` 移除 6+17 条硬编码 Cookie**（微博 SESSDATA + B站 bili_ticket JWT 等高敏感凭证），改为读取 `.env`：
  - `ZBC_WEIBO_COOKIE_JSON` / `ZBC_BILI_COOKIE_JSON`：JSON 数组形式，无配置时打印友好提示不硬报错，最终全部为空 `sys.exit(1)` 防静默空落盘。
- `.env.example` 新增 `ZBC_WEIBO_COOKIE_JSON / ZBC_BILI_COOKIE_JSON / ZBC_API_KEY` 三模板占位。
- `.gitignore` 追加 `.env.local/.env.prod/.env.txt`，并加 `scripts/_zachary_t0*` 临时审计脚本忽略。
- SEC-006：`requirements.txt` 从 18 项扩至 31 项，补全 Flask-CORS、Flask-Limiter、APScheduler、schedule、beautifulsoup4、lxml、websocket-client、python-dateutil、PyYAML 九项实际运行依赖；本地 `.venv` 单包重试 3 次 → 9/9 装成。
- Secret 扫描：ZBC 源码层面 **0 HIGH**；OSAI 库 **0 HIGH**（双库 SEC 基线到净）。

### T0-3 启动入口统一收敛为 `scripts\start_production.ps1`
- 35 个 LEGACY 入口（start_\*、一键\*、启动系统\*、run_\*、start_tunnel、系统守护闭环、run.ps1、run_production、run_supervised、cloudflared_guardian 等 .bat/.ps1/.vbs/.py）统一在首行注入 **LEGACY REDIRECT NOTICE**：指向 `scripts/start_production.ps1`（保留 shebang/@echo off/编码声明，不删主体逻辑以兼容）。
- `scripts/start_production.ps1` 重写为 ASCII 安全 + UTF-8 输出版：
  - 互斥锁 `Global\ZBrandCoreLauncher8201`；.venv Python 强制路径（避开全局 3.14.7 vs .venv 3.13.15 混用）。
  - 新增启动前依赖预检，调用 `scripts/_prod_dep_check.py`（flask/playwright/apscheduler/schedule/dotenv/requests/bs4 7 项；OK exit 0 / MISSING exit 2 + 中文指引）。
  - 8201 Flask / 9222 Edge CDP 三幂等（互斥+进程存在+HTTP 健康）；启动后 15 秒 healthz 等待；失败自动打印日志末 20 行 stderr。
  - 启动完成打印看板：`Zachary-OS-AI · Z-Brand-Core production launcher` + UP/Healthz/CDP 地址。
- 新增 `scripts/_prod_dep_check.py`（被 start_production.ps1 调用，必须随仓库保留）。

### T0-4 首次四层 E2E 实锚（真实启动，非静态断言）
- L1 HTTP 健康：`/healthz` = HTTP 200 / `{"ok":true,"service":"taikoo-monitor","version":"5.9.9"}`。
- L2 路由注册：359 条 Flask 路由已注册 → 60 页 SPA/SSR + 290 `/api/*` 接口。
- L3 Playwright 真实浏览器 15 SPA：
  - 修正 Basic Auth 用 Header 注入（不再 user:pass@URL 导致浏览器 `Failed to execute fetch`）后，`/` 首页 HTTP 200 + `title=广州太古汇舆情监测系统·CTH-POMS`。
  - 15 张 Hash Router SPA（/#/overview ... /#/settings）DOM 判据：15/15 全部 OK；**JS fatal / pageerror = 0**；Console 错误 = 2（非致命样式警告）。
  - SSR `/v4/` + `/topic-campaign` = HTTP 200 OK。
  - 非阻塞告警：`/architecture` + `/event-graph` 两蓝图路由返回 404（属 P1 能力，不阻塞 CTH 15 核心页上线）。
- L4 pytest 核心 152 用例：exit=0，**152 passed · 0 failed · 0 error**（`-k 'not browser or playwright or selenium or e2e or live or remote'` + `ZBC_DB_PATH=staging/monitor.staging.db` 与生产隔离）。
- L5 双时间铁律再验：`publish空=0 / pub=cap嫌疑=0`；遗留 notes 空正文 = 253 → 记为 T1-1 分批 CDP 补抓。
- pytest-timeout 2.4.0 补装解决早期 `unrecognized arguments: --timeout`。

### 已知风险 / 后续
- 真实 bili_ticket expires=2026-08-31 已过期（系统启服不阻塞，但 B 站采前需 `.env` 换最新凭证）。
- 小红书 NEED_VERIFY 全链路真人扫码闭环未人为触发真实验证 → 安排至 T1-2。
- `_tmp_p0_*`、`.trae/`、`_zachary_t0*` 脚本与截图本提交不包含；临时产物已于审计结束后物理删除。

## [5.9.9] - 2026-08-31（事件关系图谱数据库持久化修复）

### 修复：event_graph.py 从纯内存实现改为数据库持久化

**问题**：event_graph.py 使用内存字典存储事件和关系，没有数据库表，进程重启后数据丢失，无法与现有events表（427条）关联。前端事件关系图谱页面永远显示"空状态"。

**修复内容**：
1. 新增数据库表：event_graph_events（事件表，含source_event_id关联现有events表）、event_graph_relations（关系表，唯一约束防重复）
2. BrandEvent类新增：from_row()、save_to_db()、source_event_id、created_at/updated_at
3. EventRelation类新增：save_to_db()、created_at
4. EventGraph类重构：__init__自动建表+加载、load_from_db()、add_event/create_event/add_relation自动持久化、import_from_existing_events()从现有events表导入（按risk_level判断类型）、reset_event_graph()
5. 新增写入API：POST /api/event-graph/events、POST /api/event-graph/relations、POST /api/event-graph/import、DELETE /api/event-graph/events/<id>
6. 保留所有现有读取API，向后兼容

**数据**：从现有events表导入15条（13传播+2舆情），手动创建1条营销事件，添加1条触发关系。当前16事件+1关系。

**验证**：健康检查5.9.9、统计/列表/创建/添加关系API全部正常、进程重启数据不丢失、前端页面正常加载。

### 版本号统一
- VERSION文件：5.9.8 -> 5.9.9
- app.py APP_VERSION：5.9.8 -> 5.9.9

## [5.9.8] - 2026-08-31（P0-1生产事实校准 + P0-2阶段1影子模式 + P1 App Evidence最小版）

### P0-1 生产事实校准（版本漂移修复）
- VERSION文件: 5.9.0 → 5.9.7。
- README.md: 版本声明→v5.9.7，最新进度重写，新增v5.9.0~v5.9.7演进记录。
- CURRENT_BASELINE.md: v5.8.6→v5.9.7。
- PROJECT_STATUS.md: v5.8.11→v5.9.7。
- 未触碰采集核心代码，仅修正文档版本漂移。

### P0-2 阶段1：Topic Campaign 调度收口（影子模式）
- 统一动态调度体系已存在（platform_adapters/scheduling/）：policy+decision+planner+store+state_map。
- topic_campaign.py接入：
  - 导入统一Scheduler（get_planner），异常降级不影响生产。
  - 固定时间点触发时同时调用planner.decide('xhs')，记录对比日志。
  - 采集完成后调用planner.record_result()回写结果（SUCCESS/NO_NEW_DATA/NEED_VERIFY/IP_RISK）。
- 不改变任何生产采集行为，只做观察、记录、回写。
- 保留固定时间点[9,11,13,15,17,19]，阶段2灰度后再由Scheduler门控。

### P1：XHS App Evidence Adapter 最小可运行版（Shadow模式）
- 定位：用户主动截图上传→字段识别→人工确认→Shadow。
- 严格禁止：自动登录、自动浏览、私有API、逆向签名、抓包、绕风控。
- 新增app_evidence.py（14KB）：
  - AppEvidence数据结构 + 数据库表app_evidence_records。
  - 支持来源xhs_app/douyin_app/weibo_app/other。
  - 支持指标browse_count/discussion_count/note_count等。
  - 状态机pending→confirmed/rejected/shadow。
  - MD5哈希去重。
- API路由（8端点）：stats/list/get/upload/confirm/reject/shadow/delete。
- 前端页面：导航入口+统计卡片+上传表单+筛选+记录列表。
- 新增static/js/app_evidence.js（12.8KB）。

### 端到端测试（全部通过）
- 健康检查v5.9.7正常。
- App Evidence API：统计/列表/上传/确认/删除全部正常。
- 前端资源：app_evidence.js 200/12808 bytes，导航/页面/JS引用全部存在。
- 语法验证：app_evidence.py/topic_campaign.py语法正确。

## [5.9.7] - 2026-08-31（CHANGELOG补全 + V3.0三模块前端页面全链路集成）

### CHANGELOG补全
- 补全v5.9.1~v5.9.6共6个版本的完整变更记录。

### V3.0三模块前端页面集成
- 品牌知识库：导航+统计(80条/7分类)+分类筛选+搜索+详情。
- 事件关系图谱：导航+统计+关系图例+空状态+事件卡片。
- 品牌分析报告：导航+生成表单+报告展示(6维度)。
- 新增v3_modules.js(20KB)+v3_modules.css(9.6KB)。
- 42项E2E全部通过。

## [5.9.6] - 2026-08-31（案例深度拆解前端全链路集成 + 知识库第六批扩充 + 系统全面测试）

### 案例深度拆解前端页面集成（全链路完成）
- 新增侧边栏导航入口「案例深度拆解」，与现有页面风格统一。
- 新增页面：统计卡片（20案例/5类型/平均质量分100）+ 类型筛选 + 关键词搜索 + 案例卡片列表（响应式网格）。
- 案例详情弹窗：11维数据完整展示——核心挑战、策略目标、核心创意、执行细节（时间线）、传播渠道、数据成果、成功要素（带权重条）、可复用方法论（公式+适用场景）、系统启示。
- 新增 static/js/case_deep_analysis.js（18KB）和 static/css/case_deep_analysis.css（12KB），含移动端响应式适配。
- app.js navigateTo 重写中添加 case-analysis 页面懒加载初始化。

### 知识库第六批扩充（60→80条）
- 消费者行为学（4条）：双因素理论、前景理论（损失厌恶/框架效应）、社会认同理论、认知失调理论。
- 广告创意理论（4条）：USP独特销售主张、品牌形象论、定位理论、IMC整合营销传播。
- 全球品牌案例（3条）：Dior文化叙事、Spotify数据个性化、Patagonia环保价值观。
- 商业地产案例（3条）：成都远洋太古里、上海前滩太古里、东京表参道。
- 危机公关案例（2条）：肯德基鸡荒（正面）、特斯拉刹车门（反面）。
- 舆情管理方法论（2条）：黄金4小时法则、三级响应机制。
- 传播策略（2条）：AISAS模型、KOL营销金字塔。
- 知识库分类：品牌营销16/危机公关14/品牌案例24/舆情管理9/消费者行为8/广告宣传7/传播策略2。

### Bug修复
- 修复案例深度拆解列表API 500错误：min_quality_score传None导致TypeError，改为传0。
- 传播主体分类器验证：「羊城晚报官方账号」→ 媒体(media)，置信度0.9。

### 系统全面测试（33项全部通过，通过率100%）
- 系统基础、舆情监测核心、话题监测、事件管理。
- 案例深度拆解API（6端点）、品牌知识库API（2端点）、传播主体分类器、事件关系图谱。
- 前端页面集成验证、静态资源加载、核心功能回归。

### 版本号更新
- APP_VERSION: 5.9.0 → 5.9.6
- 前端22处资源引用版本号统一更新为 v=5.9.6

## [5.9.5] - 2026-08-31（传播主体分类器V2 + 案例拆解API集成 + 第五批知识扩充）

### 传播主体分类器V2：多类型匹配+冲突解决机制
- 修复「羊城晚报官方账号」被误判为官方的问题：媒体+官方组合判定为媒体。
- 新增6条冲突解决规则：媒体+官方、机构+官方、媒体+机构、KOS+官方等组合优先级。
- 传统媒体关键词（日报/晚报/电视台）置信度提升至0.9。
- 12/12测试用例全部通过。

### 案例深度拆解API集成到app.py（6个路由）
- GET /api/case-analysis/stats - 案例库统计
- GET /api/case-analysis/list - 案例列表（筛选+分页）
- GET /api/case-analysis/detail - 案例详情（11维）
- GET /api/case-analysis/search - 案例搜索
- GET /api/case-analysis/methodology - 所有方法论（58条）
- GET /api/case-analysis/system-insights - 所有系统启示（77条）

### 第五批知识扩充（知识库52→60条，案例库12→20个）
- 8条新知识：耐克Just Do It、苹果Think Different、抖音、小红书、小米生态链、特斯拉、阿那亚、天目里。
- 8个案例11维深度拆解，质量分均100。

### 端到端测试：30/30全部通过

## [5.9.4] - 2026-08-31（案例深度拆解模块 + 行业平台配置 + 知识库扩充至52条）

### case_deep_analysis.py：11维案例深度拆解框架
- 11维结构：基本信息、核心挑战、策略目标、核心创意Big Idea、执行细节、传播渠道、数据成果、获奖、成功要素（带权重）、可复用方法论、系统启示。
- SQLite存储，支持筛选/搜索/JSON导出。

### 12个经典案例11维深度拆解（质量分均100）
- 品牌营销（5）：多芬、可口可乐、奥利奥、凡士林、喜力。
- 危机公关（4）：强生泰诺、星巴克、海底捞、Airbnb。
- 商业地产（3）：广州太古汇、兴业太古汇、成都万象城。

### config/industry_platforms.json：行业平台链接配置
- 7大类30+平台：营销创意、舆情公关、商业地产、全球4A、知识学术、数据研究、社交媒体。

### 知识库扩充至52条（第四批8条）
- 危机公关：丰田召回、三星Note7、SK-II。
- 商业地产：侨福芳草地。
- 营销理论：AARRR、私域流量、营销归因、A/B测试。

## [5.9.3] - 2026-08-31（XHS App API研究 + 新模块API路由集成）

### XHS App端API可行性研究
- 结论：小红书App端API采用签名算法（x-s/x-t/x-s-common），Web端无法直接调用。
- 话题浏览量/讨论量仅在App端显示，Web端无此数据。
- 当前选择：保持Web端数据真实性，不伪造，该指标标注为App端专属。

### 新模块API路由集成到app.py
- 传播主体分类器：POST /api/subject-classifier/classify、GET /api/subject-classifier/types。
- 事件关系图谱：GET /api/event-graph/stats、GET /api/event-graph/events。
- 品牌分析报告：POST /api/brand-report/generate。
- 品牌知识库：GET /api/brand-knowledge/stats、GET /api/brand-knowledge/search。

## [5.9.2] - 2026-08-31（/remote修复 + 事件关系图谱 + 品牌分析报告升级）

### /remote和知识库API 404修复
- 问题：旧进程未完全停止导致新路由未加载。
- 修复：彻底重启8200进程，确认所有新API路由正常加载。

### 事件关系图谱模块（event_graph.py）
- 三类事件：营销事件、传播事件、舆情事件。
- 四种关系：触发（trigger）、衍生（derive）、继发（follow）、并行（parallel）。
- API：GET /api/event-graph/stats、GET /api/event-graph/events。

### 品牌分析报告升级（brand_report_generator.py）
- 从舆情报告升级为品牌传播与市场情报报告。
- 报告维度：品牌声量、传播主体、内容类型、情绪、竞品对比、营销事件、舆情风险、建议。
- API：POST /api/brand-report/generate。

## [5.9.1] - 2026-08-31（隧道守护 + 品牌知识库 + 传播主体分类器V1）

### Cloudflare隧道稳定性守护（tunnel_guardian.py）
- 隧道守护进程，自动检测隧道状态，断开时自动重连。
- 限制：trycloudflare免费版无法固定域名，固定域名需Cloudflare付费版token。

### 品牌知识库模块（brand_knowledge_base.py，影子板块）
- 目标：全网学习品牌营销、广告宣传、舆情监测知识，为系统脱离外部AI提供知识基础。
- 9大分类：品牌营销、广告宣传、舆情管理、消费者行为、市场趋势、品牌案例、传播策略、危机公关。
- SQLite存储，支持分类检索、全文搜索、标签关联。
- API：GET /api/brand-knowledge/stats、GET /api/brand-knowledge/search。
- 首批知识44条。

### 传播主体分类器V1（subject_classifier.py）
- subject_type与content_type分离：传播主体身份与内容属性独立判断。
- 基于规则的分类：作者名称关键词、认证信息、粉丝量级、内容模式。
- API：POST /api/subject-classifier/classify、GET /api/subject-classifier/types。
- 已知问题：「羊城晚报官方账号」被误判为官方（V2在5.9.5修复）。

### 数据库变化
- 新增表：brand_knowledge、event_graph、case_deep_analysis。
- 无结构变化、无迁移、历史数据零删除零清空。

## [5.9.0] - 2026-08-31（V3.0 基线首批落地：Auth Recovery Center + XHS App Topic Adapter + QR_REQUIRED状态）

### V3.0 P0: Auth Recovery Center（认证恢复中心）
- 新增 \uth_recovery_center.py\：认证异常检测 → 恢复任务创建 → 前端弹窗提示 → 用户扫码恢复 → 状态回写 → 健康探活 → 解除熔断 完整闭环。
- 新增 \uth_recovery_tasks\ 表：存储恢复任务（platform/issue_type/status/title/description/recovery_url/expires_at等）。
- 恢复任务状态：pending / in_progress / completed / failed / expired，TTL 1小时自动过期。
- 支持异常类型：cookie_expired / login_expired / captcha / qr_required / session_invalid / ip_risk / unknown。
- 去重机制：相同platform+issue_type的pending任务不重复创建。

### V3.0 P0: Auth Recovery API（认证恢复API蓝图）
- 新增 \uth_recovery_api.py\：\/api/auth-recovery/\ 蓝图，提供6个接口：
  - GET /health：恢复中心健康检查
  - GET /summary：恢复中心摘要（前端轮询用，判断是否需要弹窗）
  - GET /tasks：获取恢复任务列表
  - POST /tasks：创建恢复任务
  - POST /tasks/<id>/start：标记任务为进行中
  - POST /tasks/<id>/complete：标记任务完成（自动触发后台健康探活和熔断恢复）
  - POST /tasks/<id>/fail：标记任务失败
- 任务完成后自动在后台线程调用 \	opic_campaign.topic_recover()\ 执行健康探活，确认完全健康才解除熔断。

### V3.0 P0: CollectionStatus 增加 QR_REQUIRED 状态
- \platform_adapters/base.py\ 的 CollectionStatus 枚举增加 \QR_REQUIRED\ 状态，用于标识需要扫码恢复的采集异常。
- 与现有 NEED_VERIFY / BLOCKED / SESSION_EXPIRED 等状态并列，不破坏现有逻辑。

### V3.0 P1: XHS App Topic Adapter（小红书App端话题适配器）
- 新增 \platform_adapters/xhs_app_topic.py\：继承 BasePlatformAdapter，实现 search/detail/health_check 接口。
- 目标：补齐话题发现 + 话题浏览量/讨论量（App端专属数据，Web端无法获取）。
- Feature Flag 控制：\XHS_APP_TOPIC_ENABLED\ 环境变量，默认关闭，不影响现有Web采集主链路。
- 来源字段区分：\enrich_note_with_source()\ 方法为笔记数据增加 source=data_source 字段，区分 xhs_web / xhs_app。
- App端API接入点预留：\_discover_topics_from_app()\ 和 \_topic_metrics_from_app()\ 方法待实现（需要小红书App端API endpoint和签名算法），当前返回空（不伪造数据）。
- 已注册到 Adapter Registry：\list_adapters()\ 返回 ['douyin', 'xhs', 'xhs_app_topic']。

### V3.0 约束遵守
- 不修改现有Web采集主链路（xhs_campaign_monitor.js / topic_campaign.py 核心逻辑未动）。
- Adapter化接入，复用 BasePlatformAdapter 接口和 Registry。
- 数据统一进入 Content Center（预留，后续接入）。
- 复用事件中心（预留，后续接入）。
- 保留主体过滤规则（subject_rules.py 未修改，Adapter层不做业务判断）。
- Feature Flag 控制上线，默认关闭。
- 禁止大规模重构，禁止破坏现有CTH-POMS生产能力。

### 端到端测试（已实测通过）
- 模块导入：auth_recovery_center / auth_recovery_api / platform_adapters.xhs_app_topic 全部导入成功。
- Adapter注册：list_adapters() 返回 ['douyin', 'xhs', 'xhs_app_topic']。
- QR_REQUIRED状态：CollectionStatus.QR_REQUIRED.value == 'QR_REQUIRED'。
- Auth Recovery API健康检查：/api/auth-recovery/health 返回 ok=True, module=auth_recovery_center。
- 恢复任务完整流程：创建(task_id=1, status=pending) → 查询(count=1) → 摘要(pending_count=1, has_issue=True) → 标记完成(ok=True, 触发后台健康探活)。
- healthz：8201旁路 ok=True, version=5.8.11。

### 数据库变化
- 新增表：\uth_recovery_tasks\（恢复任务表，12字段，2个索引）。
- 无结构变化、无迁移、历史数据零删除零清空。

### 未解决 / 后续计划
- XHS App Topic Adapter 的 App端API接入：需要小红书App端API endpoint和签名算法（逆向或抓包），当前为框架预留。
- 话题 browse_count/discussion_count：Web端无此数据（App端专属），待App端API接入后获取。
- 影子板块（AI学习知识库）：品牌营销/广告宣传/舆情监测知识的全网学习和数据库充实，作为下一批V3.0任务。
- 传播主体模型（subject_type分离）、事件关系图谱、品牌分析报告升级：按V3.0开发顺序后续推进。
- 8200现网仍运行v5.8.4，是否切v5.9.0生产待用户拍板。

## [5.8.11] - 2026-08-31（探活修复 + 详情补抓 + 话题聚合页指标研究结论）

### 探活函数修复（P0，已E2E验证）
- 修复 \_probe_xhs_health_via_cdp\ 中 \page.url()\ 应为 \page.url\（属性非方法）的bug，原报错被异常吞掉导致健康探活永远失败。
- 修复 \	opic_recover\ 调用 \_probe_runtime_state\ 在熔断OPEN时跳过实时探活的bug，改为直接做完整探活（explore + 搜索测试）。
- 增强 \_probe_xhs_health_via_cdp\ 增加 \	est_search\ 参数：recover时额外做搜索测试，只有搜索也不跳验证页才判定完全健康并解除熔断。
- 修复 \	opic_note_detail_backfill.py\ 中同样的 \page.url()\ bug。

### 详情补抓完成（已实测）
- 120条笔记详情补抓完成：94条 full（正文+媒体+评论齐全）、25条 partial、1条 failed（页面加载失败）。
- 117条有正文、119条有媒体（平均20张/条）、96条有评论。
- 全程拟人间隔3-8秒，未触发验证，未撞风控。
- 补抓后重新分类回填：主体命中59条（49.2%），内容类型 UGC85/官方16/体验11/活动内容8，情绪 neutral107/positive13。

### 话题聚合页指标研究结论（已知限制，不伪造数据）
- 研究发现：小红书Web端搜索结果页无"话题"tab，也无浏览量/讨论量指标。
- 小红书Web端话题页（\/topic/话题名\）是引导下载App的落地页，无浏览量/讨论量数据。
- 结论：话题浏览量/讨论量仅在小红书App内显示，Web端无法通过CDP采集。保持 \rowse_count=0, discussion_count=0\，绝不伪造数据。
- 后续可选方案：研究小红书App端API接口（需逆向），或在文档中明确标注该指标为App端专属。

### E2E测试（8/8通过）
- 依赖自检：flask/playwright/sqlite3/requests OK（apscheduler为可选依赖）。
- 模块导入：app/topic_campaign/xhs_runtime_state/subject_rules/collector 全部OK。
- 数据库：4表存在，新字段完整，120条笔记，94条full证据。
- 健康检查：healthz返回5.8.10，ok=True。
- API Smoke：status/runtime-state/stats/campaigns/topics/notes/timeline 7个接口全部OK。
- 六态验证：overall=healthy, auth=valid, session=real_session_valid, platform=reachable, circuit=closed。
- 主体口径：17主体词/18排除词，4个测试用例全部通过。
- Note Detail API：689字正文/20媒体/11评论，主体命中，官方类型，full证据。

### 未解决 / 已知限制
- 话题卡 browse_count/discussion_count 保持0（小红书Web端无此数据，App端专属，不伪造）。
- 8200现网仍运行v5.8.4，是否切v5.8.11生产待用户拍板。
- trycloudflare公网隧道为临时随机域名，固定域名需Cloudflare token。

## [5.8.10] - 2026-08-31（V2.0 基线 P0 收口：Runtime State 六态 + Topic Evidence Layer + UI Drill-down + 数据对齐）

### P0-1：统一 Runtime State 六态（已实测）
- 新建 `xhs_runtime_state.py`：统一 XHS 六态状态机（AUTH/SESSION/PLATFORM/COLLECTOR/CIRCUIT/RECOVERY），含 `XhsRuntimeState` 类、6 个枚举、`state_from_circuit()`/`state_from_probe()` 便捷函数。
- `topic_campaign.py` 新增 `_probe_runtime_state()`：熔断 OPEN 时跳过实时 CDP 探活（避免撞风控），仅加载熔断文件返回六态；非熔断时做真实探活。
- 新增 `/api/topic-campaign/runtime-state` 接口：返回统一六态（overall/auth/session/platform/collector/circuit/recovery + detail + last_check），前端全局健康小点/Auth Modal 共用。
- `topic_status` 集成 `runtime_state` 字段输出，`topic_recover` 改造为返回完整六态 dict。
- 实测：当前 NEED_VERIFY 熔断正确识别为 `circuit_open / auth=required / platform=verify / session=no_cookie / collector=idle / recovery=idle`，detail 标注 `skipped_probe`。

### P0-3/P0-4：熔断恢复闭环 + 半开探测（已实测）
- 新增 `_half_open_probe()`：IP_RISK 冷却结束后做半开探测（CDP 探活 + 单话题小流量采集验证），成功才解除熔断，失败重新冷却，绝不直接全量恢复。
- 新增 `/api/topic-campaign/half-open-probe` 接口（POST）：触发半开探测，返回探测结果 + 当前六态。
- 恢复闭环：识别→停止→熔断→冷却→人工验证→健康探活→半开→完全恢复，全程不绕过平台验证。

### P0-5/P0-6：Topic Evidence Layer + 主体过滤 + 分类（已实测）
- `topic_campaign_notes` 表向后兼容扩展 8 字段（16→24）：`media_json`/`comments_json`/`subject_hit`/`content_type`/`sentiment`/`risk_level`/`evidence_quality`/`detail_captured_at`，无迁移、无数据丢失。
- `_save_notes` 重写：集成 `subject_rules.subject_hit()` 正式主体规则（绝不重新实现第二套），新增 `_classify_note()` 基于规则的内容类型/情绪/风险/证据质量判断（不依赖 AI，可解释可追溯）。
- 120 条历史笔记分类回填完成：主体命中 59 条（49.2%），内容类型 UGC 85/官方 16/体验 11/活动内容 8，情绪 neutral 107/positive 13，风险全部 none，证据质量全部 search_only（证实详情补抓必要性）。
- 新建 `topic_note_detail_backfill.py`：对 search_only 笔记进入小红书详情页补抓正文/媒体/评论，熔断中拒绝启动（423），遇验证立即停止，拟人间隔 3-8 秒。
- 新增 `/api/topic-campaign/backfill-detail` 接口（POST）：后台线程触发补抓（支持单条 note_id 或批量 limit），熔断中返回 423。

### P0-7/P0-8：UI Drill-down + 数据对齐（已实测）
- 新增 `/api/topic-campaign/note/<note_id>` 接口：返回单条笔记完整详情（正文/媒体/评论/主体/分类/情绪/风险/证据质量），用于 Note Detail 下钻。
- 新增 `/api/topic-campaign/stats` 接口：话题聚合统计（Unique/New 24h/Runs/主体命中/风险/完整证据 + 按话题分组 + 内容类型分布 + 情绪分布），口径统一。
- 前端 `topic_campaign.js`：笔记列表增加分类标签（主体/内容类型/风险/证据质量/情绪），笔记行点击打开 Note Detail 弹窗（显示正文/媒体九宫格/评论/四指标/标签）。
- 前端 `topic_campaign.html`：增加 `#noteDetailModal` 弹窗 DOM，JS 缓存戳升级 v=5.8.10。
- 前端 `topic_campaign.css`：增加分类标签样式（7 种内容类型色 + 3 级风险 + 3 级证据质量 + 3 级情绪）、Note Detail 弹窗样式（header/stats/section/media/comments/actions）。
- 实测：stats API 返回 Unique=79（去重）、Runs=14、主体命中率 44.3%、full_evidence=0；笔记详情 API 正常返回全字段；JS 语法通过。

### 回归（已实测）
- Python 语法：topic_campaign.py / xhs_runtime_state.py / topic_note_detail_backfill.py / app.py / subject_rules.py 全部 OK。
- 导入测试：全部模块导入成功，MODULE_VERSION=5.8.10-p0-runtime-state。
- DB 验证：24 字段无缺失，120 条笔记，59 条主体命中，全部 search_only。
- API 冒烟：healthz / status / runtime-state / stats / campaigns / notes / timeline 全部 OK。
- 前端：JS 语法 OK，HTML noteDetailModal 存在，CSS type-tag 存在。
- 主体红线：subject_rules.py 未修改，_save_notes 调用正式 subject_hit()。

### 未解决 / 需用户操作
- 【需操作一次】当前 9222 小红书会话仍为 NEED_VERIFY 熔断（系统已正确保护，未硬撞）。需在 9222 真实窗口或手机小红书 App 完成官方扫码，再到话题页点「我已完成验证，重新检测」，健康探活通过即自动恢复。
- 120 条笔记全部为 search_only（无正文/媒体/评论），熔断解除后需运行 `python topic_note_detail_backfill.py` 或调用 `/api/topic-campaign/backfill-detail` 补抓详情。
- 话题卡 browse_count/discussion_count 仍为 0（该指标位于话题聚合页，当前抓的是笔记搜索页，不伪造，后续补聚合页抓取）。
- 8200 现网仍运行 v5.8.4（8/30 启动的旧进程），是否切到 v5.8.10 需用户拍板。
- trycloudflare 公网隧道当前未运行，固定域名需 Cloudflare 账号 token 建命名隧道。

### 绝对禁止（本轮遵守）
- 未删除 collector.py、未切 collector_v2、未删 Topic 表、未重建/清空生产 DB。
- 未修改 subject_rules.py 主体词/排除词/subject_hit()。
- 未破解验证码、未绕过风控、未新增第三套 Adapter 或 AI Gateway。
- 公网未混入本轮核心修复，8200 现网全程未动。

## [5.8.9] - 2026-08-31（双端显示一次性修复 + 话题采集链路多层根因修复 + 版本统一）
### 前端双端显示修复（已实测）
- 修复手机端 `#modal` 被两套旧 `.modal` 规则复用导致的居中裁切：`mobile.css` 增加移动端全屏容器、`.modal-panel` 贴底 sheet、`.modal-content` 弹性滚动；390 视口实测满宽（x=0、宽 390、bottom 贴屏幕底 844）、内容可滚。
- 首页/话题监测移动端布局收口：指标卡、任务卡、工具按钮自动换行整齐全宽，错误信息完整不截断，移动/桌面均零横向溢出；Zachary 机器人窄屏 52 贴边吸附；底部轻提示点击先移除黑条再展开贴底 sheet，不再叠加遮挡。桌面端维持原有弹窗交互不变。
### 话题采集链路根因修复（已实测真出数）
- Edge/Chromium 远程调试补 `--remote-allow-origins=*`（8 个启动点），修复 111+ 版本 ws 握手挂起导致的 connectOverCDP Timeout。
- `xhs_campaign_monitor.js` 成功路径补 `process.exit(0)`、150s 硬超时、close 5s 保护，修复事件循环被挂住、subprocess 空等 50 分钟、快照永不落地。
- 新增 CDP 目标复位（`cdp_helper.reset_cdp_targets` 与 node `resetCdpTargets`，纯 HTTP `PUT /json/new`+`/json/close`），连接前把重页面复位到 about:blank，修复 attach 重页面 30s 超时；复位后连接约 0.15s。
- 搜索前先 goto `/explore` 预热（冷导航 search_result 会挂起）；笔记接口匹配由 v1 改为 `v\d+` 以兼容已升级的 `/api/sns/web/v2/search/notes`；重写 DOM 兜底为浏览器侧自包含（原实现在 page.evaluate 内引用 node 侧 `clean()` 必抛 ReferenceError 并被静默吞掉，兜底从未生效）。
- 修复 `_run_collector` 缺省 `XHS_CDP_URL` 为空导致误走 headless 未登录 profile，默认连 9222 已登录浏览器（可用环境变量覆盖）。
- 修复 `_save_notes` INSERT 占位符 15、参数仅 14 的 `sqlite3.ProgrammingError`（补 first_seen_at，不改表结构、不迁移）。
- 同一轮相邻话题增加拟人随机冷却（12–28s）与连续空结果指数退避（封顶 90s），避免短时密集搜索被平台软降频（不报错、结果暂空），符合状态驱动/不撞风控口径。
- 实测：手动单话题「太古汇」19.6s EXIT=0、60 条真实笔记字段完整；8201 端到端 run_campaign 7 话题快照全部无 connectOverCDP 错误、每话题 24–26s 正常退出，热词各 60 条真实笔记落库（共 120，作者/赞评藏/链接齐全）。排查中曾疑冷词“0 条”为密集搜索软空窗，经诊断实测真因为连续采集触发小红书安全验证（302 到 website-login/captcha、verifyType=124），已由下述风控识别与熔断机制接管，绝不显示为 0 条。
### 风控识别 / 熔断 / 恢复（P0，已实测）
- node 采集脚本新增 `detectRisk`：识别跳转 captcha/login、扫码/滑块/安全验证、频繁/IP 风险/300012；命中即停止后续请求，输出结构化 risk_status（NEED_VERIFY/IP_RISK）与独立退出码（3/4），绝不再把验证页当成“0 笔记 ok=true”。实测命中后约 9.8s 退出、退出码 3、状态结构化。
- Python 专题采集新增熔断：快照状态区分 success/need_verify/blocked/error；命中即终止本轮后续话题并写 `data/private/topic_campaign_circuit.json`（NEED_VERIFY 须人工恢复、IP_RISK 冷却 45 分钟自动半开）；`run_campaign` 与 `/run` 接口熔断中直接拒绝（HTTP 423、不起 node、不撞平台，实测），`/status` 返回 circuit。
- 新增 `/api/topic-campaign/recover`：人工完成官方扫码/验证后做真实 CDP 健康探活（访问 explore 不跳验证页才算通过），通过才解除熔断，不绕过任何平台验证。
- 相邻话题拟人随机冷却 12–28s + 连续空结果指数退避（封顶 90s），降低短时密集搜索触发风控的概率。
- 前端话题详情新增全局熔断横幅（不跳页）：显示平台/状态/原因/触发时间与「我已完成验证，重新检测」按钮，need_verify 卡片橙色标注“已熔断，不计 0 条”；移动 390 与桌面 1440 双端实测零横向溢出、零第一方 JS 错误。

### 版本统一
- 运行时版本统一升 v5.8.9（VERSION、app.APP_VERSION、waitress ident、version_center 兜底、页头页脚、静态缓存戳、启动打印，共 40+ 处）。
### 回归（已实测）
- 主体红线 24/24；安全扫描 ALL_PASS；API 冒烟 ALL_PASS；核心回归 16/16（test_auth_api 空闲复跑通过，前次 ReadTimeout 系采集占用的瞬时现象）；移动 390 无阻断弹窗、6 指标齐全、零第一方 JS 错误、零横向溢出，桌面 1440 数字齐全且维持原行为。
### 未实测 / 遗留
- 话题卡 browse_count/discussion_count 在笔记搜索页为 0（该指标位于话题聚合页，当前未抓话题页，不伪造）；冷词在软空结果窗的长期表现需冷却后分批观察；trycloudflare 为临时随机域名，固定域名需 Cloudflare 命名隧道 token。

## [5.8.8] - 2026-08-30（Release Gate V1.0 基线门禁 + 统一认证 Contract + 安全整改，旁路不重构）
### 安全整改
- 移除 `system_watchdog.py` 源码内硬编码凭证，改读 `TAIKOO_AUTH_USER/TAIKOO_AUTH_PASSWORD` 环境变量（与 app.py 一致），仅在配置时发送 Basic 头。
- 新增 `tests/test_security_scan.py`：断言被跟踪源码无真实 Cookie/Session 票据、`.env`/生产库/私有状态目录被忽略、无硬编码密码（ALL_PASS 已实测）。
### 认证统一（安全不降）
- `app.py::_basic_auth` 在保留 HTTP Basic 的同时认可 v4 有效会话（Bearer/同名 session cookie），修复手机端仅登录 v4 时根级健康 API 401、全局健康小点无法取数的问题；匿名/无效会话仍返回 401。
### 测试 / 门禁
- 主体红线断言 12 → 24 项（外地太古汇排除、品牌词单独不命中、五字段命中、跨字段一票否决），`tests/test_subject_redline.py` 24/24 通过。
- 新增 `tests/test_api_smoke.py`（10 端点 200 + 匿名 401，测试会话自清理）；核心回归 `run_core_regression.py` 11/11 通过；四页面真实浏览器 E2E 无第一方 JS 错误。
### 文档 / 能力归类
- 新增 `docs/CAPABILITY_BASELINE.md`：Production/Compatibility/Shadow/Experimental/Rollback/Deprecated 六级能力分类，明确四代采集器、两套 Registry、多代 AI 的归属与唯一事实源，不做物理大合并。
### 版本统一
- 运行时对外版本统一为 v5.8.8：`VERSION`、`app.APP_VERSION`、waitress ident、version_center 兜底、页头/页脚显示、静态资源缓存戳、启动打印；`daily_git_sync` 自动提交标题改为动态读取 VERSION，避免再次发散。历史引入注释与真实文件名保留不改。
### 公网上线（已实测）
- 修复 `start_tunnel.py` 的旧项目硬编码路径，改为项目根 + `TUNNEL_PORT` 环境变量（默认 8201 验证实例，切生产设 8200）。
- cloudflared quick tunnel 建立并通过公网验证：`/healthz` 3/3 返回 5.8.8；受保护根路由与 `/api/platform-health` 无凭证返回 401（不裸奔）；`/v4/` 未登录跳转 `/v4/settings/login` 登录页正常；真实浏览器公网 E2E 通过。quick tunnel 为随机临时域名，固定域名需后续绑定 Cloudflare 命名隧道。

## [5.8.7] - 2026-08-30（22:00 豆包施工基线：公网平台化 + Ollama + 双产品适配）
### 新增：正式施工入口
- 新增 `docs/DOUBAO_2200_EXECUTION.md`，作为 22:00 豆包本地执行的正式施工指令。
- 明确 GitHub main 为研发事实源；开始任务先读取 AGENTS/README/CURRENT_BASELINE/PROJECT_STATUS/CHANGELOG/DEV_LOG/AI_POLICY/ARCHITECTURE/DEPLOYMENT/DOUBAO_GITHUB_UPGRADE_PROTOCOL 及品牌平台蓝图。

### 架构收口
- 产品 A：广州太古汇舆情监测系统；产品 B：品牌传播与市场情报智能平台；共享 Core，保持配置、数据隔离和版本血缘。
- WHO/WHAT/WHAT HAPPENED/SO WHAT 模型固定；`subject_type` 与 `content_type` 严格分离；营销/传播/舆情三类事件通过 `event_relation` 关联。
- Ollama 为正式本地 AI Runtime；云端 AI 不作为生产依赖；新 AI 能力优先 Shadow Mode。

### 公网与无人值守原则
- 公网访问采用 HTTPS + 反向代理/Cloudflare Tunnel，8200 不裸暴露。
- Web/API 与 Worker/Scheduler 解耦，页面关闭不影响后台任务。
- 生产启动入口必须统一 Python/依赖环境，修复全局 Python 与 `.venv` 不一致。

### Auth/采集保护
- Cookie/session 任何时候失效都进入系统内 Auth Recovery Modal，不简单跳登录页；合法流程支持时显示二维码/验证入口，验证成功后健康检查并恢复。
- `300012`、验证码、IP 风控进入状态机/熔断/冷却/告警；不伪装成 0 条，不进行验证码破解或风控绕过。
- 采集采用动态调度，不以固定 30 分钟/1 小时/固定时间点作为生产硬规则。

### 文档事实基线
- `PROJECT_STATUS.md` 同步为 v5.8.6 后续施工基线，并将公网、Ollama、Auth Recovery 纳入当前重点。

## [5.8.6] - 2026-08-30（平台 Adapter 架构 + 商业化代码来源审计基线）
### 新增：统一 Platform Adapter 层
- 新增 `platform_adapters/base.py`：统一 search/detail/comments/creator/health_check 与 CollectionStatus/CollectionResult 契约。
- 新增 `platform_adapters/registry.py`、`config.py`：平台注册、能力矩阵和优先级。
- 小红书定位 PRIMARY，抖音定位 SECONDARY；快手/B站/微博/贴吧/知乎暂保留扩展槽位，不进行深度开发。
- 新增 `platform_adapters/xhs.py`：以薄适配层桥接现有生产 `collector.py`，不替换现有采集主链。
- 新增 `platform_adapters/douyin.py`：安全扩展接口；未验证后端时明确返回未就绪，不伪造 0 数据。

### 新增：GitHub → 豆包升级闭环
- 新增 `scripts/github_upgrade_check.py`：比较本地 HEAD 与 GitHub main，远端有更新时生成 `.runtime/github_upgrade_task.md`。
- 新增 `DOUBAO_GITHUB_UPGRADE_PROTOCOL.md`：规定先审计、再修改、先旁路、再切换、测试通过才提交的升级流程。
- GitHub 仅作为协作基线，不允许远端代码无审计覆盖本地生产环境。

### 新增：第三方代码 / 许可证审计基线
- 新增 `THIRD_PARTY_LICENSE_AUDIT.md`：记录第三方来源、许可证和商业化前审计要求。
- 新增 `scripts/license_audit.py`：本地源码来源保护扫描，检测 MediaCrawler 等受限项目标记。
- MediaCrawler 仅作为架构研究参考；其当前源码明确采用 NON-COMMERCIAL LEARNING LICENSE 1.1，因此本项目不复制其源码、不作为运行时依赖、不把其实现直接并入生产系统。
- 商业化发布前仍需针对最终锁定依赖版本完成完整 SBOM/许可证扫描；本次不是法律级最终审计。

### 核心保护
- 保持现有广州太古汇主体过滤、风险/事件/报告、数据库和历史数据不变。
- 不绕过验证码、安全验证、IP 风控或平台访问控制。
- Adapter 层只负责平台传输/归一化，业务判断继续由 Z-Brand-Core 核心完成。

## [5.8.5] - 2026-08-30（上线冲刺：进程韧性 / 采集主链 / 采集风险引擎）
### 新增：无人值守韧性（冲刺3）
- 9222 真人采集浏览器掉线时，采集器自动 `CollectorAutomation.start_browser` 拉起持久 Edge 再走 CDP，拉不起才退 headless 兜底；真机“杀进程→自动拉起→CDP 就绪”验证通过。
- `scripts/start_production.ps1`（幂等：8201 看门狗 / 9222 已在跑则跳过）+ 登录自启 cmd，部署到当前用户启动文件夹免管理员，开机登录自动恢复采集。形成四层无人值守：登录自启 / app 崩溃看门狗双探测自愈 / 9222 崩溃采集器自愈 / 每日 08·18·24 自动版本同步。

### 增强：CollectorGuard 接入采集主链 + 采集提速（冲刺4）
- `collect_all` 每个关键词经 CollectorGuard 保护层（动态拟人间隔 / 响应归因 / 指标 / 断点），命中 IP 风险 / 验证码 / 登录失效即熔断并停止后续关键词请求，绝不伪装 0 条、不无限重试；5 项接入单测通过。
- 反馈词进入采集前清洗停用词/噪声并限量；全网发现 GDELT 超时默认 30s→8s，国内不可达快速放弃。真机回归任务 done（原始19/有效10/新增3/更新7/AI复核3秒过/事件链跑通/未崩），新笔记 publish_datetime 自动正确填充、标题非空。

### 新增：统一 Auth Recovery Center 前端闭环（P0，冲刺5）
- 统一控制台外壳新增“全局状态中心 + 不跳页统一恢复弹窗”：首页采集健康矩阵并入小红书主采集六态（v4 适配器 + 老链路合并，共 12 平台），修正平台中文名/数量字段；异常平台点击直接在当前页弹恢复窗而非跳陌生页。
- 弹窗严格 A 登录失效 / B 人机验证 / C IP风控熔断三类分清：C 类只显示冷却倒计时、不显示扫码（扫码不可解）；三步状态机（打开登录页→扫码/验证→恢复续采）、二维码或登录页截图、“我已完成验证/重新检测”“稍后处理（保持暂停不伪装）”；恢复成功自动解除暂停续采。
- 全局看门每 12s 巡检，任何子页（含 iframe）平台失效都在外壳弹同一弹窗，手机端底部卡片适配。后端复用既有 /v4/adapters/recovery/* 与 /api/xhs/collect-health，未重造。浏览器真机 E2E：12 平台矩阵、A/B/C/恢复四态渲染、无 JS 运行错误；小红书持久 Profile 登录态只读探测 AUTH_VALID。


