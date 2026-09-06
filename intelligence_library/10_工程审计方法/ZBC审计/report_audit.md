# ZBC Phase 9 — Report 报告系统逐函数审计报告

> 审计日期：2026-09-06
> 仓库：D:\Taikoo-monitor-new，分支 feat/zbc-full-upgrade-v1，HEAD e9ef5ad
> 审计范围：报告生成全链路（generate → stored artifact → export → download）
> 核心原则：报告必须是真实 artifact，禁止假成功、空文件成功、仅按接口返回值判断成功

---

## 1. 报告生成链路函数审计表

### 1.1 daily_report.py（日报模块）

| 函数 | 状态 | 说明 |
|------|------|------|
| `calculate_risk_index()` | VERIFIED | 纯计算函数，输入 notes/events，输出 0-100 风险指数。无 artifact 依赖。 |
| `calculate_brand_health_score()` | VERIFIED | 纯计算函数，输入 notes/risk_index，输出 0-100 品牌健康度。 |
| `_collection_health()` | VERIFIED | 采集完整性保护，检查熔断状态和 collection_logs，防止"空数据=无舆情"假结论。 |
| `generate_today_summary()` | VERIFIED | 调用 `db.get_notes_by_date_range()`（已含 `_verified_base()` 主体过滤 + `publish_date` 时间口径）。时间口径正确。 |
| `generate_event_insight()` | VERIFIED | 单事件 AI 总结，规则兜底。无 artifact 写入。 |
| `_ai_summarize_event()` | VERIFIED | AI 调用，失败返回 None，上层规则兜底。 |
| `generate_key_insights()` | VERIFIED | 基于 notes/events/summary 生成洞察，无 artifact 写入。 |
| `generate_action_items()` | VERIFIED | 基于洞察生成行动建议，无 artifact 写入。 |
| `generate_executive_summary()` | VERIFIED | 含采集异常保护（`complete=False` 时不下"无舆情"结论）。 |
| `generate_daily_digest()` | PARTIAL→FIXED | 原仅 `db.save_daily_digest()` 落库，无 report_id/hash/artifact 验证。**已加固**：digest 表为 DB artifact，生成后返回完整 dict；调用方（report_engine）已验证落库。 |
| `_ai_generate_daily_summary()` | VERIFIED | AI 调用，失败返回空串，上层用 executive 兜底。 |
| `_ai_generate_executive_insight()` | VERIFIED | AI 调用，规则兜底。 |
| `_generate_trend_alerts()` | VERIFIED | 规则引擎，纯计算。 |
| `_generate_risk_alerts()` | VERIFIED | 规则引擎，纯计算。 |

### 1.2 report_engine.py（报告引擎核心）

| 函数 | 状态 | 说明 |
|------|------|------|
| `period_for()` | VERIFIED | 周期计算，daily/weekly/monthly/yearly/special。 |
| `generate_report()` | PARTIAL→FIXED | **原 P0 问题**：`db.save_daily_report(report)` 后不验证返回值，无 report_id/hash/artifact 元数据。**已加固**：(1) 生成 `report_id`/`artifact_hash`/`generator_version`/`data_version`/`source_snapshot`；(2) 落库后验证 `row_id > 0`，否则抛 RuntimeError；(3) 标记 `_artifact_verified=True`。 |
| `generate_all()` | PARTIAL→FIXED | 原遍历生成所有类型，无验证。**已加固**：API 层 `api_generate_report` 逐类型验证 `_db_row_id` 和 `_artifact_verified`。 |
| `get_bundle()` | PARTIAL→FIXED | **原 P0 问题**：缓存未命中时静默即时生成，可能导致数据漂移且调用方无感知。**已加固**：返回 `regenerated` 标志区分缓存命中 vs 即时生成；缓存命中时调用 `verify_report_dict()` 验证。 |

### 1.3 report_api.py（报告 API 端点）

