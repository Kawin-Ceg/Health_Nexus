"""Measures the scorer and the population model on this machine and writes measurements.json.

    cd backend && python ../docs/ml_guide/measure.py
"""

import json
import os
import statistics as st
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def timeit(fn, n=300):
    xs = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        xs.append((time.perf_counter() - t) * 1000)
    xs.sort()
    return {"median_ms": round(st.median(xs), 1), "p95_ms": round(xs[int(0.95 * len(xs))], 1), "runs": n}


t = time.perf_counter()
import sklearn.ensemble  # noqa: E402,F401
import joblib  # noqa: E402,F401

import_s = round(time.perf_counter() - t, 2)

import app.services.scoring as S  # noqa: E402
from app.services import population  # noqa: E402

t = time.perf_counter()
bundle = population._bundle()
load_s = round(time.perf_counter() - t, 2)
forest = bundle["forest"]
history = [{"heart_rate": 72 + (i % 5), "spo2": 97, "respiratory_rate": 15, "temperature_c": 36.6, "systolic": 118, "diastolic": 76} for i in range(30)]
reading = {"heart_rate": 74, "spo2": 97, "respiratory_rate": 15, "temperature_c": 36.7, "systolic": 119, "diastolic": 77}
who = uuid.uuid4()

with_pop = {
    "history_30": timeit(lambda: S.score_reading(who, reading, history)),
    "history_120": timeit(lambda: S.score_reading(who, reading, history * 4)),
}
check = timeit(lambda: population.check(reading))
population.check = lambda v: None
rules_only = timeit(lambda: S.score_reading(who, reading, history))

out = {
    "measured_on": time.strftime("%Y-%m-%d"),
    "machine_note": "a developer laptop running Windows, one request at a time, scikit-learn 1.9.1",
    "sklearn_import_s": import_s,
    "model_load_s": load_s,
    "model_file_kb": os.path.getsize(population._configured_path()) // 1024,
    "forest": {"n_estimators": forest.n_estimators, "max_samples": int(forest.max_samples_), "contamination": bundle["contamination"], "version": bundle["version"]},
    "score_reading_with_population": with_pop,
    "population_check": check,
    "score_reading_rules_only": rules_only,
}
(HERE / "measurements.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
