from lib import ROOT, bullets, chain, chapter, files, flow, functions, h2, kpis, note, p, pre, qa, ref, table
from ml_b import MEASURED

BE, FE, ML = "backend/app/", "frontend/src/", "model/healthnexus_ml/"


def _loc(path: str) -> int:
    return len((ROOT / path).read_text(encoding="utf-8").split("\n"))


def _kb(path: str) -> str:
    return f"{(ROOT / path).stat().st_size / 1024:,.0f} KB"


def _tree() -> str:
    rows = [
        ("model/", "", "everything about the anomaly models"),
        ("  healthnexus_ml/", "", "the Python package"),
        ("    preprocessing.py", f"{_loc(ML + 'preprocessing.py')}", "cleans the LifeSnaps daily CSV"),
        ("    anomaly.py", f"{_loc(ML + 'anomaly.py')}", "the Isolation Forest class; research baselines"),
        ("    vitals.py", f"{_loc(ML + 'vitals.py')}", "the app's model: the two shared signals"),
        ("    train.py", f"{_loc(ML + 'train.py')}", "trains the models, writes artifacts/"),
        ("    evaluate.py", f"{_loc(ML + 'evaluate.py')}", "evaluates the scorer and forest, writes reports/"),
        ("    features.py", f"{_loc(ML + 'features.py')}", "symptoms and vitals to syndromes"),
        ("    clustering.py", f"{_loc(ML + 'clustering.py')}", "space-time DBSCAN and the Poisson test"),
        ("  artifacts/", "", "trained files"),
        ("    vitals_anomaly.joblib", _kb("model/artifacts/vitals_anomaly.joblib"), "THE MODEL THE API LOADS (in git)"),
        ("    vitals_anomaly.json", "", "its model card"),
        ("    global_anomaly.joblib", _kb("model/artifacts/global_anomaly.joblib"), "ten-signal research model (not in git)"),
        ("  notebooks/", "", "01 to 04: preprocessing, model, alert rule, scorer"),
        ("  reports/", "", "metrics JSON files and figures/*.png"),
        ("  data/", "", "LifeSnaps files and processed CSV (not in git)"),
        ("  tests/", "", "preprocessing, anomaly, clustering tests"),
        ("  pyproject.toml, uv.lock", "", "the package's environment (Python 3.12)"),
        ("backend/app/services/", "", "where the app uses it"),
        ("    scoring.py", f"{_loc(BE + 'services/scoring.py')}", "THE SCORER: baselines and the flag decision"),
        ("    population.py", f"{_loc(BE + 'services/population.py')}", "loads the forest, answers population checks"),
        ("    triage.py", f"{_loc(BE + 'services/triage.py')}", "severity bands and the plain-language signal"),
        ("    readings.py", f"{_loc(BE + 'services/readings.py')}", "stores a reading, scores it, writes the alert"),
        ("    metrics.py", f"{_loc(BE + 'services/metrics.py')}", "vitals vocabulary: bands, plausible ranges"),
        ("    outbreaks.py", f"{_loc(BE + 'services/outbreaks.py')}", "runs the clustering every 6 hours"),
    ]
    width = max(len(a) for a, _, _ in rows) + 2
    return "\n".join(f"{name.ljust(width)}{(size + ' ').rjust(8)} {what}" for name, size, what in rows)


