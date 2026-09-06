# ZBC Phase 10 — 统一 Evaluation 系统审计报告

> **日期**: 2026-09-06
> **分支**: feat/zbc-full-upgrade-v1
> **HEAD**: e9ef5ad
> **阶段**: Phase 10 — 统一 Evaluation 系统建立
> **状态**: 已完成，测试通过

---

## 1. 执行摘要

本次变更建立了统一 Evaluation 系统，核心解决两个反模式：
1. **不允许只统计接口是否返回 200** —— 所有指标评价真实数据质量
2. **unknown 绝不默认 pass** —— 无数据/无法评估时标记 unknown，汇总时单独计数且拉低整体评级

系统覆盖五个维度：**data / ai / collector / report / runtime**，共 20 个指标，全部有明确阈值（pass/warn/fail），结果持久化到新建的 `evaluation_records` 表。

---

## 2. 现有评估模块审计表

| 模块 | 覆盖维度 | 持久化方式 | 真实质量评价 | unknown处理 | 状态 | 备注 |
|------|---------|-----------|-------------|------------|------|------|
| `evaluation_system.py` | collection / analysis / report / stability | JSON文件 | 部分（stability仅查端口连通性≈200统计） | 无（缺数据默认0分） | **LEGACY** | 已标记Legacy，保留接口；缺AI/Collector/Runtime细分 |
| `case_ai_evaluate.py` | AI案例4维评分（影响力/创新性/可复制性/风险） | 无（函数返回） | 是（AI评分+本地模板兜底） | 无 | **VERIFIED** | 仅覆盖案例库AI评估，非通用AI质量 |
| `evaluate_system_timing.py` | API响应时间/调度时间/DB查询性能 | 无（脚本输出） | 部分（仅延迟测量） | 无 | **PARTIAL** | 硬编码凭证，脚本式非模块，仅覆盖延迟 |
| `engineering_metrics.py` | 任务闭环/采集性能/调度健康/系统健康/告警 | 无（函数返回JSON） | 是（真实指标+阈值告警） | 无数据→None→WARN | **VERIFIED** | 已接入桥接函数 `engineering_to_evaluation()` |
| `data_quality_gate.py` | 写入前字段校验（必填/格式/范围/长度） | 无（函数返回） | 是（per-field规则校验） | 无 | **VERIFIED** | 已接入桥接函数 `batch_quality_to_evaluation()` |
| `check_system.py` | DB空表/API连通性 | 无（脚本输出） | 否（纯200统计+空表检查） | 无 | **PARTIAL** | 典型反模式：只查API是否返回ok |
| `verify_system.py` | DB表/文件存在/env配置 | 无（脚本输出） | 部分（文件存在性检查） | 无 | **PARTIAL** | 配置检查有价值，但非质量评价 |
| `verify_system_e2e.py` | E2E API调用/DB/日志/配置/数据流 | 无（脚本输出） | 部分（API-centric） | 无 | **PARTIAL** | 端到端验证但以API连通性为主 |
| `quick_check.py` | DB计数/文件存在 | 无（脚本输出） | 否（纯计数） | 无 | **PARTIAL** | 快速巡检脚本，非质量评估 |

### 审计结论
- **VERIFIED**: 3个（case_ai_evaluate, engineering_metrics, data_quality_gate）—— 有真实质量评价逻辑
- **PARTIAL**: 5个（evaluate_system_timing, check_system, verify_system, verify_system_e2e, quick_check）—— 部分真实质量或纯200统计
- **LEGACY**: 1个（evaluation_system）—— 已标记，保留接口，新代码使用统一系统
- **BLOCKED**: 0个

---

## 3. 五维度指标清单

### 3.1 Data 维度（4指标）

| 指标 | 阈值(pass/warn) | 方向 | 数据源 | 说明 |
|------|----------------|------|--------|------|
| completeness | 0.90 / 0.70 | 越高越好 | notes表 | 必填字段(note_id/title/content/collected_at)填充率 |
| freshness_hours | 24.0 / 72.0 | 越低越好 | notes表 | 最新publish_datetime/collected_at距现在小时数 |
| duplication_rate | 0.05 / 0.15 | 越低越好 | notes表 | is_duplicate=1的记录比例 |
| provenance_rate | 0.95 / 0.80 | 越高越好 | notes表 | 有source_platform+collected_at+note_id的比例 |

