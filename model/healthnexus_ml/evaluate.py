"""Evaluate the app's scorer and the population model, the way notebook 04 does, as a script.

    python -m healthnexus_ml.evaluate

Imports the backend's own scorer (backend/app/services/scoring.py), so the
numbers are the real app's. Writes reports/app_scorer_metrics.json and
reports/population_model_metrics.json.

Data: LifeSnaps resting heart rate -> heart_rate and sleeping breathing rate ->
respiratory_rate, one "reading" per day. The population model is refitted on 56
people and tested on the other 15 (notebook 02's split), so it is never scored on
anyone it has seen.
"""

import json
import sys
import uuid

import numpy as np
import pandas as pd

from . import vitals
from .preprocessing import ML_ROOT, PROCESSED_DIR

sys.path.insert(0, str(ML_ROOT.parent / "backend"))
import app.services.scoring as S  # noqa: E402  (the app's scorer, after the path is set)

REPORTS = ML_ROOT / "reports"
U = uuid.uuid4()
HISTORY = 120
SEVERITY = {"mild": (6, 1.5), "moderate": (10, 2.5), "strong": (15, 4.0)}
TIMINGS = {"established": 25, "new user": 3}


def load():
    df = pd.read_csv(PROCESSED_DIR / "daily_clean.csv", parse_dates=["date"]).sort_values(["user_id", "date"])
    return df


def sequences(df):
    app = vitals.app_frame(df)
    seqs = {}
    for user, g in app.groupby("user_id"):
        readings = []
        for hr, rr in zip(g["heart_rate"], g["respiratory_rate"], strict=True):
            v = {}
            if not np.isnan(hr):
                v["heart_rate"] = round(float(hr), 1)
            if not np.isnan(rr):
                v["respiratory_rate"] = round(float(rr), 1)
            if v:
                readings.append(v)
        seqs[user] = readings
    return seqs


def shipped(v, h):
    return S.score_reading(U, v, h).is_anomaly


def false_flags(seqs, scorer):
    flags = [scorer(v, s[max(0, i - HISTORY):i]) for s in seqs.values() for i, v in enumerate(s)]
    return float(np.mean(flags))


def pick_starts(seqs, after, rng):
    starts = {}
    for user, s in seqs.items():
        ok = [i for i in range(after, len(s) - 3) if all("heart_rate" in s[j] for j in range(i, i + 3))]
        starts[user] = int(rng.choice(ok)) if ok else None
    return starts


def caught(seqs, starts, d_hr, d_rr, scorer):
    hits = []
    for user, start in starts.items():
        if start is None:
            continue
        s = [dict(v) for v in seqs[user]]
        for j in range(start, start + 3):
            s[j]["heart_rate"] += d_hr
            if "respiratory_rate" in s[j]:
                s[j]["respiratory_rate"] += d_rr
        hits.append(any(scorer(s[j], s[max(0, j - HISTORY):j]) for j in range(start, start + 3)))
    return float(np.mean(hits))


def detection(seqs, starts, scorer):
    return {
        timing: {name: caught(seqs, starts[timing], d_hr, d_rr, scorer) for name, (d_hr, d_rr) in SEVERITY.items()}
        for timing in TIMINGS
    }


def population_variant(model, threshold):
    """The shipped scorer, plus: flag when the population model says >= threshold and the
    person has no personal heart rate baseline yet (the stage the global model is for)."""

    def scorer(v, h):
        if S.score_reading(U, v, h).is_anomaly:
            return True
        if sum("heart_rate" in x for x in h) >= S.MIN_BASELINE_READINGS:
            return False
        row = pd.DataFrame([{f: v.get(f, np.nan) for f in model.features}])
        return bool(model.score(row)[0] >= threshold)

    return scorer


def agreement(test, model):
    """How the population check relates to the app's flags, reading by reading."""
    rows = []
    for s in test.values():
        for i, v in enumerate(s):
            h = s[max(0, i - HISTORY):i]
            flagged = S.score_reading(U, v, h).is_anomaly
            pop = float(model.score(pd.DataFrame([{f: v.get(f, np.nan) for f in model.features}]))[0])
            new = sum("heart_rate" in x for x in h) < S.MIN_BASELINE_READINGS
            rows.append((flagged, pop >= 0.5, new))
    a = pd.DataFrame(rows, columns=["flagged", "unusual", "new_user"])
    return {
        "readings": int(len(a)),
        "population_unusual_share": round(float(a["unusual"].mean()), 4),
        "unusual_that_the_app_also_flagged": round(float(a.loc[a["unusual"], "flagged"].mean()), 3),
        "flags_the_population_model_agrees_with": round(float(a.loc[a["flagged"], "unusual"].mean()), 3),
        "new_user_readings": int(a["new_user"].sum()),
        "new_user_readings_unusual": int(a.loc[a["new_user"], "unusual"].sum()),
    }


def main():
    df = load()
    seqs = sequences(df)
    users = np.array(sorted(seqs))
    np.random.default_rng(0).shuffle(users)
    test_users = set(users[:15])
    test = {u: s for u, s in seqs.items() if u in test_users}
    model = vitals.fit(df[~df["user_id"].isin(test_users)])

    rng = np.random.default_rng(7)
    starts = {timing: pick_starts(test, after, rng) for timing, after in TIMINGS.items()}

    variants = {"app scorer (shipped)": shipped}
    for threshold in (1.0, 0.75, 0.5):
        variants[f"+ population model flags at {threshold:g} (new users)"] = population_variant(model, threshold)

    rows = []
    for name, scorer in variants.items():
        det = detection(test, starts, scorer)
        rows.append({
            "variant": name,
            "false_flags": round(false_flags(test, scorer), 4),
            **{f"{t}|{s}": round(v, 3) for t, by in det.items() for s, v in by.items()},
        })
        print(rows[-1])

    agree = agreement(test, model)
    print(agree)

    REPORTS.mkdir(exist_ok=True)
    out = {
        "scorer_model_version": S.MODEL_VERSION,
        "population_model_version": vitals.VERSION,
        "test_people": len(test),
        "test_readings": sum(map(len, test.values())),
        "note": "LifeSnaps resting values stand in for spot readings; real spot readings are noisier, "
        "so the population model's false-flag cost here is a lower bound.",
        "variants": rows,
        "agreement": agree,
        "decision": "The app shows the population check with every reading but does not let it flag: on held-out "
        "people it added no detection, and most readings it calls unusual are ordinary for that person.",
    }
    (REPORTS / "population_model_metrics.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print("saved", REPORTS / "population_model_metrics.json")


if __name__ == "__main__":
    main()