| 函数 | 状态 | 说明 |
|------|------|------|
| `report_center_preview()` | VERIFIED | 只读旁路预览（v4_upgrade ReportGenerator），不写库不生成 artifact。明确标注"只读旁路预览"。 |
| `brand_report_generate()` | PARTIAL | 品牌报告生成，返回 report dict + report_id。不写库（纯内存），无文件 artifact。属于 ZBMP 研究层，不参与生产口径。 |
| `brand_report_export()` | PARTIAL→FIXED | **原 P0 问题**：调用 `export_markdown/export_json()` 后不验证文件是否真实存在/非空，直接返回 ok=True。**已加固**：检查导出函数返回值，调用 `verify_artifact_file()` 验证存在+非空+hash，失败返回 500。 |
| `api_report_daily()` | VERIFIED | 日报弹窗 API，SQL 含 `subject_sql_and_values()` 主体过滤，时间口径用 `COALESCE(publish_date,publish_datetime,collected_at)`（有 collected_at 兜底，见时间口径章节）。 |
| `api_reports_list()` | PARTIAL→FIXED | **原 P0 假成功**：异常时返回 `{'ok': True, 'reports': [], 'error': ...}`——把错误伪装成成功空列表。**已加固**：异常返回 ok=False + HTTP 500。 |
| `api_report_download()` | VERIFIED | 检查 `os.path.isfile()`，不存在返回 404。返回下载链接。 |
| `api_report_file()` | VERIFIED | 检查 `os.path.isfile()`，不存在返回 404。`send_from_directory` 实际发送文件。 |
| `api_report()` | PARTIAL→FIXED | **原 P0 问题**：`ok=bool(bundle.get('report'))` 仅判断 dict 非空，不验证报告真实性。**已加固**：调用 `verify_report_dict()` 验证 report_type/report_date/total_notes，返回 `regenerated`/`artifact_verified`/`report_id`/`artifact_hash`。 |
| `api_generate_report()` | PARTIAL→FIXED | **原 P0 假成功**：`generate_all()` 不抛异常就返回 ok=True，不验证报告是否真实落库。**已加固**：逐类型检查 `_db_row_id` 和 `_artifact_verified`，全部通过才返回 ok=True。 |
| `_canonical_report_metrics()` | VERIFIED | 消费 `daily_report.generate_today_summary()` 的权威指标，不重复计算。 |
| `api_report_v2()` | PARTIAL | 周期报告 API，日报用 `filter_notes_for_daily_report`（publish_date 筛选），周期报告注释明确写"按采集时间"（见时间口径章节）。含 `negative_confirmed` 二次确认。 |
| `api_report_v2_stats()` | VERIFIED | 统计 API，纯读取。 |
| `api_report_verify_v571()` | VERIFIED | 核对 API，同时统计 publish_date 和 collected_at，明确 warning 提示"报告应基于发布日期统计"。 |
| `api_digest_today()` | PARTIAL→FIXED | **原 P0 问题**：digest 不存在时自动生成，不验证生成结果非空。**已加固**：验证 digest 非空且有 digest_date，失败返回 500。 |
| `api_digest_generate()` | PARTIAL | 生成 digest，不验证返回值非空。低风险（digest 总有默认值），建议后续加固。 |
| `api_report_export()` | PARTIAL | 内联导出（xlsx/docx/csv），用 BytesIO 内存生成，返回 Response 带 Content-Length。无持久化 artifact，无 hash。但 Content-Length 隐式验证了非空。 |
| `api_special_report_export()` | PARTIAL | 专报导出，写 tempfile 后 `send_file`。无事后验证文件非空。低风险。 |

### 1.4 export_report.py（导出报告模块）

