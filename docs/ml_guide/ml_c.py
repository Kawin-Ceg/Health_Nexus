from lib import bullets, chain, chapter, figure, files, flow, functions, h2, kpis, note, p, pre, qa, ref, table
from ml_b import MEASURED, POP_REPORT, REPORT

BE, FE, ML = "backend/app/", "frontend/src/", "model/healthnexus_ml/"


def pct(x: float, digits: int = 1) -> str:
    return f"{x * 100:.{digits}f}%"


def build() -> list[str]:
    out = []
    ff, ep = REPORT["false_flags"], REPORT["episode_detection"]

    out.append(chapter("7", "Reducing false positives", "c7", "Yes, a lot was done, and each step was measured. This chapter lists every measure, the number that justified it, and what was not done.", (
        kpis([(pct(ff["old"]), "false flags before (published ranges only)"), (pct(ff["new"]), "false flags now"), ("15 → 0", "people flagged on more than half their days"), ("~3×", "fewer false alarms from the second-reading rule")])
        + p("A **false positive** here is a flagged reading from a person who is simply well. It matters because a health worker who sees too many will stop reading alerts, and a citizen who is alarmed for nothing stops trusting the app.")
        + h2("7.1 Every measure, with its evidence")
        + table(["#", "Measure", "Evidence", "Code"], [
            ["1", "**Personal baseline instead of published ranges alone**", f"The old placeholder flagged **{pct(ff['old'])} of normal days** and 15 of 71 people on more than half their days (fit people with a resting heart rate in the 50s, healthy but below '60 to 100'). Now {pct(ff['new'])} and nobody.", ref(BE + "services/scoring.py", "def personal_contribution")],
            ["2", "**A vital counts only from contribution 0.5** (`FLAG_THRESHOLD`)", "Without it, a value one unit outside the band still flagged while the baseline was blending in: **13 of 20 healthy demo citizens** were flagged. Sweep: 0 → 10.1%, 0.25 → 3.7%, **0.5 → 1.5%**, 0.75 → 0.65%.", ref(BE + "services/scoring.py", "FLAG_THRESHOLD =")],
            ["3", "**Second unusual reading needed** for a change that is only unusual for that person", "With realistic one-off spikes (+12 to +20 bpm on 5% of readings): **5.1% false flags without the rule, 1.5% with it**. Cost: moderate episodes caught 74% → 68%, and detection on day 2 instead of day 1.", ref(BE + "services/scoring.py", "confirmed = previous is not None")],
            ["4", "**Smallest allowed spread** per vital", "Without the floors, false flags rose **6 times** (9.1%): a very regular person's 'normal band' gets so narrow that everyday noise trips it.", ref(BE + "services/scoring.py", "MIN_SPREAD:")],
            ["5", "**Gradual blend** from published to personal (7 to 21 readings)", "No sudden change in behaviour; false flags by stage: learning 3.5%, blending 0.75%, personal 1.4%.", ref(BE + "services/scoring.py", "def baseline_weight")],
            ["6", "**Safety limits wider than the normal bands**", "A person with controlled chronic hypertension (say 145/92) is judged against their own baseline instead of flagged on every reading.", ref(BE + "services/scoring.py", "SAFETY_LIMITS")],
            ["7", "**Median and MAD** (robust statistics); baseline excludes the reading being judged", "One odd value neither inflates the spread nor hides the next unusual one.", ref(BE + "services/scoring.py", "def robust_baseline")],
            ["8", "**Typos blocked before scoring** (plausible ranges)", "A mistyped 1200 for 120 is rejected with 'check for a typo' instead of becoming a critical flag.", ref(BE + "services/metrics.py", "def validate_vitals")],
            ["9", "**Activity signals left out** of the research personal score", "Including steps flagged about 25% of normal days.", ref(ML + "anomaly.py", "PHYSIO = ")],
            ["10", "**The population forest may not flag**", "Letting it flag new users at 1.0, 0.75 or 0.5 added no detection on 15 held-out people; most 'unusual' readings were ordinary for the person.", ref(BE + "services/population.py", "def check")],
            ["11", "**Alert only after two flagged days in a row** (research alert rule)", "About **3 times fewer** notifications on normal data; cost: moderate 3-day episodes caught 90% → 53%.", ref(ML + "anomaly.py", "ALERT_DAYS = ")],
            ["12", "**A human reviews every flag**, grouped per person, with Resolve or Dismiss **and a reason**", "A worker clears a person's flags in one action; the reason (false alarm, already treated, contacted, other) is stored on the flag.", ref(BE + "api/routes/phc.py", "async def worklist")],
            ["13", "**Honest wording to the citizen**", "A flag is shown as 'a prompt to check, not a diagnosis', and a citizen is told plainly when nobody is reviewing it.", ref(BE + "services/readings.py", "def _citizen_message")],
        ])
        + h2("7.2 What was not done (say this before you are asked)")
        + bullets([
            "**No feedback loop yet.** A dismissal 'false alarm' is stored but is not used to retrain or tune thresholds. That is the natural next step: use dismissal reasons as weak labels.",
            "**No per-person threshold tuning.** All citizens share the same constants; only their baselines differ.",
            "**No validation on real illness.** Detection rates come from synthetic episodes; false-flag rates come from days assumed normal.",
            "**New people are the weakest case:** with fewer than 7 readings only published ranges apply, so 3.5% of readings flag (still far below the old 24.6%).",
        ])
        + h2("7.3 The ablation table (what each design choice earns)")
        + table(["Variant (one change at a time)", "False flags on normal days", "Moderate episodes caught", "Mild caught"], [
            [a["variant"], pct(a["false flags"]), pct(a["moderate caught"], 0), pct(a["mild caught"], 0)] for a in REPORT["ablations"]
        ])
        + note("Read it as: **no spread floor** detects more (98%) but flags 6 times more people for nothing; the **2.5 SD first version** flags almost nobody but also misses most episodes; the **old placeholder** is worst on false flags and its detection is mostly luck. The shipped model is the balance.", "key")
        + qa([
            ("Which single change reduced false positives the most?", "Moving from published ranges alone to personal baselines: from 24.6% to 1.5% of normal days, and from 15 people flagged daily to none."),
            ("Does the second-reading rule delay a real alert?", "By one reading: most detections happen on day 2 of an episode. For something that develops over days that was judged acceptable; a safety-limit value (a real fever, low SpO₂) flags immediately."),
        ])
    )))

    out.append(chapter("8", "Evaluation results", "c8", "Measured on the 71-person LifeSnaps data with the app's own scorer imported from the backend, so these are the real app's numbers.", (
        table(["", "Old placeholder", "New scorer"], [
            ["False flags on normal days", pct(ff["old"]), pct(ff["new"])],
            ["People flagged on more than half their days", str(REPORT["people_flagged_over_half"]["old"]) + " of 71", str(REPORT["people_flagged_over_half"]["new"])],
            ["Moderate episodes caught (people with history)", pct(ep["established|moderate"]["old"], 0), pct(ep["established|moderate"]["new"], 0)],
            ["Strong episodes caught (people with history)", pct(ep["established|strong"]["old"], 0), pct(ep["established|strong"]["new"], 0)],
            ["Moderate episodes caught (brand-new users)", pct(ep["new user|moderate"]["old"], 0), pct(ep["new user|moderate"]["new"], 0)],
            ["Mild episodes caught", pct(ep["established|mild"]["old"], 0), pct(ep["established|mild"]["new"], 0) + " (accepted: the size of normal day-to-day change)"],
        ])
        + figure("model/reports/figures/false_flags_per_user.png", "False flags per person. Blue is the old rule; orange is the personal baseline: almost everyone is near zero.")
        + figure("model/reports/figures/episode_detection.png", "Three-day illness-like episodes caught, people with history. Strong and moderate episodes are caught far more often.")
        + figure("model/reports/figures/threshold_tradeoff.png", "Choosing FLAG_THRESHOLD: 0.5 is the knee of the curve. Lower flags more normal days; higher misses episodes quickly.")
        + h2("8.1 How the episodes were made")
        + p("There are no illness labels, so **three-day episodes were injected** into real days: heart rate and breathing rate pushed up together (mild +6 bpm and +1.5 breaths, moderate +10 and +2.5, strong +15 and +4), after the person's 25th reading for established users and from their 4th for new users. Most of the pushes stay **inside** the normal range (for example 58 → 68 bpm), which is exactly what published ranges cannot see.")
        + h2("8.2 The threshold sweep")
        + table(["FLAG_THRESHOLD", "False flags", "Moderate episodes caught"], [[f"{s['FLAG_THRESHOLD']}", pct(s["false flags"], 2), pct(s["moderate episodes caught"], 0)] for s in REPORT["threshold_sweep"]])
        + h2("8.3 The population model, tested separately")
        + table(["Measure", "Value"], [
            ["Test people / readings (held out)", f"{POP_REPORT['test_people']} / {POP_REPORT['test_readings']}"],
            ["Readings the forest calls unusual", pct(POP_REPORT["agreement"]["population_unusual_share"])],
            ["…of which the app also flagged", pct(POP_REPORT["agreement"]["unusual_that_the_app_also_flagged"], 0)],
            ["App flags the forest agrees with", pct(POP_REPORT["agreement"]["flags_the_population_model_agrees_with"], 0)],
            ["Detection added by letting the forest flag new users", "none, at all three thresholds"],
        ])
        + p("Decision recorded in the report: *the app shows the population check with every reading but does not let it flag.*")
        + h2("8.4 Other findings reported")
        + bullets([
            "Global (population) Isolation Forest alone: ROC AUC only **0.52 to 0.61** at catching a personal change; personal baselines reached **0.90**.",
            "Detection grows with history: 0% on global-only days, 22% while blending, **58%** once fully personal (notebook 02).",
            "**Negative result:** flagged days showed no link to self-reported tense or tired moods (blended score 0.088 on bad-mood days against 0.096 on others). The model cannot be claimed to detect stress.",
        ])
    )))

    out.append(chapter("9", "End-to-end workflow", "c9", "Two pipelines: the offline one that builds and checks the model, and the online one that scores every reading.", (
        h2("9.1 Offline: from data to a model the app can load")
        + chain(["LifeSnaps raw CSV", "preprocessing", "daily_clean.csv", "train", "vitals_anomaly.joblib + model card", "evaluate", "reports/*.json + figures", "restart the API"])
        + flow([
            ("Model", "Load the raw daily Fitbit CSV (63 columns), keep ten, rename them.", ML + "preprocessing.py", "def select_columns"),
            ("Model", "Drop non-wear days, blank impossible values, clear short-sleep nights, add the per-person history counters, save `daily_clean.csv`.", ML + "preprocessing.py", "def preprocess("),
            ("Model", "Keep the two signals that match app vitals (resting HR to heart_rate, breathing rate to respiratory_rate).", ML + "vitals.py", "def app_frame"),
            ("Model", "Fit the forest on the median and MAD standardised data; keep the sorted training scores for percentiles.", ML + "anomaly.py", "def fit(self, df)"),
            ("Model", "Save a plain dict (features, medians, scales, forest, training scores, contamination, version) with `joblib` and write the model card.", ML + "train.py", "joblib.dump(model.to_bundle(**meta)"),
            ("Model", "Evaluate: the app's real scorer is imported from the backend; the forest is refitted on 56 people and tested on 15.", ML + "evaluate.py", "import app.services.scoring as S"),
            ("Model", "Write the metrics and figures into `model/reports`.", ML + "evaluate.py", "def main"),
        ])
        + pre("cd model\npython -m healthnexus_ml.preprocessing   # raw CSV -> data/processed/daily_clean.csv\npython -m healthnexus_ml.train            # -> artifacts/\npython -m healthnexus_ml.evaluate         # -> reports/*.json (a few minutes)\npython -m pytest tests\n# then restart the API: it loads the model once", "tree")
        + h2("9.2 Online: what happens to one reading")
        + flow([
            ("Router", "A reading arrives from the smartwatch sync or a worker's examination and is validated.", BE + "schemas/health.py", "class VitalsIn"),
            ("Service", "The citizen's earlier readings (up to 120, oldest first) are loaded.", BE + "services/readings.py", "history = await earlier_vitals("),
            ("Database", "The reading is stored in `health_records`.", BE + "services/readings.py", "record = HealthRecord("),
            ("Model", "`score_reading` judges each vital: published part, personal part, weight, safety, confirmation; returns score, flag, features and details.", BE + "services/scoring.py", "def score_reading"),
            ("Model", "`population.check` runs the Isolation Forest on heart rate and breathing rate (the artifact is loaded once and cached).", BE + "services/population.py", "def check"),
            ("Database", "`processed_data` stores score, features, per-vital working and the population view, so a flag can explain itself later.", BE + "services/readings.py", "processed = ProcessedData("),
            ("Service", "A flagged reading gets its sentence (`describe_signal`) and a severity (`severity_of`), and an `Alert` for the citizen.", BE + "services/triage.py", "def describe_signal"),
            ("Email", "Emails are queued for the citizen and, if the flag can be reviewed, the centre's workers, and sent only after the database commit.", BE + "services/notify.py", "async def reading_flagged"),
            ("Browser", "The citizen's dashboard, history and alerts, and the worker's worklist, read the stored score and its explanation.", FE + "components/app/ModelInsights.tsx", "export function ScoreBreakdown"),
        ])
        + h2("9.3 Tests that guard the pipeline")
        + table(["File", "What it checks"], [
            ["`model/tests/test_preprocessing.py`", "Non-wear days dropped, impossible values blanked, short sleep clears overnight signals, history counters are per person and cumulative"],
            ["`model/tests/test_anomaly.py`", "The weight ramp, the baseline never uses today's value, flags run across gaps and people, a change normal for the population is still caught personally, normal days rarely flag, the saved model scores the same after reloading"],
            ["`model/tests/test_clustering.py`", "A tight group is found, one person repeating is not a cluster, the same place weeks apart is not one cluster, the Poisson tail, syndromes"],
            ["`backend/tests/test_scoring.py`", "The app scorer's rules"],
        ])
    )))
    return out
