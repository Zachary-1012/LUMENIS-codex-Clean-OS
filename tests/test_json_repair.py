# -*- coding: utf-8 -*-
"""轻量 JSON 修复测试（能力提取自 outputguard）。"""
from scripts.json_repair import repair_json, safe_parse_json


def test_clean_json_no_repair():
    data, applied = repair_json('{"a": 1, "b": [1, 2]}')
    assert data == {"a": 1, "b": [1, 2]} and applied == []


def test_strip_fences():
    data, applied = repair_json('```json\n{"a": 1}\n```')
    assert data == {"a": 1} and "strip_fences" in applied


def test_extract_json_from_prose():
    data, _ = repair_json('好的，这是结果：{"a": 1, "b": "x"} 希望对你有帮助')
    assert data == {"a": 1, "b": "x"}


def test_fix_booleans_keys_quotes_commas():
    data, applied = repair_json("{'a': True, 'b': None, 'c': 3,}")
    assert data == {"a": True, "b": None, "c": 3}
    assert "fix_quotes" in applied and "fix_booleans" in applied


def test_fix_truncated_closers():
    data, _ = repair_json('{"a": 1, "b": "hel')
    assert data == {"a": 1, "b": "hel"}


def test_safe_parse_and_failure():
    assert safe_parse_json('{"x": 1}') == {"x": 1}
    assert safe_parse_json("not json at all !!!") is None
    assert repair_json("") == (None, [])
    assert repair_json(None) == (None, [])
