# LUMENIS 兼容、旁路、灰度与 Release 血缘审计 V1

状态：十二大类第 10 类交付物

审计对象：当前清洁仓库、原始远程仓库、序枢远程仓库、本地运行实例、生产/便携候选目录、发布与调度代码、边界测试

审计原则：只采用源码、Git、真实进程、真实数据库和测试结果；不以文件名、旧文档、版本号或配置存在推导完成状态

结论：`RELEASE ASSETS EXIST / DUAL RELEASE NOT IMPLEMENTED / LINEAGE NOT VERIFIED`

## 1. 本轮边界

本轮只审计和定义以下工程问题，不修改业务源码、不删除历史资产、不重建数据库：

1. 一套 Core 是否已经能够产生 CTH 客户 Release 与 LUMENIS 平台 Release；
2. 兼容层、旁路、Shadow、Canary、Enforce 是否有唯一状态与晋级证据；
3. Release 是否能够追溯到源码、配置、Profile、数据库 Schema、测试和运行实例；
4. 客户 Release 是否真正独立、隔离、可回滚；
5. 序枢是否保持为非生产依赖的 R&D Sidecar。

本报告不把旧命名中的“双产品”理解为两套 Core，也不新增第四产品线。目标始终是：

```text
LUMENIS Core
├── CUSTOMER_RELEASE / CTH / 序境·商业运营
└── ZBRAND_PLATFORM / LUMENIS Platform
    ├── CTH
    ├── BMP
    ├── Shared Capability
    └── SYSTEM
```

## 2. Git 与远程事实

本轮事实核验以 `6b11846…` 为清洁仓库起点；报告提交期间，远端由另一条已授权工作链推进到 `4fd7f23…`，本报告已在读取新增治理规则后以 rebase 方式整合，没有强推或覆盖并发成果。

| 对象 | 当前可验证事实 |
|---|---|
| 本轮清洁仓库输入基线 | `6b11846782bba2d5d8a5a3e0dd17d5623a312883` |
| 并发成果整合基线 | `4fd7f23`；最终报告 Commit 以 Git 提交记录为准 |
| 原始 `Z-Brand-Core` 远程 `main` | `0d25b913a62c90ea38c183267d89fba8222dbb53` |
| `lumenis-command` 远程 `main` | `2f65a218eb5131c6abbfabd203dc37ef3cbf8d21` |
| 三个远程连通性 | `git ls-remote` 均成功 |
| 三个远程 Tag | 均未发现 tag ref |
| 清洁仓库 submodule | `.gitmodules` 为空；没有 gitlink |
| GitHub Release / 可见性 | 当前 `gh` 未认证，不能实时验证 |

结论：三仓提交点可读取，但没有不可变 Tag 或 GitHub Release 证据。旧文档所述 Command Console submodule 与当前仓库实况不一致；当前事实是序枢独立仓库，不是清洁仓库 submodule。

### 2.1 Heritage 前置检索

并发提交新增 Heritage Intelligence Retrieval Gate 后，本轮按 Release/Runtime/Security 域完整读取：

- `heritage_intelligence/README.md`；
- `ASSET_REGISTRY.md`、`ASSET_GOVERNANCE.md`、`SOURCE_MAP.md`；
- Decision Memory、Regression Memory 与 Migration Status。

与本轮直接相关的资产判断：

| Asset | Registry 状态 | 本轮处理 |
|---|---|---|
| HIA-20260909-010 Engineering Audit & Verification Memory | VERIFIED | `ENGINEERING_ENHANCEMENT`：强化 Evidence、Boundary、Deployment 与 Release Gate，但仍以本轮当前源码/测试为准 |
| HIA-20260909-013 Regression Memory Collection | DISCOVERED | `ENGINEERING_ENHANCEMENT`：保留编码、权限、浏览器、Truth Chain、Runtime 和扫描故障模式；未把 DISCOVERED 误报为已完整迁移 |
| HIA-20260909-014 Decision Memory Collection | DISCOVERED | `REFERENCE_ONLY`：当前仅有 Contract-first 决策条目，与 Release 血缘没有可直接晋级的完整实现 |

Heritage 只影响验证方法和防回归要求，没有被当作 Runtime、当前功能或发布完成证据。

## 3. Release 模式实现核验

### 3.1 目标模式没有落地为唯一开关

