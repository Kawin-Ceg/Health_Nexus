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

WATCH_VITALS = ("heart_rate", "spo2", "respiratory_rate", "temperature_c")


@dataclass(frozen=True)
class Slot:
    key: str
    label: str
    start: int  # local hour, inclusive
    end: int  # local hour, exclusive (wraps past midnight for night)


SLOTS = (
    Slot("morning", "Morning", 5, 12),
    Slot("afternoon", "Afternoon", 12, 17),
    Slot("evening", "Evening", 17, 21),
    Slot("night", "Night", 21, 5),
)

TYPICAL = {"heart_rate": 74.0, "spo2": 97.6, "respiratory_rate": 15.0, "temperature_c": 36.6}
SPREAD = {"heart_rate": 3.5, "spo2": 0.6, "respiratory_rate": 0.9, "temperature_c": 0.12}
SHIFT = {
    "morning": {"heart_rate": -1.0, "temperature_c": -0.1},
    "afternoon": {"heart_rate": 3.0, "temperature_c": 0.15},
    "evening": {"heart_rate": 1.0, "temperature_c": 0.1},
    "night": {"heart_rate": -7.0, "respiratory_rate": -1.0, "temperature_c": -0.2},
}
DECIMALS = {"heart_rate": 0, "spo2": 0, "respiratory_rate": 0, "temperature_c": 1}
LIMITS = {"heart_rate": (40, 180), "spo2": (85, 100), "respiratory_rate": (8, 35), "temperature_c": (34.5, 41.0)}


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
    return out
