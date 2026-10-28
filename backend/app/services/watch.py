"""Simulated smartwatch sync.

A day has four slots (India time). Each slot can be synced once: syncing again in
the same slot returns that slot's reading instead of taking a new one. The values
are drawn around the person's own usual readings (or typical adult values for a
new person), shifted the way the body is across a day: lower heart rate and
breathing at night, slightly warmer in the afternoon.
"""

import random
import statistics
import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HealthRecord

from .visit_state import LOCAL_TZ

WATCH_VITALS = (
    "heart_rate",
    "spo2",
    "respiratory_rate",
    "temperature_c",
    "systolic",
    "diastolic",
    "glucose_mg_dl",
    "weight_kg",
)


@dataclass(frozen=True)
class Slot:
    key: str
    label: str
    start: int
    end: int


SLOTS = (
    Slot("morning", "Morning", 5, 12),
    Slot("afternoon", "Afternoon", 12, 17),
    Slot("evening", "Evening", 17, 21),
    Slot("night", "Night", 21, 5),
)

TYPICAL = {
    "heart_rate": 74.0,
    "spo2": 97.6,
    "respiratory_rate": 15.0,
    "temperature_c": 36.6,
    "systolic": 118.0,
    "diastolic": 77.0,
    "glucose_mg_dl": 92.0,
    "weight_kg": 64.0,
}
SPREAD = {
    "heart_rate": 3.5,
    "spo2": 0.6,
    "respiratory_rate": 0.9,
    "temperature_c": 0.12,
    "systolic": 4.0,
    "diastolic": 3.0,
    "glucose_mg_dl": 6.0,
    "weight_kg": 0.3,
}
SHIFT = {
    "morning": {"heart_rate": -1.0, "temperature_c": -0.1, "systolic": 3.0, "diastolic": 2.0, "glucose_mg_dl": -4.0},
    "afternoon": {"heart_rate": 3.0, "temperature_c": 0.15, "glucose_mg_dl": 12.0, "weight_kg": 0.4},
    "evening": {"heart_rate": 1.0, "temperature_c": 0.1, "glucose_mg_dl": 8.0, "weight_kg": 0.6},
    "night": {"heart_rate": -7.0, "respiratory_rate": -1.0, "temperature_c": -0.2, "systolic": -6.0, "diastolic": -4.0},
}
DECIMALS = {
    "heart_rate": 0,
    "spo2": 0,
    "respiratory_rate": 0,
    "temperature_c": 1,
    "systolic": 0,
    "diastolic": 0,
    "glucose_mg_dl": 0,
    "weight_kg": 1,
}
LIMITS = {
    "heart_rate": (40, 180),
    "spo2": (85, 100),
    "respiratory_rate": (8, 35),
    "temperature_c": (34.5, 41.0),
    "systolic": (80, 200),
    "diastolic": (45, 130),
    "glucose_mg_dl": (50, 300),
    "weight_kg": (20, 200),
}


def slot_at(moment: datetime) -> tuple[Slot, date]:
    """The slot a moment falls in and the day it counts for. 00:00-05:00 is the previous day's night."""
    local = moment.astimezone(LOCAL_TZ)
    hour = local.hour
    for s in SLOTS[:3]:
        if s.start <= hour < s.end:
            return s, local.date()
    day = local.date() if hour >= 21 else date.fromordinal(local.date().toordinal() - 1)
    return SLOTS[3], day


async def synced_today(session: AsyncSession, user_id: uuid.UUID, day: date) -> dict[str, HealthRecord]:
    rows = await session.scalars(
        select(HealthRecord).where(
            HealthRecord.user_id == user_id, HealthRecord.source == "watch", HealthRecord.watch_day == day
        )
    )
    return {r.watch_slot: r for r in rows if r.watch_slot}


async def simulate(session: AsyncSession, user_id: uuid.UUID, slot: Slot, day: date) -> dict[str, float]:
    recent = (
        await session.scalars(
            select(HealthRecord.vitals)
            .where(HealthRecord.user_id == user_id)
            .order_by(HealthRecord.timestamp.desc())
            .limit(30)
        )
    ).all()
    rng = random.Random(f"{user_id}-{day.isoformat()}-{slot.key}")
    out: dict[str, float] = {}
    for key in WATCH_VITALS:
        own = [float(v[key]) for v in recent if v.get(key) is not None]
        usual = statistics.median(own) if len(own) >= 5 else TYPICAL[key]
        value = usual + SHIFT[slot.key].get(key, 0.0) + rng.gauss(0, SPREAD[key])
        low, high = LIMITS[key]
        out[key] = round(min(high, max(low, value)), DECIMALS[key])
    out["spo2"] = min(out["spo2"], 100.0)
    out["diastolic"] = min(out["diastolic"], out["systolic"] - 20)
    return out
