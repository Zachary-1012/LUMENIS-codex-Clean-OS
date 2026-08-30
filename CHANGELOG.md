# 变更日志

## [5.8.5] - 2026-08-30（上线冲刺：进程韧性 / 采集主链 / 采集风险引擎）
### 新增：无人值守韧性（冲刺3）
- 9222 真人采集浏览器掉线时，采集器自动 `CollectorAutomation.start_browser` 拉起持久 Edge 再走 CDP，拉不起才退 headless 兜底；真机“杀进程→自动拉起→CDP 就绪”验证通过。
- `scripts/start_production.ps1`（幂等：8201 看门狗 / 9222 已在跑则跳过）+ 登录自启 cmd，部署到当前用户启动文件夹免管理员，开机登录自动恢复采集。形成四层无人值守：登录自启 / app 崩溃看门狗双探测自愈 / 9222 崩溃采集器自愈 / 每日 08·18·24 自动版本同步。

### 增强：CollectorGuard 接入采集主链 + 采集提速（冲刺4）
- `collect_all` 每个关键词经 CollectorGuard 保护层（动态拟人间隔 / 响应归因 / 指标 / 断点），命中 IP 风险 / 验证码 / 登录失效即熔断并停止后续关键词请求，绝不伪装 0 条、不无限重试；5 项接入单测通过。
- 反馈词进入采集前清洗停用词/噪声并限量；全网发现 GDELT 超时默认 30s→8s，国内不可达快速放弃。真机回归任务 done（原始19/有效10/新增3/更新7/AI复核3秒过/事件链跑通/未崩），新笔记 publish_datetime 自动正确填充、标题非空。

