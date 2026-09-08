# LUMENIS 数据库与运行事实单一基线 V1

状态：第 6 类“数据库与运行事实核验”交付物  
审计基线：`78c469d81905568350338f9d01e2ce5baf3c6c67`  
本轮范围：只读核验数据库路径、启动顺序、Schema、迁移、运行进程、API 与真实页面事实。

## 1. 研究与判定原则

本轮研究由 OpenCode 使用智谱配置读取 `app.py`、`database.py`、`database_migrations.py`、`runtime_guardian.py`、`runtime_preflight.py`、`config.py`；Ollama 进行独立检查建议。模型输出中的不存在文件名或未经源码支持的结论均被剔除。

数据库健康必须分别检查：

`路径 → 进程 → Schema → migration version → integrity_check → foreign_key_check → 核心数据 → API → 页面`

“服务健康”“数据库文件存在”“迁移函数存在”都不能单独证明生产运行正确。

## 2. 代码事实

### 数据库路径来源

- `database.py:22`：默认使用仓库目录下 `data/monitor.db`，支持 `ZBC_DB_PATH` 覆盖。
- `database_migrations.py:22`：采用同样的默认路径规则，并支持 `ZBC_DB_PATH`。
- `runtime_guardian.py`：同样读取 `ZBC_DB_PATH` 或自身基准路径。
- `app.py` 启动阶段使用 `db.DB_PATH`，并将其传给 Evidence、Canonical 和质量表初始化。

代码层存在统一环境变量入口，但运行时事实证明当前服务实际落在另一个根目录，说明“代码默认路径一致”没有转化为“运行实例路径唯一”。

### 启动顺序

从 `app.py` 真实源码确认的顺序：

1. 导入 runtime preflight。
2. `db.init_db()`。
3. `_dm.migrate()`。
4. 质量日志表初始化。
5. `evidence_chain.init_db(db.DB_PATH)`。
6. `canonical_data.ensure_canonical_table(db.DB_PATH)`。
7. 运行服务与各 API/Guardian 路径继续启动。

迁移发生在 Evidence/Canonical 专用表初始化之前；已有清洁临时库实测迁移阶段在 v9→v10 访问 `canonical_data` 时出现 `no such table: canonical_data`，随后回滚到 v0。完整导入 app 后表可以被补建，但这不是迁移成功证据。

### 运行健康判定

`runtime_preflight.py` 默认可只记录不阻断，只有 `ZBC_PREFLIGHT_ENFORCE=1` 才进入 P0 阻断语义。因而“preflight 有输出”不能直接等价于“生产基线通过”。

`runtime_guardian.py` 自行初始化运行表，并提供 worker、checkpoint、DLQ、lease 等状态；但运行 API 当前显示 workers 为空、reaper 未运行，不能把 guardian overall healthy 解释为采集链路正在生产运行。

## 3. 运行时实测

实测地址：`http://127.0.0.1:8202`。

| 检查项 | 实测结果 |
|---|---|
| `/api/health` | `ok=true`、database=ok、端口 8202、version 5.9.9 |
| `/api/system/runtime` | `zbc_root=D:\Z-Brand-Core_MAIN_AUDIT` |
| 运行数据库 | `D:\Z-Brand-Core_MAIN_AUDIT\data\monitor.db` |
| 表对象 | 62 |
| 核心数据 | notes/events/daily_reports = 0/0/0 |
| Guardian | overall healthy；workers 为空；reaper_running=false |
| `/api/status` | provider=ollama，model=qwen2.5-coder:7b-agent，total_notes=0 |
| `/api/cth/overview` | CTH subject=guangzhou_taikoo_hui，total_notes=0，total_canonical=0，total_web_mentions=0 |

此前真实页面已确认：CTH 概览页面能打开，页面标题为“商业运营总览 · 序境 LUMENIS”，KPI、趋势和信息流为空，与当前 API 一致。

## 4. 数据库实测对照

| 数据库 | 表对象 | integrity_check | foreign_key_check | notes/events/reports |
|---|---:|---|---:|---:|
| 工作区 `D:\Z-Brand-Core\data\monitor.db` | 130 | ok | 43 | 1020 / 494 / 40 |
| 运行实例 `D:\Z-Brand-Core_MAIN_AUDIT\data\monitor.db` | 62 | ok | 0 | 0 / 0 / 0 |
| 清洁克隆测试库 | 6（测试产生） | ok | 0 | 未形成生产数据 |

工作区数据库的违规对象集中在 `ai_task_step`、`ai_task_trace` 和 `content_generation_evidence` 的父引用关系。未执行任何清理、修复、重建或迁移写入。

## 5. 单一基线判定

### 当前唯一可确认的事实

- 8202 服务是健康可访问的。
- 8202 当前使用 MAIN_AUDIT 数据库。
- 8202 当前核心业务数据为 0。
- 工作区另有一份有业务数据但有 43 条外键违规的数据库。
- 清洁仓库默认设计为使用自身 `data/monitor.db`，但当前运行实例没有使用清洁仓库路径。

### 不能宣称的内容

- 不能宣称清洁仓库已经成为当前运行版本。
- 不能宣称工作区数据库是当前生产数据库。
- 不能宣称 API 的 0 条是采集无数据，而不是运行库选择不同。
- 不能宣称数据库迁移链已经在空库和有数据库上都成功。
- 不能宣称 Guardian healthy 就代表 Collector、Worker、Queue 和 Report 正在运行。

## 6. 生产基线阻断项

1. **运行实例归属不唯一**：服务根目录与当前清洁审计仓库不一致。
2. **数据集归属不唯一**：工作区有数据库，运行实例使用另一数据库。
3. **迁移顺序存在风险**：迁移 v9→v10 依赖尚未由启动顺序保证存在的 `canonical_data`。
4. **数据完整性未达标**：工作区数据库存在 43 条外键违规。
5. **健康状态粒度不足**：overall healthy 与 worker/reaper 空状态并存。
6. **空数据语义未闭环**：API 能返回 0，但尚未让用户明确区分真实空、库错、采集未运行和过滤为空。

## 7. 七项验收

| 验收项 | 结果 | 证据 |
|---|---|---|
| Source | PASS | 数据库、迁移、app 启动、preflight、guardian 源码已读取 |
| Call Graph | PASS | 已确认 app 初始化与 migration 顺序、DB_PATH 传播路径 |
| Data / API | FAIL | 运行 DB 与工作区 DB 分裂；核心数据量不一致；工作区 FK=43 |
| Frontend / Consumer | PARTIAL | CTH 页面与 API 同步显示 0，但无法证明其来源为清洁基线 |
| Runtime | FAIL | 8202 运行根目录不是当前审计清洁仓库；workers 为空 |
| Tests | PARTIAL | 既有运行时/迁移测试资产存在；空库迁移实测暴露 v9→v10 顺序问题 |
| Production Evidence | FAIL | 尚未形成唯一仓库、唯一进程、唯一数据库、唯一版本的可发布证据 |

## 8. 本类结论与后续边界

第 6 类审计完成，最终状态：`FAIL / BASELINE NOT RELEASEABLE`。

本轮只建立事实，不修复。后续进入前端产品重构前，必须先完成经用户确认的基线切换方案：明确唯一运行仓库、唯一数据库、备份策略、迁移顺序、回滚证据和页面/API 数据来源。任何方案都不得覆盖或删除现有工作区数据库。

