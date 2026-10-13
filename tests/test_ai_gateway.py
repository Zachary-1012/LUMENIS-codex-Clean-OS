# -*- coding: utf-8 -*-
"""AI Gateway helper tests with an isolated usage log and a stubbed response."""

from scripts.ai_gateway import chat, _estimate_tokens


def test_estimate_tokens():
    assert _estimate_tokens("中文测试内容") == 6  # 6 个汉字
    assert _estimate_tokens("abc") == 1          # 3 ascii / 3
    assert _estimate_tokens("") == 0


def test_chat_uses_fixed_prefix_and_records_budget(tmp_path, monkeypatch):
    import scripts.ai_budget as ab

    monkeypatch.setattr(ab, "LOG", str(tmp_path / "ai-budget.jsonl"))

    captured = {}

    def fake_chat(system, user, **kwargs):
        captured["system"] = system
        captured.update(kwargs)
        return "这是摘要结果", "owned", {"model": "owned-test-model"}

    # Patch the public Gateway API; the helper must not call its private transport.
    from lumenis.system.ai_gateway import core as ai_core
    monkeypatch.setattr(ai_core, "chat", fake_chat)

    content, provider, meta = chat("summarizer", "请摘要这段内容", model="owned-test-model")
    assert content == "这是摘要结果" and provider == "owned"
    assert captured["use_cache"] is False
    assert captured["model"] == "owned-test-model"
    # 固定前缀已加载（含角色描述，非空且稳定）
    assert "摘要引擎" in captured["system"]
    assert meta["role"] == "summarizer" and meta["in_tokens"] > 0
    # budget 已记录
    s = ab.summary()
    assert s["total_calls"] == 1
    assert s["by_provider"]["owned"]["calls"] == 1


def test_chat_unknown_role_raises_keyerror(monkeypatch):
    import pytest
    from lumenis.system.ai_gateway import core as ai_core
    monkeypatch.setattr(ai_core, "chat", lambda *a, **k: ("x", "owned", {}))
    with pytest.raises(KeyError):
        chat("no_such_role", "hi")


def test_chat_json_repairs_broken_output(tmp_path, monkeypatch):
    import scripts.ai_gateway as g
    import scripts.ai_budget as ab
    monkeypatch.setattr(ab, "LOG", str(tmp_path / "ai-budget.jsonl"))
    captured = {}

    def fake_chat(system, user, **kwargs):
        captured.setdefault("calls", 0)
        captured["calls"] += 1
        if captured["calls"] == 1:
            return "`json\n{'name': 'Alice', 'age': 30,}\n`", "owned", {}
        return '{"name": "Alice", "age": 30}', "owned", {}

    from lumenis.system.ai_gateway import core as ai_core
    monkeypatch.setattr(ai_core, "chat", fake_chat)

    data, provider, meta = g.chat_json("summarizer", "返回用户 JSON", max_retries=0)
    assert data == {"name": "Alice", "age": 30}
    assert provider == "owned"
    assert "fix_quotes" in meta["strategies"] or "fix_commas" in meta["strategies"]
    assert meta["attempts"] == 1
    assert ab.summary()["total_calls"] == 1


def test_chat_json_retries_on_failure(tmp_path, monkeypatch):
    import scripts.ai_gateway as g
    import scripts.ai_budget as ab
    monkeypatch.setattr(ab, "LOG", str(tmp_path / "b.jsonl"))

    def fake_chat(system, user, **kwargs):
        # 第一次坏，第二次好
        if "不是合法 JSON" in user:
            return '{"name": "Bob", "age": 25}', "owned", {}
        return "完全不是JSON", "owned", {}

    from lumenis.system.ai_gateway import core as ai_core
    monkeypatch.setattr(ai_core, "chat", fake_chat)

    data, _provider, meta = g.chat_json("summarizer", "返回用户 JSON", max_retries=1)
    assert data == {"name": "Bob", "age": 25}
    assert meta["attempts"] == 2