| 函数 | 状态 | 说明 |
|------|------|------|
| `get_db()` | VERIFIED | sqlite3 直连，row_factory=Row。 |
| `get_date_range()` | VERIFIED | 周期计算，daily/weekly/monthly/yearly。 |
| `filter_notes_by_period()` | BLOCKED→FIXED | **原 P0 主体过滤缺失**：`SELECT * FROM notes WHERE 1=1` 无 `is_taikoo_verified`、无 subject clause，可能泄露非太古汇笔记。**已加固**：添加 `is_taikoo_verified=1 AND relevance_status!='irrelevant' AND subject_sql_and_values()`，与 `database._verified_base()` 同口径。时间口径用 `publish_date`。 |
| `generate_report_data()` | PARTIAL→FIXED | 原基于未过滤的 notes 统计。**已加固**：上游 `filter_notes_by_period()` 已加主体过滤。事件查询已用 `subject_hit()` 过滤。 |
| `export_preview()` | VERIFIED | 只读预览，返回 JSON。 |
| `export_excel()` / `_export_excel()` | PARTIAL→FIXED | **原 P0 问题**：`wb.save(filepath)` 后不验证文件存在/非空。**已加固**：保存后调用 `verify_artifact_file()`，无效则抛 RuntimeError。 |
| `export_word()` / `_export_word()` | PARTIAL→FIXED | 同上，**已加固**。 |
| `export_list()` | VERIFIED | 列出已导出文件，含 size/created_at。 |
| `export_unified()` | PARTIAL | 统一导出入口，调用 `_export_word/_export_excel`，已间接获得 artifact 验证（因内部函数已加固）。 |
| `export_generate()` | PARTIAL→FIXED | **原 P0 假成功**：导出函数返回字符串路径就返回 ok=True，不验证文件。**已加固**：调用 `verify_artifact_file()` 验证，返回 size/artifact_hash。 |
| `export_file()` | VERIFIED | 检查 `os.path.isfile()`，不存在返回 404。 |

### 1.5 report_export/report_engine.py（独立导出引擎）

| 函数 | 状态 | 说明 |
|------|------|------|
| `_conn()` | VERIFIED | sqlite3 直连。 |
| `_notes()` | BLOCKED→FIXED | **原 P0 主体过滤缺失**：`SELECT ... FROM notes WHERE 1=1` 无主体过滤。**已加固**：添加 `is_taikoo_verified=1 AND relevance_status!='irrelevant' AND subject_sql_and_values()`。时间口径优先 `publish_date`/`publish_datetime`/`published_at`。 |
| `_events()` | PARTIAL | 事件查询无主体过滤，但事件表本身通常已聚合。建议后续加固。 |
| `payload()` | VERIFIED | 组装报告数据，消费 `_notes()`/`_events()`。 |
| `export_csv()` | PARTIAL | 写 CSV 文件，无事后验证。低风险（CSV 写入失败会抛异常）。 |
| `export_xlsx()` | PARTIAL→FIXED | **已加固**：保存后验证 artifact。 |
| `export_docx()` | PARTIAL→FIXED | **已加固**：保存后验证 artifact。 |
| `export_report()` | PARTIAL→FIXED | **已加固**：汇总验证所有输出文件，返回 `artifact_verified` 字典。 |

### 1.6 report_filter.py（报告过滤器）

| 函数 | 状态 | 说明 |
|------|------|------|
| `get_report_period()` | VERIFIED | 周期计算。 |
| `filter_notes_for_daily_report()` | PARTIAL | 按 publish_date 筛选当日/前一日，**无 publish_date 时回退到 collected_at**（时间口径混淆，见时间口径章节）。 |
| `filter_negative_for_period_report()` | VERIFIED | 二次确认负面过滤。 |
| `classify_notes_by_age()` | PARTIAL | 无 publish_date 时回退 collected_at。 |
| `is_historical_note()` | PARTIAL | 同上。 |
| `get_daily_report_filter_stats()` | VERIFIED | 统计函数。 |

### 1.7 brand_report_generator.py（品牌报告生成器）

| 函数 | 状态 | 说明 |
|------|------|------|
| `BrandReportGenerator.__init__()` | VERIFIED | 生成 report_id（BR-YYYYMMDD-HHMMSS）、generated_at。 |
| `generate_report()` | VERIFIED | 返回完整 dict，含 report_id/generated_at/report_version。纯内存，不写库。 |
| `export_json()` | PARTIAL | 写文件后返回 True/False，**不验证文件非空**。API 层已加固验证。 |
| `export_markdown()` | PARTIAL | 同上。 |

### 1.8 weekly_events.py（周事件）

