"""The vitals vocabulary: keys, labels, units and ranges for health_records.vitals.

The single source for every page and endpoint. The frontend reads it from
GET /health/metrics rather than keeping its own copy.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class VitalSpec:
    key: str
    label: str
    unit: str
    group: str  # how the entry form groups fields
    normal: tuple[float, float] | None  # None: no normal band (weight)
    plausible: tuple[float, float]  # outside this a value is a typo, not an anomaly
    decimals: int = 0


_SPECS = (
    VitalSpec("systolic", "Systolic", "mmHg", "blood_pressure", (90, 120), (50, 300)),
    VitalSpec("diastolic", "Diastolic", "mmHg", "blood_pressure", (60, 80), (30, 200)),
    VitalSpec("heart_rate", "Heart rate", "bpm", "vitals", (60, 100), (25, 250)),
    VitalSpec("temperature_c", "Temperature", "°C", "vitals", (36.1, 37.2), (30, 45), decimals=1),
    VitalSpec("spo2", "Oxygen saturation", "%", "vitals", (95, 100), (50, 100)),
    VitalSpec("respiratory_rate", "Breathing rate", "/min", "vitals", (12, 20), (4, 60)),
    VitalSpec("glucose_mg_dl", "Blood glucose", "mg/dL", "other", (70, 99), (20, 600)),
    VitalSpec("weight_kg", "Weight", "kg", "other", None, (2, 400), decimals=1),
)

VITALS: dict[str, VitalSpec] = {spec.key: spec for spec in _SPECS}

# Offered as chips on the entry form. Free text is accepted too, within limits.
COMMON_SYMPTOMS = (
    "fever",
    "cough",
    "headache",
    "body ache",
    "breathlessness",
    "chest pain",
    "dizziness",
    "fatigue",
    "nausea",
    "diarrhoea",
    "thirst",
    "rash",
)


class ImplausibleVitalError(ValueError):
    pass


def validate_vitals(vitals: dict[str, float | None]) -> dict[str, float]:
    """Drop unknown keys and blanks; reject physically implausible values as input errors."""
    clean: dict[str, float] = {}
    for key, value in vitals.items():
        spec = VITALS.get(key)
        if spec is None or value is None:
            continue
        low, high = spec.plausible
        if not low <= float(value) <= high:
            raise ImplausibleVitalError(
                f"{spec.label} {value:g} {spec.unit} is not a plausible reading "
                f"(expected {low:g}–{high:g}). Check for a typo."
            )
        clean[key] = float(value)
    return clean


def position(key: str, value: float) -> str:
    """'below', 'normal' or 'above' the published normal band ('normal' when there is none)."""
    normal = VITALS[key].normal
    if normal is None:
        return "normal"
    if value < normal[0]:
        return "below"
    if value > normal[1]:
        return "above"
    return "normal"
