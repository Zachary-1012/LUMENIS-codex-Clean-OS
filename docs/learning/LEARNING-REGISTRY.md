# LEARNING-REGISTRY · 统一学习资产索引

> 用途：所有 GitHub / 业界研究成果必须沉淀于此，不允许只停留在聊天记录。
> Research ID 规则：`LR-YYYYMMDD-NNN`。状态：VERIFIED（已用一手来源核实）/ CANDIDATE（候选，待 Staging）/ ADOPTED（已采用）/ REJECTED（明确不采用）/ REFERENCE-ONLY（只学思想不引依赖）。
> 数据取数日：**2026-08-31**，star/license 来自 GitHub REST API 一手返回；license 显示 NOASSERTION 表示 GitHub 未自动识别标准 SPDX，**以该仓库 LICENSE 原文为准**。
> 铁律：只学习架构思想 / 工程模式 / 算法 / 治理与测试方法 / 数据结构 / 可验证机制；**不直接复制第三方源码**，不把受限许可代码包装成自研。任何依赖引入走 THIRD_PARTY_LICENSE_AUDIT + SBOM。

## 一、研究总表（对应任务书 A–S 方向）

| Research ID | 方向 | 项目 | GitHub | License | star(08-31) | 结论 | 关联 Feature/Asset |
|---|---|---|---|---|---|---|---|
| LR-20260831-001 | A 能力/服务目录 | Backstage | backstage/backstage | Apache-2.0 | 34283 | REFERENCE-ONLY（学 Catalog 模型，不引重型平台） | FEATURE-REGISTRY / ASSET-REGISTRY |
| LR-20260831-002 | B 架构治理 | ADR（Architecture Decision Records） | joelparkerhenderson/architecture-decision-record | 见仓库 LICENSE | 16778 | ADOPT-思想（轻量 Markdown ADR，已存在 ARCHITECTURE_DECISION_RECORD_20260830） | docs/governance |
| LR-20260831-003 | C 来源/证据 | in-toto | in-toto/in-toto | Apache-2.0（以仓库为准） | 1035 | REFERENCE-ONLY（学 Attestation/链路证据结构） | app_evidence_records / Evidence |
| LR-20260831-004 | C 供应链等级 | SLSA Generator | slsa-framework/slsa-github-generator | Apache-2.0 | 596 | REFERENCE-ONLY（学"分级+可验证产物"思想） | Release Gate |
| LR-20260831-005 | D/E 追踪/可观测 | OpenTelemetry Python | open-telemetry/opentelemetry-python | Apache-2.0 | 2607 | CANDIDATE（先 structlog，量大后再 OTel） | SYS-001 / health |
| LR-20260831-006 | E 指标 | prometheus_client | prometheus/client_python | Apache-2.0 | 4363 | CANDIDATE（/metrics 后续暴露） | SYS-001 |
| LR-20260831-007 | E 结构化日志 | structlog | hynek/structlog | MIT/Apache（以仓库为准） | 4937 | CANDIDATE（统一日志键，利于审计/E2E Evidence） | 全链日志 |
| LR-20260831-008 | F 依赖图 | pydeps | thebjorn/pydeps | BSD-2-Clause | 2105 | ADOPT-工具（只读生成模块依赖图，不进运行时） | module_graph.json |
| LR-20260831-009 | F/G 图结构/关系 | NetworkX | networkx/networkx | BSD（以仓库为准） | 17236 | CANDIDATE（事件关系图谱算法，event_graph） | EVT-002 |
| LR-20260831-010 | G 代码智能 | tree-sitter | tree-sitter/tree-sitter | MIT | 26804 | REFERENCE-ONLY（未来多语言静态解析，当前正则足够） | asset_scan |
| LR-20260831-011 | H/S 多仓/版本治理 | Changesets | changesets/changesets | MIT | 12344 | REFERENCE-ONLY（学"变更单+版本+changelog"绑定） | 版本中心 |
| LR-20260831-012 | S Monorepo 平台 | Nx | nrwl/nx | MIT | 29285 | REJECT（过重，三仓独立，不引入构建体系） | — |
| LR-20260831-013 | I 安全迁移 | Alembic | sqlalchemy/alembic | MIT | 4357 | CANDIDATE→ADOPT（DB 向后兼容迁移/回滚，51 表治理） | schema_version / 迁移 |
| LR-20260831-014 | J 浏览器自动化 | Playwright Py | microsoft/playwright-python | Apache-2.0 | 14965 | ADOPT（主浏览器测试/运行基础） | human_browser/cdp_helper |
| LR-20260831-015 | J 浏览器自动化 | Selenium | SeleniumHQ/selenium | Apache-2.0 | 34428 | DEPRECATED 候选（本仓 0 真 import，回归后退） | CAPABILITY-OWNERSHIP §9 |
| LR-20260831-016 | K 采集框架 | Crawlee Py | apify/crawlee-python | Apache-2.0 | 9479 | REFERENCE-ONLY（学 RequestQueue/自动限速/去重，不换采集主链） | collector 链 |
| LR-20260831-017 | K 爬虫框架 | Scrapy | scrapy/scrapy | BSD-3-Clause | 64136 | REJECT（重型异步框架，与真人 CDP 路线不符） | — |
| LR-20260831-018 | L 限流 | slowapi | laurentS/slowapi | MIT | 2051 | CANDIDATE（对外 API 限流，保护自身服务） | 对外 API |
| LR-20260831-019 | L 重试退避 | tenacity | jd/tenacity | Apache-2.0 | 8769 | ADOPT-候选（NETWORK_ERROR 指数退避，替代手写重试） | 调度/采集恢复 |
| LR-20260831-020 | L 退避 | backoff | litl/backoff | MIT | 2694 | 备选（与 tenacity 二选一，避免重复依赖） | 同上 |
| LR-20260831-021 | L 熔断 | circuitbreaker | fabfuel/circuitbreaker | 见仓库 LICENSE | 523 | REFERENCE-ONLY（学状态机，本仓熔断逻辑自研且贴合平台，不换） | RISK-002 |
| LR-20260831-022 | M 调度 | APScheduler | agronholm/apscheduler | MIT | 7619 | ADOPT（进程内轻量调度，契合动态频率状态机） | MON-003 |
| LR-20260831-023 | M 分布式调度 | Celery | celery/celery | BSD（以仓库为准） | 28842 | REJECT（需 broker/worker，单机场景过度复杂） | — |
| LR-20260831-024 | N 测试 | pytest | pytest-dev/pytest | MIT | 14462 | ADOPT（统一 L0–L10 入口） | tests/ |
| LR-20260831-025 | O 生产 WSGI | gunicorn | benoitc/gunicorn | 见仓库 LICENSE | 10663 | REJECT-on-Windows（**不支持 Windows**；Linux 云部署时再用） | 部署 |
| LR-20260831-026 | O 进程守护 | supervisor | Supervisor/supervisor | 见仓库 LICENSE | 9111 | REJECT-on-Windows（**仅 Unix**） | 部署 |
| LR-20260831-027 | O 生产 WSGI(Win) | waitress | Pylons/waitress | ZPL/MIT 类（以仓库为准） | 1598 | ADOPT-候选（**Windows 可跑**的生产 WSGI，替代开发服务器） | 部署 |
| LR-20260831-028 | O 文件看门/自愈 | watchdog | gorakhargosh/watchdog | Apache-2.0 | 7404 | CANDIDATE（源码变化检测→自动版本保存触发） | SYS-002 版本中心 |
| LR-20260831-029 | Q 学习库/向量 | sqlite-vec | asg017/sqlite-vec | Apache-2.0 | 8061 | ADOPT-候选（SQLite 向量扩展，单文件、零额外服务，做学习/案例语义检索） | SICI 学习库 / AI-001 |
| LR-20260831-030 | R 设计 Token | Style Dictionary | amzn/style-dictionary | Apache-2.0 | 4793 | REFERENCE-ONLY（学 token 编译/多端输出，UI ⑨ 用原生 CSS 变量即可） | UI-FEATURE-MAP |
| LR-20260831-031 | 依赖/环境复现 | uv | astral-sh/uv | Apache-2.0 | 89277 | CANDIDATE（极速锁定/复现环境，Staging 一致性） | Staging Runtime |
| LR-20260831-032 | 安全签名 | PyJWT | jpadilla/pyjwt | MIT | 5696 | CANDIDATE（session/token 签名，替代裸存） | AUTH-002 |
| LR-20260831-033 | Flask 签名 | itsdangerous | pallets/itsdangerous | BSD-3-Clause | 3131 | 已是 Flask 生态（随 Flask，用于签名/会话） | AUTH |

