"""Vital keys, units and ranges for health_records.vitals. The single source for both."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VitalSpec:
    unit: str
    normal: tuple[float, float] | None  # None: no normal band (e.g. weight)
    plausible: tuple[float, float]  # readings outside this are rejected as input errors


VITALS: dict[str, VitalSpec] = {
    "systolic": VitalSpec("mmHg", (90, 120), (50, 300)),
    "diastolic": VitalSpec("mmHg", (60, 80), (30, 200)),
    "heart_rate": VitalSpec("bpm", (60, 100), (25, 250)),
    "temperature_c": VitalSpec("°C", (36.1, 37.2), (30, 45)),
    "spo2": VitalSpec("%", (95, 100), (50, 100)),
    "respiratory_rate": VitalSpec("breaths/min", (12, 20), (4, 60)),
    "glucose_mg_dl": VitalSpec("mg/dL", (70, 99), (20, 600)),
    "weight_kg": VitalSpec("kg", None, (2, 400)),
}


class ImplausibleVitalError(ValueError):
    pass


def validate_vitals(vitals: dict[str, float]) -> dict[str, float]:
    """Drop unknown keys and reject physically implausible values."""
    clean: dict[str, float] = {}
    for key, value in vitals.items():
        spec = VITALS.get(key)
        if spec is None or value is None:
            continue
        low, high = spec.plausible
        if not low <= float(value) <= high:
            raise ImplausibleVitalError(f"{key}={value} {spec.unit} is outside {low}-{high}")
        clean[key] = float(value)
    return clean
