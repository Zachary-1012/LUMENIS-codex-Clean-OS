# ZBC Track 3 审计报告：AI & Risk & Evidence & Subject Rules

**审计日期**: 2026-09-06
**审计范围**: AI 网关、风险引擎、主题规则、证据链、AI 治理
**仓库路径**: D:\Taikoo-monitor-new
**Python 环境**: .\.venv\Scripts\python.exe
**总体结果**: **PASS**（6/6 验证项通过）

---

## 一、模块状态总览

| 模块 | 文件 | 审计前状态 | 审计后状态 | 修复内容 |
|------|------|-----------|-----------|---------|
| Provider Registry | provider_registry.py | **BUG**: ollama 硬编码 ACTIVE，无运行时探测 | PASS | 新增 AVAILABLE/BLOCKED 状态 + probe_local_providers() 运行时探测 |
| AI Call Logger | ai_call_logger.py | **GAP**: 缺 task_id/trace_id/input_text/final_decision/timestamp | PASS | 补齐 5 个字段 + 旧表自动迁移 + 输入脱敏 |
| AI Governance | ai_governance.py | **GAP**: get_status 硬编码 zhipu，无 per-provider 成本 | PASS | 新增 get_provider_stats()，zhipu/ark 分别统计 |
| Risk Engine | risk_engine.py (root) | **GAP**: 仅兼容转发，无风险评估逻辑 | PASS | 新增 evaluate_risk()/aggregate_risk()，unknown 保持 unknown |
| Evidence Chain | evidence_chain.py | **GAP**: 缺 task_id/trace_id/evaluation_id/source_id | PASS | 补齐 4 个追踪 ID + 旧表迁移 |
| Subject Rules | subject_rules.py | OK | PASS | 未修改，仅验证（硬约束保护） |
| AI Channel | ai_channel.py | OK | PASS | 未修改，熔断/重试/故障转移正常 |
| AI Analyzer | ai_analyzer.py | OK | PASS | 未修改，本地规则情感/风险分析正常 |
| Intelligence | intelligence.py | OK | PASS | 未修改，zhipu 主通道 + 本地兜底正常 |
| Ark LLM | ark_llm.py | OK (LEGACY) | PASS | 未修改，PROVIDER_ACTIVE 守卫正常 |
| Local AI Client | local_ai_client.py | OK | PASS | 未修改，check_availability 正常 |
| AI API | ai_api.py | OK | PASS | 未修改，治理层集成正常 |

---

## 二、审计发现与修复详情

### 2.1 Provider Registry — 本地 Provider 伪造 ACTIVE（已修复）

**问题**: `provider_registry.py` 中 ollama 状态硬编码为 `ACTIVE`，无论 Ollama 是否实际运行。违反"禁止 ACTIVE 但实际无法调用"红线。

**修复**:
- 新增 `AVAILABLE`（已配置未验证）和 `BLOCKED`（探测失败）状态枚举
- ollama/lmstudio/llama_cpp 默认状态改为 `AVAILABLE`
- 新增 `probe_local_providers()` 函数：运行时探测 `/api/tags`（Ollama）或 `/v1/models`（LM Studio/llama.cpp），有可用模型才升级为 `ACTIVE`，否则标记 `BLOCKED`
- 新增 `is_provider_active()` 严格判断和 `active_providers()` 仅返回 ACTIVE
- zhipu 保持 `ACTIVE`（.env 中 ZHIPU_API_KEY 已验证连通）

**验证证据**:
```
Before probe: {'ollama': 'AVAILABLE', 'lmstudio': 'AVAILABLE', 'llama_cpp': 'AVAILABLE'}
After probe:  {'ollama': 'ACTIVE', 'lmstudio': 'BLOCKED', 'llama_cpp': 'BLOCKED'}
Registry summary: {'ACTIVE': 2, 'BLOCKED': 2, 'LEGACY': 2, 'DISABLED': 3}
no_fake_active: true
```
Ollama 实际在运行（探测到模型列表），正确标记 ACTIVE；LM Studio/llama.cpp 未运行，正确标记 BLOCKED。

---

### 2.2 AI Call Logger — 记录字段不完整（已修复）

**问题**: `ai_call_logger.py` 的 `ai_call_logs` 表缺少任务要求的字段：`task_id`、`trace_id`、`input`（原始输入，仅有 input_hash）、`final_decision`（仅有 final_result）、`timestamp`（仅有 created_at）。