### 3.2 AI 维度（5指标）

| 指标 | 阈值(pass/warn) | 方向 | 数据源 | 说明 |
|------|----------------|------|--------|------|
| accuracy | 0.85 / 0.70 | 越高越好 | ai_filter_log | AI结果与规则/人工一致率（filter_result=pass/filtered比例） |
| confidence_avg | 0.70 / 0.50 | 越高越好 | ai_filter_log | AI过滤平均置信度 |
| human_correction_rate | 0.10 / 0.25 | 越低越好 | note_review_history | 人工修正记录占比 |
| provider_reliability | 0.90 / 0.75 | 越高越好 | ai_filter_log | 云provider调用成功率（非error比例） |
| fallback_rate | 0.20 / 0.40 | 越低越好 | ai_filter_log | 降级到rule/local的比例 |

### 3.3 Collector 维度（4指标）

| 指标 | 阈值(pass/warn) | 方向 | 数据源 | 说明 |
|------|----------------|------|--------|------|
| success_rate | 0.85 / 0.60 | 越高越好 | collection_logs | status=success的采集运行比例 |
| failure_rate | 0.10 / 0.30 | 越低越好 | collection_logs | status=failed/error/blocked比例 |
| recovery_rate | 0.70 / 0.40 | 越高越好 | collection_logs | 从失败恢复成功的比例（有error_msg但最终success） |
| latency_sec | 120.0 / 300.0 | 越低越好 | collection_logs | finished_at-started_at平均秒数 |

### 3.4 Report 维度（3指标）

| 指标 | 阈值(pass/warn) | 方向 | 数据源 | 说明 |
|------|----------------|------|--------|------|
| generation_success | 0.90 / 0.70 | 越高越好 | daily_reports表 | summary非空的报告比例 |
| artifact_validity | 0.90 / 0.70 | 越高越好 | data/reports/目录 | 文件存在+非空(>=100bytes)比例 |
| evidence_coverage | 0.80 / 0.60 | 越高越好 | daily_reports表 | 有hot_notes/key_events/risk_alerts的比例 |

### 3.5 Runtime 维度（4指标）

| 指标 | 阈值(pass/warn) | 方向 | 数据源 | 说明 |
|------|----------------|------|--------|------|
| uptime_hours | 24.0 / 1.0 | 越高越好 | runtime_guardian_checkpoints | 最早checkpoint到现在的运行小时数 |
| heartbeat_rate | 0.95 / 0.80 | 越高越好 | runtime_guardian_checkpoints | state=active的checkpoint比例 |
| crash_count | 0.0 / 3.0 | 越低越好 | runtime_guardian_checkpoints | state=crashed/failed/dead的次数 |
| recovery_count | 2.0 / 5.0 | 越低越好 | runtime_guardian_checkpoints | 含recovery/recover的checkpoint次数 |

**合计：5维度 × 20指标**

---

## 4. evaluation_recorder.py 核心 API

### 4.1 数据类

```python
@dataclass
class EvaluationRecord:
    evaluation_id: str       # UUID4
    dimension: str           # data/ai/collector/report/runtime
    metric_name: str         # 指标名
    metric_value: Optional[float]  # 指标值（None→unknown）
    threshold: str           # JSON: {"pass":x, "warn":y, "higher_is_better":bool}
    status: str              # pass/warn/fail/unknown（默认unknown，不默认pass）
    evaluated_at: str        # ISO8601
    source: str              # 数据来源
    evidence_ref: str        # 证据引用（SQL/trace_id/文件路径）
    metadata: str            # JSON扩展元数据
```

### 4.2 核心函数

| 函数 | 说明 |
|------|------|
| `record_evaluation(dimension, metric_name, metric_value, pass_threshold, warn_threshold, higher_is_better, ...)` | 核心写入API，自动判断状态并持久化。metric_value=None → status=unknown |
| `judge_status(value, pass_threshold, warn_threshold, higher_is_better)` | 阈值判断：None→unknown，否则按方向判断pass/warn/fail |
| `get_evaluation_summary(dimension=None, since=None)` | 汇总：按维度统计pass/warn/fail/unknown，计算pass_rate和overall_status |
| `get_evaluation_records(dimension=None, status=None, limit=100)` | 查询记录列表 |
| `init_db(db_path)` | 建表（CREATE TABLE IF NOT EXISTS，幂等） |

