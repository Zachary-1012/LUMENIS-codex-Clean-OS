"""Deterministic feature extraction for the ad-intelligence baseline layer.

No external writes are performed here. The extractor normalizes input into a
stable, explainable structure that can later feed a replaceable trained model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class AdFeatureSet:
    user_features: dict[str, Any] = field(default_factory=dict)
    ad_features: dict[str, Any] = field(default_factory=dict)
    context_features: dict[str, Any] = field(default_factory=dict)
    realtime_features: dict[str, Any] = field(default_factory=dict)

    def to_flat_dict(self) -> dict[str, Any]:
        flat: dict[str, Any] = {}
        for prefix, values in (
            ("user", self.user_features),
            ("ad", self.ad_features),
            ("context", self.context_features),
            ("realtime", self.realtime_features),
        ):
            for key, value in values.items():
                flat[f"{prefix}_{key}"] = value
        return flat


class AdFeatureEngineer:
    """Normalize ad-analysis input without creating a second business truth."""

    _IMPORTANCE = {
        "context_platform": 0.22,
        "context_hour": 0.12,
        "ad_creative_type": 0.16,
        "ad_bid_amount": 0.10,
        "user_age": 0.10,
        "user_gender": 0.08,
        "user_region": 0.07,
        "realtime_ctr": 0.10,
        "realtime_impressions": 0.05,
    }

    @staticmethod
    def _mapping(value: Any) -> Mapping[str, Any]:
        return value if isinstance(value, Mapping) else {}

    def extract_features(self, payload: Mapping[str, Any] | None) -> AdFeatureSet:
        payload = payload or {}
        user = self._mapping(payload.get("user"))
        ad = self._mapping(payload.get("ad"))
        creative = self._mapping(ad.get("creative"))
        metrics = self._mapping(payload.get("metrics"))

        impressions = metrics.get("impressions", 0) or 0
        clicks = metrics.get("clicks", 0) or 0
        try:
            impressions_num = float(impressions)
        except (TypeError, ValueError):
            impressions_num = 0.0
        try:
            clicks_num = float(clicks)
        except (TypeError, ValueError):
            clicks_num = 0.0
        ctr = clicks_num / impressions_num if impressions_num > 0 else 0.0

        return AdFeatureSet(
            user_features={
                "age": user.get("age"),
                "gender": user.get("gender"),
                "region": user.get("region"),
            },
            ad_features={
                "creative_type": creative.get("format_type") or creative.get("type"),
                "title": creative.get("title"),
                "bid_amount": ad.get("bid_amount"),
            },
            context_features={
                "platform": payload.get("platform"),
                "hour": payload.get("hour"),
            },
            realtime_features={
                "impressions": impressions,
                "clicks": clicks,
                "ctr": ctr,
            },
        )

    def get_feature_importance(self) -> dict[str, float]:
        return dict(self._IMPORTANCE)
