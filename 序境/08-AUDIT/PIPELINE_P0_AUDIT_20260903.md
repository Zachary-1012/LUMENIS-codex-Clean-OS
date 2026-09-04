# Unified Data Intelligence Pipeline V1.0 — P0 审计报告（Inventory / Reference Scan / 双真相识别）

- 日期：2026-09-03 ｜ 阶段：**P0（只审计，未改任何生产代码）** ｜ 状态：VERIFIED-IN-SCAN
- 事实基线：ZBC 生产库 `D:\Taikoo-monitor-new`（main）+ monitor.db 真实数据；全部数字由脚本扫描/DB 实查得到，非记忆。
- 扫描脚本（可复跑）：Temp/audit_a~f.py；机器清单：`序境/08-AUDIT/P0_api_endpoints_inventory.json`（165 端点）。

## 0. 真实底数
- 生产 Python（剔除 .venv/.git/__pycache__/.trae-cn(IDE缓存79503行)/tests/archive/staging）：核心 root 136 文件 50,855 行 + 各业务模块；路由装饰器约 **501** 个。
- 前端：static/js **40 个 JS**、**10 个 HTML**（index.html 2106 行）；前端共消费 **165 个 /api 端点**；产品页 **27 个 page-***。
- 数据库 monitor.db：**64 张表**（旧记录"51 表"已过时，以此为准）。另有根目录空库 `你的数据库文件名.db`（0 表，疑似误建，先登记不删）。

## 1. Data Inventory（64 表 / 12 业务域）
| 业务域 | 表数 | 主要表（行数） |
|---|---|---|
| 采集/笔记原始 | 10 | notes(1052,68列)、note_review_history(8419)、schedule_decisions(10308)、collection_logs(660)、note_comments(141)、ai_filter_log(919) |
| 事件/话题 | 11 | events(484)、event_mentions(1135)、topic_campaign_notes(481)/snapshots(406)、weekly_events(30)、event_graph_events/relations |
| KOS/KOL | 5 | kos_profiles(375,59列)、kos_executions(259)、kos_operations(108)、kos_paid_plans(38)、kos_rewards(19) |
| 品牌/案例/知识 | 7 | brand_industry_monitor(198)、brand_knowledge(103)、resources(321)、case_deep_analysis(20) |
| 报告 | 2 | daily_reports(43)、daily_digest(10) |
| Web 外部监测 | 5 | web_topics(96)/mentions(82)/events(20)/runs(31)/sources(1) |
| Swire/太古 | 3 | swire_projects(9)/events(32)/notes(0) |
| 播客 | 2 | podcast_entities(0)/ai_runs(0)（能力在建，无数据不造假） |
| Auth/工作区 v4 | 8 | v4_workspace_keys(674)/sessions(163)/grants(132)/audit_logs(42)/users(1) 等 |
| Evidence/评测 | 4 | app_evidence_records(41)、review_tickets/logs/samples(0) |
| 系统/配置/迁移 | 9 | metric_snapshots(250)、system_config(10)、schema_version(8)、alembic_version、token_stat、notification_* |
| 认证恢复（补） | 1 | auth_recovery_tasks(122) |

**数据时间口径**：notes 同时存在 publish_date / publish_datetime / collected_at，事件有 events 时间、topic 有 snapshot 时间——已具备"发布≠采集≠事件≠快照"多时间轴的物理基础（符合零号序列），P1 接入时逐 Metric 绑定正确时间字段。

## 2. Function Inventory — 计算实现分布与重复族（核心发现）
### 族 A：情感分布计数 positive/neutral/negative（≥8 文件 15+ 处独立实现）
| 位置 | 实现风格 | 输入集 |
|---|---|---|
| app.py L1651 | Python `cnt(rows_all,...)` | rows_all |
| app.py L2242 / L2499 / L1480-1484 | Python sum | notes / filtered_notes / 分品类循环 |
| app.py L2805 | **SQL** `SUM(CASE WHEN sentiment=...)` | 按 publish_date |
| daily_report.py L45/102/195/252/371 | Python sum（5 个函数各算一遍） | notes/effective_notes/event_notes |
| v4_upgrade/report_center/report_generator.py L128/251 | Python sum | notes |
| export_report.py L157 | Python sum | notes（+负面确认 pending_neg 特化） |
| intelligence.py L330 | Python sum | event notes |
| brand_stats_recompute.py L77 / reprocess.py L124 / report_export/report_engine.py L92 | Python sum | rows / mentions / 通用 cnt |