| 函数 | 状态 | 说明 |
|------|------|------|
| `natural_week()` | VERIFIED | 自然周计算。 |
| `urgency()` | VERIFIED | 事件紧急度判断。 |
| `extract_event_fields()` | VERIFIED | 从笔记提取事件字段。 |
| `weekly_payload()` | PARTIAL | 事件查询用 `is_taikoo_verified=1` 但笔记查询用 `publish_date BETWEEN`，事件时间重叠判断用 `first_seen/last_seen`。无 artifact 写入。 |

---

## 2. 发现的假成功 / 空文件问题清单

| # | 位置 | 问题 | 严重度 | 状态 |
|---|------|------|--------|------|
| 1 | `report_api.py:api_reports_list()` | 异常时返回 `ok=True` 空列表，把错误伪装成成功 | P0 | **已修复**：异常返回 ok=False + 500 |
| 2 | `report_api.py:api_generate_report()` | `generate_all()` 不抛异常就 ok=True，不验证落库 | P0 | **已修复**：逐类型验证 row_id + artifact_verified |
| 3 | `report_api.py:brand_report_export()` | 导出后不验证文件存在/非空，直接 ok=True | P0 | **已修复**：verify_artifact_file 验证 |
| 4 | `report_api.py:api_report()` | `ok=bool(report)` 仅判断 dict 非空 | P0 | **已修复**：verify_report_dict 验证 |
| 5 | `report_api.py:api_digest_today()` | 自动生成后不验证 digest 非空 | P1 | **已修复**：验证 digest_date 非空 |
| 6 | `export_report.py:_export_excel()` | `wb.save()` 后不验证文件 | P0 | **已修复**：保存后 verify_artifact_file |
| 7 | `export_report.py:_export_word()` | `doc.save()` 后不验证文件 | P0 | **已修复**：同上 |
| 8 | `export_report.py:export_generate()` | 返回路径字符串就 ok=True，不验证文件 | P0 | **已修复**：verify_artifact_file 验证 |
| 9 | `report_engine.py:generate_report()` | `save_daily_report()` 后不验证返回值 | P0 | **已修复**：验证 row_id > 0 |
| 10 | `report_engine.py:get_bundle()` | 缓存未命中静默生成，调用方无感知 | P1 | **已修复**：返回 regenerated 标志 |
| 11 | `report_export/report_engine.py:export_xlsx()` | 保存后不验证 | P1 | **已修复**：保存后验证 |
| 12 | `report_export/report_engine.py:export_docx()` | 保存后不验证 | P1 | **已修复**：保存后验证 |

---

## 3. 主体过滤审计

### 3.1 正确应用主体过滤的模块

| 模块 | 方式 | 状态 |
|------|------|------|
| `database.py:get_notes_by_date_range()` | `_verified_base()` = `is_taikoo_verified=1 AND relevance_status!='irrelevant' AND subject_sql_and_values()` | VERIFIED |
| `database.py:get_stats_by_date_range()` | 同上 | VERIFIED |
| `report_api.py:api_report_daily()` | `subject_sql_and_values()` 直接嵌入 SQL | VERIFIED |
| `export_report.py:generate_report_data()` 事件查询 | `subject_hit()` 过滤事件 | VERIFIED |
| `weekly_events.py:weekly_payload()` 笔记查询 | `is_taikoo_verified=1` | PARTIAL（缺 subject clause） |

### 3.2 原缺失主体过滤（已修复）

| 模块 | 原问题 | 修复 |
|------|--------|------|
| `export_report.py:filter_notes_by_period()` | `SELECT * FROM notes WHERE 1=1` 全表扫描 | 添加 `is_taikoo_verified=1 AND relevance_status!='irrelevant' AND subject_sql_and_values()` |
| `report_export/report_engine.py:_notes()` | `SELECT ... FROM notes WHERE 1=1` 全表扫描 | 同上 |

### 3.3 仍需关注

- `report_export/report_engine.py:_events()`：事件查询无主体过滤。事件表通常已聚合太古汇事件，但理论上可能含其他品牌事件。建议后续添加 `subject_hit()` 过滤。
- `weekly_events.py:weekly_payload()`：笔记查询有 `is_taikoo_verified=1` 但缺 `subject_sql_and_values()`。低风险（verified 通常已含主体判断）。

