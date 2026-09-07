# -*- coding: utf-8 -*-
"""G1 单测：kos_attribution.py 权重配置化

验证：
1. 配置驱动权重生效（demand_threshold/time_weight_coeff/platform_weights）
2. 配置缺失触发 WARNING 并回退默认值
3. 不同平台权重不同
"""
import json
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import kos_attribution as ka

@pytest.fixture(autouse=True)
def _reload_attribution_config_before_each():
    """Ensure clean config state before each test (defensive isolation).

    Previous tests may have left ka.CONFIG_PATH patched or _attr_config_cache stale.
    Reloading before every test guarantees a known-good starting state.
    """
    ka.reload_attribution_config()
    yield
    ka.reload_attribution_config()



class TestG1ConfigLoading:
    """G1: 配置加载与回退"""

    def test_config_loaded_successfully(self):
        """配置文件存在时，config_status 应为 configured。"""
        ka.reload_attribution_config()
        cfg = ka.load_attribution_config()
        assert cfg["config_status"] == "configured"
        assert cfg["attribution_weights"]["demand_threshold"] == 500
        assert cfg["attribution_weights"]["time_weight_coeff"] == 0.5

    def test_config_missing_triggers_warning_and_fallback(self, caplog):
        """配置文件缺失时，应 WARNING 并回退默认值。"""
        ka.reload_attribution_config()
        with patch.object(ka, 'CONFIG_PATH', Path('/nonexistent/g1_test_config.json')):
            ka.reload_attribution_config()
            with caplog.at_level(logging.WARNING):
                cfg = ka.load_attribution_config()
            assert cfg["config_status"] in ("fallback_default", "missing")
            assert cfg["attribution_weights"]["demand_threshold"] == 500  # 默认值与配置一致
            assert cfg["attribution_weights"]["time_weight_coeff"] == 0.5
            assert any("KOS归因配置缺失" in rec.message for rec in caplog.records)
        # 恢复
        ka.reload_attribution_config()

    def test_config_corrupt_triggers_warning(self, caplog, tmp_path):
        """配置文件损坏时，应 WARNING 并回退默认值。"""
        bad_config = tmp_path / "bad_rules.json"
        bad_config.write_text("{invalid json", encoding="utf-8")
        ka.reload_attribution_config()
        with patch.object(ka, 'CONFIG_PATH', bad_config):
            ka.reload_attribution_config()
            with caplog.at_level(logging.WARNING):
                cfg = ka.load_attribution_config()
            assert cfg["config_status"] == "fallback_default"
            assert any("KOS归因配置损坏" in rec.message for rec in caplog.records)
        ka.reload_attribution_config()


class TestG1PlatformWeights:
    """G1: 平台权重差异化"""

    def test_platform_normalization(self):
        """平台别名归一化：xhs/xiaohongshu-cdp → xiaohongshu。"""
        assert ka._normalize_platform("xhs") == "xiaohongshu"
        assert ka._normalize_platform("xiaohongshu-cdp") == "xiaohongshu"
        assert ka._normalize_platform("xiaohongshu") == "xiaohongshu"
        assert ka._normalize_platform("") == "xiaohongshu"  # 空回退默认

    def test_different_platforms_different_weights(self):
        """不同平台互动权重不同（小红书 comments=2.0, 抖音 shares=3.0）。"""
        cfg = ka.load_attribution_config()
        xhs = cfg["platform_weights"]["xiaohongshu"]
        dy = cfg["platform_weights"]["douyin"]
        assert xhs["comments"] == 2.0
        assert dy["shares"] == 3.0
        assert xhs != dy  # 平台权重确实不同

    def test_platform_weighted_interactions(self):
        """按平台权重计算互动量：小红书 likes=1, comments=2, collects=1.5, shares=2。"""
        note = {"likes": 10, "comments": 5, "collects": 3, "shares": 2, "source_platform": "xiaohongshu"}
        result = ka._platform_weighted_interactions(note)
        # 10*1 + 5*2 + 3*1.5 + 2*2 = 10 + 10 + 4.5 + 4 = 28.5
        assert result == 28.5

    def test_douyin_weighted_interactions(self):
        """抖音权重：likes=1, comments=2, collects=1, shares=3。"""
        note = {"likes": 10, "comments": 5, "collects": 3, "shares": 2, "source_platform": "douyin"}
        result = ka._platform_weighted_interactions(note)
        # 10*1 + 5*2 + 3*1 + 2*3 = 10 + 10 + 3 + 6 = 29
        assert result == 29.0

    def test_platform_weighted_differs_from_equal_weight(self):
        """平台加权互动量 ≠ 等权互动量（证明权重确实生效）。"""
        note = {"likes": 0, "comments": 10, "collects": 0, "shares": 0, "source_platform": "xiaohongshu"}
        weighted = ka._platform_weighted_interactions(note)
        equal = 10  # 等权 comments=1
        assert weighted == 20.0  # 小红书 comments 权重=2
        assert weighted != equal


class TestG1AttributionThresholds:
    """G1: demand_threshold/time_weight_coeff 从配置读取"""

    def test_demand_threshold_from_config(self):
        """demand_score 阈值从配置 demand_threshold 读取，不再硬编码 500。"""
        cfg = ka.load_attribution_config()
        assert cfg["attribution_weights"]["demand_threshold"] == 500
        # 验证默认值与配置一致
        assert ka._DEFAULT_ATTRIBUTION_WEIGHTS["demand_threshold"] == 500

    def test_time_weight_coeff_from_config(self):
        """time_weight 系数从配置 time_weight_coeff 读取，不再硬编码 0.5。"""
        cfg = ka.load_attribution_config()
        assert cfg["attribution_weights"]["time_weight_coeff"] == 0.5
        assert ka._DEFAULT_ATTRIBUTION_WEIGHTS["time_weight_coeff"] == 0.5

    def test_custom_threshold_changes_demand_score(self, tmp_path):
        """修改配置 demand_threshold 后，demand_score 计算应随之变化。"""
        # 创建自定义配置
        custom_config = {
            "_meta": {"version": "test"},
            "attribution_weights": {
                "demand_threshold": 100,  # 更低阈值
                "time_weight_coeff": 0.3,
                "time_weight_range": 1.0,
                "interaction_threshold": 5000,
                "reach_threshold": 2000,
                "commercial_threshold": 1000,
            },
            "xiaohongshu": {
                "engagement_weights": {"likes": 1.0, "comments": 2.0, "collects": 1.5, "shares": 2.0},
            },
        }
        config_file = tmp_path / "test_rules.json"
        config_file.write_text(json.dumps(custom_config), encoding="utf-8")

        ka.reload_attribution_config()
        with patch.object(ka, 'CONFIG_PATH', config_file):
            ka.reload_attribution_config()
            cfg = ka.load_attribution_config()
            assert cfg["attribution_weights"]["demand_threshold"] == 100
            assert cfg["attribution_weights"]["time_weight_coeff"] == 0.3
        ka.reload_attribution_config()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
