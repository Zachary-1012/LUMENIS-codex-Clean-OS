# P0-B-2 AI 网关 intelligence._chat 深度代码审查（glm-5.3）

> 日期：2026-09-03 | 模型：glm-5.3 | 消耗：per_call 1次
> 目的：审查 AI Provider 路由/思考模型/脱敏/错误处理边界

---

Let me carefully analyze the code provided.

Key facts from the prompt:
- Production system, AI is enhancement layer only (never rewrites business facts)
- Production default Ollama-only, cloud needs explicit enable
- glm-5.3 is an "always thinking" model (passing any thinking param → 400, content may be empty requiring reasoning_content fallback)
- Current logic: `if not model.startswith('glm-5.3'): payload['thinking']={'type':'disabled'}`

Let me go through each review point.

**1. Routing correctness (_provider_config)**

- `requested=_env('AI_PROVIDER','auto').lower()` — lowercases, good for case handling.
- `if requested in ('ollama','lmstudio','llama_cpp')` — sets LOCAL_AI_PREFERRED and _detect_local().
- `elif requested in ('qwen','openai','deepseek','ark','doubao','zhipu','glm')` — configs dict built for all keys. Note: `'glm'` maps to zhipu config via `configs[requested]` — wait, `'glm'` is in the tuple, but `configs` dict only has keys 'qwen','zhipu','openai','deepseek','ark','doubao' — there is NO 'glm' key in `configs`! So `configs[requested]` with requested='glm' will raise KeyError!

Let me check: configs = {'qwen':..., 'zhipu':..., 'openai':..., 'deepseek':..., 'ark':..., 'doubao':...}. The elif includes 'glm' in the membership test, but `key,base,model=configs[requested]` — if requested=='glm', KeyError('glm') → exception. This would propagate up — is _provider_config called inside try? No, it's called at top of _chat: `d=_provider_config()` before the try block. So a KeyError would propagate and crash _chat entirely (not even returning 'rule'). That's a bug.

Actually wait — let me re-read: `provider_name = 'zhipu' if requested == 'glm' else (...)`. So they intended glm→zhipu, but they access `configs[requested]` BEFORE computing provider_name, and 'glm' isn't in configs. So AI_PROVIDER=glm → KeyError → _chat crashes (no 'rule' fallback since the call is outside try). Definitely a bug. Fix: add 'glm' key to configs or map requested='zhipu' before lookup.

- `doubao` and `ark` both map to ark config with same env; provider_name = 'ark' for both. Fine, but note in _chat, api_key_map has 'ark' but not 'doubao' — however since _provider_config maps doubao→ark, provider is 'ark' by the time _chat uses it, so api_key_map lookup works. OK.

- Case handling: `.lower()` applied to AI_PROVIDER. But model names are NOT lowercased anywhere. The thinking check `if not str(model).startswith('glm-5.3')` — case sensitivity: 'GLM-5.3' would not match, and thinking={'type':'disabled'} would be sent → 400 error. Zhipu model names are lowercase typically, but env-configurable via ZHIPU_MODEL — user could set 'GLM-5.3'. Risk: model names are case-sensitive on provider side too, so 'GLM-5.3' likely wouldn't be a valid model anyway. But defensive fix: `.lower()` the model before startswith.

- Model defaults: zhipu default 'glm-4.5-air' — for that model, thinking param is passed as disabled. Is that correct for glm-4.5 series? Zhipu glm-4.5/4.6 support thinking param ('enabled'/'disabled'). The code comment says GLM thinking models default to reasoning_content which crowds out final output; disabling is fine. Not verifiable beyond code; but per given spec only glm-5.3 is always-thinking. OK.

- Future glm-5.4: per the current logic, glm-5.4 would get thinking disabled. If glm-5.4 is also always-thinking (unknown), 400. The startswith('glm-5.3') is a version allowlist that breaks on new versions. Better: maintain a set of always-thinking models, or try/except retry without thinking on 400, or read model capability list. Suggest: use a set/regex like `ALWAYS_THINKING_MODELS = {'glm-5.3', ...}` or better, an env var, plus a 400-retry fallback that strips thinking and retries.

- Variants: 'glm-5.3-flash' startswith('glm-5.3') → True → thinking not sent. Correct per spec ("glm-5.3 is always thinking model... glm-5.3-flash"). Wait, the user asks: "显式传 glm-5.3-flash / glm-5.3 变体 / 大小写 / 未来 glm-5.4 时会不会误传 thinking 或漏处理?" So:
  - glm-5.3-flash: startswith matches → thinking NOT passed → correct (assuming flash variant also always-thinking).
  - But wait — does startswith also accidentally match hypothetical 'glm-5.30'? or 'glm-5.3x'? Yes, 'glm-5.30' startswith 'glm-5.3' → treated as always-thinking → thinking not passed. If glm-5.30 doesn't exist, moot; but a version-prefix match could over-match. E.g., 'glm-5.3-air' hypothetical. Minor.
  - Case: 'GLM-5.3' → not matched → thinking passed → 400. Bug (defensive).
  - glm-5.4: not matched → thinking passed. If it's also always-thinking → 400. Unknown but fragile.

