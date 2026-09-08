# LUMENIS 数据真相链审计 V1

状态：第 5 类“数据真相链审计”交付物  
审计提交：`78c469d81905568350338f9d01e2ce5baf3c6c67`  
本轮原则：只读核验；未修改数据库、未同步数据、未删除实现、未把 AI 输出当作事实。

## 1. 审计链路

目标链路：

`External Data → Evidence → Canonical Data → Function → Metric → Truth Table → View Model → Visualization → Report`

业务情报链补充为：

`Source → Evidence → Event → Case → Finding → Decision → Action → Outcome → Evaluation`

### 本轮判定规则

SQLite 的 `PRAGMA integrity_check` 只证明底层格式、索引和约束的一部分；它不检查外键，外键必须另行执行 `PRAGMA foreign_key_check`。本轮同时执行二者。SQLite 的事务原子性也不能证明应用选对了数据库、选对了时间字段或没有重复计算。

## 2. 真实数据库与运行时事实

### 当前服务 8202

实测接口：`/api/system/runtime`、`/api/system/database`、`/api/cth/overview`、`/api/status`、`/api/health`。

| 项目 | 当前运行事实 |
|---|---|
| 运行根目录 | `D:\Z-Brand-Core_MAIN_AUDIT` |
| 运行数据库 | `D:\Z-Brand-Core_MAIN_AUDIT\data\monitor.db` |
| 表对象 | 62 |
| notes / events / daily_reports | 0 / 0 / 0 |
| CTH overview | `total_notes=0`、`total_canonical=0`、`total_web_mentions=0` |
| AI 状态 | API status 显示 provider `ollama`，模型 `qwen2.5-coder:7b-agent` |
| runtime guardian | overall healthy；workers 为空；`reaper_running=false` |
| health | database ok，服务端口 8202 |

此前已打开的真实 CTH 页面显示标题“商业运营总览 · 序境 LUMENIS”，页面 KPI、趋势、信息流均为空；与本轮运行 API 的 0 数据一致，但不能推导工作区数据库也为空。

### 数据库文件对照

| 数据库 | 表数量 | integrity_check | foreign_key_check | notes | events | reports | 其他关键事实 |
|---|---:|---|---:|---:|---:|---:|---|
| `D:\Z-Brand-Core\data\monitor.db` | 130 | ok | 43 | 1020 | 494 | 40 | canonical_data 14、zbc_evidence 6、zbc_canonical_data 4、metric_snapshots 1087、app_evidence_records 22、ai_call_logs 1847 |
| `D:\Z-Brand-Core_MAIN_AUDIT\data\monitor.db` | 62 | ok | 0 | 0 | 0 | 0 | 运行服务实际使用，非工作区数据集 |
| `D:\LUMENIS_REBUILD\Z-Brand-Core\data\monitor.db` | 6（测试产生） | ok | 0 | 未形成生产链路 | 未形成 | 未形成 | 清洁克隆测试副产物，非提交内容 |

工作区数据库的 43 条外键违规主要涉及：

- `ai_task_step` / `ai_task_trace` 指向不存在的 `ai_task`。
- `content_generation_evidence` 的自引用/父证据关系存在无效引用。

`integrity_check=ok` 与 `foreign_key_check=43` 同时成立，说明不能只用 integrity_check 宣称数据库健康。

## 3. 各阶段真实实现

### 3.1 External Data → Evidence

当前采集与外部数据入口分散在 `collector.py`、`collector_v2`、`web_monitor.py`、`web_monitor_v570.py`、平台适配器、浏览器运行时和 `app.py`。

已确认存在三类证据存储：

1. `evidence_chain.py`：`EvidenceStore` 写入 `zbc_evidence`，具备 hash、source、captured_at、publish_datetime、domain/product、trace 等字段。
2. `canonical_data.py`：由 `notes` / `web_mentions` 转换并写入 `canonical_data`。
3. `app_evidence.py` / `app_evidence_records`：应用证据记录，包含 metric、evidence_hash、verification、subject_scope 等。

结论：External Data 到 Evidence 的能力存在，但尚未证明所有 Collector 都统一进入同一个 canonical Evidence 门面；当前属于 `PARTIAL`。

### 3.2 Evidence → Canonical Data

`evidence_chain.py` 自己维护：

`zbc_evidence → zbc_canonical_data → zbc_lifecycle_tracking`

`canonical_data.py` 维护另一条：

`notes / web_mentions → note_to_canonical() / web_mention_to_canonical() → persist_canonical() → canonical_data`

`app.py` 的采集写入路径同时调用 EvidenceChain 与 `canonical_data.persist_canonical()`。这证明两条体系都可能被主应用触发，但没有证明二者由唯一 canonical ID、唯一写入口和统一读取层连接起来。

结论：存在双 Canonical 事实承载体系，属于最高优先级的重复真相风险；不得直接删除任何一方，必须先完成 ID、读写者、迁移和运行验证。

### 3.3 Canonical Data → Function → Metric

`canonical_metrics.py` 的函数主要接收 `list[dict]` 并计算情绪、风险、互动、比例和分组统计；它没有直接绑定一个唯一数据库读取入口。

`database.py` 还从 `notes` 直接提供 `get_stats()`、`get_metric_trend()` 等统计；`viz_data_provider.py` 的 overview 统计直接查询 `notes`，趋势使用 `collected_at`；`metric_snapshots` 由数据库函数另行记录。

因此当前至少存在三种统计输入形态：

- `notes` 直接统计。
- `canonical_data` / 双 Canonical 体系统计候选。
- `metric_snapshots` 快照统计。

