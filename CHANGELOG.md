# 变更日志

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
