# -*- coding: utf-8 -*-
"""视频脚本模板 + 多平台运营策略 测试。"""
from scripts.video_script import VIDEO_TYPES, generate_video_script
from scripts.social_ops import PLATFORMS, generate_social_matrix, generate_social_ops


def test_video_script_all_types():
    for vt in VIDEO_TYPES:
        r = generate_video_script("岚序", "美妆个护", "高奢小众", "luxury", vt,
                                  product_point="东方节气香氛", hotspot="中秋")
        assert r["meta"]["video_type"] == VIDEO_TYPES[vt]["name"]
        assert r["meta"]["ratio"]
        assert len(r["shots"]) >= 4
        for s in r["shots"]:
            assert s["scene"] and s["shot_size"] and s["content"]
        assert r["publish_advice"]
        assert r["meta"]["hotspot_bind"] and "中秋" in r["meta"]["hotspot_bind"]


def test_video_script_shot_count():
    r = generate_video_script("X", "汽车", "户外运动", "premium", "douyin", "赛道性能", n_shots=5)
    assert len(r["shots"]) == 5
    assert r["meta"]["video_type"] == "抖音视频"
    assert r["meta"]["ratio"] == "9:16 竖屏"
    assert r["title_candidates"] and all("%s" not in t for t in r["title_candidates"])


def test_social_all_platforms():
    m = generate_social_matrix("太古汇", None, "高奢小众", "luxury", "世界杯")
    assert set(m.keys()) == set(PLATFORMS.keys())
    for p, cfg in m.items():
        assert cfg["ecosystem"] and cfg["content_columns"] and cfg["invest"]
        assert cfg["meta"]["hotspot_bind"] and "世界杯" in cfg["meta"]["hotspot_bind"]


def test_social_luxury_tonality():
    r = generate_social_ops("太古汇", "小红书", "高奢小众", "luxury")
    assert "克制" in r["viral_formula"]
    assert r["tone_advice"] and "克制" in r["tone_advice"]


def test_social_mass_differs():
    a = generate_social_ops("X", "抖音", "Z世代潮人", "mass")
    b = generate_social_ops("X", "抖音", "高奢小众", "luxury")
    assert "玩梗" in a["tone_advice"]
    assert "克制" in b["tone_advice"]
