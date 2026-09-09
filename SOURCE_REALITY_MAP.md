# LUMENIS 源码与运行事实地图

状态：十二大类审计后的 Canonical 事实入口

更新时间：2026-09-09

## 1. 使用规则

本文只记录已由当前 Git、源码、数据库、Runtime、测试和真实页面证明的事实。详细证据仍以各专项审计报告和机器清单为准。

事实优先级：

```text
当前运行证据
→ 当前数据库与 API
→ 当前源码和调用链
→ 当前测试
→ 当前架构决策
→ Heritage / 历史文档
```

文件存在、旧文档结论、测试通过、页面返回 200、配置存在均不等于生产完成。

## 2. Repository 基线

| 对象 | 当前事实 |
|---|---|
| 清洁仓库 | `D:\LUMENIS_REBUILD\Z-Brand-Core` |
| 目标远程 | `Zachary-1012/LUMENIS-codex-Clean-OS`，Private |
| 本文件生成前基线 | `366931661b49f1fdf9de31af5af150afa3a0c620` |
| 原始工程远程 | `Zachary-1012/Z-Brand-Core`；作为工程与历史来源，不等于当前 Runtime |
| OSAI | 本地与远程分叉，不能混用本地/远程状态 |
| GGI | 独立产品，只允许版本化 Artifact/Contract |
| LUMENIS Command | R&D Sidecar，不是生产依赖、产品线或 Production Truth Owner |

最终报告提交后 Commit 以 Git 记录为准，不用本文预写哈希冒充最终提交。

## 3. 源码规模与机器清单

当前仓库已存在以下机器/半机器事实源：

| 事实源 | 内容 | 使用限制 |
|---|---|---|
| `audit/module_inventory.json` | 旧扫描快照：504 Python 模块、4106 函数、375 类、589 路由 | 来自历史 Commit/路径，只能做候选清单，状态需当前复核 |
| `audit/module_inventory.md` | 模块级分类、引用与测试候选 | 其中 VERIFIED/DELETE-CANDIDATE 不能直接继承 |
| `function_map.json` | 旧函数分组 | 粒度有限，不是当前完整调用图 |
| `audit/FULL_CAPABILITY_INVENTORY.md` | 现有能力族清单 | 作为 Inventory，不作为生产完成声明 |
| `序境/08-AUDIT/P0_api_endpoints_inventory.json` | API 清单快照 | 必须与真实 Flask route map 和消费者复核 |
| `heritage_intelligence/_inventory/` | 5 仓、130 分支、2986 Commit、5449 unique knowledge blobs | 只代表知识来源覆盖，不代表 Runtime 迁移 |

当前审计确认 334 条 Feature Registry 记录混合 Capability、实现、脚本、Provider 和实验资产，且大量缺少 DB、API、Frontend、Permission、Test、Runtime Evidence 字段。

## 4. 当前目录与实现关系

```text
LUMENIS Clean Repository
├── Production candidates
│   ├── app.py / Flask routes
│   ├── database.py / database_migrations.py
│   ├── collector.py / collector_v2 / platform_adapters
│   ├── evidence_chain.py / canonical_data.py / canonical_metrics.py
│   ├── event_graph.py / risk_engine.py / report_engine.py
│   ├── permission_gate.py / security_boundary.py / action firewall
│   └── frontend templates / static / viz / view model
├── Compatibility and historical candidates
│   ├── v4_upgrade
│   ├── report_export
│   ├── old API and route aliases
│   └── governance path backups
├── Research / knowledge
│   ├── intelligence_library
│   └── heritage_intelligence
└── Tests / scripts / release assets
```

上述目录名不决定状态。任何实现必须进入 Dependency Trace 与 Runtime Verification 后才能标记 ACTIVE、LEGACY、DEPRECATED 或 DEAD。

## 5. Runtime 事实

| 项目 | 当前事实 |
|---|---|
| 地址 | `http://127.0.0.1:8202` |
| 启动参数 | `app.py --host 127.0.0.1 --port 8202 --no-scheduler` |
| 实际资产来源 | 哈希匹配 `D:\Z-Brand-Core_MAIN_AUDIT` |
| 与清洁仓关系 | 无；该实例由 `D:\Z-Brand-Core_MAIN_AUDIT` 启动，不是清洁仓 Runtime |
| Scheduler | 当前实例明确禁用 |
| Worker | 0 |
| Guardian | UNKNOWN |
| Collection | `NO_RUN` |
| 平台状态 | 小红书 `SESSION_EXPIRED`、需要人工处理、stop request |
| AI | 当前 8202 为 disabled / local rule；不能证明生产模型调用 |

当前健康接口没有 `release_id/core_commit/product_mode/db/schema/profile`，Runtime 不能自证血缘。

### 5.1 `D:\Taikoo-monitor-new` 活跃但未获准晋级的候选

