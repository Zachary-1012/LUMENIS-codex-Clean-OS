# -*- coding: utf-8 -*-
"""广告投流与深度学习模块单元测试"""
import sys, os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestAdBase:

    def test_ad_metric_to_dict(self):
        from ad_intelligence.base import AdMetric
        m = AdMetric(impressions=1000, clicks=50, cost=100, revenue=300)
        d = m.to_dict()
        assert d["impressions"] == 1000
        assert d["clicks"] == 50
        assert d["cost"] == 100

    def test_ad_campaign_is_active(self):
        from ad_intelligence.base import AdCampaign
        c = AdCampaign(status="ACTIVE")
        assert c.is_active() is True
        c2 = AdCampaign(status="PAUSED")
        assert c2.is_active() is False

    def test_ad_platform_total_metrics(self):
        from ad_intelligence.base import AdPlatform, AdCampaign, AdMetric
        p = AdPlatform(platform="test")
        p.campaigns = [
            AdCampaign(metrics=AdMetric(impressions=1000, clicks=50, cost=100, revenue=300)),
            AdCampaign(metrics=AdMetric(impressions=2000, clicks=100, cost=200, revenue=500)),
        ]
        total = p.total_metrics()
        assert total.impressions == 3000
        assert total.clicks == 150
        assert total.cost == 300
        assert total.revenue == 800
        assert total.ctr > 0
        assert total.roas > 0


class TestAdPermissionGate:

    def test_default_permissions(self):
        from ad_intelligence.permission_gate import AdPermissionGate, AdPermissionLevel
        gate = AdPermissionGate()
        assert gate.has_permission(AdPermissionLevel.READ) is True
        assert gate.has_permission(AdPermissionLevel.ANALYZE) is True
        assert gate.has_permission(AdPermissionLevel.PREVIEW) is False
        assert gate.has_permission(AdPermissionLevel.EXECUTE) is False

    def test_execute_requires_canonical_human_approval(self, monkeypatch):
        monkeypatch.delenv("AD_PERMISSION_LEVEL", raising=False)
        monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
        from ad_intelligence.permission_gate import AdPermissionGate, AdPermissionLevel
        from lumenis.system.security import PermissionGate, PermissionLevel, permission as permission_module

        monkeypatch.setattr(permission_module, "_TESTING_BYPASS_ENABLED", False)

        system_gate = PermissionGate()
        system_gate.grant_permission(PermissionLevel.PUSH)
        gate = AdPermissionGate(system_gate=system_gate)
        gate.enable_level(AdPermissionLevel.EXECUTE)

        assert gate.require(AdPermissionLevel.EXECUTE, "test") is False
        token = gate.grant_human_approval(duration_minutes=5)
        assert token.startswith("apr_")
        assert gate.require(AdPermissionLevel.EXECUTE, "test") is True

    def test_execute_with_gate_denied(self):
        from ad_intelligence.permission_gate import AdPermissionGate, AdPermissionLevel
        gate = AdPermissionGate()
        success, result = gate.execute_with_gate(
            AdPermissionLevel.EXECUTE, "test_op", lambda: "done"
        )
        assert success is False
        assert "权限不足" in result

    def test_human_approval_expiry_is_owned_by_system_permission(self):
        from ad_intelligence.permission_gate import AdPermissionGate, AdPermissionLevel
        from lumenis.system.security import PermissionGate, PermissionLevel, OperationType
        from datetime import datetime, timedelta

        system_gate = PermissionGate()
        system_gate.grant_permission(PermissionLevel.PUSH)
        gate = AdPermissionGate(system_gate=system_gate)
        gate.enable_level(AdPermissionLevel.EXECUTE)
        token = gate.grant_human_approval(duration_minutes=1)
        system_gate._approvals[token].expires_at = datetime.now() - timedelta(minutes=2)

        gate._check_approval_expiry()
        assert system_gate.is_approved(OperationType.AD_EXECUTE.value) is False
        assert gate.get_status()["human_approved"] is False


class TestCTRPredictor:

    def test_baseline_prediction(self):
        from ad_intelligence.models.ctr_predictor import CTRPredictor
        predictor = CTRPredictor()
        result = predictor.predict({"platform": "xhs", "hour": 20})
        assert result.predicted_ctr is None
        assert 0 < result.heuristic_signal < 1
        assert result.confidence is None
        assert result.model_version == "heuristic-v1.0"

    def test_batch_predict(self):
        from ad_intelligence.models.ctr_predictor import CTRPredictor
        predictor = CTRPredictor()
        results = predictor.batch_predict([
            {"platform": "xhs", "hour": 20},
            {"platform": "douyin", "hour": 3},
        ])
        assert len(results) == 2
        assert results[0].heuristic_signal > results[1].heuristic_signal  # 晚间 > 凌晨

    def test_model_info(self):
        from ad_intelligence.models.ctr_predictor import CTRPredictor
        predictor = CTRPredictor()
        info = predictor.get_model_info()
        assert info["mode"] == "heuristic_uncalibrated"
        assert info["heuristic_base_scale"] == 0.02


class TestFeatureEngineer:

    def test_extract_features(self):
        from ad_intelligence.models.feature_engineer import AdFeatureEngineer
        engineer = AdFeatureEngineer()
        features = engineer.extract_features({
            "user": {"age": 25, "gender": "female", "region": "广州"},
            "ad": {"creative": {"title": "test", "format_type": "video"}, "bid_amount": 5.0},
            "platform": "xhs",
            "metrics": {"impressions": 1000, "clicks": 50},
        })
        assert features.user_features["age"] == 25
        assert features.ad_features["creative_type"] == "video"
        assert features.context_features["platform"] == "xhs"
        assert features.realtime_features["impressions"] == 1000

    def test_flat_dict(self):
        from ad_intelligence.models.feature_engineer import AdFeatureEngineer
        engineer = AdFeatureEngineer()
        features = engineer.extract_features({"platform": "test"})
        flat = features.to_flat_dict()
        assert "user_age" in flat
        assert "context_platform" in flat

    def test_feature_importance(self):
        from ad_intelligence.models.feature_engineer import AdFeatureEngineer
        engineer = AdFeatureEngineer()
        importance = engineer.get_feature_importance()
        assert len(importance) > 0
        assert sum(importance.values()) <= 1.01  # 允许浮点误差
