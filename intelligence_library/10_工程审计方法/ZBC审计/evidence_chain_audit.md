# ZBC Phase 8 — Evidence / Canonical Data 数据链审计报告

> **审计日期**: 2026-09-06
> **分支**: feat/zbc-full-upgrade-v1
> **审计范围**: 证据存储、规范数据、数据质量、数据边界、数据反馈闭环、ORM模型、数据库操作
> **核心目标**: 统一数据生命周期 External Source → Evidence → Canonical Data → ... → Learning Asset，原始证据不可被分析结果覆盖，Evidence 有完整 provenance

---

## 1. 现有证据模块审计表

| 模块 | 文件 | 状态 | hash | provenance | timestamp | source | subject_scope | AI/人工分离 | rule_version | 主要发现 |
|------|------|------|------|------------|-----------|--------|---------------|-------------|--------------|----------|
| 证据存储 | `evidence_store.py` | **PARTIAL** | ✅ SHA256(16字符截断) | ✅ source/project/feature/account | ✅ captured_at/created_at/updated_at | ✅ | ❌ 无 | ❌ 无 | ❌ 无 | hash基于元数据而非原始内容；无content_hash；无subject_scope；无去重强制执行 |
| 应用证据 | `app_evidence.py` | **PARTIAL** | ✅ MD5(文件) | ✅ source/capture_mode/topic | ✅ captured_at/created_at/updated_at | ✅ | ❌ 无 | ✅ verified_by/verified_at/status | ❌ 无 | 使用MD5(弱于SHA256)；仅文件哈希无内容哈希；无publish_datetime；Shadow模式不进生产 |
| 规范指标 | `canonical_metrics.py` | **VERIFIED** | N/A | N/A | N/A | N/A | N/A | N/A | ✅ CANONICAL_FUNCTIONS版本注册表 | 纯函数零I/O；sentiment/risk/engagement口径锁定；critical独立桶不并入high；分母0返回None不伪装0 |
| 数据质量门 | `data_quality_gate.py` | **VERIFIED** | N/A | N/A | N/A | N/A | N/A | N/A | ✅ contract version | 契约驱动写入前校验；10种规则类型；enrich_quality_record软门；unique批内去重 |
| 数据边界 | `data_boundary.py` | **VERIFIED** | N/A | ✅ 4区分类(CODE/BRAND_DATA/CREDENTIAL/RUNTIME) | N/A | N/A | N/A | N/A | N/A | sanitize_text凭证脱敏；assert_no_tracked_credentials；DB分区识别 |
| 数据反馈闭环 | `data_feedback_loop.py` | **PARTIAL** | N/A | ❌ 无evidence关联 | ✅ timestamp | ✅ | ❌ 无 | ❌ 无 | ❌ 无 | 5类异常检测(负面突增/品牌投诉/数据缺失/情绪失衡/高重复率)；无rule_version追踪；无证据链关联 |
| ORM模型 | `models.py` | **PARTIAL** | N/A | ✅ Note/Event/Comment等27个模型 | ✅ | ✅ | ❌ Note无content_hash | ❌ 无Evidence/CanonicalData模型 | ❌ 无 | Note模型70+字段但无content_hash；无Evidence或CanonicalData ORM模型；subject_type/content_type已分离 |
| 数据库操作 | `database.py` | **VERIFIED** | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 无证据相关操作(0处匹配)；不存在覆盖原始证据的风险 |
| 证据API | `evidence_api.py` | **VERIFIED** | N/A | ✅ 只读查询 | N/A | ✅ | N/A | N/A | N/A | 只读REST接口；无删除/修改；证据不可篡改只能追加 |

### 状态定义
- **VERIFIED**: 功能完整，符合证据链要求
- **PARTIAL**: 部分符合，存在缺失字段或能力，需逐步接入
- **BLOCKED**: 存在阻断性问题，需优先修复（本次审计无BLOCKED）

---

## 2. 现有 canonical_data 表审计

### 2.1 表结构
- **表名**: `canonical_data`
- **行数**: 13行（非空）
- **字段数**: 45列
- **主键**: `canonical_id` (TEXT)

### 2.2 数据来源分析
全部13行均为**测试数据**（data_quality_gate测试夹具），来源特征：
- `source_id` 格式: `qgate_ok_001`, `qgate_warn_001`, `qgate_explicit_001` 等
- `provenance` 格式: `notes:qgate_xxx`
- `raw_ref`: `{"table": "notes", "note_id": "qgate_xxx", "id": N}`
- `created_at`: 2026-09-06 04:59:57（批量生成）
- `source_platform`: 全部为 `xhs`
- `source_table`: 全部为 `notes`

