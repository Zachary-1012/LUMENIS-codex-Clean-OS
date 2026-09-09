# LUMENIS 纯净产品重建、上线准备与持续闭环路线

状态：十二大类第 12 类交付物

结论：`ROADMAP COMPLETE / IMPLEMENTATION NOT STARTED / CURRENT RELEASE NO-GO`

## 1. 目标

本路线不是“重新写一套系统”，也不是把旧页面换皮。目标是在不丢失已验证能力、不破坏生产数据、不复制两套 Core 的前提下，把现有资产收敛为一个可上线、可追溯、可持续演进的 LUMENIS。

产品北极星：

```text
真实信号
→ 可验证理解
→ 有依据的决策
→ 有边界的创作与行动
→ 可衡量结果
→ 可复用学习
→ 进入下一轮业务生产
```

它不是普通 SaaS 后台，而是围绕传播、营销、运营、广告、创意和决策形成的生产生态。生态能力必须建立在 Production Truth 之上，不靠 AI 对话、菜单数量或动画制造产品感。

## 2. 执行红线

1. 只保留 CTH 与 BMP 两条业务产品线。
2. Shared Capability、SYSTEM、AI、Agent、Command、OSAI、GGI 不成为第三或第四产品线。
3. 新设计不复制旧线上 UI、菜单、布局和旧双核叙事。
4. 不删除任何尚未完成依赖追踪的源码、表、API、脚本、Provider 或知识资产。
5. 不覆盖、重建、清空现有数据库；迁移只在备份副本和隔离环境先验证。
6. 不把文件存在、测试通过、页面 200、配置有 Key、健康接口 `ok=true` 当作生产完成。
7. AI 不拥有 Production Truth、数据所有权、业务规则和最终风险边界。
8. 采集账号永久只读；不执行关注、点赞、收藏、评论、私信、发布、改资料、退出或切换账号。
9. 任一云 Provider、OSAI、GGI 或 Command 不可用时，LUMENIS 核心生产链继续运行。
10. 每次只允许一个 Writer；交接必须携带 Test + Evidence + Git Diff。

## 3. 当前输入基线

### 3.1 源码基线

- 纯净仓：`D:\LUMENIS_REBUILD\Z-Brand-Core`；
- 目标远程：`Zachary-1012/LUMENIS-codex-Clean-OS`；
- 当前纯净仓包含前十一类审计与 Heritage 索引，但尚未有可证明的纯净 Runtime；
- 原始远程 `Z-Brand-Core/main` 提供工程血缘，不自动成为上线基线。

### 3.2 两个真实 Runtime 候选

| Runtime | 源码/数据 | 事实 | 结论 |
|---|---|---|---|
| 8201 | `D:\Taikoo-monitor-new` | 真实运行、Basic Auth、1044 notes；数据/测试混合、35 FK 违规、落后远端 2 Commit | 生产资产候选，不可直接发布 |
| 8202 | `D:\Z-Brand-Core_MAIN_AUDIT` | 页面可访问、`--no-scheduler`、空业务库、UI 假健康 | 审计预览候选，不是纯净 Runtime |

不能从两个候选中凭名称选择“最新”。必须通过 Release Baseline Decision 明确唯一输入、数据迁移策略和回滚点。

## 4. 执行依赖图

### P0 强制前置原则

测试隔离和生产资产保护是任何写操作的首要前置。唯一 Runtime / Database 身份以及 `Evidence → Canonical Data → Metric` 真相链完成收敛前，禁止启动 UI 主链替换。新设计只能在隔离旁路中实现和验证，不得用视觉完成度掩盖数据或运行事实尚未闭环。

```text
P0-A 资产冻结与只读备份
  ↓
P0-B 唯一源码 / Runtime / DB 身份
  ↓
P0-C 测试隔离 + Migration 三路径
  ↓
P0-D Evidence / Canonical / Metric 单一真相链
  ↓
P0-E API / State / Permission Contract
  ↓
P0-F CTH / BMP / Shared / SYSTEM 路由与领域隔离
  ↓
P0-G Collector / Auth / Runtime 真实状态闭环
  ↓
P0-H AI / Agent 生产准入闭环
  ↓
P0-I 新设计旁路实现 + 双读验证
  ↓
P0-J Release Manifest / Build Provenance / Security Gate
  ↓
P0-K Clean Runtime / Browser E2E / Rollback Drill
  ↓
第 13 项最终验收
```

任何后续阶段不得绕过前置 Gate。P1/P2 可以并行研究，不能提前接管生产写入或公开发布。

