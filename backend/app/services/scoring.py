"""The ML seam. `score_reading` is the only thing the rest of the app calls.

Model: personal baselines on top of published normal ranges (MODEL_VERSION).
The method comes from the research in model/ (notebooks 02 and 03, LifeSnaps data):

- A new person is compared with published normal ranges, the "global model".
- Each vital gets its own baseline from the person's earlier readings: a median
  and a robust spread (MAD), so one odd reading does not move it much.
- Per vital, the weight moves from the published range to the personal baseline
  as readings build up: none below MIN_BASELINE_READINGS, all of it from
  FULL_BASELINE_READINGS on.
- A value past a safety limit always counts in full (SAFETY_LIMITS): a fever
  is a fever, whatever the person's usual temperature.
- A value inside the published range that is only unusual *for this person*
  needs a second unusual reading of that vital in a row before it flags.
  Until then it is reported in `watch` and contributes nothing. One odd home
  reading is usually noise; illness keeps a value off for days.

The trained population model (services/population.py, built in model/) runs
on every reading too. Its answer, how unusual the heart rate and breathing rate
are next to 71 people's data, is returned in `population` and stored, but it
never flags by itself: on held-out people it caught nothing these rules missed,
and most readings it calls unusual are ordinary for that person
(model/reports/population_model_metrics.json).

Keep the signature and the ScoreResult fields: triage, alerts and the record
page depend on them. model/healthnexus_ml/evaluate.py and
model/notebooks/04_app_scorer.ipynb evaluate this module.
"""

import statistics
import uuid
from dataclasses import asdict, dataclass, field
from typing import Literal

from . import population
from .metrics import VITALS
from .population import PopulationCheck

MODEL_VERSION = "personal-baseline-v1"

# Below this many earlier readings of a vital there is no personal baseline for
# it, and nothing may be scored against one. The dashboard and record page use
# the same number.
MIN_BASELINE_READINGS = 7
# From this many earlier readings the vital is compared with the person alone.
FULL_BASELINE_READINGS = 21
# The baseline looks at the person's most recent readings of each vital.
BASELINE_WINDOW = 30

# The personal contribution starts this many robust SDs from their own median,
# and each further PERSONAL_UNIT_Z adds 1. With FLAG_THRESHOLD 0.5 a vital
# counts from 2.25 SD, and an in-range one needs that twice in a row. Tuned in
# model/notebooks/04_app_scorer.ipynb: 2.5 caught only 16 % of moderate episodes;
# 1.5 catches 68 % for 1.5 % false flags.
PERSONAL_OK_Z = 1.5
PERSONAL_UNIT_Z = 1.5
# (low, high): at or past these a value always counts in full, however usual it
# is for the person. Set where a clinician would want to hear about it even
# from someone who is always a bit high, and wider than the normal bands, so a
# person with controlled chronic hypertension (say 145/92) is judged against
# their own baseline instead of being flagged on every reading.
SAFETY_LIMITS: dict[str, tuple[float | None, float | None]] = {
    "systolic": (85, 160),
    "diastolic": (50, 100),
    "heart_rate": (45, 120),
    "temperature_c": (35.5, 38.0),
    "spo2": (92, None),
    "respiratory_rate": (9, 24),
    "glucose_mg_dl": (65, 180),
}

# A vital counts toward a flag only from this contribution up (safety limits
# always count). Without it, a systolic of 121 still flags while the baseline is
# blending in, because 1 mmHg over the published band is "outside" it. 0.5 is
# about half a half-band: systolic 128, heart rate 110, temperature 37.5 °C, or
# 2.25 SD from the person's own usual. Chosen in model/notebooks/04_app_scorer.ipynb.
FLAG_THRESHOLD = 0.5

# A contribution of this size maps to anomaly_score 1.0.
SCORE_CEILING = 4.0

MAD_TO_SD = 1.4826
# Smallest spread a baseline may have. A very regular person would otherwise
# get a near-zero spread and be flagged for ordinary measurement noise; these
# are roughly the repeatability of home devices.
MIN_SPREAD: dict[str, float] = {
    "systolic": 5.0,
    "diastolic": 4.0,
    "heart_rate": 4.0,
    "temperature_c": 0.2,
    "spo2": 1.0,
    "respiratory_rate": 1.5,
    "glucose_mg_dl": 8.0,
    "weight_kg": 0.8,
}

Basis = Literal["published_ranges", "personal_baseline"]
Stage = Literal["learning", "blending", "personal"]


@dataclass(frozen=True)
class VitalDetail:
    """How one vital of one reading was judged. Stored with the score for audit."""

    value: float
    readings: int  # earlier readings of this vital the baseline could use
    stage: Stage
    weight: float  # 0 = published range only, 1 = personal baseline only
    published: float  # contribution from the published range (0 inside it)
    safety: bool  # past a safety limit: counts in full
    baseline: float | None = None  # personal median
    spread: float | None = None  # personal robust SD
    z: float | None = None  # (value - baseline) / spread
    personal: float | None = None  # contribution from the personal baseline
    confirmed: bool = True  # False: unusual for them, waiting for a second reading


