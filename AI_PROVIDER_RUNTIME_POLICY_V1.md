# AI Provider Runtime Policy V1

Status: Frozen execution policy

## Objective
Keep only AI providers/models that have an evidenced runtime path; remove dead implementations and stale configuration while preserving a clean provider interface.

## Provider states
- ACTIVE: implementation + configuration path + real health/integration evidence.
- INTERFACE_ONLY: reusable adapter/interface intentionally retained, but no active credential/configuration.
- DISABLED: known unusable and excluded from runtime selection; remove implementation when dependency tracing proves it is dead.
- REMOVE: dead/duplicate/obsolete implementation with no required contract, test, CI, compliance or evidence dependency.

## Credential rule
Never commit API keys, tokens, cookies or secrets. Runtime secrets are environment/secret-manager values only. Empty/missing credentials must fail explicitly and use a documented fallback; never silently report success.

## Current confirmed signal
ZBC has a real ARK/Volcengine adapter history. Commit `35213832a1b74977cc3ddee023c75dc157b72afd` removed a hard-coded ARK API key and requires the key from `.env`, with explicit empty-key failure/degradation. Therefore ARK implementation remains subject to runtime health verification; the credential itself is never stored in Git.

## Execution
For every provider: locate adapter → locate config/env → locate callers → locate model/endpoint → inspect tests/CI → runtime health check → classify → clean unused implementation → regression test → evidence → commit.

Do not classify a provider as ACTIVE merely because code or an environment variable exists.

## Boundary
Provider cleanup must not alter ZBC business Truth, Subject filtering, risk thresholds, reporting semantics, permissions, or the Zachary↔ZBC repository contract.

## Required evidence
ACTIVE requires timestamped health/integration evidence with provider/model identifier, endpoint class, result, failure reason if any, and no secret values.

## 2026-09-04 豆包最小输出硬边界（追加证据）
用户指令：智谱最大算力、豆包最小输出。
现状核验：
- AI_PROVIDER=zhipu（智谱主力，glm_4_5_air 资源包 1191万 tokens 已启用，日限 20万）。
- 豆包(ARK)唯一调用点 ai_learning_engine（/api/web-sentiment/search，手动触发）此前不受 AI_PROVIDER 主开关约束，仅受 MAX_DAILY_TOKEN=190000 上限。
加固内容：
1. ark_llm.py 增加 PROVIDER_ACTIVE 守卫：AI_PROVIDER ∈ {ark,doubao,volc,doubao-ark} 才允许 call_ark_api，否则 raise ark_channel_disabled。
2. ai_learning_engine.__init__ 增加 AI_PROVIDER 门控：zhipu 主力模式下 ai_available=False（豆包通道禁用）。
3. .env 固化 ARK_MAX_DAILY_TOKEN=190000（防默认值漂移）。
验证：AI_PROVIDER=zhipu → PROVIDER_ACTIVE=False / ai_available=False ✅；AI_PROVIDER=ark → PROVIDER_ACTIVE=True ✅；py_compile OK；相关测试 71 pass（唯一 FAIL test_sentiment_analysis 为既有 tests/data/monitor.db 缺失，与本次无关）。
证据：ark_llm.py / ai_learning_engine.py / .env（无密钥提交）。