## 5. P0：生产真相与可上线底座

### P0-A：资产冻结、备份与决策点

工作：

- 对 8201、8202、纯净仓、原工作区、便携包建立只读 Manifest；
- 记录 Commit、tree digest、文件清单、DB hash、schema、进程、端口、配置键名和数据时间范围；
- 对所有生产候选 DB 做只读 integrity/fk/schema/count 摘要；
- 保存可恢复备份，不把备份加入 Git；
- 建立人工批准的 Baseline Decision Record。

退出条件：任何后续修改都能回答“从哪个源码和哪份数据开始、如何回到这里”。

### P0-B：唯一 Runtime Identity

工作：

- 纯净仓成为唯一开发和构建源；
- Runtime 只能从不可变 Release Manifest 启动；
- `/healthz` 或受控 attestation 输出 `release_id/core_commit/tree_digest/product_mode/profile/schema/db_digest/worker_set`；
- 禁止同一产品同时以多个未标识目录提供服务；
- 8201、8202 在切换前保持并行只读观察，不直接关闭或覆盖。

退出条件：给定任意页面请求，可以追溯到唯一 Commit、构建产物、数据库和 Product Mode。

### P0-C：测试数据库隔离与 Migration

工作：

- 所有测试强制临时 DB，启动前后校验生产候选 DB hash/mtime 不变；
- 将 production/test/experiment 数据目录物理隔离；
- 修复 `canonical_data` 建表与 v9→v10 顺序；
- 分别验证 clean bootstrap、历史库 upgrade、生产副本 migrate、应用 rollback/read compatibility；
- 35/43 个外键违规只在副本中分析和修复，先形成逐行根因与迁移方案；
- 清理动作必须另行批准，不能在路线执行中默认发生。

退出条件：四条迁移路径均通过，失败可回滚，生产 DB 在测试期间零变化。

### P0-D：唯一数据真相链

工作：

- 为 External Record、Evidence、Canonical Data、Event、Case、Metric、Report 分配稳定 ID 和 owner；
- 建立 `canonical_id/evidence_id/source_id/subject_id/brand_id/time_basis/rule_version`；
- 对 `canonical_data` 与 `zbc_canonical_data` 做双读对账，不先删；
- 对 notes 直算、canonical 计算、metric snapshot 做同输入差异报告；
- 统一 `publish_datetime` 与 `captured_at`；
- 报告每个数字绑定 Function、Metric、Truth Table、period 和 Evidence；
- AI 派生字段单独存储，保留 rule result、AI result、human correction 和 final decision。

退出条件：选取真实样本能从 UI/Report 逐级回到原始证据，反向也能定位全部消费者；重复计算差异为 0 或有批准解释。

### P0-E：API、State 与 Permission Contract

工作：

- 为每个正式端点定义 request/response/error/state/schema/version；
- 统一 `OK/NO_DATA/NO_RUN/STALE/UNKNOWN/ERROR/BLOCKED/SESSION_EXPIRED`；
- `NO_DATA` 不等于 0，`NO_RUN` 不等于健康；
- 建立 Page → API → Function → DB → Evidence 矩阵；
- 收紧 `/api/auth/config`、Runtime/Health 摘要等认证例外；
- 不再向未认证调用暴露本机路径、数据库计数、Cookie 是否存在、内部仓库路径；
- Permission 默认 fail-close，高影响写入要求人类批准。

退出条件：Contract 测试和浏览器 Network 证明所有页面只消费注册端点，未经认证无法读取敏感运行事实。

### P0-F：纯净产品边界与路由

工作：

- 建立唯一 `product_mode`：`CUSTOMER_RELEASE` / `LUMENIS_PLATFORM`；
- CTH、BMP、Shared、SYSTEM 使用独立 Route/Capability allowlist；
- canonical BMP 使用 `/lumenis/bmp/*`，旧 `/zbmp/*` 进入显式兼容层；
- BMP 访问保护未配置时 fail-close，不回落显示 CTH；
- Subject/Brand selector 只改变 Context，不改写 Production Truth；
- CUSTOMER_RELEASE 在后端路由和能力注册层真正阻止 BMP/研发/实验能力，不只隐藏菜单。

退出条件：两种 Release 的 route map、API surface、DB access、worker set 和页面均符合 allowlist；不存在第四产品线。

### P0-G：Collector、Auth 与 Runtime 状态闭环

工作：

