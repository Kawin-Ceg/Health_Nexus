"""Preprocessing for the LifeSnaps (RAIS) daily Fitbit data.

Turns the raw daily CSV into a clean per-user, per-day table that the
anomaly models can use. See notebooks/01_preprocessing.ipynb for the
reasoning behind each step.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ML_ROOT = Path(__file__).resolve().parent.parent
RAW_DAILY = ML_ROOT / "data" / "rais_anonymized" / "csv_rais_anonymized" / "daily_fitbit_sema_df_unprocessed.csv"
PROCESSED_DIR = ML_ROOT / "data" / "processed"

# signals we use for anomaly detection (raw column -> our name)
FEATURES = {
    "resting_hr": "resting_hr",
    "rmssd": "hrv_rmssd",
    "nremhr": "sleep_hr",
    "full_sleep_breathing_rate": "breathing_rate",
    "nightly_temperature": "skin_temp",
    "minutesAsleep": "sleep_minutes",
    "sleep_efficiency": "sleep_efficiency",
    "steps": "steps",
    "very_active_minutes": "very_active_minutes",
    "sedentary_minutes": "sedentary_minutes",
}

# self-reported mood columns, kept only for sanity checking the model later
MOOD_COLS = ["ALERT", "HAPPY", "NEUTRAL", "RESTED/RELAXED", "SAD", "TENSE/ANXIOUS", "TIRED"]

# physiologically plausible ranges, anything outside is treated as a sensor error
VALID_RANGES = {
    "resting_hr": (30, 120),
    "hrv_rmssd": (5, 200),
    "sleep_hr": (30, 120),
    "breathing_rate": (6, 30),
    "skin_temp": (30, 38),
    "sleep_minutes": (120, 900),
    "sleep_efficiency": (50, 100),
    "steps": (0, 60000),
    "very_active_minutes": (0, 600),
    "sedentary_minutes": (0, 1440),
}

SLEEP_COLS = ["sleep_minutes", "sleep_efficiency", "hrv_rmssd", "sleep_hr", "breathing_rate", "skin_temp"]


def load_daily(path=RAW_DAILY):
    df = pd.read_csv(path, low_memory=False)
    return df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])


def select_columns(df):
    cols = ["id", "date", *FEATURES, *[c for c in MOOD_COLS if c in df.columns]]
    out = df[cols].rename(columns={**FEATURES, "id": "user_id"}).copy()
    out["date"] = pd.to_datetime(out["date"])
    for c in MOOD_COLS:
        if c in out.columns:
            out[c] = out[c].fillna(0).astype(int)
    return out


def drop_nonwear_days(df):
    """A day with 1440 sedentary minutes and no steps/HR means the watch wasn't worn."""
    no_activity = (df["sedentary_minutes"] >= 1440) | df["sedentary_minutes"].isna()
    no_signal = df["steps"].fillna(0).eq(0) & df["resting_hr"].isna()
    return df[~(no_activity & no_signal)].copy()


def mask_invalid_values(df):
    df = df.copy()
    for col, (lo, hi) in VALID_RANGES.items():
        df.loc[(df[col] < lo) | (df[col] > hi), col] = np.nan
    # a "sleep" shorter than 2h is usually a nap or a bad recording,
    # so the overnight readings from it aren't comparable to a real night
    short_sleep = df["sleep_minutes"].isna()
    df.loc[short_sleep, SLEEP_COLS] = np.nan
    # 1440 sedentary minutes on a day we kept = no data, not a lazy day
    df.loc[df["sedentary_minutes"] >= 1440, "sedentary_minutes"] = np.nan
    return df


def add_history_columns(df):
    """Per-user counters used later to decide global vs personal baseline."""
    df = df.sort_values(["user_id", "date"]).reset_index(drop=True)
    g = df.groupby("user_id")
    df["day_index"] = g.cumcount() + 1
    df["days_since_start"] = (df["date"] - g["date"].transform("min")).dt.days
    for col in FEATURES.values():
        df[f"{col}_n_obs"] = g[col].transform(lambda s: s.notna().cumsum())
    return df


def preprocess(path=RAW_DAILY):
    df = load_daily(path)
    df = select_columns(df)
    df = drop_nonwear_days(df)
    df = mask_invalid_values(df)
    df = df.dropna(subset=list(FEATURES.values()), how="all")
    return add_history_columns(df)


def save(df, name="daily_clean.csv"):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / name
    df.to_csv(out, index=False)
    return out


if __name__ == "__main__":
    clean = preprocess()
    print(f"saved {len(clean)} rows, {clean['user_id'].nunique()} users -> {save(clean)}")