### UI/UX 设计工程研究（2026-08-31 增补，详见 `docs/learning/ui/`）
| ID | 方向 | 标杆 | 官方/来源 | 采用结论 | 关联 |
|---|---|---|---|---|---|
| LR-20260831-034 | R 设计体系 | GitHub Primer | primer.style | ADOPT：token 三层 + functional color + 密度档 | Design System |
| LR-20260831-035 | R 高密度/命令 | Linear | linear.app | ADOPT：⌘K、紧凑列表、Drawer 不跳页 | 全局交互 |
| LR-20260831-036 | R 黑白灰工程感 | Vercel Geist | vercel.com/geist | ADOPT：近黑主操作、边框优先、Skeleton | Design System |
| LR-20260831-037 | R AI 分区 | OpenAI 产品 | platform.openai.com | REFERENCE：AI/系统/人工三分区，仅 AI 区 | AI-001 |
| LR-20260831-038 | R 安全控制台 | Anthropic Console | console.anthropic.com | ADOPT：密钥脱敏、危险确认 | SETT/AUTH |
| LR-20260831-039 | R 列表-详情 | Stripe Dashboard | stripe.com | ADOPT：列表+抽屉、数字对齐、向导 | 笔记/事件/报告 |
| LR-20260831-040 | R 监控驾驶舱 | Datadog | datadoghq.com | ADOPT 结构/REJECT 高饱和配色 | CTH 总览 |
| LR-20260831-041 | R 事件生命周期 | Sentry | sentry.io | ADOPT：Issue 流/严重度/Evidence | 事件中心/DCC |
| 动效标尺 | Motion | 行业公开经验（100/200/300ms、4-8pt、小半径） | 见 ui/MOTION-INTERACTION-PATTERNS | ADOPT，数值固化进 Design System §10 | 全局 |

