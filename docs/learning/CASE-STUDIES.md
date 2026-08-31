# CASE-STUDIES · GitHub 成熟案例研究（逐案字段）

> 取数 2026-08-31（GitHub API 一手）。字段：解决什么 / 核心架构 / 技术栈 / 成熟度 / License / 商业可用 / 我们现状 / 它强在哪 / 是否吸收 / 吸收成本 / 风险 / 对生产影响。
> 评级：成熟度按 star + 最近 push + 是否多方在用综合；"吸收"分 引依赖 / 学思想 / 不采用。

## A. 能力目录与架构治理

### LR-001 Backstage（backstage/backstage，Apache-2.0，34.3k★，TS，08-31 仍活跃）
- 解决：服务/组件/系统目录（Software Catalog）、文档、模板、插件化开发者门户。
- 架构：Catalog 实体 YAML（Component/System/API/Resource/Owner 关系图）+ 插件。
- 成熟度：CNCF 孵化级，大型组织广泛使用。商业可用：是（Apache-2.0）。
- 我们现状：已有 FEATURE-REGISTRY / ASSET-REGISTRY / CAPABILITY-OWNERSHIP（Markdown 版"目录"）。
- 强在：实体关系模型（spec.type/owner/dependsOn/providesApi），正是我们"Feature→Asset→Owner→API→DB"要的结构。
- 吸收：**只学 Catalog 实体关系模型**，不引 Backstage（Node 重平台，对单 Flask 项目是杀鸡牛刀）。成本：低（对齐字段）。风险：无。生产影响：零（文档层）。

### LR-002 ADR Architecture Decision Records（joelparkerhenderson/architecture-decision-record，16.8k★）
- 解决：重大架构决策用轻量文本（Context/Decision/Status/Consequences）随码版本化。
- 现状：本仓已有 `docs/ARCHITECTURE_DECISION_RECORD_20260830.md`，方向一致。
- 吸收：**采用 ADR 模板与编号**（adr-NNNN-标题，状态 Proposed/Accepted/Superseded），替代多份并行 PRODUCTION_BASELINE。成本：低。风险：无。生产影响：零。

## C/D/E. 证据、追踪、可观测

### LR-003 in-toto（Apache-2.0，1.0k★，Py）/ LR-004 SLSA Generator（Apache-2.0，0.6k★，Go）
- 解决：链路"谁在什么材料上做了什么步骤产出什么"的可验证 attestation；SLSA 给构建成熟度分级。
- 强在：Evidence 不是日志堆积，而是"步骤+材料+产物+签名"的链。
- 吸收：**学证据结构**——我们的 app_evidence_records / E2E Evidence 应固定 {commit,version,env,step,input,output,result,artifact} 字段；不引入 in-toto 工具链。成本：低。风险：无。

### LR-005 OpenTelemetry Python（Apache-2.0，2.6k★）/ LR-006 prometheus_client（Apache-2.0，4.4k★）/ LR-007 structlog（4.9k★）
- 解决：trace/metrics/log 统一；/metrics 指标；结构化日志键。
- 现状：有 /healthz、system_health、collection_logs、schedule_decisions（调度依据已较全）。
- 吸收：**分阶段**——先 structlog 统一日志键（CANDIDATE），再 prometheus_client 暴露 /metrics（CANDIDATE）；OTel 待真有多服务/链路再上，避免现在过度。成本：中。风险：低（旁路加，不改业务）。生产影响：增量、可回滚。

## F/G. 依赖图与代码智能

### LR-008 pydeps（thebjorn/pydeps，BSD-2-Clause，2.1k★）/ LR-009 NetworkX（BSD，17.2k★）/ LR-010 tree-sitter（MIT，26.8k★）
- pydeps：静态 import 依赖图（我们①已自写 asset_scan 产出 module_graph.json；pydeps 可作为交叉校验的第二只眼，**只读工具不进运行时**）。
- NetworkX：图算法，可用于 event_graph 的关系/连通/聚类分析（CANDIDATE，替代手写遍历）。
- tree-sitter：增量语法树解析，强但当前我们正则+AST 已够，REFERENCE-ONLY。
- 成本：pydeps 低；networkx 中。风险：低。生产影响：零（离线分析）。

