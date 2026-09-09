# LUMENIS 真实运行、真实页面与跨仓 Contract 验证审计 V1

状态：十二大类第 11 类交付物

审计时间：2026-09-09（Asia/Shanghai）

审计对象：LUMENIS 清洁仓库、当前 8202 运行实例、真实 CTH/BMP/Shared/SYSTEM 页面、运行数据库、OSAI、GGI、LUMENIS Command、专项测试、OpenCode/智谱与本地 Ollama 调用结果

审计原则：只采用当前源码、Git、真实进程、只读数据库查询、真实 HTTP/API、真实浏览器页面和测试结果；不以文件存在、旧文档、配置、测试通过或页面可打开推导生产完成。

总判定：`REAL PAGE REACHABLE / RUNTIME LINEAGE MISMATCH / UI TRUTH CONFLICT / CROSS-REPO CONTRACT PARTIAL / NO-GO`

## 1. 本轮边界与产品线

本轮完成十二大类第 11 类“真实运行、真实页面和跨仓 Contract 验证”。不修改产品源码，不删除或迁移历史资产，不重建或覆盖生产数据库，不重新设计旧页面。

本轮仍只承认以下纯净产品结构：

```text
序境 / LUMENIS
├── CTH：序境·商业运营（Subject-first）
├── BMP：序境·品牌市场（Brand-first）
├── Shared Capability：Evidence / Content Creation / Evaluation / Learning Asset / AI Enhancement
└── SYSTEM：Collector / Runtime / AI Gateway / Database / Security / Settings
```

Shared Capability、SYSTEM、AI、Agent、Agent Groups、OSAI、GGI 与 LUMENIS Command 均不是第四条 LUMENIS 产品线。

## 2. Git 与仓库事实

| 仓库 | 本轮核验点 | 当前事实 |
|---|---|---|
| LUMENIS 清洁仓库 | `main` / `lumenis-clean-os/main` | 均为 `e719112b732ca89e3be8f998a0144bee3d75e459`；报告生成前 Git 工作树无已跟踪变更 |
| OSAI 本地工作区 | 本地 / 远程 | 本地 `09a627a8ff9c168f0c5cbc54fcf1311ec012cce1`；远程 `dedf8a2d48b948132870ea8ecec848e2afa4d2d9`；双方 `13 / 5` 分叉，不能把本地运行结果直接归属远程主线 |
| GGI 镜像 | `main` | `c4bc5323d65c495571deec0ce26b5b4515fed6e5`；镜像未保存 `origin/main` ref，不能证明本地镜像与当前远程仍完全一致 |
| LUMENIS Command | 本地 / 远程 | 均为 `2f65a218eb5131c6abbfabd203dc37ef3cbf8d21` |

结论：四仓都能定位到具体 Commit，但没有一个统一 Cross-Repo Release Manifest 把 Commit、Contract Version、Schema、Artifact Digest、测试和运行实例绑定成一次不可变验收。

## 3. 当前 8202 Runtime 身份

### 3.1 真实进程

监听 `127.0.0.1:8202` 的进程为 PID `17080`，命令行为：

```text
"D:\Z-Brand-Core\.venv\Scripts\python.exe" app.py --host 127.0.0.1 --port 8202 --no-scheduler
```

实际执行器位于本机沙箱 Python；父进程为 `D:\Z-Brand-Core\.venv\Scripts\python.exe`。`--no-scheduler` 明确证明此实例没有运行采集调度器。

### 3.2 页面资产血缘

对 HTTP 实际返回字节计算 SHA-256：

| 资产 | 8202 返回 SHA-256 | 本地匹配 |
|---|---|---|
| `/static/js/lumenis-core.js` | `eb5db824ee7385d8e1aab88169e08e2952ed42539fa567999f3fdd61336c71dc` | 精确匹配 `D:\Z-Brand-Core_MAIN_AUDIT\static\js\lumenis-core.js` |
| `/static/js/lumenis-zero.js` | `e193a61c284b2f501f9d14ceaed968dbd588cc810ebd6fea1ae283e83495c3a5` | 仅在 `Z-Brand-Core_MAIN_AUDIT` 候选中匹配 |
| `/static/css/lumenis-zero.css` | `582785857a0c69545cea6a6f9077048cea7273bef875cafd3d1cf7e47f546d44` | 仅在 `Z-Brand-Core_MAIN_AUDIT` 候选中匹配 |

清洁仓库 `static/js/lumenis-core.js` 的 SHA-256 为 `62f815cb...`，并且不存在两个 `lumenis-zero` 资产。