### 新增：统一 Auth Recovery Center 前端闭环（P0，冲刺5）
- 统一控制台外壳新增“全局状态中心 + 不跳页统一恢复弹窗”：首页采集健康矩阵并入小红书主采集六态（v4 适配器 + 老链路合并，共 12 平台），修正平台中文名/数量字段；异常平台点击直接在当前页弹恢复窗而非跳陌生页。
- 弹窗严格 A 登录失效 / B 人机验证 / C IP风控熔断 三类分清：C 类只显示冷却倒计时、不显示扫码（扫码不可解）；三步状态机（打开登录页→扫码/验证→恢复续采）、二维码或登录页截图、“我已完成验证/重新检测”“稍后处理（保持暂停不伪装）”；恢复成功自动解除暂停续采。
- 全局看门每 12s 巡检，任何子页（含 iframe）平台失效都在外壳弹同一弹窗，手机端底部卡片适配。后端复用既有 /v4/adapters/recovery/* 与 /api/xhs/collect-health，未重造。浏览器真机 E2E：12 平台矩阵、A/B/C/恢复四态渲染、无 JS 运行错误；小红书持久 Profile 登录态只读探测 AUTH_VALID。


### 修复：采集六态正确落库 + 失效自动建恢复任务（冲刺6）
- 新增 `collector.classify_collect_state`，把采集结果归一为 SUCCESS/EMPTY/AUTH_REQUIRED/CAPTCHA/BLOCKED/NETWORK_ERROR 标准六态写入 collection_logs（修复旧版笼统 success/error、熔断被误判空结果的缺陷，guard 硬状态优先）；AUTH/CAPTCHA/BLOCKED 三类幂等自动创建 Auth 恢复任务，形成“失效→暂停→建任务→恢复续采”后端闭环。13 项单测通过、集成回归真机大写 SUCCESS。

### 修复：数据质量治理（冲刺7）
- 脏发布时间归一（captured 优先、昨天/前天/编辑于 MM-DD 跨年判断、非法月日不臆造）；`insert_note` 标题兜底（正文首句/作者回退，UPDATE 同步补存量），空标题与相对时间脏值清零。

### 新增：版本中心接入统一控制台（冲刺8）
- 统一控制台「系统」组内嵌版本中心（单页 iframe 不跳页，手机侧栏可进）；后端 9 接口只读实测、真机渲染 v5.8.5/同步态/历史/操作按钮正常，配合每日 08·18·24 定时同步与 30 分钟自动巡检，形成开发→成版本→推送 GitHub→可回滚闭环。

### 新增：ProxyPool 可插拔代理池接入（冲刺9，对齐《ProxyPool 补丁1.0》）
- 补齐 proxy_pool 模块的 Flask 最后一公里：可选导入、启动加载本机付费代理节点、独立健康巡检线程、`/api/proxy/status|check`（Basic、URL 脱敏）。总开关默认关闭（关闭等同直连原版），代理失败冷却切换、按平台策略回退直连，强制出海平台无节点不裸奔，不自动抓免费节点。11 项单测通过，付费代理 10808 真实健康检查出海成功（约 1.2s）。《交叉认证》补丁审计：采集风险五档/状态机/熔断/恢复已由 collector_guard 覆盖，多 Provider/交叉认证属母平台分期。

### 修复：双时间补齐 + 核心回归全绿（冲刺10）
- captured_at 空串老数据由旧采集列 collected_at 回填 492 条（只补采集时间）；publish_datetime 与 publish_date 双列一致清洗（8 条脏原文归一）；修复后空标题/采集时间缺失/发布晚于采集/脏时间全部为 0。5 个测试补项目根路径引导可独立运行，核心回归 16/16 全绿；上线就绪审计 44 表 integrity ok、subject_hit 64.6% 口径未弱化。

### 运维：运行态实例巡检（冲刺11）
- 新增 `scripts/inspect_instances.ps1` 只读诊断 8200/8201 监听归属与重复实例；实证多实例有采集锁兜底、无重复入库（同词同分钟重复=0），8200 历史重复实例的清理与版本切换按约定留待授权。

### 稳定：进程看门狗双探测 + 独立常驻
- 看门狗在“子进程退出检测”之外叠加 `/healthz` 端口健康探测，修复 Flask multiprocessing worker 原生崩溃、父进程不退导致的“假活”盲区：连续 3 次（约30s）端口不通即杀整棵进程树并重启；快速崩溃指数退避、最长冷却 5 分钟。
- 看门狗以隐藏窗口独立常驻进程方式启动，脱离交互式 shell 会话，避免会话回收连带停服（为“不在电脑前也能跑”打底）。

### 修复：小红书采集主链（真人 CDP 通道）
- 采集前清洗英文停用词/单字符/纯符号噪声关键词并去重限量；核心词深采、扩展反馈词浅采，单次任务由约 10 分钟降至约 3 分 20 秒，同时减少详情页风控暴露。
- 修复 `publish_datetime` 留空：入库时用平台 `publish_date` 回填缺失的发布时间，存量 874 条幂等补齐，且无一条与 `captured_at` 混淆；详情标题缺失时用正文首个非空行兜底。
- 真机确认笔记链接必须带 xsec_token（无 token 的 explore 链会 404），保留可打开的链接形态。

### 新增：采集风险评分引擎（对齐交叉认证补丁 §21/§22）
- collector_guard/risk_engine：0-100 连续风险分 → NORMAL / WATCH / THROTTLED / COOLDOWN / CIRCUIT_OPEN 五档，映射七态状态机；安全页/登录失效为硬熔断信号、限流为硬冷却；成功与时间推移使风险分衰减恢复，形成 健康→升高→熔断→恢复检查→逐渐恢复 闭环。只识别与降级，不绕过任何平台安全机制。10 项单测通过。

### 文档
- 存档《交叉认证 + 风险闸门 + 采集安全控制》为 docs/BLUEPRINT_brand_intel_platform.md 长期架构基线（多品牌 Workspace / AI Gateway / 交叉认证 / 证据链 / AI Data Gate 分期落地）。


## [5.8.5] - 2026-08-29

### 升级：「太古集团」→「品牌营销案例库」
- 以品牌主体为一级维度，点击品牌下钻其【事件库 + 小红书笔记库】（与品牌/太古舆情同逻辑）。
- 品牌增删接口：brand-save（新增或重新激活同名品牌并更新资料）、brand-remove（软删除 is_active=0，事件/笔记数据完整保留，重加同名自动恢复）、brand-collect（手动再采集补齐）、brand-detail（二级下钻：品牌信息+6 项统计+类型分布+事件库+笔记库）。
- swire_projects 无损迁移新增 kind/keywords/is_active/collect_status/created_at/updated_at（老库自动 ALTER 补列）；添加品牌后异步 CDP 关键词采集写入 swire_notes，环境受限优雅降级为“待补齐”，不阻塞、不伪装成功。
- 前端：品牌卡片矩阵（采集状态点、软删 ×、点击下钻）、品牌详情层（返回/采集补齐/6 统计卡/类型筛选/事件库/笔记库）、添加品牌弹窗；侧边栏更名「品牌营销案例库」。

### 升级：「十五周年专题」→「话题监测端口」（多任务泛化）
- 由单一固定活动泛化为通用话题监测：输入任务名 + 起止时间段 + 话题集合即可建任务，各自独立专题笔记库 / 快照 / 传播趋势；十五周年作为内置任务保留，接口默认值向后兼容。
- 新增 campaigns（任务列表 + 各任务话题/笔记/快照数 + 窗口状态）、campaign-save（新建/更新，话题支持换行与 ; , 分隔，key 自动生成、编辑复用）、campaign-toggle（active/paused 启停）；status/topics/timeline/notes/export 全部支持 campaign_key；手动 run 按所选任务自身窗口判断，暂停或窗口外拒绝并提示。
- 调度器由只跑固定活动改为遍历所有 active 且在各自时间窗内的任务；新增 _campaign_in_window()（固定任务走旧窗口，其余按自身 start/end/status，暂停不放行）。
- 前端重写为两层：监测任务列表（状态点/时间段/话题数/累计讨论互动/进入/编辑/启停）→ 任务详情（话题指标卡、时段传播趋势新增笔记量绿线、专题笔记库、立即更新、CSV 导出、编辑）；新建/编辑苹果风弹窗；侧边栏更名「话题监测端口」。
- tests/test_topic_port.py 全链路通过；真实网页 E2E：列表→进入详情（7 话题卡/趋势/空态）→新建任务自动进详情/话题正确→物理清理闭环。

### 升级：笔记 / 事件下钻分析 + 事件「发生日期」口径
- events 表新增 event_date（发生日期），幂等迁移；新增事件默认取 first_seen，更新不覆盖已确定的发生日期，显式传入优先。init_db 每次启动用 event_mentions 关联笔记的最早规范发布日期幂等校正；平台相对时间（“编辑于 / 小时前”）无法核实时置空，前端显示“待核实”，绝不展示脏相对时间。现有 392 事件校正后 385 条规范、7 条无法核实置空。
- 事件列表排序由 last_seen（发现日）改为 COALESCE(event_date,first_seen,last_seen)（发生日优先），符合“分析以事件发生日期为底层逻辑、采集发现日期仅作运维统计”的口径。
- 事件详情弹窗新增「发生日期」行，原“时间线”改为「发现窗口（系统采集发现，非发生日期）」，两者明确区分。
- 笔记详情弹窗新增「笔记正文」区块（content/body，保留换行、限高滚动，空正文明确提示“尚未抓取”），并补「命中关键词」「AI 洞察」、发布/采集时间分列、情感/风险合并展示。
- tests/test_event_date.py 回归通过（默认值/更新不覆盖/显式优先/输出无脏日期）；真实网页 E2E：事件弹窗发生日期 2026-08-03 与发现窗口 2026-08-06→08-12 正确分列，笔记弹窗 363 字正文与分析字段正常。

### 升级：报告中心自然周 + 双排重点笔记 + 全下钻
- 报告中心进入默认展示「最近一个自然周（周一至周日）」，可切日/周/月/年报与基准日期，非滚动近 7 天（后端 get_date_range 周一为起点，本周 2026-08-24→08-30 实测一致）。
- 周期事件归属口径由「发现窗口与周期重叠」改为「事件发生日期 event_date 落在周期内」（无发生日期回退 first_seen），排序同步按发生日期，符合“分析以发生日期为底层逻辑”。
- 报告预览重点笔记由单列改为一行 2 条双排网格（auto-fill minmax 300px），负面优先且负面卡浅红底加粗；事件卡与重点笔记卡均可点击下钻：事件→openEvent 聚合分析弹窗（含发生日期/发现窗口分列），笔记→openNote 详情分析弹窗（正文/命中词/研判），空正文诚实提示“尚未抓取”。
- 延续锁定口径：事件分析驱动、无事件/无负面写“无”不凑空表；日报只推负面、一天两窗口看过即归档；Excel 三表（概览/笔记明细/舆情事件）与 Word/CSV 导出保持。API 实测：本周 53 篇（正14/中35/负4）、重点事件 12 起（另 2 起单篇低关注折叠）、重点笔记 8 条负面优先且带 note_id；真实网页 E2E 双排与两类弹窗均通过。

### 核对：全局趋势日期口径
- 趋势/分析统一按笔记发布日期 publish_date（trends/global、dashboard/all 主趋势均已符合）；collected_at 仅用于今日采集量/采集区间筛选/报告核对等运维字面统计，不参与趋势。

### 修复 / 验证
- 修复 overview 排序误用不存在的 id 列（改为 sort,project_key）。
- tests/test_brand_library.py 全链路通过；真实网页 E2E：8 品牌矩阵、广州太古汇下钻 3 事件/200 笔记/35510 互动、添加→采集态→软删归档闭环，测试数据已清理（active 8、removed 0）。

## [5.8.4] - 2026-08-29

### 新增
- **太古集团全域营销事件/笔记库模块（swire_group.py）**: 不止舆情，覆盖太古汇/太古里/颐堤港 8 个项目（广州太古汇、成都/三里屯/前滩/西安太古里、兴业太古汇、颐堤港、集团品牌）与全类型事件（营销活动/展览艺术/联名快闪/开业周年/品牌调整/服务体验/公益可持续/舆情风险，正/中/负全收）。新建 swire_projects/swire_events/swire_notes 三表（幂等建表+公开事实种子 10 事件）；接口 `/api/swire/overview|events|notes`、POST `/api/swire/event`；广州太古汇笔记复用主库 notes（518 条），外延项目沉淀 swire_notes 待采集补全。前端新增侧边栏「太古集团」页（统计卡+项目 chips+类型筛选+事件时间线+笔记库，支持搜索/筛选/外链），E2E 验证渲染与筛选闭环。
- **静态资源缓存戳统一升至 5.8.4**，避免改了 CSS/JS 浏览器仍读旧缓存（此前机器人尺寸改了不生效即此因）。

### 修复
- **十五周年专题页卡“加载中”/无样式/错误 JSON 泄漏成标题**: static/topic_campaign.html 误引用根路径 `/topic_campaign.js|.css`（实际在 /static/，均 404），改为 /static/ 路径；topic_campaign.js 新增 escHtml/cleanErr，嵌套 CDP 报错（connectOverCDP ECONNREFUSED）不再截断 title 属性泄漏到卡片大标题，改为红色小字简短可读原因，去除 ANSI 转义符。
- **窄屏顶栏按钮文字溢出被裁/状态丢失**: 顶部采集数据/rednote/AI分析/导出报告 4 按钮裸文本包 `<span class="btn-label">`，≤768 断点可正确隐藏文字只留 34×34 图标；重写手机顶栏规则（避让菜单钮、标题 ellipsis）。
- **侧边导航图标质感统一**: 15 个 Unicode/emoji 混用图标（⌂◉△🏪📚）全部换成 lucide 线性 SVG，随 active 变蓝。
- **Zachary 机器人调大**: 桌面 76×90 → 100×112（同步修正被级联后方旧规则覆盖的两处尺寸），手机端仍保持 56px。

### 采集器纯自动化闭环（真实环境端到端跑通）
- **修复 base_dir 路径错位（关键 bug）**: collector_automation 的 self.base_dir 多上溯一级误指向 `D:\`，导致 CDP 兜底采集找不到 `rednote_collector.cjs`（报 `D:\rednote_collector.cjs 不存在`）、profile/history 误写到 D 盘根。改为本文件所在项目根；已把最新登录态 profile（44KB Cookies）与 collector_history.json 迁回项目目录。
- **新增 HTTP→CDP 自动降级**: 纯 Cookie HTTP 通道被风控（六态 BLOCKED/CAPTCHA/AUTH_FAILED）时，自动改用已启动的 CDP 真实浏览器（rednote_collector.cjs）采集并真实入库（含详情正文+评论+主体过滤），不再“浏览器白启动、HTTP 一拦就 0 条”；HTTP 与 CDP 均失败时按真实原因报错（区分需人机验证 / 慢网络 load_failed），**绝不把失败伪装成 0 条**。
- **新增 CDP 采集前热身 `_warmup_cdp`**: 慢网络/手机热点下从 about:blank 冷启动直 goto 搜索页会 45s 超时，先进入 explore 建连、带验证 cookie 再采集，显著提升成功率。
- **真实 E2E 验证（手机热点+刚被风控环境）**: 9222 从 0 自启 → 热身 → HTTP 识别 BLOCKED → 自动切 CDP → 真实入库（新增笔记正文 363/277/201 字等、评论入库）→ finally 自动关闭、9222 释放且无残留 Edge 进程。
- **新增 tests/backfill_detail_cdp.py 详情补抓**: 经已过验证的 CDP 浏览器分批补抓历史空正文笔记（--limit/--delay，断点续跑、遇 captcha 即停不硬刚），首批 5 条成功（空正文 204→197，正文 379/418/409 字等）。
- 合规边界：不绕过小红书人机验证，captcha 需在采集浏览器人工过一次，过后该 profile+IP 短期恢复。

### 数据治理（空表处置结论）
- 逐表核查：web_topics(83)/web_events(20)/weekly_events(30)/notification_logs(3) 均非空且被代码引用；7 张空表（collection_counters/notification_config/review_logs/review_samples/review_tickets/web_sources/topic_campaign_notes）均为功能表、待对应功能运行后自然填充。**无废表、不删除**。web_topics/web_events 旧数据为早期灌入的旧小红书帖、前端未接，已由太古集团模块承接重建。

## [5.8.3] - 2026-08-29

### 修复（数据正确性）
- **事件相关笔记不再 0 条**: 事件详情“查看该事件相关笔记案例”原用事件类型词拼 keyword 模糊搜索，匹配不到真实关联笔记而显示 0 条。新增 `/api/events/<id>/notes`，优先走 event_mentions 关联表（event_id→note_id）取真实笔记、负面/高风险在前，关联缺失时用事件关键词兜底；前端 openEvent 改调该接口。实测“方所闭店”事件正确关联 7 条（4 负 2 正 1 中）。
- **负面审核剔除全网案例、详情不再 404**: `/api/negative/pending` 与 `/api/negative-review/stats` 原只按 sentiment 过滤，把导入的全网公关案例（宝格丽/拉夫劳伦/ZARA 等非太古汇、2022–2025）也列为待办，而详情接口有主体过滤导致一点“查看详情”即 Not found(404)。现两处统一补上与日报一致的主体 + 去重(is_duplicate) + 去噪(noise_type) 口径，待办由 51 收敛为 14 条且全部为太古汇笔记，每条详情均 200，统计 pending/confirmed/rejected/total/high_risk 与列表完全对齐；列表改为高风险优先、风险分降序。
- **数据分析页死模块修复**: page-analysis 缺 `analysisPageContent` 挂载容器，renderAnalysisPage 直接 return，只剩一个空的静态 trendChart 显示“暂无趋势数据”；同时合并接口 `/api/dashboard/all` 的 overview 漏带 trend。现补齐挂载容器（统计 6 卡 + 14 天趋势柱 + 8 类内容分类柱完整渲染），并在 dashboard/all 的 overview 内补同口径近 14 天 trend，主轮询不再缺趋势数据、不增加额外请求。

### 优化（UI / 响应式）
- **指标卡图标升级为 iOS 风渐变 Squircle**: 原 ■●△••• 文本符号配浅色底质感偏低，统一改为 38px 圆角渐变彩标 + 白色线性 SVG（蓝文档/绿笑脸/灰平脸/红哭脸/橙警告/紫脉冲），hover 微缩放，接近 iOS 设置图标质感。
- **修复横向溢出/图表裁切**: grid·flex 子项统一 min-width:0（metric-grid/home-cards/panel-row/bottom-grid/report-grid/ai-console-grid），首页紧凑风险行在小卡片内收为两列、隐藏趋势/状态列，html·body 禁止横向滚动；全站 14 个页面逐页扫描，横向溢出均为 0、无横向滚动条，390–1440 宽度下趋势/分类柱图标签完整。

### 验证
- 新增 tests/test_negative_event_api.py，6 项断言全过（待办非空、不含全网案例、每条详情经主体口径可见、事件经 event_mentions 可关联且负面在前、统计与列表一致）。
- 浏览器 E2E：事件关联笔记弹窗 7 条且可下钻笔记详情；负面审核 14 条全太古汇、查看详情正常；分析页 6 统计 + 14 趋势柱 + 8 分类柱；品牌页 viewBrand 下钻（翠园 18 篇/楼层/情感/最近笔记）正常；全站 14 页无 undefined/NaN、无横向溢出。
- 主体词过滤口径（SUBJECT_WORDS / subject_hit / 主体 SQL）未改内部实现，仅在缺失处补齐外壳调用。

## [5.8.2] - 2026-08-29

### 修复
- **采集六态错误状态机（核心）**: 采集结果由"成功/0条"二态升级为 SUCCESS/EMPTY/BLOCKED/AUTH_FAILED/CAPTCHA/NETWORK_ERROR 六态。xhs_cookie_search.js 基于最终 URL、接口 error_code（如 300012）、验证码/登录页精确分类；xhs_cookie_bridge.py 聚合任务级 task_state（含 PARTIAL_BLOCKED），逐关键词写 collection_logs（被拦截时 collected_count 记 NULL，绝不伪装成"0 条正常"）。修复一处成功采集被正文风控词频误判为 BLOCKED 的缺陷；清理旧 v2 采集器把英文句子按空格拆成单词（Chinese/and/the…）的历史脏日志。
- **采集自动熔断与测试旁路**: 半数以上关键词被拦截/网络失败时写 xhs_circuit.json 熔断，自动任务在恢复前跳过、手动可强制健康检查；新增 XHS_TEST_MODE=1 旁路冷却/新账号保护/熔断，端到端测试期可不冷却连续验证。新增 `/api/xhs/collect-health` 返回总状态/熔断/今日各态计数/最近批次。
- **日报数据完整性保护**: generate_today_summary 增加 collection_health 判定（熔断或当日采集全失败时标记不完整）；管理层摘要在此情况下输出"采集受平台安全限制、数据不完整、不作无舆情结论"，杜绝据空数据写"今日未发现舆情/风险较低"。
- **Zachary 换用设计稿 PNG 形象**: 停用 Three.js 3D（避免双外观叠加），悬浮球改用 robot_open/close.png（黑球身体+紫光猫耳+青色耳机+NOMI 液晶脸），新增 zachary_png_face.js 双表情 3.2s 淡入淡出与紫青呼吸光晕；拖拽、点击开聊天、X/遮罩关闭、系统知识问答全部保留并经浏览器 E2E 验证（问答数据与仪表盘实时一致）。
### 修复（历史）
- **采集风控可见化**: xhs_cookie_search.js 在关闭前读取最终 URL/title，输出 blocked_reason（IP_RISK_OR_CAPTCHA/LOGIN_REQUIRED/EMPTY_NO_API）与 page_hint；xhs_cookie_bridge.py 累计 blocked、上报自适应降频，任务被拦截时明确提示"IP 存在风险，请切换网络"，不再静默返回"同步完成 0 条"。前端一键更新被拦截时同步弹明确提示。
- **设置页口径对齐**: 采集频率由写死的"每 90 分钟"改为真实策略（8:05–23:05 错峰约 9 次/天、每次后冷却 1h、手动一键 3 次/天）；品牌/业态数字由过时的 199/9 统一为数据库与 API 一致的 198 品牌 / 8 业态。
- **Zachary 3D 加载修复**: three.js 外网 CDN（jsdelivr r160 已移除 UMD）返回 404 导致 3D 形象不加载，改为本地化 static/js/vendor/three.min.js（r160），离线可用、不依赖外网。
- **静态资源缓存统一**: 全部 CSS/JS 统一 ?v=5.8.2，修复改代码后浏览器强缓存不更新的问题。
- **案例分类中文化**: 案例库分类标签与下拉由英文 key（service_attitude 等）统一中文映射，补全为 12 个中文分类，消除英文残留。

### 优化
- **Zachary 形象**: 主体荧光白、辉光/猫耳/耳机统一荧光浅蓝，面部改为 Nomi 风格横椭圆深色液晶屏 + 浅蓝发光表情点，保留紫色星粒、透明背景、拖拽不出界。
- **版本统一**: app.py / run_production.py / 前端兜底 / 静态资源全部对齐 5.8.2。

### 验证
- 服务以 waitress 生产模式运行，17 线程（含重新启用的整点自动采集/日报/周报调度线程），内存约 66MB。
- 浏览器逐页 E2E：overview/notes/events/reports/brands/calendar/cases/negative/settings 共 9 页无 undefined/NaN，console 0 错误；机器人聊天开/关正常、3D 挂载成功；事件详情中文化+关联笔记下钻正常。
- 已知外部边界：当前出口 IP 被小红书风控（error_code=300012），Cookie 本身有效，需切换网络（公司网络/手机热点）或改用有头真实登录 profile，系统已按"检测→降频→告警→人工"处理，不硬刚风控。

## [5.7.0] - 2026-08-28

### 新增

#### 短期修复
- **app.py结构修复**: app.run()从第2577行移到文件最后，修复后面140行路由无法访问的问题
- **前端9个API接入确认**: 全部9个v5.7.0 API已在前端JS中调用（trends/publish-buckets/dashboard-changes/weekly-events/web-discovery/brand-industry/ai-providers/ai-analyze-v570/negative）

#### 中期4项基础设施
- **数据库迁移脚本** (`database_migrations.py`): 统一schema管理，v0→v8迁移，自动备份，避免升级数据丢失
- **端到端测试** (`test_e2e.py`): 12个测试点全覆盖，采集→入库→分析→报告全流程验证，100%通过
- **日志系统完善** (`logger.py`): 统一日志格式，按大小/时间轮转，多日志器分类，自动清理
- **配置管理统一** (`config.py`): 统一.env+JSON配置，31个配置键，验证功能，避免硬编码

#### 监控告警
- **系统监控模块** (`monitoring.py`): 健康检查、告警通知、后台监控、监控报告
- **CI/CD自动化** (`ci_cd.py`): 测试→构建→部署→发布全流程自动化

#### 模块化重构
- **采集引擎V2** (`collector_v2/`): 模块化架构，PlatformCollector基类、BrowserSession独立登录管理、XHSClient独立HTTP层、数据处理流水线、智能调度器
- **重构蓝图** (`app_refactor_blueprint.py`): app.py模块化重构参考，8个蓝图定义，4阶段迁移计划

#### 新增功能模块
- **人工复核闭环** (`review_workflow.py`): 负面舆情二次确认、工单流转、样本回流、模型迭代
- **微信通知中心** (`wechat_notifier.py`): 4种渠道、消息去重、失败重试、推送日志
- **微博采集器** (`collector_v2/weibo/`): 基于PlatformCollector基类，不占用小红书采集次数
- **collector_v2接入补丁** (`collector_v2_integration.py`): 可选启用新采集器，不破坏现有系统

#### SimHash语义去重优化
- 阈值从3调整为6，短文本更准确
- 修复is_duplicate返回False时距离硬编码为0的bug
- 新增debug_distance调试方法

#### 品牌业态数据更新
- 从官方零售清单2026.08.20更新品牌目录
- 198个场内品牌，8大业态
- 每个品牌含英文名/中文名/业态/楼层/铺位号

### 修复
- app.py app.run()位置错误（中间启动导致后面路由无法注册）
- SimHash阈值过低导致相似文本无法识别
- SimHash返回值不准确，无法调试
- 品牌目录数据不准确（旧版349个，更新为官方198个）

---

## [5.6.3] - 2026-08-27

### 新增
- 小红书Cookie数据桥
- 智能调度器（每日12次，手动3次+自动9次）
- 新账号保护机制
- 负面舆情二次确认数据库字段
- Zachary智能机器人（3D浮动AI助手）

### 修复
- 采集器稳定性
- 主体过滤准确性
- 报告导出格式

---

## [5.3.0] - 2026-08-20

### 新增
- 系统名称固定为"广州太古汇·舆情监测系统"
- 首页恢复左侧导航与模块分布
- Apple/iOS风格微交互
- 热门话题正面/中性/负面分类
- 5G远程访问（Cloudflare Tunnel）

---

## 早期版本

详见项目历史记录。

## [5.8.1] - 2026-08-29 前端显示与报告质量修复
- 修复案例详情弹窗标题undefined、事件概述缺失（兼容pr_case_library的name/event/response与case_library两套字段）
- rednote采集从顶部主操作区移除，改为系统设置内的备选采集入口（主采集固定账号保护优先）
- 品牌详情弹窗实时关联该品牌笔记（标题/正文匹配），补总/正/中/负统计与最近笔记列表
- 报告中心默认改为自然周期（周报=本周一至今、月报=本月1日、年报=本年1.1），切换类型联动，后端导出支持自定义起止日期
- Word/Excel导出按运营明细表重做（体裁/赞评藏享/互动合计行，曝光观看点击率涨粉无采集来源记—），概览补互动/体裁/日均、新增高互动Top与分类占比
- 新增/favicon.ico路由(204)消除控制台404；pytest 46项全绿，浏览器E2E遍历案例/品牌/报告/日历通过