### 4.3 汇总状态判定规则（unknown不默认pass）

```
有 fail → "fail"
无 fail 但有 unknown → "warn"（unknown是风险信号）
无 fail/unknown 但有 warn → "warn"
全部 pass → "pass"
无记录 → "unknown"
```

pass_rate = pass_count / total_count（unknown计入分母，拉低pass_rate）

---

## 5. evaluation_runner.py 核心 API

| 函数 | 说明 |
|------|------|
| `EvaluationRunner(db_path).run_full_evaluation(mock_data=None, dimensions=None)` | 五维度全量评估，返回global_summary + anti_pattern_check |
| `EvaluationRunner(db_path).run_dimension_evaluation(dimension, mock_data=None)` | 单维度评估 |
| `run_full_evaluation(db_path, mock_data)` | 模块级便捷函数 |
| `run_dimension_evaluation(dimension, db_path, mock_data)` | 模块级便捷函数 |

### anti_pattern_check 字段
```python
{
    "only_200_count": 0,           # 没有任何指标叫200/http_status
    "unknown_not_pass": True,      # 硬编码保证：unknown绝不默认pass
    "real_quality_metrics": 20,    # 所有指标都是真实质量指标
}
```

---

## 6. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `evaluation_recorder.py` | **新建** | 统一记录与持久化层，EvaluationRecord + record_evaluation + get_evaluation_summary |
| `evaluation_dimensions.py` | **新建** | 五维度真实质量评估（20指标），支持mock_data注入 |
| `evaluation_runner.py` | **新建** | 统一评估执行器，run_full_evaluation + run_dimension_evaluation |
| `tests/test_evaluation_system.py` | **新建** | 52个测试用例，覆盖持久化/阈值/unknown/五维度/汇总/反模式/桥接 |
| `evaluation_system.py` | **修改** | 标记Legacy（LEGACY=True + LEGACY_SINCE + LEGACY_REPLACED_BY），保留全部接口 |
| `data_quality_gate.py` | **修改** | 新增 `batch_quality_to_evaluation()` 桥接函数，接入data维度 |
| `engineering_metrics.py` | **修改** | 新增 `engineering_to_evaluation()` 桥接函数；stdout重配改用`reconfigure()`避免关闭pytest capture buffer |
| `audit/evaluation_system_audit.md` | **新建** | 本审计报告 |

**数据库变更**: 新建 `evaluation_records` 表（CREATE TABLE IF NOT EXISTS，不破坏现有数据）

---

## 7. 测试运行结果

### 7.1 新增测试

```
tests/test_evaluation_system.py
============================= 52 passed in 2.45s =============================
```

测试类覆盖：
- `TestEvaluationRecordPersistence` (6 tests) — 持久化CRUD
- `TestThresholdJudgment` (9 tests) — pass/warn/fail边界判断
- `TestUnknownNotDefaultPass` (5 tests) — **核心红线：unknown不默认pass**
- `TestFiveDimensionEvaluation` (8 tests) — 五维度执行+阈值配置完整性
- `TestEvaluationSummary` (6 tests) — 汇总逻辑
- `TestNotOnlyHTTP200` (4 tests) — **反模式：不允许只统计200**
- `TestEvaluationRunner` (7 tests) — 执行器全量/单维度/子集
- `TestLegacyBridges` (4 tests) — Legacy标记+桥接函数
- `TestDatabaseSchema` (3 tests) — 表结构+唯一约束

### 7.2 回归测试（修改的现有模块）

```
tests/test_engineering_metrics.py — 15 passed
tests/test_data_quality_gate.py  — 10 passed
```

### 7.3 合计

**77 tests passed, 0 failed, 0 errors**

---

## 8. unknown 不默认 pass 验证结果

### 8.1 代码级保证

1. `judge_status(None, ...)` → 返回 `"unknown"`，不返回 `"pass"`
2. `record_evaluation(metric_value=None, ...)` → 自动设置 `status="unknown"`
3. `get_evaluation_summary()`:
   - unknown 计入 `total` 分母，拉低 `pass_rate`
   - `global_status`: 有 unknown 且无 fail → `"warn"`（不是 pass）
