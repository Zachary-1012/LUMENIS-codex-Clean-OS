# `D:\Taikoo-monitor-new` 源码、数据与运行资产审计 V1

状态：第 12 类增量事实审计

审计方式：Git、进程、HTTP/API、源码、只读 SQLite；未使用历史印象，未读取或输出 `.env` 值，未登录、未绕过认证、未运行可能写生产库的测试。

总判定：`ACTIVE RUNTIME + VALUABLE DATA ASSET / NOT CLEAN / NOT CURRENT REMOTE / NOT RELEASEABLE`

## 1. Git 事实

| 项目 | 事实 |
|---|---|
| 路径 | `D:\Taikoo-monitor-new` |
| 分支 | `main` |
| Local HEAD | `fda599abf5e35aecebe3ff37b0e66060e68c3017` |
| Fetch 后 origin/main | `0d25b913a62c90ea38c183267d89fba8222dbb53` |
| 分叉 | 本地 0、远端 2；本地落后 2 Commit |
| 远端 | `Zachary-1012/Z-Brand-Core.git` |
| tracked status | clean |
| ignored entries | 644 个状态条目 |

远端新增 2 个 Commit、7 个文档文件；本地产品源码与远端该差异中没有代码变更。但本地落后仍意味着不能用本地 HEAD 代表“当前远程 main”。

## 2. 文件与语言

Git 跟踪文件 3660 个：

- Python 1013；
- Markdown 1021；
- JSON 411；
- HTML 58；
- JavaScript 32；
- CSS 10；
- tests 路径文件 406。

工作区还包含 `.env`、`.venv`、多个 Edge CDP Profile、缓存数据库、staging 数据库、日志、自修复备份、node_modules 等运行资产。它们多数被忽略，Git clean 不能证明工作目录纯净。

## 3. 与纯净仓的关系

关键源码 SHA-256：

| 文件 | SHA-256 |
|---|---|
| `app.py` | `064544279d4304d58a7d4e4730b2bdece1e9aee0142e571b8bcb4a3e9cfdc30f` |
| `subject_rules.py` | `1c6e499c752ceb8a7ebb16663fd3a3e128b4dc5fc5304dd8ced8b694ee78329a` |
| `database.py` | `a21d517d08daae491f703c21fe6c1758c5fc774582947f0ee0fbc4fd594bf970` |
| `database_migrations.py` | `b637db5876126281debeb44e439ad3b1f0636cb3de047034118b64afb71c42c9` |
| `static/js/lumenis-core.js` | `62f815cbffdbe5ad9d1052afcc640f905425669fa5f5abbbfde5373c4ccfd41b` |

纯净仓能够解析该 Commit；当前 tree 差异主要是后续治理、审计与 Heritage 文档。说明 Taikoo 路径是纯净仓核心代码的重要运行/数据来源，但不应整目录复制：`.env`、浏览器 Profile、缓存、数据库、日志与测试产物必须保持隔离治理。

## 4. 真实进程

8201 当前运行链：

```text
run_supervised.py --host 0.0.0.0 --port 8201
→ app.py --host 0.0.0.0 --port 8201
→ Edge --remote-debugging-port=9222
   --user-data-dir=D:\Taikoo-monitor-new\edge-cdp-profile
```

应用主进程创建于 2026-09-08 20:59:41，监听 `0.0.0.0:8201`。这证明它是当前活跃 Runtime，不证明它是已发布版本。

## 5. 认证与公开边界

未经认证：

- `/`、CTH/BMP 页面、`/api/status` 等返回 401；
- 响应使用 `Basic realm=TaikooMonitor`；
- 浏览器访问收到 `ERR_INVALID_AUTH_CREDENTIALS`，本轮没有尝试绕过或读取凭据。

但 `app.py` 的 Basic Auth 例外列表显式放行：

- `/api/system/runtime`；
- `/api/system/health`；
- `/api/system/health/summary`；
- `/api/auth/config`；
- 若干 CTH readonly GET 与其他状态端点。

实测 `/api/system/runtime` 未认证返回本机根路径、OSAI 路径、数据库表/行数和 Worker 明细；`/api/system/health/summary` 未认证返回 Cookie 文件存在性、CDP 状态、notes 数、采集次数、最近新增与下次调度时间。

结论：认证保护不是完整边界。公开健康端点泄漏内部运行和数据状态，`/api/auth/config` 还需要按既有第 9 类安全结论立即收紧。

## 6. 数据库事实

主库：`D:\Taikoo-monitor-new\data\monitor.db`，23,212,032 bytes。

只读检查：

| 项目 | 结果 |
|---|---|
| 业务表 | 128（Runtime API 统计 129，统计口径需统一） |
| integrity_check | ok |
| foreign_key_check | 35 条违规 |
| notes | 1044 |
| events | 510 |
| daily_reports | 40 |
| collection_logs | 543 |
| canonical_data / zbc_canonical_data | 14 / 4 |
| app_evidence_records / zbc_evidence | 19 / 6 |
| metric_snapshots | 1166 |
| runtime_guardian_workers | 2798 |
| ai_task / ai_call_logs | 2833 / 2499 |
| v4_users | 9 |

