# 22:00 豆包推进指令｜公网平台化 + Ollama + 双产品适配

> 目的：作为 2026-08-30 22:00 起豆包本地执行的正式施工入口。
> 事实源：GitHub main 最新代码及仓库工程文档优先于历史聊天记录。

## 0. 执行纪律

开始前必须读取：
- AGENTS.md
- README.md
- CURRENT_BASELINE.md
- PROJECT_STATUS.md
- CHANGELOG.md
- DEV_LOG.md
- AI_POLICY.md
- ARCHITECTURE.md
- DEPLOYMENT.md
- DOUBAO_GITHUB_UPGRADE_PROTOCOL.md
- docs/BLUEPRINT_brand_intel_platform.md

不得凭历史方案直接改代码；先审计当前 main，再施工。禁止推翻稳定系统、删除生产数据、弱化广州太古汇主体过滤、把采集失败伪装成 0 条、把 UGC 当账号类型、把 AI 当最终事实来源。

## 1. 产品双层架构

产品 A：广州太古汇舆情监测系统。
产品 B：品牌传播与市场情报智能平台。

两者共享 Core，但配置、发布边界、客户/品牌数据隔离、版本血缘必须清晰。新能力优先嵌入现有 15 个 SPA + 独立话题监测页，不大量增加顶级菜单。

核心模型固定为：
WHO=传播主体（KOS/KOL/KOC/普通用户/媒体/官方/机构）
WHAT=内容（UGC/商业/官方/测评/体验/投诉/活动等）
WHAT HAPPENED=事件（营销/传播/舆情）
SO WHAT=品牌影响（传播贡献/情绪/风险/竞品/AI洞察/报告）

subject_type 与 content_type 必须严格分离；禁止 user_type=UGC。

## 2. 公网平台化

目标：手机、电脑通过 HTTPS 访问；后台 Worker/Scheduler 在页面关闭后仍运行。

推荐链路：Internet → HTTPS/Cloudflare Tunnel 或等价反向代理 → 本机 Web/API → Worker/Scheduler → SQLite/采集器/Ollama。

8200 不裸暴露公网；生产 DEBUG=false；后台接口必须鉴权；Cookie、Token、API Key、Secret 不得进入 GitHub、前端或普通日志。

部署分阶段：先保持现有 Python/Waitress 稳定架构完成公网访问，再考虑服务拆分/Docker，不为“容器化”而破坏现网。

## 3. P0 启动环境

优先解决当前全局 Python 与 .venv 不一致问题：生产启动入口必须固定使用同一 Python/依赖来源，并能双击/自启动稳定运行。启动器应检查 Python、依赖、数据库、Ollama、应用健康状态；不要让“本地手工 venv 能跑、双击失败”再次出现。

## 4. Ollama-only AI

生产默认：AI_PROVIDER=local；正式 AI Runtime=Ollama。

外部云端 AI 不得成为生产依赖；历史云端 AI 代码可暂留 Legacy/Optional，但默认关闭且不得被主链路隐式调用。

统一 AI Provider 接口，优先适配现有 ai_gateway/ai_analyzer，不重复造第二套架构。

新 AI 能力必须 Shadow Mode：系统规则先判断，Ollama 并行给出辅助结果，保存模型版本、Prompt 版本、输入摘要、结果、置信度、是否采纳、人工修正，再决定是否进入生产结论。

无 Ollama 时核心采集、主体过滤、去重、事件、风险、统计、报告仍必须运行。

## 5. 小红书 Auth Recovery

Cookie/session 在任何时候失效、需要验证、出现验证码/IP 风险时：
1. 采集状态进入 AUTH_REQUIRED / CAPTCHA / BLOCKED 等真实状态；
2. 暂停危险请求并进入冷却/熔断；
3. 系统内弹出 Auth Recovery Modal，不强制跳登录页；
4. 弹窗显示平台、账号、状态、原因、处理步骤；
5. 如当前合法采集流程能提供二维码/验证入口，则在弹窗中展示；
6. 提供“重新检测”“稍后处理”“我已完成验证”；
7. 用户完成合法验证后重新健康检查；
8. 验证成功才恢复 Collector/Scheduler。

禁止验证码破解、风控绕过、规避平台限制。不得把失效、验证或熔断显示为“0 条”。

当前采集频率采用动态调度，不再把固定 30 分钟/1 小时或固定时间点作为生产硬规则：健康时正常间隔；轻风险延长；验证暂停；300012/IP 风险熔断；恢复后健康检查并逐步恢复。

## 6. 采集主链保护

保留：账号/Cookie → Persistent Browser/CDP/Playwright → 搜索 → 发现 → 详情 → 评论 → 标准化 → 主体过滤 → 质量 → 去重 → 入库。

广州太古汇 SUBJECT_WORDS、SUBJECT_EXCLUDE_WORDS、subject_hit() 及所有 SQL 主体过滤口径不得弱化或绕过。

现有 CollectorGuard、六态状态机、CDP 自动恢复、质量日志等优先复用。

## 7. 品牌传播平台 Phase 1

在不破坏现网的前提下逐步接入：
- subject_type
- content_type
- event_relation
- 营销/传播/舆情三类事件
- 首页三类事件与主体/内容看板
- 舆情监测/笔记搜索主体类型与内容类型筛选
- 事件中心三类事件 Tab 与基础关系展示

后续 Phase 2/3：六维主体画像、事件生命周期/图谱、消费者需求洞察、品牌对标、因果溯源、综合报告、AI 辅助聚类与人工修正样本。

## 8. 数据库

任何迁移前先备份。不得 DROP 生产表、重建生产数据库或删除历史数据。新增字段/表必须通过现有迁移机制或兼容迁移实现，并执行 schema、计数、完整性和回滚检查。

保护 publish_datetime、captured_at、event_date、source_id、detail_status、comment_status 等数据口径。

## 9. 测试门禁

每个阶段必须执行：语法/导入、相关单测、数据库迁移、启动、API/蓝图、关键页面 E2E、JS 错误扫描、主体过滤回归、时间口径回归、采集状态机回归。

真实 E2E 未完成不得写“已完成”；计划不得写成实测结果。

## 10. GitHub 同步

每个施工阶段必须同步：代码、测试、CHANGELOG.md、DEV_LOG.md、PROJECT_STATUS.md、ARCHITECTURE.md/DEPLOYMENT.md（涉及则更新）。

Commit 使用 feat/fix/refactor/test/docs/chore 前缀，并记录：修改、原因、测试、数据库影响、风险、回滚点。

## 11. 第一轮只做

先完成“审计 → 备份 → P0 启动环境 → 公网运行模式设计/验证 → Ollama 健康检查 → Auth Recovery 与现有采集状态机联动核查”。

未经真实测试不得切换新采集器，不得一次性进行大规模重构。

最终验收：手机/电脑 HTTPS 访问、页面关闭后台仍运行、Cookie 失效可在系统内恢复、300012 不伪装成 0 条、Ollama 可选但不阻断核心系统、双产品 Core 边界清晰、GitHub 文档与代码一致。
