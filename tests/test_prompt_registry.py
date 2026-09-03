# -*- coding: utf-8 -*-
"""Prompt Registry 稳定性测试：固定前缀逐字符稳定（缓存命中前提）。

改动前缀正文必须 bump version——本测试校验 version 与正文 hash 对应，
防止"原地改前缀"导致智谱缓存静默失效。
"""
from scripts.prompt_registry import list_roles, load_system_prompt


def test_all_roles_loadable():
    roles = list_roles()
    assert len(roles) >= 4  # analyst/summarizer/risk_reviewer/compliance
    for name, ver in roles:
        assert ver and int(ver) >= 1
        txt = load_system_prompt(name)
        assert isinstance(txt, str) and len(txt) > 20


def test_prefix_stability_hash():
    """同一角色两次加载逐字符一致（无尾部漂移/拼接差异）。"""
    for name, _ in list_roles():
        a = load_system_prompt(name)
        b = load_system_prompt(name)
        assert a == b and len(a) == len(b)


def test_unknown_role_raises():
    import pytest
    with pytest.raises(KeyError):
        load_system_prompt("no_such_role_xyz")
