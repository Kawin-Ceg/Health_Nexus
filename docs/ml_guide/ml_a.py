import sys
import uuid

from lib import ROOT, bullets, chain, chapter, files, flow, functions, h2, kpis, md, note, p, pre, qa, ref, table

sys.path.insert(0, str(ROOT / "backend"))
import app.services.scoring as S  # noqa: E402
from app.services.metrics import VITALS  # noqa: E402


def score_rules(uid, vitals, history):
    """The rules alone: the worked examples show how a vital is judged, not what the forest says."""
    saved = S.population.check
    S.population.check = lambda v: None
    try:
        return S.score_reading(uid, vitals, history)
    finally:
        S.population.check = saved


BE, ML = "backend/app/", "model/healthnexus_ml/"


def _stage_rows() -> list[list[str]]:
    rows = []
    for n in (3, 6, 7, 10, 14, 20, 21, 30):
        w = S.baseline_weight(n)
        rows.append([str(n), S.stage_of(n), f"{w:.2f}", f"{(1 - w) * 100:.0f}% published range / {w * 100:.0f}% personal"])
    return rows


def _spike_example() -> str:
    """A person whose heart rate sits near 62: one odd reading, then a second one."""
    uid = uuid.uuid4()
    usual = [61, 63, 62, 60, 64, 62, 61, 63, 62, 65, 60, 62, 63, 61, 62, 64, 62, 61, 63, 62, 60, 62, 64, 63, 61, 62, 63, 62, 61, 62]
    history = [{"heart_rate": v} for v in usual]
    one = score_rules(uid, {"heart_rate": 78}, history)
    two = score_rules(uid, {"heart_rate": 79}, history + [{"heart_rate": 78}])
    d1, d2 = one.details["heart_rate"], two.details["heart_rate"]
    return table(
        ["", "Reading", "Baseline (median, spread)", "z-score", "Personal part", "Confirmed?", "Contribution", "Flagged?"],
        [
            ["Day 1", "heart rate 78", f"{d1.baseline:g}, {d1.spread:g}", f"{d1.z:+.1f}", f"{d1.personal:.2f}", "no (needs a second reading)", f"{one.features.get('heart_rate', 0):.2f}", "no, only 'watch'"],
            ["Day 2", "heart rate 79", f"{d2.baseline:g}, {d2.spread:g}", f"{d2.z:+.1f}", f"{d2.personal:.2f}", "yes (day 1 was also unusual, same direction)", f"{two.features.get('heart_rate', 0):.2f}", "yes"],
        ],
    )


