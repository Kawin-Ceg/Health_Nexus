from lib import bullets, chain, chapter, files, flow, functions, h2, note, p, qa, ref, table

BE, FE = "backend/app/", "frontend/src/"


def build() -> list[str]:
    out = []

    out.append(chapter("10", "Reports and the risk map", "c10", "Area-level views for the centre. They count only citizens who opted into community monitoring, and never show a group smaller than three.", (
        files([
            (FE + "pages/phc/Reports.tsx", "export function Reports", "Totals, a daily bar chart of readings and flags, and a locality table."),
            (FE + "pages/phc/RiskMap.tsx", "export function RiskMap", "Leaflet map of localities coloured by risk, with a ranked list beside it."),
            (BE + "api/routes/phc.py", "async def reports", "`GET /phc/reports?days=` (7 to 180, default 30)."),
            (BE + "api/routes/phc.py", "async def risk_map", "`GET /phc/map` and `/phc/locality-risk`."),
            (BE + "services/localities.py", "async def locality_risk", "Ranks localities by the share of citizens with an open flag."),
            (BE + "services/localities.py", "def suppress", "Folds any locality under 3 citizens into 'Other localities'; drops that too if still under 3."),
            (BE + "services/consent.py", "def counts_in_community", "The consent filter (default **no**) every area-level query includes."),
        ])
        + table(["Risk level", "Share of the locality's citizens with an open flag"], [
            ["High", "30% or more"], ["Elevated", "15% to under 30%"], ["Some", "above 0%"], ["None", "0%"],
        ])
        + flow([
            ("Browser", "The period selector changes `days`; the URL keeps it.", FE + "pages/phc/Reports.tsx", "const rep = useResource((s) => getReports(days, s)"),
            ("Router", "Whole local days: 'last 30 days' is today and the 29 before it, counted in India time.", BE + "api/routes/phc.py", "first_day = local_date(now) - timedelta(days=days - 1)"),
            ("Database", "Totals and the daily series use the whole catchment; the **locality table** adds `counts_in_community`.", BE + "api/routes/phc.py", "community = counts_in_community(User.id)"),
            ("Service", "`suppress` removes small cells so a locality of one or two people cannot be identified.", BE + "services/localities.py", "def suppress"),
            ("Browser", "The map plots each locality at the average position of its citizens; colour is the risk level.", FE + "pages/phc/RiskMap.tsx", "<CircleMarker"),
        ])
        + qa([
            ("Why show totals for everyone but localities only for opted-in people?", "A total says nothing about a person. A small locality does: the numbers could point at one household, so it needs both consent and a minimum size."),
            ("What does 'Other localities' mean?", "Localities under three people merged together, so the rest of the table is still complete but no small group is exposed."),
        ])
    )))

    out.append(chapter("11", "Outbreak signals (worker view)", "c11", "The system looks for clusters of people with the same illness close together in space and time, and asks the worker to confirm or reject each one.", (
        files([
            (FE + "pages/Outbreaks.tsx", "export function Outbreaks", "Full-width map, a searchable signals table, a pop-up with the reasons and a feedback form."),
            (BE + "api/routes/clusters.py", "async def current_clusters", "`GET /clusters`: for a worker, only clusters that include their centre's citizens."),
            (BE + "api/routes/clusters.py", "def reasons", "Writes the plain-language reasons with the real numbers."),
            (BE + "services/outbreaks.py", "async def run", "One clustering run: collect cases, cluster, test against the usual level, store."),
            ("model/healthnexus_ml/clustering.py", "def find_clusters", "Space-time DBSCAN."),
            (BE + "services/outbreaks.py", "def same_cluster", "Recognises the same signal across runs, so 'seen' and feedback carry over."),
        ])
        + table(["Rule", "Value"], [
            ["Cases", "a reading with fever, body ache or rash (or 38.0 °C and above); cough, breathlessness or chest pain (or SpO₂ 93 or below); diarrhoea, nausea or thirst"],
            ["Window", "the last 14 days; one point per person (their first onset)"],
            ["Cluster", "at least 3 different people within 1.5 km, where one day apart counts as 0.5 km"],
            ["Unusual?", "compared with the same area in the 56 days before; flagged as a possible outbreak when the chance of this many cases is below 1% (Poisson test)"],
            ["Who counts", "only active citizens who opted into community monitoring"],
            ["How often", "every 6 hours in the background; an administrator can run it now"],
        ])
        + flow([
            ("Background", "A task started at server start runs the clustering every 6 hours.", BE + "services/outbreaks.py", "async def run_forever"),
            ("Service", "Cases come from consenting citizens' readings with a location; each syndrome is clustered separately.", BE + "services/outbreaks.py", "for syndrome, cases in current.items():"),
            ("Database", "Each cluster is stored with its cases, expected count, p-value, centre, radius, localities and the centres involved (`phc_ids`).", BE + "services/outbreaks.py", "outbreak_flag=p_value < SIGNIFICANCE"),
            ("Router", "A worker's list is filtered to clusters whose `phc_ids` contain their centre.", BE + "api/routes/clusters.py", "def _scoped"),
            ("Browser", "Opening a signal shows the numbered reasons: how many people, the usual level, the p-value, symptoms and the share of nearby residents.", FE + "pages/Outbreaks.tsx", "function Details"),
            ("Router", "'Mark as seen' records who and when; the feedback (real outbreak, false alarm, unsure) keeps a track record of the clustering's accuracy.", BE + "api/routes/clusters.py", "async def review"),
            ("Browser", "'Write an advisory' opens the advisory form pre-filled from the signal (chapter 12).", FE + "pages/Outbreaks.tsx", "Write an advisory"),
        ])
        + qa([
            ("Is this a diagnosis?", "No. It says 'more people than usual with similar symptoms live close together'. The worker decides, and their feedback is stored so the signal's accuracy can be measured."),
            ("Why a 56-day baseline?", "It estimates how many cases the same area usually has; the run compares the current count with that expected number (never below 0.5)."),
        ])
    )))

    out.append(chapter("12", "Advisories (worker view)", "c12", "A worker can warn the citizens of their own centre, and the people living near it. Red is allowed only when the data supports it.", (
        files([
            (FE + "pages/Advisories.tsx", "export function Advisories", "A composer, then the history table with search and filters and a details pop-up."),
            (FE + "pages/Advisories.tsx", "function Audience", "Chooses who gets it: for a worker it is their own centre, optionally plus people living within a radius."),
            (BE + "api/routes/advisories.py", "async def create_advisory", "Publishes after the red check and the target resolution."),
            (BE + "api/routes/advisories.py", "async def resolve_target", "A worker is forced to `scope = centre` for their own centre."),
            (BE + "api/routes/advisories.py", "async def red_check", "Decides whether red (emergency) is justified."),
            (BE + "api/routes/advisories.py", "def targeting", "Which citizens see which advisory."),
        ])
        + table(["Colour", "Meaning", "Who can choose it"], [
            ["Green", "for information", "anyone"], ["Yellow", "take precautions", "anyone (default)"],
            ["Red", "emergency, act now", "only if a flagged outbreak with 10 or more cases exists, or at least 15 citizens (5% of the area) had high alerts this week, and no other red is running; a reason of 30+ characters is required"],
        ])
        + flow([
            ("Browser", "Choosing red asks the server first; if refused the choice snaps back to yellow with the real numbers.", FE + "pages/Advisories.tsx", "const result = await checkRed("),
            ("Router", "`red_check` counts flagged outbreaks, citizens with high alerts in 7 days, and running red advisories.", BE + "api/routes/advisories.py", "RED_MIN_CASES = 10"),
            ("Router", "`create_advisory` repeats the red check (a client cannot skip it) and requires the written reason.", BE + "api/routes/advisories.py", "if data.severity == AlertSeverity.high:"),
            ("Service", "`resolve_target` gives a worker their own centre and, if asked, the radius around it; the reach is previewed beforehand.", BE + "api/routes/advisories.py", "async def reach"),
            ("Database", "The advisory is stored with its scope, radius and the centre's coordinates.", BE + "api/routes/advisories.py", "advisory = Advisory("),
            ("Browser", "Citizens matching `targeting` see it on their Alerts page; the worker sees it in the history and can withdraw it or record whether it helped.", BE + "api/routes/advisories.py", "async def review_advisory"),
        ])
        + qa([
            ("Why restrict red?", "A false red alarm causes panic and teaches people to ignore alerts. The server checks outbreak size and the share of high alerts before allowing it."),
            ("Can a worker advise another centre's citizens?", "No: for a worker `resolve_target` rejects any scope except their own centre."),
        ])
    )))

    out.append(chapter("13", "Complaints about a citizen, and Notifications", "c13", "A worker can report repeated missed visits only when the record proves it; their own notifications have a page of their own.", (
        files([
            (FE + "components/app/ReportCitizen.tsx", "export function ReportCitizen", "'Report a problem': keeps missing visits, or behaviour during a visit."),
            (BE + "services/complaints.py", "async def missed_visits", "Counts the citizen's missed visits at this centre in 90 days and how many are unexplained."),
            (BE + "services/complaints.py", "async def prepare", "Refuses a missed-visits complaint without evidence; attaches the visits as evidence."),
            (BE + "api/routes/phc.py", "async def citizen_missed_visits", "`GET /phc/citizens/{id}/missed-visits`: the evidence, before the worker writes anything."),
            (FE + "pages/Notifications.tsx", "export function Notifications", "The worker's own alerts: bookings, changes, visits waiting for an outcome."),
            (BE + "api/routes/alerts.py", "async def list_alerts", "The same endpoint the citizen uses, for the worker's own alerts."),
        ])
        + flow([
            ("Browser", "'Report a problem' on a citizen's pop-up or record shows the evidence first.", FE + "components/app/ReportCitizen.tsx", "const evidence = useResource("),
            ("Service", "The rule: at least **3 missed visits with no reason given** in the last 90 days. A visit the citizen explained does not count.", BE + "services/complaints.py", "MISSED_THRESHOLD = 3"),
            ("Browser", "'Send to admin' stays disabled until the rule is met.", FE + "components/app/ReportCitizen.tsx", "disabled={blocked ||"),
            ("Router", "`POST /settings/concerns` calls `prepare`, which checks the rule **again** and stores the visits as evidence on the complaint.", BE + "api/routes/settings.py", "subject, evidence = await prepare("),
            ("Browser", "The district administrator sees it under 'From PHC workers' with the evidence, and decides.", "frontend/src/pages/admin/Concerns.tsx", "function EvidenceBlock"),
        ])
        + qa([
            ("Why must a citizen's explanation stop a complaint?", "Missing a visit while in hospital is not misconduct. The citizen can explain a missed visit from their Visits page, and an explained one stops counting."),
            ("Can the rule be bypassed from the browser?", "No. The API raises 422 with the exact count if fewer than three are unexplained."),
        ])
    )))

    out.append(chapter("14", "Nira for workers", "c14", "The same assistant pipeline as for citizens, with the catchment's tools and the worker's centre bound from the sign-in.", (
        p("The flow is exactly the one in the citizen guide (chapter 11): safety check, plan, read-only retrieval, wording, number check, storage. What differs is **which queries are open** and **what is bound**.")
        + functions([
            ("tools_for", BE + "services/assistant/catalog.py", "def tools_for", "A worker gets 11 of the 29 queries: own alerts, catchment overview, flagged citizens, citizen summary, silent citizens, own schedule, locality breakdown, catchment trend, symptom counts, advisories published, outbreak signals."),
            ("_binds", BE + "services/assistant/__init__.py", "def _binds", "Adds `:me`, `:phc_id` and `:district` from the signed-in user, never from the question or the model."),
            ("needs_facility", BE + "services/assistant/__init__.py", "tool.needs_facility", "A worker with no centre gets the 'not linked' message instead of an empty answer."),
        ])
        + bullets([
            "Area-level queries (locality breakdown, trend, symptom counts) include only citizens who opted into community monitoring, the same rule as the Reports page.",
            "Because the catchment is bound as `:phc_id`, asking about 'my citizens' can never reach another centre.",
        ])
        + qa([
            ("Can Nira show an individual citizen's readings to a worker?", "Only through the `citizen_summary` query, restricted to the catchment and to citizens who have not withdrawn worker access."),
        ])
    )))

    out.append(chapter("15", "Profile and settings", "c15", "The same pages and endpoints as for a citizen, with a few worker-only fields.", (
        p("The profile, password, sessions and email-change flows are identical to the citizen guide (chapters 3, 12 and 13). The differences:")
        + table(["Where", "Worker difference", "Code"], [
            ["Profile", "A **department** field is editable (hidden for citizens).", ref(FE + "pages/Profile.tsx", "const worker = p.role")],
            ["Settings → tabs", "'Your work' replaces 'Your health centre': facility, designation and working hours.", ref(FE + "pages/Settings.tsx", "function WorkTab")],
            ["Working hours", "Stored in preferences; the **default time** offered when booking a visit is the start of the working day.", ref(FE + "components/app/phc.tsx", "function useDefaultSlot")],
            ["Preferences", "Email choices for alerts and visits and the least severe flag worth an email apply to a worker too; language is a citizen-only choice.", ref(BE + "services/preferences.py", "def emails_flag")],
            ["Privacy tab", "Shows only the consents that apply to a worker; the three citizen ones are hidden.", ref(FE + "pages/Settings.tsx", "function PrivacyTab")],
            ["Support", "A worker raises app and access problems here; complaints about citizens start from the citizen's record.", ref(FE + "pages/Settings.tsx", "function SupportTab")],
        ])
        + functions([
            ("update_profile", BE + "api/routes/profile.py", "async def update_profile", "Same route as citizens; `department` is accepted for any role but only workers see it."),
            ("update_preferences", BE + "api/routes/settings.py", "async def update_preferences", "`working_hours` is validated: the end must be after the start."),
            ("reading_flagged (worker part)", BE + "services/notify.py", "async def reading_flagged", "A worker is emailed about a new flag at their centre only if the flag is reviewable and their own preferences and minimum severity allow it."),
        ])
        + qa([
            ("Does a worker choose a centre in settings?", "No. The centre is set by the administrator at approval; a worker without one is shown the 'not linked' screen and no readings reach them."),
        ])
    )))
    return out
