# HealthNexus model

Everything about the anomaly model lives here: the code, how it is trained, how it is evaluated, and the trained files the app loads. The notebooks are the research write-up; every step they run is also a plain Python module, so nothing depends on opening a notebook.

## What is in here

| Path | What it is |
|---|---|
| `healthnexus_ml/preprocessing.py` | Cleans the raw LifeSnaps daily Fitbit CSV into `data/processed/daily_clean.csv` (non-wear days, impossible values, history counters). |
| `healthnexus_ml/anomaly.py` | The method: `GlobalModel` (an Isolation Forest on median/MAD-standardised features) plus per-person rolling baselines and the 2-day alert rule. |
| `healthnexus_ml/vitals.py` | The **app's** model: the same `GlobalModel`, trained on the two LifeSnaps signals that match app vitals (resting heart rate → `heart_rate`, breathing rate → `respiratory_rate`). |
| `healthnexus_ml/train.py` | Trains both models and writes them to `artifacts/`. |
| `healthnexus_ml/evaluate.py` | Evaluates the app's scorer and the population model (the notebook 04 method, as a script). Writes `reports/population_model_metrics.json`. |
| `healthnexus_ml/features.py` | Maps a reading's symptoms and vitals to syndromes: febrile, respiratory, gastrointestinal. |
| `healthnexus_ml/clustering.py` | Outbreak detection: space-time DBSCAN over symptomatic cases and a Poisson test against the area's baseline. |
| `artifacts/vitals_anomaly.joblib` | The trained model the API loads. Tracked in git. `vitals_anomaly.json` is its model card. |
| `artifacts/global_anomaly.joblib` | The ten-signal wearable model from notebooks 02 and 03. Rebuilt by `train.py`, not tracked. |
| `notebooks/01`–`04` | Preprocessing, anomaly model, alert rule, app scorer evaluation. |
| `tests/` | `pytest` for preprocessing, the model and the saved bundle. |

## How the app uses it

On every reading, the API (`backend/app/services/scoring.py`) does two things:

1. **Flags or not**, with the rules this research produced: published normal ranges for new users, a personal baseline (median and MAD of their last 30 readings) blended in between 7 and 21 readings, safety limits that always count, and a second unusual reading needed before an in-range change flags.
2. **Runs the trained population model** (`backend/app/services/population.py` loads `artifacts/vitals_anomaly.joblib`) on the reading's heart rate and breathing rate. The answer is stored with the score (`processed_data.population`) and shown to the citizen and their health worker as a "population check".

The population model never flags a reading on its own. `evaluate.py` tested letting it flag new users at three thresholds: on 15 held-out people it caught nothing extra. Most readings it calls unusual are ordinary *for that person* (notebook 02 found the same: a population model mostly learns "who is this person"). Letting it flag would mainly add false alarms.

The artifact is a plain dict of numpy arrays and a scikit-learn forest, so the backend needs scikit-learn (same version as `vitals_anomaly.json` says) but not this package. If the file is missing, readings are still scored, just without the population check.

## Outbreak clustering

`backend/app/services/outbreaks.py` runs every 6 hours over the last 14 days of readings from citizens who allowed community monitoring:

1. Each reading is mapped to the syndromes it points to (a fever symptom or a temperature of 38 °C or more is febrile, and so on).
2. Per syndrome, each person counts once, at their first onset in the window.
3. Cases are projected to kilometres, with time as a third axis (one day = 0.5 km), and clustered with DBSCAN: `eps` 1.5 km, `min_samples` 3. Three is also the smallest group any community figure in the app shows, so a cluster can never point at one or two people.
4. Each cluster is compared with the same area over the previous 8 weeks. If that many people would be unlikely by chance (Poisson, p < 0.01, with at least 0.5 cases expected), it is flagged as a possible outbreak; otherwise it is shown as one to watch.

Health workers see clusters that include their centre's citizens and can turn one into an advisory. `python -m app.seeds.seed_outbreak` seeds a demo fever cluster.

## Rebuild

Needs the LifeSnaps data (CC BY 4.0) in `data/rais_anonymized/`.

```bash
cd model
uv sync                                   # or: pip install -e . pytest
python -m healthnexus_ml.preprocessing    # raw CSV -> data/processed/daily_clean.csv
python -m healthnexus_ml.train            # -> artifacts/
python -m healthnexus_ml.evaluate         # -> reports/population_model_metrics.json (a few minutes)
python -m pytest tests
```

Restart the API after retraining; it loads the model once.