## 二、结论分布
- **可直接采用（工具/库，需走 Staging + License 审计）**：pydeps（只读工具）、Playwright、APScheduler、pytest；候选优先：waitress（Windows 生产 WSGI）、sqlite-vec（学习库）、tenacity（退避）、alembic（迁移）。
- **只学思想不引依赖**：Backstage、in-toto/SLSA、Crawlee、Style Dictionary、Nx 治理、circuitbreaker、tree-sitter。
- **明确不采用**：Nx、Celery、Scrapy（过重/路线不符）；gunicorn、supervisor（Windows 不支持，仅未来 Linux 云部署备选）。
- 详见 `CASE-STUDIES.md`（逐案例字段）、`TECHNOLOGY-COMPARISON.md`（择优评分）、各 PATTERNS 文件。

## 三、智谱旗舰工程第二意见（2026-09-03，per_call 1 次）
| 来源 | 资产 | 结论 | 状态 | 关联 |
|---|---|---|---|---|
| 智谱 glm-5.3 架构评审（ZHIPU-ENGINEERING-REVIEW-20260903.md） | 1.CTF: risk_engine 熔断状态为内存态，重启即丢→冷却违约/风控风险，需崩溃持久化；2.SQLite 单写+54表+时序快照，需 VACUUM INTO 定期备份+metric 独立DB；3.CDP 端口/代码沙箱/Flask 绑定=攻击面，须绑 127.0.0.1；4.统一时间源(utcnow)+单一snapshot写入；5.browser_lifecycle 统一CDP生命周期 | ADOPT（逐项最小落地） | P0-A / P0-G / 备份 / 安全 |

