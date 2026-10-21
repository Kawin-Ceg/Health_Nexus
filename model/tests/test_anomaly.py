import numpy as np
import pandas as pd
import pytest

from healthnexus_ml import anomaly as an
from healthnexus_ml.preprocessing import add_history_columns


def make_user(user_id, n, rhr, seed):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "user_id": user_id,
        "date": pd.date_range("2021-06-01", periods=n),
        "resting_hr": rhr + rng.normal(0, 1.5, n),
        "hrv_rmssd": 50 + rng.normal(0, 5, n),
        "sleep_hr": rhr - 3 + rng.normal(0, 1.5, n),
        "breathing_rate": 15 + rng.normal(0, 0.5, n),
        "skin_temp": 34 + rng.normal(0, 0.2, n),
        "sleep_minutes": 420 + rng.normal(0, 30, n),
        "sleep_efficiency": 92 + rng.normal(0, 2, n),
        "steps": 8000 + rng.normal(0, 2000, n),
        "very_active_minutes": 20 + rng.normal(0, 5, n).clip(-20),
        "sedentary_minutes": 700 + rng.normal(0, 60, n),
    })


@pytest.fixture(scope="module")
def population():
    users = [make_user(f"u{i}", 60, rhr, seed=i) for i, rhr in enumerate(np.linspace(52, 80, 20))]
    return add_history_columns(pd.concat(users, ignore_index=True))


@pytest.fixture(scope="module")
def model(population):
    return an.GlobalModel().fit(population)


def test_personal_weight_ramp():
    w = an.personal_weight(np.array([0, an.MIN_DAYS, 14, an.FULL_DAYS, 100]))
    assert w[0] == 0 and w[1] == 0
    assert 0 < w[2] < 1
    assert w[3] == 1 and w[4] == 1


def test_baseline_does_not_use_todays_value(population, model):
    user = population[population["user_id"] == "u0"].copy()
    before = an.personal_baselines(user, model.mad_)
    user.loc[user.index[30], "resting_hr"] = 200
    after = an.personal_baselines(user, model.mad_)
    # today's baseline is unchanged; only the following days see the new value
    assert before.loc[user.index[30], "resting_hr_base"] == after.loc[user.index[30], "resting_hr_base"]
    assert before["resting_hr_n_prev"].iloc[0] == 0


def test_consecutive_flags_break_on_gaps_and_users():
    s = pd.DataFrame({
        "user_id": ["a"] * 5 + ["b"] * 2,
        "date": pd.to_datetime(["2021-06-01", "2021-06-02", "2021-06-03", "2021-06-05", "2021-06-06",
                                "2021-06-07", "2021-06-08"]),
        "flag": [True, True, False, True, True, True, True],
    })
    # a: run of 2, break, gap on 06-04 so run restarts, b: new user so it restarts
    assert an.consecutive_flags(s).tolist() == [1, 2, 0, 1, 2, 1, 2]


def test_change_normal_for_population_is_caught_personally(population, model):
    # u0 has a low resting HR (~52). +10 bpm is still normal for the population,
    # but clearly off for them.
    user = population[population["user_id"] == "u0"].copy()
    clean = an.score_days(user, model)
    # inject after a day that isn't flagged, so any alert comes from the injection
    start = next(i for i in range(40, 58) if not clean["flag"].iloc[i - 1])
    days = user.index[start:start + 2]
    user.loc[days, ["resting_hr", "sleep_hr"]] += 10
    user.loc[days, "hrv_rmssd"] *= 0.6
    user.loc[days, "skin_temp"] += 1.0

    scored = an.score_days(user, model)
    assert scored.loc[days, "personal_weight"].eq(1).all()
    assert scored.loc[days, "flag"].all()
    assert scored.loc[days[1], "alert"]  # second day in a row -> alert
    assert not scored.loc[days[0], "alert"]
    assert scored.loc[days, "reason"].isin(an.FEATS).all()


def test_normal_days_rarely_flag(population, model):
    scored = an.score_days(population, model)
    assert scored["alert"].mean() < 0.05


def test_new_user_uses_global_model(model):
    new = add_history_columns(make_user("new", 3, 60, seed=99))
    scored = an.score_days(new, model)
    assert scored["personal_weight"].eq(0).all()
    assert np.allclose(scored["score"], scored["global_score"])


def test_bundle_round_trip_scores_the_same(model, population):
    again = an.GlobalModel.from_bundle(model.to_bundle(version="t"))
    assert np.allclose(again.score(population), model.score(population))
    assert set(model.to_bundle()) >= {"features", "median", "scale", "forest", "train_scores", "contamination"}


def test_vitals_model_uses_the_two_shared_signals(population):
    from healthnexus_ml import vitals

    m = vitals.fit(population)
    assert m.features == ["heart_rate", "respiratory_rate"]
    usual = pd.DataFrame({"heart_rate": [66.0], "respiratory_rate": [15.0]})
    odd = pd.DataFrame({"heart_rate": [115.0], "respiratory_rate": [26.0]})
    assert m.score(usual)[0] < 0.5 <= m.score(odd)[0]