**修复**:
- Schema 新增 5 列：`input_text`、`final_decision`、`task_id`、`trace_id`、`timestamp`
- 新增 `_migrate_schema()`：对已存在表执行 `ALTER TABLE ADD COLUMN`（幂等），新列索引在迁移后创建
- `log_call()` 签名新增对应参数
- `@log_ai_call` 装饰器自动透传 task_id/trace_id，从返回值提取 final_decision
- 新增 `_sanitize_input()`：写入 input_text 前脱敏 API key/token/cookie
- `query_calls()` 支持按 task_id/trace_id 过滤

**验证证据**:
```
Zhipu API 调用后 ai_call_logger record id=23
记录包含: provider=zhipu, model=glm-4.5-air, prompt_version=track3-verification-v1,
          input_text(脱敏), output, confidence=0.95, final_decision=verified_zhipu_connectivity,
          task_id=track3-audit, trace_id=trace-xxxxxxxxxxxx, timestamp, latency_ms, token_usage
```

---

### 2.3 AI Governance — 成本模型未按 Provider 分离（已修复）

**问题**: `ai_governance.py` 的 `get_status()` 硬编码 `provider: "zhipu"`，未按 provider 分别统计成本。任务要求"成本模型分别记录 zhipu 与 ark 两 provider"。

**修复**:
- `record_call()` 新增 `provider_tokens` 字典，按 provider 精确记录 calls/prompt_tokens/completion_tokens/total_tokens/failures
- 新增 `get_provider_stats()`：返回 `{zhipu: {...}, ark: {...}}` 分别统计
- `get_status()` 改为返回 `active_providers` + `primary_provider` + `provider_stats`，不再硬编码
- `call_ai_with_governance()` 新增 `provider` 参数，治理链路完整：额度→脱敏→调用准备→回补→统计→标记

**验证证据**:
```
zhipu calls today: 8, tokens: 800
ark calls today: 4, tokens: 520
quota allowed: True, remaining: 488/500 calls
desensitize/restore roundtrip: PASS (brand/location layer)
PII desensitization: PASS (intelligence.redact_for_cloud layer - 手机号/API key/邮箱)
```

---

### 2.4 Risk Engine — 缺少风险评估与 unknown 保护（已修复）

**问题**: 根目录 `risk_engine.py` 仅为兼容转发层（转发到 daily_report），无实际风险评估函数。任务要求验证 sentiment/risk/engagement/severity/confidence/threshold/aggregation，且"未知必须保持 unknown，不能伪造数据"。

**修复**:
- 新增统一枚举：`RISK_LEVELS = (low, medium, high, critical, unknown)`，`SENTIMENT_LABELS = (positive, neutral, negative, unknown)`
- 新增 `evaluate_risk()`：
  - `_is_unknown()`：None/空字符串/"unknown"/"none"/"null"/"n/a" 均视为 unknown
  - unknown 输入 → unknown 输出，不伪造为 negative/low/0
  - critical 独立于 high，禁止 critical=high
  - `_safe_div()`：0/0 返回 0.0 但标记 `data_available=False`
  - 低置信度（<threshold）时 high/critical 降级为 medium（不覆盖原始 final_risk）
  - 非法枚举值归一化为 unknown
- 新增 `aggregate_risk()`：聚合时 unknown 保持独立计数，平均值仅在有数据的样本上计算，`fabrication_safe=True`

**验证证据**（10 用例 + 1 聚合，全部 PASS）:
```
[PASS] 空值-全部unknown: final_risk=unknown, sentiment=unknown, data_available=False
[PASS] 空字符串-unknown: final_risk=unknown, sentiment=unknown, data_available=False
[PASS] critical独立验证: final_risk=critical (未被合并为 high)
[PASS] 0互动量: engagement=0.0 (0/0 安全处理)
[PASS] 非法risk值→unknown: risk_level=unknown
[PASS] aggregate_risk: total=3, unknown_count=1, fabrication_safe=True
```

---

### 2.5 Evidence Chain — 追踪 ID 不完整（已修复）

**问题**: `evidence_chain.py` 的证据链缺少任务要求的 `task_id`、`trace_id`、`evaluation_id`、`source_id`。仅有 evidence_id/canonical_id/tracking_id。

