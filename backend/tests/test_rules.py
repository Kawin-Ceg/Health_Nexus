"""The single-source rules: visit state, triage, scoring, the vitals vocabulary. No database."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.enums import VisitStatus
from app.services.metrics import ImplausibleVitalError, validate_vitals
from app.services.scoring import score_reading
from app.services.triage import band_bounds, citizen_ref, describe_signal, severity_of
from app.services.visit_state import LOCAL_TZ, format_local, visit_state

S = VisitStatus.scheduled


def ist(*args: int) -> datetime:
    return datetime(*args, tzinfo=LOCAL_TZ)


def test_day_boundaries_are_local_not_utc():
    now = ist(2026, 9, 24, 1, 30)
    assert now.astimezone(timezone.utc).day == 23
    assert visit_state(S, ist(2026, 9, 24, 10, 0), now) == "today"
    assert visit_state(S, ist(2026, 9, 25, 0, 30), now) == "upcoming"


def test_a_passed_visit_is_never_today_or_upcoming():
    now = ist(2026, 9, 24, 15, 0)
    assert visit_state(S, now - timedelta(minutes=1), now) == "due_now"
    assert visit_state(S, now - timedelta(hours=4), now) == "due_now"
    assert visit_state(S, now - timedelta(hours=4, minutes=1), now) == "overdue"
    assert visit_state(S, now + timedelta(minutes=1), now) == "today"


def test_decisions_are_reported_as_stored():
    now = ist(2026, 9, 24, 15, 0)
    for status in (VisitStatus.completed, VisitStatus.cancelled, VisitStatus.missed):
        assert visit_state(status, now - timedelta(days=3), now) == status.value


def test_format_local():
    assert format_local(ist(2026, 9, 24, 9, 5)) == "Thu 24 Sep, 9:05 AM"


def test_severity_bands_and_sql_bounds_agree():
    for score in (0.01, 0.25, 0.49, 0.5, 0.74, 0.75, 1.0):
        band = severity_of(score)
        low, high = band_bounds(band)
        assert low <= score and (high is None or score < high)


def test_citizen_ref_is_stable_and_short():
    uid = uuid.UUID("1a2b3c4d-0000-0000-0000-000000000000")
    assert citizen_ref(uid) == "HN-1A2B3C4D"


def test_describe_signal_reads_blood_pressure_as_a_pair():
    vitals = {"systolic": 167, "diastolic": 103, "heart_rate": 80}
    features = score_reading(uuid.uuid4(), vitals, []).features
    assert describe_signal(features, vitals) == "Blood pressure 167/103 mmHg — well above the normal range"


def test_describe_signal_below_range_and_nothing_flagged():
    for spo2, expected in ((88.0, "Oxygen saturation 88% — well below the normal range"),
                           (92.0, "Oxygen saturation 92% — below the normal range")):
        vitals = {"spo2": spo2}
        assert describe_signal(score_reading(uuid.uuid4(), vitals, []).features, vitals) == expected
    normal = {"heart_rate": 72.0}
    assert describe_signal(score_reading(uuid.uuid4(), normal, []).features, normal) is None


def test_scorer_contract():
    result = score_reading(uuid.uuid4(), {"temperature_c": 38.9, "weight_kg": 70}, [{"temperature_c": 36.6}] * 3)
    assert result.is_anomaly and 0 < result.anomaly_score <= 1
    assert set(result.features) == {"temperature_c"}
    assert result.basis == "published_ranges"
    assert not score_reading(uuid.uuid4(), {"heart_rate": 70}, []).is_anomaly


def test_implausible_values_are_typos_not_anomalies():
    with pytest.raises(ImplausibleVitalError):
        validate_vitals({"systolic": 1200})
    assert validate_vitals({"systolic": 120, "unknown": 5, "spo2": None}) == {"systolic": 120.0}
