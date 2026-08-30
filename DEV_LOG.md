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