结论：8202 是真实可访问实例，但不是当前清洁仓库 `e719112...` 的可证明 Runtime。页面可打开不能作为清洁仓已部署、已发布或正在生产运行的证据。

### 3.3 Runtime Attestation 缺失

`/lumenis/healthz` 只返回前端基础层状态，没有返回：

- `release_id`；
- `core_commit`；
- `source_tree_digest`；
- `product_mode`；
- `profile_digest`；
- `db_path/schema_version`；
- `scheduler/worker identity`。

因此无法由 Runtime 自证“我是谁、从哪个 Commit 构建、连接哪份数据库、运行哪种产品模式”。

## 4. 真实 API 与状态事实

| API | 真实结果 | 判定 |
|---|---|---|
| `/api/status` | `last_collection=null`、`total_notes=0`、`ai_enabled=false`、`ai_provider=local_rule`、系统名仍为“广州太古汇舆情监测系统” | 没有正在采集或 AI 正常调用证据；旧产品语义仍泄漏 |
| `/api/system/health` | DB `ok`；AI `enabled=false/running=false`；Ollama installed 但 running=false | 只能证明接口可读与 DB 可打开，不能证明完整系统健康 |
| `/api/metrics/canonical` | `collection_health.state=NO_RUN`；当日无采集记录；所有事实计数为 0；无数据时仍返回 `brand_health_score=50` | 50 分不是当前业务事实，必须标记基线/不可计算，不得显示为真实健康度 |
| `/api/platform-health` | 总体 `SESSION_EXPIRED`；小红书需要人工处理；`stop_request=true`；9 个平台禁用 | 采集链不健康且需要用户处理，不能显示“采集正常” |

`/api/status` 单次响应约 4.7 秒，而其他只读接口多为数十毫秒。该延迟需要在第 12 类路线中进入性能基线与 SLO，不在本轮以一次采样推导稳定性能结论。

## 5. 真实页面核验

本轮使用真实浏览器读取可访问页面结构，并用 HTTP 路由探针交叉验证；没有执行登录、点赞、评论、发布、关注或任何平台写操作。

### 5.1 CTH / 序境·商业运营

`/lumenis/cth/overview` 返回 200，页面显示：

- 今日笔记 0；
- 活跃品牌 194 / 199；
- 风险事件 0；
- 采集状态“运行中 / 采集正常”；
- 系统健康“健康 / 所有模块正常”；
- 趋势、业态、实时流均无数据。

但同一时刻真实 Runtime 为：

```text
--no-scheduler
last_collection = null
collection_health = NO_RUN
platform overall = SESSION_EXPIRED
XHS stop_request = true
AI enabled/running = false
```

因此 CTH 总览存在确定的 UI Truth 冲突。不是“文案可以优化”，而是 View Model 把未运行、会话失效和停机请求映射成了绿色健康状态。

### 5.2 BMP / 序境·品牌市场

- 正式目标路径 `/lumenis/bmp/overview` 返回 404；
- 兼容路径 `/lumenis/zbmp/overview` 返回 200，但实际仍展示 CTH 总览；
- 页面弹窗为“进入序境·品牌市场”，并显示“产品访问保护未配置”；
- 未出现可核验的 BMP Brand-first 页面、BMP 数据或独立 View Model。

结论：BMP 只能标记 `SOURCE ASSETS EXIST / ROUTE BLOCKED / REAL PRODUCT PAGE NOT VERIFIED`，不能标记已运行或已发布。

### 5.3 Shared Capability

实际导航使用：

- `/lumenis/content?domain=cth`：200，标题为 `Content · 序境 LUMENIS`；
- `/lumenis/podcast?domain=cth`：200，但标题仍为 `ZBMP Podcast · 序境 LUMENIS`。

错误猜测路径 `/lumenis/shared/content` 与 `/lumenis/shared/podcast` 均为 404。说明 Shared Capability 已有页面入口，但路由与标题仍绑定历史产品语义，尚未形成 canonical Shared Capability Contract。

### 5.4 SYSTEM

`/lumenis/system/runtime` 返回 200。加载完成后显示：

- 活跃 Worker 0；
- 任务 0；
- Guardian 总体 `UNKNOWN`；
- Lease Manager / Heartbeat Monitor / Reaper / Checkpoint 全部 `UNKNOWN`；
- DLQ 显示为空。

SYSTEM 页面比 CTH 总览更接近真实运行状态，但两者对同一 Runtime 的结论互相冲突。当前缺少统一 Runtime State Contract 作为所有页面的唯一数据源。

## 6. 数据库与测试隔离事实

### 6.1 8202 实际候选数据库

只读连接 `D:\Z-Brand-Core_MAIN_AUDIT\data\monitor.db`：