## 四、智谱源码级交叉验证方法（2026-09-03，per_call 1 次）

- **Research ID**：LR-20260903-002
- **来源**：智谱 glm-5.3 对 ZBC 脱敏源码头（docstring/import/关键签名）的逐项核对
- **方法（可复用，已脚本化思想）**：把 CAPABILITY-REGISTRY 声称"✅已落地"的 Capability + 对应文件真实源码头喂给大模型，要求"只依据证据、不臆测、无法确认标需补证"，输出 OK/疑似失实/需补证 三项结论。**防假闭环（文档说完成、代码没完成）的关键手段**。
- **发现**：① risk_engine 声称"六态生命周期"与源码不符——真实为 `state.py` 七态(HEALTHY/WARNING/COOLDOWN/PAUSED/AUTH_REQUIRED/NEED_VERIFY/NETWORK_ERROR) + `risk_engine.py` 五风险档(NORMAL/WATCH/THROTTLED/COOLDOWN/CIRCUIT_OPEN)，已按源码修正 CAPABILITY-REGISTRY；② dev_exec "JSONL审计"头部无据但实现真实存在(data/audit/dev_exec_audit.jsonl)→Registry 正确；③ 其余 8 项 OK。
- **教训**：①给模型的源码片段必须**真实包含内容**（脚本 bug 曾导致传空→模型正确拒绝臆断）；②"源码头"足以初判，但涉及状态枚举/审计逻辑需看实现体；③文档状态口径必须与源码一致，不一致时**以源码为准改文档**。
- **沉淀**：`docs/learning/P0B-CAPABILITY-CROSSCHECK-20260903.md`
- **状态**：ADOPT（方法）；发现已修复
### 五、GitHub 前沿研究：采集合规自适应 / AI 网关路由 / Agent 可观测（2026-09-03，详见 GITHUB-FRONTIER-20260903-COLLECTOR-AIGATEWAY-OBSERVABILITY.md）

| Research ID | 方向 | 项目 | GitHub | License | 结论 | 关联 |
|---|---|---|---|---|---|---|
| LR-20260903-003 | K 采集自适应 | Scrapling | D4Vinci/Scrapling | MIT 类 | ADOPT-部分（**AutoThrottle 思想**：补 jitter + Retry-After；拒绝其 stealth/bypass，守合规红线） | collector_guard/rate_limiter |
| LR-20260903-004 | K 礼貌爬取 | Polite Scraper 五习惯 | link.sc / Firecrawl | 文 | ADOPT（per-host 并发 + **jitter 随机化** + Retry-After + 激进缓存 + 背压；本轮已落地） | collector_guard/guard |
| LR-20260903-005 | L 动态限流 | GitHub API Pacer | 社区方案 | 文 | ADOPT-方法（动态水位感知优于静态计数；429=软信号非硬熔断） | analyzer/rate_limiter |
| LR-20260903-006 | AI 网关 | LiteLLM | BerriAI/litellm | MIT | REFERENCE-ONLY（自研 intelligence.py+ai_budget 已覆盖核心；吸收 fallback cooldown + per-key budget 思想） | intelligence.py / ai_budget.py |
| LR-20260903-007 | AI 路由 | vLLM Semantic Router | vllm-project/semantic-router | Apache-2.0 | CANDIDATE（Signal/Decision 分离设计值得借鉴；任务量足够前不引入 embedding 分类器；登记 BACKLOG T-P1G-01） | AI Task Router |
| LR-20260903-008 | 观测/自愈 | TraceRoot | traceroot-ai/traceroot | 开源 | REFERENCE-ONLY（生产发现→golden dataset→离线 eval 循环 = Observatory+ZELL 成熟对标；登记 BACKLOG T-P0D-03） | zell_trace / observatory_feed |
| LR-20260903-009 | 观测/采样 | Tail-based Sampling | AgentOps/OTel | 文 | ADOPT-思想（指标全保/审计结构保/内容抽样保；ai_budget 记账分层） | ai_budget.py |
