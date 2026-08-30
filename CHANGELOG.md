# 变更日志

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