## H/S. 仓库与多仓治理

### LR-011 Changesets（MIT，12.3k★）/ LR-012 Nx（MIT，29.3k★）
- Changesets：每个变更带"变更单→版本→changelog"，发布时汇总。强在把"改了什么、影响谁、版本号"绑定。
- Nx：monorepo 任务图/缓存/依赖边界。**三仓独立、非 monorepo，Nx 过重 → 不采用**；只学"依赖边界约束（enforce boundaries）"思想。
- 吸收：学 Changesets 的变更单字段，落到我们的 CHANGE-MAP + 版本中心；不引 JS 工具链。成本：低。生产影响：零。

## I. 安全迁移

### LR-013 Alembic（sqlalchemy/alembic，MIT，4.4k★，08-14 活跃）
- 解决：DB schema 版本化、upgrade/downgrade 可回滚迁移、自动生成迁移脚本。
- 现状：51 张表、有 schema_version 表但迁移靠手写/向后兼容；红线要求"改 schema 必经 Gate + 可回滚"。
- 吸收：**CANDIDATE→建议采用**。先用 alembic 对现有 51 表做一次 baseline 快照（autogenerate 后人工核对，不直接跑），之后所有改表走 upgrade/downgrade。成本：中。风险：中（首次 baseline 必须在 Staging 副本验证，绝不碰生产库）。生产影响：零（只读 baseline + 迁移脚本评审后才用）。

## J/K. 浏览器与采集

### LR-014 Playwright Python（Apache-2.0，15.0k★）vs LR-015 Selenium（Apache-2.0，34.4k★）
- Playwright：自动等待、trace viewer、网络拦截、codegen、单浏览器多 context、官方 CI/Docker 支持。
- 现状结论一致：Playwright 为主要浏览器基础；**本仓 Selenium 0 真 import → DEPRECATED 候选**，Staging 回归后才从 requirements 退出（不现在删）。
- 吸收：已采用方向；补 trace/screenshot 作为 E2E Evidence。成本：低。风险：低。

### LR-016 Crawlee Python（apify/crawlee-python，Apache-2.0，9.5k★，08-31 活跃）/ LR-017 Scrapy（BSD-3，64.1k★）
- Crawlee 强在：RequestQueue（去重/重试队列）、**自动限速（autoscaled pool，按反馈调并发）**、session 轮换、router、存储抽象——与我们"动态频率+状态驱动冷却+平台隔离"理念同构。
- Scrapy：成熟重型异步爬虫框架，但与我们"真人 CDP 会话、合规、低频、保护账号"路线不符 → 不采用。
- 吸收：**只学 Crawlee 的 RequestQueue/自适应并发/会话隔离数据结构**，落到统一 Scheduler 策略字段（minimum_interval/max_frequency/backoff…），不换采集主链、不引框架。成本：中。风险：低（设计层）。生产影响：零。

## L. 限流 / 退避 / 熔断

### LR-018 slowapi（MIT，2.1k★）/ LR-019 tenacity（Apache-2.0，8.8k★）/ LR-020 backoff（MIT，2.7k★）/ LR-021 circuitbreaker（0.5k★）
- slowapi：Flask 限流（保护**我们自己的对外 API**，不是对抗平台）。CANDIDATE。
- tenacity：指数退避/抖动/重试条件，正好实现 NETWORK_ERROR"退避不连撞"。**ADOPT-候选**，与手写重试二选一，避免重复（backoff 为备选，不并引）。
- circuitbreaker：通用熔断器，学其 CLOSED/OPEN/HALF-OPEN 三态；本仓熔断贴合小红书 300012/验证码语义（自研更合身），**不替换**。
- 成本：低。风险：低。注意：这些只用于自身服务健壮性与网络重试，**绝不用于绕过平台风控/验证码**。

