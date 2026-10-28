"""The trained population model: an Isolation Forest from model/ (healthnexus_ml/vitals.py).

It says how unusual a reading's heart rate and breathing rate are, together,
compared with 4,400 days from 71 people in the LifeSnaps study. scoring.py runs
it on every reading that has either vital and stores the answer with the score.

The artifact is a plain dict (features, median, scale, forest, train_scores,
contamination, version), so loading it needs scikit-learn but not the model
package. If it is missing or will not load, readings are still scored; they
just carry no population check, and the API logs why once.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "model" / "artifacts" / "vitals_anomaly.joblib"


@dataclass(frozen=True)
class PopulationCheck:
    score: float
    percentile: float
    features: tuple[str, ...]
    version: str

    @property
    def unusual(self) -> bool:
        return self.score >= 0.5


def _configured_path() -> Path:
    try:
        from app.core.config import get_settings
    except ImportError:
        return DEFAULT_PATH
    return Path(get_settings().POPULATION_MODEL_PATH or DEFAULT_PATH)


@lru_cache
def _bundle() -> dict[str, Any] | None:
    path = _configured_path()
    try:
        import joblib

        bundle = joblib.load(path)
    except FileNotFoundError:
        log.warning("Population model not found at %s; readings will carry no population check.", path)
        return None
    except Exception as exc:  # noqa: BLE001 - a bad artifact must not stop scoring
        log.error("Population model at %s did not load (%s); readings will carry no population check.", path, exc)
        return None
    log.info("Loaded population model %s from %s", bundle.get("version"), path)
    return bundle


def model_info() -> dict[str, Any] | None:
    """What is loaded, for the API and the about page. None when nothing is."""
    b = _bundle()
    if b is None:
        return None
    return {key: b.get(key) for key in ("version", "features", "trained_on_days", "trained_on_people", "trained_at", "data")}


def check(vitals: dict[str, float]) -> PopulationCheck | None:
    """None when no model is loaded or the reading has none of the model's vitals."""
    b = _bundle()
    if b is None:
        return None
    features: list[str] = b["features"]
    used = tuple(f for f in features if vitals.get(f) is not None)
    if not used:
        return None
    row = [
        (float(vitals[f]) - m) / s if vitals.get(f) is not None and s > 0 else 0.0
        for f, m, s in zip(features, b["median"], b["scale"], strict=True)
    ]
    raw = -float(b["forest"].score_samples([row])[0])
    train = b["train_scores"]
    percentile = _searchsorted(train, raw) / len(train)
    c = b["contamination"]
    lo, hi = 1 - 2 * c, 1 - c / 6
    score = min(1.0, max(0.0, (percentile - lo) / (hi - lo)))
    return PopulationCheck(round(score, 3), round(percentile, 4), used, str(b.get("version", "unknown")))


NAMES = {"heart_rate": "heart rate", "respiratory_rate": "breathing rate"}


def describe(score: float, percentile: float, features: list[str] | tuple[str, ...]) -> str:
    """One sentence for a person reading it: what the model compared and what it found."""
    what = " and ".join(NAMES.get(f, f) for f in features)
    verb = "are" if len(features) > 1 else "is"
    if score >= 0.5:
        return f"Unusual next to 71 people's data: this {what} {verb} more unusual than {percentile:.1%} of their days."
    return f"Typical next to 71 people's data: this {what} {verb} within what they usually showed."


def _searchsorted(sorted_values, value: float) -> int:
    """numpy.searchsorted (side='left') on a sorted 1-D array, without importing numpy here."""
    lo, hi = 0, len(sorted_values)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_values[mid] < value:
            lo = mid + 1
        else:
            hi = mid
    return lo