@dataclass(frozen=True)
class ScoreResult:
    anomaly_score: float  # 0..1
    is_anomaly: bool
    # Per-vital contribution, e.g. {"systolic": 2.8}. Not optional: it is what
    # lets a flag explain itself (services/triage.describe_signal).
    features: dict[str, float]
    # What the reading was compared with. "personal_baseline" only when at least
    # one vital had MIN_BASELINE_READINGS earlier readings.
    basis: Basis = "published_ranges"
    model_version: str = MODEL_VERSION
    details: dict[str, VitalDetail] = field(default_factory=dict)
    # Vitals unusual for this person but not yet confirmed by a second reading.
    watch: list[str] = field(default_factory=list)
    # The trained population model's view of this reading; None without heart rate
    # or breathing rate, or without the model. Informs, never flags.
    population: PopulationCheck | None = None

    def details_json(self) -> dict[str, dict]:
        return {key: asdict(detail) for key, detail in self.details.items()}

    def population_json(self) -> dict | None:
        return asdict(self.population) if self.population else None


def published_contribution(key: str, value: float) -> float:
    """How far outside the published normal band, in half-band widths. 0 inside, or with no band."""
    normal = VITALS[key].normal
    if normal is None:
        return 0.0
    low, high = normal
    half_band = (high - low) / 2
    if value < low:
        return (low - value) / half_band
    if value > high:
        return (value - high) / half_band
    return 0.0


def past_safety_limit(key: str, value: float) -> bool:
    low, high = SAFETY_LIMITS.get(key, (None, None))
    return (low is not None and value <= low) or (high is not None and value >= high)


def baseline_weight(readings: int) -> float:
    """0 below MIN_BASELINE_READINGS, rising to 1 at FULL_BASELINE_READINGS."""
    if readings < MIN_BASELINE_READINGS:
        return 0.0
    span = FULL_BASELINE_READINGS - MIN_BASELINE_READINGS + 1
    return min(1.0, (readings - MIN_BASELINE_READINGS + 1) / span)


def stage_of(readings: int) -> Stage:
    if readings < MIN_BASELINE_READINGS:
        return "learning"
    return "personal" if readings >= FULL_BASELINE_READINGS else "blending"


def robust_baseline(key: str, values: list[float]) -> tuple[float, float]:
    """Median and robust SD (MAD-based, floored) of the most recent values."""
    recent = values[-BASELINE_WINDOW:]
    median = statistics.median(recent)
    mad = statistics.median(abs(v - median) for v in recent)
    # never exactly 0: a run of identical values must not divide by zero
    return median, max(mad * MAD_TO_SD, MIN_SPREAD.get(key, 0.0), 1e-6)


def personal_contribution(z: float) -> float:
    return max(0.0, abs(z) - PERSONAL_OK_Z) / PERSONAL_UNIT_Z


def _previous_z(key: str, earlier: list[float]) -> float | None:
    """z of the most recent earlier value against the baseline before it."""
    if len(earlier) - 1 < MIN_BASELINE_READINGS:
        return None
    median, spread = robust_baseline(key, earlier[:-1])
    return (earlier[-1] - median) / spread


def _judge(key: str, value: float, earlier: list[float]) -> VitalDetail:
    readings = len(earlier)
    weight = baseline_weight(readings)
    published = published_contribution(key, value)
    safety = past_safety_limit(key, value)
    if weight == 0:
        return VitalDetail(value, readings, "learning", 0.0, round(published, 2), safety)

    median, spread = robust_baseline(key, earlier)
    z = (value - median) / spread
    personal = personal_contribution(z)
    confirmed = True
    if published == 0 and personal > 0:
        previous = _previous_z(key, earlier)
        # Same direction and also outside their usual band.
        confirmed = previous is not None and abs(previous) > PERSONAL_OK_Z and (previous > 0) == (z > 0)
    return VitalDetail(
        value=value,
        readings=readings,
        stage=stage_of(readings),
        weight=round(weight, 3),
        published=round(published, 2),
        safety=safety,
        baseline=round(median, 2),
        spread=round(spread, 2),
        z=round(z, 2),
        personal=round(personal, 2),
        confirmed=confirmed,
    )


def _contribution(d: VitalDetail) -> float:
    """What this vital adds to the score: 0 unless it passes FLAG_THRESHOLD or a safety limit."""
    if not d.confirmed:
        return 0.0
    blended = (1 - d.weight) * d.published + d.weight * (d.personal or 0.0)
    if d.safety:
        return max(blended, d.published, FLAG_THRESHOLD)
    return blended if blended >= FLAG_THRESHOLD else 0.0


def score_reading(user_id: uuid.UUID, vitals: dict[str, float], history: list[dict[str, float]]) -> ScoreResult:
    """Returns anomaly_score (0–1), is_anomaly, and features:
    a per-vital contribution dict such as {"systolic": 2.8}.

    `history` is this person's earlier readings, oldest first, excluding this one.
    A vital is scored if it has a published band or a personal baseline.
    """
    del user_id  # everything personal arrives in `history`
    details: dict[str, VitalDetail] = {}
    for key, value in vitals.items():
        spec = VITALS.get(key)
        if spec is None:
            continue
        earlier = [float(h[key]) for h in history if h.get(key) is not None]
        if spec.normal is None and len(earlier) < MIN_BASELINE_READINGS:
            continue  # no band and no baseline yet: nothing to compare with (weight)
        details[key] = _judge(key, float(value), earlier)

    features = {key: round(_contribution(d), 2) for key, d in details.items()}
    peak = max(features.values(), default=0.0)
    return ScoreResult(
        anomaly_score=round(min(1.0, peak / SCORE_CEILING), 3),
        is_anomaly=peak > 0,
        features=features,
        basis="personal_baseline" if any(d.weight > 0 for d in details.values()) else "published_ranges",
        details=details,
        watch=[key for key, d in details.items() if not d.confirmed],
        population=population.check(vitals),
    )