## M. 调度

### LR-022 APScheduler（MIT，7.6k★，08-30 活跃）vs LR-023 Celery（BSD，28.8k★）
- APScheduler：进程内 BackgroundScheduler/AsyncIOScheduler、持久化 jobstore、多种 trigger，轻量、单进程即可。
- Celery：需 Redis/RabbitMQ broker + worker 多进程，分布式强但单机过度。
- 结论：**APScheduler 契合**"统一 Scheduler 读平台策略/状态动态决定 next_run_at"；Celery 不采用（增加运维面，违背最小复杂度）。成本：低（项目已在用调度，规范化即可）。

## N. 测试

### LR-024 pytest（MIT，14.5k★）
- 统一 L0–L10（Syntax/Import/Startup/Health/API/DB/Page/E2E/Browser/Restart/Regression）入口、fixture、参数化、失败产 Evidence。**ADOPT**，配合 Playwright trace。成本：中（补用例）。风险：无（测试侧）。

## O. 部署 / 自愈（Windows 现实约束，重点）

### LR-025 gunicorn（10.7k★）/ LR-026 supervisor（9.1k★）—— **均不支持 Windows**
- gunicorn 是 Unix WSGI Server、supervisor 是 Unix 进程守护；在当前 Windows 主机无法原生运行。**结论：本地/Windows 阶段不采用**；仅当未来迁 Linux 云服务器时作为标准件。

### LR-027 waitress（Pylons/waitress，ZPL/MIT 类商业友好，1.6k★，08-30 活跃）
- 纯 Python、**跨平台含 Windows** 的生产级 WSGI Server，可多线程、可 behind 反代。
- 吸收：**ADOPT-候选**——Windows 上用 `waitress-serve` 替代 Flask 开发服务器作为生产入口（Linux 再换 gunicorn），接口不变。成本：低。风险：低。

### LR-028 watchdog（Apache-2.0，7.4k★）
- 文件系统事件监控。可用于"检测源码变化→触发自动版本保存（Git Commit/Push）"，正是版本中心自动保存机制需要的触发源。CANDIDATE。成本：低。风险：低（只触发、不自动改码）。

### 部署模式结论（详见 DEPLOYMENT-PATTERNS）
- 当前 Windows：waitress（WSGI）+ run_supervised 看门狗 + cloudflared（临时，后续固定域名/反代）+ Docker Desktop（healthcheck/restart:unless-stopped 自愈）作为可选项。
- 未来 Linux：gunicorn + systemd/supervisor + nginx + Docker。两条路径都满足"健康检查失败自动重启"。

## Q. 学习库

### LR-029 sqlite-vec（asg017/sqlite-vec，Apache-2.0，8.1k★，C 扩展）
- SQLite 向量搜索扩展，**零独立服务、单文件**，可与现有 monitor.db 体系同构，做案例/知识/事件语义检索。
- 吸收：**ADOPT-候选**，契合"不新增重型服务"原则；SICI 学习资产 + Zachary 案例库语义检索用。成本：中（需打包扩展、Staging 验证）。风险：中（C 扩展跨平台 wheel，需锁定版本）。生产影响：旁路新库/新表，不动生产库。

## R. 设计 Token

### LR-030 Style Dictionary（Apache-2.0，4.8k★）
- 设计 token 一次定义、编译到 CSS/多端。**学 token 分层（primitive/semantic/component）与命名**；UI ⑨ 用原生 CSS 变量即可，不引 Node 构建。成本：低（方法）。生产影响：零。

## 其他

### LR-031 uv（Apache-2.0，89.3k★）极速 Python 包/环境管理：用于 Staging 可复现环境与锁定（CANDIDATE，不强制替换现有 venv）。
### LR-032 PyJWT（MIT，5.7k★）/ LR-033 itsdangerous（BSD-3，Flask 自带生态）：会话/签名规范化候选；AUTH 域增强时评估，当前 Basic+v4 session 在用，不急于改。
