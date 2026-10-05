# AI Provider 额度切换规则 V1.0 — 历史证据

> **版本**: V1.0
> **定版日期**: 2026-09-07
> **状态**: SUPERSEDED / HISTORICAL ONLY
> **原适用范围**: Z-Brand Core / CorTech-TaikooHui 旧 AI 调用链路
> **关联 Commit**: `20da4c5` (lumenis-dual-domain-v3)
> **关联文件**: `ai_channel.py`, `intelligence.py`, `provider_registry.py`, `ai_call_logger.py`, `ai_governance.py`, `ai_resource_packs.py`

> **Current rule:** this document cannot enable or select a provider. The sole
> current execution rule is `AGENTS.md` plus the SYSTEM AI Gateway owner:
> Ollama, LM Studio, llama.cpp, Zhipu, Ark and other external-provider paths
> remain compatibility/history only and may not be called, probed, discovered,
> selected or used as fallback. Product AI proceeds only through the approved
> LUMENIS-owned foundation-weight route, which returns explicit unavailable
> states until its training/inference gates have real evidence.

---

## 1. 背景与目标

### 1.1 问题基线（修复前）

| 问题 | 修复前状态 | 影响 |
|------|-----------|------|
| 失败率偏高 | 今日 30 次调用 16 次"失败"（53.3%） | 误报，实际为 rule 兜底被记为失败 |
| token_usage 为 0 | 58 次调用中 52 次 token_usage=0 | 无法统计真实成本，额度控制失效 |
| ark/doubao 状态 | LEGACY（即使 API Key 已配置） | 无法作为 fallback 被自动切换 |
| rule 兜底记录 | provider=rule, success=0, model=glm-4.5-air | 污染失败率统计，model 字段错误 |
| 默认资源包 | per_call（20次/天） | 额度过小，频繁触发 budget_blocked |

### 1.2 修复目标

1. 智谱额度用完或限流时，自动切换到可用备用 Provider，不阻塞生产链路
2. 每次 AI 调用正确记录 token 用量（prompt_tokens / completion_tokens / total_tokens）
3. rule 本地确定性规则兜底标记为正常降级（success=1），不计算在 AI 失败率内
4. Provider 状态基于 .env 实际配置动态判定（有 Key=ACTIVE_FALLBACK，无 Key=NOT_CONFIGURED）
5. 所有切换可追溯（时间/从哪到哪/原因/task_id/trace_id）

---

## 2. Provider 层级定义（6层架构）

### 2.1 层级表

| 层级 | Provider | 角色 | 模型 | 当前状态 | 切换条件 |
|------|----------|------|------|---------|---------|
| **L1** | zhipu | 云端主力 | glm-4.5-air（日常）/ glm-5.3（强推理）/ glm-4.6v（视觉）/ web-search-pro（联网） | ACTIVE | 默认入口 |
| **L2** | ark（豆包） | 云端兜底 | doubao-lite-4k / doubao-pro-32k | ACTIVE_FALLBACK | L1 限流/熔断/额度耗尽 |
| **L3** | qwen（千问） | 云端备用 | qwen-flash / qwen-turbo | NOT_CONFIGURED（无 Key） | L1+L2 均不可用；配置 DASHSCOPE_API_KEY 后激活 |
| **L4** | ollama | 本地主力 | qwen2.5-coder:7b-agent | AVAILABLE（运行时探测） | 云端全部不可用；本地自动发现 |
| **L5** | lmstudio / llama.cpp | 本地备用 | local-model | AVAILABLE | L4 不可用时自动探测 |
| **L6** | rule（本地确定性规则） | 最终兜底 | deterministic_rule | RULE_FALLBACK | L1-L5 全部不可用；始终可用 |

### 2.2 实际运行链路

`_chat()` 主链路使用 `ai_channel.provider_chain()` 返回：

```python
['zhipu', 'ark', 'ollama']  # → 全部失败后返回 (None, 'rule')
```

- **云端部分**: zhipu L1 → ark L2（通过 `route_with_fallback()` 逐 Provider 尝试，独立熔断）
- **本地部分**: ollama L4（`_provider_config()` 自动探测，本地模型路径独立处理）
- **最终兜底**: rule L6（所有 Provider 失败/熔断后返回）
- **L3 qwen / L5 lmstudio**: 框架已支持（`build_fallback_chain_v1()` / `route_with_fallback_v1()`），需配置 Key 或启动本地服务后纳入主链路

---

## 3. 自动切换触发规则

### 3.1 同 Provider 内切换（智谱模型间）