对可执行源码检索 `CUSTOMER_RELEASE`、`ZBRAND_PLATFORM`，结果均为 0。当前存在 `ZBC_PRODUCT_ID`、`ZBC_ACTIVE_BRAND`、Feature Flag、Subject Context 等局部开关，但没有一个 canonical Release Definition 同时约束：

- 构建产物；
- 路由与页面；
- Capability allowlist；
- Profile；
- 数据库；
- Migration；
- 权限；
- Runtime；
- 测试证据；
- 回滚目标。

因此，当前状态只能认定为“配置与边界资产存在”，不能认定为“双 Release 已实现”。

### 3.2 Subject 隔离不等于 Release 隔离

源码中存在多个 Brand Profile，包括 `guangzhou_taikoo_hui` 与 `hainan_cdf`。`ZBC_PRODUCT_ID=CTH` 时，Subject Context 能拒绝非 CTH 品牌上下文。这是有效的主体保护资产，但只证明主体选择边界，不证明产品页面、API、模块和数据库已经裁剪为客户 Release。

### 3.3 真实路由探针

在临时数据库和 `ZBC_PRODUCT_ID=CTH` 下，分别导入清洁源码与两个便携候选后端并读取真实 Flask route map：

| 候选 | 总规则 | ZBMP 路由 | CTH 路由 |
|---|---:|---:|---:|
| 清洁源码 | 813 | 20 | 35 |
| `Z-Brand-Core_PORTABLE_20260908_140912` | 817 | 20 | 35 |
| `Z-Brand-Core-portable` | 817 | 20 | 35 |

在 CTH 模式下仍注册 `/lumenis/zbmp/overview`、Brand、Content、KOS、Competition、Risk、Report、Evaluation、Launch 及 `/api/zbmp/*` 等路径。

结论：`ZBC_PRODUCT_ID=CTH` 当前不是客户专属路由面；仅隐藏导航或选择主体不能作为产品隔离证据。

## 4. 兼容与旁路审计

### 4.1 已存在的兼容资产

- Subject 规则、Subject Context 和双域测试保留了 CTH/BMP 语义边界；
- 数据库迁移采用版本表、备份和向后兼容方向；
- API 中保留 legacy、v2、v4、domain、viz 等兼容入口；
- AI、OSAI、Agent 和 Scheduling 均存在边界或降级测试；
- 报告、Canonical Data、Provider 等模块存在 Feature Gate 或旁路设计。

### 4.2 当前问题

1. 没有统一 Compatibility Registry，无法回答每个旧 API、表、字段、页面和 Provider 的 owner、消费者、终止条件与移除版本。
2. 旁路分散在环境变量、模块局部默认值、异常降级和启动逻辑中，不能形成统一可审计状态。
3. `app.py` 导入会执行数据库初始化、Migration 和后台模块初始化，不是纯构建/契约检查；隔离探针中出现后台 TopicCampaign 线程启动日志。
4. 清洁空库导入时 v9→v10 Migration 因缺少 `canonical_data` 回滚，说明兼容迁移与全新安装不是同一条已验证路径。
5. 清洁源码导入还出现 `evidence_api` 蓝图重复注册；应用继续运行，路由结果可能受注册顺序影响。

兼容状态：`PARTIAL`。当前能保护部分旧路径，但没有形成“Inventory → Dependency Trace → Runtime Verification → 生命周期决策”的机器可读闭环。

## 5. Shadow / Canary / Enforce 审计

### 5.1 调度门控已实现的部分

`platform_adapters/scheduling/gate.py` 已实现：

- `shadow`：只记录决策，不改变硬规则结果；
- `canary`：仅对 `ZBC_SCHED_GATE_PLATFORMS` 中的平台执行规划器裁决；
- `enforce`：执行规划器裁决；
- 无效模式回退 `shadow`；
- 规划器异常时回退确定性 `hard_allow`。

这证明调度 Gate 的代码级状态机与降级路径存在，并有专项测试覆盖。

### 5.2 默认值冲突

`.env.example` 与 `config.py` 默认 `ZBC_SCHED_GATE_MODE=shadow`，但 `app.py` 的 `scheduler_loop()` 使用：

```text
setdefault('ZBC_SCHED_GATE_MODE', 'enforce')
```

当环境未显式配置时，配置层表达 Shadow，而真实 scheduler 进程会把模式设为 Enforce。一个能力存在两个默认真相，违反单一配置所有权。

