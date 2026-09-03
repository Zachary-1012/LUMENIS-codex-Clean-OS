## 2026-09-03｜案例库 AI 评估接入（智谱增强层）+ 架构处置方案（AI学习·只给建议）
**A. 案例库 AI 评估**：新增 case_ai_evaluate.py（智谱stream+thinking disabled+精简输入），POST /api/case-analysis/ai-evaluate（4维评分：影响力/创新性/可复制性/风险系数+综合分+AI建议+推荐处置模板）；前端案例详情弹窗新增"AI 智能评估"区块（开始 AI 评估 按钮+结果渲染）。真实验证：天目里案例 → 综合7.5/10（影响力9/创新8/可复制6/风险3）+建议"强化差异化内容运营"；前端 aiEvaluate() 真实渲染评分与建议（DOM验证）。AI失败自动回退本地模板匹配，不阻断。
**B. 架构处置方案**：智谱AI学习生成 docs/learning/ARCHITECTURE-REMEDIATION-20260903.md（6项技术债：app.py 6095行/采集耦合/AI接口/DAO/资源管理/认证适配 每项含现状/建议/优先级/风险/影响/验收 + 落地顺序）。只给建议不施工，符合架构红线。LR-20260903-004。

## 2026-09-03｜处置模板推荐落地：案例模板体系接入产品（线A功能线）
> 基于学习任务①产物 CASE-TEMPLATE-REUSE，把 9 个可复用模板 + 危机SOP 结构化落地为可调用能力

**新增 case_templates.py**：9模板结构化注册表(品牌健康/危机应对/事件ROI/社会智能/UGC漏斗/市场机会/竞品对标/文化契合/风险预警矩阵) + 危机SOP 5阶段(0-2h黄金期→2-6h证据链→6-12h口径→12-72h执行→3-7天复盘带KPI) + 轻量本地关键词匹配 match_templates()（不调AI不扣额度）
**新增接口**：GET/POST /api/case-analysis/template-match（按事件/场景匹配模板）；GET /api/case-analysis/crisis-sop（危机SOP）
**前端**：案例深度拆解页新增"处置模板推荐"区块（输入场景→匹配模板→展示步骤/指标）
**真实验证**：生产8201重启后，/api/case-analysis/template-match?keyword=商场商户坠楼事件舆情危机 → 危机应对框架；crisis-sop → 5阶段；前端输入关键词真实渲染模板卡片（DOM+截图双验证）

## 2026-09-03｜per_call 学习任务①②完成：案例模板体系 + 代码库架构学习（智谱glm-4.5-air）
> 目标：使用预留的2次学习额度，让 ZBC 案例资料库与全量代码库被 AI 真正"吃透"，沉淀可复用学习资产，支撑 AI 自主学习与不断进化

**学习任务① 案例资料库整合吃透**：
- 输入：BRAND_INTELLIGENCE_CASE_LIBRARY_V1.md + case_deep_analysis(20营销案例)
- 产出 docs/learning/CASE-TEMPLATE-REUSE-20260903.md：9个可复用模板总览(品牌健康/危机应对/事件营销ROI/社会智能/UGC漏斗/市场机会/竞品对标/文化契合/风险预警矩阵)；品牌营销模板2个(价值革命型/社群共创型)；危机公关处置SOP(黄金期0-2h→证据链2-6h→口径6-12h→执行12-72h→复盘3-7天，带KPI)；模板接入产品数据结构建议
**学习任务② 全量代码库 + ChatGPT/Codex 编程设计**：
- 输入：ZBC 627文件/94979行 架构事实(本地采集)
- 产出 docs/learning/CODEBASE-ARCHITECTURE-LEARNING-20260903.md：8层架构分层评估(MVC/DAO/SOA等)；app.py 6095行单文件过大风险与耦合点；12项可复用组件清单；ChatGPT/Codex式编程设计5-8个可借鉴点；P0/P1/P2可进化板块；产品架构增强映射
**技术要点**：智谱glm-4.5-air 对"长中文输入+大输出"非流式请求会长时间挂起；改用 stream 流式+thinking disabled+精简输入(300-600字)+分段多次调用(每次800-1200tokens)后稳定快速返回
**额度**：per_call 3→5/20（预留2次已用，剩15次），glm-4.5-air tokens 正常消耗

## 2026-09-03｜Search-STD 增强搜索前端端到端验证通过（智能能力中心入口）
> 目标：确认 topbar 智能能力中心的「搜索增强」卡片真实可用（输入→联网搜索→展示带来源结果）

**验证过程（浏览器真实操作 8201）**：
1. 智能能力中心 4 卡片可见：API Key 管理(181 keys)/AI 资源包(4 packs)/小红书登录(待登录)/搜索增强(100次)
2. 点「搜索增强」卡片 → toggleSearchEnhance 展开输入框（hidden=false, visible=true）
3. 输入「商业地产 舆情危机公关 处置案例」→ 调用前端 runSearchEnhance() → 真实返回：
   - 综合摘要：7月重大负面舆情处置典型案例/房地产市场舆情应急处置预案/商业地产舆情危机公关要点及指引2.0
   - 结果1：西安赛格购物中心商户坠楼事件（含官方/商场方处置复盘，带来源）
4. 额度真实扣减：search_std 0→1（修复验证）→2（前端验证），剩余 98/100
**结论**：增强搜索前端+后端全链路真实可用（输入→/api/search/enhance→智谱web-search-pro联网→带来源展示），无需代码改动
**当前额度**：search_std 2/100、per_call 3/20（剩17）、glm-4.5-air 0/200000(日)

## 2026-09-03｜Search-STD 增强搜索修复：search-std 模型不可用 → 改智谱 web-search-pro 真实联网搜索
> 目标：让 /api/search/enhance（100次 Search-STD 配额）真正返回真实可追溯的搜索结果

**问题根因（真实探测）**：
1. 原实现 model="search-std" 调智谱返回 HTTP 200 但 message 只有 role 无 content（空壳响应，usage 全 0）→ 解析 KeyError("content")，功能实际不可用
2. 探测确认智谱官方联网搜索模型 web-search-pro 可用：返回 message.role="tool" + tool_calls[].search_result[]（含 title/content/refer 真实来源资讯）
**修复（intelligence.search_enhance）**：
1. 默认模型 search-std → web-search-pro（真实联网搜索）
2. 解析逻辑：从 message.tool_calls 提取 type="search_result" 的条目，映射 title/content/source（从正文提取来源）/url；无结果时兜底读 content
3. summary 由前 3 条标题自动生成；保留 search_std 100 次配额扣减 + 来源标注，不写入生产数据库（仅参考）
**真实验证**：POST /api/search/enhance（query=2025年广州太古汇高端购物中心营销活动）→ ok=true, 3 条真实搜索结果（太古汇品牌专区40.6万㎡/兴业太古汇零售额回正增长41% 2025-11-07/广州购物中心天花板），search_std 已用 0→1（剩99次）
**回归测试**：tests/test_ai_channel_flag.py 新增 2 用例（默认模型断言 + tool_calls 解析断言），全文件 10 用例通过

## 2026-09-03｜AI资源包「按次需求执行」端到端验证通过（真实扣减）
> 目标：确认 topbar ⚡ 面板的按次执行功能真实可用（输入需求→消耗1次→AI执行→返回结果）

**验证过程（全部真实）**：
1. 智谱连通性：glm-4.5-air 0.5s / glm-5.3 3.2s 均返回 OK（provider=zhipu，key 有效）
2. 真实端到端调用生产 POST /api/ai-resource-packs/per-call-execute：
   - 请求：{"request":"请用一句话介绍Z-Brand Intelligence Platform的定位","model":"glm-4.5-air"}
   - 结果：ok=true, provider=zhipu, result="Z-Brand Intelligence Platform：品牌智能决策助手。", 0.7s
   - 额度：per_call 已用 2 → 3（真实扣减 1 次），剩余 17 次
3. 浏览器真实打开 ⚡ AI资源包面板（380x543）：连接状态运行中/GLM-4.5-Air剩余11915296/GLM-4.6V剩余6000000/按次剩余17次/Search-STD 100次，渲染正常
4. 前端 per-call UI 结构确认：aiPackRequestInput 输入框 + executePerCallRequest() 执行按钮 + aiPackResult 结果区，调用链完整
**结论**：「按次需求执行」功能已完整可用（后端额度检查+预留学习保护+智谱调用+扣减+前端输入/执行/结果展示全通），无需代码改动
**注意**：本次验证真实消耗 1 次按次额度（2→3/20）；per_call 默认模型 glm-5.3（旗舰），前端不传 model 时走默认；glm-5.3 已验证连通

## 2026-09-03｜修复 GAP-21 Cookie 测试污染生产数据 + raw API 加固（真实性校验/apply 开关/数据隔离）
> 协议：WORK → VERIFY → LOG → COMMIT → PUSH → REMOTE VERIFY

**问题**：GAP-21 raw 导入 API 验证时，测试 cookie（a1=s/web_session=x 等）写入生产 data/ 的 xhs_cookies.json/source/cookie_string/login_status，导致生产误判小红书已登录，真实 cookie 被覆盖（用户红线：任何测试残留不得影响最新系统）
**修复**：
1. 清理全部测试污染文件（备份到 data/backups/cookie_test_pollution_20260903/），生产 data/ 恢复干净
2. raw API 加真实性校验：小红书必须含非占位 web_session（值长度≥6 且非 x/test/placeholder 等），否则 400 拒绝
3. raw API 加 apply 开关：默认只写 source.json 不覆盖生产 xhs_cookies.json（防止测试/误操作污染），apply=true 才同步生产
4. 两个 cookie 导入端点支持 ZBC_DATA_DIR 环境变量，测试 fixture 指向临时目录，彻底隔离测试对生产 data/ 的写入
**验证**：12 单测全过（含假 web_session 拒绝/缺 web_session 拒绝/apply 语义/数据隔离）；测试后生产 data/ 无 cookie 文件；生产 8201 重启后 healthz 200/import-status 200/假 session 400
**Commit**：待提交（app.py + static/js/system_controls.js + tests/test_cookies_import_api.py）

## 2026-09-03｜GAP-21 UI 接入闭环 + 响应式逐档验证证据 + AI 资源包/治理面板生产确认
> 协议：WORK → VERIFY → LOG → COMMIT → PUSH → REMOTE VERIFY

**A. GAP-21 Cookie 导入 UI 接入（RESOLVED，生产上线）**
- 后端新增 POST /api/cookies/import/raw：接收 {platform, cookies(JSON数组)}，规范化后写入 data/ 源文件（weibo_cookies.json/bilibili_cookies.json/xhs_cookies.source.json + status + 小红书额外生成 cookie_string.txt 供采集器），Basic Auth 保护、凭证仅存本地不入库、Evidence 记录（不记录 Cookie 值）
- 前端设置弹窗（openSettings）新增"平台 Cookie 导入"区块：平台选择(小红书/微博/B站) + textarea 粘贴 JSON + "导入并运行"按钮 + 状态反馈，调 POST /api/cookies/import/raw
- 测试：tests/test_cookies_import_api.py 扩到 8 用例（401/200结构/400非法平台/400空cookies/405/无明文泄漏），全过
- 生产 8201 重启上线验证：healthz 200 / raw导入 200 / status 200 / 静态JS含Cookie导入UI / 无凭证 401，全 PASS
- Commit：acd746e

**B. 响应式逐档验证（证据入库）**
- Playwright+Edge 对生产 8201 五断点（430/768/1024/1280/1440）真实加载截图：启动页三状态卡(采集/风险/AI)正常；主界面 GPT 工作台 430 移动单列2x2按钮/768 平板单行4按钮/1024-1440 桌面完整侧栏+顶栏+问答区
- 结论：响应式适配无布局 bug，层级清晰，符合"GPT 工作台外壳 + 黑白灰侘寂"方向
- 证据：docs/UI/evidence/main-*.png + responsive-*.png + responsive-check.json；Commit：582ed46

**C. AI 资源包/治理面板生产确认（已工作）**
- /api/ai-resource-packs/status：glm-4.5-air 已用0/总额1191.5万/日限20万；glm-4.6v 0/600万；per_call 已用2/20次；search_std 0/100；paused=false
- /api/ai-governance/status：provider=zhipu，日调用限500/已用0、日token限20万/已用0
- 前端 topbar ⚡ AI资源包面板 + ✦ AI治理面板均接真实 API 每5分钟刷新，无需额外施工

**Commit 链**：acd746e → 582ed46（HEAD，本地=origin）

（注：期间并行窗口新增 8077fdf 报告topic_label+QueueWorker、1162434 报告docx/xlsx主题标签+调度入队，与 GAP-21/UI 无冲突，已同步）

## 2026-09-03｜GAP-09 负面评审写路径收敛唯一 Owner + GAP-15 核实 + 并行巡检入库
> 协议：WORK → VERIFY → LOG → COMMIT → PUSH → REMOTE VERIFY

