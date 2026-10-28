"""Anomaly scoring: global Isolation Forest + per-user rolling baselines.

New users are scored by the global model only. As a user builds up valid
days for a signal, their own baseline takes over for that signal.
See notebooks/02_anomaly_model.ipynb.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .preprocessing import FEATURES

FEATS = list(FEATURES.values())
PHYSIO = ["resting_hr", "hrv_rmssd", "sleep_hr", "breathing_rate", "skin_temp"]

MIN_DAYS = 7
FULL_DAYS = 21
WINDOW = 60
FLAG_THRESHOLD = 0.5
ALERT_DAYS = 2

MAD_SCALE = 1.4826


def _mad(x):
    return np.nanmedian(np.abs(x - np.nanmedian(x)))


def z_to_score(z):
    """combined z of 1 -> 0, 2 -> 0.5 (flag), 3 -> 1."""
    return np.clip((z - 1) / 2, 0, 1)


class GlobalModel:
    """Isolation Forest trained on population-standardised features.

    `features` defaults to the ten wearable signals. The app's model uses the two
    signals its spot readings share with LifeSnaps (see vitals.py).
    """

    def __init__(self, contamination=0.03, random_state=42, features=None):
        self.contamination = contamination
        self.random_state = random_state
        self.features = list(features or FEATS)

    def fit(self, df):
        X = df[self.features]
        self.median_ = X.median()
        self.mad_ = X.apply(lambda s: _mad(s.to_numpy())) * MAD_SCALE
        Xs = self._standardise(X)
        self.forest_ = IsolationForest(
            n_estimators=300, contamination=self.contamination, random_state=self.random_state
        ).fit(Xs)
        self.train_scores_ = np.sort(-self.forest_.score_samples(Xs))
        return self

    def _standardise(self, X):
        return ((X - self.median_) / self.mad_).fillna(0).to_numpy()

    def population_z(self, df):
        return (df[self.features] - self.median_) / self.mad_

    def percentile(self, df):
        """Share of training days less unusual than each row (0..1)."""
        raw = -self.forest_.score_samples(self._standardise(df[self.features]))
        return np.searchsorted(self.train_scores_, raw) / len(self.train_scores_)

    def score(self, df):
        lo, hi = 1 - 2 * self.contamination, 1 - self.contamination / 6
        return np.clip((self.percentile(df) - lo) / (hi - lo), 0, 1)

    def to_bundle(self, **meta):
        """Plain numpy/sklearn objects only, so the backend can load it without this package."""
        return {
            "features": self.features,
            "median": self.median_.to_numpy(dtype=float),
            "scale": self.mad_.to_numpy(dtype=float),
            "forest": self.forest_,
            "train_scores": self.train_scores_,
            "contamination": self.contamination,
            **meta,
        }

    @classmethod
    def from_bundle(cls, bundle):
        model = cls(contamination=bundle["contamination"], features=bundle["features"])
        model.median_ = pd.Series(bundle["median"], index=model.features)
        model.mad_ = pd.Series(bundle["scale"], index=model.features)
        model.forest_ = bundle["forest"]
        model.train_scores_ = bundle["train_scores"]
        return model


def personal_baselines(df, pop_mad):
    """Rolling median/MAD per user and feature, using only previous days."""
    df = df.sort_values(["user_id", "date"])
    out = pd.DataFrame(index=df.index)
    for f in FEATS:
        g = df.groupby("user_id")[f]
        prev = g.transform(lambda s: s.shift(1))
        roll = prev.groupby(df["user_id"]).rolling(WINDOW, min_periods=1)
        med = roll.median().reset_index(level=0, drop=True)
        mad = roll.apply(_mad, raw=True).reset_index(level=0, drop=True) * MAD_SCALE
        out[f"{f}_base"] = med
        out[f"{f}_spread"] = mad.clip(lower=0.25 * pop_mad[f])
        out[f"{f}_n_prev"] = g.transform(lambda s: s.notna().cumsum().shift(1, fill_value=0))
    return out


def personal_weight(n_prev):
    return np.clip((n_prev - MIN_DAYS) / (FULL_DAYS - MIN_DAYS), 0, 1)


def score_days(df, model):
    """Score every day. Returns global, personal and blended scores plus the main reason."""
    df = df.sort_values(["user_id", "date"])
    base = personal_baselines(df, model.mad_)
    pop_z = model.population_z(df)

    z_personal = pd.DataFrame({f: (df[f] - base[f"{f}_base"]) / base[f"{f}_spread"] for f in FEATS})
    weights = pd.DataFrame({f: personal_weight(base[f"{f}_n_prev"]) for f in FEATS})
    weights = weights.where(df[FEATS].notna())

    z_blend = (1 - weights) * pop_z + weights * z_personal.fillna(0)

    out = df[["user_id", "date"]].copy()
    out["global_score"] = model.score(df)
    rms = np.sqrt((z_personal[PHYSIO] ** 2).mean(axis=1, skipna=True))
    out["personal_score"] = z_to_score(rms).fillna(0)
    out["personal_weight"] = weights[PHYSIO].mean(axis=1).fillna(0)
    out["score"] = (1 - out["personal_weight"]) * out["global_score"] + out["personal_weight"] * out["personal_score"]
    out["flag"] = out["score"] >= FLAG_THRESHOLD

    top = z_blend.abs().fillna(0)
    out["reason"] = top.idxmax(axis=1).where(top.max(axis=1) > 0)
    out["reason_z"] = z_blend.to_numpy()[np.arange(len(df)), top.to_numpy().argmax(axis=1)]

    out["alert"] = consecutive_flags(out) >= ALERT_DAYS
    return out


def consecutive_flags(scored):
    """Length of the current run of flagged days. A missing calendar day breaks the run."""
    new_run = (
        ~scored["flag"]
        | scored["user_id"].ne(scored["user_id"].shift())
        | scored["date"].diff().dt.days.ne(1)
    )
    run_id = new_run.cumsum()
    return scored["flag"].groupby(run_id).cumsum().where(scored["flag"], 0).astype(int)