### 5.3 当前运行不能证明灰度

8202 实例的真实命令行为：

```text
D:\Z-Brand-Core\.venv\Scripts\python.exe app.py --host 127.0.0.1 --port 8202 --no-scheduler
```

进程工作目录为 `D:\Z-Brand-Core_MAIN_AUDIT`，健康接口返回 `taikoo-monitor / 5.9.9`。由于使用 `--no-scheduler`，该实例不能证明 Shadow、Canary 或 Enforce 正在运行，也不能证明清洁仓库代码正在提供页面。

灰度状态：调度门控为 `IMPLEMENTED + TESTED`，但不是 `VERIFIED / RELEASED / OPERATING`。

## 6. 发布资产与可重复构建

### 6.1 已存在

- `VERSION=5.9.9`；
- Dockerfile、production compose、staging overlay；
- production/staging 数据库挂载与健康检查；
- 便携包启动脚本；
- 发布、恢复、校验和旧变更清单类脚本。

### 6.2 未形成可验证 Release

1. 根目录未发现包含 Release 血缘的机器可读 JSON/YAML/TOML Manifest。
2. production compose 使用可变标签 `zbrand-core:latest`，没有 immutable image digest。
3. 容器和健康接口没有暴露 `release_id`、`core_sha`、`profile_digest`、`schema_version`、`product_mode`。
4. `scripts/start_production.ps1` 固定使用 `D:\Taikoo-monitor-new`，不能证明从当前清洁仓库启动。
5. 当前机器未安装 Docker CLI，因此本轮不能验证 compose 解析、镜像构建和容器启动。
6. 三个远程均无 Tag，且当前不能验证 GitHub Release。
7. 没有 SBOM、签名、构建环境摘要、Artifact Digest 与回滚 Manifest 的统一产物。

结论：存在“可以继续建设发布流程的资产”，不存在“本轮已证明可重复发布”的证据。

## 7. 候选目录与包血缘

| 候选 | Git / 版本 | 关键事实 |
|---|---|---|
| 清洁仓库 | Git `6b11846…` / 5.9.9 | 7,688 文件；3 个 DB；无 `.env` |
| `Z-Brand-Core` | Git `6f0c9f4…` | 37,952 文件；72 个 DB；存在 `.env`；根 `app.py` 不在同一位置 |
| `Z-Brand-Core_MAIN_AUDIT` | Git `b6b52b…` / 5.9.9 | 当前 8202 来源；10 个 DB；无 `.env` |
| `Z-Brand-Core_PORTABLE_20260908_140912` | 无 Git / 5.9.9 | 3,803 文件；无 DB、`.env`、`.venv` |
| `Z-Brand-Core-portable` | 无 Git / 5.9.9 | 2,072 文件；包含 1 个 DB；无 `.env`、`.venv` |
| `Taikoo-monitor-new` | Git `fda599a…` / 5.9.9 | 45,031 文件；48 个 DB；存在 `.env` |

实测所有候选的 `app.py` 哈希并不相同。两个无 Git 便携包的关键 Blob 不能映射到清洁仓库对象；`Taikoo-monitor-new` 的关键 Blob 可在清洁仓库历史提交中找到，但当前目录仍不是一个由 Manifest 证明的 Release。

因此：

- 相同 `VERSION` 不等于相同源码；
- 文件夹名称中的 `PORTABLE`、`MAIN_AUDIT`、`new` 不代表发布状态；
- 没有 Commit、Digest、Profile、Schema 和 Test Evidence 的包不得命名为已验证 Release。

## 8. 客户包数据库事实

对 `D:\Z-Brand-Core-portable\backend\data\monitor.db` 只读核验：

- `integrity_check=ok`；
- 外键违规为 0；
- 32 张表；
- 不存在 `notes` 表；
- `auth_recovery_tasks=1`、`schedule_decisions=8`、`schema_version=5`、`v4_security_questions=2`、`v4_users=1`；
- 其余本轮列举业务表为 0；未读取或披露任何行内容。

结论：该包不是可证明的空白、无身份状态客户种子库，也不具备当前 Schema 完整性证据。未经专门迁移与脱敏验收，不能作为客户 Release 数据库。

## 9. 独立运行与跨仓边界

### 已验证

