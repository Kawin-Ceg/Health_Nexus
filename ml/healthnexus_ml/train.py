"""Train the global anomaly model on the cleaned data and save it."""

import joblib
import pandas as pd

from .anomaly import GlobalModel
from .preprocessing import ML_ROOT, PROCESSED_DIR

MODEL_PATH = ML_ROOT / "models" / "global_anomaly.joblib"


def main():
    df = pd.read_csv(PROCESSED_DIR / "daily_clean.csv", parse_dates=["date"])
    model = GlobalModel().fit(df)
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"trained on {len(df)} days from {df['user_id'].nunique()} users -> {MODEL_PATH}")


if __name__ == "__main__":
    main()
