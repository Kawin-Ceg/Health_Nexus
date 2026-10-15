"""The population model the app runs on every reading (backend/app/services/population.py).

App readings are spot vitals (blood pressure, heart rate, temperature...), not
daily Fitbit summaries, so the ten-signal wearable model cannot score them. Two
LifeSnaps signals do match app vitals, the same mapping notebook 04 uses:

    resting_hr      -> heart_rate
    breathing_rate  -> respiratory_rate

This is the wearable model's method (GlobalModel: an Isolation Forest on
median/MAD-standardised features) trained on just those two, so it answers "how
unusual is this heart rate and breathing rate, together, compared with 71
people's days?". A resting value is calmer than a spot reading, so the app uses
the answer as a population check next to its own scorer, never as a flag on its
own (evaluate.py measures what letting it flag would cost).
"""

import pandas as pd

from .anomaly import GlobalModel

APP_FEATURES = {"resting_hr": "heart_rate", "breathing_rate": "respiratory_rate"}
VERSION = "population-iforest-v1"


def app_frame(df: pd.DataFrame) -> pd.DataFrame:
    """The cleaned daily table with the two shared signals under their app names; days with neither dropped."""
    out = df[["user_id", "date", *APP_FEATURES]].rename(columns=APP_FEATURES)
    return out.dropna(subset=list(APP_FEATURES.values()), how="all")


def fit(df: pd.DataFrame) -> GlobalModel:
    return GlobalModel(features=list(APP_FEATURES.values())).fit(app_frame(df))