def build() -> list[str]:
    out = []

    out.append(chapter("1", "The big picture: what 'the ML' is in HealthNexus", "c1", "Three pieces do machine-learning work. Knowing which one decides what is the first thing to say in a viva.", (
        kpis([("71", "people in the training data (LifeSnaps)"), ("4,432", "days of heart rate and breathing rate"), ("300", "trees in the Isolation Forest"), ("29 ms", "to score one reading (median)"), ("1.5%", "false flags on normal days, was 24.6%")])
        + table(["Piece", "What it is", "What it decides", "Where it lives"], [
            ["**Personal-baseline scorer** (`personal-baseline-v1`)", "Statistics: each person's own median and spread per vital, blended with published normal ranges", "**Whether a reading is flagged, and how severe** (low, moderate, high, critical)", ref(BE + "services/scoring.py", "def score_reading")],
            ["**Population model** (`population-iforest-v1`)", "A trained **Isolation Forest** (scikit-learn) on heart rate and breathing rate", "**Nothing on its own.** It adds a 'population check' beside each reading: how unusual next to 71 people", ref(BE + "services/population.py", "def check")],
            ["**Outbreak clustering**", "Space-time **DBSCAN** plus a Poisson test", "Whether several people near each other have the same illness more than usual", ref("model/healthnexus_ml/clustering.py", "def find_clusters")],
        ])
        + note("**Say this first:** *the Isolation Forest does not decide low, moderate, high or critical.* Those levels come from how far a vital is outside its normal range or the person's own baseline (chapter 6). The forest only reports a percentile, and the research showed it added no detection beyond the rules, so it is shown as information and never raises a flag.", "key")
        + h2("Why two layers instead of one model")
        + bullets([
            "**There are no labels.** Nobody marked which days were 'ill'. A supervised classifier cannot be trained; the options are unsupervised models (Isolation Forest) or statistics that explain themselves.",
            "**People differ more than days do.** For resting heart rate, HRV and breathing rate, people's averages differ about **3 times more than one person changes day to day** (notebook 02). A model trained on everyone mostly learns 'who is this person', not 'is today unusual'. A personal baseline is therefore needed.",
            "**The Isolation Forest alone barely beats guessing** at spotting a personal change (ROC AUC 0.52 to 0.61), while personal baselines reached 0.90.",
            "**A flag must explain itself.** A worker is told 'oxygen saturation 89%, well below the normal range', which a forest score cannot say.",
        ])
        + h2("What the PDF covers")
        + p("Input features (2), the personal baseline (3), data constraints and good answers (4), hyperparameters (5), how severity is decided (6), false-positive reduction (7), results (8), the end-to-end workflow (9), the folder structure and where the model lives (10), tech stack and response time (11), and a defence Q&A (12).")
    )))

    out.append(chapter("2", "Input features", "c2", "Three different sets of inputs exist: what the research trained on, what the population model uses, and what the live scorer reads.", (
        h2("2.1 Training data: LifeSnaps")
        + p("**LifeSnaps** (Yfantidou et al., 2022, *Scientific Data*, CC BY 4.0): Fitbit data from **71 people over about four months in 2021**. The raw daily file has 63 columns; ten were kept because a normal smartwatch also gives them.")
        + table(["Signal (our name)", "Raw column", "Used in personal score?", "Why"], [
            ["resting_hr", "resting_hr", "**yes**", "Rises with infection; maps to the app's `heart_rate`"],
            ["hrv_rmssd", "rmssd", "**yes**", "Falls when the body is stressed or ill"],
            ["sleep_hr", "nremhr", "**yes**", "Heart rate in deep sleep"],
            ["breathing_rate", "full_sleep_breathing_rate", "**yes**", "Maps to the app's `respiratory_rate`"],
            ["skin_temp", "nightly_temperature", "**yes**", "Temperature trend at night"],
            ["sleep_minutes, sleep_efficiency", "minutesAsleep, sleep_efficiency", "no", "Context only"],
            ["steps, very_active_minutes, sedentary_minutes", "steps, very_active_minutes, sedentary_minutes", "no", "Depends on what someone chose to do (gym, lazy Sunday), not on health. Using them made **25% of normal days flag**."],
        ])
        + p("**Left out on purpose:** `spo2` (only 17% of days have it), `stress_score` (itself a model output, on 25% of days), `calories`, `bpm` and `distance` (duplicates of steps and heart rate), and age, gender and body measurements.")
        + h2("2.2 The population model uses two inputs")
        + table(["Model input", "From LifeSnaps", "Matches the app's"], [["heart_rate", "resting heart rate", "`heart_rate` (bpm)"], ["respiratory_rate", "breathing rate during sleep", "`respiratory_rate` (/min)"]])
        + p("These are the only two LifeSnaps signals that match something a citizen's app measures, so the ten-signal wearable model could not be used on app readings. The forest is trained on exactly these two (`vitals.py`), and a missing one is treated as 'the population median' (nothing unusual).")
        + h2("2.3 The live scorer reads eight vitals")
        + table(["Vital", "Unit", "Normal band", "Plausible range (typo guard)", "Safety limit (always counts)", "Smallest spread allowed"], [
            [
                f"`{v.key}`", v.unit, f"{v.normal[0]:g} to {v.normal[1]:g}" if v.normal else "none",
                f"{v.plausible[0]:g} to {v.plausible[1]:g}",
                (lambda lim: (f"at or below {lim[0]:g}" if lim[0] is not None else "") + (" · " if lim[0] is not None and lim[1] is not None else "") + (f"at or above {lim[1]:g}" if lim[1] is not None else "") if lim != (None, None) else "none")(S.SAFETY_LIMITS.get(v.key, (None, None))),
                f"{S.MIN_SPREAD[v.key]:g}" if v.key in S.MIN_SPREAD else "none",
            ]
            for v in VITALS.values()
        ])
        + files([
            (BE + "services/metrics.py", "_SPECS = (", "The vitals vocabulary: label, unit, normal band, plausible range."),
            (BE + "services/scoring.py", "SAFETY_LIMITS", "Safety limits per vital."),
            (BE + "services/scoring.py", "MIN_SPREAD", "Floors for a person's spread."),
        ])
        + h2("2.4 Where the readings come from")
        + bullets([
            "**Smartwatch sync** (four a day, simulated in this build): heart rate, SpO₂, breathing rate, temperature.",
            "**A health worker's examination:** blood pressure, glucose, weight and any of the others.",
            "Each reading is one row of `health_records.vitals` (a JSON object) and is scored the moment it is stored.",
        ])
        + h2("2.5 Symptoms are not model inputs")
        + p("The 12 symptoms a person can record (fever, cough, headache, body ache, breathlessness, chest pain, dizziness, fatigue, nausea, diarrhoea, thirst, rash) **do not change the anomaly score**. They are shown to the worker and are used by the **outbreak clustering**, which maps them to three syndromes (febrile, respiratory, gastrointestinal) in `features.py`.")
        + qa([
            ("Why did you not use all ten signals in the personal score?", "Steps and activity depend on choices, not health. In the first try, taking the biggest z-score over all ten signals flagged about 25% of normal days, almost always because of steps. Only the five body signals are used."),
            ("Why only two features for the Isolation Forest?", "Those are the only two that exist both in the research data and in what the app measures. A forest trained on signals the app never has would be useless at run time."),
            ("Do symptoms affect severity?", "No. Severity depends only on vitals. Symptoms inform the worker and the outbreak detector."),
        ])
    )))

    out.append(chapter("3", "The personal baseline: how it works", "c3", "Each person is compared with their own usual values, once there are enough of them, and with published normal ranges before that.", (
        chain(["Earlier readings of this vital (up to 120)", "Take the latest 30", "Median = their usual", "Robust spread (MAD × 1.4826, with a floor)", "z = (today − usual) ÷ spread", "Blend with the published range", "Second-reading check", "Contribution"])
        + h2("3.1 The four ingredients")
        + table(["Ingredient", "Formula", "Why"], [
            ["Usual value", "median of the person's latest 30 readings of that vital, **earlier ones only**", "The median is not pulled by one odd reading; excluding today stops an abnormal reading being compared with itself."],
            ["Spread", "`max(1.4826 × MAD, smallest-allowed spread, 1e-6)`", "MAD is the median absolute deviation (robust to outliers); 1.4826 makes it comparable to a standard deviation; the floor stops a very regular person getting a near-zero spread and being flagged for ordinary noise."],
            ["z-score", "(today − usual) ÷ spread", "How many 'normal wobbles' away today is."],
            ["Personal contribution", "`max(0, |z| − 1.5) ÷ 1.5`", "Nothing until 1.5 spreads away; then each further 1.5 adds 1."],
        ])
        + h2("3.2 From published ranges to personal: the weight")
        + p("Per vital, the weight moves gradually from the published normal band to the personal baseline as readings accumulate, so there is **no sudden jump** when a baseline becomes available.")
        + table(["Earlier readings of that vital", "Stage", "Weight on personal", "Judged by"], _stage_rows())
        + pre("contribution = (1 − weight) × published_contribution + weight × personal_contribution\npublished_contribution = distance outside the normal band, in half-band widths (0 inside the band)", "tree")
        + files([
            (BE + "services/scoring.py", "def baseline_weight", "0 below 7 readings, rising to 1 at 21."),
            (BE + "services/scoring.py", "def robust_baseline", "Median and floored robust spread of the latest 30."),
            (BE + "services/scoring.py", "def personal_contribution", "`max(0, |z| − 1.5) ÷ 1.5`."),
            (BE + "services/scoring.py", "def published_contribution", "Distance outside the normal band in half-band widths."),
            (BE + "services/readings.py", "async def earlier_vitals", "Loads up to 120 earlier readings, oldest first, for the baseline."),
        ])
        + h2("3.3 The confirmation rule (one odd reading is usually noise)")
        + p("A value that is **inside the published range but unusual for this person** counts only if the **previous** reading of that vital was also outside their usual band, in the same direction. Until then it is reported as 'watch' and contributes nothing. Illness keeps a value off for days; a hurried measurement does not.")
        + _spike_example()
        + h2("3.4 Safety limits override the baseline")
        + p("A value past a **safety limit** (for example SpO₂ at or below 92, temperature at or above 38.0 °C, systolic at or above 160) always counts in full, whatever the person's usual: a fever is a fever. The limits are wider than the normal bands so that someone with controlled chronic hypertension (say 145/92) is judged against their own baseline instead of being flagged on every reading.")
        + h2("3.5 From contributions to a flag")
        + bullets([
            "A vital counts only if its contribution is at least **0.5** (`FLAG_THRESHOLD`); safety limits count in full.",
            "`anomaly_score = min(1, strongest contribution ÷ 4)`. A reading is flagged when any vital counts.",
            "`basis` records whether the flag used published ranges or a personal baseline; the page tells the citizen and worker which.",
            "Everything is stored with the score (`processed_data.details`), so any flag can be explained later.",
        ])
        + functions([
            ("_judge", BE + "services/scoring.py", "def _judge", "One vital: published part, personal part, weight, safety and the confirmation check."),
            ("_contribution", BE + "services/scoring.py", "def _contribution", "Blends the two parts; applies the 0.5 threshold and the safety rule."),
            ("score_reading", BE + "services/scoring.py", "def score_reading", "The only function the rest of the app calls: returns score, flag, features, basis, details, watch list and population check."),
        ])
        + qa([
            ("Why median and MAD instead of mean and standard deviation?", "A single outlier moves a mean and standard deviation a lot, which would hide the next unusual value. The median and MAD barely move."),
            ("What happens to a brand-new citizen?", "Fewer than 7 readings of a vital means weight 0: only the published normal range is used, so they are not left unprotected. The dashboard says how many readings remain until a personal baseline starts."),
            ("Why must the baseline exclude today's reading?", "Otherwise an abnormal reading would be partly compared with itself and look less abnormal."),
        ])
    )))
    return out