### 族 B：风险等级计数 high/medium/low —— **发现口径分叉（当前潜在）**
- 口径① `risk_level=='high'`：daily_report L46、export_report L162、app.py L2502/L2908/L2299。
- 口径② `risk_level in ('high','critical')`：report_center/report_generator L131。
- 口径③ 风险合计 `risk in ('high','medium')`：daily_report L197（其余处只算 high）。
- **DB 实证**：notes.risk_level 实际枚举仅 high=23 / medium=80 / low=949，**当前不存在 critical** → 口径①②当前数值等价（都=23），属**潜在双真相**：一旦未来写入 critical，报告中心与日报/导出立即出现两个"高风险"数字。P0 不夸大为已发生，但 Registry 必须锁死唯一口径。
- 自洽校验：sentiment 97+326+629=1052=总数（无空值），首页正面率 629/1052=59.8%、负面率 9.2% 与 UI 一致。

### 族 C：KOS/KOL 作者维度聚合（3+ 处，公式需对齐）
- kos_engine.py L92 SQL：note_count、total_likes（**仅 likes**）。
- kos_metrics.py L93 SQL：exposure = likes+comments+collects+shares（**4 字段总互动**）。
- kol_analysis.py L61 SQL：inter = likes+comments+collects+shares（同 4 字段）。
- kos_attribution.py L40 Python：total_likes/total_comments。
→ "总赞"与"总互动"是两个不同 Metric，命名相近易混；kos_metrics 与 kol_analysis 的 4 字段公式一致，应收敛为同一 Canonical Function。

## 3. 产品层 / 端点 / 可视化 Inventory
- **27 个产品页**：overview/monitor/topics/events/notes/negative/cases/case-analysis/brands/brand-hub/brand-dashboard/brand-report/kos/event-graph/knowledge-base/reports/calendar/podcast/swire/official/resident-health/internal-browser/settings/analysis/alerts/app-evidence/evidence。
- **同数据多端点（需 Reference Scan 判定是否同源，疑似多真相入口）**：
  - 总览统计：`/api/dashboard/all`、`/api/stats`、`/api/brand-stats`、`/api/brand-industry/stats`
  - Evidence：`/api/evidence/stats`、`/api/app_evidence/stats`
  - 事件：`/api/events`、`/api/event-graph/events`、`/api/event-graph/stats`
  - 品牌知识：`/api/brand-knowledge/stats`、`/api/brand-industry/stats`
- **可视化渲染器**：
  - app.js：renderDonut / renderMonitorDonuts（conic-gradient 环）、renderTrend+spark（手写 SVG 折线/迷你线）、renderCategories、renderCalendar。
  - ui_interactions_v5.8.0.js：**renderTrendChart（第二套趋势渲染器）**、renderWebTopics/WeeklyEvents。
  - zbmp-workbench.js：drawGraphCanvas（关系图 canvas）；zachary_3d.js：3D canvas（装饰）；taiji-state.js：renderPipeline；kos_dashboard.js：漏斗/分层条/三表。
  - **前端计算性质判定**：app.js 55 个计算点经逐一查看，count 全部来自后端 stats，前端只做 `n/total*100` 占比、max 归一化、fmt 格式化 —— 属合规 View Model，**未发现前端重算业务计数**；但占比分母口径（total 是否含中性）须在 Metric Registry 登记统一。