- 62 张业务表，`schema_version` 表 11 行，`PRAGMA user_version=0`；
- `notes/events/daily_reports/collection_logs` 均为 0；
- `swire_projects=8`、`swire_events=10`、`topic_campaigns=1`；
- `auth_recovery_tasks=7`；
- AI Task、Evidence 和 Worker 表均为 0。

该数据与页面“194/199 活跃品牌”的来源没有在本轮形成同库、同函数、同 Metric 的可追溯证明。

### 6.2 清洁仓数据库被边界测试触碰

清洁仓 `data/monitor.db` 被 `.gitignore` 排除，不受 Git Diff 保护。执行当前仓库 OSAI 边界测试期间，其大小和修改时间发生变化，最终只读检查为：

- 63 张表，文件大小 `1,122,304` bytes；
- `ai_task=57`、`ai_task_step=166`、`ai_task_evidence=97`、`ai_task_trace=191`；
- `runtime_guardian_workers=73`；
- `ai_call_logs=9`、`skill_executions=3`。

测试源码直接调用 `init_task_engine_db()`、创建并执行 Task；没有把数据库强制重定向到临时目录。文件在测试期间由 `1,044,480` bytes 增长到 `1,122,304` bytes，修改时间更新至 09:27:12。

结论：测试隔离失败。即使 Git 工作树显示 clean，也不能证明数据未被改变。未经用户明确授权，本轮没有覆盖、回滚、清空或删除该数据库。

## 7. 跨仓 Contract 源码核验

### 7.1 书面契约一致的部分

LUMENIS、OSAI 与 GGI 文档均要求：

- 各产品独立运行；
- OSAI 贡献异步、可选、非阻塞；
- 不共享生产数据库、凭据、Session 或内部 ORM；
- OSAI 输出只能作为建议；
- 生产规则、数据、风险、发布边界仍由各产品持有；
- 资产必须经过 Evidence、Evaluation、Human Approval 与本产品 Release Gate。

### 7.2 契约 Schema 不一致

OSAI `SHARED-INTELLIGENCE-CONTRIBUTION-CONTRACT-V1` 规定最小 envelope 包含 `source_module`、`source_reference`、`lineage_id`、`evidence`、`context`、`input`、`action`、`result`、`generalizable`、顶层 `created_at` 等字段。

GGI `build_contribution_payload()` 当前只生成其中一部分字段，缺少多项必填字段；LUMENIS 则输出独立的 `zbc.evidence-export.v1` JSONL + manifest 结构。三方没有共享机器可读 Schema、兼容性校验器或 receiver ACK 测试。

结论：V1 文档名称相同不等于协议可互操作。

### 7.3 LUMENIS 侧实现

已确认的有效资产：

- `contracts/lumenis_adapter.py`：只读快照，不写 DB，不暴露主体词表内容；
- `platform_adapters/evidence_exporter.py`：源 DB 使用 SQLite `mode=ro`，白名单投影与脱敏，写入本地 outbox；
- 边界测试覆盖 OSAI 缺失、导出失败隔离、幂等水位和生产导入链。

未收敛问题：

1. `production_core_snapshot()` 中的 `contracts_implemented` 是声明性字典，不是端到端 Contract 证明；
2. `lumenis_skill_adapter.py` 通过 subprocess 直接运行 OSAI `canonical_skill_registry` / `skill_invocation` 内部模块；
3. `lumenis_agg_api.py` 动态 `__import__` OSAI `permission_gate`、`research_pipeline` 等内部模块；
4. `/api/research/start` 明确创建 OSAI 研究记录，已经超出“只读 Contract 调用”；
5. 当前实现与 `CROSS_REPO_CONTRACT_BOUNDARY.md` 中“禁止直接 OSAI 内部模块 import、只经版本化 Contract/Artifact”的规则不一致；
6. 本地 outbox 没有在本轮证明被 OSAI receiver 校验、ACK、拒绝、重试和回放。

这些实现能在 OSAI 不可用时降级，说明“非启动硬依赖”有代码与测试基础；但不能据此声明跨仓 Contract 已 VERIFIED。

### 7.4 OSAI

从 OSAI `origin/main` 的独立源码快照执行 Contract 相关测试：`45 passed`。这证明远程提交中的 Repository、Permission、Runtime、UI State、Learning 与基础 Contract 单测成立。

但 OSAI 本地工作区与远程主线分叉；本轮没有一条真实 receiver 链消费 LUMENIS/GGI payload，也没有 ACK/拒绝/回传资产的端到端证据。

### 7.5 GGI

GGI 存在：