### 2.3 质量评估

| 检查项 | 状态 | 说明 |
|--------|------|------|
| content_hash | ✅ 有 | 16字符截断哈希（与evidence_store一致），非完整SHA256 |
| provenance | ✅ 有 | `notes:note_id` 格式 |
| evidence_id 关联 | ❌ 无 | `evidence_ref` 字段存在但全部为空字符串 |
| hash 去重 | ⚠️ 部分 | 有content_hash字段但无UNIQUE约束，未强制执行去重 |
| 主体过滤 | ⚠️ 未验证 | `subject_id` 全部为空，`scope` 全部为 `default` |
| rule_version | ⚠️ 有但简单 | `version` 字段全部为 `1.0.0`，非语义化规则版本 |
| AI/人工分离 | ❌ 无 | `ai_provider`/`ai_model` 存在但无独立ai_analysis/human_correction JSON字段 |
| publish_datetime | ⚠️ 部分 | 部分行有值(2026-08-31)，部分为空 |
| 真实生产数据 | ❌ 无 | 全部为测试夹具数据，非真实采集数据 |

### 2.4 结论
现有 `canonical_data` 表为**测试阶段产物**，结构上已具备部分证据链要素（content_hash/provenance/version），但缺少：
- evidence_id 外键关联
- 完整SHA256哈希
- AI分析与人工修正分离存储
- 语义化rule_version追踪
- 主体过滤验证

**处理策略**: 不修改、不删除现有13行测试数据；新建独立表 `zbc_canonical_data` 承载Phase 8规范数据，逐步迁移。

---

## 3. 新建 evidence_chain.py 核心API

### 3.1 数据类

#### Evidence（原始证据，不可变）
```python
@dataclass
class Evidence:
    evidence_id: str              # ev_ + 16字符hex
    source_type: str              # xhs_note / xhs_comment / weibo / web_mention ...
    source_url: str
    raw_content: str              # 原始内容，写入后不可修改
    content_hash: str             # SHA256完整哈希(64字符)
    captured_at: str              # 系统采集时间
    publish_datetime: Optional[str]  # 内容真实发布时间
    subject_scope: str            # 主体范围(CTH=广州太古汇)
    collection_metadata: Dict     # 采集元数据JSON
    provider: str                 # 采集提供者/适配器
    authenticity_score: float     # 真实性评分0-1
    created_at: str
```

**不可变字段**（写入后禁止UPDATE）:
`evidence_id, source_type, source_url, raw_content, content_hash, captured_at, publish_datetime, subject_scope, collection_metadata, provider, authenticity_score, created_at`

#### CanonicalData（规范数据，AI/人工分离）
```python
@dataclass
class CanonicalData:
    canonical_id: str             # can_ + 16字符hex
    evidence_id: str              # FK → Evidence.evidence_id
    normalized_content: str
    subject_hit: bool
    subject_keywords: List[str]
    sentiment: str                # positive/neutral/negative/unknown
    risk_level: str               # low/medium/high/critical
    engagement_metrics: Dict      # likes/comments/collects/shares
    rule_version: str             # 规则版本，创建后不变
    ai_analysis: Dict             # AI原始输出（独立，不被人工覆盖）
    human_correction: Dict        # 人工最终判断（独立，不覆盖AI）
    created_at: str
    updated_at: str
```

### 3.2 核心类

| 类 | 职责 | 关键方法 |
|----|------|----------|
| `EvidenceStore` | 原始证据存储（不可变） | `add_evidence()` (hash去重), `get_evidence()`, `get_by_hash()`, `list_evidence()`, `verify_immutability()` |
| `CanonicalDataStore` | 规范数据存储（AI/人工分离） | `create_canonical()`, `apply_human_correction()` (只改human_correction), `update_ai_analysis()` (只改ai_analysis+历史), `list_by_rule_version()` |
| `LifecycleTracker` | 数据生命周期追踪 | `record_stage()`, `trace_data_lineage(evidence_id)`, `get_stage_definition()`, `list_all_stages()` |
| `EvidenceChain` | 统一门面 | `capture_and_canonicalize()` (端到端), `trace_lineage()`, `get_stats()` |

