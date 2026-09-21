# -*- coding: utf-8 -*-
"""多供应商 LLM 网关健壮性回归（可反复运行）：
任何一家云端失败都必须自动回退本地规则、绝不抛异常；结构字段必须合法。
有真实 key 时对应 provider 会真实出数，无 key / 无额度时回退 rule，两种情况都覆盖。
"""
import os
import sys
import json
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
    valid_providers = ("rule", "zhipu", "ark", "qwen", "deepseek", "openai", "ollama")
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
    assert prov in ("zhipu", "ollama", "rule")
    if prov == "zhipu":
        assert raw
    print("[PASS] 智谱接线正确，在线出数/失败回退均安全 ->", prov)

def test_auto_priority():
    for k in ("ARK_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY"):
        os.environ.pop(k, None)
    st = use("auto")
    assert st["provider"] in ("zhipu", "local_rule") + LOCAL_PROVIDERS, st
    print("[PASS] auto 选择 ->", st["provider"], st.get("model"))


def test_daily_capability_uses_authorized_zhipu_pack():
    selected = intelligence.select_model_by_capability("daily")
    assert selected["provider"] == "zhipu"
    assert selected["model"] == "glm-4.5-air"


def test_strong_reasoning_uses_authorized_glm_47_pack():
    selected = intelligence.select_model_by_capability("strong_reasoning")
    assert selected["provider"] == "zhipu"
    assert selected["model"] == "glm-4.7"


def test_local_chat_does_not_consume_cloud_pack(monkeypatch):
    """Ollama 已就绪时，chat 不应检查或记录云端资源包。"""
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    local = ("ollama", "qwen2.5-coder:7b-agent", "http://127.0.0.1:11434")
    monkeypatch.setattr(intelligence, "_provider_config", lambda: local)
    monkeypatch.setattr(intelligence, "_chat", lambda *args, **kwargs: ("本地结果", "ollama"))
    budget_checks = []
    budget_records = []
    monkeypatch.setattr(intelligence, "_budget_check", lambda *args, **kwargs: budget_checks.append(args) or False)
    monkeypatch.setattr(intelligence, "_budget_record", lambda *args, **kwargs: budget_records.append(args))
    raw, provider, meta = intelligence.chat(
        "只回复结果", "本地测试", level="medium", pack_id="glm_4_5_air", use_cache=False
    )
    assert (raw, provider) == ("本地结果", "ollama")
    assert meta["model"] == "qwen2.5-coder:7b-agent"
    assert budget_checks == []
    assert budget_records == []


def test_explicit_local_failure_falls_back_to_rule_only(monkeypatch):
    """显式 Ollama 失败时不得偷偷切到云端 Provider。"""
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setattr(
        intelligence,
        "_provider_config",
        lambda: ("ollama", "qwen2.5-coder:7b-agent", "http://127.0.0.1:11434"),
    )

    def fail_urlopen(*args, **kwargs):
        raise OSError("simulated local outage")

    monkeypatch.setattr(intelligence.urllib.request, "urlopen", fail_urlopen)
    raw, provider = intelligence._chat("只回复结果", "本地测试", 0.0, 8)
    assert raw is None
    assert provider == "rule"


def test_cloud_failure_falls_back_to_ollama_with_thinking_disabled(monkeypatch):
    """云端链耗尽后应使用本机 Ollama，并禁用 Qwen3 隐式思考。"""
    monkeypatch.setenv("AI_PROVIDER", "zhipu")
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
    monkeypatch.setattr(
        intelligence,
        "_provider_config",
        lambda: ("zhipu", "glm-4.7", "https://example.invalid/v1"),
    )
    monkeypatch.setattr(
        intelligence.ai_channel,
        "route_with_fallback",
        lambda *args, **kwargs: (None, "rule"),
    )
    monkeypatch.setattr(
        intelligence,
        "_detect_local",
        lambda: ("ollama", "qwen3:4b", "http://127.0.0.1:11434"),
    )
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({
                "message": {"content": "LOCAL_OK"},
                "prompt_eval_count": 5,
                "eval_count": 2,
            }).encode("utf-8")

    def fake_urlopen(request, timeout=None):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(intelligence.urllib.request, "urlopen", fake_urlopen)
    raw, provider = intelligence._chat("system-local", "user-local", 0.0, 16)
    assert (raw, provider) == ("LOCAL_OK", "ollama")
    assert captured["payload"]["think"] is False
    assert captured["payload"]["messages"][1]["content"] == "user-local"
    assert intelligence._get_call_meta()["total_tokens"] == 7


def test_cloud_and_ollama_failure_falls_back_to_rule(monkeypatch):
    """云端和 Ollama 都不可用时，最终状态必须诚实标记为规则降级。"""
    monkeypatch.setenv("AI_PROVIDER", "zhipu")
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
    monkeypatch.setattr(
        intelligence,
        "_provider_config",
        lambda: ("zhipu", "glm-4.7", "https://example.invalid/v1"),
    )
    monkeypatch.setattr(
        intelligence.ai_channel,
        "route_with_fallback",
        lambda *args, **kwargs: (None, "rule"),
    )
    monkeypatch.setattr(
        intelligence,
        "_detect_local",
        lambda: ("ollama", "qwen3:4b", "http://127.0.0.1:11434"),
    )
    monkeypatch.setattr(
        intelligence.urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("offline")),
    )
    raw, provider = intelligence._chat("system", "user", 0.0, 16)
    assert raw is None
    assert provider == "rule"
    assert intelligence._get_call_meta()["model"] == "deterministic_rule"


def test_ollama_hint_reflects_reachable_models(monkeypatch):
    """健康提示必须以 /api/tags 的真实结果为准，而不是只看 PATH。"""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setattr(
        intelligence,
        "_get_json",
        lambda url, timeout=1.5: {"models": [{"name": "qwen2.5-coder:7b-agent"}]},
    )
    hint = next(item for item in intelligence._installed_hints() if item["provider"] == "ollama")
    assert hint["running"] is True
    assert hint["model_count"] == 1
    assert "可调用 1 个模型" in hint["detail"]

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
