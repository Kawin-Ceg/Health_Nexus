"""Train both models on the cleaned data and save them to model/artifacts.

    python -m healthnexus_ml.preprocessing   # once: raw LifeSnaps CSV -> data/processed/daily_clean.csv
    python -m healthnexus_ml.train

- vitals_anomaly.joblib: the population model the app loads (vitals.py). Tracked in git.
- global_anomaly.joblib: the ten-signal wearable model from notebooks 02 and 03.

Both are saved as plain dicts of numpy arrays and a scikit-learn forest
(GlobalModel.to_bundle), so the backend can load them without this package.
"""

import json
from datetime import UTC, datetime

import joblib
import pandas as pd
import sklearn

from . import vitals
from .anomaly import GlobalModel
from .preprocessing import ML_ROOT, PROCESSED_DIR

ARTIFACTS = ML_ROOT / "artifacts"
MODEL_PATH = ARTIFACTS / "global_anomaly.joblib"
VITALS_MODEL_PATH = ARTIFACTS / "vitals_anomaly.joblib"


def _meta(df: pd.DataFrame, version: str) -> dict:
    return {
        "version": version,
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "trained_on_days": int(len(df)),
        "trained_on_people": int(df["user_id"].nunique()),
        "sklearn_version": sklearn.__version__,
        "data": "LifeSnaps (Yfantidou et al., 2022), CC BY 4.0",
    }


def main():
    df = pd.read_csv(PROCESSED_DIR / "daily_clean.csv", parse_dates=["date"])
    ARTIFACTS.mkdir(exist_ok=True)

    wearable = GlobalModel().fit(df)
    joblib.dump(wearable.to_bundle(**_meta(df, "wearable-iforest-v1")), MODEL_PATH)
    print(f"wearable model: {len(df)} days from {df['user_id'].nunique()} people -> {MODEL_PATH}")

    app_df = vitals.app_frame(df)
    model = vitals.fit(df)
    meta = _meta(app_df, vitals.VERSION)
    joblib.dump(model.to_bundle(**meta), VITALS_MODEL_PATH, compress=3)
    card = {
        **meta,
        "features": model.features,
        "median": dict(zip(model.features, model.median_.round(3).tolist(), strict=True)),
        "robust_sd": dict(zip(model.features, model.mad_.round(3).tolist(), strict=True)),
        "contamination": model.contamination,
        "score": "0.5 = more unusual than 97% of training days, 1.0 = more unusual than 99.5%",
    }
    VITALS_MODEL_PATH.with_suffix(".json").write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    print(f"app vitals model: {len(app_df)} days from {app_df['user_id'].nunique()} people -> {VITALS_MODEL_PATH}")


if __name__ == "__main__":
    main()
