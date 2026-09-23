"""The ML seam. `score_reading` is the only thing the anomaly model owner replaces.

The body below is a placeholder: it flags any value outside its published
normal range. Keep the signature and the ScoreResult shape exactly; the rest of
the app (triage, alerts, the record page) depends on them.
"""

import uuid
from dataclasses import dataclass
from typing import Literal

from .metrics import VITALS

# Below this many earlier readings there is no personal baseline, and nothing
# may be scored against one. The dashboard and record page use the same number.
MIN_BASELINE_READINGS = 7

# A contribution of this size maps to anomaly_score 1.0.
SCORE_CEILING = 4.0

Basis = Literal["published_ranges", "personal_baseline"]


@dataclass(frozen=True)
class ScoreResult:
    anomaly_score: float  # 0..1
    is_anomaly: bool
    # Per-vital contribution, e.g. {"systolic": 2.8}. Not optional: it is what
    # lets a flag explain itself (services/triage.describe_signal).
    features: dict[str, float]
    # What the reading was compared with. A model that uses a personal baseline
    # must only say so when history has at least MIN_BASELINE_READINGS rows.
    basis: Basis = "published_ranges"


def score_reading(user_id: uuid.UUID, vitals: dict[str, float], history: list[dict[str, float]]) -> ScoreResult:
    """Returns anomaly_score (0–1), is_anomaly, and features:
    a per-vital contribution dict such as {"systolic": 2.8}.

    `history` is this person's earlier readings, oldest first, excluding this one.

    Placeholder: each contribution is how far the value sits outside its normal
    band, in half-band-widths (0 inside). Any non-zero contribution flags.
    It always compares with published ranges, whatever the history length.
    """
    del user_id, history  # the placeholder uses neither; the model will
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

    peak = max(features.values(), default=0.0)
    return ScoreResult(
        anomaly_score=round(min(1.0, peak / SCORE_CEILING), 3),
        is_anomaly=peak > 0,
        features=features,
        basis="published_ranges",
    )
