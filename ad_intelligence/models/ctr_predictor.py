"""Read-only, explicitly uncalibrated CTR heuristic (G144).

The historical coefficients are retained for explanation/comparison only. They
are not measured click probabilities, confidence, or a bidding recommendation.
G150 calibration reports do not activate a trained CTR model by themselves.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class CTRPrediction:
    predicted_ctr: float | None
    confidence: float | None
    model_version: str
    factors: dict[str, float]
    heuristic_signal: float | None
    state: str
    missing_features: tuple[str, ...]
    probability_state: str = "UNCALIBRATED"
    prediction_interval: tuple[float, float] | None = None
    trained_model: bool = False
    source_evidence_id: int | None = None
    calibration_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CTRPredictor:
    """Original ad owner; unknown probability until a verified model is active."""

    MODEL_VERSION = "heuristic-v1.0"
    BASELINE_CTR = 0.02  # Historical heuristic scale; not an observed base rate.
    _PLATFORM_FACTOR = {
        "xhs": 1.15, "xiaohongshu": 1.15, "douyin": 1.10,
        "weibo": 0.95, "bilibili": 1.00, "test": 1.00,
    }

    @staticmethod
    def _hour_factor(hour: int | None) -> float:
        if hour is None:
            return 1.0
        if type(hour) is not int or not 0 <= hour <= 23:
            raise ValueError("CTR_HOUR_INVALID")
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
        if features is None:
            features = {}
        if not isinstance(features, Mapping):
            raise ValueError("CTR_FEATURES_INVALID")
        platform = features.get("platform")
        if platform is not None and (not isinstance(platform, str) or not platform.strip()):
            raise ValueError("CTR_PLATFORM_INVALID")
        platform = platform.strip().lower() if platform is not None else None
        platform_factor = self._PLATFORM_FACTOR.get(platform, 1.0)
        hour_factor = self._hour_factor(features.get("hour"))
        bid = features.get("bid_amount")
        if bid is not None and (
            type(bid) not in (int, float) or not math.isfinite(bid) or bid < 0
        ):
            raise ValueError("CTR_BID_INVALID")
        bid_factor = 1.0 if bid is None else 1.0 + min(bid, 20.0) * 0.002
        missing = tuple(k for k in ("platform", "hour", "bid_amount") if features.get(k) is None)
        # With no evidence/features, even a heuristic output would be an invented default.
        signal = None if len(missing) == 3 else self.BASELINE_CTR * platform_factor * hour_factor * bid_factor
        return CTRPrediction(
            predicted_ctr=None, confidence=None, model_version=self.MODEL_VERSION,
            factors={"platform": platform_factor, "hour": hour_factor, "bid": bid_factor},
            heuristic_signal=signal,
            state="NO_DATA" if signal is None else "HEURISTIC_UNCALIBRATED",
            missing_features=missing,
        )

    def batch_predict(self, rows: Iterable[Mapping[str, Any]]) -> list[CTRPrediction]:
        return [self.predict(row) for row in rows]

    def get_model_info(self) -> dict[str, Any]:
        return {
            "mode": "heuristic_uncalibrated", "heuristic_base_scale": self.BASELINE_CTR,
            "model_version": self.MODEL_VERSION, "read_only": True, "trained_model": False,
            "probability_state": "UNCALIBRATED", "prediction_interval": None,
            "parameters": {"platform_factors": dict(self._PLATFORM_FACTOR),
                           "hour_factors": {"19-22": 1.35, "11-14,17-18": 1.15,
                                            "0-5": 0.65, "6-8": 0.85, "other": 1.0},
                           "bid_coefficient": 0.002, "bid_cap": 20.0},
            "calibration_owner": "lumenis.shared.reporting.statistics_methods",
            "limitations": ["Historical coefficients are uncalibrated heuristics, not click probabilities.",
                            "No verified CTR model, model lineage, or applicable calibration is active.",
                            "G150 READY denotes a computation, not CTR deployment eligibility."],
        }