### 3.3 独立数据库表
新建3张独立表，不修改现有生产表：
- `zbc_evidence` — 原始证据（12字段+3索引）
- `zbc_canonical_data` — 规范数据（14字段+4索引，FK关联zbc_evidence）
- `zbc_lifecycle_tracking` — 生命周期追踪（12字段+3索引）

---

## 4. 数据生命周期阶段定义

13个阶段，每阶段有明确输入/输出/转换规则：

| 阶段 | 顺序 | 输入 | 输出 | 转换规则 | 不可变 |
|------|------|------|------|----------|--------|
| EXTERNAL_SOURCE | 0 | 平台原始内容 | 未处理原始文本+元数据 | 仅读取不修改 | ✅ |
| EVIDENCE | 1 | EXTERNAL_SOURCE输出 | Evidence记录(含hash/provenance) | SHA256 hash + provenance采集 + hash去重 | ✅ |
| CANONICAL_DATA | 2 | Evidence记录 | CanonicalData(规范化+主体过滤+质量门) | 规范化 + subject_filter + sentiment/risk + engagement + rule_version标记 + AI/人工分离 | ❌ |
| EVENT | 3 | CanonicalData集合 | Event(事件聚合) | 事件聚类 + 生命周期标记 + mention/source统计 | ❌ |
| CASE | 4 | Event + 人工判断 | Case(案例/工单) | 事件升级 + 负责人分配 + 状态跟踪 | ❌ |
| FINDING | 5 | Case分析结果 | Finding(发现/结论) | 根因分析 + 事实确认 + 影响评估 | ❌ |
| INSIGHT | 6 | Finding + 历史数据 | Insight(洞察) | 趋势识别 + 模式提炼 + 跨事件关联 | ❌ |
| DECISION | 7 | Insight + 业务目标 | Decision(决策) | 策略选择 + 优先级排序 + 资源分配 | ❌ |
| ACTION | 8 | Decision | Action(执行动作) | 任务分解 + 执行跟踪 + 责任人 | ❌ |
| OUTCOME | 9 | Action执行结果 | Outcome(结果) | 效果度量 + KPI对比 + 成功/失败判定 | ✅ |
| EVALUATION | 10 | Outcome + 预期目标 | Evaluation(评估) | ROI分析 + 经验总结 + 差距识别 | ❌ |
| FEEDBACK | 11 | Evaluation | Feedback(反馈) | 规则优化建议 + 采集策略调整 + 词表更新 | ❌ |
| LEARNING_ASSET | 12 | Feedback + 历史案例 | Learning Asset(学习资产) | 样本沉淀 + 规则更新 + 模型微调数据 + 知识库 | ✅ |

### trace_data_lineage(evidence_id) 返回结构
```python
{
    "evidence_id": "...",
    "evidence": {...},                    # 原始证据完整记录
    "canonical_data": [...],              # 关联的规范数据列表
    "lifecycle_stages": [...],            # 按stage_order排序的阶段记录
    "stage_summary": {"EVIDENCE": 1, ...},
    "rule_versions": ["v1.0.0", ...],
    "total_stages_recorded": N,
}
```

---

## 5. 修改文件列表

| 文件 | 操作 | 变更说明 | 破坏性 |
|------|------|----------|--------|
| `evidence_chain.py` | **新建** | Evidence/CanonicalData数据类 + EvidenceStore/CanonicalDataStore/LifecycleTracker/EvidenceChain + 13阶段生命周期定义 + hash去重 + AI/人工分离 + rule_version追踪 | 无（独立新文件） |
| `tests/test_evidence_chain.py` | **新建** | 44个单元测试，覆盖hash去重/不可变性/AI分离/生命周期/rule_version/历史数据保护/端到端 | 无（独立新文件） |
| `evidence_store.py` | **修改** | 新增 `compute_full_content_hash()` (完整SHA256) + `migrate_evidence_chain_fields()` (ADD COLUMN迁移) + `EVIDENCE_CHAIN_NEW_COLUMNS` + `_get_table_columns()` (向后兼容列过滤) + record_evidence新增6个可选参数 | **无**（新参数全部可选有默认值；INSERT自动过滤不存在的列；迁移函数需显式调用） |
| `audit/evidence_chain_audit.md` | **新建** | 本审计报告 | 无 |

