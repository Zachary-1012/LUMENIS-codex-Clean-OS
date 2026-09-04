# 序境-Core · Data Contract / Quality Gate / Lineage 骨架（V1.0）

> 状态：P0-DESIGN-DONE（2026-09-04；注册与复用，不改生产代码）
> 依据：《Unified Data Intelligence Pipeline V1.0》
> 复用：`data_quality_gate.py`（执行器）+ `config/data-contracts/`（4 契约）+ `schema_registry.py`（Schema 反射）——**不重建**。

---

## 1. Canonical Data Contract（Truth 入口校验）

### 1.1 已有契约（复用，KEEP）
- `config/data-contracts/note.yaml` — 笔记（not_empty/regex/allowed_values/date_format/max_length）
- `config/data-contracts/event.yaml` — 事件
- `config/data-contracts/event_db.yaml` — 事件落库
- `config/data-contracts/topic_snapshot.yaml` — 话题快照

### 1.2 需扩展契约（下一阶段，登记）
- `kos_profile.yaml` — KOS 账号资产（必填 author_id、归属门字段、score 0-100 范围、tier 枚举）
- `topic_campaign_note.yaml` — Campaign 笔记（subject_hit 必填、publish_datetime 格式）
- `web_topic.yaml` — Web 话题（mention_count 非负、relevance 0-100）
- `marketing_node.yaml` — 营销节点（date 格式、category/region 枚举）
- `metric_snapshot.yaml` — 指标快照（snapshot_at 必填、值非负）

> 扩展遵循既有 note.yaml 结构（contract/name/version/owner/status/rules），由 DataQualityGate 统一执行。

## 2. Data Quality Gate（0 与缺失显式区分）

数据进入业务计算前必须经过：Schema Validation / Type / Required / Nullability / Range / Uniqueness / Referential Integrity / Freshness / Completeness / Business Rule。

**五值语义（强制，禁止伪装 0）**：
| 语义 | 含义 | 处理 |
|---|---|---|
| 0 | 真实零值 | 正常参与计算 |
| NULL / UNKNOWN | 缺失/未知 | 不参与聚合，调用方判空 |
| NOT_AVAILABLE | 明确不可得 | 显式标记，禁止回退 0 |
| STALE | 过期 | 触发 Freshness 告警/重采 |
| ERROR | 采集/计算失败 | 隔离 QUARANTINE，不进入 Canonical 计算 |

执行器：`data_quality_gate.py::DataQualityGate.validate(contract_name, record)`（已实现）。

## 3. Data Lineage（可追溯真相链）

目标链路：
```
Source → Collector → Raw → Parser → Canonical Data → Function → Metric → Table → View → Visualization → Report / AI
```

落地载体（复用现有）：
- **Evidence**：`app_evidence.py` / `evidence_store.py` / `evidence_api.py` / `app_evidence_records` 表（41 条已有）
- **指标快照**：`metric_snapshots` 表（entity_type/entity_key/raw_json/snapshot_at）— 指标历史 Truth
- **采集日志**：`collection_logs` / `collection_counters` / `collector_quality_log` — Source→Raw 轨迹
- **Schema**：`schema_registry.py` — 表结构反射
- **KOS 归属证据**：`ownership_evidence_ids` 字段（kos_profiles）— 归属可追溯

**Lineage 反向追溯示例**：
```
MET-RISK-01(日报风险指数)
  ← FUNC-RISK-01 daily_report.calculate_risk_index
  ← notes + events 表（Canonical Data）
  ← Raw JSON（data/*.json / collector）
  ← XHS/Web Collector（Source/Run）
  ← Evidence（app_evidence_records / 采集日志）
```

## 4. Visualization 只消费 Canonical Dataset

- 前端（app.js/kos_dashboard 等）**不重算业务指标**，只 render 后端 API 返回值（已符合，审计确认 §2.3）。
- 可视化类型注册（下一阶段，P3）：VIS-TREND / VIS-RANKING / VIS-DISTRIBUTION / VIS-TIMELINE / VIS-HEATMAP / VIS-NETWORK / VIS-FUNNEL / VIS-CORRELATION / VIS-COMPARISON（VIS-GEO 仅作结构示意，不渲染地图）。
- 筛选状态（时间/品牌/业态/KOS/事件/Campaign）由 View Model / Query 状态驱动，动态更新不重算。

## 5. AI / Agent 接入边界

- AI 只能通过 Semantic Layer → Metric → Canonical Dataset → Evidence 获取业务数据。
- AI 可：查询/解释/比较/异常发现/分析/建议。
- AI 禁止：改 Production Truth、改 Canonical Metric、绕过 Quality/Permission/Contract/Test/Audit、直接上线新算法。
- 研究/模型只作输入，须经 Research→Evidence→Evaluation→Contract→Implementation Spec→Production→Test→Evidence→Audit→Release。

## 6. 分阶段迁移路径（渐进，不重写）

```
Existing → Adapter/Wrapper → Canonical Function → Canonical Metric → Canonical Table → New View → Validation → Cutover
```

阶段与优先级：
- P0（本次审计后）：Inventory ✓、Reference/Dependency Scan（登记）、Function Registry ✓、Metric Registry ✓、Data Contract 复用 ✓、Quality Gate 复用 ✓、Lineage 骨架 ✓
- P1：Content/Brand/KOS/KOL/KOC/UGC/Event/Risk/Campaign 接入 Canonical
- P2：Dashboard/UI/Table 统一消费 Canonical
- P3：Visualization Registry + 动态可视化
- P4：Reports + Export 统一
- P5：AI Semantic Access
- P6：全产品一致性 + Cross-Surface Consistency Test + Lineage + Regression + Audit

迁移期允许新旧路径并行比对结果，但禁止长期双真相（双真相清单见 INVENTORY_AUDIT §2.2）。

## 7. 一致性测试（Cross-Surface）

同一 Metric + 相同参数（时间/维度/过滤/权限），校验：
UI = Table = Chart = Report = Export = AI。
出现差异 → 定位 Function/Metric/Dataset/View Model/Filter/Time Window/Permission/Cache/Version；**禁止修改展示层数字对齐**。

## 8. 可观测性（Pipeline 必须可见）

新增字段约定：`last_success_at` / `last_attempt_at` / `row_count` / `freshness` / `quality_status` / `error_count`（复用现有表结构，滚动补齐）。