- 从 Collector 多实现中确定唯一 Orchestrator，其他转为 Adapter/Legacy；
- XHS 搜索、详情、评论分层，失败不静默为 0；
- Auth 全局弹窗表达账号、原因、暂停任务、人工验证和恢复；
- CAPTCHA/风控只停止、记录、冷却和等待合法人工验证，不绕过；
- Runtime Guardian 统一 Worker、Lease、Checkpoint、Retry、DLQ 与 Scheduler 真相；
- 移除测试 Worker/Task 对生产 Runtime 统计的污染；
- CTH 与 SYSTEM 必须消费同一状态对象。

退出条件：真实故障注入能在页面/API/Trace 中一致显示，并能在人工恢复后从 checkpoint 安全继续。

### P0-H：AI / Agent 生产准入

工作：

- 所有 Provider 只经 AI Gateway；
- Provider ACTIVE 必须有真实调用、模型、延迟、结果和 trace；
- 智谱失败自动降级至备用/本地 Ollama/确定性规则；
- 所有用户任务经唯一 Orchestrator；
- Specialist Agent 只能调用注册 Tool；
- 所有生产 effect 强制 Permission → Firewall → Fence → Idempotency → Approval → Evidence；
- 删除 LUMENIS 对 OSAI 内部 Python 模块的直接 import/subprocess 调用，改成版本化 Artifact Contract；
- AI 输出不可更新 Subject、事实时间、统计数量和最终风险规则。

退出条件：云端断开、Key 错误、Ollama 停止、Prompt Injection、越权工具和重复请求测试均通过，核心业务仍可完成。

### P0-I：新产品体验旁路建设

工作：

- 严格采用 Context → KPI/State → Change → Analysis → Evidence → Decision → Action → Outcome；
- 不复用旧页面结构作为设计模板；旧页面仅作为能力与消费者清单；
- 新 CTH 以 Subject、Event、Risk、Decision 为核心；
- 新 BMP 以 Brand、Campaign、Content、Audience、Evaluation 为核心；
- Shared Content/Podcast 从旧 ZBMP 语义解耦；
- 动态只表达趋势、事件生命周期、风险迁移、Evidence 增长和行动反馈；
- 新旧页面先并行读取同一 View Model，差异通过 Evidence 对账。

退出条件：真实浏览器验证页面无假数据、无旧产品线泄漏、无 Console/Network 错误，桌面与移动端均可完成核心决策任务。

### P0-J：安全供应链与 Release

工作：

- 建立阻断式 CI：compile、unit、integration、migration、API、browser、security、subject/time/report regression；
- 固定依赖、生成 SBOM、许可证与漏洞报告；
- 生成不可变 Release Manifest、artifact digest、签名/attestation；
- 构建来源证明绑定官方 source commit 和 build process；
- 安全验收映射 OWASP ASVS 5.0；
- 安全开发流程映射 NIST SSDF；
- Release 默认 OFF → SHADOW → CANARY → ENFORCE；
- 数据库只使用 expand → migrate → verify → contract，不做破坏性倒退。

退出条件：任意发布包可离线验证来源、内容、依赖、配置/Profile、Schema、测试和审批记录。

### P0-K：Clean Runtime 与切换演练

工作：

- 从纯净仓构建隔离候选，不连接真实生产 DB；
- 在生产副本上完成数据迁移和完整 E2E；
- CUSTOMER_RELEASE 在无 OSAI、无 Command、无云 AI 时完成核心链；
- LUMENIS_PLATFORM 同时验证 CTH/BMP/Shared/SYSTEM；
- 进行进程崩溃、DB lock、Provider down、Auth expired、网络失败、回滚演练；
- Canary 观察满足 SLO 后才允许人工批准切换；
- 旧 Runtime 先保留只读回退窗口，不直接删除。

退出条件：清洁 Runtime 七类证据全部通过，并完成一次可重复 rollback drill。

## 6. P1：完整产品能力重建

P1 只能在 P0 Truth Foundation 通过后进入生产。

### P1-CTH：商业运营工作空间

- Subject 工作台；
- Evidence 流与业务时间线；
- Event lifecycle 与 Case；
- Risk transition 与人工确认；
- Decision Room；
- Action/Outcome 复盘；
- 日报、周报、月报与专题报告。

### P1-BMP：品牌市场工作空间

- Brand Focus 与竞品/市场范围；
- Campaign Pulse；
- Content Universe；
- KOS/KOL/KOC/媒体/官方/普通用户六维画像；
- 营销事件 → 传播事件 → 舆情事件 → 品牌影响；
- 消费者需求与品牌对标；
- Evaluation 与下一步增长行动。

### P1-Shared：创作与学习闭环

