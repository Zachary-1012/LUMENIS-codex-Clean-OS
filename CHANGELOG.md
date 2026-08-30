# 变更日志

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