### 未修改文件（确认无需修改）
- `canonical_metrics.py` — VERIFIED，指标定义完整
- `data_quality_gate.py` — VERIFIED
- `data_boundary.py` — VERIFIED
- `data_feedback_loop.py` — PARTIAL但无需本次修改（后续Phase逐步接入evidence_id关联）
- `models.py` — PARTIAL但无需本次修改（新evidence_chain.py自包含数据类）
- `database.py` — VERIFIED，无证据相关操作
- `app_evidence.py` — PARTIAL但保持Shadow模式不变
- `evidence_api.py` — VERIFIED，只读接口

---

## 6. 测试运行结果

```
============================= test session starts =============================
platform win32 -- Python 3.13.15, pytest-9.1.1
collected 52 items

tests/test_evidence_store.py ........                                    [ 15%]
tests/test_evidence_chain.py ........................................... [ 98%]
.                                                                        [100%]

============================= 52 passed in 1.48s ==============================
```

### 测试覆盖明细（44个新增测试）

| 测试类 | 测试数 | 覆盖内容 |
|--------|--------|----------|
| TestEvidenceHash | 9 | SHA256计算/相同内容同哈希/不同内容异哈希/空内容/None处理/去重(同内容不重复入库)/不同内容正常入库/ID格式 |
| TestEvidenceImmutability | 5 | 不可变字段集合定义/verify_immutability验证/不存在处理/创建Canonical后raw_content不变/无update方法 |
| TestAISeparation | 5 | 独立字段存在/人工修正不覆盖AI/AI更新不影响人工/AI分析历史保留(_history) |
| TestLifecycleTracking | 9 | 13阶段存在/顺序连续/每阶段有IO定义/EVIDENCE&OUTCOME不可变/记录有效阶段/无效阶段抛异常/trace_data_lineage完整/不存在追踪/阶段定义查询 |
| TestRuleVersion | 6 | 默认版本定义/Canonical记录rule_version/按版本筛选/人工修正不改版本/AI更新不改版本 |
| TestHistoricalDataProtection | 3 | 新旧版本数据互不影响/Evidence raw_content永远不变/created_at不被后续更新修改 |
| TestProvenance | 3 | 完整provenance字段/to_dict可JSON序列化/evidence_id FK关联 |
| TestEndToEnd | 3 | capture_and_canonicalize全流程/重复内容返回已有Evidence/get_stats |
| TestBackwardCompatibility | 2 | adapt_evidence_store_hash/build_provenance_metadata |

---

## 7. 原始证据不可覆盖验证结果

### 7.1 设计层验证
- ✅ `EvidenceStore.IMMUTABLE_FIELDS` 定义了12个不可变字段
- ✅ `EvidenceStore` 不提供 `update_evidence()` / `modify_evidence()` 方法
- ✅ `Evidence` 数据类写入后只能通过重新读取验证，无修改入口
- ✅ `zbc_evidence` 表设计为追加-only（append-only），无UPDATE代码路径

### 7.2 运行时验证（测试通过）
- ✅ `test_raw_content_preserved_after_canonical_creation`: 创建CanonicalData后，原始Evidence的raw_content和content_hash不变
- ✅ `test_evidence_raw_content_never_changes`: 连续5次读取，raw_content和content_hash始终一致
- ✅ `test_evidence_no_update_method`: EvidenceStore不存在update方法
- ✅ `test_evidence_verify_immutability`: verify_immutability返回有效验证报告

### 7.3 AI输出与人工判断分离验证
- ✅ `test_apply_human_correction_preserves_ai`: 人工修正后，ai_analysis["sentiment"]仍为原始"negative"，human_correction["sentiment"]为"neutral"
- ✅ `test_update_ai_analysis_preserves_human`: AI更新后，human_correction保持不变
- ✅ `test_ai_analysis_history_preserved`: 多次AI更新保留历史版本在_history中

### 7.4 历史数据不被静默改写验证
- ✅ `test_old_rule_version_data_preserved_after_new_version`: v1.0.0数据在v2.0.0数据创建后保持不变
- ✅ `test_human_correction_does_not_change_rule_version`: 人工修正不改rule_version
- ✅ `test_ai_update_does_not_change_rule_version`: AI更新不改rule_version
- ✅ `test_canonical_created_at_unchanged_by_updates`: created_at不被后续更新修改

---

## 8. 数据库变更说明

### 8.1 生产数据库状态
- **生产库 `data/monitor.db` 未被修改**
- `app_evidence_records` 表仍为16列，0行数据
- `canonical_data` 表仍为45列，13行测试数据
- 所有现有表结构和数据完整保留