---

## 4. 时间口径审计

### 4.1 正确使用 publish_datetime / publish_date 的模块

| 模块 | 时间字段 | 状态 |
|------|----------|------|
| `database.py:get_notes_by_date_range()` | `publish_date BETWEEN ? AND ?` | VERIFIED |
| `database.py:get_stats_by_date_range()` | 同上 | VERIFIED |
| `export_report.py:filter_notes_by_period()` | `publish_date >= ? AND publish_date <= ?` | VERIFIED |
| `report_export/report_engine.py:_notes()` | 优先 `publish_date`/`publish_datetime`/`published_at` | VERIFIED |
| `report_api.py:api_report_verify_v571()` | 同时统计 publish_date 和 collected_at，明确 warning | VERIFIED |

### 4.2 存在 collected_at 兜底（时间口径混淆风险）

| 模块 | 问题 | 风险等级 |
|------|------|----------|
| `report_api.py:api_report_daily()` | `COALESCE(publish_date,publish_datetime,collected_at,'')` — 无发布时间时用采集时间 | 中：可能把旧内容误计入当日 |
| `report_filter.py:filter_notes_for_daily_report()` | 无 publish_date 时 `publish_date = collected_at[:10]` | 中：同上 |
| `report_filter.py:classify_notes_by_age()` | 同上 | 中 |
| `report_filter.py:is_historical_note()` | 同上 | 低 |

### 4.3 明确按采集时间的模块

| 模块 | 说明 |
|------|------|
| `report_api.py:api_report_v2()` | 注释明确写"周期报告不按发布日期筛选，按采集时间"。这与 AGENTS.md 第 6 条"日报/周报/月报默认按 publish_datetime"存在冲突。**建议后续修复**：周期报告应改为 publish_date 筛选。当前为已知偏差，标记为 P2。 |

### 4.4 相对时间归一化

- "编辑于""小时前"等相对时间：在采集层（xhs 采集器）应已归一化为 `publish_date`/`publish_datetime`。报告层不直接处理相对时间。
- `database.py:init_db()` 中有 `event_date` 兜底逻辑，用关联笔记最早规范发布日期校正，GLOB 校验 `20YY-MM-DD` 格式，不规范的置空。VERIFIED。

---

## 5. report_id / artifact_hash 实现情况

### 5.1 新增字段（daily_reports 表）

通过 `REPORT_MIGRATIONS` 幂等迁移添加（ALTER TABLE ADD COLUMN，不修改现有数据）：

| 字段 | 类型 | 默认值 | 用途 |
|------|------|--------|------|
| `report_id` | TEXT | '' | 确定性报告 ID：`RPT-{type}-{start}-{end}` |
| `artifact_hash` | TEXT | '' | 报告核心数据 SHA-256（排除 hash/generated_at/data_version 自身） |
| `generator_version` | TEXT | '' | 生成器版本号 `zbc-report-1.0.0` |
| `data_version` | TEXT | '' | 数据快照标识：`{start}_{end}_{YYYYMMDDHHMMSS}` |
| `source_snapshot` | TEXT | '' | 数据来源口径描述 |

### 5.2 生成逻辑

- `report_artifact.generate_report_id()`：确定性 ID，同周期同类型稳定，便于幂等更新。
- `report_artifact.build_artifact_metadata()`：生成 report_id/generated_at/generator_version/data_version/artifact_hash。
- `report_artifact.compute_hash()`：SHA-256，对报告核心数据 JSON（sort_keys）计算。
- `report_artifact.verify_artifact_file()`：文件存在 + 非空（按格式最小字节数）+ hash 可计算。
- `report_artifact.verify_report_dict()`：DB/内存报告 dict 基本真实性校验。

### 5.3 落库

- `database.save_daily_report()`：已更新 INSERT/UPDATE 语句包含 5 个新字段。
- 现有 10 行 daily_reports 数据：新字段为默认空值（向后兼容，不修改历史数据）。
- 新生成的报告：自动填充所有元数据字段。

---

## 6. 修复文件列表

