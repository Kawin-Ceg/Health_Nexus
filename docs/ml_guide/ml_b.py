import json
import uuid

from lib import ROOT, bullets, chain, chapter, files, flow, functions, h2, note, p, pre, qa, ref, table
from ml_a import S, score_rules

from app.services import population
from app.services.triage import BANDS, alert_severity, describe_signal, severity_of
from healthnexus_ml.clustering import Params

BE, ML = "backend/app/", "model/healthnexus_ml/"
REPORT = json.loads((ROOT / "model/reports/app_scorer_metrics.json").read_text(encoding="utf-8"))
POP_REPORT = json.loads((ROOT / "model/reports/population_model_metrics.json").read_text(encoding="utf-8"))
MEASURED = json.loads((ROOT / "docs/ml_guide/measurements.json").read_text(encoding="utf-8"))


def _severity_examples() -> str:
    cases = [
        ("Oxygen saturation 96%", {"spo2": 96}), ("Oxygen saturation 92%", {"spo2": 92}), ("Oxygen saturation 89%", {"spo2": 89}), ("Oxygen saturation 85%", {"spo2": 85}),
        ("Temperature 37.5 °C", {"temperature_c": 37.5}), ("Temperature 38.0 °C", {"temperature_c": 38.0}), ("Temperature 38.4 °C", {"temperature_c": 38.4}), ("Temperature 39.3 °C", {"temperature_c": 39.3}),
        ("Heart rate 105 bpm", {"heart_rate": 105}), ("Heart rate 125 bpm", {"heart_rate": 125}), ("Heart rate 150 bpm", {"heart_rate": 150}),
        ("Blood pressure 130/85", {"systolic": 130, "diastolic": 85}), ("Blood pressure 145/92", {"systolic": 145, "diastolic": 92}),
        ("Blood pressure 167/103", {"systolic": 167, "diastolic": 103}), ("Blood pressure 190/120", {"systolic": 190, "diastolic": 120}),
        ("Breathing rate 22 /min", {"respiratory_rate": 22}), ("Breathing rate 27 /min", {"respiratory_rate": 27}),
    ]
    uid = uuid.uuid4()
    rows = []
    for name, vitals in cases:
        r = score_rules(uid, vitals, [])
        peak = max(r.features.values(), default=0.0)
        if r.is_anomaly:
            sev = severity_of(r.anomaly_score)
            rows.append([name, f"{peak:.2f}", f"{r.anomaly_score:.3f}", f"**{sev}**", alert_severity(sev).value])
        else:
            rows.append([name, "below 0.5", "0", "not flagged", "none"])
    return table(["A new person's reading", "Strongest contribution", "anomaly_score = min(1, c ÷ 4)", "Severity", "Citizen's alert level"], rows)


def _population_examples() -> str:
    rows = []
    for label, vitals in [("typical resting person", {"heart_rate": 68, "respiratory_rate": 15}), ("fast and breathing hard", {"heart_rate": 112, "respiratory_rate": 24}),
                          ("very fast and breathing very hard", {"heart_rate": 150, "respiratory_rate": 32}), ("heart rate only, 58 bpm", {"heart_rate": 58})]:
        c = population.check(vitals)
        rows.append([label, ", ".join(f"{k.replace('_', ' ')} {v:g}" for k, v in vitals.items()), f"{c.percentile * 100:.1f}%", f"{c.score:.2f}", "yes" if c.unusual else "no"])
    return table(["Example", "Input", "Percentile of the 4,432 training days", "Population score", "'Unusual' (score 0.5 or more)"], rows)


