# AI Provider 审计报告 — ZBC Phase 7

> **审计日期**: 2026-09-06
> **分支**: feat/zbc-full-upgrade-v1
> **审计范围**: 全部 AI Provider、AI 调用链、AI 模块状态、AI 与核心规则边界
> **审计原则**: 先审计、再修改；AI 是辅助层，不得替代核心确定性规则

---

## 1. AI Provider 状态总表

| Provider | 状态 | 调用链 | 凭证配置 | 健康检查 | 业务使用 |
|---|---|---|---|---|---|
| **智谱 GLM (zhipu)** | **ACTIVE** — 云端主力 | `intelligence._chat()` → `_call_cloud('zhipu')` → `ai_channel.post_with_retry()` → `ZHIPU_BASE_URL/chat/completions` | `ZHIPU_API_KEY` (.env，已配置) | `ai_channel.channel_health()` + `CircuitBreaker` + 24h 心跳 + `ProviderBreaker` 独立熔断 | 全量：chat/analyze_sentiment/generate_summary/extract_keywords/review_note/summarize_event/vision_chat/search_enhance/generate_report/ai_filter 二次审核 |
| **火山 ARK / 豆包 (ark)** | **LEGACY** — 已停用 | `ark_llm.call_ark_api()` → `ARK_BASE_URL/chat/completions` | `ARK_API_KEY` (.env，**空**) | 无独立健康检查；`ark_llm.get_api_status()` 仅读 token 统计 | 残余：`ai_learning_engine.WebSentimentSearch`（受 `AI_PROVIDER` 开关约束，zhipu 模式下禁用）、`v4_upgrade/importer/analyzer.py`（非主链路）、`app.py` 仅 try-import 标记可用性 |
| **本地 Ollama** | **ACTIVE_FALLBACK** — 本地兜底 | `intelligence._chat()` 本地分支 → `OLLAMA_BASE_URL/api/chat`；`local_ai_client.LocalAIClient` 独立客户端 | 无需凭证（本地） | `intelligence._detect_local()` 探测 `/api/tags`；`local_ai.check_availability()` | `intelligence._chat()` 自动发现本地模型；`/api/local-ai/*` 路由（system_features_api.py） |
| **LM Studio** | **CONFIGURED_NOT_RUNNING** | `intelligence._detect_local()` → `LMSTUDIO_BASE_URL/v1/models` | 无需凭证 | `_detect_local()` 自动探测 | `intelligence._chat()` 本地分支（自动发现，需用户启动 LM Studio Server） |
| **llama.cpp** | **CONFIGURED_NOT_RUNNING** | `intelligence._detect_local()` → `LLAMA_CPP_BASE_URL/v1/models` | 无需凭证 | `_detect_local()` 自动探测 | `intelligence._chat()` 本地分支（自动发现，需用户启动 llama.cpp server） |
| **通义千问 (qwen)** | **CONFIGURED_NOT_ACTIVE** | `intelligence._call_cloud('qwen')`（代码存在） | `DASHSCOPE_API_KEY` (.env，已配置) | 无独立健康检查 | 不在默认 `provider_chain()`（默认 `['zhipu','ark']`）；仅 `AI_PROVIDER=qwen` 或 `ALLOW_CLOUD_AI` auto 模式下可能选中 |
| **OpenAI** | **CONFIGURED_NOT_ACTIVE** | `intelligence._call_cloud('openai')`（代码存在） | `OPENAI_API_KEY` (.env，已配置，含代理) | 无独立健康检查 | 不在默认 provider_chain；需显式配置 |
| **DeepSeek** | **NOT_CONFIGURED** | `intelligence._call_cloud('deepseek')`（代码存在） | `DEEPSEEK_API_KEY` (.env，**空**) | 无 | 无 Key，不可用 |
| **本地规则 (rule/local_rule)** | **RULE_FALLBACK** — 最终兜底 | `ai_analyzer.py` 确定性规则引擎 | 无需 | N/A | 所有 AI 失败/不可用时的最终兜底；情感/风险/话题/分类/摘要全部有规则实现 |

---

## 2. Provider 收敛结论

### 2.1 当前生效架构

```
智谱 GLM (云端主力)
  ├── glm-4.5-air    — 日常文本（默认，关思考）
  ├── glm-5.3        — 强推理（ZHIPU_STRONG_MODEL，HIGH/CRITICAL 任务）
  ├── glm-4.6v       — 视觉（vision_chat）
  └── web-search-pro — 联网搜索（search_enhance）
        │
        ▼ 失败/熔断/无 Key
本地 AI (Ollama / LM Studio / llama.cpp 自动发现)
        │
        ▼ 本地也不可用
本地确定性规则 (ai_analyzer.py + subject_rules.py)
```

### 2.2 收敛动作

