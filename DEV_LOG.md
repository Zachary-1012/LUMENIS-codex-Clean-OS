# Z-Brand-Core 开发协作日志

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