该路径不是离线历史目录：8201 当前由 `run_supervised.py → app.py` 提供服务，并启动 9222 Edge CDP。它仅是待收敛的 Runtime / 数据资产候选，不是已验证纯净版，也不是已发布版本。Local HEAD 为 `fda599a...`，fetch 后落后 `origin/main` 两个 Commit；tracked 工作树 clean，但有 644 个 ignored 状态条目。

其主数据库有 1044 notes、510 events、40 reports 和 35 条外键违规。Health Summary 报告今日采集正常，但当日 collection log 只出现 3 次 `NETWORK_ERROR`，Guardian 为 degraded、运行 worker 为 0。完整证据见 `TAIKOO_MONITOR_NEW_RUNTIME_ASSET_AUDIT_V1.md`。

## 6. 数据库事实

| 数据库 | 当前事实 | 状态 |
|---|---|---|
| `Z-Brand-Core_MAIN_AUDIT/data/monitor.db` | 8202 候选运行库；62 表；notes/events/reports 为 0 | 可读，不是清洁仓数据库 |
| `Taikoo-monitor-new/data/monitor.db` | 8201 活跃候选；1044/510/40；35 FK 违规 | 最高保护；只能对副本迁移 |
| 原工作区数据库 | 有业务数据，但审计发现 43 条外键违规 | 受保护，不得直接迁移/清理 |
| 清洁仓 `data/monitor.db` | 被 Git 忽略；OSAI 边界测试曾写入 Task/Evidence/Worker 数据 | 测试隔离失败，不得视为纯净生产库 |
| 便携包数据库 | Schema 与状态数据不满足客户 Release 验收 | 不可发布 |

数据库迁移在 clean bootstrap 的 v9→v10 路径出现过依赖 `canonical_data` 尚未创建的问题。当前不能声明空库安装、历史升级和回滚三条路径均通过。

## 7. 产品页面事实

| 产品/层 | 真实页面结果 | 当前状态 |
|---|---|---|
| CTH | `/lumenis/cth/overview` 200 | 页面可访问；健康状态与 API 冲突 |
| BMP | `/lumenis/bmp/overview` 404 | 未验证 |
| 旧 ZBMP | `/lumenis/zbmp/overview` 200，但展示 CTH 并提示保护未配置 | 兼容冲突 |
| Content | `/lumenis/content?domain=cth` 200 | Shared 候选，Contract 未收敛 |
| Podcast | 200，但标题仍带 ZBMP | 历史语义未清理 |
| SYSTEM Runtime | 200，显示 0 Worker、Guardian UNKNOWN | 页面可访问，运行不健康 |

CTH 页面把 `NO_RUN/SESSION_EXPIRED/--no-scheduler` 显示为“运行中、采集正常、所有模块正常”，属于 P0 Production Truth 冲突。

## 8. 数据真相链事实

目标链：

```text
External Data → Evidence → Canonical Data → Function → Metric
→ Truth Table → View Model → Visualization → UI / Report / Export
```

当前确认：

- Evidence 与 Canonical 存在多套承载候选；
- `canonical_data` 与 `zbc_canonical_data` 并存；
- Metric 可从 notes 直算、Canonical 计算或快照读取；
- Report 存在多生成器和导出入口；
- 页面并非全部消费统一 View Model；
- 无数据时仍出现 50 分健康度；
- AI 字段与确定性事实字段尚未在所有报告中强制隔离。

状态：`FAIL / PRODUCTION BLOCKED`。

## 9. AI、Agent 与跨仓事实

- AI Gateway、Provider fallback、Agent、Permission、Evidence、Evaluation、Trace 构件存在；
- 尚未证明所有用户任务经过唯一 Orchestrator；
- 尚未证明所有生产写入强制经过 Permission → Firewall → Effect Fence → Approval；
- LUMENIS 存在直接动态导入或子进程调用 OSAI 内部模块的实现，与最终跨仓 Contract 边界冲突；
- OSAI 远程 Contract 单测 45 项通过，不等于跨仓 E2E 通过；
- GGI outbox 实现存在，但当前提交测试因缺失模块无法收集；
- Command 的 Evidence 源码被 `.gitignore` 排除，远程事实不完整；
- Ollama 已在审计中真实调用成功；智谱/OpenCode 最近一次调用认证失败；二者都不能改变生产事实。

## 10. 当前总状态

```text
Product Architecture：DEFINED
Source Inventory：AVAILABLE / CURRENT STATUS PARTIAL
Capability Canonicalization：PARTIAL
Data Truth Chain：FAIL
Frontend Redesign Baseline：READY / NOT IMPLEMENTED
Dynamic Decision Design：READY / NOT OPERATING
AI Agent Admission：NOT VERIFIED
Engineering Release Gate：FAIL
Release Lineage：NOT VERIFIED
Clean Runtime：NOT VERIFIED
BMP Runtime：NOT VERIFIED
Cross-Repo Contract：PARTIAL
Production Release：NO-GO
```