### 8.2 新增表（evidence_chain.py init_db时创建）
| 表名 | 字段数 | 索引数 | 说明 |
|------|--------|--------|------|
| `zbc_evidence` | 12 | 3 | 原始证据（content_hash/source_type/subject_scope索引） |
| `zbc_canonical_data` | 14 | 4 | 规范数据（evidence_id/rule_version/sentiment/risk_level索引） |
| `zbc_lifecycle_tracking` | 12 | 3 | 生命周期追踪（evidence_id/canonical_id/stage索引） |

### 8.3 可选迁移（需显式调用，未自动执行）
`evidence_store.migrate_evidence_chain_fields()` 可对现有 `app_evidence_records` 表执行 ADD COLUMN 迁移：
- 新增6列: `content_hash`, `subject_scope`, `collection_metadata`, `provider`, `authenticity_score`, `publish_datetime`
- 全部可空/有默认值，非破坏性
- 已在生产库副本上验证通过（16列→22列，数据零损失）
- **未在生产库上执行**，需用户确认后手动调用

---

## 9. 风险与已知限制

| 风险/限制 | 级别 | 说明 | 缓解措施 |
|-----------|------|------|----------|
| 现有canonical_data 13行测试数据无evidence_id关联 | 中 | 历史测试数据无法追溯到Evidence | 不修改现有数据；新数据使用zbc_canonical_data表，逐步迁移 |
| evidence_store的evidence_hash为16字符截断 | 低 | 碰撞概率略高于完整SHA256 | 新增compute_full_content_hash()提供64字符完整哈希；新表zbc_evidence使用完整哈希 |
| app_evidence.py使用MD5 | 低 | MD5安全性弱于SHA256 | 保持Shadow模式不变；不进入生产主链路 |
| data_feedback_loop无evidence_id关联 | 低 | 反馈闭环无法追溯到具体证据 | 后续Phase逐步接入；本次不修改 |
| 新表zbc_*与现有canonical_data并存 | 低 | 存在两套规范数据表 | 新表为Phase 8标准，旧表保留兼容；后续统一迁移 |
| 迁移函数未在生产库执行 | 信息 | app_evidence_records尚未添加新字段 | 需用户确认后调用migrate_evidence_chain_fields()；record_evidence已做向后兼容（自动跳过不存在的列） |

---

## 10. 下一步建议

1. **P1**: 在用户确认后执行 `migrate_evidence_chain_fields()` 为生产库 `app_evidence_records` 添加6个新字段
2. **P1**: 采集主链路接入 `EvidenceChain.capture_and_canonicalize()`，替代直接写notes表的路径
3. **P2**: 现有 `canonical_data` 表13行测试数据迁移到 `zbc_canonical_data`（补充evidence_id）
4. **P2**: `data_feedback_loop.py` 接入evidence_id关联，实现反馈→证据的追溯
5. **P2**: Event/Case/Finding/Insight等下游阶段接入 `LifecycleTracker.record_stage()`
6. **P3**: 统一 `evidence_store` 的16字符截断哈希为完整SHA256（需数据迁移）
7. **P3**: `app_evidence.py` MD5升级为SHA256（Shadow模式，低优先级）

---

## 11. 验收标准对照

| 验收标准 | 状态 | 验证方式 |
|----------|------|----------|
| Evidence有完整provenance（hash/timestamp/source/subject_scope/collection_metadata） | ✅ 通过 | Evidence数据类12字段 + TestProvenance测试 |
| 原始证据不可被分析结果覆盖 | ✅ 通过 | IMMUTABLE_FIELDS + 无update方法 + 5个不可变性测试 |
| AI输出与人工最终判断分离 | ✅ 通过 | 独立ai_analysis/human_correction字段 + apply_human_correction只改人工 + 5个AI分离测试 |
| historical data不被新规则静默改写 | ✅ 通过 | rule_version创建后不变 + 人工修正/AI更新不改版本 + 6个版本追踪+3个历史保护测试 |
| 测试通过 | ✅ 通过 | 52 passed (8 existing + 44 new) |
| 审计报告已创建 | ✅ 通过 | 本文件 |

---

*报告生成时间: 2026-09-06*
*审计工具: evidence_chain.py v1.0.0 + pytest 9.1.1*
*生产数据库: 未修改*