- Also: what if provider is zhipu but model passed explicitly to _chat is a different zhipu model via `model=` param — fine, same check.

- Another routing issue: `_provider_config` returns None if key missing for cloud → _chat returns None,'rule'. Good.

- Cache: `_CACHE['ts']` 30s. But if _CACHE['provider'] is None and within 30s... The code: `if now-_CACHE['ts']<30: detected=(...) if _CACHE['provider'] else None`. So if provider detection failed before, within 30s returns None without retry. OK. But there's a subtle issue: for `auto` mode with cloud fallback, detection result is cached including... fine.

- Also potential issue: in _chat, `provider,model_default,base=d`; `model = model or model_default`. If caller passes model='' (empty string) — falsy → default. OK. If caller passes model='glm-5.3' while provider resolved as ollama — the thinking logic only applies to zhipu path; the payload for ollama path doesn't include thinking anyway. But note: if provider is zhipu and model explicitly passed as non-glm (e.g., 'glm-4.5'), thinking disabled is sent — consistent.

- One more: in _chat cloud path, `payload_obj` was built earlier; for zhipu they add thinking and re-serialize payload. But if provider=='zhipu', the earlier `payload=json.dumps(payload_obj,...)` happens first (line: `payload=json.dumps(payload_obj,ensure_ascii=False).encode('utf-8')` before try). Then inside try, for zhipu they mutate payload_obj and re-serialize. Fine. But note: for non-zhipu cloud providers, no thinking param — good (thinking is zhipu-specific). But wait — qwen (dashscope) and deepseek also have reasoning models (qwen3 thinking, deepseek-reasoner). deepseek-reasoner returns reasoning_content; code handles reasoning_content fallback generically. OK.

- ark default model 'doubao-seed-evolving-latest-version' — hmm, that looks like a placeholder-ish name; ark models are usually endpoint IDs like 'ep-...' or 'doubao-...'. Can't verify; note as suspicious default but per instruction only judge based on code. Actually 'doubao-seed-1-6-flash' etc. Not verifiable — skip or note mild.

- Base URL for zhipu: 'https://open.bigmodel.cn/api/paas/v4' — and code appends '/chat/completions'. Zhipu v4 chat completions path is '/api/paas/v4/chat/completions'. Correct. Note comment in _chat says "base已包含/v1或/v3" but zhipu base ends with /v4 — comment inaccurate but harmless (says /v1 or /v3, zhipu is v4; the code just rstrip('/') and appends path, so fine). Minor doc inconsistency.

**2. Thinking model handling**

Covered above. Summary:
- glm-5.3-flash and variants: startswith → correct skip.
- Case 'GLM-5.3' → not matched → thinking sent → 400 → falls to 'rule'. Bug.
- glm-5.4 future: not matched → thinking sent; if always-thinking → 400 → silent degradation to rule (no retry). Fragile design: should catch 400 and retry without thinking.
- Over-match: 'glm-5.3-something-new' also skipped (treated as always-thinking) — if a future non-thinking variant named glm-5.3-x exists, thinking would never be disabled, causing reasoning to crowd output — but the reasoning_content fallback mitigates empty content.
- Also: the reasoning_content fallback: `_content = (_msg.get('content') or '').strip() or (_msg.get('reasoning_content') or '').strip()` — this falls back for ANY provider with empty content, good. But note: for glm-5.3, reasoning_content is the chain-of-thought — returning CoT as the "final JSON" result may not be valid JSON. The comment says "思考结果在 reasoning_content" — so for glm-5.3, the actual answer may be in reasoning_content? Hmm, the user states: "glm-5.3 是'始终思考'模型（传任何 thinking 参数都 400，content 可能为空需回退 reasoning_content）". So per spec, fallback to reasoning_content is the intended behavior. But caution: reasoning_content is raw thought; if it contains "<think>..." tags or prose, downstream JSON parsing may fail. Also, `_msg.get('content') or ''` — if content is None. OK.

Also subtle: `.strip()` on content — fine.

Another issue: when thinking is disabled for zhipu non-5.3 models, some zhipu API versions expect `thinking: {"type": "disabled"}` — that matches. Fine per given code.

Also: the thinking param is added to payload_obj AFTER payload was already serialized once; they re-serialize. OK. But if provider=='zhipu' and the code path — wait, there's a subtle bug: the re-serialization `payload = json.dumps(payload_obj, ...)` happens INSIDE `if provider == 'zhipu':` block — good.

But hold on — is there an issue that `thinking` should also not be sent for other providers? It's only added under zhipu. Good.

Edge: what if provider=='zhipu' but model is like 'glm-4.5v' vision? Not relevant to _chat.

**3. redact_for_cloud security**

We only see 9 patterns referenced via `_REDACT_PATTERNS`