- 清洁仓库没有序枢 submodule 或 gitlink；
- OSAI/Agent/Safety 边界测试的业务逻辑在 UTF-8 环境下通过；
- 序枢远程仓库可独立读取；
- 当前 Core 不需要通过 submodule 获取序枢源码。

### 未验证

- 没有 Sidecar Contract 的版本、Schema、兼容矩阵和 Artifact Digest；
- 没有“序枢停止/删除后 Core 全生产链仍通过”的真实长时间运行证据；
- 旧文档、旧仓库名与当前 `lumenis-command` 关系未完成 Canonical Registry 收敛。

结论：源码结构支持“序枢非运行依赖”的目标，但生产独立性只能标记 `PARTIAL`。

## 10. 测试事实

### 10.1 Release/产品边界测试

执行 Scheduling Gate、Request Domain Context、Subject Context、KOS Subject Ownership、Dual Domain E2E：

```text
71 passed
```

### 10.2 跨仓与安全边界测试

默认 Windows 编码环境：

```text
120 passed, 1 failed, 1 skipped
```

失败项 `test_20_osai_modules_not_in_app_import_chain` 的父测试进程以 `text=True` 按 GBK 解码 UTF-8 子进程输出，触发 `UnicodeDecodeError`，随后 `stdout=None` 导致 `TypeError`。仅对该项设置 `PYTHONUTF8=1` 后：

```text
1 passed
```

这证明被检查的 OSAI 导入边界在 UTF-8 下通过，同时也证明 Release Gate 对宿主编码敏感。原始失败与 1 个 skipped 必须保留，不能只报告修复环境后的通过数。

### 10.3 AI 协作核验

- OpenCode + 智谱 GLM 4.7 已在只读 Plan 模式执行仓库扫描，独立确认目标双 Release 常量未出现在可执行源码，并识别现有 Shadow/Canary/Enforce 与容器资产；
- 本地 Ollama `qwen2.5-coder:7b-agent` 已使用真实源码片段调用，但超过两分钟未产生可用输出后终止；其结果不作为本报告证据。

## 11. 七类证据验收

| 证据 | 状态 | 说明 |
|---|---|---|
| Source | PASS | 发布、Profile、Gate、容器与边界代码已读取 |
| Call Graph | PARTIAL | 已追踪 scheduler、Subject 与路由注册；全量兼容消费者尚未入 Registry |
| Data / API | FAIL | 客户包 Schema 不完整，CTH 模式仍暴露 BMP API |
| Frontend / Consumer | FAIL | CTH Release 路由面未隔离，不能证明客户 UI 只消费允许能力 |
| Runtime | FAIL | 8202 非清洁仓库且禁用 scheduler；Docker 未验证 |
| Tests | PARTIAL | 71 项通过；边界套件原始有 1 fail、1 skip，UTF-8 复测失败项通过 |
| Production Evidence | FAIL | 无不可变 Release、Tag、Manifest、部署证明与回滚演练 |

本类综合状态：`PARTIAL / RELEASE GATE FAIL`。

## 12. Canonical Release 架构

### 12.1 唯一 Release Definition

每个发布产物必须生成不可变 Manifest，至少包含：

| 字段 | 含义 |
|---|---|
| `release_id` | 全局唯一发布标识 |
| `product_mode` | `CUSTOMER_RELEASE` 或 `ZBRAND_PLATFORM` |
| `core_commit` | 唯一 Core Git Commit |
| `source_tree_digest` | 源码树摘要 |
| `profile_id/version/digest` | 客户或平台 Profile 血缘 |
| `capability_set_digest` | 启用能力和 Route allowlist 摘要 |
| `db_schema_version` | 数据库目标版本 |
| `migration_range` | 允许升级路径 |
| `api_contract_version` | API Contract 版本 |
| `ui_contract_version` | Page/View Model 契约版本 |
| `sidecar_contract_version` | 可选序枢协议版本，不构成运行依赖 |
| `artifact_digest` | 包或镜像不可变摘要 |
| `test/security/runtime_evidence` | 验收证据引用 |
| `known_limits` | 已知限制 |
| `rollback_to` | 已验证回滚目标 |

### 12.2 一套 Core、两种产物

```text
Core Commit
  → Release Definition
  → Product Mode
  → Profile Overlay
  → Capability / Route Allowlist
  → Build
  → SBOM + Digests
  → Isolated Database
  → Test + Security + Runtime Evidence
  → Human Approval
  → Immutable Tag / Artifact
  → Deploy
  → Runtime Attestation
```

