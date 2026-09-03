# -*- coding: utf-8 -*-
"""营销节点日历模块测试。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.marketing_calendar import (suggest_hotspot, nodes_for_month, node_on,
                                        _NODES)


def test_month_nodes_complete():
    for m in range(1, 13):
        assert len(nodes_for_month(m)) >= 2, "月%d 节点不足" % m


def test_hotspot_hits_midautumn():
    r = suggest_hotspot("2026-09-25", "商业地产")
    assert any(n["name"] == "中秋节" for n in r["nodes"]), r["nodes"]
    assert r["themes"]


def test_hotspot_double11():
    r = suggest_hotspot("2026-11-11", "美妆")
    assert any("双11" in n["name"] for n in r["nodes"]), r["nodes"]


def test_hotspot_valentine():
    r = suggest_hotspot("2026-02-14")
    assert any("情人节" in n["name"] for n in r["nodes"]), r["nodes"]


def test_node_on_today():
    import datetime
    today = datetime.date.today().strftime("%m-%d")
    hits = node_on(datetime.date.today().strftime("%Y-%m-%d"))
    # 今天可能是也可能不是节点，但口径必须与 MM-DD 版一致
    assert hits == node_on(today)


def test_all_nodes_have_required_fields():
    for nodes in _NODES.values():
        for n in nodes:
            assert {"name", "date", "kind", "theme", "cats"} <= set(n), n
            assert len(n["date"]) == 5