- Evidence-informed brief；
- 内容、广告、活动、播客等资产候选；
- 版本、版权/授权、审批和发布准备；
- Outcome Measurement；
- Evaluation、Badcase、Golden Case；
- Learning Asset 的验证、采用、回滚和过期管理。

### P1-System：多平台和可靠性

- BasePlatformAdapter 正式收敛；
- XHS 稳定链完成后再启用 Weibo/Bilibili 等；
- 完整 Observability；
- SLO、错误预算、容量与性能基线；
- 多租户/多 Subject/多 Brand 数据与权限隔离。

## 7. P2：生态与多终端增长

P2 不新增产品线，只扩展同一 LUMENIS 生态的入口和网络效应。

### P2-1：创意与传播生态

- 从 Evidence/Insight 形成 Brief；
- 从 Brief 形成内容、营销、广告和运营资产；
- 从已批准资产形成受控 Activate 任务；
- 采集传播反馈并归因；
- 将结果回流 Evaluation 和下一轮决策。

### P2-2：多终端体验

- Web：深度分析与决策空间；
- Desktop：运行、采集、浏览器、批量工作；
- Mobile：风险、审批、事件和行动反馈；
- API：受控生态集成；
- Command：研发和发布验证，不进入业务 Runtime。

入口共享同一 State、Permission、Evidence 和 Product Context，不形成多个数据真相。

### P2-3：能力生态

- Versioned Capability Contract；
- 可安装但受权限限制的 Skill/Tool；
- Partner/Customer Profile；
- 模板、方法论、Evaluation 和 Learning Asset 市场；
- 任何第三方能力默认隔离、最小权限、可撤销、可审计。

### P2-4：持续智能

- 真实 Outcome 驱动模型与规则评估；
- 人工修正优先沉淀为规则、样本和 Evaluation；
- Provider 可替换；
- 模型升级先 Shadow/Canary，不直接接管 Production Truth；
- Heritage 资产按任务检索，不把旧 Runtime 恢复到生产。

## 8. LUMENIS 个性化设计原则

新体验要形成可识别的 LUMENIS 产品语言，而不是常规 SaaS 卡片墙：

1. **境**：用户始终处于明确 Subject/Brand/时间/范围之中。
2. **序**：事件、风险、传播和行动以因果与时间秩序展开。
3. **证**：任何判断都能一键回到 Evidence。
4. **势**：动态展示变化方向、速度、置信度和新鲜度。
5. **策**：页面终点是有依据的 Decision，不是更多图表。
6. **行**：行动有权限、有边界、有回执、有结果。
7. **复**：Outcome 回流 Evaluation，形成下一轮增长。

视觉与交互不复制 iPhone、Mac、Tesla 或 ChatGPT；借鉴的是一致性、低认知负担、端到端体验和生态扩展方式，最终形成序境自己的表达。

## 9. Release Manifest

每次候选发布必须包含：

```text
release_id
product_mode
core_commit / source_tree_digest
profile_id / profile_version / profile_digest
capability_set / route_allowlist_digest
db_schema_version / migration_range
api_contract_version / ui_contract_version
cross_repo_contract_versions
dependency_lock / SBOM / license / vulnerability result
artifact_digest / provenance / signature
test_evidence / security_evidence / runtime_evidence
known_limits / rollback_to / approval
```

Runtime 必须读取并暴露同一 Manifest 的非敏感摘要，禁止代码、包和运行实例各自报告不同版本。

## 10. SLO 与产品质量

正式阈值必须在基线测试后确定，不在没有数据时编造数字。至少覆盖：

- API 可用性与 P50/P95/P99；
- 页面核心任务完成时间；
- Collector 成功/无新增/阻断/恢复率；
- 数据 freshness 与 Evidence 完整率；
- Metric/Report 可回溯率；
- Auth 恢复时间；
- Worker stale、Retry、DLQ 和恢复；
- AI fallback 成功率与规则兜底率；
- Permission 拒绝准确性；
- Canary 错误预算与 rollback 时间。

Observability 使用稳定结构化字段关联 logs、metrics、traces 和 Evidence；“进程在线”不等于“用户任务可靠完成”。

## 11. 持续闭环

```text
Operate
→ Observe SLI + Business Outcome
→ Detect Gap / Badcase
→ Evidence
→ Root Cause
→ Decision Record
→ Research / Heritage Retrieval
→ Patch Preview
→ Test / Shadow
→ Human Approval
→ Canary / Release
→ Outcome Evaluation
→ Learning Asset
```

每个闭环必须留下：Issue/Task、Evidence、Decision、Diff、Tests、Release、Outcome、Regression 和 Owner。

