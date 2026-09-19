"""Score one reading against published normal ranges.

Each vital's contribution is how far it sits outside its normal band, in units
of half the band width (0 inside the band). Those contributions are stored in
processed_data.features, so every flag can say which vital drove it.

This is the fallback used before a citizen has a personal baseline; the
healthnexus_ml Isolation Forest replaces it once there is enough history.
"""

from dataclasses import dataclass

from .vitals import VITALS

# A contribution of 2.0 means the value is a full band-width outside normal.
FLAG_THRESHOLD = 2.0
# Contribution at which anomaly_score reaches 1.0
SCORE_CEILING = 4.0


@dataclass(frozen=True)
class Score:
    features: dict[str, float]
    anomaly_score: float  # 0..1
    is_anomaly: bool
    top_feature: str | None


def score_reading(vitals: dict[str, float]) -> Score:
    features: dict[str, float] = {}
    for key, value in vitals.items():
        spec = VITALS.get(key)
        if spec is None or spec.normal is None:
            continue
        low, high = spec.normal
        half_band = (high - low) / 2
        if value < low:
            features[key] = round((low - value) / half_band, 2)
        elif value > high:
            features[key] = round((value - high) / half_band, 2)
        else:
            features[key] = 0.0

    top = max(features, key=features.__getitem__, default=None)
    peak = features[top] if top else 0.0
    return Score(
        features=features,
        anomaly_score=round(min(1.0, peak / SCORE_CEILING), 3),
        is_anomaly=peak >= FLAG_THRESHOLD,
        top_feature=top if peak > 0 else None,
    )
