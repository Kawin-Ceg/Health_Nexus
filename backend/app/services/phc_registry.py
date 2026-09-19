"""Matching claimed PHC names against the valid_phc_facilities registry."""

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ValidPhcFacility

_PHC_ALIASES = re.compile(
    r"\b(?:primary\s+health\s+cent(?:re|er)|p\.?\s*h\.?\s*c\.?)(?=\W|$)",
    re.IGNORECASE,
)


def normalise_facility_name(name: str) -> str:
    """Lowercase; fold "P.H.C." / "Primary Health Centre" to "phc"; collapse punctuation.

    >>> normalise_facility_name("Mylapore Primary Health Centre")
    'mylapore phc'
    >>> normalise_facility_name("P.H.C. Mylapore")
    'phc mylapore'
    """
    folded = _PHC_ALIASES.sub(" phc ", name.lower())
    return " ".join(re.sub(r"[^a-z0-9]+", " ", folded).split())


async def match_facility(
    session: AsyncSession, phc_name: str, district: str, state: str
) -> ValidPhcFacility | None:
    """Exactly one active match in the claimed district, or None.

    An ambiguous match (two or more) returns None so the worker's phc_id stays
    NULL and an admin links it by hand. A NULL phc_id sees nobody.
    """
    rows = (
        await session.scalars(
            select(ValidPhcFacility)
            .where(
                ValidPhcFacility.normalised_name == normalise_facility_name(phc_name),
                ValidPhcFacility.district.ilike(district.strip()),
                ValidPhcFacility.state.ilike(state.strip()),
                ValidPhcFacility.is_active.is_(True),
            )
            .limit(2)
        )
    ).all()
    return rows[0] if len(rows) == 1 else None