- `contribution_outbox` 表与 Migration；
- payload builder；
- 本地队列；
- bounded retry (`MAX_RETRIES=3`)；
- `OSAI_EXPORT_ENABLED=0` 时跳过；
- JSON 文件导出。

但从 Commit `c4bc532...` 解包后，测试在加载 `ggi.intelligence.service` 时失败：仓库源码引用 `ggi.intelligence.data`，Git 树中不存在该模块。因收集阶段失败，不能用局部实现存在推导 GGI Contract 可运行。

### 7.6 LUMENIS Command

Command 主线 Commit 可定位，但当前恢复的 `evidence/store.py`、`evidence/sqlite_store.py` 等文件被仓库 `.gitignore` 的 `evidence/` 规则排除，`git ls-files` 中不存在。现有源码又依赖这些模块；会话 API 还因 store 方法不接受 `limit` 参数返回 500。

因此 Command 不能作为当前跨仓 Evidence、Release 或 Verification 的可靠远程事实来源，只能标记 `LOCAL RESTORED / REMOTE INCOMPLETE / CONTRACT NOT VERIFIED`。

## 8. 测试与 AI 协作事实

### 8.1 LUMENIS 边界测试

使用 `D:\Z-Brand-Core\.venv` 的解释器，在清洁仓源码上执行两个 OSAI 边界测试文件：

- 默认 Windows 编码：`31 passed, 1 failed, 1 skipped`；
- 失败原因：父进程以 GBK 解码 UTF-8 子进程输出，触发 `UnicodeDecodeError`，随后测试访问 `stdout=None` 产生 `TypeError`；
- `PYTHONUTF8=1` 复测：原失败项通过，整体显示通过并保留 1 个 skip；
- 同时发现测试写入清洁仓被忽略数据库，故测试环境不具备生产数据隔离。

### 8.2 OSAI 与 GGI

- OSAI `origin/main` Contract 快照：45 项通过；
- GGI：测试收集阶段因缺失 `ggi.intelligence.data` 阻断，未形成通过结果。

### 8.3 Ollama、OpenCode 与智谱

- 本地 Ollama 模型 `qwen2.5-coder:7b-agent` 已被真实调用，对本轮核心矛盾给出“事实矛盾、Production Truth 风险、不可判定当前纯净仓 Runtime 已验证”的结论；调用完成后已停止本轮启动的 Ollama 进程，最终进程数与监听数均为 0；未下载模型、未修改自启动和配置。
- OpenCode `1.18.29` 已两次调用智谱（`zai-coding-plan/glm-4.7` 与 `zai/glm-4.5-air`），均返回 `Authentication Failed`。本轮不能编造智谱复核结果；这也证明“配置/凭证存在”不等于 Provider 可用。

AI 结论只作为辅助复核，不替代本报告的源码、Runtime、数据库、测试与页面证据。

## 9. 七类证据验收

| 证据类别 | 状态 | 事实 |
|---|---|---|
| Source | PASS | 已读取 Runtime、页面、Adapter、Exporter、OSAI/GGI/Command 相关源码与契约 |
| Call Graph | PARTIAL | 已追踪页面→API、ZBC→OSAI 动态 import/subprocess、Exporter→outbox；receiver/ACK/回传链缺失 |
| Data / API | FAIL | 页面健康状态与 API 冲突；8202 DB 与清洁仓 DB 分离；测试污染非临时 DB |
| Frontend / Consumer | FAIL | CTH 显示假健康；BMP 正式路径 404；Shared 标题和路由仍混有历史语义 |
| Runtime | FAIL | 8202 非清洁仓可证明实例、禁用 scheduler、0 worker、Guardian UNKNOWN、无 Runtime Attestation |
| Tests | PARTIAL | LUMENIS 有默认编码失败和 skip；OSAI 45 通过；GGI 无法收集；Command 存在远程缺件与 API 失败 |
| Production Evidence | FAIL | 无纯净仓真实部署、BMP 页面、跨仓 E2E、统一 Contract Schema/ACK、不可变 Release Manifest |

本类状态：`PARTIAL / VERIFICATION GATE FAIL`。

## 10. 功能状态判定

