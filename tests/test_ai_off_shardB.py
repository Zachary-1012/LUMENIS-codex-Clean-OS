# -*- coding: utf-8 -*-
"""AI OFF Test — 模拟 AI 完全不可用，验证核心链路仍可运行。

真实测试：不 mock，通过环境变量强制 AI 不可用，验证：
1. intelligence._chat() → (None, 'provider_disabled')
2. review_note() → 回退规则引擎结果
3. subject_hit() → 正常工作（不依赖 AI）
4. 风险规则 → 正常工作（不依赖 AI）
5. ai_status() → enabled=False, provider=provider_disabled
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

results = []

def check(name, passed, detail=""):
    results.append({"name": name, "passed": passed, "detail": detail})
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}: {detail}")


def _run_ai_off_tests():
    """AI OFF 测试（可被 pytest 收集，也可独立运行）"""
    global results
    results = []

    # 强制 AI OFF：指定云端 provider 但清空 key（阻止本地 auto-detect）
    os.environ["AI_PROVIDER"] = "zhipu"
    os.environ["ALLOW_CLOUD_AI"] = "false"
    os.environ["ZHIPU_API_KEY"] = ""
    os.environ["ARK_API_KEY"] = ""
    os.environ["DASHSCOPE_API_KEY"] = ""
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["DEEPSEEK_API_KEY"] = ""
    os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:1"
    if "LOCAL_AI_PREFERRED" in os.environ:
        del os.environ["LOCAL_AI_PREFERRED"]

    print("=" * 60)
    print("AI OFF Test — 模拟 AI 完全不可用")
    print("=" * 60)

    # 1. ai_status() should show disabled
    print("\n--- 1. AI Status ---")
    try:
        import intelligence
        intelligence._CACHE['ts'] = 0
        intelligence._CACHE['provider'] = None
        intelligence._CACHE['model'] = None
        intelligence._CACHE['base'] = None
        status = intelligence.ai_status()
        check("ai_status.enabled=False", status.get("enabled") == False,
              f"enabled={status.get('enabled')}, runtime={status.get('runtime')}")
        check("ai_status.provider=provider_disabled", status.get("provider") == "provider_disabled",
              f"runtime={status.get('runtime')}")
    except Exception as e:
        check("ai_status()", False, f"exception: {e}")

    # 2. Retired Zhipu is explicitly unavailable; business rule continuity is checked below.
    print("\n--- 2. _chat() Disabled Provider ---")
    try:
        content, provider = intelligence._chat("system", "user", max_tokens=100)
        check("_chat returns None content", content is None, f"content={repr(content)[:80]}")
        check("_chat provider=provider_disabled", provider == "provider_disabled", f"provider={provider}")
    except Exception as e:
        check("_chat()", False, f"exception: {e}")

    # 3. review_note() should fall back to rule engine
    print("\n--- 3. review_note() Rule Fallback ---")
    try:
        from subject_rules import subject_hit
        note = {"title": "广州太古汇探店", "content": "今天去了广州太古汇，环境很好", "source_platform": "xiaohongshu"}
        rule_analysis = {"verified": True, "summary": "规则引擎初判", "topics": ["探店"]}
        result = intelligence.review_note(note, rule_analysis)
        check("review_note returns dict", isinstance(result, dict), f"type={type(result)}")
        check("review_note provider=rule (AI off)", result.get("provider") == "rule",
              f"provider={result.get('provider')}")
        check("review_note has relevance", "relevance" in result, f"keys={list(result.keys())[:8]}")
    except Exception as e:
        check("review_note()", False, f"exception: {e}")

    # 4. subject_hit() works without AI
    print("\n--- 4. Subject Filter (No AI) ---")
    try:
        from subject_rules import subject_hit, SUBJECT_WORDS
        hit1 = subject_hit("广州太古汇今天有活动")
        hit2 = subject_hit("上海恒隆广场很好")
        check("subject_hit detects Taikoo Hui", hit1 == True, f"hit1={hit1}")
        check("subject_hit excludes non-Taikoo", hit2 == False, f"hit2={hit2}")
        check("SUBJECT_WORDS non-empty", len(SUBJECT_WORDS) > 0, f"count={len(SUBJECT_WORDS)}")
    except Exception as e:
        check("subject_hit()", False, f"exception: {e}")

    # 5. AI Gateway chat() should fail gracefully
    print("\n--- 5. AI Gateway chat() Graceful Failure ---")
    try:
        from scripts.ai_gateway import chat
        content, provider, meta = chat("summarizer", "test content", max_tokens=50)
        check("gateway chat returns None on AI off", content is None, f"content={repr(content)[:80]}")
        check("gateway reports provider_disabled", provider == "provider_disabled", f"provider={provider}")
        check("gateway meta has role", meta.get("role") == "summarizer", f"meta={meta}")
    except Exception as e:
        check("gateway chat()", False, f"exception: {e}")

    # 6. Provider Registry still works
    print("\n--- 6. Provider Registry (No AI) ---")
    try:
        from lumenis.system.ai_gateway.providers import (
            provider_status, is_provider_available, active_providers, DISABLED,
        )
        check("zhipu status=DISABLED", provider_status("zhipu") == DISABLED, "")
        check("is_provider_available(zhipu)=False", is_provider_available("zhipu") is False, "")
        check("ark status=ACTIVE_FALLBACK", provider_status("ark") == "ACTIVE_FALLBACK", "")
        check("qwen status=NOT_CONFIGURED", provider_status("qwen") == "NOT_CONFIGURED", "")
        check("is_provider_available(qwen)=False", is_provider_available("qwen") == False, "")
        active = active_providers()
        check("active_providers excludes zhipu", "zhipu" not in active, f"active={active}")
    except Exception as e:
        check("provider_registry", False, f"exception: {e}")

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"AI OFF Test Summary: {passed}/{total} PASSED")
    print("=" * 60)
    for r in results:
        if not r["passed"]:
            print(f"  FAILED: {r['name']} — {r['detail']}")

    return passed == total


_ENV_KEYS = (
    "AI_PROVIDER", "ALLOW_CLOUD_AI", "ZHIPU_API_KEY", "ARK_API_KEY",
    "DASHSCOPE_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY",
    "OLLAMA_BASE_URL", "LOCAL_AI_PREFERRED",
)
_ENV_MISSING = object()


def run_ai_off_tests():
    """Run with retired routes disabled, then restore process env and cache."""
    import intelligence

    original_env = {key: os.environ.get(key, _ENV_MISSING) for key in _ENV_KEYS}
    original_cache = dict(intelligence._CACHE)
    try:
        return _run_ai_off_tests()
    finally:
        intelligence._CACHE.clear()
        intelligence._CACHE.update(original_cache)
        for key, value in original_env.items():
            if value is _ENV_MISSING:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_ai_off_core_chain():
    """pytest 入口：AI 关闭后核心链路仍可运行"""
    import intelligence

    env_before = {key: os.environ.get(key, _ENV_MISSING) for key in _ENV_KEYS}
    cache_before = dict(intelligence._CACHE)
    assert run_ai_off_tests() is True
    assert {key: os.environ.get(key, _ENV_MISSING) for key in _ENV_KEYS} == env_before
    assert intelligence._CACHE == cache_before


if __name__ == "__main__":
    ok = run_ai_off_tests()
    sys.exit(0 if ok else 1)
