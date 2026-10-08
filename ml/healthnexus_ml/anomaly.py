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
# body signals used for the personal score. Activity (steps etc.) depends on what
# someone chose to do that day, so it is too noisy to alert on by itself.
PHYSIO = ["resting_hr", "hrv_rmssd", "sleep_hr", "breathing_rate", "skin_temp"]

MIN_DAYS = 7  # personal baseline starts counting after this many valid days
FULL_DAYS = 21  # fully personal from here
WINDOW = 60  # baseline looks at the user's last 60 valid days
FLAG_THRESHOLD = 0.5
ALERT_DAYS = 2  # only alert the user after this many flagged days in a row

MAD_SCALE = 1.4826  # makes MAD comparable to a standard deviation


def _mad(x):
    return np.nanmedian(np.abs(x - np.nanmedian(x)))


def z_to_score(z):
    """combined z of 1 -> 0, 2 -> 0.5 (flag), 3 -> 1."""
    return np.clip((z - 1) / 2, 0, 1)


class GlobalModel:
    """Isolation Forest trained on population-standardised features."""

    def __init__(self, contamination=0.03, random_state=42):
        self.contamination = contamination
        self.random_state = random_state

    def fit(self, df):
        X = df[FEATS]
        self.median_ = X.median()
        self.mad_ = X.apply(lambda s: _mad(s.to_numpy())) * MAD_SCALE
        Xs = self._standardise(X)
        self.forest_ = IsolationForest(
            n_estimators=300, contamination=self.contamination, random_state=self.random_state
        ).fit(Xs)
        # reference distribution of raw scores, used to turn a score into a percentile
        self.train_scores_ = np.sort(-self.forest_.score_samples(Xs))
        return self

    def _standardise(self, X):
        # missing values -> population median, i.e. "nothing unusual"
        return ((X - self.median_) / self.mad_).fillna(0).to_numpy()

    def population_z(self, df):
        return (df[FEATS] - self.median_) / self.mad_

    def score(self, df):
        raw = -self.forest_.score_samples(self._standardise(df[FEATS]))
        pct = np.searchsorted(self.train_scores_, raw) / len(self.train_scores_)
        # top 3% of training days -> 0.5, top 0.5% -> 1
        lo, hi = 1 - 2 * self.contamination, 1 - self.contamination / 6
        return np.clip((pct - lo) / (hi - lo), 0, 1)


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
        # floor so a very regular user doesn't get infinite z-scores
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
    weights = weights.where(df[FEATS].notna())  # only features measured today count

    # per feature: global z early on, personal z once there is history
    z_blend = (1 - weights) * pop_z + weights * z_personal.fillna(0)

    out = df[["user_id", "date"]].copy()
    out["global_score"] = model.score(df)
    # root-mean-square over the body signals measured today: one signal slightly off
    # doesn't flag, several off together (like getting sick) does
    rms = np.sqrt((z_personal[PHYSIO] ** 2).mean(axis=1, skipna=True))
    out["personal_score"] = z_to_score(rms).fillna(0)
    out["personal_weight"] = weights[PHYSIO].mean(axis=1).fillna(0)
    out["score"] = (1 - out["personal_weight"]) * out["global_score"] + out["personal_weight"] * out["personal_score"]
    out["flag"] = out["score"] >= FLAG_THRESHOLD

    # which signal is most off, so the app can say *why* a day was flagged
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