| Provider | 动作 | 理由 |
|---|---|---|
| 智谱 GLM | **保留为主力** | 完整调用链、熔断、心跳、预算管理、多模型分层 |
| 火山 ARK/豆包 | **标记 LEGACY，不删除** | 代码仍被 ai_learning_engine 和 v4 importer 引用；`AI_PROVIDER=zhipu` 时自动禁用；路由已迁移到智谱 |
| Ollama | **保留为本地兜底** | intelligence.py 自动探测；local_ai_client.py 独立服务 /api/local-ai/* |
| LM Studio / llama.cpp | **保留自动探测，不主动启用** | 代码已支持，用户启动服务后自动接入 |
| 通义千问 / OpenAI | **保留代码，标记非激活** | 有 Key 但不在默认 provider_chain；可作为未来备用 |
| DeepSeek | **保留代码骨架** | 无 Key，不可用；代码已支持接入 |

### 2.3 关键发现

1. **ark_llm.py 已有 `.bak-providerguard` 备份的说法与实际不符**：审计时未发现 `.bak-providerguard` 文件，ark_llm.py 为当前唯一版本。
2. **`.ollama/` 目录不存在**：Ollama 配置通过 .env 环境变量（`OLLAMA_BASE_URL`, `OLLAMA_MODEL`）管理，无需独立配置目录。
3. **ai_api.py 中 `/api/ark/*` 路由已全部迁移到智谱**：注释明确标注 "云智(ARK)已停用，改用智谱(zhipu)驱动"，provider 字段标记真实来源。
4. **ai_learning_engine.py 的 WebSentimentSearch 仍依赖 ark_llm**：但受 `AI_PROVIDER` 开关约束，当前 zhipu 模式下 `ark_channel_enabled=False`，不会实际调用 ARK。

---

## 3. AI 模块状态标记

所有核心 AI 模块已添加 `MODULE_STATUS` / `AI_ROLE` 常量：

| 模块 | MODULE_STATUS | AI_ROLE | 说明 |
|---|---|---|---|
| `intelligence.py` | ACTIVE_PRIMARY | CENTRAL_GATEWAY | 中央 AI 网关，所有调用经此路由 |
| `ai_channel.py` | ACTIVE | TRANSPORT_LAYER | 重试/熔断/心跳/多 Provider 故障转移 |
| `ai_analyzer.py` | RULES_ENGINE_PRIMARY | AUXILIARY_ONLY | 确定性规则引擎，AI 仅辅助 |
| `ai_filter.py` | ACTIVE | SECONDARY_REVIEW_ONLY | 主体过滤第一道关，AI 仅二次判断 |
| `ai_governance.py` | ACTIVE | GOVERNANCE_LAYER | 脱敏/额度/输出标记，不做业务判断 |
| `ai_resource_packs.py` | ACTIVE | BUDGET_AND_QUOTA | 资源包额度管理 |
| `local_ai_client.py` | ACTIVE_FALLBACK | LOCAL_INFERENCE | Ollama 本地客户端 |
| `ark_llm.py` | LEGACY | — | 已停用，保留兼容 |
| `ai_learning_engine.py` | LEGACY_PARTIAL | AUXILIARY_RESEARCH | 全网舆情检索依赖 ark_llm（受开关约束） |

---

## 4. AI 调用全链路追踪

### 4.1 新增模块：`ai_call_logger.py`

**数据库表**: `ai_call_logs`（CREATE TABLE IF NOT EXISTS，自动建表）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增 ID |
| provider | TEXT | 调用的 Provider |
| model | TEXT | 模型名称 |
| prompt_version | TEXT | Prompt 版本标识 |
| input_hash | TEXT | 输入 SHA-256 哈希（不存原文，保护敏感内容） |
| output | TEXT | AI 输出（截断 4000 字符） |
| confidence | REAL | 置信度 0-1 |
| rule_result | TEXT | 确定性规则结果（对比用） |
| final_result | TEXT | 最终采用结果 |
| human_correction | TEXT | 人工修正内容 |
| latency_ms | INTEGER | 调用延迟（毫秒） |
| token_usage | INTEGER | Token 用量 |
| failure_reason | TEXT | 失败原因 |
| success | INTEGER | 是否成功（1/0） |
| created_at | TEXT | 创建时间 |

**核心 API**:
- `log_call(...)` — 记录单次调用（旁路写入，失败不阻断主链路）
- `@log_ai_call(provider, model, prompt_version, ...)` — 装饰器，自动计时/记录/异常追踪
- `compute_input_hash(*parts)` — 输入哈希计算
- `query_calls(provider, success, limit, offset, since)` — 查询调用日志
- `get_stats(provider, since)` — 调用统计
- `record_human_correction(call_id, correction)` — 人工修正反馈
- `get_provider_status(provider)` — Provider 状态查询

**接入点**: `intelligence.chat()` 已接入旁路调用追踪（try/except 全包，绝不阻断 AI 调用主链路）。

### 4.2 新增模块：`ai_evaluation.py`

**核心指标**:
- `ai_accuracy` — AI 结果与规则结果一致率
- `ai_replacement_rate` — AI 替代规则的比例（仅计 AI 与规则不同且被采用的情况）
- `human_correction_rate` — 人工修正率
- `confidence_distribution` — 低/中/高置信度分布
- `provider_failure_rate` — 按 Provider 统计失败率
- `fallback_rate` — AI 回退到规则的比例
- `latency` — 平均/P50/P95/最大延迟
- `token_cost` — 总/平均 Token 用量

**核心 API**:
- `evaluate_ai_quality(since, provider, limit)` — 完整质量评估
- `record_rule_vs_ai(...)` — 记录规则与 AI 对比
- `submit_human_correction(call_id, correction, corrected_result)` — 人工修正闭环
- `get_correction_feedback(since, limit)` — 获取修正记录（用于规则沉淀）
- `evaluate_provider_health(since)` — Provider 健康评估
- `verify_ai_not_replacing_rules()` — AI 不替代核心规则验证器
- `generate_evaluation_report(since)` — 生成可读评估报告
- `quick_summary()` — 快速摘要（供 API 调用）

---

## 5. AI 不替代核心规则验证

### 5.1 验证结果

```
=== AI 不替代核心规则验证 ===
PASSED: True
Summary: AI 未替代核心规则
  ai_replacement_rate_below_50pct: PASS (value=0.0)
  rule_result_priority: PASS (value=1.0)
  subject_filter_not_ai_replaced: PASS (value=0)
```

### 5.2 验证项说明

| 检查项 | 阈值 | 当前值 | 结果 |
|---|---|---|---|
| AI 替代率 ≤ 50% | ≤ 0.5 | 0.0 | PASS |
| 规则结果优先率 ≥ 50% | ≥ 0.5 | 1.0 | PASS |
| 主体过滤未被 AI 替代 | = 0 | 0 | PASS |

### 5.3 主体过滤边界确认

- `subject_rules.py`: `SUBJECT_WORDS` / `SUBJECT_EXCLUDE_WORDS` / `subject_hit()` — **未修改**
- `ai_analyzer.py`: `verify_taikoo_location()` 调用 `subject_hit()` — 主体验证在 AI 分析之前
- `ai_filter.py`: `ai_secondary_review()` — 规则层（质量/去重/垃圾）先执行，AI 仅做深度二次判断；营销内容被规则层直接拒绝，不调用 AI
- `intelligence.review_note()`: 先检查 `rule_analysis.get('verified')`，未通过主体验证直接返回 rejected，不调用 AI

### 5.4 风险判断边界确认

- `ai_analyzer.assess_risk()` — 确定性规则（关键词/句式/互动量/话题），不依赖 AI
- `risk_engine.py` — 独立风险引擎，AI 不参与核心风险评级
- AI 仅用于：风险原因解释、事件摘要、报告润色（辅助层）

---

## 6. 测试结果

### 6.1 新增测试：`tests/test_ai_evaluation.py`

```
45 passed in 0.95s
```

覆盖 6 大类：
1. **AI 调用追踪**（10 项）：log_call 成功/失败、旁路容错、输入哈希、装饰器成功/失败/自定义提取器、查询过滤、统计、Provider 状态注册表
2. **Evaluation 指标计算**（13 项）：空库、准确率、替代率、修正率、置信度分布、Provider 失败率、回退率、延迟、Token 成本、规则对比记录、JSON/文本匹配、Provider 健康、评估报告
3. **AI 不替代主体过滤**（7 项）：subject_hit 独立验证、模块常量、ai_filter 规则层优先、验证器空库/有数据、主体过滤调用零替代、ark_llm LEGACY 标记
4. **Provider Fallback**（5 项）：默认链、全失败回退 rule、主通道成功不切备用、备用接管、本地路径、云端回退 rule
5. **人工修正反馈**（5 项）：提交修正、带结果修正、查询反馈、修正影响指标、完整闭环
6. **模块状态标记**（2 项）：全部 AI 模块有状态、中央网关策略声明

### 6.2 回归测试：现有 AI 测试

```
51 passed in 0.77s
```

- `test_ai_channel.py` (18)
- `test_ai_channel_flag.py` (10)
- `test_ai_degrade.py` (6)
- `test_ai_channel_multiprovider.py` (10)
- `test_ai_gateway.py` (5)
- `test_ai_budget_cache.py` (2)

**无回归。**

---

## 7. 修改文件清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `ai_call_logger.py` | **新增** | AI 调用全链路追踪（SQLite 持久化 + 装饰器） |
| `ai_evaluation.py` | **新增** | AI 质量评估体系（指标计算 + 规则对比 + 人工修正闭环） |
| `tests/test_ai_evaluation.py` | **新增** | 45 项单元测试 |
| `audit/ai_provider_audit.md` | **新增** | 本审计报告 |
| `scripts/_zbc_phase7_verify.py` | **新增** | 验证脚本（临时，可清理） |
| `intelligence.py` | 修改 | 添加 MODULE_STATUS 标记；chat() 接入旁路调用追踪 |
| `ai_analyzer.py` | 修改 | 添加 MODULE_STATUS / AI_ROLE / SUBJECT_FILTER_BEFORE_AI 标记 |
| `ai_filter.py` | 修改 | 添加 MODULE_STATUS / AI_ROLE / SUBJECT_FILTER_FIRST 标记 |
| `ark_llm.py` | 修改 | 添加 MODULE_STATUS=LEGACY / DEPRECATION_NOTE 标记 |
| `ai_governance.py` | 修改 | 添加 MODULE_STATUS / AI_ROLE 标记 |
| `ai_learning_engine.py` | 修改 | 添加 MODULE_STATUS / AI_ROLE 标记 |
| `ai_resource_packs.py` | 修改 | 添加 MODULE_STATUS / AI_ROLE 标记 |
| `local_ai_client.py` | 修改 | 添加 MODULE_STATUS / AI_ROLE 标记 |
| `ai_channel.py` | 修改 | 添加 MODULE_STATUS / AI_ROLE 标记 |

### 数据库变更

- **新增表**: `ai_call_logs`（CREATE TABLE IF NOT EXISTS，由 ai_call_logger.py 自动创建）
- **新增索引**: `idx_ai_call_provider`, `idx_ai_call_created`, `idx_ai_call_success`
- **不修改任何现有表**，不影响生产数据

---

## 8. 未完成项 / 后续建议

| 项 | 优先级 | 说明 |
|---|---|---|
| 更多 AI 调用点接入 @log_ai_call | P1 | 当前仅 intelligence.chat() 接入旁路日志；ai_filter._ai_deep_review、intelligence.review_note 等可逐步接入装饰器 |
| ai_call_logs 数据接入 Dashboard | P2 | 在系统设置/AI 管理页面展示调用统计和质量指标 |
| 人工修正 UI | P2 | 前端提供人工审核界面，调用 submit_human_correction() |
| 修正结果沉淀为规则 | P2 | 定期分析 get_correction_feedback()，将高频修正转化为确定性规则 |
| ark_llm 完全移除评估 | P3 | 确认 ai_learning_engine 和 v4 importer 不再需要后，可评估移除 |
| 通义千问/OpenAI 清理 | P3 | 确认不使用后可从 provider_chain 和 _call_cloud 中移除 |

---

## 9. 风险与已知限制

1. **ai_call_logs 表在生产库中创建**：使用 CREATE TABLE IF NOT EXISTS，不影响现有表；但生产库 monitor.db 会新增一张表。
2. **旁路日志写入可能在高并发下产生锁竞争**：已使用 threading.Lock 保护写操作；SQLite WAL 模式可进一步优化（当前未启用）。
3. **input_hash 不存原文**：这是安全设计，但意味着无法从日志回溯原始 prompt；如需追溯需配合其他日志。
4. **AI 准确率依赖 rule_result 字段填充**：当前仅 record_rule_vs_ai() 会填充 rule_result；intelligence.chat() 的旁路日志不填 rule_result，因此 ai_accuracy 指标需要业务层主动调用 record_rule_vs_ai() 才有意义。
5. **ark_llm 仍可被 AI_PROVIDER=ark 激活**：虽然标记 LEGACY，但如果用户切换 AI_PROVIDER，ark 通道仍可工作（如果配置了 ARK_API_KEY）。

---

## 10. 结论

- **AI Provider 收敛完成**：智谱 GLM 为主力，Ollama 本地兜底，规则最终兜底；ARK 标记 LEGACY，其他 Provider 标记非激活。
- **AI 调用全链路追踪已建立**：ai_call_logger.py 提供持久化追踪和装饰器，intelligence.chat() 已接入旁路记录。
- **AI Evaluation 体系已建立**：ai_evaluation.py 提供 8 项核心指标、规则对比、人工修正闭环、Provider 健康评估。
- **AI 不替代核心规则已验证**：3 项检查全部 PASS，主体过滤和风险判断由确定性规则主导。
- **测试通过**：新增 45 项 + 现有 51 项 AI 测试全部通过，无回归。
- **无 API Key 写入源码**：所有凭证仅通过 .env / 环境变量注入。
- **未执行 git commit**：按要求仅做代码修改和测试。