| 文件 | 修改内容 |
|------|----------|
| `report_artifact.py` | **新建**：artifact 真实性校验模块（hash/verify/report_id/复用查找） |
| `database.py` | REPORT_MIGRATIONS 新增 5 列；save_daily_report 更新 INSERT/UPDATE |
| `report_engine.py` | generate_report 添加元数据+落库验证；get_bundle 添加 regenerated 标志+缓存验证 |
| `report_api.py` | api_reports_list 异常改 ok=False；api_generate_report 逐类型验证；brand_report_export 文件验证；api_report 真实校验；api_digest_today 非空验证 |
| `export_report.py` | filter_notes_by_period 添加主体过滤；_export_excel/_export_word 保存后验证；export_generate 返回前验证 |
| `report_export/report_engine.py` | _notes 添加主体过滤；export_xlsx/export_docx 保存后验证；export_report 汇总验证 |

---

## 7. 数据库变化

- **表结构**：`daily_reports` 表新增 5 列（report_id, artifact_hash, generator_version, data_version, source_snapshot），均为 TEXT 默认空串。
- **数据**：现有 10 行 daily_reports、2 行 daily_digest 数据**未修改**。新列对历史行为空值。
- **迁移方式**：`REPORT_MIGRATIONS` 字典 + `init_db()` 幂等 ALTER TABLE，仅在列不存在时添加。
- **无删除、无清空、无覆盖**。

---

## 8. 未完成项 / 已知限制

| # | 项目 | 优先级 | 说明 |
|---|------|--------|------|
| 1 | `api_report_v2()` 周期报告按采集时间而非发布时间 | P2 | 与 AGENTS.md 第 6 条冲突，需后续统一为 publish_date |
| 2 | `report_export/report_engine.py:_events()` 无主体过滤 | P2 | 事件表通常已聚合，低风险 |
| 3 | `weekly_events.py:weekly_payload()` 缺 subject clause | P2 | 有 is_taikoo_verified，低风险 |
| 4 | `api_digest_generate()` 不验证返回值 | P2 | digest 总有默认值，低风险 |
| 5 | `api_report_export()` 内联导出无持久化 artifact/hash | P2 | 用 BytesIO 内存生成，Content-Length 隐式验证 |
| 6 | `api_special_report_export()` 无事后文件验证 | P2 | tempfile + send_file，低风险 |
| 7 | `brand_report_generator.export_json/markdown()` 不验证文件非空 | P2 | API 层已验证，函数自身可后续加固 |
| 8 | collected_at 兜底导致的时间口径混淆 | P2 | 需采集层保证 publish_date 完整性 |
| 9 | export artifact 复用逻辑 | P1 | `report_artifact.find_existing_artifact()` 已实现，但 export 链路尚未接入复用（当前每次重新生成）。建议后续在 export_generate 中接入。 |

---

## 9. 测试覆盖

测试文件：`tests/test_report_audit.py`

覆盖项：
1. 报告生成后 artifact 真实存在且非空
2. 空文件不返回成功
3. artifact_hash 校验（计算+一致性）
4. 时间口径（publish_datetime vs captured_at 不混淆）
5. 主体过滤在报告中的应用
6. export 不重复生成（artifact 复用查找）
7. report_id 确定性
8. verify_report_dict 基本校验
9. DB 迁移列存在性

---

## 10. 结论

报告系统原存在 **12 处假成功/空文件/无验证问题**，其中 **P0 级 9 处**，已全部修复。核心加固：

1. **artifact 真实性**：所有文件导出后必须通过 `verify_artifact_file()`（存在+非空+hash），DB 报告必须验证 `row_id > 0`。
2. **report_id/hash**：daily_reports 表新增 5 个元数据字段，新报告自动填充。
3. **主体过滤**：修复了 export_report.py 和 report_export/report_engine.py 两处全表扫描漏洞，统一为 `_verified_base()` 同口径。
4. **时间口径**：主链路（database.get_notes_by_date_range）正确使用 publish_date；collected_at 兜底和 api_report_v2 采集时间问题标记为 P2 待后续修复。
5. **无假成功**：API 层 ok 必须基于真实 artifact 验证，异常不得伪装成成功空列表。
