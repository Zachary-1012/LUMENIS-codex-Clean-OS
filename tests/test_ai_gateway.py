# -*- coding: utf-8 -*-
"""AI Gateway 测试：固定前缀收敛 + budget 记录（mock _chat，不触网）。"""
import sys

from scripts.ai_gateway import chat, _estimate_tokens


def test_estimate_tokens():
    assert _estimate_tokens("中文测试内容") == 6  # 6 个汉字
    assert _estimate_tokens("abc") == 1          # 3 ascii / 3
    assert _estimate_tokens("") == 0


def test_chat_uses_fixed_prefix_and_records_budget(tmp_path, monkeypatch):
    import scripts.ai_gateway as g
    import scripts.ai_budget as ab

    monkeypatch.setattr(ab, "LOG", str(tmp_path / "ai-budget.jsonl"))
    monkeypatch.setattr(ab, "QUOTA", str(tmp_path / "quota.json"))
    import json
    json.dump({"provider": "zhipu", "resources": []},
              open(str(tmp_path / "quota.json"), "w", encoding="utf-8"))

    captured = {}

    def fake_chat(system, user, temperature=0.1, max_tokens=1200, model=None):
        captured["system"] = system
        return "这是摘要结果", "zhipu"

    # 注入 intelligence 模块（chat 内部 from intelligence import _chat）
    import types
    fake_intel = types.ModuleType("intelligence")
    fake_intel._chat = fake_chat
    sys.modules["intelligence"] = fake_intel

    content, provider, meta = chat("summarizer", "请摘要这段内容", model="glm-4.7")
    assert content == "这是摘要结果" and provider == "zhipu"
    # 固定前缀已加载（含角色描述，非空且稳定）
    assert "摘要引擎" in captured["system"]
    assert meta["role"] == "summarizer" and meta["in_tokens"] > 0
    # budget 已记录
    s = ab.summary()
    assert s["total_calls"] == 1
    assert s["by_provider"]["zhipu"]["calls"] == 1


def test_chat_unknown_role_raises_keyerror():
    import pytest
    import scripts.ai_gateway as g
    import types
    import sys as _sys
    fake_intel = types.ModuleType("intelligence")
    fake_intel._chat = lambda *a, **k: ("x", "zhipu")
    _sys.modules["intelligence"] = fake_intel
    with pytest.raises(KeyError):
        chat("no_such_role", "hi")


def test_chat_json_repairs_broken_output(tmp_path, monkeypatch):
    import scripts.ai_gateway as g
    import scripts.ai_budget as ab
    import json
    monkeypatch.setattr(ab, "LOG", str(tmp_path / "ai-budget.jsonl"))
    monkeypatch.setattr(ab, "QUOTA", str(tmp_path / "quota.json"))
    json.dump({"provider": "zhipu", "resources": []},
              open(str(tmp_path / "quota.json"), "w", encoding="utf-8"))
    import types, sys as _sys
    captured = {}

    def fake_chat(system, user, temperature=0.1, max_tokens=1200, model=None):
        captured.setdefault("calls", 0)
        captured["calls"] += 1
        if captured["calls"] == 1:
            return "`json\n{'name': 'Alice', 'age': 30,}\n`", "zhipu"
        return '{"name": "Alice", "age": 30}', "zhipu"

    fake_intel = types.ModuleType("intelligence")
    fake_intel._chat = fake_chat
    _sys.modules["intelligence"] = fake_intel

    data, provider, meta = g.chat_json("summarizer", "返回用户 JSON", max_retries=0)
    assert data == {"name": "Alice", "age": 30}
    assert provider == "zhipu"
    assert "fix_quotes" in meta["strategies"] or "fix_commas" in meta["strategies"]
    assert meta["attempts"] == 1
    assert ab.summary()["total_calls"] == 1


def test_chat_json_retries_on_failure(tmp_path, monkeypatch):
    import scripts.ai_gateway as g
    import scripts.ai_budget as ab
    import json
    monkeypatch.setattr(ab, "LOG", str(tmp_path / "b.jsonl"))
    monkeypatch.setattr(ab, "QUOTA", str(tmp_path / "q.json"))
    json.dump({"provider": "zhipu", "resources": []},
              open(str(tmp_path / "q.json"), "w", encoding="utf-8"))
    import types, sys as _sys

    def fake_chat(system, user, temperature=0.1, max_tokens=1200, model=None):
        # 第一次坏，第二次好
        if "不是合法 JSON" in user:
            return '{"name": "Bob", "age": 25}', "zhipu"
        return "完全不是JSON", "zhipu"

    fake_intel = types.ModuleType("intelligence")
    fake_intel._chat = fake_chat
    _sys.modules["intelligence"] = fake_intel

    data, provider, meta = g.chat_json("summarizer", "返回用户 JSON", max_retries=1)
    assert data == {"name": "Bob", "age": 25}
    assert meta["attempts"] == 2
