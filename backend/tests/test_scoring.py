"""The anomaly scorer (services/scoring.py): published ranges first, then the person's own baseline. No database."""

import random
import uuid

from app.services.scoring import (
    FULL_BASELINE_READINGS,
    MIN_BASELINE_READINGS,
    MODEL_VERSION,
    baseline_weight,
    robust_baseline,
    score_reading,
    stage_of,
)

USER = uuid.uuid4()


def history(n: int, seed: int = 1, **centres: float) -> list[dict[str, float]]:
    """n readings scattered around `centres`, oldest first."""
    rng = random.Random(seed)
    spread = {"heart_rate": 2, "systolic": 4, "diastolic": 3, "temperature_c": 0.1, "spo2": 0.5, "weight_kg": 0.3}
    return [{k: round(c + rng.gauss(0, spread[k]), 1) for k, c in centres.items()} for _ in range(n)]


def test_weight_ramps_from_published_to_personal():
    assert baseline_weight(MIN_BASELINE_READINGS - 1) == 0
    assert 0 < baseline_weight(MIN_BASELINE_READINGS) < 1
    assert baseline_weight(FULL_BASELINE_READINGS) == 1
    assert [stage_of(n) for n in (0, MIN_BASELINE_READINGS, FULL_BASELINE_READINGS)] == ["learning", "blending", "personal"]


def test_new_person_is_compared_with_published_ranges():
    result = score_reading(USER, {"heart_rate": 48}, [])
    assert result.is_anomaly  # well below 60 bpm, and nothing else to go on
    assert result.basis == "published_ranges"
    assert result.details["heart_rate"].stage == "learning"
    assert result.model_version == MODEL_VERSION


def test_low_resting_heart_rate_is_normal_for_someone_whose_usual_is_low():
    result = score_reading(USER, {"heart_rate": 55}, history(25, heart_rate=55))
    assert not result.is_anomaly
    assert result.basis == "personal_baseline"
    assert result.details["heart_rate"].stage == "personal"


def test_controlled_hypertension_is_judged_against_the_persons_own_baseline():
    earlier = history(25, systolic=145, diastolic=92)
    assert not score_reading(USER, {"systolic": 147, "diastolic": 93}, earlier).is_anomaly
    assert score_reading(USER, {"systolic": 163, "diastolic": 95}, earlier).is_anomaly  # past the safety limit


def test_just_outside_a_band_is_not_a_flag():
    # 1 mmHg over 120 is within measurement noise: below FLAG_THRESHOLD
    assert not score_reading(USER, {"systolic": 121}, []).is_anomaly
    assert score_reading(USER, {"systolic": 131}, []).is_anomaly


def test_safety_limits_are_one_sided_where_only_one_side_is_dangerous():
    assert not score_reading(USER, {"spo2": 99}, []).is_anomaly
    assert score_reading(USER, {"spo2": 91}, []).is_anomaly


def test_safety_limits_flag_whatever_the_baseline():
    earlier = history(25, temperature_c=36.6, spo2=97)
    fever = score_reading(USER, {"temperature_c": 38.1}, earlier)
    assert fever.is_anomaly and fever.details["temperature_c"].safety
    assert score_reading(USER, {"spo2": 92}, earlier).is_anomaly


def test_in_range_change_needs_a_second_reading_to_flag():
    earlier = history(25, heart_rate=55)
    first = score_reading(USER, {"heart_rate": 75}, earlier)  # inside 60-100, far above their 55
    assert not first.is_anomaly
    assert first.watch == ["heart_rate"]
    assert first.features["heart_rate"] == 0
    second = score_reading(USER, {"heart_rate": 76}, earlier + [{"heart_rate": 75}])
    assert second.is_anomaly and second.watch == []
    assert second.details["heart_rate"].confirmed


def test_a_change_in_the_other_direction_does_not_confirm():
    earlier = history(25, heart_rate=70)
    result = score_reading(USER, {"heart_rate": 84}, earlier + [{"heart_rate": 60.5}])
    assert not result.is_anomaly and result.watch == ["heart_rate"]


def test_weight_is_scored_only_against_a_personal_baseline():
    assert "weight_kg" not in score_reading(USER, {"weight_kg": 70}, []).features
    earlier = history(25, weight_kg=70)
    steady = score_reading(USER, {"weight_kg": 70.3}, earlier)
    assert "weight_kg" in steady.features and not steady.is_anomaly


def test_one_odd_reading_barely_moves_the_baseline():
    values = [70.0] * 20 + [140.0]
    median, spread = robust_baseline("heart_rate", values)
    assert median == 70 and spread == 4.0  # floored at MIN_SPREAD, not blown up by the outlier


def test_details_are_json_ready_for_storage():
    result = score_reading(USER, {"heart_rate": 90, "systolic": 118}, history(10, heart_rate=72, systolic=112))
    stored = result.details_json()
    assert set(stored) == {"heart_rate", "systolic"}
    assert {"stage", "weight", "published", "baseline", "spread", "z", "confirmed", "safety"} <= set(stored["heart_rate"])