## 4. 新旧分类初判（KEEP/MERGE/MIGRATE/LEGACY/ARCHIVE/DELETE）
| 对象 | 初判 | 依据 / 动作 |
|---|---|---|
| notes/events/kos_* 等 64 表与采集主链 | **KEEP** | 生产 Truth，稳定有数据 |
| 族 A 情感计数 15+ 处 | **MERGE** | 抽 1 个 Canonical 纯函数，其余 WRAP 调用，禁止再新写 |
| 族 B high vs high+critical | **MERGE（先定口径）** | Registry 锁唯一枚举语义；当前等价，迁移零数字变化 |
| kos_metrics 与 kol_analysis 的 4 字段互动 | **MERGE** | 同一 FN-ENGAGEMENT；kos_engine total_likes 保留为独立"总赞"Metric |
| app.js renderTrend vs ui_interactions renderTrendChart | **MIGRATE(缓)** | 两套趋势渲染器，P3 可视化 Registry 统一为一个 VIS-TREND 渲染器、数据同源 |
| /api/dashboard/all vs /api/stats 等多端点 | **EVALUATE** | 逐个 Reference Scan 是否同口径，同则保留一个 Canonical、其余薄适配 |
| app.js L165/L171 conic-gradient `#0a84ff` | **MIGRATE(视觉)** | 旧 iOS 装饰蓝残留（他文件已清零，此处漏网），转 Stone token |
| 根目录空库「你的数据库文件名.db」 | **ARCHIVE 候选** | 0 表；须先 Reference Scan 确认无连接串引用再归档，不直接删 |
| .trae-cn(79503行)/archive/staging | **LEGACY/ARCHIVE** | IDE 缓存/历史，不进生产路径，不参与 Function Registry |
| zachary_3d.js 3D canvas | **EVALUATE** | 装饰性可视化，确认无数据承载后按"不为动画而动画"原则评估去留 |

## 5. Function / Metric Registry 第一批 Canonical 提案（待你确认口径后实施）
- **FN-SENTIMENT-COUNT v1**：input=note 集合+维度过滤；output={positive,neutral,negative}；规则=按 sentiment 精确匹配；error=缺失计 unknown 不并入任一；一处实现，族 A 全部 WRAP。
- **FN-RISK-COUNT v1**：output={high,medium,low}；**待拍板：high 是否含 future critical**（建议 high 仅 high；若引入 critical 作为独立更高等级，单独成 Metric，不悄悄并入 high）。
- **MET-NEG-RATIO**＝negative/(positive+neutral+negative)，分母固定三值总和（=total，已验证无空值）。
- **FN-ENGAGEMENT v1**＝likes+comments+collects+shares（笔记与 KOS 统一 4 字段）；FN-LIKES 单独保留仅 likes。
- **FN-KOS-AUTHOR-AGG v1**：作者维度 note_count/engagement/均互动，kos_metrics 与 kol_analysis 共用。
- 每个 Function 落：function_id/version/inputs/outputs/formula/dimensions/time_window/unit/error_policy/tests/evidence/status（按指令第五节字段）。

## 6. Data Quality / Lineage 现状
- 已有可复用资产：data_quality_gate.py（质量分 100/90 规则）、schema_registry.py（表声明分类）、app_evidence/evidence_store（Evidence 链）、collector_quality_log、metric_snapshots(250)。→ P0 Quality Gate / Lineage **不重造，WRAP 既有**。
- 缺口（P0 收尾）：0/NULL/UNKNOWN/STALE/ERROR 五态在各计数处尚未统一显式区分（当前靠 `||0`/`get(...,0)` 兜底，存在"缺失看起来像 0"的风险，正是指令第六节要禁的）；核心 Metric 缺端到端 lineage 指针。

## 7. 本阶段明确未做（遵循"先审计禁止改代码"）
未改任何 .py 生产逻辑、未删任何文件/表/端点、未切换任何实现；仅新增本报告与端点清单。上述 MERGE/MIGRATE 全部进入迁移队列，按"Adapter/Wrapper→Canonical→比对一致→Cutover"渐进，迁移期允许并行比对但不长期双真相，删除前必须过 8 项 Gate。

## 8. 建议推进顺序（接 P0 收尾 → P1）
1. **P0 收尾**：你拍板族 B high/critical 口径 → 建 FN-SENTIMENT-COUNT/FN-RISK-COUNT/FN-ENGAGEMENT 三个 Canonical 纯函数 + 单测（只新增、不改调用方）；多端点 Reference Scan 出同源关系表。
2. **P1**：notes/情感/风险 → KOS → event/topic 顺序把页面接到 Canonical Function，每接一个做 Cross-Surface 一致性比对（UI=表=图=报告=导出）。
3. **P2/P3**：27 页 View Model 收口、VIS-* 渲染器统一（先收趋势双渲染器、清 #0a84ff）。
4. **P4/P5**：报告与导出改消费 Canonical；AI 经 Semantic Layer 只读 Metric/Evidence。

## 9. Evidence 索引
- 规模/表：audit_a 输出；计算点：audit_b；情感口径：audit_c；前端：audit_d；后端口径：audit_e1；页面/端点：audit_e2/audit_f；端点机器清单：P0_api_endpoints_inventory.json；risk/sentiment 真实枚举：DB 实查 2026-09-03。