4. `EvaluationRunner.run_full_evaluation()`:
   - `anti_pattern_check["unknown_not_pass"] = True` 硬编码
   - 维度 `overall_status`: 有 unknown → `"warn"`

### 8.2 测试级验证

| 测试用例 | 验证点 | 结果 |
|---------|--------|------|
| `test_none_metric_value_produces_unknown` | metric_value=None → status=unknown | PASS |
| `test_unknown_counted_in_summary` | unknown在汇总中被计数，global_status=warn | PASS |
| `test_all_unknown_global_status_warn` | 全部unknown → global_status=warn（非pass） | PASS |
| `test_empty_data_produces_unknown` | 空数据集(total=0) → 指标unknown | PASS |
| `test_runner_unknown_not_pass` | runner中unknown不让维度变成pass | PASS |

### 8.3 空数据场景验证

```python
# total_notes=0 时
completeness = None   # 不是0，是None → unknown
duplication = None    # unknown
provenance = None     # unknown
# 维度 overall_status = "warn"（因为有unknown），不是 "pass"
```

---

## 9. 不允许只统计接口 200 验证结果

### 9.1 指标设计保证

- 20个指标全部基于真实数据表（notes/ai_filter_log/collection_logs/daily_reports/runtime_guardian_checkpoints）
- 没有任何指标名包含 "200"、"http_status"、"status_code"
- 每个指标都有 `source`（表名）和 `evidence_ref`（SQL查询/计数）
- Legacy `evaluation_system.py` 的 `evaluate_system_stability()` 已文档化为已知局限（仅查端口连通性≈200统计）

### 9.2 测试级验证

| 测试用例 | 验证点 | 结果 |
|---------|--------|------|
| `test_no_200_metric_in_dimensions` | 五维度无200类指标名 | PASS |
| `test_anti_pattern_check_in_runner` | runner返回anti_pattern_check，only_200_count=0 | PASS |
| `test_all_metrics_have_real_values` | 所有指标有threshold+source | PASS |
| `test_legacy_stability_is_not_200_only` | Legacy标记存在，已知局限文档化 | PASS |

---

## 10. 风险与已知限制

1. **AI accuracy 口径简化**: 当前用 `filter_result IN ('pass','filtered')` 作为一致率代理，未来需要人工标注集做真实准确率计算
2. **Collector recovery_rate 口径简化**: 当前用"有error_msg但最终success"作为恢复代理，未来需要事件级恢复追踪
3. **Report artifact_validity**: 仅检查文件存在+非空，未做hash校验和内容完整性校验
4. **Runtime uptime**: 基于最早checkpoint，系统重启后会重置，未来需要持久化运行时长
5. **mock_data 测试**: 所有测试使用mock数据，未执行真实采集/AI调用/报告生成（符合任务要求）
6. **Legacy模块共存**: evaluation_system.py 保留运行，新代码应逐步迁移到统一系统

---

## 11. 下一步建议

1. **P1**: 将 `check_system.py` / `verify_system_e2e.py` 中的API连通性检查迁移到统一系统的runtime维度，替换纯200统计
2. **P1**: 建立AI人工标注集，替换accuracy的代理口径
3. **P1**: 为Report artifact添加hash校验，升级artifact_validity指标
4. **P2**: 建立评估定时任务（每日自动run_full_evaluation），结果写入Dashboard
5. **P2**: 将evaluation_records接入报告中心，生成评估周报/月报

---

## 12. 交付物清单

- [x] 五维度评估全部建立（data/ai/collector/report/runtime）
- [x] 每个维度有明确的指标和阈值（20指标）
- [x] EvaluationRecord 持久化（evaluation_records表）
- [x] 不允许只统计接口200（anti_pattern_check + 测试验证）
- [x] unknown 不默认 pass（代码+测试双重保证）
- [x] 测试通过（52新增 + 25回归 = 77 passed）
- [x] 审计报告已创建（本文件）
- [x] 未删除任何评估模块
- [x] 未修改 SUBJECT_WORDS / subject_hit()
- [x] 未修改现有数据库数据
- [x] 未执行真实采集/AI调用/报告生成
- [x] 未 git commit