| 触发条件 | 切换目标 | 实现位置 |
|---------|---------|---------|
| glm-5.3 rate_limit / HTTP 429 / 额度耗尽 | glm-4.5-air | `ai_resource_packs.check_quota()` + 调用方 model 参数 |
| glm-5.3 连续 3 次失败 | glm-4.5-air | 熔断器 `CircuitBreaker(fail_threshold=3)` |
| glm-4.5-air 也限流 | 切 L2 ark | `route_with_fallback()` 跨 Provider 切换 |
| glm-4.6v 视觉不可用 | glm-5.3 文本描述 | `vision_chat()` 调用方降级 |
| web-search-pro 联网不可用 | glm-5.3 无联网标记 unverified | `search_enhance()` 调用方降级 |

### 3.2 跨 Provider 切换

| 触发条件 | 切换目标 | 实现机制 |
|---------|---------|---------|
| 智谱每日调用 ≥ 500 或 token ≥ 200000 | L2 ark | `ai_governance.check_quota()` 返回 `quota_exceeded=True, fallback_suggestion='ark'` |
| 智谱熔断器 OPEN | L2 ark | `route_with_fallback()` 跳过熔断中的 Provider |
| ark 也超限/熔断 | L3 qwen（需配置 Key） | `route_with_fallback()` 链式尝试 |
| 云端全部不可用 | L4 ollama | `_provider_config()` 本地自动探测 |
| ollama 不可用 | L5 lmstudio / llama.cpp | `_detect_local()` 按优先级探测 |
| L1-L5 全部不可用 | L6 rule | `_chat()` 返回 `(None, 'rule')` |

### 3.3 熔断器参数

| 参数 | 值 | 说明 |
|------|-----|------|
| fail_threshold | 3 | 连续 3 次失败触发 OPEN |
| cooldown_sec | 20 | OPEN 状态持续 20 秒后 HALF_OPEN 探测 |
| max_attempts | 3 | 单次请求最大重试次数（含首次） |
| max_backoff | 4.0s | 指数退避封顶 |
| hard_max_attempts | 5 | 硬上限，即使配置错误也不超过 |

---

## 4. 恢复机制

| 机制 | 触发条件 | 行为 |
|------|---------|------|
| 熔断器 HALF_OPEN 探测 | cooldown 20 秒到期 | 允许 1 次探测请求；成功→CLOSED，失败→重新 OPEN |
| 次日 0 点额度重置 | 自然日切换 | `AIUsageTracker` 按日统计，新的一天额度自动清零，L1 智谱恢复 |
| 人工切换 | 管理端操作 | 立即生效，记录 audit 日志 |
| 心跳保活 | 60s 间隔（`start_24h_heartbeat`） | 多 Provider 独立探活，自动恢复可用 Provider |

---

## 5. 必须执行的 7 条规则

### 规则 1：所有 AI 调用必须经过额度检查 + 熔断器

```
调用方 → ai_governance.check_quota() → ai_channel.route_with_fallback() → ProviderBreaker.allow()
```

- 额度检查：`AIUsageTracker.check_quota()`（500次/天，200000 token/天）
- 熔断器：每个 Provider 独立 `ProviderBreaker`（CLOSED→OPEN→HALF_OPEN）
- 资源包配额：`ai_resource_packs.check_quota()`（glm_4_5_air: 1191万tokens，per_call: 100次/天）

### 规则 2：切换必须记录完整审计信息

每次 Provider 切换记录以下字段（`ai_channel.record_provider_switch()`）：

| 字段 | 说明 |
|------|------|
| timestamp | 切换时间 |
| from_provider | 原 Provider |
| to_provider | 目标 Provider |
| reason | 切换原因（rate_limit/circuit_open/quota_exceeded/...） |
| task_id | 任务 ID |
| trace_id | 追踪 ID |
| first_result | 切换后首次调用结果 |

切换记录同时写入 `ai_call_logs` 表（model='provider_switch'）。

### 规则 3：成本按 Provider 分别记录

- `AIUsageTracker` 按 Provider 分别统计：`provider_tokens[zhipu]` / `provider_tokens[ark]` / `provider_tokens[ollama]`
- `ai_call_logs.token_usage` 记录每次调用的 total_tokens
- `ai_resource_packs` 按资源包（glm_4_5_air / glm_5_3 / glm_4_6v / per_call）分别统计
- **禁止合并不同 Provider 的成本**

### 规则 4：任务类型选模型

| 任务类型 | 模型 | 说明 |
|---------|------|------|
| 日常/轻量 | glm-4.5-air | 默认，低成本高并发 |
| 深度推理 | glm-5.3 | 复杂分析、报告生成 |
| 视觉理解 | glm-4.6v | 图片输入 |
| 联网搜索 | web-search-pro | 真实联网检索 |
| 代码生成 | glm-5.3 | 代码任务 |