`CUSTOMER_RELEASE` 必须只注册获准的 CTH 页面、API、任务和表访问者；BMP、研发、样本、实验和平台管理能力不能仅靠前端隐藏。`ZBRAND_PLATFORM` 才包含 CTH、BMP、Shared Capability 与 SYSTEM 的完整受控集合。

### 12.3 Capability 生命周期

所有高风险新能力统一使用：

```text
OFF → SHADOW → CANARY → ENFORCE
                    ↘ ROLLBACK
```

要求：

1. 默认值只在 Capability Registry 声明一次；
2. App、Worker、CLI、Container 读取同一解析结果；
3. Shadow 记录新旧差异，不改变 Production Truth；
4. Canary 按 Subject、平台、Tenant 或流量比例明确选择；
5. 晋级必须绑定指标、Evidence 和人工批准；
6. 失败自动回到确定性规则或上一已验证版本；
7. 小红书等高风险采集平台最后进入 Enforce。

## 13. 回滚模型

回滚不是只把代码切回旧 Commit，必须同时覆盖：

```text
Code + Config + Profile + Capability Set
+ API/UI Contract + Schema Compatibility + Runtime State
```

数据库禁止用破坏性“倒退重建”实现回滚。正确策略是：

- 向后兼容扩展；
- Expand → Migrate → Verify → Contract；
- 保留可读旧字段的兼容窗口；
- 数据写入使用幂等键与 Effect Fence；
- 回滚前验证旧版本能读取新 Schema；
- 每个 Release 进行独立数据副本演练并记录证据。

## 14. 整改优先级

### P0：发布前阻断项

1. 建立唯一 `product_mode` 和机器可读 Release Manifest；
2. 解决 Scheduling Gate 的 Shadow/Enforce 默认值冲突；
3. 为客户 Release 建立 Capability、Route、Worker 和数据访问 allowlist；
4. 修复空库 Migration 顺序与导入即启动后台线程的问题；
5. 移除启动脚本对 `D:\Taikoo-monitor-new` 的硬编码，改为明确且可证明的 Release 根目录；
6. 禁止把现有便携数据库直接作为客户种子库，先完成 Schema、身份状态和数据资产验收；
7. 固定 UTF-8 测试环境并让 fail/skip 阻断 Release；
8. 生成 immutable Tag、Artifact Digest、SBOM、测试证据和回滚目标；
9. 让 `/healthz` 或受控 Runtime Manifest 暴露可核验的 `release_id/core_sha/product_mode/schema_version`；
10. 在隔离环境验证客户包无序枢、无云 AI、无平台后台依赖仍能启动和完成核心链。

### P1：自动化与跨仓契约

1. 从同一 Core 自动构建两种 Release；
2. 建立 Compatibility Registry 与 Legacy 退役门禁；
3. 建立 Sidecar Contract 版本、Schema 与兼容矩阵；
4. 加入镜像/包签名、SBOM、依赖锁与 Provenance；
5. 自动执行 Schema 升级、回滚兼容和客户 Profile 隔离测试；
6. 建立 Shadow 差异、Canary 健康与回退仪表。

### P2：渐进发布与运营闭环

1. 按 Subject、平台和能力建立渐进式发布；
2. 将 SLO、错误预算、数据质量与业务结果作为晋级门禁；
3. 建立多版本迁移兼容窗口和定期回滚演练；
4. 将 Release → Outcome → Evaluation → Learning Asset 纳入持续改进。

## 15. 最终判定

事实：仓库存在兼容代码、Subject 边界、调度 Gate、容器文件、便携包和测试资产。

产品：仍是一套正在收敛的 Core；CTH/BMP 产品边界尚未落地为两个可验证 Release 产物。

缺失：唯一 Product Mode、Route/Capability allowlist、不可变 Manifest、Tag、Artifact Digest、完整 Schema、真实部署与回滚证据。

重复：多个同版本但源码哈希不同的候选目录和包；多个配置默认真相。

风险：客户包暴露 BMP 路由、调度默认进入 Enforce、启动路径指向旧目录、便携数据库含状态数据、测试受系统编码影响。

发布结论：`NO-GO`。在 P0 完成并通过七类证据验收前，不得把任何现有目录、Docker 配置或便携包声明为 LUMENIS 正式 Release。