**修复**:
- `Evidence` dataclass 新增 `source_id`、`task_id`、`trace_id` 字段
- `zbc_evidence` 表新增对应 3 列
- `zbc_lifecycle_tracking` 表新增 `task_id`、`trace_id`、`evaluation_id` 3 列
- 新增 `_migrate_evidence_chain()`：旧表自动 ALTER TABLE 补列
- `EvidenceStore.add_evidence()`、`LifecycleTracker.record_stage()`、`EvidenceChain.capture_and_canonicalize()` 均新增对应参数
- `capture_and_canonicalize()` 返回值包含 task_id/trace_id/evaluation_id/source_id

**验证证据**:
```
evidence_id: ev_499853ad33934669
canonical_id: can_511678e06cca4e05
source_id: xhs_note_8dd67fce
task_id: track3-eval-a0ca21ba
trace_id: trace-b01eb38a5155
evaluation_id: eval-5b4814ef
lifecycle stages: 2 (EVIDENCE → CANONICAL_DATA)
subject_hit: True, sentiment: negative, risk: high
content_hash: 0cc686a8a8686723...
[PASS] evidence_chain full traceability (10/10 checks OK)
```
完整链路：Raw Input → Normalized Data → Rule Result (subject_hit+sentiment) → AI Result (zhipu) → Evidence → Canonical Data → Final Decision

---

### 2.6 Subject Rules — 未修改，仅验证（硬约束保护）

**状态**: PASS（10/10 用例通过）

**验证证据**:
```
[PASS] 广州太古汇正面命中: actual=True (命中主体词:广州太古汇)
[PASS] 太古汇简称命中: actual=True (命中主体词:太古汇)
[PASS] 上海太古汇排除: actual=False (主体排除词一票否决:上海太古汇)
[PASS] 成都远洋太古汇排除: actual=False (主体排除词一票否决:成都太古汇)
[PASS] 北京三里屯排除: actual=False (主体排除词一票否决:三里屯太古汇)
[PASS] 无主体词未命中: actual=False
[PASS] LV太古汇命中: actual=True (命中主体词:太古汇)
[PASS] 排除词优先于命中词: actual=False (上海太古汇一票否决)
[PASS] 空输入: actual=False
[PASS] None输入安全: actual=False
```

`SUBJECT_WORDS`（18 词）、`SUBJECT_EXCLUDE_WORDS`（18 词）、`subject_hit()` 逻辑**完全未修改**，符合硬约束。

---

## 三、AI 运行链收敛验证

### 3.1 Zhipu API 真实调用（glm-4.5-air）

```
Provider: zhipu
Model: glm-4.5-air
Base URL: https://open.bigmodel.cn/api/paas/v4
API Key: 已配置 (8564...tXXW, 脱敏)
Prompt: 请用一句话回答：广州太古汇位于哪个城市？
Response: 广州太古汇位于中国广州市。
HTTP Status: 200
Latency: 562ms
Usage: prompt_tokens=39, completion_tokens=9, total_tokens=48
ai_call_logger record id: 23
Status: SUCCESS
```

### 3.2 Provider 优先级链

`ai_channel.provider_chain()` 返回 `['zhipu', 'ark']`，`route_with_fallback()` 实现：
1. zhipu（主，glm-4.5-air，完整 max_tokens）
2. ark（备，豆包，最小输出 300 tokens 兜底）
3. rule（本地规则最终兜底）

每个 Provider 独立熔断器（`ProviderBreaker`），主通道失败自动切换，全部失败返回 `(None, 'rule')`。

### 3.3 本地 AI 状态

| Provider | 探测前 | 探测后 | 说明 |
|----------|--------|--------|------|
| ollama | AVAILABLE | **ACTIVE** | 实际运行中，探测到模型列表 |
| lmstudio | AVAILABLE | **BLOCKED** | 未运行，/v1/models 连接失败 |
| llama_cpp | AVAILABLE | **BLOCKED** | 未运行，/v1/models 连接失败 |

无伪造 ACTIVE：`no_fake_active: true`

---

## 四、AI 不能替代核心规则验证

链路保持：**Rule → AI辅助 → Evidence → Evaluation → Final Decision**