调用方通过 `chat(model=...)` 或 `pack_id=` 指定模型和资源包。

### 规则 5：禁止 AI 不可用阻塞核心生产链路

- 所有 AI 调用必须有 fallback：`AI 失败 → rule 本地规则 → 空值/默认值`
- `_chat()` 永远不抛异常到业务层（最外层 try/except 返回 `(None, 'rule')`）
- `ai_call_logger.log_call()` 旁路写入，失败不阻断主链路
- 业务函数（`review_note` / `summarize_event` / `analyze_sentiment` 等）均有 rule 回退

### 规则 6：禁止静默切换不记录

- 每次跨 Provider 切换必须调用 `record_provider_switch()`
- `route_with_fallback_v1()` 自动记录切换到 `_FAILOVER_LOG` 和 `ai_call_logs`
- 切换日志可通过 `ai_channel.get_failover_log()` 查询

### 规则 7：禁止本地规则输出伪装 AI 输出

- L6 rule 兜底输出必须明确标记：
  - `provider='rule'`
  - `model='deterministic_rule'`
  - `success=1`（规则正常执行，不是 AI 失败）
  - `token_usage=0`
  - `failure_reason=''`
- 业务层通过 `provider == 'rule'` 可识别规则输出，不得将其标记为 `ai_enhanced=True`
- `ai_governance.mark_ai_output()` 仅用于真实 AI 输出

---

## 6. token_usage 记录机制（修复 token=0 bug）

### 6.1 修复前

`intelligence.chat()` 中 `token_usage=0` 硬编码，`_chat()` 不返回 usage 信息。

### 6.2 修复后

```
_chat() 调用 API → 解析 response.usage → _set_call_meta(provider, model, prompt_tokens, completion_tokens, total_tokens)
chat() 调用 _chat() → _get_call_meta() → meta['token_usage'] = total_tokens → log_call(token_usage=total_tokens)
```

- 云端 Provider：解析 OpenAI 兼容格式 `response.usage.{prompt_tokens,completion_tokens,total_tokens}`
- 本地 Ollama：解析 `response.prompt_eval_count` / `response.eval_count`
- total_tokens 缺失时自动计算：`prompt_tokens + completion_tokens`
- rule 兜底：token_usage=0

### 6.3 验证结果

| 调用 | provider | model | latency | token_usage |
|------|----------|-------|---------|-------------|
| 测试1 | zhipu | glm-4.5-air | 468ms | 23 (21+2) |
| 测试2 | zhipu | glm-4.5-air | 673ms | 40 |
| 测试3 | zhipu | glm-5.3 | 3164ms | 234 |
| 测试4 | zhipu | glm-4.5-air | 382ms | 28 |

---

## 7. Provider 状态判定（基于 .env 实际配置）

### 7.1 状态枚举

| 状态 | 含义 |
|------|------|
| ACTIVE | 主力 Provider，已验证可用 |
| ACTIVE_FALLBACK | 备用 Provider，API Key 已配置，可作为 fallback |
| AVAILABLE | 已配置但未运行时验证（本地 Provider 默认态） |
| BLOCKED | 运行时探测失败，不可调用 |
| NOT_CONFIGURED | 未配置 API Key，不可用 |
| LEGACY | 遗留代码，保留但不主动使用 |
| DISABLED | 已禁用 |
| RULE_FALLBACK | 本地确定性规则，始终可用 |

### 7.2 当前状态（2026-09-07）

| Provider | 状态 | 依据 |
|----------|------|------|
| zhipu | ACTIVE | ZHIPU_API_KEY 已配置，连接验证 200 |
| ark | ACTIVE_FALLBACK | ARK_API_KEY 已配置 |
| doubao | ACTIVE_FALLBACK | ark 别名，共用 ARK_API_KEY |
| qwen | NOT_CONFIGURED | DASHSCOPE_API_KEY 未配置 |
| ollama | AVAILABLE | 本地自动探测（运行时验证后 ACTIVE） |
| lmstudio | AVAILABLE | 本地自动探测 |
| llama_cpp | AVAILABLE | 本地自动探测 |
| openai | DISABLED | 未启用 |
| deepseek | NOT_CONFIGURED | 未配置 |
| rule | RULE_FALLBACK | 始终可用 |

---

## 8. 资源包配额配置

| 资源包 | 总量 | 预留学习 | 说明 |
|--------|------|---------|------|
| glm_4_5_air | 11,910,000 tokens | - | 日常主力模型，默认 pack_id |
| glm_5_3 | 按智谱账户 | - | 强推理模型 |
| glm_4_6v | 6,000,000 tokens | - | 视觉模型 |
| per_call | 100 次/天 | 5 次 | 按次计费调用（V1.0 从 20 调大到 100） |

