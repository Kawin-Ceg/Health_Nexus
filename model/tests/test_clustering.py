import numpy as np

from healthnexus_ml.clustering import Case, Params, find_clusters, haversine_km, poisson_tail
from healthnexus_ml.features import syndromes

CENTRE = (13.033, 80.262)


def around(n, lat, lng, km, days, seed, prefix="p"):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        dlat = rng.normal(0, km) / 111.0
        dlng = rng.normal(0, km) / (111.0 * np.cos(np.radians(lat)))
        out.append(Case(f"{prefix}{i}", lat + dlat, lng + dlng, float(rng.uniform(*days)), ("fever",)))
    return out


def test_a_tight_group_is_found_and_scattered_cases_are_noise():
    group = around(6, *CENTRE, km=0.3, days=(8, 11), seed=1)
    scattered = around(8, *CENTRE, km=15, days=(0, 14), seed=2, prefix="s")
    clusters = find_clusters(group + scattered)
    assert len(clusters) == 1
    assert {c.person for c in clusters[0].cases} >= {c.person for c in group[:4]}
    assert haversine_km(clusters[0].centre_lat, clusters[0].centre_lng, *CENTRE) < 1
    assert clusters[0].symptoms == {"fever": clusters[0].people}


def test_one_person_repeating_is_not_a_cluster():
    same = [Case("p1", *CENTRE, day=d) for d in range(10)] + [Case("p2", *CENTRE, day=3)]
    assert find_clusters(same) == []


def test_same_place_weeks_apart_is_not_one_cluster():
    early = around(2, *CENTRE, km=0.1, days=(0, 1), seed=3, prefix="a")
    late = around(2, *CENTRE, km=0.1, days=(12, 13), seed=4, prefix="b")
    assert find_clusters(early + late, Params(min_people=3)) == []


def test_poisson_tail():
    assert poisson_tail(0, 2.0) == 1.0
    assert abs(poisson_tail(1, 2.0) - (1 - np.exp(-2))) < 1e-9
    assert poisson_tail(8, 0.5) < 1e-6


def test_syndromes():
    assert syndromes(["Fever", "cough"], {}) == {"febrile", "respiratory"}
    assert syndromes([], {"temperature_c": 38.4}) == {"febrile"}
    assert syndromes(["headache"], {"spo2": 97}) == set()