def build() -> list[str]:
    out = []
    m = MEASURED

    out.append(chapter("10", "Folder structure and where the model lives", "c10", "The training code and the model file are in `model/`; the app code that uses them is in `backend/app/services`. The two meet at one file.", (
        h2("10.1 The folders (line counts and sizes are real)")
        + pre(_tree())
        + h2("10.2 Where the model lives, step by step")
        + table(["Question", "Answer"], [
            ["Which file is the trained model?", "`model/artifacts/vitals_anomaly.joblib` (" + _kb("model/artifacts/vitals_anomaly.joblib") + "). It is the only trained file tracked in git."],
            ["What is inside it?", "A plain dictionary: the two feature names, the population medians and scales, the **scikit-learn `IsolationForest`** (300 trees), the sorted training scores (for percentiles), the contamination, the version and training date. No custom classes, so the backend can load it without the model package."],
            ["Who loads it?", f"{ref(BE + 'services/population.py', 'def _bundle')}: `joblib.load`, cached with `lru_cache`, loaded **once** on the first reading after the server starts."],
            ["From which path?", f"{ref(BE + 'services/population.py', 'DEFAULT_PATH =')} (the repository's `model/artifacts` folder), or the `POPULATION_MODEL_PATH` setting if set."],
            ["Who calls it?", f"{ref(BE + 'services/scoring.py', 'population=population.check(vitals)')}: the last line of `score_reading`."],
            ["Where is its answer kept?", "In `processed_data.population` (JSON) beside the score, and shown by the page as the 'population check'."],
            ["What if the file is missing or will not load?", "The API logs it once and carries on: readings are scored by the rules and simply have no population check."],
            ["How is it rebuilt?", "`python -m healthnexus_ml.train` (needs the LifeSnaps files), then restart the API."],
        ])
        + note("**One sentence for the examiner:** *the model is a 1 MB scikit-learn file in `model/artifacts`, loaded by `backend/app/services/population.py` and called from `scoring.py` for every reading; the rules in `scoring.py` decide the flag.*", "key")
        + h2("10.3 What each file does")
        + files([
            (ML + "preprocessing.py", "def preprocess(", "Raw CSV in, clean per-person daily table out."),
            (ML + "anomaly.py", "class GlobalModel", "The forest, its standardising, percentile and score; `to_bundle` and `from_bundle`."),
            (ML + "anomaly.py", "def score_days", "The research scorer (global and personal blended, 2-day alert rule): used by the notebooks, not the app."),
            (ML + "vitals.py", "APP_FEATURES =", "The two signals shared with the app and the model version."),
            (ML + "train.py", "def main", "Trains both models and writes the model card."),
            (ML + "evaluate.py", "def main", "The evaluation that produced the report files."),
            (ML + "features.py", "SYNDROMES", "Symptoms to the three syndromes used by outbreak detection."),
            (ML + "clustering.py", "def find_clusters", "DBSCAN over space and time, and `poisson_tail`."),
            (BE + "services/scoring.py", "def score_reading", "The only function the app calls to judge a reading."),
            (BE + "services/population.py", "def check", "Percentile and score for a reading's heart rate and breathing rate."),
        ])
        + p("**Scratch files:** `model/data/processed/sample.csv`, `new.py` and similar files are your preprocessing experiments. Nothing in the pipeline reads them.")
        + p("**Environments:** the model package targets Python 3.12 (`model/.venv`); the API runs in its own environment with the **same scikit-learn version** (1.9.1) so the saved forest loads.")
    )))

    out.append(chapter("11", "Tech stack and response time", "c11", "What the ML side is built with, and how fast it is, measured on this machine.", (
        table(["Layer", "Technology", "Used for"], [
            ["Language", "Python 3.12 (model package), the API on its own Python", "All ML code"],
            ["Numerics and data", "numpy 2, pandas 2.2", "Cleaning, standardising, the research scoring"],
            ["Machine learning", "scikit-learn 1.9.1: `IsolationForest`, `DBSCAN`", "Population model; outbreak clustering"],
            ["Model storage", "joblib (compressed dict)", "`vitals_anomaly.joblib`"],
            ["Research", "JupyterLab, matplotlib", "Notebooks 01 to 04 and the figures"],
            ["Packaging", "hatchling, uv (`pyproject.toml`, `uv.lock`)", "Installing `healthnexus_ml` (also installed into the backend with `-e ../model`)"],
            ["Tests", "pytest", "Preprocessing, anomaly model, clustering"],
            ["Serving", "FastAPI + SQLAlchemy async + PostgreSQL", "Scoring runs inside the request that stores the reading"],
            ["Data", "LifeSnaps (CC BY 4.0), 71 people", "Training and evaluation"],
        ])
        + h2("11.1 Response time (measured)")
        + kpis([(f"{m['score_reading_with_population']['history_30']['median_ms']:g} ms", "score one reading, median (30 earlier readings)"), (f"{m['score_reading_with_population']['history_120']['median_ms']:g} ms", "with 120 earlier readings"),
                (f"{m['score_reading_rules_only']['median_ms']:g} ms", "the rules alone"), (f"{m['model_load_s']:g} s", "load the model file (once)"), (f"{m['model_file_kb']} KB", "model file size")])
        + table(["Step", "Median", "95th percentile", "Note"], [
            ["`score_reading` with the forest", f"{m['score_reading_with_population']['history_30']['median_ms']} ms", f"{m['score_reading_with_population']['history_30']['p95_ms']} ms", "30 earlier readings; the whole scoring of one reading"],
            ["`score_reading` with 120 earlier readings", f"{m['score_reading_with_population']['history_120']['median_ms']} ms", f"{m['score_reading_with_population']['history_120']['p95_ms']} ms", "The most history the app ever supplies"],
            ["`population.check` alone", f"{m['population_check']['median_ms']} ms", f"{m['population_check']['p95_ms']} ms", "Isolation Forest on one row of 300 trees"],
            ["`score_reading`, rules only", f"{m['score_reading_rules_only']['median_ms']} ms", f"{m['score_reading_rules_only']['p95_ms']} ms", "Personal baseline, blend, safety, confirmation"],
            ["Import scikit-learn and joblib", f"{m['sklearn_import_s']} s", "", "Once per server start"],
            ["`joblib.load` of the model", f"{m['model_load_s']} s", "", "Once per server start (cached)"],
        ])
        + bullets([
            f"Measured on {m['machine_note']}, {m['runs'] if 'runs' in m else 300} timings per row, on {m['measured_on']}.",
            "**The forest is about 99.5% of the scoring time.** The rules take about a tenth of a millisecond; scikit-learn's per-call overhead for predicting **one row** across 300 trees is the rest. It is still negligible next to a database round trip and a network request.",
            "**The first reading after a server start is slower**: importing scikit-learn (about 3 s) and loading the model (under 1 s), once. In one cold measurement it took about 15 s. A start-up warm-up call would remove this from the first user's request (an easy improvement, not yet done).",
            "Nothing here is a bottleneck for four smartwatch readings a day per citizen; scoring happens synchronously in the request that stores the reading.",
        ])
        + qa([
            ("Is 29 ms fast enough?", "Yes. A reading is stored and scored in one request, a person sends a few a day, and 29 ms is small next to the database and network time. If volume grew, the first step would be scoring several readings per call or dropping the forest from the hot path, since it never decides a flag."),
            ("Why is the first call slow?", "The scikit-learn import and the model load are lazy (`lru_cache`), so they happen on the first reading after a start. A warm-up call at start-up would hide it."),
        ])
    )))

    out.append(chapter("12", "Defence Q&A", "c12", "Short answers to the questions a technical examiner is most likely to ask about the ML.", (
        qa([
            ("Is this really machine learning, or just rules?", "Both, and each is used where it fits. There is a trained, unsupervised model (an Isolation Forest on 4,432 days from 71 people) and a statistical learning layer that estimates each person's own baseline from their own data. The flag decision is deliberately the explainable layer, because a health worker needs 'oxygen saturation 89%, well below the normal range', not a score."),
            ("Why an Isolation Forest?", "There are no labels, so the model has to be unsupervised. It handles several signals together, is fast, needs no distribution assumption, and isolates unusual points in fewer random splits."),
            ("Why not a deep model such as an LSTM?", "71 people and four months of data with no labels is far too little, and a deep model would not be able to explain a flag. The research showed the simple personal baseline already reaches AUC 0.90 on injected episodes."),
            ("How can you claim it works with no labelled illness?", "I do not claim accuracy on real illness. I measured two things honestly: false flags on ordinary days (1.5%, down from 24.6%) and detection of **injected** illness-like episodes (98% of strong, 68% of moderate for people with history). The limits are written down."),
            ("Were the thresholds tuned on the test data?", "The forest was tested on 15 people it never saw. The scorer's constants (1.5 and 0.5) were chosen with a grid over the same 71-person data, so the reported numbers are somewhat optimistic. A truly held-out set, or real worker feedback, is the next step."),
            ("Why does the Isolation Forest not flag?", "I tested it. At three thresholds it added no detection on 15 held-out people, because a population model mostly learns who a person is, and most readings it calls unusual are ordinary for that person. It is shown as context only."),
            ("What does contamination 0.03 mean?", "I expect about 3% of days to be unusual. It sets the cut for 'score 0.5 means more unusual than 97% of training days'."),
            ("How is a brand-new user protected?", "With fewer than 7 readings only the published normal range applies, so a clearly abnormal reading still flags; 3.5% of normal readings flag in that stage, against 24.6% before."),
            ("Does the model learn from users' data?", "The forest is trained once and never updated by users. Each person's baseline is computed on demand from their own readings and is not shared, so no one's data trains a model another person is scored by."),
            ("What happens if the model file is missing?", "Scoring continues with the rules; readings just carry no population check. This is tested by design: the check returns `None`."),
            ("Why pin scikit-learn at 1.9.1?", "A saved forest is a pickled object; loading it in a different scikit-learn version can fail or change behaviour. The model card records the version it was trained with."),
            ("What would you improve first?", "Use workers' 'false alarm' dismissals as weak labels to tune thresholds; validate on real wearable and spot-reading data; a meal-aware glucose band; warm the model up at start-up; per-vital tuning where real data exists."),
            ("What is the privacy position?", "Training data is the public, anonymised LifeSnaps set (CC BY 4.0). No citizen's readings are used to train anything. Area-level outbreak views count only people who opted in, and never a group under three."),
        ])
    )))
    return out