| 能力 | 状态 | 禁止声明 |
|---|---|---|
| CTH 页面壳与导航 | `RUNNING PAGE / DATA PARTIAL` | 不得声明采集正常、系统全健康 |
| CTH Production Truth View Model | `CONFLICT` | 不得用绿色状态覆盖 NO_RUN / SESSION_EXPIRED |
| BMP | `SOURCE/PROMPT EXISTS / BLOCKED` | 不得声明真实 BMP 产品已运行 |
| Shared Content | `PAGE REACHABLE / CONTRACT PARTIAL` | 不得声明路由、命名和归属已收敛 |
| SYSTEM Runtime | `PAGE REACHABLE / RUNTIME UNKNOWN` | 不得声明 Guardian 或 Worker 正常运行 |
| LUMENIS→OSAI Export | `IMPLEMENTED + TESTED LOCALLY / E2E MISSING` | 不得声明 OSAI 已接收、验证或学习 |
| OSAI Contract Core | `REMOTE TESTED` | 不得声明与 LUMENIS/GGI 已互操作 |
| GGI Contract | `IMPLEMENTED PARTIAL / TEST BLOCKED` | 不得声明可发布 |
| Command Sidecar | `LOCAL PARTIAL / REMOTE INCOMPLETE` | 不得作为 Production Runtime 或 Truth Owner |
| Ollama | `REAL CALL VERIFIED FOR THIS AUDIT` | 不得推导 LUMENIS 8202 AI Runtime 已启用 |
| 智谱/OpenCode | `CALL ATTEMPTED / AUTH FAILED` | 不得声明本轮成功调用或完成复核 |

## 11. P0 阻断项

1. 建立 Runtime Attestation：页面/API 必须暴露并校验 `release_id/core_commit/product_mode/profile/schema/db/worker`。
2. 让清洁仓在隔离环境真实启动；不得继续以 `MAIN_AUDIT` 页面冒充纯净仓 Runtime。
3. 建立唯一 Runtime State Contract；CTH、SYSTEM、API 对 scheduler、worker、auth、collector、AI 的状态必须一致。
4. 修复 UI 假健康：`NO_RUN`、`SESSION_EXPIRED`、`UNKNOWN`、`DISABLED` 必须显式呈现并阻止绿色成功状态。
5. 无事实数据时 `brand_health_score` 应为 `NOT_COMPUTABLE/NO_DATA` 或明确规则基线，不得显示为真实 50 分。
6. 建立 canonical BMP 路由与 Brand-first View Model；访问保护未配置必须 fail-close，不能回落显示 CTH 页面。
7. 将 Shared Capability 的路由、标题、Domain Context 从 ZBMP 历史语义中解耦。
8. 所有测试强制使用临时数据库；测试启动前后校验 Production DB 哈希和修改时间不变。
9. 收敛唯一机器可读 Cross-Repo Schema；实现 producer validation、receiver validation、ACK/reject、bounded retry、lineage 和回传采用门禁。
10. 移除对 OSAI 内部模块的动态 import/subprocess 耦合，改为版本化 Contract/Artifact；写 OSAI 的研究接口必须经过独立授权与 Effect Fence。
11. 修复 GGI 远程源码缺件并让 Contract 测试可收集、可执行；补齐与 OSAI envelope 的兼容测试。
12. 将 Command Evidence 实现纳入 Git 受控路径，修复 Session API Contract；序枢继续保持非生产依赖。
13. 固定 UTF-8 测试运行环境；默认编码失败和 skip 必须进入 Release Gate。
14. 修复智谱/OpenCode Provider 认证链并执行真实健康调用；凭证不得进入源码、报告、日志或 Git。

## 12. 最终判定

事实：当前有真实可访问页面、部分真实 API、部分跨仓适配代码和多组通过测试。

产品：纯净产品线仍是 CTH + BMP；Shared Capability 与 SYSTEM 是跨产品层，不增加第四产品线。

缺失：清洁仓 Runtime、BMP Brand-first 真实页面、统一 Runtime State、测试数据库隔离、跨仓机器契约、receiver/ACK/E2E、Command 远程 Evidence 完整性。

重复与冲突：多个源码目录共同参与运行；CTH 与 SYSTEM 对同一运行状态给出不同结论；书面 Contract 与直接 OSAI 模块调用并存；三方 payload Schema 不一致。

风险：UI 覆盖真实故障、测试修改非临时数据库、错误仓库被视为线上版本、跨仓内部实现耦合、未验证 BMP 被误报完成、Provider 配置存在却无法调用。

最终结论：

```text
Runtime：NOT VERIFIED
CTH Production Truth UI：CONFLICT
BMP：NOT VERIFIED
Shared Capability：PARTIAL
SYSTEM：PARTIAL / UNKNOWN
Cross-Repo Contract：PARTIAL / NOT INTEROPERABLE
Release：NO-GO
```

在以上 P0 完成并重新取得 Source、Call Graph、Data/API、Frontend、Runtime、Tests、Production Evidence 七类证据前，不得声明 LUMENIS 清洁版已经上线、BMP 已完成、采集正常、AI 正常或四仓闭环已经形成。
