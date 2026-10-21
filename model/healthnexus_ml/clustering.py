"""Space-time DBSCAN over symptomatic cases, and a Poisson test for whether a cluster is more than usual.

Each case is projected to kilometres around the cases' mean latitude, with time as a
third axis: `km_per_day` says how far apart one day counts. DBSCAN then finds groups
where at least `min_people` different people fall within `radius_km` of each other in
that space. Each person contributes one point (their first onset in the window), so one
person logging the same fever every day cannot form a cluster alone.
"""

import math
from dataclasses import dataclass, field
from typing import Hashable

import numpy as np
from sklearn.cluster import DBSCAN

EARTH_KM = 6371.0088


@dataclass(frozen=True)
class Case:
    person: Hashable
    lat: float
    lng: float
    day: float
    symptoms: tuple[str, ...] = ()


@dataclass(frozen=True)
class Params:
    radius_km: float = 1.5
    km_per_day: float = 0.5
    min_people: int = 3
    min_radius_km: float = 0.3


@dataclass
class Cluster:
    cases: list[Case]
    centre_lat: float
    centre_lng: float
    radius_km: float
    first_day: float
    last_day: float
    symptoms: dict[str, int] = field(default_factory=dict)

    @property
    def people(self) -> int:
        return len(self.cases)


def first_onsets(cases: list[Case]) -> list[Case]:
    first: dict[Hashable, Case] = {}
    for c in cases:
        if c.person not in first or c.day < first[c.person].day:
            first[c.person] = c
    return list(first.values())


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_KM * math.asin(math.sqrt(a))


def project(cases: list[Case], params: Params) -> np.ndarray:
    lat0 = math.radians(float(np.mean([c.lat for c in cases])))
    return np.array([
        [
            EARTH_KM * math.radians(c.lng) * math.cos(lat0),
            EARTH_KM * math.radians(c.lat),
            c.day * params.km_per_day,
        ]
        for c in cases
    ])


def find_clusters(cases: list[Case], params: Params = Params()) -> list[Cluster]:
    points = first_onsets(cases)
    if len(points) < params.min_people:
        return []
    labels = DBSCAN(eps=params.radius_km, min_samples=params.min_people).fit_predict(project(points, params))
    clusters = []
    for label in sorted(set(labels) - {-1}):
        members = [p for p, lab in zip(points, labels, strict=True) if lab == label]
        lat = float(np.mean([m.lat for m in members]))
        lng = float(np.mean([m.lng for m in members]))
        radius = max(haversine_km(lat, lng, m.lat, m.lng) for m in members)
        counts: dict[str, int] = {}
        for m in members:
            for s in m.symptoms:
                counts[s] = counts.get(s, 0) + 1
        clusters.append(Cluster(
            cases=members,
            centre_lat=lat,
            centre_lng=lng,
            radius_km=max(radius, params.min_radius_km),
            first_day=min(m.day for m in members),
            last_day=max(m.day for m in members),
            symptoms=dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        ))
    clusters.sort(key=lambda c: -c.people)
    return clusters


def poisson_tail(observed: int, expected: float) -> float:
    """P(X >= observed) for X ~ Poisson(expected)."""
    if observed <= 0:
        return 1.0
    term = math.exp(-expected)
    below = term
    for k in range(1, observed):
        term *= expected / k
        below += term
    return max(0.0, 1.0 - below)