def build() -> list[str]:
    out = []

    out.append(chapter("4", "Constraints on the data, and the good answers", "c4", "Every rule that limits what data the model sees, with the reason for it. Each reason is the answer to give if asked 'why?'.", (
        h2("4.1 Cleaning the research data (preprocessing.py)")
        + table(["Constraint", "Value", "The good answer (why)"], [
            ["Drop 'non-wear' days", "1440 sedentary minutes **and** no steps **and** no resting heart rate", "Fitbit records exactly 1440 when the watch is off. Left in, the model would learn that '0 steps' is normal and miss real drops."],
            ["Impossible values become missing (not deleted)", "resting HR 30 to 120 · HRV 5 to 200 · sleeping HR 30 to 120 · breathing 6 to 30 · skin temp 30 to 38 · steps 0 to 60,000", "Sensors glitch. The rest of the day may still be fine, so only the value is blanked. The ranges are wide **on purpose**: they catch broken sensors, not real unusual readings, which are exactly what the model must find."],
            ["Sleep under 2 hours clears the overnight signals", "`sleep_minutes` below 120 → HRV, sleep HR, breathing, skin temp become missing", "A nap or a recording that cut out is not comparable with a full night."],
            ["1440 sedentary minutes on a kept day means no data", "set to missing", "It is not a lazy day; it is the watch being off."],
            ["Per-person history counters", "`day_index`, and for each signal a running count of valid values, **up to and including** that day", "Lets the model know how much history exists on each day, with **no look into the future** (no leakage)."],
            ["Split by **person**, not by day", "56 people to train, 15 to test", "If days were split, the model would already have seen the test people's other days and look better than it is for a brand-new user."],
            ["Personal baseline uses earlier days only", "`shift(1)` then a rolling window", "The day being scored must not be part of its own baseline."],
            ["Robust standardising", "population median and MAD × 1.4826; missing → 0", "The data has outliers. Missing → 0 means 'same as the median person', because a forest cannot take empty values and half the days have no HRV."],
        ])
        + files([
            (ML + "preprocessing.py", "VALID_RANGES = {", "The plausible ranges."),
            (ML + "preprocessing.py", "def drop_nonwear_days", "Non-wear rule."),
            (ML + "preprocessing.py", "def mask_invalid_values", "Impossible values and the short-sleep rule."),
            (ML + "preprocessing.py", "def add_history_columns", "The per-person counters."),
        ])
        + h2("4.2 What the app accepts as input")
        + table(["Constraint", "Value", "The good answer (why)"], [
            ["Plausible range per vital", "e.g. SpO₂ 50 to 100, heart rate 25 to 250, temperature 30 to 45 °C", "Outside it a value is a **typo, not an anomaly**: the form says 'check for a typo' instead of raising a false alarm."],
            ["Unknown measurements rejected; at least one required", "`VitalsIn` validator", "Nothing the scorer does not understand can be stored."],
            ["Systolic must be above diastolic", "`_pressure_order`", "A swapped pair is a data-entry error."],
            ["Symptoms", "at most 12, duplicates removed", "Keeps a record readable and bounded."],
            ["Time of measurement", "not in the future (5 minutes' tolerance), at most 30 days back", "A reading from long ago would distort the baseline order; the real storage time is kept separately in `created_at`."],
            ["Examination needs a place", "2 to 160 characters", "A worker's measurement must say where it was taken."],
            ["Health-tracking consent", "off → no reading is stored", "A person who turned tracking off must not have readings created for them."],
            ["Only the citizen's **own** history", "`earlier_vitals` filters on the user id", "A baseline must be personal; another person's data never enters."],
            ["History available to the scorer", "latest 120 readings; baseline from the latest 30; at least 7 to start", "Bounds the work per reading; below 7 readings a baseline would be a guess, so none is used ('no baseline is better than a fake one')."],
            ["Watch simulator limits", "heart rate 40 to 180, SpO₂ 85 to 100, breathing 8 to 35, temperature 34.5 to 41", "Simulated values stay physiologically possible."],
        ])
        + files([
            (BE + "schemas/health.py", "class VitalsIn", "Request rules for every reading."),
            (BE + "services/metrics.py", "def validate_vitals", "The plausible-range check."),
            (BE + "services/watch.py", "LIMITS = ", "Simulator clamps."),
        ])
        + h2("4.3 Honest limits of the data")
        + bullets([
            "**No labels.** Nobody marked which days were illness, so there is no accuracy on real illness; the episodes used for testing are **synthetic** (a rise of heart rate and breathing rate injected into real days).",
            "**Resting values stand in for spot readings.** LifeSnaps has a calm once-a-day heart rate; real spot readings are noisier, so the false-flag rates here are a **lower bound**.",
            "**Only heart rate and breathing rate could be tested** on real data; blood pressure, SpO₂, temperature and glucose use the same code but have no real test data.",
            "**71 people, 15 of them held out**, so every number comes from a small sample.",
            "**Glucose's normal band is the fasting range (70 to 99)**, so a normal after-meal 130 mg/dL scores as 'high'. A meal-aware band is future work.",
        ])
        + qa([
            ("Why not delete rows with impossible values?", "Because the same day's other signals may be fine. Setting only the broken value to missing keeps the rest of the evidence."),
            ("How do you know the model works if there are no labels?", "Three ways: injected illness-like episodes at three strengths, false flags on ordinary days, and (as a negative result) mood check-ins, which showed no link. The limits are stated, not hidden."),
        ])
    )))

    out.append(chapter("5", "Hyperparameters", "c5", "Every tunable value, where it is defined, and what was done to choose it.", (
        h2("5.1 The Isolation Forest (population model)")
        + table(["Hyperparameter", "Value", "Meaning and why"], [
            ["`n_estimators`", f"{MEASURED['forest']['n_estimators']}", "Number of random trees. More trees give a steadier score; 300 is well past the point where the score stops changing."],
            ["`contamination`", f"{MEASURED['forest']['contamination']}", "The share of training days expected to be unusual (3%). It sets the cut that turns the raw score into 'score 0.5 = more unusual than 97% of training days'."],
            ["`max_samples`", f"auto, which is {MEASURED['forest']['max_samples']}", "Each tree is built from 256 random days (scikit-learn's default)."],
            ["`random_state`", "42", "Makes training repeatable."],
            ["Standardising", "median and MAD × 1.4826", "Robust to outliers; missing values become 0 ('same as the median person')."],
            ["Score scaling", "percentile 0.94 → 0, about 0.97 → 0.5, 0.995 → 1", "`score = clip((percentile − (1 − 2c)) ÷ ((1 − c/6) − (1 − 2c)))` with c = contamination. 'Unusual' means score 0.5 or more."],
            ["Training data", "4,432 days from 71 people", "Two features: heart rate and breathing rate."],
        ])
        + files([(ML + "anomaly.py", "IsolationForest(", "Where the forest is built (`class GlobalModel`)."), (ML + "anomaly.py", "def score(self, df)", "The percentile-to-score scaling."), ("model/artifacts/vitals_anomaly.json", "", "The model card: versions, medians, spreads.")])
        + h2("5.2 The personal-baseline scorer")
        + table(["Constant", "Value", "Meaning", "How it was chosen"], [
            ["`MIN_BASELINE_READINGS`", f"{S.MIN_BASELINE_READINGS}", "Readings before any personal baseline", "About a week of daily readings; fewer is a guess"],
            ["`FULL_BASELINE_READINGS`", f"{S.FULL_BASELINE_READINGS}", "Readings for a fully personal baseline", "Three weeks. Ablation: changing it to 14 or 30 barely changed results"],
            ["`BASELINE_WINDOW`", f"{S.BASELINE_WINDOW}", "Latest readings used for the median and spread", "Recent enough to follow a person's drift"],
            ["`SCORING_HISTORY`", "120", "Earlier readings loaded per scoring", "Bounds the work"],
            ["`PERSONAL_OK_Z`", f"{S.PERSONAL_OK_Z}", "z beyond which a personal change starts to count", "Tuned: the first version (2.5) caught only 16% of moderate episodes; 1.5 catches 68%"],
            ["`PERSONAL_UNIT_Z`", f"{S.PERSONAL_UNIT_Z}", "Each further z of this adds 1 to the contribution", "Paired with the line above"],
            ["`FLAG_THRESHOLD`", f"{S.FLAG_THRESHOLD}", "A vital counts only from this contribution", "The knee of the trade-off curve (figure in chapter 8)"],
            ["`SCORE_CEILING`", f"{S.SCORE_CEILING}", "A contribution of this size is score 1.0", "Spreads severities across 0 to 1"],
            ["`MAD_TO_SD`", f"{S.MAD_TO_SD}", "Makes MAD comparable to a standard deviation", "A statistical constant"],
            ["Spread floors", ", ".join(f"{k} {v:g}" for k, v in S.MIN_SPREAD.items()), "Smallest spread a baseline may have", "About the repeatability of home devices. Without floors false flags rose 6 times"],
        ])
        + table(["Severity band", "From anomaly_score"], [[name, f"{floor}"] for name, floor in BANDS])
        + files([
            (BE + "services/scoring.py", "MIN_BASELINE_READINGS = ", "All the constants above."),
            (BE + "services/triage.py", "BANDS", "The severity bands."),
        ])
        + h2("5.3 Outbreak clustering (DBSCAN and the Poisson test)")
        + table(["Parameter", "Value", "Meaning"], [
            ["`radius_km` (DBSCAN eps)", f"{Params().radius_km}", "How close cases must be"],
            ["`km_per_day`", f"{Params().km_per_day}", "One day apart counts as this many kilometres, so time is a third axis"],
            ["`min_people` (min_samples)", f"{Params().min_people}", "Smallest cluster; three is also the smallest group any area figure in the app shows"],
            ["Window / baseline", "14 days / 56 days", "Current cases against the same area's earlier level"],
            ["Significance", "p below 0.01", "Poisson tail: unlikely to be chance"],
            ["Expected-cases floor", "0.5", "Stops a tiny baseline making any cluster look extreme"],
        ])
        + h2("5.4 Research-only values (notebooks 02 and 03)")
        + p("`WINDOW` 60 days, `MIN_DAYS` 7, `FULL_DAYS` 21, `FLAG_THRESHOLD` 0.5 and `ALERT_DAYS` 2 (alert only after two flagged days in a row) in `anomaly.py` belong to the **wearable research model**. The app uses its own constants above.")
        + h2("5.5 How the values were chosen")
        + p("Notebook 04 ran a small grid over the two settings that matter most. Result (false flags on normal days, share of 3-day episodes caught for people with history):")
        + table(["PERSONAL_OK_Z", "FLAG_THRESHOLD", "False flags", "Mild", "Moderate", "Strong"], [
            [f"{g['PERSONAL_OK_Z']}", f"{g['FLAG_THRESHOLD']}", f"{g['false flags'] * 100:.1f}%", f"{g['mild'] * 100:.0f}%", f"{g['moderate'] * 100:.0f}%", f"{g['strong'] * 100:.0f}%"]
            for g in REPORT["grid"]
        ])
        + note("**Chosen: 1.5 and 0.5.** 1.5 with threshold 0.25 catches more (87% of moderate) but more than doubles false flags (3.7%), which is too many alerts for a health worker.", "key")
    )))

    out.append(chapter("6", "How severity (low, moderate, high, critical) is decided", "c6", "Severity is the size of the strongest contribution, not an Isolation Forest output. This chapter shows the arithmetic on real inputs.", (
        chain(["Each vital's contribution", "Strongest one (the 'driver')", "÷ 4, capped at 1 = anomaly_score", "Band: 0.25 / 0.5 / 0.75", "Severity", "Citizen alert colour + worker queue order"])
        + table(["anomaly_score", "Severity", "Meaning", "Citizen's alert"], [
            ["below 0.25", "low", "flagged, but only just past the threshold", "low (green)"],
            ["0.25 to 0.50", "moderate", "clearly outside range", "medium (amber)"],
            ["0.50 to 0.75", "high", "well outside range", "high (red)"],
            ["0.75 and above", "critical", "far outside range", "high (red)"],
        ])
        + h2("6.1 The arithmetic")
        + bullets([
            "**Published range part:** how far outside the normal band the value is, in **half-band widths**. Example: SpO₂ normal band 95 to 100 has a half-band of 2.5; a reading of 89 is 6 below, which is 2.4 half-bands.",
            "**Personal part** (once there are readings): `max(0, |z| − 1.5) ÷ 1.5`, blended in by the weight (chapter 3).",
            "**Safety limits** raise a value to at least 0.5 so it always flags.",
            "The reading's score is `strongest contribution ÷ 4` capped at 1, then compared with the bands. The vital that produced the strongest contribution is the **driver** and gives the sentence the user reads.",
        ])
        + h2("6.2 Worked examples (computed live from the real scorer)")
        + _severity_examples()
        + p("A person with history is judged the same way but against **their own** usual: a heart rate of 78 is 'critical-sized' for someone whose usual is 55 with a tight spread, and nothing for someone whose usual is 75. That is the point of the personal baseline.")
        + files([
            (BE + "services/triage.py", "def severity_of", "Score to band."),
            (BE + "services/triage.py", "def describe_signal", "Builds 'Oxygen saturation 89% — well below the normal range'."),
            (BE + "services/triage.py", "def alert_severity", "Four bands to the alerts table's three levels."),
            (BE + "api/routes/phc.py", "def _severity_sql", "The worker dashboard's SQL uses the same bands, so counts and cards agree."),
        ])
        + h2("6.3 What the Isolation Forest says, and what it does not")
        + p("For every reading that has heart rate or breathing rate the forest returns a **percentile**: the share of the 4,432 training days that were *less* unusual than this one. A score of 0.5 or more is labelled 'unusual' and shown to the citizen and worker as a **population check**.")
        + _population_examples()
        + note("**It never sets severity and never raises a flag.** `evaluate.py` tried letting it flag new users at three thresholds (1.0, 0.75, 0.5): on 15 held-out people it added **no** detection, because most readings it calls unusual are ordinary for that person. Letting it flag would only add false alarms.", "key")
        + qa([
            ("So how does the Isolation Forest give low, moderate, high and critical?", "It does not. Those four levels come from the size of the strongest vital contribution (distance outside the range or the person's baseline). The forest provides a separate percentile-based population check shown beside the reading."),
            ("Why show the population check at all if it cannot flag?", "It is honest extra context: 'next to 71 people's data this heart rate and breathing rate are unusual / typical'. A worker may find it useful; it never alarms a citizen on its own."),
            ("Why divide by 4?", "A contribution of 4 is four half-bands outside the range (for example SpO₂ 85), which is clearly critical. Dividing by 4 spreads real readings across the 0 to 1 scale so the four bands are all reachable."),
        ])
    )))
    return out
