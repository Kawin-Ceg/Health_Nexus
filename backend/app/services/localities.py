"""Locality aggregates for the Reports and Risk Map pages. These carry no names.

A locality with fewer than MIN_CELL citizens is folded into "Other localities":
"1 of 1 citizens in Luz is flagged" would name that person as surely as a list.
"""

from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProcessedData, User

from .catchment import catchment_citizens
from .consent import counts_in_community

MIN_CELL = 3
OTHER = "Other localities"
UNSPECIFIED = "Unspecified"

RiskLevel = Literal["high", "elevated", "some", "none"]


def locality_of(area: str | None) -> str:
    return area.strip() if area and area.strip() else UNSPECIFIED


def risk_level(share: float) -> RiskLevel:
    if share >= 0.3:
        return "high"
    if share >= 0.15:
        return "elevated"
    return "some" if share > 0 else "none"


def suppress(rows: dict[str, dict[str, float]], size_key: str = "citizens") -> dict[str, dict[str, float]]:
    """Fold localities below MIN_CELL into OTHER, summing their counts. Drops OTHER if it is itself too small."""
    kept: dict[str, dict[str, float]] = {}
    other: dict[str, float] = {}
    for name, values in rows.items():
        if values[size_key] >= MIN_CELL:
            kept[name] = values
        else:
            for key, value in values.items():
                other[key] = other.get(key, 0) + value
    if other and other[size_key] >= MIN_CELL:
        kept[OTHER] = other
    return kept


async def locality_risk(session: AsyncSession, worker: User) -> list[dict]:
    """Localities ranked by the share of their citizens with at least one open flag.

    Counts only citizens who allowed community health monitoring.
    """
    flagged_ids = (
        select(ProcessedData.user_id)
        .where(ProcessedData.is_anomaly.is_(True), ProcessedData.resolution.is_(None))
        .distinct()
        .scalar_subquery()
    )
    citizens = catchment_citizens(worker).where(counts_in_community(User.id)).subquery()
    rows = await session.execute(
        select(
            citizens.c.area,
            func.count().label("citizens"),
            func.count().filter(citizens.c.id.in_(flagged_ids)).label("flagged"),
            func.avg(citizens.c.geo_lat).label("lat"),
            func.avg(citizens.c.geo_lng).label("lng"),
        ).group_by(citizens.c.area)
    )
    merged: dict[str, dict[str, float]] = {}
    coords: dict[str, tuple[float | None, float | None]] = {}
    for area, n, flagged, lat, lng in rows.all():
        name = locality_of(area)
        bucket = merged.setdefault(name, {"citizens": 0, "flagged": 0})
        bucket["citizens"] += n
        bucket["flagged"] += flagged
        coords.setdefault(name, (lat, lng))

    items = []
    for name, values in suppress(merged).items():
        share = values["flagged"] / values["citizens"] if values["citizens"] else 0.0
        lat, lng = coords.get(name, (None, None)) if name not in (OTHER, UNSPECIFIED) else (None, None)
        items.append(
            {
                "locality": name,
                "citizens": int(values["citizens"]),
                "flagged": int(values["flagged"]),
                "share": round(share, 3),
                "level": risk_level(share),
                "lat": lat,
                "lng": lng,
            }
        )
    items.sort(key=lambda item: (-item["share"], -item["flagged"], item["locality"]))
    return items