结论：Metric 尚未形成唯一生产真相入口；存在重复计算和时间字段不一致风险，属于 `PARTIAL / HIGH RISK`。

### 3.4 Metric → Truth Table → View Model

`ui_view_model.py` 已实现 `DataResult`、`TruthTable`、`MetricLayer`、`ViewModel`、证据引用、freshness、confidence、缺失状态和可视化配置。

`viz_api.py` 的设计路径是：

`function registry → viz_data_provider → ui_view_model → API response`

但 `viz_data_provider.py` 的多个 Provider 直接以 `notes`、`events`、`metric_snapshots`、`ai_call_logs` 等表为数据源；不能仅凭 View Model 存在，证明所有实际页面都经过该路径。

结论：标准 View Model 体系存在；实际页面到该体系的全量接入尚未证实，属于 `PARTIAL`。

### 3.5 View Model → Visualization → Report

可视化标准入口在 `viz_api.py`，报告存在多条生成/导出链：

- `report_engine.generate_report()`：读取 notes/stats，调用 `ai_analyzer`，写入 `daily_reports`。
- `report_engine.generate_domain_report()`：CTH/BMP 双域报告路径，另写 JSON artifact。
- `daily_report.py`：日报计算/摘要路径。
- `report_api.py`：API、文档、导出和专题报告路由。
- `export_report.py`：报告导出数据生成。
- `brand_report_generator.py`：品牌报告独立生成器。

`report_engine.generate_report()` 虽然写入 `report_id`、`artifact_hash`、`data_version`、`source_snapshot` 等元数据，但同时调用 AI 过滤/分析；生产报告仍需验证每个数字是否由确定性数据和明确周期计算。

结论：报告具有审计元数据设计，但多入口并存，View Model 与 Report 尚未统一为单一生产报告编排入口，属于 `PARTIAL / HIGH RISK`。

## 4. 数据丢失、重复与 AI 覆盖检查

### 已确认或高度可见的风险

1. 运行时数据库与工作区数据库不同，导致真实页面 0 数据与工作区有数据并存；这是运行基线分裂，不是数据为空结论。
2. `canonical_data`、`zbc_canonical_data`、`app_evidence_records` 并存，可能造成同一外部事实重复存储、ID 不可回溯或读取路径分裂。
3. 统计既可直接读取 `notes`，又存在 canonical 与快照体系，存在重复计算风险。
4. `report_engine.py` 允许 AI 过滤/分析参与报告生成；当前代码注释和字段设计支持保留规则结果与 AI 结果，但尚未用生产样本证明 AI 永不覆盖确定性事实。
5. `daily_reports` 中存在 `ai_summary`、`key_insights`、`action_items` 等字段；必须区分事实字段、派生指标和 AI 建议字段。
6. `viz_data_provider.py` 返回 `no_data` 状态的设计存在，但当前运行页面的 0 数据还需要进一步区分“真实无数据、数据库选错、采集未运行、过滤后为空”。

### 当前没有证据支持的结论

- 不能宣称所有采集数据都已进入 Evidence。
- 不能宣称两个 Canonical 表已经完成合并或其中一个可以删除。
- 不能宣称报告数字全部来自 Truth Table。
- 不能宣称页面所有 KPI 都没有假数据；只能确认当前 CTH 页面显示为空，且 API 返回为空。
- 不能宣称 AI 已成功参与生产链；只能确认配置/状态信息存在，实际生产调用链仍需单独验证。

## 5. 七项验收

| 验收项 | 结果 | 依据 |
|---|---|---|
| Source | PASS | Evidence、Canonical、Metric、View Model、Viz、Report、DB 源码均已读取 |
| Call Graph | PARTIAL | `app.py` 同时触发两套 Canonical 写入；报告和导出存在多入口 |
| Data / API | FAIL | 运行 DB 与工作区 DB 分裂；工作区 DB 有 43 条外键违规；核心数据量不一致 |
| Frontend / Consumer | PARTIAL | CTH 真实页面与 API 均显示 0；全量页面到 View Model 尚未证明 |
| Runtime | FAIL | 8202 运行根目录为 `Z-Brand-Core_MAIN_AUDIT`，不是当前清洁审计仓库 |
| Tests | PASS / PARTIAL | 既有 Evidence、Canonical、Viz、双域和报告测试资产可运行；测试通过不能覆盖数据库基线分裂 |
| Production Evidence | FAIL | 没有一条统一数据库、统一 ID、统一报告真相链的生产证据 |

## 6. 第 5 类结论

第 5 类“数据真相链审计”完成，最终状态：`FAIL / PRODUCTION BLOCKED`。

核心阻断不是页面样式，而是：

1. 运行时和工作区使用不同数据库。
2. Evidence/Canonical 至少有两套正式候选体系。
3. Metric 既可从 notes 直算，也存在快照与 canonical 路径。
4. Report 存在多条生成/导出路径。
5. 工作区生产候选数据库存在 43 条外键违规。

下一项必须先建立“数据库与运行事实单一基线”，再进入前端动态化或报告重构；任何 UI 优化都不能覆盖上述真相链阻断。

## 7. 研究依据

- SQLite 官方 PRAGMA 文档：`integrity_check` 不检查外键，必须使用 `foreign_key_check`：<https://www.sqlite.org/pragma.html>。
- SQLite 官方事务文档：事务原子性保证单次事务的完整提交/回滚，但不替代应用层数据源、ID 和读写链路审计：<https://www.sqlite.org/transactional.html>。