证据链验证中：
1. **Rule 层**: `subject_hit()` 判定主体相关性，`ai_analyzer.analyze_sentiment()` 本地规则情感分析
2. **AI 辅助层**: zhipu glm-4.5-air 提供 sentiment/risk/summary，标记 `ai_enhanced=True, system_truth=False`
3. **Evidence 层**: 原始内容 SHA256 哈希去重，不可变存储
4. **Evaluation 层**: `evaluation_id` 关联评估
5. **Final Decision**: `rule_primary=True, ai_auxiliary=True`，AI 不覆盖规则判断

`ai_governance.mark_ai_output()` 强制标记所有 AI 输出为 `system_truth=False`，禁止 AI 一句话直接覆盖核心业务判断。

---

## 五、其他模块问题记录（不在修改范围，仅记录）

1. **collector_guard/risk_engine.py**: 真实采集风险评分引擎（0-100 连续分 + 五档），已实现且有 7 用例测试，但当前未被 CollectorGuard 实例化（"已实现、已测、当前未接管"状态）。建议未来旁路验证后接入。不在本 Track 修改范围。
2. **app.py**: 体量巨大（292KB），AI 相关路由已拆分到 ai_api.py，但部分 AI 调用仍直接在 app.py 中。建议后续逐步收敛。不在本 Track 修改范围。
3. **ai_api.py /api/ai/analyze**: 返回模拟数据（`'summary': '这是AI分析的摘要内容'`），未接入真实 AI 调用。建议后续接入 intelligence._chat()。不在本 Track 修改范围。
4. **OSAI / LUMENIS Command**: 未成为 ZBC runtime dependency，符合硬约束。

---

## 六、修改文件清单（仅职责范围内）

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| provider_registry.py | 重写 | AVAILABLE/BLOCKED 状态 + 运行时探测 |
| ai_call_logger.py | 重写 | 补齐 5 字段 + 迁移 + 脱敏 |
| ai_governance.py | 重写 | per-provider 成本统计 + 治理链路完善 |
| risk_engine.py | 重写 | evaluate_risk/aggregate_risk + unknown 保护 |
| evidence_chain.py | 补丁 | 补齐 4 追踪 ID + 迁移（13 处补丁） |

**未修改文件**（硬约束保护）: subject_rules.py、ai_channel.py、ai_analyzer.py、intelligence.py、ark_llm.py、local_ai_client.py、ai_api.py、ai_evaluation.py、ai_filter.py、ai_learning_engine.py、ai_resource_packs.py、evidence_api.py、evidence_store.py、app_evidence.py、canonical_data.py、canonical_metrics.py、evaluation_system.py、evaluation_runner.py、evaluation_recorder.py、evaluation_dimensions.py、case_ai_evaluate.py、case_deep_analysis.py、subject_classifier.py、subject_context.py、context_intelligence.py、collection_intelligence.py

---

## 七、验证结果摘要

| 验证项 | 结果 | 证据 |
|--------|------|------|
| Zhipu API 真实调用 (glm-4.5-air) | **SUCCESS** | HTTP 200, 562ms, 48 tokens, response="广州太古汇位于中国广州市。" |
| subject_hit() 规则验证 | **PASS** | 10/10 用例，排除词一票否决正确 |
| risk_engine unknown 保护 | **PASS** | 10/10 用例 + 聚合，unknown 不伪造，critical 独立 |
| evidence_chain 可追溯 | **PASS** | 10/10 checks，task_id/trace_id/evaluation_id/source_id 完整 |
| ai_governance 额度+统计 | **PASS** | zhipu/ark 分别统计，额度控制正常，双层脱敏 |
| Local AI 运行时探测 | **PASS** | ollama=ACTIVE(真实运行), lmstudio/llama_cpp=BLOCKED, 无伪造 |
| **OVERALL** | **PASS** | 6/6 全部通过 |

---

## 八、API Key 安全确认

- 所有输出、日志、JSON 文件中 API key 均已脱敏（`8564...tXXW` 格式）
- `ai_call_logger._sanitize_input()` 在写入 input_text 前自动脱敏 API key/token/cookie
- `intelligence.redact_for_cloud()` 在发送到云端前脱敏 PII/凭证
- 审计报告中未出现任何明文 API key
- `.env` 文件未被修改，API key 未出现在任何 commit 或输出中

---

*报告生成时间: 2026-09-06 14:40 CST*
*审计执行: Track 3 AI & Risk & Evidence & Subject Rules*