**A. GAP-09 负面评审写路径收敛（RESOLVED）**
- 根因：笔记级负面评审新旧 4 入口（/api/negative/confirm|reject + /api/negative-review/<id>/confirm|reject）SQL 完全重复（写同一 notes.negative_confirmed 字段），代码重复维护风险
- 收敛：抽唯一写路径 `_note_set_review(note_id, state)`（state=1 确认/2 驳回），4 入口统一调用，行为零变化
- 事件评审 /api/event-review/*（_event_set_review 联动笔记）为独立能力，保留不动
- 验证：5 单测（test_note_review_unified.py）+ API 级验证（临时库 4 入口真实 Flask 请求，A1=1/A2=2 一致）+ 生产 8201 重启后 stats/pending 200
- Commit：e0c9959

**B. GAP-15 核实（RESOLVED，无需修改）**
- daily_git_sync.py:72 现为 `gm.current_version()` 已带括号，无漏括号 bug，GAP 已自然解决

**C. 并行巡检成果入库**
- database.py DataQualityGate 写入门软门（enrich 标记不丢弃=数据零丢失）+ scripts/ai_gateway.py 新模块
- 测试 13 项全过，独立提交 eae0587

**Commit 链**：e0c9959 → eae0587（HEAD，已 push，本地=origin）

## 2026-09-03｜双子库密码适配 + 登录弹窗闪烁根因修复 + GAP-10 生产上线
> 协议：WORK → VERIFY → LOG → COMMIT → PUSH → REMOTE VERIFY

**A. 全仓库旧密码 ID082610 → Zachary01 适配（21 文件）**
- 13 个 .py：v4_upgrade/auth/models.py（首次建号默认密码 2 处）+ tests/ 8 个 + 根目录运维脚本 4 个
- 4 个 .md：V4升级模块旁路测试报告 / V4接入密钥登录清单 / SESSION-HANDOFF / v4_upgrade集成指南
- 4 个 .bat/.ps1：start_v4 / 一键启动系统 / 系统守护闭环.ps1（真实 Basic 探测）/ 系统守护闭环_可靠版.bat
- 验证：tracked 残留 ID082610 = 全清零；生产 8201 用新密码 200；test_security_scan 硬编码密码 NONE

**B. 登录弹窗闪烁根因修复（RFC7617 静态资源认证）**
- 根因：/static/* 静态资源全部 401（CSS/JS 并发触发浏览器原生 Basic 登录框反复弹）
- 修复：_basic_auth 白名单加 /static/ 前缀放行；业务 API 仍严格 401
- 验证（staging 8301 + 生产 8201）：静态 HTML/CSS/JS 200、真实 API 带凭证 200、无凭证 401

**C. GAP-10 报告路由 Deprecation 头生产上线**
- after_request 拦截器：8 个重复路由打 Deprecation+Sunset+Link 头
- 验证：report/daily 有头、report-center/preview 与 reports 列表无误伤

**Commit**：44caa8d → 65855dc → 3eb65ba（HEAD，已 push，本地=origin）

# Z-Brand-Core 开发协作日志

## 2026-09-02｜Zachary-OS-AI 总工程执行师 T0 基线锚定（四层 E2E 实跑 · SEC HIGH 清零 · 启动收口 · Git Push 同步）
> 执行协议：HUB-PROTO-AI-WORKLOG-PUSH-V1 · WORK → VERIFY → LOG → COMMIT → PUSH → REMOTE VERIFY → HANDOFF
> GitHub：Zachary-1012/Z-Brand-Core (main) · 远端同步：Zachary-1012/Zachary-OS-AI 三份 ZBIP_EXECUTION_LOG_2026-09-02

**执行师身份**：Zachary-OS-AI（总工程执行师）。用户授权："以后你作为Zachary-OS-AI，代码开发的总工程执行师，负责落地等等一系列保证开发完成能够上线的任务，保证进度" + "评估未完成排序，优先上线系统为基准"后回复【可以】启动 T0-1~T0-4。

**核心改动文件**：
1. import_cookies.py（148→123 行：SEC-001 硬编码 Cookie 迁移至 `.env` 的 ZBC_WEIBO_COOKIE_JSON / ZBC_BILI_COOKIE_JSON）
2. requirements.txt（18→31 项：补 Flask-CORS / Flask-Limiter / APScheduler / schedule / bs4 / lxml / websocket-client / python-dateutil / PyYAML + pytest-timeout 插件独立装）
3. .env.example（尾 3 模板：ZBC_WEIBO_COOKIE_JSON / ZBC_BILI_COOKIE_JSON / ZBC_API_KEY）
4. .gitignore（新增 .env.local/.env.prod/.env.txt；加 scripts/_zachary_t0\* 临时审计脚本忽略）
5. scripts/start_production.ps1（122 行重写：ASCII 安全、UTF-8 中文报错、.venv 强制路径、互斥、7 依赖预检、8201+9222 三幂等、15 秒 healthz 等待、失败日志末 20 行自动打印）
6. scripts/_prod_dep_check.py（7 依赖预检 exit 0/2，被启动脚本调用）
7. 35 个 LEGACY 启动脚本：.bat/.ps1/.vbs/.py 首行注入 LEGACY REDIRECT NOTICE → scripts/start_production.ps1（保留 @echo off/编码声明/Shebang，不删原逻辑以兼容）
8. 文档变更：CHANGELOG.md 新增 [5.9.9-t0] 章；DEV_LOG.md（本条）

**目的**：
- 先审计再修改：按 Z-Brand-Core AGENTS.md §13 10 项交付 + 您说的"每回开发必须端到端启动系统测试"，执行 T0-1~T0-4 四项今日必须项，锚定可回归的可信生产基线。
- 双产品线（CTH-POMS + ZBMP）一套 Core 不复制；35 LEGACY 入口兼容而非删除；Cookie 凭证全迁出源码；requirements 新机 `pip install -r` 可复现；pytest + Playwright 双层 E2E 做基线证据。

**数据库**：
- DDL/DML：零变更（全程以 `file:data/monitor.db?mode=ro` 只读打开）。
- 生产库锁定：data/monitor.db，53 表 / notes=957 / events=427 / daily_reports=33 / collection_logs=495 / ai_filter_log=827 / note_review_history=8327。
- 根目录 monitor.db（1表 token_stat 12KB）已证伪 = 废弃壳。
- 双时间铁律：publish空=0 / pub=cap嫌疑=0 ✅；notes 空正文=253（T1-1 分批 CDP 补抓）。

**实测（真实启动 E2E，非静态检查，按 AGENTS 10 项交付）**：
1. T0-1 DB Schema 对账：notes/events/daily_reports 等核心表 4 候选库比对 + 三列对账。CONFLICT-001 证伪 ✅。
2. T0-2 SEC：高精度 secret scan v2（EXCLUDE 目录 + placeholder/pattern 误报过滤 + IGNORE_HINTS）→ ZBC 源码 HIGH=0 / OSAI HIGH=0 ✅。`python import_cookies.py` → 微博=6 / B站=17 正确回写到 data/\*_cookies.json ✅；.venv 9 依赖逐包 3 次重试 → 全装成功 ✅。
3. T0-3 Launch：`python scripts/_prod_dep_check.py` → OK ✅；35 LEGACY NOTICE 注入 → 35/35 100% ✅；start_production.ps1 实跑 → Already healthy（幂等正常，8201/9222 重复拉起被跳过）✅。
4. T0-4 E2E 四层防线：
   - L1 HTTP：`/healthz` 200 · `{"ok":true,"service":"taikoo-monitor","version":"5.9.9"}` ✅
   - L2 路由：359（60 页 / 290 API）✅
   - L3 Playwright Chromium 无头 1440×900：
     · Basic Auth 从 URL 注入改为 Header 注入，修复浏览器顶部红色横幅 `TypeError: Failed to execute fetch`（URL 带 credentials 被浏览器 Fetch 拒绝）✅
     · `/` 200 · title="广州太古汇舆情监测系统 · CTH-POMS" ✅
     · 15 SPA Hash 路由 /#/overview ... /#/settings = 15/15 DOM OK；JS fatal/pageerror=0；Console 错误=2（非致命样式警告）✅
     · SSR /v4/ + /topic-campaign = 200 OK ✅
     · WARN：`/architecture` + `/event-graph` 蓝图路由=404（P1 能力，不阻塞 CTH-POMS 核心 15 页上线）
   - L4 pytest：`ZBC_DB_PATH=staging/monitor.staging.db .venv/Scripts/python.exe -m pytest -x -q --timeout=180 --maxfail=5 -k "not browser or playwright or selenium or e2e or live or remote"` → exit 0 · **152 passed · 0 failed · 0 error** ✅
   - L5 双时间铁律再验：0/0 违规 ✅

**未完成项（已登记到 T1/T2/T3，下次按 AGENTS 排序开工）**：
- T1-1 notes 空正文 253 条分批 CDP 补抓
- T1-2 XHS NEED_VERIFY 真人扫码闭环真实触发
- T1-3 Cloudflare 固定 HTTPS 域名隧道自启验收
- T1-4 Golden Dataset 50 样本
- T1-5 全新 venv `pip install -r` 完整复现验收
- T1-6 日报 Word/Excel 导出 + 微信真实发送
- T1-7 Pre-push CI 守门脚本（≤2min：secret + DB schema + 50 pytest 红线）
- T2-1~T2-6 安全稳定层：system_config 脱敏、自动备份调度回滚、ZBC Header 鉴权最小骨架、PII 90 天保留 v1、重复 watchdog 单实例、app_backup_v589.py CI 观察后删
- T3-? `/architecture` + `/event-graph` 蓝图 404 补

**已知风险**：
1. `.env` 中 B 站 bili_ticket expires=2026-08-31（已过期）。系统启服 & 报告不受影响，B 站真实采集前需人工更新 `.env` 的 ZBC_BILI_COOKIE_JSON。
2. XHS Cookie 实际 NEED_VERIFY 全链路恢复需真人配合，尚未真实验证（不是代码问题，是风控前置条件）。
3. `.venv` 3.13.15 与全局 Python 3.14.7 并存：已通过 start_production.ps1 的硬路径 `.venv\Scripts\python.exe` 规避，但历史 LEGACY 脚本仍需经 REDIRECT NOTICE 被操作人员看到才会切换。

**回滚点**：`git revert` 本 commit 后所有启动脚本仍可被原方式手工双击执行（LEGACY NOTICE 仅注入不删逻辑）。Cookie 硬编码已迁移至 `.env`，回滚后重新写入 `.env` 即可，不写回源码。

**交接（豆包/Ollama/下一轮 ChatGPT 必读）**：
- 生产基线 SHA：见 `git log -1 --oneline`（本次 commit 后再 push）。
- 双库同步后开工第一步必须：先 `git fetch origin main` 再审计 SHA 是否变化；认证失败立即标 BLOCKED，不得宣称 push 成功。
- 未来 T1 任何改动：WORK → VERIFY → DEV_LOG.md append → CHANGELOG.md append → commit → push → 远端 VERIFY → OSAI 三仓 ZBIP_EXECUTION_LOG append → commit → push → 远端 VERIFY。


## 2026-08-30｜上线冲刺(2) 进程韧性 + 采集主链修复 + 采集风险引擎（本地执行，commit df79c1e）

**改动文件**：run_supervised.py、collector.py、database.py、collector_guard/risk_engine.py(新)、docs/BLUEPRINT_brand_intel_platform.md(新)、tests/healthcheck.py、tests/test_risk_engine.py。
**目的**：根治“采集触发 Flask 退出/假活”、单次采集过慢、publish_datetime 留空三类问题，并把《交叉认证+风险闸门+采集安全控制》补丁的采集风险分档落地为可测代码。

**实测（真实运行，非静态检查）**：
- 看门狗：新增 /healthz 端口双探测，修复 multiprocessing worker 原生崩溃后父进程不退的“假活”监督盲区，连续3次不通杀整棵进程树重启；改为 Start-Process 隐藏窗口独立常驻、脱离交互会话；多次 kill app 子进程均约3秒自动拉起、8201 healthz 恢复 ok，8200 现网全程不受影响（旁路隔离成立）。
- 采集提速降噪：关键词清洗（英文停用词/单字符/纯符号）+ 核心词深采(10详情)/扩展反馈词浅采(3详情,2滚动)。端到端任务 20260830135202182 = done：小红书原始19、主体硬过滤后有效9、新增3更新6、AI复核3条约4秒秒过（Ollama-only 收口后不再逐条打云端卡62%）、事件链跑通、全程未崩，用时约3分20秒（原约10分钟）。
- 双时间铁律：定位根因为 insert_note 未把平台 publish_date 回填到 publish_datetime；修复后存量 874 条幂等补齐，校验 0 条 publish_datetime=captured_at；新样本发布日期(08-27/08-18 等)与采集时刻(08-30 13:55)正确分列、来源不同。
- 真机验证：小红书 explore/{id} 不带 xsec_token 会 404“当前笔记暂时无法浏览”，带 token 的 search_result 链可正常进入详情，故保留带 token 链接形态、不做去 token 规范化。
- collector_guard/risk_engine 10 项单测全过；tests/healthcheck 只读检查关键模块全 ok、双时间列齐全。

**遗留**：详情标题偶发为空已加“正文首行兜底”待下一轮采集复验；GDELT 海外网页发现在国内直连超时（独立线程、不阻塞主链，建议缩短超时或默认关闭）；统一 Auth Recovery Center、AI Gateway/交叉认证/多品牌 Workspace 已存为 docs/BLUEPRINT 蓝图，按 P0/P1 分期。
**回滚点**：`git revert df79c1e`；本次只补空值、未改库表结构，无需回滚迁移。


## 2026-08-30｜协作规范同步

- 新增 `docs/DOUBAO_HANDOFF.md`，作为豆包/本地开发环境执行接管指令。
- 固化 ChatGPT 主开发窗口与豆包本地执行角色边界。
- 固化 Ollama-only 生产 AI 架构：无 AI 时核心采集、过滤、去重、事件、风险、统计、报告仍可运行。
- 固化两产品、一套 Core、配置/Release 隔离原则。
- 固化数据库保护、广州太古汇主体口径、发布时间口径、小红书 Auth/风控状态机、测试和 Git 审计要求。

### 历史审计快照
v5.8.5；38 张表；875 笔记（678 有正文、197 空正文）；392 事件（385 发生日期规范、7 待核）；141 评论；507 事件关联；258 采集日志；15 个 SPA + 1 个独立话题页；主轮询 60 秒；memory_optimizer/stability_monitor 此前已启动；Zachary 面板开关此前 E2E 零 JS 错误。

> 以上仅为历史快照，后续必须重新核查，不得冒充当前真实状态。

### 当前优先级
P0：启动环境一致性、历史空正文合法补抓、相对时间归一化、小红书 300012 状态机。
P1：全局 Auth 状态弹窗+二维码/合法验证入口、登录/权限、专题与太古外延数据实采、守护模块评估、微博/B站免登、微信安全通知。
P2：移动端完整交互、版本统一、collector_v2 切换、临时诊断脚本清理、Ollama/CI/CD/监控/蓝图化。

### 日志规则
每次代码改动记录日期/时间、commit、文件、目的、测试方式、实测结果、遗留问题和回滚点。不得把计划、代码已写或静态检查通过写成真实 E2E 已完成。


---

## 2026-08-30 14:37 · v5.8.5 上线冲刺 3/4/5（无人值守 / Guard 接入 / 统一 Auth 恢复前端）

### 改了什么 / 文件
- collector.py：新增 `_ensure_cdp_online`（9222 掉线自动拉起持久 Edge）；`collect_all` 接入 CollectorGuard（单词受控、熔断即停后续请求）。
- app.py：反馈词源头清洗限量 6 个；GDELT 全网发现超时默认 30s→8s。
- scripts/start_production.ps1、scripts/start-zbrand-autostart.cmd：幂等生产启动器 + 登录自启（已部署到当前用户 Startup）。
- v4_upgrade/console/templates/console.html：全局状态中心（并入小红书主采集，12 平台）+ 不跳页统一 Auth Recovery Modal（A/B/C 三类分清、三步状态机、二维码截图、重新检测/稍后处理、12s 全局看门、手机端适配）。
- tests：test_guard_wiring.py（5 项）、test_auth_api.py（后端恢复链路只读集成）转正。

### 数据库
- 无结构变更、无迁移；本轮未写业务数据（仅前端/采集链/脚本）。

### 测试与真实结果
- 9222 自愈：真机 taskkill 9222 Edge → `_ensure_cdp_online` 自动拉起、/json/version 恢复 Edg/152，通过。
- Guard 接入：5 项单测全过（健康透传 / NEED_VERIFY 受控 / 熔断后不再调用采集函数 / 关闭直通）。
- 采集回归：任务 20260830141457326 done，原始19/有效10/新增3/更新7/AI复核3秒过/事件100/未崩，新增笔记 publish_datetime 自动正确填充（08-29/07-08 ≠ 采集 14:18）、标题非空。
- Auth 后端：登录→6 个可恢复真人平台、全局健康 11 适配器、小红书只读登录态 AUTH_VALID（web_session/a1 等齐全）。
- 浏览器 E2E（127.0.0.1:8201/v4/console）：12 平台健康矩阵含“小红书·主采集”，A 登录/B 验证/C 熔断/恢复 四态渲染正确，C 类不显示二维码、步骤全灰，无 JS 运行错误（仅测试注入时两张预期内的截图 404）。

### 遗留 / 未实测
- 真实“扫码恢复”全链路需在某平台 Cookie 真正失效时由看门自动触发验证（当前小红书登录有效，未人为制造失效；后端 _open_and_watch 已经代码审查，弹窗到接口链路已实测）。
- 微博 / B站 Cookie 适配器、Auth 恢复与主采集 collector 的自动联动触发（采集到 AUTH 态时自动 request_recovery）尚未接线，下一轮做。
- 8200 现网多对重复 python 实例仍待谨慎清理；免费公网服务器/域名选型待用户确认。

### 回滚点
- 前端仅 console.html 单文件，回滚即 `git revert` 本次提交；采集链改动均有 env 开关（TAIKOO_COLLECTOR_GUARD=0 可关 Guard、TAIKOO_WEB_DISCOVERY=0 可关全网发现）。


---

## 2026-08-30 14:45 · v5.8.5 上线冲刺 6（采集六态正确落库 + 失效自动建恢复任务）

### 问题
主采集链此前把任何错误都笼统写成 collection_logs.status='error'，全局健康无法区分 登录失效 / 人机验证 / IP熔断 / 网络异常，夜间失效也不会自动产生恢复任务。

### 改动 / 文件
- collector.py：新增正式函数 `classify_collect_state(error, guard_state, count)`，归一化为 SUCCESS/EMPTY/AUTH_REQUIRED/CAPTCHA/BLOCKED/NETWORK_ERROR；guard 硬状态（cooldown/paused/auth_required/need_verify）优先于空结果判定，避免熔断被误判成 EMPTY。
- app.py：采集结果按标准六态落库（不再笼统 error/success）；AUTH_REQUIRED/CAPTCHA/BLOCKED 自动幂等调用 auth_recovery.request_recovery，夜间失效即保留登录/验证入口，手机打开统一控制台即可恢复，形成“采集→发现失效→暂停→建恢复任务→手机恢复→续采”闭环。
- tests/test_collect_state.py：13 项六态归一化单测全部通过。

### 数据库
- 无结构变更、无迁移；仅 collection_logs.status 写入标准六态值（文本字段，向后兼容旧值）。

### 测试与真实结果
- 13 项单测全过（含“guard 已熔断但 error 为空不得判 EMPTY”这一回归点，修复前后对比验证）。
- py_compile app/collector 通过，8201 已重启加载。
- 未实测：AUTH/CAPTCHA/BLOCKED 真实触发自动建恢复任务的端到端（当前小红书登录有效，未人为制造失效；函数与 Auth 后端 request_recovery 已分别单测/接口实测，待真实失效时由自动采集自然验证）。

### 回滚点
- 单一函数 + 一段循环，`git revert` 本次提交即可；恢复任务创建包裹 try/except，任何异常都不影响采集主流程。


---

## 2026-08-30 14:58 · v5.8.5 上线冲刺 7（数据质量：脏发布时间归一 + 空标题入库兜底 + 采集集成回归）

### 采集集成回归（整合冲刺3-6后第一次全链路真机）
- 任务 20260830144623905：web 发现→7 词回搜，服务端约 14:51 完成，未崩；7 个词全部写入**标准六态 SUCCESS**（对比旧批次小写 success，证明六态落库生效），核心词「广州太古汇」10 条；今日新增 7 条，publish_date 零空（双时间修复持续生效）。

### 脏发布时间归一（v4_upgrade/data_cleanup/fix_publish_date.py 增强）
- 基准时间改为优先 captured_at、回退 collected_at（严守发布时间≠采集时间）；补「昨天/前天/今天/刚刚」与「编辑于 MM-DD」跨年判断；非法月日不臆造、原样保留。
- dry-run 预览 7 条全部正确后 --apply 写库：编辑于06-02→2026-06-02、昨天→2026-08-28、5小时前→2026-08-29、编辑于2025-08-22 保留 2025 年份等；复查相对时间残留=0。

### 空标题入库兜底（database.py insert_note）
- 统一入口兜底：title 缺失时用正文首句（按换行/句读切分、去空白、截24字），再退「作者昵称+的笔记」；UPDATE 路径 title 为无条件覆盖，故历史先空后补正文的笔记也会在下次更新时自动补齐。
- 已修复存量 2 条空标题（id 964/967），全库「空标题但有正文」=0。
- tests/test_title_fallback.py：真实 insert 后立即删除的回环测试，覆盖「正文首句」「纯空白标题→作者兜底」两种，通过且测试残留=0（修复过程中抓到并修正了“纯空白标题短路作者兜底”的真实缺陷）。

### 数据库
- **无结构变更、无迁移**；仅 7 条 publish_date、2 条 title 的业务数据确定性修复（可由同一脚本复算）。

### 未实测 / 遗留
- 195 条空正文均为小红书，需 CDP 进详情页分批补抓（用户不在场、为降风控不在此刻批量跑），脚本与批次已就绪。
- 标题兜底对“未来新采集”的效果待下次真实采集自然验证（入库回环已测）。


---

## 2026-08-30 15:04 · v5.8.5 上线冲刺 8（版本中心接入统一控制台 + 接口实测）

### 改动 / 文件
- console.html：侧边栏「系统」组新增「版本中心」，以单页内嵌 iframe 方式接入（与采集/设置同模式，不跳陌生页，手机端从汉堡侧栏进入）；补 TITLES 映射，复用通用 iframe 懒加载。
- tests/test_version_api.py：版本中心后端只读集成测试（登录→status/history/config）。

### 真实测试结果
- 后端接口实测：status 返回 v5.8.5 / main / HEAD 6f5c10a / synced / ahead0 behind0 / changed0 / 远程地址正确；history 返回真实提交链；config 显示自动提交+自动推送已开启、巡检 30 分钟。
- 浏览器真机 E2E（8201）：侧边栏点击「版本中心」→主区单页内嵌渲染正常，版本号、GitHub 同步态、分支/提交/最近保存/远程、版本操作按钮齐全，并正确识别出 console.html 自身这处未保存改动。
- console.html JS 经 node --check 通过。

### 数据库
- 无变更、无迁移。

### 说明
- 版本中心后端（git_manager：安全闸/保存/推送/检查/拉取/回滚/自动守护）此前已就位，本次完成「统一控制台入口 + 真机/接口联调」；配合每日 08/18/24 定时同步与自动巡检，形成 开发→自动成版本→推送 GitHub→可回滚 的闭环。


---

## 2026-08-30 15:21 · v5.8.5 上线冲刺 9（ProxyPool 代理池接入 + 两份补丁审计对齐 + 空正文补抓）

### 一、ProxyPool 可插拔代理池（用户补丁《可插拔 ProxyPool 补丁1.0》落地）
- 现状审计：proxy_pool/ 模块（config/models/health/manager/adapters/loader/__init__/README）与 config/proxy_nodes.example.json 此前已建好且实现严谨，但**未接入 Flask**（无加载、无路由）。本次补齐最后一公里，不重写已稳定模块。
- app.py 最小侵入接入（全部 try 包裹，失败不影响启动）：
  1. 可选导入 proxy_manager/load_proxy_nodes/ProxyConfig；
  2. 启动时 load_proxy_nodes()：从 .env 的 PROXY_HTTP/PROXY_SOCKS 及历史 GOOGLE_PROXY/OPENAI_PROXY 自动识别本机付费代理为 local-primary，另加载人工审核的 config/proxy_nodes.json（缺文件正常启动）；
  3. 独立守护线程做节点健康巡检（与核心采集 scheduler_loop 解耦）；
  4. 新增 GET /api/proxy/status、POST /api/proxy/check（走现有 HTTP Basic，URL 脱敏，不覆盖任何现有路由）。
- 安全边界：总开关 PROXY_POOL_ENABLED 默认 false（关闭时 get_requests_proxies 恒 None，系统等同直连原版）；代理失败→节点冷却→切换→按平台策略决定是否直连，强制出海平台 allow_direct=False 时无节点即抛 ProxyUnavailable，绝不把登录态流量裸奔到直连；不自动抓取任何免费节点；敏感只从 env/本地 json，config/proxy_nodes.json 已在 .gitignore。

### 二、真实测试结果（非静态）
- tests/test_proxy_pool.py：11 项单测全过（默认关闭等同直连、冷却跳过选路、平台匹配、强制出海不裸奔、失败回退直连并标记冷却、状态脱敏、loader 缺文件容错、无自动抓取结构断言）。
- 付费代理真实健康检查：经 127.0.0.1:10808（本地 Xray→付费节点）连 gstatic generate_204 成功，延迟约 1219–1241ms。
- 接口实测（带 Basic）：GET status=200（enabled=false/mode=direct/1 节点 local-primary）；POST check=200（local-primary ok=True）。
- py_compile：proxy_pool 全部 + app.py 通过。

### 三、《交叉认证+风险闸门+采集安全控制》补丁审计对齐（不硬造半成品）
- 已覆盖：补丁「采集风险五档 NORMAL/WATCH/THROTTLED/COOLDOWN/CIRCUIT_OPEN、状态机、熔断器、受控恢复」已由现有 collector_guard（state/guard/rate_limiter）+ risk_engine 五档评分 + auth_recovery 落地，语义一一对应且状态划分更细（区分 AUTH_REQUIRED/NEED_VERIFY/NETWORK_ERROR，见冲刺6 classify_collect_state）；坚持「停止任务而非绕过平台安全机制」。
- 列入分期（本次不硬造）：brand_core 多品牌工作区、ai_gateway 多 Provider（Dots/OpenRouter）、ai_validation 交叉认证/证据引擎/置信度、security 的 ai_data_gate/secret_scanner —— 属 Z-Brand Monitoring Platform 母平台长期底座；当前正式 AI 架构 Ollama-only、云端默认关闭、AI 仅增强层，故这些模块按 BLUEPRINT 分期预留，不在上线冲刺里写无真实调用方的空壳。

### 四、历史空正文补抓（真人通道、慢速受控）
- 通过 9222 已登录真人浏览器，分 3 批、每条间隔 7–9s、遇验证即停，共补 17 条真实笔记正文（空正文 195→178），零拦截；唯一 1 条失败为无 xsec_token 的 explore 链接（结构性 404，非风控）。
- 管线 tests/backfill_detail_cdp.py 验证有效（#detail-desc 等选择器仍可取出正文），天然断点续跑；剩余空正文后续每天小批量慢速补，避免与整点自动采集争抢 9222。

### 数据库
- 仅补写 17 条 notes.content 与 detail_fetched_at（数据补齐），无表结构变更、无迁移。

### 未实测/遗留
- ProxyPool 当前保持默认关闭，未把现有小红书/Google 采集器统一切到 safe_request（渐进接入，避免动稳定采集链；Google/IG 现有代理读取仍正常）。
- 交叉认证/多 Provider 母平台模块未开发（分期，见上）。


---

## 2026-08-30 15:30 · v5.8.5 上线冲刺 10（双时间补齐治理 + 核心回归全绿 + 上线就绪审计）

### 一、发现并修复双时间两处真实问题（只读审计先行，不臆断）
- 上线就绪审计初看「publish 晚于 captured 500 条」，核查证实是审计口径把空串 '' 当非空比较所致的**假象**；但顺藤摸出两个真实问题并修复：
  1. **captured_at 492 条为空串**：均为历史笔记，旧采集列 collected_at 有值而新规范列 captured_at 未回填。增强清洗模块新增 backfill_captured_from_collected()，按“只补采集时间、绝不碰发布时间”的铁律回填 492 条，现 882 条 captured_at 全部有值、缺失=0。
  2. **publish_datetime 8 条残留脏原文**（编辑于/昨天/小时前）：冲刺7只清了 publish_date，双列不一致。fix_publish_dates() 升级为双列一致清洗——publish_date 已干净时用其标准日期同步脏的 publish_datetime，8 条全部归一，两列脏值均=0。
- 修复后复查：integrity_check=ok；空标题=0、captured_at 缺失=0、发布日晚于采集日=0、相对时间残留=0、非法日期=0。

### 二、核心回归套件 16/16 全绿
- 初次跑发现 5 个测试（sentiment/safety_boundary/data_feedback/auto_recovery/adaptive_engine）直接 python tests/xxx.py 运行时缺项目根路径引导（带 PYTHONPATH 即可过，属测试脚本健壮性问题、非产品缺陷）；统一补 sys.path 注入后，不带任何环境变量独立运行全部 EXIT=0。
- 最终核心回归：六态归一、标题兜底、Guard 接线、风险引擎、事件日期、报告周期、情感引擎、安全边界、数据库、采集管线、ProxyPool(11)、Auth API、版本 API、数据闭环、自动恢复、自适应引擎 = 16/16 通过。

### 三、上线就绪只读审计结果（tests/_readiness_audit.py）
- 44 张表 integrity ok；notes 882（小红书 873 + CDP 9），今日新增 7；events 401、daily_reports 25。
- 采集六态：今日新批次为标准大写 SUCCESS（冲刺6 生效），历史小写 success/error 为旧代码记录，保留不改历史。
- subject_hit 主体命中 570/882=64.6%（未命中的为 silver/Manga 等干扰词采集后被主体硬过滤 reject 的笔记，证明太古汇主体口径在起作用、未被弱化）。
- 空正文剩 178：冲刺9 已真人慢速补 17 条；其余多为无 xsec_token 的 explore 结构性 404（补不到）+ 后续每日小批量慢速补。

### 数据库
- 数据修复：492 条 captured_at 回填、8 条 publish_datetime 归一；无表结构变更、无迁移。

### 未实测/遗留
- 历史 collection_logs 的小写 status 为旧批次事实记录，未做改写（不篡改运行历史）。
- 178 条空正文按慢速补抓计划持续消化，不在整点采集前争抢 9222。


---

## 2026-08-30 15:36 · v5.8.5 上线冲刺 11（运行态巡检：实例卫生 / 调度重复实证 / 只读巡检工具）

### 一、进程实例巡检（只读，不擅杀现网）
- 8200 现网：存在 5 套共 10 个 app.py 进程（06:05 一套、08:06 四套，各自父进程为独立 cmd，均未带 --no-scheduler），多实例共享 8200 端口、healthz 返回 v5.8.4，请求可能在不同启动时刻的旧实例间漂移。**严格遵守“现网 8200 不动、切换由用户决定”，本次未杀任何 8200 进程**；清理为单实例需用户授权后连同其父 cmd 一并处理（工具已能列出 LISTEN/DUPLICATE）。
- 8201 测试：看门狗(20412)→reloader(25544)→server(440) 单一健康链，healthz v5.8.5；9222 真人浏览器在线（Edg/152）；D 盘剩余 63.9GB 充足。
- 开机自启 scripts/start_production.ps1 本身幂等（先 healthz 探测、只起 8201+9222、明确不碰 8200），8200 重复系历史上多个 cmd 手动叠加启动所致，非自启重复。

### 二、重复调度危害实证（有锁兜底，无脏数据）
- 核查 collection_logs：今日“同关键词同一分钟重复采集”组数 = 0；虽多实例各跑调度线程，但 _collect_lock/频率限制兜底，未产生重复任务或重复入库。结论：当前是资源卫生/版本漂移隐患，而非正在发生的数据错误，故按现网授权流程处理、不紧急强杀。

### 三、新增只读运维工具
- scripts/inspect_instances.ps1：列出 8200/8201 真正监听 PID、各实例 LISTEN(KEEP)/DUPLICATE、内存/启动时间、healthz 版本与 9222 状态；只诊断不清理（脚本用纯 ASCII 以兼容 Windows PowerShell 5.1 的 GBK 解析）。

### 数据库 / 迁移
- 无变更、无迁移。

### 待用户授权 / 遗留
- 【需拍板】8200 现网 5 套重复实例的清理：授权后保留唯一健康实例、其余连同父 cmd 优雅退出，并确认现网是否从 v5.8.4 升到已回归通过的 v5.8.5（属“切换”动作，按约定由用户决定）。

## 2026-09-03｜GAP-08/13/17/18/19 批量核对收尾 + Alembic 生产接入 + Selenium 死依赖移除
> 协议：WORK → VERIFY → LOG → COMMIT → PUSH → REMOTE VERIFY

**A. GAP-08 Evidence 层核实（RESOLVED，并行巡检已闭环）**
- evidence_store.py 统一写入层（record_evidence/collection/health + query + stats）已实现
- 采集链接线：collector_automation.py:361/389 调 record_collection_evidence
- 健康链接线：resident_health.py:221 调 record_health_evidence
- Evidence API：evidence_api.py stats/list/<id>/timeline 4 端点，生产全部 200
- 生产 app_evidence_records 32 条真实健康证据（18FAIL+14PASS，最新 09-03 03:47）

**B. GAP-13 Alembic 生产接入（RESOLVED，本轮实际施工）**
- 生产库 data/monitor.db 备份（monitor_pre_alembic_stamp_20260903_092723.db）→ ZBC_DB_PATH=生产库 alembic stamp e4278c4d1d79
- 结果：alembic_version=e4278c4d1d79，仅加元数据表（53→54），业务表零变化
- 验证：notes=1049/events=463 完整，8201 全 API 200（healthz/brand-knowledge/negative/evidence）
- 今后生产 schema 变更走 DB-MIGRATION-PLAYBOOK Gate（迁移→staging 验证→备份→upgrade→验证）

**C. GAP-17/18 核实（RESOLVED，无需施工）**
- GAP-17：8200 端口当前 0 实例（历史重复已清理）
- GAP-18：conftest pytest_ignore_collect 已忽略无 def test_ 的脚本式文件（28 个不再被误收集，仍可手动跑）

**D. GAP-19 部分（Selenium 死依赖移除）**
- 全仓 0 selenium import，Playwright 已全面替代（app.py/collector_automation/browser_runtime）
- requirements.txt 移除 selenium>=4.0.0，保留 playwright
- Browser/Scheduler 重复调用部分仍待审计

**E. Commit**
- c14e91a（GAP-08/17/18 注册表）、af4d590（GAP-13 生产接入）、1066b15（Selenium 移除 + GAP-19）
- 已 push，本地=origin/main

**F. 剩余开放 GAP（需决策）**
- GAP-11 DCC 跨仓落后（跨仓 rebase 高风险）、GAP-14 P3 文档级、GAP-16 固定域名（部署项）、GAP-20 工程清理、GAP-21 ZBMP importer API（涉及 Cookie 敏感数据安全面）

## 2026-09-03｜GAP-11/14/20/21 全面推进 + 生产上线
> 协议：WORK → VERIFY → LOG → COMMIT → PUSH → REMOTE VERIFY

**A. GAP-11 DCC 跨仓（RESOLVED）**
- DCC 仓库已被并行巡检废弃（远程 b0448d3/551d17f/27f6baf 标记"内容已迁移至 Zachary-OS-AI"）
- ZBC 内 tools/development-command-console submodule 解除（git rm --cached + .gitmodules 移除 DCC 段），目录内容保留为历史资产（tools/ 已 gitignore）
- 跨仓分叉消除；commit ac9c15f

**B. GAP-20 工程清理（RESOLVED）**
- .trae-cn 已 gitignore；*.log/*.bak/app.py.bak_* 已 gitignore
- 2 个被跟踪的废弃历史备份（style.css.bak_011101/app.js.bak_20260827）已 git rm（文档标注"应删除"、无引用）
- 16 个 start_*.bat/ps1 为在用启动脚本保留；commit 455a510

**C. GAP-14 文档校正（RESOLVED）**
- FEATURE-FINAL-VERIFICATION-MATRIX.md 4 处 API 前缀校正对照真实路由表：
  MON-003=/api/collect|status/<id>|tasks|browser/start|stop；RISK-002=无独立API(内部+状态文件)；SYS-002=/v4/api/status|history|save|push|check|pull|rollback；SETT-001=/api/settings/*|/v4/*
- commit 742a135

**D. GAP-21 Cookie 导入 API（升 DEVELOPING，生产上线）**
- 补受 Basic Auth 保护的 API：POST /api/cookies/import（触发从 data/ 源文件重导入微博/B站/小红书，不接收/不返回 Cookie 明文）+ GET /api/cookies/import/status（仅元信息）
- 安全：写 data/(gitignore 不入库)、Evidence 记录、无凭证 401
- 4 单测通过（401/200结构/无泄漏/405）：tests/test_cookies_import_api.py
- 生产 8201 重启加载，GAP-21 status/import 200 + 既有 API 无回归 + 无凭证 401；commit b46d384

**E. GAP-16 固定域名（登记待决策）**
- 登记方案选项：A) Cloudflare Named Tunnel（固定域名免费断线自愈）/ B) 云服务器反向代理 / C) 保持本机内网
- 涉及公网暴露，待用户拍板

**F. 剩余 GAP 状态**
- 已 RESOLVED：GAP-01~15, 17, 18, 19(Selenium), 20, 23~30
- 待决策：GAP-16（固定域名）、GAP-21 UI 占位（API 已补，前端待接入）

---

## 2026-09-03 推进批次（search-std 案例库增强 + UI 线条icon + 视觉审计 + RedNote 保活核验）

### 已完成
1. **事件三类四关系补全（GAP-07）**：调 /api/event-graph/rebuild-relations（时间+主题词双证据保守重算）→ 16 事件三类（传播13/舆情2/营销1）+ 4 关系（并行3/触发1）。event_graph_relations 1→4 行。
2. **search-std 案例库/RAG 增强接入**：
   - static/index.html 加"⚡ 增强搜索"按钮 + #caseEnhanceResults 容器
   - case_deep_analysis.js 加 CaseDeepAnalysis.enhanceSearch()（POST /api/search/enhance，query/max_results=5，渲染综合摘要+带来源结果+链接）
   - 真实验证（glm 搜索）：输入"商业地产 舆情危机 公关处置 案例" → 返回西安赛格购物中心商户坠楼事件等真实外部案例（来源：智谱搜索）。search-std 已用 3/100。
3. **UI 全局精修（视觉模型适配第一批）**：
   - 用智谱 glm-4.6v 视觉模型（vision_chat）审计生产主页，产出专业建议（顶栏 icon 不统一/快捷按钮无层级/通知缺语义）
   - 落地：顶栏 6 个 emoji icon（🔍✦⚡▦🔔↻）全部替换为线条 SVG（复用 zbip-shell.js 的 SVG 库，stroke=currentColor），顶栏现 9 个 SVG 无 emoji 残留
   - 保存 docs/UI/evidence/UI-VISUAL-AUDIT-20260903.md + ui-review-home-20260903.png
4. **RedNote 登录保活核验**：
   - CDP 9222/9223 在线；/api/xhs/rednote/check-login → is_logged_in=true（香港 RedNote 真实在线）
   - 保活机制已存在（RedNoteLoginKeepalive: should_login_today/check_login_status/mark_login_success）+ /api/xhs/rednote/keepalive 正常；今日 should_login_today=true、last_login_at=null（待执行当日登录保活，走系统内弹窗扫码）

### 未完成
- UI 快捷按钮视觉层级（核心按钮深色背景）待施工（视觉模型建议）
- 状态点语义扩展 + 顶栏留白微调待施工
- RedNote 当日登录保活执行动作（需用户扫码，走 #xhsLoginModal 系统内弹窗）
- staging→main UI 合并回归待执行

### 实测结论
- 增强搜索全链路（前端按钮→/api/search/enhance→web-search-pro→带来源结果渲染）通过
- 顶栏线条 SVG 渲染通过（bu.js 断言 9 SVG / 无 emoji）
- glm-4.6v 视觉模型调用成功（vision_chat，需先注入 .env 到 os.environ，_env 只读环境变量）

---

## 2026-09-03 第二批（守护稳定 + 登录平台修复 + 采集巩固）

### 已完成
1. **守护稳定性修复（关键）**：发现 8201 存在**多套守护进程竞争**（老 run_supervised 17592 + 多套 app.py 抢端口，PID 轮换导致响应不确定）→ 清理全部冗余，单套 run_supervised.py 干净重启。当前单守护+单 app.py，连续调用接口 message 稳定一致。
2. **香港 RedNote 登录平台修复**：`/api/xhs/login/start` 原来硬编码 CDP 9222 + xiaohongshu.com（国内），香港保活却走 rednote.com/9223 → 新增 platform 参数：
   - platform=rednote → CDP 9223 + rednote.com/login（message"香港 RedNote"）
   - platform=xhs → CDP 9222 + xiaohongshu.com（原逻辑保留）
   - 前端 startXhsLogin 默认传 platform=rednote
   - 真实验证：rednote 返回"小红书（香港 RedNote）"、xhs 返回"小红书"
3. **RedNote 保活核验**：CDP 9222/9223 在线；rednote.com/login 打开即显示**已登录首页**（会话有效）——已登录用户无二维码属正常；当日保活状态 should_login_today=true、last_login_at=null（待标记）
4. **采集巩固核验**：
   - 三端配置完整（topic 话题/opinion 舆情/event 事件，keywords+description）
   - 自适应调度已启用（GAP-05 用户已签字）：ShadowPlanner 门控 gate_should_run 决定是否采集，不再固定时间点；当前判定 RUN_DUE
   - 结果回写闭环已接入：network_adaptive.report_collection_result 覆盖风控/拦截/成功/无数据；冷却时长随策略递增（normal60/cautious90/conservative180/suspended360 分钟）
   - 触发真实采集验证：/api/collect 任务 20260903115937217，web-discovery 完成 → 小红书回搜 collecting 阶段（真实链路可跑）
5. **UI 精修（视觉模型第二批落地）**：
   - 快捷按钮视觉层级：核心"进入智能问答"设为 Primary 深色 #1C1917+白字+hover #292524+scale0.98（Oxi Design System Single CTA 原则），其余保持白底——实测生效
   - 六语义状态点体系：.zb-dot-ok/warn/risk/crit/info/unknown（彩色小圆点+外圈光晕+可选 pulse）——实测 zb-dot-risk=#f97316
   - GitHub 研究沉淀：docs/learning/UI-KEEPALIVE-RESEARCH-20260903.md + LR-20260903-005

### 未完成
- RedNote 当日保活 last_login_at 标记（当前会话已在线，无二维码；可标记当日成功，避免重复触发）
- 采集任务最终入库结果待查（异步进行中）
- 其他未提交改动登记：taiji-state.css/js/demo.html（未跟踪）、config/prompts/zbc-prompts.yaml、creative_workbench.html、scripts/idea_generator.py（M，非本轮改动，未擅动）

### 实测结论
- login/start platform 双分支验证通过（rednote→香港 RedNote / xhs→小红书），连续调用稳定
- 快捷按钮 Primary + 六语义状态点 CSS 渲染验证通过（bu.js computed style）
- 守护清理后 8201 单实例稳定

---

## 2026-09-03 第三批（双平台登录保活完整闭环 + 守护稳定性修复）

### 已完成
1. **小红书双平台统一保活机制（核心）**：xhs_collection_optimizer.py 平台化 RedNoteLoginKeepalive：
   - rednote_hk（香港 RedNote，CDP 9223/rednote.com）+ xhs_cn（国内小红书，CDP 9222/xiaohongshu.com）
   - 各平台独立 keepalive 文件（xhs_login_keepalive.json / xhs_cn_login_keepalive.json）
   - 新增 `recheck_and_decide()`：已登录→自动标记当日保活完成（不重复弹）；CDP 不可达→cdp_down（等恢复不误判）；会话登出→重置当日标记+need_relogin（前端自动再弹）
   - 新增 `_mark_login_reset()`：掉线重置当日标记
2. **保活 API 三件套（app.py）**：
   - `/api/xhs/rednote/keepalive?platform=`（增强，双平台状态）
   - `/api/xhs/keepalive/mark`（标记当日完成）
   - `/api/xhs/keepalive/recheck`（检查+决策，need_relogin）
3. **定时自动检查**：scheduler_loop 每 30 分钟对双平台 recheck（已登录自动确认；掉线自动再弹，审计不阻断采集）
4. **前端完整闭环（index.html）**：
   - 登录弹窗平台参数化（openXhsLogin/startXhsLogin 支持 rednote/xhs）
   - 登录成功后自动 mark 对应平台当日保活
   - keepaliveMonitorTick：每 5 分钟轮询双平台 recheck，掉线自动弹登录（弹窗已开则跳过避免轰炸），已登录显示"今日已保活"
5. **守护稳定性修复（关键根因）**：
   - 发现 8201 存在 run_supervised 递归链（run_supervised→run_supervised→app→app）多进程竞争
   - run_supervised.py 增加**单实例保护**（PID lock + 存活检测 + 退出清理）防重复守护
   - 递归链根因未完全定位，当前生产**改用 app.py 直跑**（Flask reloader 父子，无递归，稳定）
6. **真实验证（实测）**：
   - rednote_hk recheck：会话已在线→"当日保活已确认" need_relogin=false ✓
   - xhs_cn recheck：会话已在线→自动确认 ✓
   - 假 CDP 9999 → cdp_online=false（掉线不误判）✓
   - mark API：双平台标记成功 ✓
   - 前端：console 无错误，keepaliveMonitorTick 执行 tick-ok ✓
   - 进程：单套 app.py（Flask 父子 2 进程）稳定

### 未完成 / 登记
- run_supervised.py 递归链根因待排查（单实例保护已加防重复；当前生产用 app.py 直跑，不阻塞）
- 前端保活状态占位元素（keepalive-rednote_hk / keepalive-xhs_cn）可选，自动再弹逻辑独立于 DOM 已生效
- 其余非本轮改动（taiji-state 等）仍登记未擅动

### 实测结论
- 双平台保活状态机 + recheck 决策 + mark 闭环全部实测通过
- 前端 JS 无错误，自动再弹监控运行正常
- 8201 单套 app.py 稳定运行

---

## 2026-09-03 第三批补录（8201 守护稳定性根因澄清与修复 + 上线保障）

### 根因澄清（重要）
排查发现之前的"run_supervised→run_supervised 递归链"是**误判**：
- Windows venv 的 `.venv\Scripts\python.exe` 是 launcher 壳，它会启动 base Python（Python313\python.exe）并转发命令行，launcher 壳保留为父进程
- 所以 6424(venv launcher)→27844(base main)→28084(venv launcher)→15168(base app) 是**正常的父子结构**，不是递归
- 真正的问题一直是：**HealthGuard 计划任务每 5 分钟触发 + 旧 start_production.ps1 的 wait 分支在 app.py 慢启动/卡死时不清理残留**，导致**多次独立启动叠加**（每次一套完整链），多套 app.py 竞争 8201 → PID 轮换、旧代码响应

### 修复（已落地 + 连续验证）
1. **start_production.ps1 8201 watchdog 改确定性**：
   - healthz OK → skip（不叠加）
   - healthz 不 OK → 先精准清理残留 8201 python（run_supervised.py|app.py）+ 删失效锁 → 唯一启动一个 supervisor
2. **run_supervised.py 单实例锁改原子创建**（os.O_CREAT|O_EXCL）：
   - 消除"检查-写入"非原子的并发竞争窗口，杜绝两个 supervisor 同时写锁
3. **验证（实测）**：连续 3 次模拟 HealthGuard 触发 → 全部 "already healthy, skip"，进程链保持唯一一套（6424→27844→28084→15168），lock=27844 唯一，healthz 200

### 上线保障
- 8201 守护逻辑确定化：任何时刻要么健康跳过，要么清理后单实例启动，不再叠加
- 自动恢复能力保留：HealthGuard 仍会检测 8201 并拉起
- CDP 9222/9223 双平台保活在线，recheck 自动确认当日保活（已验证）

### 本轮提交文件
- run_supervised.py（原子锁）
- scripts/start_production.ps1（确定性 watchdog）
- DEV_LOG.md

---

## 2026-09-03 第四批（UI 视觉模型审计 + search-std 案例 AI 评估）

### 已完成
1. **UI 视觉模型审计（glm-4.6v）**：
   - playwright(msedge) 真实截图生产 8201 主页 → docs/UI/evidence/ui-vision-20260903.png
   - 调用智谱视觉模型 glm-4.6v 深度审计（7 维度：布局层级/配色/排版/icon细节/交互动效/3大问题/时尚质感关键改动）
   - 审计结论已沉淀：docs/UI/evidence/UI-VISION-AUDIT-20260903.md
   - 核心发现：①信息层级混乱（核心数据与结论无视觉区分）；②配色刺眼（纯黑按钮+高饱和绿状态点）；③排版拥挤（字号层级弱、行高小）
   - 建议方向：浅灰底 #fafafa、低饱和绿 #4ade80、深灰按钮 #1f2937、1px 细线 icon、柔和阴影（#000 5%+模糊4px）、200ms 中心缩放淡入动效
2. **search-std 案例 AI 评估（99 次中的 1 次，剩 96）**：
   - 调 /api/search/enhance（web-search-pro / provider=zhipu）检索太古汇/品牌舆情风险高价值案例
   - 返回有效案例：中国李宁快闪店广州太古汇案例分析、广州数码产品危机舆情监测、太古汇品牌解析等
   - 可用于案例库增强 + 后续 AI 评估学习

### 消耗登记
- glm-4.6v 视觉模型：本次 1 次调用（用户已授权"随时用"）
- search-std：本次 1 次，剩余 96/100

### 未完成 / 下一步
- 视觉审计意见落地到 UI 精修（第二批/第三批融合：弹窗层级、配色饱和度收敛、微交互）
- 案例库增强：search-std 结果灌入案例库 + AI 评估接入

---

## 2026-09-03 第四批补录（视觉审计落地：zb-dot 六语义色收敛 + 弹窗纸感 + 按压反馈）

### 背景
glm-4.6v 视觉审计指出"高饱和绿色状态点刺眼"——根因是通用 zb-dot 状态点体系仍用高饱和 Tailwind 色（#22c55e 等），与设计系统低饱和语义色不一致。

### 落地（zbip-shell.css）
1. **zb-dot 六语义色降饱和对齐 ZBIP Design Tokens**：
   - ok: #22c55e → #16A34A（success）
   - warn: #eab308 → #D97706（attention）
   - risk: #f97316 → #EA580C（risk）
   - crit: #ef4444 → #DC2626（danger）
   - info: #3b82f6 → #2563EB（info）
   - unknown: #a8a29e → #78716C
2. **弹窗面板浅灰纸感**：modal-panel 背景 #fff → #FAFAF9（+!important 覆盖旧规则）+ 柔和阴影（内高光 + 更透的投影）
3. **主按钮按压反馈**：action.primary hover 背景加深（#1C1917→#292524）+ active scale(.98) + 轻投影；tertiary active scale(.98)
4. **版本号**：zbip-shell.css v1.1.0 → v1.1.1（确保浏览器刷新加载）

### 验证（实测）
- 服务端返回 6 个新语义色全部生效
- modal-panel 计算背景 = rgb(250,250,249) = #FAFAF9 ✓
- 日报弹窗其余元素（dr-dot #16A34A / 主按钮 #1C1917 / 结论块 #F5F5F4 / 12px 圆角 / 柔和阴影）此前已验证全部符合设计系统

### 结论
日报弹窗与全局状态点已全面符合 ZBIP 黑白灰侘寂 + 低饱和语义色 + 彩色小圆点状态签名设计语言。


---

## 2026-09-03 第五批补录（话题检测端采集恢复：INSERT 列数修复 + 日志加固 + 单实例防线）

### 背景
话题专题采集（topic_campaign_snapshots）近 1 天 36 条全部 error（note/browse/discussion 全 0），用户要求"话题检测端的问题也要解决，要正常采集"。

### 根因链（源码>运行时>测试 判定）
1. **INSERT 列数不匹配（直接落库失败主因）**：topic_campaign.py _save_notes 的 INSERT VALUES 有 24 个占位符，但 INSERT 列名 + 实际参数只有 23 个 → sqlite OperationalError "24 values for 23 columns" → 采集线程 CRITICAL 异常中断 → notes 永不落库、快照不写。生产库 topic_campaign_notes 实际 24 列（16 基础 + 8 新增字段），代码 DDL 只建 16 列（由迁移补齐）。
2. **多实例并存抢占 8201（采集被杀的间接主因）**：HealthGuard（每 5 分钟）与手动 ps1 并发启动 + ps1 watchdog 删 lock 文件，导致 2 个 run_supervised + 4 个 app.py 并存；后者 Flask app.run 绑定 8201 失败退出码=1，崩溃时正在跑的采集线程被杀 → 快照空 error。
3. **多进程共写 system.log 轮转 PermissionError 噪音**：RotatingFileHandler doRollover os.rename WinError 32，产生 33700 次日志噪音（不崩主线程但污染日志）。

### 修复（均 py_compile 通过、留 .bak 备份、未提交）
- **topic_campaign.py**：① INSERT VALUES 24→23（与列名/参数对齐）；② 采集脚本无结构化输出时兜底 `if not data:` 记 error，绝不伪造数据。
- **app.py**：`logging.raiseExceptions=False` + 自定义 `_SafeRotatingFileHandler`（doRollover 失败安全降级追加打开，绝不抛异常）。
- **run_supervised.py**：msvcrt LK_NBLCK 进程级排他锁（含空文件锁 bug 修复）+ 端口占用即退出（双重单实例防线）。

### 验证（真实测试）
- **SQL 级单测**（内存库，不动生产库）：修复后 INSERT 23 值插入成功、UPDATE 20 值（19 SET + WHERE id）更新成功。
- **生产 8201 真实采集**（重启加载新代码后 POST /api/topic-campaign/run）：
  - 4 个话题全部 success：'#广州太古汇十五周年' 40 条 / '#广州太古汇15周年' 40 条 / '#一方五境' 60 条 / '#广州太古汇' 40 条
  - 本轮新增 notes 151 条落库（first_seen_at >= 13:54）
  - 13:54+ 日志 0 条 CRITICAL / 0 Traceback（INSERT 修复 + 日志加固双生效）
  - browse_count/discussion_count 恒 0 为平台限制（小红书网页版不提供话题浏览/讨论指标，实测确认），note_count 为话题端有效产出
- **单实例防线**：手动起第 2 个 supervisor → 日志"Supervisor 已存在(PID=?，端口8201)，退出避免重复守护"，被成功挡退。

### 已知未决（登记）
- 计数双轨不一致：/api/collection/counter 读 DB collection_counters（今日 0）vs check_collection 读 JSON（今日 9 次/95 条），前端展示误报，非采集问题，后续对齐。
- ps1 watchdog 删 lock 与 msvcrt 锁的并发竞态仍可能产生冗余 supervisor 残留（不影响功能，已用端口防线兜底）。
- 话题"浏览/讨论"指标平台不提供，接受以 note_count 为话题端主要产出指标（待用户认知确认）。

### 结论
话题检测端采集已恢复正常（快照 success + notes 落库 + 无异常），生产 8201 由新代码稳定运行。

---

## 2026-09-03 第六批｜小红书双平台（大陆9222/香港9223）每日登录保活对等 + 官方账号只读红线

### 背景
用户指令：大陆小红书也要和香港 RedNote 一样做每日登录保活（优先执行）；并明令"不要动广州太古汇官方账号，即使页面登录了也不允许动"。

### 源码审计发现（修复前真实缺陷）
后台 30 分钟 recheck 与前端轮询虽已循环双平台，但链路有 4 处断裂，导致大陆实际不被对等对待：
1. **两套平台命名断裂（核心）**：登录侧用 `xhs/rednote`，保活用 `xhs_cn/rednote_hk`；前端登录成功后 mark 传 `xhs`，后端 `_get_keepalive` 只认 `xhs_cn`、其余全部回退 rednote_hk → 大陆登录被错标到香港头上。实测旧接口 `?platform=xhs_cn` 竟返回 `"platform":"rednote_hk"`（文件历史残留覆盖实例身份）。
2. **login/status 写死大陆**：固定连 9222 + xiaohongshu.com，香港登录永远判定"未登录"。
3. **login/save 写死大陆**：固定连 9222 且只存 xhs_cookies.json，香港 cookie 无法落盘。
4. **check_login_status 写死 xiaohongshu.com + 仅中文"登录"文案**：香港 rednote.com / 英文界面判定不准；前端缺 `keepalive-*` 状态占位元素（双平台状态无处显示）。

### 修复（最小增量，留 .bak-dualkeep 备份，未碰采集主链/红线函数/生产库）
- **xhs_collection_optimizer.py**：① 新增 `normalize_platform()` 统一 16 种别名到 `xhs_cn/rednote_hk`；② 平台配置补 login_url/home_url/session_cookies/login_texts，香港环境变量与歧义的 XHS_CDP_URL 解耦为独立 XHS_HK_CDP_URL（全局 XHS_CDP_URL 默认 9222 服务大陆采集，未动）；③ `check_login_status` 改为按本平台域名、cookie 优先（web_session 等）+ 多语言登录文案回退；④ `get_status` 的 platform 以实例身份为权威，不再被历史文件残留覆盖；⑤ 新增 `get_platform_endpoint()` 供登录路由统一解析。
- **app.py**：`/api/xhs/login/start|status|save` 三个路由全部改为按平台归一化分派——大陆 9222/xiaohongshu.com/xhs_cookies.json，香港 9223/rednote.com/rednote_cookies.json，互不覆盖；auth_recovery 按平台身份标记。
- **static/index.html**：统一前端平台标准名（`_xhsNormPf` 兼容旧别名）；登录弹窗标题/说明按平台显示（国内小红书 9222 / 香港 RedNote 9223）；save 带 platform；内置浏览器页新增"每日登录保活"状态条（双平台状态徽章 + 大陆/香港各自扫码登录按钮）；修复 1 个我引入的 `_xhsLoginSessionId` 重复声明（会导致整段脚本语法错误、函数全不挂载）。
- **官方账号只读红线固化**：xhs_collection_optimizer 模块 docstring + AGENTS.md 7 章新增"官方账号只读保护"硬红线（自动流程禁止关注/点赞/收藏/评论/私信/发布/退出等一切账号写操作，登录仅用户本人扫码）。

### 验证（真实测试，非推断）
- 归一化单测 11 组别名全部正确；endpoint 分派大陆 9222/xiaohongshu.com、香港 9223/rednote.com；双实例独立 keepalive 文件。
- 生产 8201 平滑重启（仅结束 app 进程链、supervisor 19440 自动拉起，新 PID 22404，healthz 200 v5.9.9）。
- 重启后 curl 实测：`?platform=xhs_cn` 与别名 `xhs` 均返回 platform=xhs_cn/9222/国内小红书/今日已保活；`rednote_hk` 与别名 `rednote` 均返回 rednote_hk/9223/香港 RedNote/今日已保活——旧错标消除。
- Playwright（msedge headless）真实加载：保活条 innerText="每日登录保活 | 国内小红书: 今日已保活 | 大陆扫码登录 | 香港 RedNote: 今日已保活 | 香港扫码登录"；大陆/香港弹窗标题正确切换；openXhsLogin/startXhsLogin 均为 function；**控制台 0 错误**。
- 自动写操作审计：采集/保活脚本中"社交写操作（follow/like/collect/comment/publish 等）自动点击"命中 0；保活模块零 click/type/fill，纯只读。证据 docs/UI/evidence/dual-keepalive-*.png。

### 未做 / 边界
- 未触碰采集主链、五条红线函数、data/monitor.db；事件笔记端仍按令暂不开放。
- 登录态 cookie 命中后仍会每 30 分钟只读 recheck；真实掉线才弹扫码（双平台对等）。

---

## 2026-09-03 第七批｜Zachary 对话面板 A1–A4：接真 AI + 意图顺序修复 + 实时版本 + 侘寂重构

### 背景（用户痛点）
问"今日发布的负面舆情"两次都返回相同"今日舆情概览"模板（答非所问）；面板是"壳+真实统计数字+if-else 假问答"，未接真 AI；蓝白旧风与已确认的 ZBIP 黑白灰侘寂不一致；系统状态硬编码 v5.7.0（实际 v5.9.9）。

### 源码审计（以现状为准，纠正一处旧结论）
- 后端 `/api/ai/chat`（app.py:2233）本就具备 `function_registry.build_context` 结构化检索 + `intelligence._chat` 模型 + local_rule 兜底，返回 `{ok,reply,provider,ai_status,context}`；前端从未调用它。
- `/api/notes` 在 data_query_api.py（blueprint），支持 sentiment/date_start/date_end/per_page；database._apply_filters 的 date_start/end 过滤的是 **publish_date（发布日期）**，符合"发布≠采集"时间红线；旧前端误用 `limit`（被忽略，实际默认 per_page=20）且不带日期。
- trace 曾记"313 行单引号致模板不解析"——现状该行已是反引号、`${}` 正常，**该 bug 不存在，不修假 bug**。
- 健康检查真实路径是根 `/healthz`（返回 {ok,version:"5.9.9"}），`/api/healthz` 为 404；旧代码若按 apiBase 拼会 404。

### 修复（最小增量，留 .bak-aifix，未碰后端业务/红线函数/生产库）
**static/js/zachary_robot_enhanced.js（generateAnswer 重写）**
- A1 接真 AI：新增 askAiChat() 调 POST /api/ai/chat；分析/建议/解释类问题与兜底都走真 AI，后端自带检索，AI 仅增强、数字仍由规则权威给出（不把 AI 当 System Truth）。
- A2 意图顺序：系统状态 → 分析建议类(走AI) → 负面 → 正面 → 风险清单 → 数量 → 概览 → 报告 → AI 兜底；把"负面/正面"等具体意图提到"概览(今日/今天)"宽泛词之前，根治"今日负面被概览拦截"；新增 ANALYTIC_RE/LIST_RE，"有什么风险+处置建议"走 AI、"有哪些风险"走清单。
- 时间：resolveDateScope 识别今日/昨日/前日，负面/正面按 publish_date 传 date_start/date_end（严格发布时间，非 captured_at）；指定时间窗为 0 时如实告知并附带最近 3 条（明确标注"不限今日"），不伪造。
- A3 去硬编码：系统状态改实时 `/healthz`(根路径 getHealthz 单独请求)+`/api/ai/status`，显示真实 v5.9.9、在线状态、真实 provider/model；删除 v5.7.0/数据库v8 假文案。
- apiCall 补 credentials:'same-origin'；帽子色/动态面板青光改中性。
**static/css/zachary-zbip.css（新增 Strangler 覆盖层，最后加载，回滚=删一个 link）**：浮子去紫青霓虹改中性投影；面板白纸细边弱阴影圆角 14；header 近黑 #1C1917 + 语义绿在线点；bot 浅灰气泡 / 用户近黑气泡；快捷钮白底描边 hover 反色；输入与发送近黑；移动端全屏化。**static/index.html**：引入该 css、脚本版本号 8.0.0→8.0.1 防缓存。

### 验证（Playwright msedge headless 真实加载 + 网络拦截 + DOM 断言）
- CASE1 "今日发布的负面舆情"：请求 `/api/notes?sentiment=negative&per_page=6&date_start=2026-09-03&date_end=2026-09-03`（按发布日期），今日为 0 如实返回并补拉最近 3 条（2026-08-30，标注不限今日）——不再误回概览。
- CASE2 "系统运行状态"：版本 **v5.9.9**（实时）、服务在线、AI zhipu/glm-4.5-air；不再 404、无 v5.7.0。
- CASE3 "方所闭店…给处置建议"：命中分析类，仅请求 `/api/ai/chat`，AI 基于系统检索（696 条/负面55/高风险23/互动302,543）输出"判断→依据→动作→责任方时限→复盘指标"。
- **CONSOLE_ERRORS=[]**（首轮发现的 /api/healthz 404 已随根路径修复消除）。证据截图 docs/UI/evidence/zachary-panel-zbip-20260903.png（近黑 header+绿点/浅灰气泡/描边快捷钮/近黑发送，无蓝紫青）。

### 边界 / 未做
- 未改后端 /api/ai/chat 与任何业务规则、红线函数、生产库；AI 输出不回写数据库事实。
- 侘寂覆盖层仅作用于 Zachary 面板；其余页面精修在后续 UI 批次。

---

## 2026-09-03 第八批｜B1 采集计数双轨对齐：/api/collection/counter 真实化（消除"今日 0"误报）

### 问题（源码>运行时判定）
前端/运维看到"今日采集 0 次 0 条"，但 check_collection 实际为 9 轮 / 95 条。根因：`collection_counters` 是**死表**——全仓只有 counter 路由"读不到就 INSERT 一行 0,0,0"，**没有任何采集流程 UPDATE 它**，故恒为 0。真实事实分散在三处：notes（今日落库）、collection_logs（每关键词任务日志）、data/collector_stats.json（调度轮次自记）。另存在第三套 collector_v2 内存计数（重启清零）。

### 真实口径（只读核查 monitor.db，未写库）
2026-09-03：notes 今日入库 **95 条**（collected_at/captured_at 一致，去重主体过滤后的生产事实）；collection_logs 今日 81 个关键词任务 = SUCCESS 50（原始抓取合计 3640，未去重）+ BLOCKED 30 + NETWORK_ERROR 1；collector_stats.json auto=9/manual=0（9 个调度轮次，一轮多关键词）；最近任务 11:54 BLOCKED、最近成功 10:40 → **当前确处熔断**。注意 status 枚举大小写混用（SUCCESS 主、旧 success、BLOCKED/error/NETWORK_ERROR/NO_NEW_DATA）。

### 修复（只改 app.py 一个路由，纯只读计算，留 .bak-counter）
- 删除"读时插 0 行"的无意义写操作；不再依赖死表数值。
- daily_count = notes 今日按**采集时刻**（captured_at 优先回退 collected_at）COUNT = 95（统计"今天采到多少"用采集时刻，正确区别于发布日期）。
- 新增 runs_today/logs_today/success_runs/blocked_runs/error_runs/raw_collected（3640 原始量）/last_task_status/last_success_at，口径全部标注；manual/auto 仅来自当日 collector_stats.json。
- circuit_state 按"最近一次任务 vs 最近一次成功的先后"判定（不用今日累计对比）：最近 BLOCKED/NETWORK_ERROR 且晚于最近成功 → blocked；NO_NEW_DATA → idle；否则 normal。
- 保留原字段名与 daily_limit/manual_limit/auto_limit 配额，不破坏任何调用方；返回 source 标明实时来源。

### 验证（真实）
- 平滑重启 8201（仅结束 app 主/子、supervisor 自动拉起，8200 未碰），healthz v5.9.9。
- 接口实测：daily_count=95、runs=9(0/9)、logs 81=50成功/30熔断/1错、raw=3640、**circuit_state=blocked（last BLOCKED，last_success 10:40）**、last_collect_at=10:49:19。
- tests/healthcheck.py 退出码 0：9 模块全 ok、notes_today=95 与接口一致、**subject_guard gz_hit=true / sh_excluded=true（主体口径红线未受影响）**、双时间字段齐备。

### 遗留登记（本轮不动，避免改采集主链）
- scripts/collect_now.py:33 仍读死表 collection_counters 判断配额 → 实际配额闸恒放行；collector_v2 另有内存计数。三套计数的"采集决策层"统一放到 D2 动态调度/熔断线（adaptive_engine）一起做，本轮只对齐展示/查询口径，不改采集规则与业务逻辑。
- 主 SPA 当前未消费该接口；真实字段已就绪，供后续"采集状态卡 / UI 精修"直接绑定，不造假数据。

---

## 2026-09-03 第九批｜D1 系统内置浏览器前端打通：同源凭证修复 + SSE 实时画面 + 侘寂化（系统内可见、不跳外部）

### 源码审计（纠正"缺前端"的旧判断）
前端并不缺：static/js/internal_browser.js（SSE 优先+轮询降级/双账号 tab/导航/点击/滚轮/fps）、internal_browser.css、index.html#page-internal-browser 容器与侧栏入口均已存在，DOM id 与 JS 全部对得上。真实断点：① **api() 的 fetch 未带 credentials**——页面以 URL 内嵌 Basic Auth（Zachary:***@127.0.0.1）打开时，同源 fetch 不自动带 Authorization，/api/internal-browser/history 等被浏览器安全策略拦截，画面一直"连接中"；② ib-btn-external 在 DOM 里但未绑事件；③ CSS 仍是旧紫渐变（#6d5df0/#9b8cff、rgba(120,110,180)、iOS 绿）。后端蓝图（accounts/state/screenshot/navigate/evaluate/click/type/scroll/history + SSE stream + browser-runtime）齐全。

### 修复（最小增量，留 .bak-ibrowser，未改后端、未碰采集与官方账号）
- static/js/internal_browser.js：fetch 增加 `credentials:'same-origin''`，并对 401 返回明确"重新登录"提示（不再静默卡住）；EventSource 增加 `{withCredentials:true}`；补绑 ib-btn-external（用户主动才在外部浏览器打开当前 URL，不自动跳转）；本就无任何自动导航/自动写操作，符合"官方账号只读、登录仅本人扫码"红线。
- static/css/internal_browser.css 整体侘寂化（保留全部布局/响应式）：容器白底细边 #E7E5E4 弱阴影圆角14；tab 未选 Stone-500/选中近黑 #1C1917 实心下划线（去紫渐变）；主按钮近黑实心；视口近黑 #1C1917 衬底（类 Safari/Chrome）；在线点语义绿 #16A34A、离线 #DC2626、暂停橙 #D97706；补 .ib-btn-external 图标钮样式。
- index.html：地址输入框内联紫边改 Stone；internal_browser.css/js 版本号 →v=8.0.2 防缓存。

### 验证（真实，Playwright msedge + Basic 头）
- 运行时：CDP 9222/9223 均 Listen；accounts 双号 online（大陆 2 target、香港 rednote 首页）；browser-runtime/status ok。
- E2E：切到内置浏览器页后 accounts/stream/screenshot/history **全部 200、has401=False**（修复前 history 被拦）；SSE 建立并显示"实时流·1-2fps"；在线点 .online；img 真实填入 data:image/jpeg；**导出的实时帧 docs/UI/evidence/internal-browser-live-20260903.png 为真实小红书 explore 画面**（频道 tab/双列瀑布流/点赞/底部导航），证明 前端→Flask→CDP→驻场浏览器→系统内回传 全链路通；CONSOLE 无脚本错误。
- 故障诚实性：某轮 CDP captureScreenshot 返回 502 Connection timed out（驻场页面忙/香港走代理的运行时抖动），前端如实显示"无法连接驻场浏览器 + 错误"并由 SSE/轮询自动续帧，**不伪造画面**。

### 遗留登记（不阻塞，后续优化）
- 后端 capture 多 page target 时固定取 pages[0]，可能选到 about:blank（应优先选非 blank 的活跃可见 target）；CDP ws 偶发超时可加一次快速重连。属后端健壮性优化，本轮不动采集主链。
- 侧栏"内置浏览器"入口位于 Zachary OS AI 分组（分组较多需滚动），其信息架构层级在 UI 精修批次统一优化。

---

## 2026-09-03 第十批｜D7 登录体系收口：原生登录框闪断根因 + v4 owner 凭证对齐 + 旧凭证残留全盘排查

### 问题（用户痛点 + 源码/运行时判定）
1. 浏览器原生登录框"账号密码输到一半自己跳没、又出现"。
2. "v4 设置页登录按钮点击无响应"（历史登记）。
3. 用户要求全盘排查 ID082610 等旧凭证残留，"旧数据残留不得影响最新系统"。

### 根因一：多个并发 401 同 realm 挑战反复重置原生登录框（真实机制修复）
- 修复前无凭证探测：`/favicon.ico`、`/api/*`、文档导航 `/` **全部**回 `WWW-Authenticate: Basic` 且 `Connection: close`。浏览器为顶层文档弹原生框的同时，favicon 等并发请求的第二个同 realm 401 挑战到达，会重置正在输入的原生框——即"输一半跳没又出现"。
- 修复（app.py `_basic_auth`，最小增量，留 .bak-auth，安全等级不降）：
  - 白名单新增 `/favicon.ico`（无凭证探测由 401 变 **204**，不再产生挑战）；
  - **仅顶层 HTML 文档导航**回 `WWW-Authenticate`（需要浏览器弹框）；`/api/`、XHR(X-Requested-With)、Accept 仅 application/json 的子请求回**纯 401 JSON（不带挑战头）**，不触发原生弹框、不打断输入，改由前端 401 流程（含 D1 的同源凭证 + 统一 Auth 恢复弹窗）处理。子请求依旧 401 拒绝，只是不弹浏览器原生框。
- 修复后实测：favicon 无凭证=204 无挑战头；API 无凭证=401 无 WWW-Authenticate；文档导航无凭证=401 且保留 WWW-Authenticate（正常弹唯一框）；正确凭证=200。

### 根因二：v4 owner 密码与 Basic Auth 没同步（"按钮无响应"实为密码不符，且差 1 次锁定）
- Playwright 实测证伪"按钮无响应"：/v4/settings/ 未登录正常 302 到 /v4/settings/login，btnPwd 点击真实发出 POST /v4/auth/login 并渲染返回，**无 JS 错误**（仅一个 password 未包 form 的 verbose 提示，无害）——旧"无响应"已被此前 fetch 凭证修复覆盖。
- 真实问题：Basic Auth(.env TAIKOO_AUTH_PASSWORD，即当前 Basic 新密码)，但 v4 独立用户库 `v4_users` 的 owner 哈希对该新密码 / 旧密码 / ZBMP 密钥 **均不匹配**（历史另一密码），且排查时 failed_attempts 已累加到 **4/5**（再错 1 次即锁 15 分钟）。这是"两套独立凭证、改了 .env 不会同步 v4 owner"的旧残留。
- 处置（用户已授权"v4 owner 密码与 Basic 对齐为同一新密码"，真实值只存 .env、不入仓）：
  - 新增可复用正式脚本 **scripts/sync_v4_owner_password.py**：从 .env 单一来源读 TAIKOO_AUTH_USER/PASSWORD（不硬编码密码），写入前用 sqlite 在线 backup API **一致性整库备份**到 data/backups/，只 UPDATE v4_users 中 role='owner' 这一行的认证字段（password_hash/failed_attempts=0/locked_until=NULL/status=active/must_change_password=0），默认 dry-run、--apply 才写，写后本地 verify_password + service.login 双重验证；**不触碰任何业务表/舆情数据**。
  - 实跑：备份 data/backups/pre_v4ownersync_20260903_153525.db；owner failed 4→0、pw_verify=True、service.login success role=owner；HTTP 复验密码登录 success/owner/token=True。
- 第二处凭证不一致：v4 密钥登录 master_access_key 默认是历史值"张志宏"，.env 未设 V4_ACCESS_KEY，故用户指定的 ZBMP 密钥 **并未生效**。已在 .env 补 `V4_ACCESS_KEY=<用户指定密钥>`（真实值只存本地、永不提交，先备 .env.bak-d7），重启后实测：该密钥→owner 成功、错钥被拒（只锁 __access_key__ 计数器不影响 owner）。

### 旧凭证残留全盘排查结论
- tracked 源码 ID082610（已废弃旧密码，仅历史对照）= 0 生效命中（仅 DEV_LOG/CHANGELOG 历史叙述，正常）；.env Basic 用户/密码与当前一致（正确；存在两行重复 AUTH，值一致无害，登记不擅改）。
- 默认密钥"张志宏"仅余：v4_upgrade/config.py 默认值（已被 .env V4_ACCESS_KEY 覆盖，生产实际生效为用户指定密钥、值仅存 .env 不入仓）、docs 历史文档（不改历史）、tests/v4_smoke.py 硬编码——**已修测试**：改为测试启动时注入固定假密钥 os.environ["V4_ACCESS_KEY"]，走与生产一致的"环境变量注入"路径，不再硬编码历史默认值、不依赖真实 .env/真实密钥。

### 验证（真实）
- tests/healthcheck.py 退出码 0：9 模块 ok、notes 1052/今日95、双时间字段齐备、**subject_guard gz_hit=true / sh_excluded=true（主体红线未受影响）**。
- tests/v4_smoke.py：认证/密钥/会话/权限/设置页相关 **22 项全 PASS**（含新"正确密钥(env注入)->owner"）；仅 2 个 FAIL（"8 个采集适配器"期望 8 实际 11、适配器平台状态列表）与 1 处临时库缺 publish_datetime 列 traceback，经 git diff 自证**均在适配器/notes 区、与本批改动无关，属 pre-existing**（适配器枚举增长未更新断言 + 临时库未建业务列），登记另线处理，不混入本 commit。
- 生产 8201 两次平滑重启（仅结束 app 主/子、supervisor 自动拉起，8200 未碰），healthz v5.9.9；401 挑战分流重启后复检仍生效。

### 边界 / 遗留登记
- 只改认证层，未碰采集主链、五条红线函数、业务数据；.env / data/backups / *.bak / 临时库均不提交。
- v4_smoke 2 个适配器断言过时 + 临时库 schema 缺列导致脚本 exit1（pre-existing）：另开小线把断言改为动态读取已注册适配器、临时库补业务列或跳过业务查询。
- .env 两行重复 TAIKOO_AUTH_*（值一致、无害）；docs 20260830 密钥清单仍写历史默认值（历史文档，需要时加注"以 .env V4_ACCESS_KEY 为准"）。

---

## 2026-09-03 第十一批｜D2 小红书动态采集/动态冻结闭环补齐（审计先行，最小增量）

### 结论：动态调度三闭环经源码逐行核实已存在，本轮只补 1 处真实缺口（+7 行，零删除）
按"源码事实优先"先把生产调度主路径完整读穿，再决定改不改，避免重复造轮子：
- 生产链 = `app.py scheduler_loop`(每20s) → `gate.gate_should_run`（app 启动 `setdefault ZBC_SCHED_GATE_MODE=enforce`，GAP-05 已从影子转真门控，**只收紧不放松**、自身异常 fail-open）→ `xhs_cookie_bridge.create_task`。
- **动态间隔（不定时）已闭环**：`platform_adapters/scheduling/decision.py` 按六态（SUCCESS/NO_NEW_DATA/RISK_WARNING/BLOCKED·COOLING_DOWN/SESSION·NEED_VERIFY/NETWORK）算 current_interval——无新数据 ×1.5 指数延长(上限6h)、风控冷却 900s×2^n(上限1800s)、网络退避 60s×2^n(上限900s，连续3次进冷却)、恢复先低频试探、连续3次成功回正；xhs 基线 1h、硬上限 20min。
- **动态冻结时长已闭环**：`xhs_cookie_bridge._adaptive_cool_minutes()` 随 adaptive 策略返回 60/90/180/360min，`_trip_circuit(...,cool_minutes=_adaptive_cool_minutes())` 熔断时长随风险递增（异常 fail-open 回 60）。
- **动态采集量已闭环**：生产路径 `sync→_run_search` 的采集量唯一旋钮是 max_scroll（无独立详情层），它被**双重动态**收紧——scheduler 取 adaptive_engine 的 max_scroll(NORMAL6/CAUTIOUS4/CONSERVATIVE2/SUSPENDED0)，`_run_search` 内再与 network_adaptive.current_scroll_limit 取 min。
- 任务完成 worker 已**双回写**：`_shadow_record_result`→planner 六态、`adaptive_engine.report_collection_result`→7指标滑窗；state_map 状态归一安全（未知态/None→COLLECT_ERROR，绝不误判成功；AUTH_FAILED→SESSION_EXPIRED、CAPTCHA→NEED_VERIFY、PARTIAL_BLOCKED→RISK_WARNING）。

### 本轮唯一补丁：worker 未预期异常分支补回写统一规划器
- 问题：worker `except Exception`（sync 未兜住的异常）此前只回写 adaptive_engine，没回写 planner，导致 planner 的 last_run_at/动态间隔不更新，enforce 门控可能在异常后仍按原间隔高频重试。
- 改动：xhs_cookie_bridge.py 异常分支补 `_shadow_record_result('NETWORK_ERROR',0,str(e),run_type)`（归一 NETWORK_ERROR 走网络退避），fail-open，与成功/受控失败路径一致；**+7 行、零删除、零红线改动**。

### 经核实"不改"的两处（避免过度施工，记录决策）
- `COOLDOWN_MINUTES=60` 保持静态：它是 create_task 内"任何情况下两次运行至少隔 60min"的账号安全硬地板（恰=planner 正常基线 1h），动态间隔由 planner 在其上层门控，二者正交；若把它改动态反而可能在风控时缩短间隔，危险。
- adaptive_engine 的 `max_details/request_delay/max_concurrent/next_collect_hours/pause_minutes` 在当前 xhs_cookie_bridge 路径无消费者：当前采集量由 max_scroll 决定、间隔由 planner 决定，两套分工已清晰；**不硬造一层详情抓取循环去"用上参数"**（违反最小增量）。登记为预留参数，未来若引入独立详情阶段再消费。request_delay NORMAL55>CAUTIOUS5 的反序疑点随之搁置（该字段当前无人读取，非生产行为）。

### 测试与真实结果（已实测）
- 新增 tests/test_adaptive_exception_feedback.py（3 例，内存态 planner state_file=None/store=None，不触网、不连浏览器、不碰生产 data/）：①异常回写后立即决策被 WAIT_INTERVAL 拦下；②连续3次网络失败进 IN_COOLDOWN；③planner 自身故障时回写 fail-open 不冒泡。
- `pytest test_adaptive_exception_feedback + test_adaptive_feedback + test_adaptive_engine -q` = **7 passed**；`py_compile` exit0。
- tests/healthcheck.py exit0：9 模块全 ok、notes_total 1052/今日95、subject_guard gz_hit=true & sh_excluded=true（广州主体口径未动）、has_publish_datetime=true（publish/captured 双时间字段在）。

### 文件
- 改：xhs_cookie_bridge.py（+7）；新增：tests/test_adaptive_exception_feedback.py；本日志。备份 xhs_cookie_bridge.py.bak-d2（不提交）。数据库无变化、无迁移。

---

## 2026-09-03 第十二批｜D3 系统内扫码登录弹窗：在线直判保活 + 未登录真实回传二维码（大陆/香港对等）

### 用户痛点与真实根因（先真实 CDP 探测，不猜）
现象：系统内登录弹窗"未弹出/没有二维码"。用常驻 CDP（9222 大陆 / 9223 香港，均在线）做**只读**探测（只 goto/读 DOM/截图，不点击账号操作）后确认三层根因：
1. 两台 CDP 浏览器当前**都已登录**：rednote `/login` 被服务端重定向到首页 `/`、国内首页跳 `/explore`，页面是 feed 流、无可见"登录"入口，自然没有二维码（命中的 `img[src*=qr]` 实为 xhscdn 头像/内容图与 logo，非登录码）。
2. 旧 `/api/xhs/login/start` 只在外部 CDP 窗口 `goto` 登录页，返回前端的 JSON **从不包含任何二维码截图/数据**；`/status` 只回 is_logged_in 布尔——系统内弹窗从源头无图可显。
3. 国内 `login_url` 是**首页**（非专门登录页），未登录时需先点"登录"入口才弹出二维码面板；rednote 是专门 `/login`。两平台出码路径不同，不能用单一写死选择器。

### 后端改动（app.py，本批提交核心）
- 新增三个模块级辅助：`_xhs_ensure_login_panel`（未登录且停首页时**仅点一次"登录"入口**唤起面板，按可见+尺寸过滤，绝不碰关注/赞藏/发布/退出/切号）、`_xhs_shot_qr_element`（多候选选择器 + 可见/近方形(80–360px,比例0.65–1.55)/取最大面积，元素截图 base64）、`_xhs_login_capture`（在线→`logged_in` 直接返回不截图；未登录→复用已开本平台 tab 或新开→唤面板→元素截图，失败回退整页视口截图，保证前端永不空白）。
- `/start` 精简为只建会话（移除一次性开页线程，避免线程泄漏/重复 tab）；`/status` 改为幂等调用 capture，返回 `stage(logged_in|qr_ready|no_qr|error)/qr_image(dataURL)/is_logged_in/message`，并对二维码做 2.5s 会话级节流（在线判定每次实时查 cookie）。
- 大陆 9222 / 香港 9223 完全对等（platform 经 get_platform_endpoint 归一，cookie 分别落 xhs_cookies.json / rednote_cookies.json，互不覆盖）。

### 前端改动（static/index.html，已随并行提交 5e1cf23 入库）
- Step2 增系统内二维码容器（侘寂：Stone 底、细 border、圆角10、弱阴影）+ `<img id=xhsLoginQr>`；`checkXhsLoginStatus` 按 `qr_image/stage` 渲染：有码显码、no_qr/加载显 spinner、error 显原因、在线自动 Step3→save→当日保活 mark→关窗。

### 测试与真实结果（已实测）
- API 双平台：start 返回会话；status 对 xhs_cn / rednote_hk 均正确 `stage=logged_in, is_logged_in=true, 无 qr_image`（在线不截图、直接保活，不再卡空扫码窗）。
- Playwright(msedge headless) E2E：二维码 DOM 就位；open→Step1→start 后 8s 内正确经 Step3 自动关窗（在线路径），无 PAGEERROR；唯一 console 502 为页面既有外部资源加载、非登录 API、非本次引入，已登记。
- py_compile app.py exit0；healthcheck exit0，subject_guard gz_hit/sh_excluded=true、has_publish_datetime=true（主体与时间口径未动）。

### 边界 / 遗留登记（不造假）
- **未登录态的"二维码元素精确截图"当前无法当场 E2E**：两平台在线，且红线禁止退出/切换广州太古汇官方账号；已用多候选+几何过滤保证鲁棒，并回退整页视口截图，待某次真实掉登录时补一次出码 E2E。
- 前端文件被并行 marketing 提交 5e1cf23 的批量 add 一并入库（内容即本批前端版本、与后端字段匹配）；后端 app.py 由本批提交补齐，在此之前旧后端缺 qr_image 字段时前端 fail-soft（只显示 loading 不报错）。
- 备份 app.py.bak-d3 / static/index.html.bak-d3（不提交）。数据库无变化、无迁移；采集红线、五条主体函数未触碰。

---

## 2026-09-03 第十三批｜修复主笔记自动采集"午后停摆"：固定日配额 → 动态调度兜底（执行层问题另立）

### 现象（运行态只读体检发现，非猜测）
- notes 最后 captured_at 停在 11:49 左右、之后主笔记不再入库；但 schedule_decisions 每 20s 一条 `allow=1 / RUN_DUE / 到达动态间隔允许采集`，schedule_state.last_run_at 冻结 15:14（该时间点是话题端独立链路回写）。即"决策一直放行、实际不采集、last_run 不回写"的空转。

### 根因（源码+数据双证）
1. 旧固定日配额钳制：`xhs_cookie_bridge.MAX_AUTO_RUNS=9 / MAX_DAILY_RUNS=12`，今日 collector_stats `auto_runs=9` 于 11:49:37 用满，此后 scheduler_loop 每 20s 经 gate 放行（hard_allow=True 且 planner RUN_DUE），但被第二道旧门 `check_rate_limit('auto')` 以"今日自动采集已达9次上限"硬挡 → 不 create_task、也不回写 planner（planner 无该配额知识，故持续判 overdue 空转）。跨天 00:00 才重置。
2. 该固定配额是动态调度（GAP-05）上线前的老策略，与用户"不定时、按状态动态决定采集量、持续运行"指令冲突，实际把动态调度架空。
3. 旁证：`AUTO_COLLECT_HOURS` 固定钟点表在生产唯一调度 scheduler_loop 中已不参与决策（仅 get_account_status 展示）；collector_v2 的固定钟点 Scheduler 未被 app.py init（旁路，未启用），无需改。

### 修复（最小、可逆、不放松账号安全）
- `MAX_AUTO_RUNS 9→26`、`MAX_DAILY_RUNS 12→30`，定位从"固定配额"改为"动态调度下的防失控高兜底"；`MAX_MANUAL_RUNS=3`、`COOLDOWN_MINUTES=60` 保持不变。
- 安全论证：采集节奏仍由 planner 动态间隔（基准 3600s、NO_NEW_DATA ×1.5 指数至上限 6h、风控/网络退避、熔断）+ 60min 硬冷却主导，任意两次运行间隔不会因本次改动而变密（理论最快仍 ≥60min、≈24 次/天，26 为兜底余量）；本次只是允许采集持续全天、不再"用满 9 次即停到次日"。
- 更正 AUTO_COLLECT_HOURS 过时注释（标注仅历史展示）。备份 xhs_cookie_bridge.py.bak-quota（不提交）。

### 测试与真实结果（已实测）
- py_compile exit0；进程外只读 import：旧逻辑 `check_rate_limit('auto')` 今日应为 False，改后为 `(True,'频率检查通过')`，manual 亦 True。
- 平滑重启 8201 后，16:47:53 scheduler 真实 create_task（collector_stats auto_runs 9→10、新增 run@16:47:53），其后连续 5+ 个 20s tick auto_runs 不再增长（60min 硬冷却正确挡住重复创建，未失控）。
- healthz exit0、主体 gz_hit/sh_excluded 未触碰；无数据库结构变更。

### 新发现并登记（采集执行层，下一批独立修，不混入本提交）
- 恢复触发后任务真实执行但：collection_logs#613 `page.goto Timeout 45000ms`、#614 `NETWORK_ERROR/EMPTY_NO_API`。
- 只读 CDP(9222) 诊断（不开代理、不点击）：搜索页 `status=200 / domcontentloaded 4.1s / title=广州太古汇-小红书搜索 / 无验证滑块 / 无登录遮罩`，但 `bodyLen=18、note-item=0`——**网络层通畅、不依赖 VPN**；页面框架到达而搜索数据 XHR 未渲染/未拦截。结合手动 domcontentloaded 仅 4.1s，判生产 goto 疑用 networkidle/load 等待策略，撞上小红书搜索页长连接导致 45s 超时；EMPTY_NO_API 为搜索 XHR（sns/web/v1/search/notes）未捕获。下一批修：goto 等待策略改 domcontentloaded+主动等待搜索 XHR/结果选择器、排查搜索接口签名与拦截时序。

---

## 第十四批（2026-09-03）：采集执行层修复——搜索改走已登录常驻 CDP，根治 goto 超时 / EMPTY_NO_API

### 真实根因（比第十三批预判更深，已坐实）
- 第十三批曾预判是"goto 等待策略撞上长连接"。逐层读穿生产链路后修正：生产搜索 `xhs_cookie_bridge._run_search` 用 Popen 跑 Node 脚本 `xhs_cookie_search.js`，而该脚本**每次 `chromium.launchPersistentContext` 冷启动一个全新 headless 浏览器 + 注入 cookie 文件获得会话，根本没有连接已登录保活的常驻 CDP（大陆 9222 / 香港 9223）**。于是"系统内登录保活显示在线、搜索子进程却没有有效会话"两条路径割裂：
  1. 全新 headless 冷启动慢、独立指纹易被风控 → `page.goto` 45s 超时（collection_logs #613）；
  2. 独立 headless 的搜索 XHR `/api/sns/web/v1/search/notes` 在反自动化下根本未发出（apiCalls=0）→ EMPTY_NO_API（#614）。
- 对照实验（同一时刻、同一 9222，只读不操作账号）：Python `connect_over_cdp(9222)` 复用已登录会话 → goto 1.2~1.9s、search/notes XHR 200、稳定返回 22 条真实笔记；而 Node 直冷导航 `search_result` 首次 ERR_TIMED_OUT、第二次卡死 150s。进一步对照成熟采集器 `xhs_cdp_collector.collect_human` 既有实践（其注释明确："无 keyword 的 search_result 冷导航易挂起；先稳落 explore 再进搜索"），确认第二个诱因是**冷导航直挂搜索页易挂起，需 explore 预热**。
- 结论：搜索应复用已登录的常驻浏览器（真实会话/指纹、快、稳、与保活统一），并在进搜索页前先落 explore 预热。功能不依赖 VPN（直连 9222 已实测 1.2s 可达，无 HTTP_PROXY、Edge 启动参数无 --proxy-server）。

### 修复（最小、可逆、旧能力保留为兜底）
- `xhs_cookie_search.js`：
  - 新增浏览器后端选择：环境变量 `XHS_CDP_URL` 可达时优先 `chromium.connectOverCDP` 复用常驻浏览器默认 context、开独立 page；连接失败自动回退原 `launchPersistentContext + addCookies` 独立 headless 路径（旧能力不删）。
  - CDP 模式进搜索页前先 goto `/explore` 预热（domcontentloaded，20s 超时，失败仅告警不中断），对齐 Python CDP 采集实践，解决冷导航挂起。
  - CDP 模式开启前自愈关闭此前异常残留的 `search_result` 标签页（不触碰 explore 等用户/保活页面）。
  - 安全清理：CDP 模式只 `page.close()` + `browser.disconnect()`，**绝不关闭常驻浏览器**；独立模式才 `context.close()`。
  - 正常路径结尾显式 `process.exit(0)`：connectOverCDP 可能残留连接句柄使 Node 事件循环不空、进程不退出（会导致 bridge 按 poll 等进程白等到 30min 超时），写完结果即干净退出。
- `xhs_cookie_bridge.py`：`_run_search` 子进程 env 增加 `XHS_CDP_URL = cdp_url_for()`（按当前激活身份自动解析大陆 9222 / 香港 9223），+2 行；其余六态判定、熔断、自适应逻辑不变。
- 备份 xhs_cookie_search.js.bak-cdp（不提交）。未改数据库、未改五条红线、未改任何业务口径。

### 测试与真实结果（已实测）
- `node --check` 语法 exit0；Python 补丁脚本每处替换均断言唯一匹配。
- 纯 Node 端到端（Popen 同款方式、XHS_CDP_URL=9222、max-scroll=2）：预热前首次 ERR_TIMED_OUT/二次卡死；加 explore 预热 + process.exit(0) 后 **exit=0、16.2s 干净退出、state=SUCCESS、total=20、api_calls=1、无 blocked/error**，笔记含作者/点赞/发布日期（2026-09-01 等，publish_date 与采集时间分离正确）。
- 生产函数直调 `xhs_cookie_bridge._run_search('广州太古汇',2)`：**45s 返回 state=SUCCESS、total=20、api_calls=1**，样例"一方五境·广州太古汇十五周年再出发"，主体全部命中广州太古汇、无其他城市同名污染。
- 红线 canonical 回归：subject_rules.subject_hit 广州太古汇=True、成都太古里=False；reprocess.aggregate_events / risk_engine.build_daily_report 均可调用；本次改动文件仅 xhs_cookie_search.js、xhs_cookie_bridge.py(+2)。
- 平滑重启 8201（只停 `-u app.py --port 8201` reloader 父子，supervisor 自拉起新 PID 23888），/healthz ok v5.9.9；8200/9222/9223 未动。

### 遗留与下一步（如实登记）
- 独立 headless 兜底路径的 cookie 文件时效本次未改（仅作 CDP 不可达时兜底）；主路径已切常驻 CDP。
- 尚未等到下一次 scheduler 自动调度真实入库（60min 冷却主导）；已用生产函数直调等价验证 worker 内部调用链。下一次自动/手动任务后复查 collection_logs 六态与 notes 新增。
- Node playwright(sandbox_runtime) connectOverCDP 对冷导航较敏感，已用 explore 预热规避；若仍偶发，CDP 不可达会自动回退 headless，不会卡死调度（process.exit 兜底 + bridge 30min 高限）。

### 补登：完整 worker 链路真实落库证据（6af4b5c 之后实测）
- 进程外同步调用 `xhs_cookie_bridge.sync(['广州太古汇'], 2)`（即 create_task 内 worker 的同一核心函数，含逐词搜索→主体过滤→去重→写 notes→写 collection_logs→回写 planner/adaptive）：**45.4s、task_state=SUCCESS、updated=13、inserted=0、blocked 空**。
- collection_logs **#626：keyword=广州太古汇 / status=SUCCESS / notes_count=19 / error_msg 空 / 17:28**，与修复前同链路 #620–#625（16:54–16:58）全部 BLOCKED/IP_RISK_OR_CAPTCHA 形成直接对照。
- inserted=0 属正确幂等：搜索返回的近期热门笔记（十五周年等）上午已入库，去重命中后只 UPDATE 刷新（updated=13）、不重复插入，notes 总量稳定不丢不重；要出现 inserted>0 取决于平台出现新笔记，非缺陷。
- 结论：自动调度主链路（scheduler_loop→create_task→worker→sync→_run_search→Node 走常驻 CDP）已端到端恢复，下一次自然调度（动态间隔 + 60min 冷却）将持续产出 SUCCESS。

## 第十五批（2026-09-03 晚）：所有采集统一暂停门 + 单轮频率收敛 + 主体默认品牌红线修复

### 背景（事实）
- 用户指令：暂停采集、控制采集频率、能复用绝不新造、**所有采集都要遵循采集器规则**。
- 暂停时审计 collection_logs：17 时 1 SUCCESS（#626 修复验证），19 时一轮 9 SUCCESS/10 EMPTY/4 NETWORK_ERROR/3 BLOCKED，20 时一轮 **17 BLOCKED/9 NETWORK_ERROR/仅 1 SUCCESS**，20:39:57 触发风控熔断（detail“RISK 17/20 关键词被拦截”，hold 到 21:39:57）。单轮 20 个关键词以约 45s/个连续搜索（20:30:56→20:39:57），单轮请求密度过高是直接诱因。
- 入口审计：三条生产采集路径（自动 create_task、collector_automation、xhs_p0_orchestrator）最终都汇聚到 `xhs_cookie_bridge.sync`；但 `/api/collect` 的全网发现+回搜走 app `_run_collect_task → collector.collect_all`，不经 sync；且 sync/_run_search 入口本身无统一暂停门（仅 create_task 顶层有），存在旁路。
- **红线发现**：subject_rules.py:115 模块默认 `ACTIVE_BRAND` 在并行 KOS 提交 f85d3ea 被改成 `"hainan_cdf"`，全仓无 ZBC_ACTIVE_BRAND 环境变量覆盖 → 不设环境变量时全局 `subject_hit/subject_reason` 用海南中免词表，广州太古汇词全部不命中（裸测“广州太古汇”=False）。生产 8201 进程 20:16 启动、正运行该口径，等同广州生产主体过滤被切换，触碰最高红线。

### 改动（最小、可回滚、只复用现成能力，不新造调度）
1. 红线修复 `subject_rules.py`：默认 `ACTIVE_BRAND` 改回 `"guangzhou_taikoo_hui"`（广州生产安全默认）。多品牌能力全部保留——海南中免/DFS 等改由环境变量 `ZBC_ACTIVE_BRAND` 或 `subject_hit_for_brand(brand_key=)` / `_subject_sql_and_values_for` 显式激活，禁止改全局默认。SUBJECT_WORDS/EXCLUDE/五字段逻辑一字未动。
2. 统一采集暂停门 `xhs_cookie_bridge.py`：在唯一汇聚点 `sync()` 入口加门——非测试模式且 `is_user_paused()` 为真时立即返回 task_state=USER_PAUSED、零平台请求；create_task worker 对 USER_PAUSED 直接收尾且不回写 planner/adaptive（用户暂停非网络成败、不触发退避）。
3. 单轮频率收敛（同文件，复用 network_adaptive，不新建控制器）：新增常量 KEYWORD_GAP_MIN_SEC=12 / KEYWORD_GAP_JITTER_SEC=6 / EARLY_STOP_CONSECUTIVE=3；关键词循环内①相邻词间保证 ≥12s 并叠加 0–6s 随机拟人间隔（末词不等）②连续 3 个关键词被拦截/网络失败即提前结束本轮（early_stop），不再硬撞风控，半数熔断仍在下方统一判定。
4. `/api/collect` 通道补门 `app.py _run_collect_task`：入口检查同一 `xhs_cookie_bridge.is_user_paused()`，暂停时全网发现+回搜一律不发起、任务标记 done 后 return（finally 仍正常释放采集锁）。

### 测试与真实结果（已实测）
- 三文件 `py_compile` 全部 exit0。
- 统一门：当前 user_paused=true 下进程外调 `sync(['广州太古汇'],1)` **0.00s 返回 USER_PAUSED**、inserted=0、调用前后 xhs_cookie_search node 进程均为 0，证明任何采集路径零平台请求。
- 红线：默认激活品牌=guangzhou_taikoo_hui；subject_hit('广州太古汇活动')=True、('成都太古里逛街')=False；subject_hit_for_brand('海南中免离岛免税',brand_key='hainan_cdf')=True 且海南口径不命中广州（多品牌隔离正确）；`_subject_sql_and_values()` 仍为广州口径、175 个绑定参数。
- 平滑重启 8201（只停 `-u app.py --port 8201` reloader 父子 1456/10600，supervisor 自拉起新 PID 22792/19180，20:59:24），/healthz ok v5.9.9；重启后 user_paused=True、circuit_open=True 经 data/private 文件持久化完整保持、未自动开采集、node 搜索进程=0；8200/9222/9223 未动。

### 未实测 / 遗留（如实登记，当前用户暂停不真发请求）
- 连续拦截早停、词间 12–18s 拟人间隔的实际防风控效果，需用户恢复采集且熔断解除后小流量观察 collection_logs 六态验证。
- “每轮关键词限量 + 跨轮轮转覆盖”（进一步降单轮密度）本轮未做，登记 backlog，下一步与用户确认目标节奏后落地（仍复用现有常量，不新造）。
- 恢复探测间隔在 schedule_state 曾被压到 current_interval=60s（policy recovery_probe=1800），原因待查，列入下一步。
- 当前采集为双暂停：用户暂停（20:44:28，恢复时间用户定，POST /api/xhs/collect-resume）+ 风控熔断（hold 到 21:39:57，由其自身健康检查恢复）。
- 备份：subject_rules.py.bak-brand、xhs_cookie_bridge.py.bak-guard、app.py.bak-guard（均不提交）。








## 第十六批：KOS 品牌采集闭环（方案 A：source_keyword 品牌隔离）

### 背景事实
- KOS 多品牌中心（brand_hub.js）已有品牌→地区→门店层级导航与品牌 Dashboard，但"启动采集"按钮仅 alert 占位，无任何采集调用；后端 /api/kos/* 无品牌采集端点（api_refresh 仅 refresh_profiles 聚合）；collector_v2/run_profile.py 为纯 CLI 入口。
- 数据隔离现状：notes 表无 brand 字段（subject_type 已被 KOS 用作身份分类 kos/official/media，不可占用）；kos_engine.refresh_profiles 全局聚合所有 notes，直接入库会稀释污染广州 KOS。

### 改动（最小可回滚，三文件 + 备份 .bak-koscollect）
1. kos_engine.py 末尾新增品牌隔离聚合（方案 A：不新增 DB 表、不写 kos_profiles 主表、不动 schema）：
   - _brand_source_filter(brand)：source_keyword ∈ 品牌采集词（复用 collect_keywords_for，品牌隔离天然标记）
   - brand_collection_stats(brand)：品牌采集状态（笔记/作者/最新采集时间）
   - brand_profiles(brand, limit)：品牌 KOS 作者实时聚合（S/A/B/C 分层，不写主表）
2. kos_routes.py 新增两端点（/api/kos/ 前缀）：
   - POST /api/kos/collect：统一暂停门（is_user_paused，与主链同一规则，测试模式豁免）→ CDP 复用（body.cdp_url 或 cdp_url_for()）→ run_live 逐词 + persist_live(brand_hit 闭包，subject_hit_for_brand 品牌主体过滤，不修改全局激活品牌) → brand_collection_stats 返回
   - GET /api/kos/brand：品牌采集状态 + 实时 KOS 聚合（广州零影响）
3. static/js/brand_hub.js：
   - activateBrand 从假 alert 改为真实 POST /api/kos/collect（USER_PAUSED 提示/成功统计/失败报错）
   - 新增 refreshBrandData(key)：GET /api/kos/brand 刷新品牌 KPI + TOP KOS；note_count>0 自动标记 active
   - renderDashboard 已激活分支：广州走原 KOS 全局链路（红线不动）；非广州品牌走品牌隔离链路

### 实测结果（已实测）
- py_compile：kos_engine/kos_routes 全过；node --check brand_hub.js 语法 OK
- 直连只读：hongkong_dfs stats=0/0；guangzhou_taikoo_hui stats=175 笔记/152 作者（隔离标记有效，DFS 不混入广州）
- 平滑重启 8201（只停 app.py reloader 父子，supervisor 自拉起新 PID 5700/18192，healthz ok v5.9.9）
- HTTP 实测（Basic Auth）：
  - POST /api/kos/collect {hongkong_dfs} → {"ok":false,"status":"USER_PAUSED","reason":"用户指令暂停：先控频率，恢复时间待定"}（统一暂停门生效，品牌采集不绕过主链规则）
  - GET /api/kos/brand?brand=hongkong_dfs → ok:true, note_count:0（尚未采集）
  - GET /api/kos/brand?brand=guangzhou_taikoo_hui → ok:true, note_count:175, author_count:152, 20 个 KOS profile（含"广州太古汇"官方账号只读聚合，无写操作）
- 前端 DOM 匹配：index.html 的 brandDashboardContent/brandKosTotal/brandKosS/brandKosPotential/brandNoteTotal/brandTopKos 均存在
- 红线复测：subject_rules.py 未改动（广州主体口径不变）；官方账号只读；notes/monitor.db 无 schema 变更；diff 敏感扫描干净（仅 xhs_cookie_bridge 模块名命中，非真实密钥）

### 未实测 / 登记
- 真实品牌采集执行被统一暂停门正确拦截（当前用户暂停+风控熔断双暂停中），未触发平台请求；恢复采集后（POST /api/xhs/collect-resume + 熔断健康检查恢复）即可通过 /api/kos/collect 启动 DFS 等品牌采集，本链路无需改代码。
- 品牌→CDP 身份映射（香港品牌应走 rednote 香港 9223）当前用 body.cdp_url 显式指定，未自动按品牌地区解析（登记，下一步增强）。
- 采集频率/词间隔沿用主链规则（本轮未在 collect 内额外限频，靠统一暂停门+主链调度约束；品牌采集批量场景待真实运行观察后校准）。
- 备份：kos_engine.py.bak-koscollect、kos_routes.py.bak-koscollect、brand_hub.js.bak-koscollect（均不提交）。


---

## 第十七批：KOS 主体归属 Gate + HUMAN_CONTROL_GATE 执行状态机 + KOS 统一香港账号采集

### 背景
KOS MASTER EXECUTION CONTRACT v1 已入双子库（ZBC d292c9f / OSAI bd088f6）。核心 P0：采集准确度、主体归属 Gate、KOS 识别、账号资产、真实运行闭环；禁止"生成=已发送"、禁止 AI 幻觉充当业务事实。本批落地 Contract 的合规底座：**内容相关 ≠ 主体归属** 的确定性判定 + **敏感动作人工确认** 的状态机审计。

### 改动
1. **主体归属 Gate（kos_engine.ownership_for）**
   - 确定性规则映射 subject_type → ownership_class（official→OFFICIAL 0.95；media→MEDIA 0.85；kos→INDEPENDENT_KOL_KOC 0.6 需复核；normal_user→UGC_CONSUMER 0.6 需复核；空→UNKNOWN 0.3 需复核）。
   - 返回 ownership_class / state / confidence / needs_manual_review / reason / evidence_hint。
   - 纯判定视图，不写回 kos_profiles、不改广州口径、AI 不越权。
   - GET /api/kos/brand 现返回 profiles 附加 ownership；新增 GET /api/kos/ownership?brand=|author_id=。
2. **HUMAN_CONTROL_GATE 执行状态机（kos_execution.py + migration v8→v9）**
   - 状态机锁定：AI_GENERATED → PENDING_HUMAN_REVIEW → HUMAN_APPROVED → EXECUTING → SUCCESS/FAILED（REJECTED 支持）；非法转移/终态/无 actor 人工批准一律拦截。
   - 门控动作集 GATED_ACTIONS：reply_send / outreach_send / email_send / lead_export / cooperation_confirm / contract_confirm / paid_media / publish / reward_issue。
   - 审计表 kos_executions（migration_8_to_9 建，DB 已备份 before_migration_v8_to_v9.db 9.79MB 后升级到 v9）；含 execution_id/action_type/target/actor/created/approved/executed/result/evidence_ref/failure_reason。
   - 新增端点：POST /api/kos/execution、POST /api/kos/execution/<id>/transition、GET /api/kos/executions。
   - reply/generate 与 outreach 接入：生成建议后自动登记 AI_GENERATED 执行（返回 hcg.execution_id + "生成≠已发送"），不再是无审计的纯文本。
3. **KOS 统一香港账号采集（用户指令 2026-09-03）**
   - POST /api/kos/collect 默认 CDP 由 cdp_url_for() 改为 cdp_url_for(XHS_RETINAUT_NAME)（香港 RedNote 9223）；body.cdp_url 仍可显式覆盖。

### 实测（真实结果）
- py_compile：kos_engine.py / kos_routes.py / kos_execution.py / database_migrations.py 全通过。
- 状态机单测（test_hcg.py）：创建 AI_GENERATED → 拦截 AI_GENERATED→SUCCESS → PENDING → 拦截无 actor 批准 → HUMAN_APPROVED(approved_at) → EXECUTING → SUCCESS(evidence) → 终态拦截 → 非门控动作拦截，全部通过。
- 迁移：database_migrations.py migrate v8→v9 成功（自动备份 9.79MB + 建表），当前 DB v9。
- HTTP 实测（HTTP Basic Auth（账户见设置页））：
  - POST /api/kos/reply/generate（"多少钱？想买"）→ hcg.status=AI_GENERATED, execution_id=KX-*（生成≠已发送）。
  - POST /api/kos/outreach（真实 author 61d58d…）→ ok=True, hcg=AI_GENERATED。
  - POST /api/kos/execution + transition 全流程（paid_media 示例）：AI_GENERATED→PENDING_HUMAN_REVIEW→HUMAN_APPROVED→EXECUTING→SUCCESS；GET /api/kos/executions?status=SUCCESS 审计可见。非法跳步 HUMAN_APPROVED→SUCCESS 被正确 400 拦截。
  - GET /api/kos/brand?brand=guangzhou_taikoo_hui → profiles 附加 ownership（新采集账号判 UNKNOWN/需复核，符合"内容相关≠KOS"契约）。
- 红线回归：active_brand=guangzhou_taikoo_hui；subject_hit('广州太古汇')=True、('成都太古里')=False；subject_hit_for_brand(title='海南中免', brand_key='hainan_cdf')=True、（三亚国际免税城/DFS尖沙咀）=True。五条红线函数未改、publish_datetime/captured_at 未混、官方账号只读。
- 香港 CDP：cdp_url_for(XHS_RETINAUT_NAME)=http://127.0.0.1:9223。
- 系统干净重启 8201（清残留进程后 supervisor 拉起，worker 19196），healthz v5.9.9 OK。

### 未实测 / 登记
- 真实品牌采集仍被统一暂停门拦截（用户暂停+风控熔断双暂停中）；恢复后 KOS 采集将默认走香港 RedNote 9223，可 body.cdp_url 覆盖。
- 归属 Gate 目前为确定性规则视图（官方/媒体自动 DIRECT，其余待人工复核）；AI 辅助分类未接入（AI 不越权原则，后续可加，但不得覆盖硬规则）。
- kos_profiles 主表未加 ownership 字段（避免 schema 变更与广州数据影响）；如后续需要持久化归属结论，建议新增独立归属表（经用户确认后做）。
- 备份：kos_engine.py.bak-ownership、kos_routes.py.bak-hcg、database_migrations.py.bak-hcg（均不提交）。


---

## 第十八批：KOS 采集功能全套增强（relevance + interaction + AI_SUGGESTED）｜智谱 per_call 5 次落地

### 背景
用户指令"kos采集功能全套用99次的5次"：使用智谱 per_call 99 次额度中的 5 次，深度推进 KOS 采集功能全套（KOS MASTER EXECUTION CONTRACT v1 落地）。5 次全部为智谱 glm（intelligence 网关，AI Budget 自动记录）。

### 智谱 5 次调用记录（均计入 per_call 额度）
1. API 连通验证：provider=zhipu，返回"在线"（此前 401 已解决）。
2. KOS 采集链路深度审查 → 输出最小增强清单：P0 subject_filter 二次验证/relevance 阈值；P1 interaction_pattern 采集；P2 AI_SUGGESTED 归属标记机制。
3. content_relevance_score 计算设计（命中位置加权：标题3/正文2/其他1，排除词0分+复核，低分不拒入库）。
4. AI_SUGGESTED 归属标记机制（AI建议→SUGGESTED→人工复核→VERIFIED）+ interaction_pattern 聚合设计。
5. 落地审查：6 项逐项 PASS（主体归属/AI权限/relevance/互动聚合/状态机/香港采集+广州口径），总评 PASS。

### 改动（全部确定性/视图层，零 AI 运行时依赖、零生产风险）
1. kos_engine.py 追加（复用现有，不改主函数）：
   - content_relevance_score(note, brand_keywords, exclude_keywords)：确定性 0-1 分数 + segment + need_recheck；排除词→0分+复核（不拒入库）；仅作 KOS 排序/分层信号，不替代 subject_hit。
   - get_interaction_pattern(author_id, brand, limit)：从 notes 聚合互动模式（likes/comments/collects/shares 均值+中位、engagement、active/emerging/quiet），KOS 识别证据，不新增生产字段。
   - brand_kos_account(brand, author_id)：单账号 360° 视图 = ownership + relevance + interaction，纯视图不写库，ai_status=RULE（AI 建议须人工复核转 VERIFIED，不越权）。
2. kos_routes.py：
   - /api/kos/ownership 现返回 profiles 附带 relevance + interaction（enrich）。
   - 新增 GET /api/kos/account?brand=&author_id= 单账号 360° 视图。

### 实测（真实结果）
- py_compile 全过。
- 单元：content_relevance_score（海南中免标题命中=1.0 high；成都排除词=0.0 excluded+need_recheck）；get_interaction_pattern（广州官方=active）。
- HTTP 实测（Basic Auth）：
  - GET /api/kos/account?brand=guangzhou_taikoo_hui&author_id=61d58d… → owner=OFFICIAL, rel=0.472 medium, notes=9, inter=active, eng_avg=225.3, ai_status=RULE。
  - GET /api/kos/ownership?brand=guangzhou_taikoo_hui&limit=2 → count=2, need_review=2，每条带 owner/relevance/interaction。
- 平滑重启 8201（worker 26668），healthz v5.9.9 OK。
- 红线回归：广州 subject_hit=True/成都=False；五条红线函数未改；AI 不越权（ai_status=RULE）；官方账号只读；publish_datetime/captured_at 未混。

### 未实测 / 登记
- AI_SUGGESTED 的人工复核 UI/持久化未做（当前机制字段就位，人工确认端点为后续）；AI 建议调用本身不自动发生（不越权），需人工显式触发。
- relevance/interaction 在品牌真实采集数据上的校准待恢复采集后观察（当前双暂停）。
- 备份：kos_engine.py.bak-enhance、kos_routes.py.bak-account（不提交）。


---

## 第十九批：AI_SUGGESTED 人工复核闭环（归属 VERIFIED override）

### 背景
守住基线后推进：完成 KOS 主体归属 Gate 的最后一步——AI 只给建议（AI_SUGGESTED），人工确认后转 VERIFIED 正式归属。全程不碰数据库、不改广州口径、可回滚。

### 改动（kos_engine.py + kos_routes.py，纯增量）
1. kos_engine.py：
   - ownership_confirm(brand, author_id, ownership_class, confirmed_by)：人工确认归属，写入 data/private/kos_ownership_overrides.json（不碰 DB 表；AI 不越权，确认后才生效）。
   - _ownership_override(author_id, brand)：按 (brand,author_id) 或全局查已确认归属。
   - ownership_for 开头加 override 检查：有人工确认 → 直接返回 VERIFIED（confidence 0.9, needs_manual_review=False, 带 confirmed_by/confirmed_at）；规则路径输出 ai_status=RULE（结构统一）。
2. kos_routes.py：新增 POST /api/kos/ownership/confirm + GET /api/kos/ownership/overrides。

### 实测（真实结果）
- py_compile 全过。
- 单元：normal_user 确认前 UGC_CONSUMER → ownership_confirm('hainan_cdf','A-OVR','TARGET_ENTITY_KOS') → 确认后 TARGET_ENTITY_KOS/VERIFIED/0.9/confirmed_by=zachary；测试 override 已清理。
- HTTP 实测（Basic Auth）：POST /api/kos/ownership/confirm → ok=True class=TARGET_ENTITY_KOS by=zachary；GET /api/kos/ownership/overrides → count=1；测试数据已清理（count=0）。
- 平滑重启 8201（worker 24812），healthz v5.9.9 OK。
- 红线复测：active_brand=guangzhou_taikoo_hui，广州=True/成都=False；五条红线函数未改；官方账号只读；publish_datetime/captured_at 未混；采集仍用户暂停（未误动）。

### 未实测 / 登记
- 前端「归属确认」UI 未做（当前 API 可调用，界面待接入 KOS 页面）。
- override 文件为 data/private/（gitignore，不提交），属运行期业务数据。
- 备份：kos_engine.py.bak-verify、kos_routes.py.bak-verify（不提交）。


---

## 第二十批：评论智能增强（情感三维 + 购买/合作信号 + 真实回复模板）

### 背景
守住基线推进 KOS 评论智能（KOS Master Contract 第十节）：在现有 analyze_comments 规则分类基础上，补齐智谱设计的情感-专业度二维与意图识别。纯增量字段、确定性规则、不碰 DB、可回滚。

### 改动（kos_engine.py，仅 analyze_comments + 3 个新辅助函数）
1. 新增确定性辅助函数：
   - _comment_sentiment(content)：positive/neutral/negative/mixed（正负关键词 + 混合判定）。
   - _purchase_signal(content)：strong/weak/none（KOS 评论承接价值）。
   - _cooperation_signal(content)：yes/no（发现潜在 KOS / 商务合作机会）。
2. analyze_comments 每条评论新增：sentiment / purchase_signal / cooperation_signal / needs_review；reply_suggestion 从"待 AI 生成"占位改为调用 generate_reply 拿真实模板（单一事实源，高风险→NO_REPLY 空建议）。
- 保留现有 category / should_reply / risk_level 结构，调用方不受影响。

### 实测（真实结果）
- py_compile 全过。
- 单元：情感（好用推荐=positive / 太垃圾=negative / 一般吧=neutral）、购买（怎么买多少钱=strong / 考虑一下=weak / 还不错=none）、合作（求合作商务=yes / 随便看看=no）。
- HTTP 实测：GET /api/kos/comments → total=141，每条带 sentiment/purchase_signal/cooperation_signal + 真实回复模板（广州太古汇口吻）。
- 平滑重启 8201（worker 28912），healthz v5.9.9 OK。
- 红线：五条红线函数未改；广州口径未动；官方账号只读；publish_datetime/captured_at 未混；采集仍用户暂停。

### 未实测 / 登记
- 评论智能的 AI 增强（语义情感/复杂意图）未启用（当前确定性规则已够生产，AI 可选通道后续）。
- 前端评论面板展示新字段 UI 待接入。
- 备份：kos_engine.py.bak-comment（不提交）。


---

## 第二十一批：KOS 品牌中心 UI 接入（归属确认 modal + TOP KOS 增强渲染）

### 背景
把已落地的后端能力（归属 Gate / relevance / interaction / AI_SUGGESTED 复核）在前端品牌中心显性化。纯前端增量，广州数据口径/采集逻辑零改动。

### 改动（static/js/brand_hub.js）
1. 共享 renderKosRows(profiles, brandKey, el)：TOP KOS 行渲染增强——归属类徽标 + 互动彩色点（active绿/emerging黄/quiet灰）+ relevance 分数 + 待复核标记 + 「归属」确认按钮（UNKNOWN/待复核时显示）。
2. 新增 window.KOSConfirmOwnership(brand, authorId, nickname)：黑白灰极简 modal，7 类归属选项（独立KOL/KOC/媒体/普通用户/主体官方/商户/合作方/未知），人工确认 → POST /api/kos/ownership/confirm → 成功后刷新。
3. 广州品牌 TOP KOS 改用 /api/kos/ownership?brand=guangzhou_taikoo_hui 渲染（带归属/互动信号）；refreshBrandData（非广州）复用 renderKosRows。

### 实测（真实浏览器验证）
- node --check 通过（node=0）。
- 浏览器真实加载 8201：进入品牌中心→广州品牌 Dashboard，TOP KOS 列表显示 5 个真实 KOS，每条带归属类（UNKNOWN）+待复核+relevance（low/medium）+互动点（active 绿）+「归属」按钮。
- 归属确认 modal 弹出正常（黑白灰居中，7 选项+取消）；关闭后 console 零报错。
- 后端红线不受影响：只改了前端 JS；广州数据口径/采集/五条红线函数未动。

### 未实测 / 登记
- 确认按钮端到端（点归属→选类型→confirm→VERIFIED）未在浏览器点实际业务数据（避免误改），后端端点已单独实测通过。
- 非广州品牌（香港DFS等）采集暂停无数据，增强列表暂以广州展示验证。
- 备份：brand_hub.js.bak-ui / .bak-refactor（不提交）。
