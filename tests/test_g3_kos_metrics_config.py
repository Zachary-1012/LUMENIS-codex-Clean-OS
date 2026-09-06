# -*- coding: utf-8 -*-
"""G3 单测：kos_metrics.py 配置缺失显式 WARNING

验证：
1. 配置缺失时触发 logging.warning
2. config_status 字段正确标记（configured/fallback_default/missing）
3. 未知平台触发 WARNING
"""
import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

import kos_metrics as km


class TestG3ConfigWarning:
    """G3: 配置缺失触发 WARNING"""

    def test_missing_config_triggers_warning(self, caplog, tmp_path):
        """配置文件不存在时，应 WARNING 并标记 missing。"""
        km.reload_platform_rules()
        with patch.object(km, 'PLATFORM_RULES_PATH', tmp_path / 'nonexistent.json'):
            km.reload_platform_rules()
            with caplog.at_level(logging.WARNING):
                km.platform_kos_score('xiaohongshu', engagement=100, note_count=5)
            assert any("KOS配置缺失" in rec.message for rec in caplog.records)
            assert km.get_platform_rules_status() == "missing"
        km.reload_platform_rules()

    def test_corrupt_config_triggers_warning(self, caplog, tmp_path):
        """配置文件损坏时，应 WARNING 并标记 fallback_default。"""
        bad = tmp_path / "bad.json"
        bad.write_text("{broken", encoding="utf-8")
        km.reload_platform_rules()
        with patch.object(km, 'PLATFORM_RULES_PATH', bad):
            km.reload_platform_rules()
            with caplog.at_level(logging.WARNING):
                km.platform_kos_score('xiaohongshu', engagement=100, note_count=5)
            assert any("KOS配置损坏" in rec.message for rec in caplog.records)
            assert km.get_platform_rules_status() == "fallback_default"
        km.reload_platform_rules()

    def test_unknown_platform_triggers_warning(self, caplog):
        """未知平台应 WARNING 并回退 xiaohongshu。"""
        km.reload_platform_rules()
        with caplog.at_level(logging.WARNING):
            result = km.platform_kos_score('totally_unknown_platform_xyz', engagement=100, note_count=5)
        assert any("未知平台" in rec.message for rec in caplog.records)
        assert result["score"] > 0  # 回退后仍能计算

    def test_normal_config_no_warning(self, caplog):
        """正常配置时不应触发配置缺失 WARNING。"""
        km.reload_platform_rules()
        with caplog.at_level(logging.WARNING):
            km.platform_kos_score('xiaohongshu', engagement=100, note_count=5)
        config_warnings = [r for r in caplog.records if "KOS配置缺失" in r.message or "KOS配置损坏" in r.message]
        assert len(config_warnings) == 0
        assert km.get_platform_rules_status() == "configured"


class TestG3ConfigStatus:
    """G3: config_status 字段正确标记"""

    def test_kos_score_has_config_status(self):
        """platform_kos_score 返回值应含 config_status。"""
        km.reload_platform_rules()
        result = km.platform_kos_score('xiaohongshu', engagement=100, note_count=5, subject_type='kos')
        assert "config_status" in result
        assert result["config_status"] == "configured"

    def test_ad_score_has_config_status(self):
        """platform_ad_score 返回值应含 config_status。"""
        km.reload_platform_rules()
        result = km.platform_ad_score('xiaohongshu', engagement=100, likes=10, comments=5, collects=3)
        assert "config_status" in result
        assert result["config_status"] == "configured"

    def test_fallback_config_status(self, tmp_path):
        """配置缺失时，config_status 应为 missing/fallback_default。"""
        km.reload_platform_rules()
        with patch.object(km, 'PLATFORM_RULES_PATH', tmp_path / 'no.json'):
            km.reload_platform_rules()
            result = km.platform_kos_score('xiaohongshu', engagement=100, note_count=5)
            assert result["config_status"] in ("missing", "fallback_default")
        km.reload_platform_rules()

    def test_platform_engagement_returns_float(self):
        """platform_engagement 保持返回 float（向后兼容，不破坏 kos_engine 调用）。"""
        km.reload_platform_rules()
        result = km.platform_engagement('xiaohongshu', 10, 5, 3, 2)
        assert isinstance(result, float)
        assert result == 28.5  # 10*1 + 5*2 + 3*1.5 + 2*2


class TestG3FallbackValues:
    """G3: 回退默认值与配置一致"""

    def test_fallback_weights_match_config(self):
        """回退默认权重应与配置文件中的小红书权重一致。"""
        default = km._DEFAULT_PLATFORM_RULES["xiaohongshu"]["engagement_weights"]
        assert default["likes"] == 1.0
        assert default["comments"] == 2.0
        assert default["collects"] == 1.5
        assert default["shares"] == 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
