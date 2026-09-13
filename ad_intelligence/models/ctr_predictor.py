"""Deterministic baseline CTR predictor.

This is intentionally a transparent read-only baseline, not a trained model and
not an automated bidding component. It provides a stable production fallback and
an explainable contract that can later be replaced behind the same interface.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class CTRPrediction:
    predicted_ctr: float
    confidence: float
    model_version: str
    factors: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CTRPredictor:
    """Small deterministic CTR baseline used when no trained model is active."""

    MODEL_VERSION = "baseline-v1.0"
    BASELINE_CTR = 0.02

    _PLATFORM_FACTOR = {
        "xhs": 1.15,
        "xiaohongshu": 1.15,
        "douyin": 1.10,
        "weibo": 0.95,
        "bilibili": 1.00,
        "test": 1.00,
    }

    @staticmethod
    def _hour_factor(hour: int | None) -> float:
        if hour is None:
            return 1.0
        hour = max(0, min(23, int(hour)))
        if 19 <= hour <= 22:
            return 1.35
        if 11 <= hour <= 14 or 17 <= hour <= 18:
            return 1.15
        if 0 <= hour <= 5:
            return 0.65
        if 6 <= hour <= 8:
            return 0.85
        return 1.0

    def predict(self, features: Mapping[str, Any] | None = None) -> CTRPrediction:
        features = features or {}
        platform = str(features.get("platform") or "").strip().lower()
        platform_factor = self._PLATFORM_FACTOR.get(platform, 1.0)
        hour_factor = self._hour_factor(features.get("hour"))

        bid_amount = features.get("bid_amount")
        bid_factor = 1.0
        if bid_amount is not None:
            try:
                bid = max(0.0, float(bid_amount))
                # Keep the baseline deliberately conservative and bounded.
                bid_factor = 1.0 + min(bid, 20.0) * 0.002
            except (TypeError, ValueError):
                bid_factor = 1.0

        ctr = self.BASELINE_CTR * platform_factor * hour_factor * bid_factor
        ctr = max(0.0001, min(0.25, ctr))

        supplied = sum(
            1 for key in ("platform", "hour", "bid_amount")
            if features.get(key) is not None
        )
        confidence = min(0.80, 0.50 + supplied * 0.08)

        return CTRPrediction(
            predicted_ctr=ctr,
            confidence=confidence,
            model_version=self.MODEL_VERSION,
            factors={
                "platform": platform_factor,
                "hour": hour_factor,
                "bid": bid_factor,
            },
        )

    def batch_predict(self, rows: Iterable[Mapping[str, Any]]) -> list[CTRPrediction]:
        return [self.predict(row) for row in rows]

    def get_model_info(self) -> dict[str, Any]:
        return {
            "mode": "baseline",
            "baseline_ctr": self.BASELINE_CTR,
            "model_version": self.MODEL_VERSION,
            "read_only": True,
            "trained_model": False,
        }