`intelligence.chat()` 默认 `pack_id='glm_4_5_air'`（V1.0 从 'per_call' 改为 'glm_4_5_air'）。

---

## 9. 数据库表结构

### ai_call_logs 关键字段

| 字段 | 类型 | 说明 |
|------|------|------|
| provider | TEXT | zhipu / ark / ollama / rule |
| model | TEXT | glm-4.5-air / glm-5.3 / deterministic_rule / provider_switch |
| success | INTEGER | 1=成功（含 rule 兜底），0=真实 AI 调用失败 |
| failure_reason | TEXT | 成功时为空；失败时为错误原因 |
| token_usage | INTEGER | 本次调用 total_tokens（rule=0） |
| latency_ms | INTEGER | 调用耗时 |
| task_id / trace_id | TEXT | 任务追踪 |
| timestamp | TEXT | ISO 格式时间 |

### 失败率统计口径

```
真实 AI 失败率 = success=0 的记录数 / (总记录数 - provider='rule' 的记录数)
```

rule 兜底记录（provider='rule', success=1）**不计算在 AI 失败率内**。

---

## 10. 与其他模块的接口契约

### 10.1 ai_task_engine.py（B Shard）

- 调用 `intelligence.chat()` / `_chat()`，接口不变
- 返回 `(output, provider, meta)`，meta 含 `token_usage`
- provider='rule' 时应识别为规则输出，不标记 ai_enhanced

### 10.2 ai_browser_runtime.py（C Shard）

- 调用 `intelligence.chat()` 做内容理解
- fallback 链确保浏览器 AI 调用不阻塞采集主链路

### 10.3 内容制作（H Shard）

- 调用 AI 生成内容时走 `intelligence.chat()`
- 智谱限流时自动切 ark，不阻塞内容生成

### 10.4 ai_governance.py

- `check_quota()` 返回 `quota_exceeded` + `fallback_suggestion`
- 超限时不直接拒绝，由调用方决定是否触发 fallback
- `call_ai_with_governance()` 返回 `should_failover=True, fallback='ark'`

---

## 11. 已知限制与后续演进

### 11.1 当前限制

1. **L3 qwen 未激活**：需配置 `DASHSCOPE_API_KEY` 后纳入主链路
2. **L5 lmstudio/llama.cpp**：框架支持但主链路未纳入，需本地服务运行
3. **同 Provider 内模型自动切换**：glm-5.3→glm-4.5-air 的自动切换由调用方/资源包控制，`_chat()` 层面未做模型级 fallback
4. **历史数据**：修复前的 rule 兜底记录仍标记为 success=0，不做回溯修改
5. **provider_registry.py 重复定义**：`ACTIVE_FALLBACK` 在第 23 行和第 30 行重复定义（无害，Python 后赋值覆盖）

### 11.2 后续演进（P1/P2）

- [ ] L3 qwen 配置 Key 后纳入 `provider_chain()` 主链路
- [ ] 同 Provider 内模型级自动 fallback（glm-5.3 失败自动切 glm-4.5-air）
- [ ] `_chat()` 统一云端+本地调用路径，完整 6 层链式 fallback
- [ ] Provider 切换告警（钉钉/飞书 webhook 通知）
- [ ] 成本看板：按 Provider/模型/日维度的 token 消耗趋势图

---

## 12. 验收清单

- [x] provider_chain 返回 ['zhipu', 'ark', 'ollama']，最终 fallback 到 rule
- [x] ark/doubao 状态为 ACTIVE_FALLBACK（API Key 已配置）
- [x] qwen 状态为 NOT_CONFIGURED（无 Key）
- [x] token_usage 正确记录（真实调用 23-934 tokens，不再为 0）
- [x] rule 兜底记录为 success=1, model='deterministic_rule', token_usage=0
- [x] rule 兜底不计算在 AI 失败率内
- [x] 熔断器独立 per-Provider，cooldown 20s
- [x] 切换记录完整（时间/从哪到哪/原因/task_id/trace_id）
- [x] 成本按 Provider 分别记录
- [x] AI 不可用不阻塞生产链路（所有调用有 fallback）
- [x] 默认 pack_id='glm_4_5_air'（1191万 tokens）
- [x] per_call 配额调大到 100 次/天
- [x] 8201 重启验证通过

---

## 13. 变更记录

| 日期 | 版本 | 变更 | 关联 Commit |
|------|------|------|------------|
| 2026-09-07 | V1.0 | 初版定版：6层 Provider 架构 + token 修复 + rule 兜底标记 + ark 升级 ACTIVE_FALLBACK | `20da4c5` |

---

*本文档基于实际代码实现编写，未实现的功能标记为"后续演进"。*