## 12. 阶段状态与禁止越级

| 阶段 | 可以做 | 不可以做 |
|---|---|---|
| 当前 | 只读审计、设计、隔离测试、报告 | 宣布上线、清理 DB、切换生产 |
| P0 Foundation | 兼容实现、旁路、双读、迁移副本 | 删除旧实现、公开发布 |
| P0 Canary | 小范围真实流量、回滚演练 | 全量切换、破坏旧回退点 |
| P1 Product | 完整 CTH/BMP/Shared 能力 | 破坏 P0 Truth/Runtime |
| P2 Ecosystem | 多终端、扩展和生态 | 建立新的 Production Truth Owner |

## 13. 第 13 项最终验收

第 13 项是十二大类完成后的唯一最终验收关口，不是新的产品线或功能阶段。

### 13.1 必须提交的 Evidence Pack

1. Source：最终 Commit、tree digest、完整 Diff、依赖锁、SBOM。
2. Call Graph：Capability → Module → Function/Class → API → DB → UI → Runtime。
3. Data/API：Schema、Migration、Contract、真实样本 Truth Trace。
4. Frontend：CTH/BMP/Shared/SYSTEM 真实浏览器证据。
5. Runtime：Manifest、Process、Worker、Queue、Auth、Provider、DB attestation。
6. Tests：unit/integration/migration/security/E2E/performance/failure/rollback。
7. Production Evidence：Canary、SLO、错误预算、人工批准、回滚演练。

### 13.2 十二类逐项复核

| 类别 | 验收要求 |
|---|---|
| 1 事实基线 | Remote/Local HEAD、Diff、文件/语言/目录与 Runtime 一致 |
| 2 源码审计 | 所有候选实现有状态和依赖证据，无未经授权删除 |
| 3 产品架构 | 只有 CTH/BMP，两者和 Shared/SYSTEM 边界落入源码与路由 |
| 4 Capability | 每个能力一个 Canonical Implementation |
| 5 数据真相链 | UI/Report 可完整回溯 Evidence，无 AI 覆盖 |
| 6 前端重构 | 新设计真实实现，不复制旧 UI，无假状态 |
| 7 动态化 | 动态全部服务决策并绑定真实变化 |
| 8 AI/Agent | Permission/Trace/Evaluation/Audit/Human Approval 强制生效 |
| 9 工程质量 | API、Migration、Security、Dependency、Performance、Tests 通过 |
| 10 Release | 兼容、Shadow、Canary、Manifest、Provenance、Rollback 完整 |
| 11 真实验证 | Clean Runtime、真实页面、真实 DB、跨仓 Contract E2E 通过 |
| 12 路线闭环 | 运营、监控、学习、改进和退役机制可执行 |

### 13.3 一票否决

出现以下任一情况，最终验收直接 NO-GO：

- Runtime 不能证明 Commit/DB/Product Mode；
- 测试触碰生产数据库；
- UI 把错误、未知、会话失效或未运行显示为健康；
- BMP/CTH 路由或数据越界；
- Subject 保护弱化；
- AI/Agent 可绕过审批写 Production Truth；
- 未认证端点泄漏凭据、路径或敏感运行信息；
- Migration 不可回滚或有未解释 FK 违规；
- 核心测试 fail/skip；
- 无真实浏览器、真实 Runtime、Canary 和 rollback evidence；
- 使用假数据或旧文档冒充完成。

### 13.4 允许的最终声明

只有第 13 项全部通过后，才能依次声明：

```text
IMPLEMENTED
→ TESTED
→ VERIFIED
→ RELEASED
→ OPERATING
```

当前只能声明：十二大类审计与重建方案已形成；产品重构实现、发布和上线尚未执行。

## 14. 研究校准

本路线只把外部标准用于设计校准，不把其存在当作本项目合规证明：

- NIST SSDF SP 800-218：安全开发贯穿组织准备、软件保护、安全生产和漏洞响应；
- SLSA Build Track：发布物需要构建来源证明和可验证 provenance；
- OWASP ASVS 5.0：Web 应用安全控制需要逐项可验证；
- OpenTelemetry：日志、指标、追踪应使用稳定语义并可关联。

最终合规状态必须由 LUMENIS 自己的实现、测试和 Runtime Evidence 证明。

## 15. 本类最终判定

P0：尚未实施，当前存在一票否决项。

P1：设计完成，受 P0 阻断。

P2：生态方向明确，禁止提前替代生产底座。

第 13 项：`NOT READY`。

当前发布：`NO-GO`。
