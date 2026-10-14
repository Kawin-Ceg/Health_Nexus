import numpy as np
import pandas as pd

from healthnexus_ml import preprocessing as pp


def make_days(n=5, **overrides):
    df = pd.DataFrame({
        "user_id": "u1",
        "date": pd.date_range("2021-06-01", periods=n),
        "resting_hr": 60.0,
        "hrv_rmssd": 50.0,
        "sleep_hr": 55.0,
        "breathing_rate": 15.0,
        "skin_temp": 34.0,
        "sleep_minutes": 420.0,
        "sleep_efficiency": 92.0,
        "steps": 8000.0,
        "very_active_minutes": 20.0,
        "sedentary_minutes": 700.0,
    })
    for col, val in overrides.items():
        df[col] = val
    return df


def test_nonwear_day_is_dropped():
    df = make_days(3)
    df.loc[1, ["sedentary_minutes", "steps", "resting_hr"]] = [1440, 0, np.nan]
    out = pp.drop_nonwear_days(df)
    assert len(out) == 2
    assert df.loc[1, "date"] not in out["date"].values


def test_fully_sedentary_day_with_signal_is_kept():
    df = make_days(3)
    df.loc[1, "sedentary_minutes"] = 1440  # still has steps and HR
    assert len(pp.drop_nonwear_days(df)) == 3


def test_impossible_values_become_nan():
    df = make_days(3)
    df.loc[0, "resting_hr"] = 250
    df.loc[1, "breathing_rate"] = 2
    out = pp.mask_invalid_values(df)
    assert np.isnan(out.loc[0, "resting_hr"])
    assert np.isnan(out.loc[1, "breathing_rate"])
    assert out.loc[2, "resting_hr"] == 60


def test_short_sleep_clears_overnight_values():
    df = make_days(2)
    df.loc[0, "sleep_minutes"] = 60
    out = pp.mask_invalid_values(df)
    assert out.loc[0, pp.SLEEP_COLS].isna().all()
    assert out.loc[0, "resting_hr"] == 60  # not a sleep value, untouched
    assert out.loc[1, pp.SLEEP_COLS].notna().all()


def test_history_counts_are_per_user_and_cumulative():
    a = make_days(3)
    b = make_days(2, user_id="u2")
    a.loc[1, "hrv_rmssd"] = np.nan
    out = pp.add_history_columns(pd.concat([a, b], ignore_index=True))
    u1 = out[out["user_id"] == "u1"]
    u2 = out[out["user_id"] == "u2"]
    assert u1["day_index"].tolist() == [1, 2, 3]
    assert u1["hrv_rmssd_n_obs"].tolist() == [1, 1, 2]
    assert u2["hrv_rmssd_n_obs"].tolist() == [1, 2]
