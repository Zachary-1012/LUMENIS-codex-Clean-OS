# -*- coding: utf-8 -*-
"""多供应商 LLM 网关健壮性回归（可反复运行）：
任何一家云端失败都必须自动回退本地规则、绝不抛异常；结构字段必须合法。
有真实 key 时对应 provider 会真实出数，无 key / 无额度时回退 rule，两种情况都覆盖。
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AI_TIMEOUT_SECONDS"] = "20"
import intelligence

# 本地 provider（本地优先基线：auto 时 Ollama/LMStudio/llama.cpp 优先于云端）
LOCAL_PROVIDERS = ("ollama", "lmstudio", "llama_cpp")

def use(p):
    os.environ["AI_PROVIDER"] = p
    intelligence._CACHE["ts"] = 0
    return intelligence.ai_status()

def test_openai_failure_falls_back():
    use("openai")  # 该 key 0 额度，应 429 -> 多 Provider 故障转移
    raw, prov = intelligence._chat("只输出OK", "测试", 0, 20)
    # 当前架构：多 Provider 故障转移（openai 失败 → zhipu/ark/qwen → rule）
    # 不再是单 Provider 直接到 rule
    valid_providers = ("rule", "zhipu", "ark", "qwen", "deepseek", "openai")
    assert prov in valid_providers, f"unexpected provider: {prov}"
    if prov == "rule":
        assert raw is None
    else:
        assert raw  # 非 rule provider 必须有内容
    print("[PASS] OpenAI：成功则出数，失败多 Provider 故障转移 ->", prov)

def test_zhipu_wired_and_safe():
    st = use("zhipu")
    # Tests must not read .env or require a cloud credential.  With an
    # explicitly injected key the configured GLM endpoint is exposed; without
    # one the production contract is the deterministic local-rule fallback.
    if st["enabled"]:
        assert st["base_url"].endswith("/paas/v4") and st["model"].startswith("glm-")
    else:
        assert st["provider"] == "local_rule" and st["runtime"] == "rule"
    raw, prov = intelligence._chat("只输出JSON：{\"ok\":1}", "测试", 0, 300)
    assert prov in ("zhipu", "rule")
    if prov == "zhipu":
        assert raw
    print("[PASS] 智谱接线正确，在线出数/失败回退均安全 ->", prov)

def test_auto_priority():
    for k in ("ARK_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY"):
        os.environ.pop(k, None)
    st = use("auto")
    assert st["provider"] in ("zhipu", "local_rule") + LOCAL_PROVIDERS, st
    print("[PASS] auto 选择 ->", st["provider"], st.get("model"))

def test_review_note_structure():
    note = {"title": "太古汇停车排队久", "content": "品牌很全环境好，就是停车场排队太久、引导不清"}
    rule = {"verified": True, "summary": "提及太古汇停车", "topics": ["停车"], "verify_reason": ""}
    res = intelligence.review_note(note, rule)
    assert res["verification"] in ("verified", "review", "suspicious_fake", "rejected")
    assert res.get("summary")
    assert res.get("provider") in ("zhipu", "rule", "openai", "qwen", "deepseek", "ark") + LOCAL_PROVIDERS
    print("[PASS] review_note 结构合法，分析来源 ->", res["provider"])

if __name__ == "__main__":
    test_openai_failure_falls_back()
    test_zhipu_wired_and_safe()
    test_auto_priority()
    test_review_note_structure()
    print("\n全部用例通过")