外键违规样本集中在 `content_generation_evidence` 自引用关系；此前审计的 43 条与本轮 35 条不同，证明数据库仍在变化。未经副本迁移和逐行根因审计，不得清理或覆盖。

除主库外还存在：

- 两个 13.3MB / 22.2MB cache monitor DB；
- 6.6MB old staging reference；
- 21.9MB staging DB；
- 多个 test DB；
- Browser Profile 内部 SQLite。

这些数据库不是自动备份/生产/测试分类的可靠证据，必须进入 Data Asset Registry。

## 7. 数据新鲜度与运行真相冲突

主库最大时间：

- notes `publish_datetime=2026-09-08`；
- notes `captured_at=2026-09-08 12:10:27`；
- daily report date `2026-09-08`；
- worker last heartbeat `2026-09-07 21:13:16`；
- AI call max created_at `2026-09-09 09:00:14`。

2026-09-09 的 `collection_logs` 只读聚合为：

```text
NETWORK_ERROR：3 runs
sum(notes_count)：null
last_finish：00:01:29
```

但未认证 `/api/system/health/summary` 同时报告：

- overall `ok`；
- collector `ok`；
- today_runs 4；
- today_collected 24；
- recent_24h_new_notes 24；
- diagnostic_hints 空。

Runtime API 另一方面报告 Guardian `degraded`、reaper 不运行、所有 domain `running=0`，并返回大量 test worker 名称和历史 created/dead/archived 状态。

结论：Health、Collection Log、Worker 和数据新鲜度没有统一 State Contract。健康摘要的“今日正常”不能作为生产采集成功证据。

## 8. AI 状态真实性

`/api/system/health` 报告 Zhipu、`glm-4.5-air`、`running=true`。源码 `intelligence.ai_status()` 的逻辑是：只要 `_provider_config()` 返回配置，即直接设置 `running=True`，并显示“云端 Key 已配置”；它没有在该函数中执行真实模型探活。

同一机器本轮 OpenCode 对智谱的两个真实调用均返回 `Authentication Failed`。两者调用路径可能不同，但足以证明“Key 已配置”不能推导 Provider 正在运行。

结论：8201 AI 状态为 `CONFIGURED / REAL CALL NOT VERIFIED`，不能标记 ACTIVE。

## 9. 测试边界

本轮没有在 Taikoo 路径运行 pytest，原因不是跳过验证，而是已有测试会写默认数据库，当前路径正在连接真实业务库。直接执行将违反数据库保护红线。

测试前置修复：

1. 强制 `TEST_DB_PATH`/临时目录；
2. 阻断测试连接 production path；
3. 测试前后验证主库 hash/mtime；
4. 将 runtime worker/task fixtures 与生产表物理分离；
5. 固定 UTF-8。

## 10. 资产处置

| 资产 | 决策 | 原因 |
|---|---|---|
| Git 源码 | KEEP AS SOURCE/DIFF EVIDENCE | 与纯净仓共享核心，仍需 Commit 级归并 |
| 主数据库 | PROTECT / MIGRATE COPY ONLY | 有真实业务数据和 FK 风险 |
| cache/staging DB | INVENTORY / VERIFY | 数据语义未确认 |
| `.env` | LOCAL SECRET ONLY | 不进入 Git、报告或发布包 |
| Edge Profile | PROTECT / LOCAL RUNTIME | 包含 Session/Cookie，禁止复制到发布包 |
| logs/self-repair/backups | EVIDENCE CANDIDATE | 需保留来源和敏感性分类 |
| 8201 Runtime | OBSERVE / CANARY SOURCE | 不能直接提升为 Clean Release |

禁止整目录复制到纯净仓，禁止直接删除，禁止让它与纯净 Runtime 同时以未标识方式承担 Production Truth。

## 11. 七类证据

| 证据 | 状态 | 说明 |
|---|---|---|
| Source | PASS | Git、关键源码、Hash 已核验 |
| Call Graph | PARTIAL | Supervisor→App→DB/CDP 明确；完整业务调用未重跑 |
| Data/API | FAIL | 35 FK 违规，Health/Log/Worker 冲突，公开信息泄漏 |
| Frontend | BLOCKED | 页面受认证保护；未绕过认证，无法完成真实业务页验收 |
| Runtime | PASS / DEGRADED | 8201/9222 活跃，但 Guardian degraded、无运行 worker |
| Tests | BLOCKED BY ISOLATION | 为保护生产 DB 未执行 |
| Production Evidence | PARTIAL | 有真实数据和进程，不具备 Release/Canary/回滚证明 |

## 12. 最终结论

`D:\Taikoo-monitor-new` 必须纳入重建基线，它包含当前最重要的真实业务数据和活跃运行资产；同时它不能直接作为纯净版上线源。

正确路径：

```text
Taikoo Source/Data/Runtime Snapshot
→ Immutable Manifest
→ Data Asset Classification
→ Production DB Copy
→ Migration + FK Repair on Copy
→ Clean Core Build
→ Contract/E2E/Canary
→ Human Approval
→ Controlled Cutover
```

当前状态：`PROTECTED PRODUCTION CANDIDATE / RELEASE NO-GO`。

