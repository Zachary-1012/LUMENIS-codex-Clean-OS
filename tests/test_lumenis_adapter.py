# -*- coding: utf-8 -*-
"""LUMENIS Production Core 只读适配层测试。

覆盖：
- import 成功
- snapshot 必需字段与 red_lines 数量
- subject_authority_readonly 不泄露词表内容
- contract_compatibility 只读声明
- 静态守卫：adapter 源码不含任何写操作关键字
"""
import ast
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from contracts import lumenis_adapter  # noqa: E402


def test_import_succeeds():
    assert callable(lumenis_adapter.production_core_snapshot)
    assert callable(lumenis_adapter.subject_authority_readonly)
    assert callable(lumenis_adapter.contract_compatibility)
    assert callable(lumenis_adapter.get_production_facts)


def test_snapshot_keys():
    s = lumenis_adapter.production_core_snapshot()
    assert isinstance(s, dict)
    for k in ("core", "repo", "role", "subject_authority",
              "capabilities", "red_lines", "contracts_implemented"):
        assert k in s, "snapshot missing key: %s" % k
    assert s["core"] == "Production Core"
    assert s["repo"] == "Z-Brand-Core"
    assert s["role"] == "production"
    assert len(s["red_lines"]) == 10
    assert "subject" in s["capabilities"]
    assert "risk" in s["capabilities"]
    assert isinstance(s["contracts_implemented"], dict)
    assert s["contracts_implemented"]["task"] == "read-only consumer"


def test_subject_authority_readonly_safe():
    sa = lumenis_adapter.subject_authority_readonly()
    assert isinstance(sa, dict)
    assert sa["status"] in ("ok", "module_not_found")
    # 只允许计数/存在性字段，禁止词表内容泄露
    allowed = {"status", "subject_words_count", "exclude_words_count",
               "subject_hit_present", "note", "detail"}
    assert set(sa.keys()) <= allowed, "unexpected keys: %s" % (set(sa.keys()) - allowed)
    if sa["status"] == "ok":
        assert isinstance(sa["subject_words_count"], int)
        assert sa["subject_words_count"] >= 0
        assert isinstance(sa["exclude_words_count"], int)
        assert sa["exclude_words_count"] >= 0
        assert isinstance(sa["subject_hit_present"], bool)
    assert sa["note"] == "counts only, contents not exposed"


def test_contract_compatibility():
    c = lumenis_adapter.contract_compatibility()
    assert isinstance(c, dict)
    for k in ("adapter_version", "lumenis_contracts_version", "role",
              "exposes", "writes", "db_writes"):
        assert k in c, "compat missing key: %s" % k
    assert c["writes"] is False
    assert c["db_writes"] is False
    assert "production_core_snapshot" in c["exposes"]


def test_no_db_write():
    """红线⑧自动化守卫：adapter 源码不得含任何写操作关键字。"""
    adapter_path = os.path.join(_REPO_ROOT, "contracts", "lumenis_adapter.py")
    with open(adapter_path, "r", encoding="utf-8") as f:
        source = f.read()
    # 先确认语法有效
    ast.parse(source)
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "commit()", "execute("]
    for token in forbidden:
        assert token not in source, "forbidden write token found in adapter: %r" % token
