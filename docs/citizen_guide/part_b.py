from lib import bullets, chain, chapter, files, flow, functions, h2, note, p, qa, ref, table, tables

BE, FE = "backend/app/", "frontend/src/"


def build() -> list[str]:
    out = []

    out.append(chapter("5", "Smartwatch: how a reading enters the system", "c5", "Citizens do not type vitals. They connect a watch and fetch one reading per part of the day; this build simulates the watch.", (
        files([
            (FE + "pages/citizen/Watch.tsx", "export function Watch", "Connect screen, four daily slots, the latest result and a disconnect button."),
            (FE + "services/health.ts", "export const getWatch", "`getWatch`, `connectWatch`, `disconnectWatch`, `syncWatch`."),
            (BE + "api/routes/vitals.py", "async def sync_watch", "The four `/health/watch*` endpoints."),
            (BE + "services/watch.py", "def slot_at", "Slots, the once-per-slot rule, and the simulator."),
            (BE + "services/readings.py", "async def submit_reading", "Stores and scores every reading from any source (chapter 6)."),
            (BE + "models/health_record.py", "source: Mapped[str]", "A reading's `source` is watch, phc (examination) or self."),
        ])
        + h2("The four slots")
        + table(["Slot", "Local hours", "Note"], [
            ["Morning", "05:00 to 12:00", ""], ["Afternoon", "12:00 to 17:00", ""], ["Evening", "17:00 to 21:00", ""],
            ["Night", "21:00 to 05:00", "00:00 to 05:00 counts as the **previous day's** night (`slot_at`)."],
        ])
        + flow([
            ("Browser", "The page loads the state and the vitals vocabulary together.", FE + "pages/citizen/Watch.tsx", "useResource((s) => Promise.all([getWatch(s)"),
            ("Router", "`GET /health/watch` returns whether a watch is connected, the current slot and what each slot holds.", BE + "api/routes/vitals.py", "async def watch_status"),
            ("Service", "`slot_at(now)` picks the slot and the day it counts for; `synced_today` finds readings already stored.", BE + "services/watch.py", "async def synced_today"),
            ("Browser", "Not connected? The Connect component asks for a brand and posts it.", FE + "pages/citizen/Watch.tsx", "function Connect"),
            ("Router", "`connect_watch` sets `has_smartwatch` and `smartwatch_brand` on the profile.", BE + "api/routes/vitals.py", "async def connect_watch"),
            ("Browser", "'Fetch from watch' calls `syncWatch`.", FE + "pages/citizen/Watch.tsx", "const out = await syncWatch()"),
            ("Guard", "`require_onboarding_user`: citizen, verified. Then the route refuses if health-tracking consent is off (403) or no watch is connected (409).", BE + "api/routes/vitals.py", "if not user.consent:"),
            ("Database", "The user row is locked (`with_for_update`) so a double tap cannot create two readings.", BE + "api/routes/vitals.py", "with_for_update()"),
            ("Service", "If this slot already has a reading it is returned (`already_synced`); otherwise `simulate` draws one.", BE + "services/watch.py", "async def simulate"),
            ("Service", "`submit_reading(source='watch', watch_day, watch_slot)` stores and scores it (chapter 6) and returns the result.", BE + "api/routes/vitals.py", "recorded = await submit_reading(db, user, vitals, [], now"),
            ("Browser", "The result card appears; a flagged reading plays the alert sound, a normal one the clear sound.", FE + "pages/citizen/Watch.tsx", "play(out.reading.flagged"),
        ])
        + note("**Why the simulator is believable:** values are drawn around the person's own recent median (or typical adult values for a new person), shifted for time of day (lower heart rate at night, slightly warmer in the afternoon), and the random generator is seeded with `user-day-slot`, so the same slot always gives the same reading.", "key")
        + qa([
            ("Why is the watch simulated?", "A real wearable needs a vendor account and device. The app's contract is a reading with four vitals per slot; replacing `simulate` with a vendor API call changes one function and nothing else."),
            ("How do you prevent two readings for one slot?", "Three layers: the row lock in `sync_watch`, the check `synced_today`, and a partial unique index `uq_health_records_watch_slot` on (user, day, slot) for watch rows (migration 0015)."),
            ("Where do blood pressure and sugar come from?", "A health worker records them during an examination (`source = phc`); they appear in History with the worker's name and place."),
        ])
    )))

    out.append(chapter("6", "From reading to alert: the scoring pipeline", "c6", "Every reading, from any source, goes through one function. This is the engine behind the dashboard, history, alerts and the worker's queue.", (
        chain(["submit_reading", "record_reading", "earlier_vitals (last 120)", "score_reading", "population.check", "ProcessedData saved", "Alert row (if flagged)", "notify.reading_flagged", "email after commit"])
        + files([
            (BE + "services/readings.py", "async def record_reading", "Stores the reading, scores it, writes the alert."),
            (BE + "services/scoring.py", "def score_reading", "The only function the rest of the app calls to judge a reading."),
            (BE + "services/population.py", "def check", "Isolation Forest percentile for heart rate and breathing; informs, never flags."),
            (BE + "services/triage.py", "def severity_of", "Score → critical / high / moderate / low, and the plain sentence for a flag."),
            (BE + "services/metrics.py", "def validate_vitals", "The vitals vocabulary: normal bands, units, plausible ranges."),
            (BE + "services/notify.py", "async def reading_flagged", "Emails the citizen and (if reviewed) the centre's workers."),
            (BE + "api/views.py", "def vitals_result", "Shapes the result the page shows, including the per-vital explanation."),
        ])
        + h2("How a reading is judged")
        + bullets([
            "**New person (fewer than 7 earlier readings of a vital):** compared with the published normal range only. Distance outside the range is measured in half-band widths (`published_contribution`).",
            "**Building a baseline (7 to 20 readings):** the weight moves gradually from the published range to the person's own median and robust spread (`baseline_weight`, `robust_baseline` using the median absolute deviation).",
            "**Personal (21 or more):** judged against the person alone. Someone whose blood pressure is always a little high is not flagged on every reading.",
            "**Confirmation rule:** a value inside the published range that is only unusual for this person needs a **second** unusual reading in the same direction before it counts (`_judge`). One odd home reading is usually noise.",
            "**Safety limits** (for example SpO₂ at or below 92, temperature at or above 38.0 °C) always count in full, whatever the person's usual (`past_safety_limit`).",
            "A vital counts only from a contribution of **0.5** (`FLAG_THRESHOLD`). `anomaly_score = min(1, strongest contribution / 4)`.",
        ])
        + table(["Severity", "Score", "Alert colour for the citizen"], [
            ["Critical", "0.75 and above", "High (red)"], ["High", "0.50 to 0.75", "High (red)"],
            ["Moderate", "0.25 to 0.50", "Medium (amber)"], ["Low", "below 0.25", "Low (green)"],
        ])
        + functions([
            ("record_reading", BE + "services/readings.py", "async def record_reading", "Saves `HealthRecord`, scores it against the earlier readings, saves `ProcessedData` (features, per-vital details, population view) and the alert."),
            ("earlier_vitals", BE + "services/readings.py", "async def earlier_vitals", "Up to 120 earlier readings, oldest first, for the baseline."),
            ("submit_reading", BE + "services/readings.py", "async def submit_reading", "record + queue emails + commit. Every way a reading arrives goes through here."),
            ("_citizen_message", BE + "services/readings.py", "def _citizen_message", "Tells the citizen honestly whether anyone is reviewing the flag (no worker, or worker access switched off)."),
            ("_judge", BE + "services/scoring.py", "def _judge", "One vital: published contribution, personal contribution, weight, safety and confirmation."),
            ("_contribution", BE + "services/scoring.py", "def _contribution", "Blends published and personal parts; applies the 0.5 threshold and safety limits."),
            ("describe_signal", BE + "services/triage.py", "def describe_signal", "Builds 'Oxygen saturation 89% — well below the normal range' from the strongest feature."),
            ("alert_severity", BE + "services/triage.py", "def alert_severity", "Four severities map to the alerts table's three levels."),
            ("check (population)", BE + "services/population.py", "def check", "Scores heart rate and breathing against 71 people's data; stored for the worker, never decides a flag."),
        ])
        + flow([
            ("Service", "Earlier readings are loaded so the baseline never includes the reading being judged.", BE + "services/readings.py", "history = await earlier_vitals("),
            ("Database", "The `HealthRecord` is stored with the citizen's location.", BE + "services/readings.py", "record = HealthRecord("),
            ("Model", "`score_reading` judges each vital and returns features, score, basis and details.", BE + "services/readings.py", "score = score_reading(citizen.id, vitals, history)"),
            ("Database", "`ProcessedData` keeps the working so a flag can explain itself later.", BE + "services/readings.py", "processed = ProcessedData("),
            ("Service", "A flagged reading creates the citizen's `Alert`.", BE + "services/readings.py", "alert = Alert("),
            ("Email", "`reading_flagged` queues emails according to each person's preferences and minimum severity.", BE + "services/notify.py", "async def reading_flagged"),
            ("Database", "One commit; queued emails are sent only after it succeeds and dropped if it rolls back.", BE + "services/notify.py", "def _send_after_commit"),
            ("Browser", "The 30-second badge poll notices the new unread alert and shows a toast with the alert sound.", FE + "components/app/AppShell.tsx", "if (news && role ==="),
        ])
        + qa([
            ("Is it machine learning?", "The decision is a transparent statistical scorer (personal median and spread), chosen because it can explain every flag. A trained Isolation Forest also scores each reading, but it only adds a 'population check' because on held-out people it caught nothing the rules missed."),
            ("Why can a flag be explained to a citizen?", "`ProcessedData.details` stores, for each vital, the value, the baseline, the spread, the z-score, the weight and whether it was confirmed; the page renders it as sentences."),
            ("What does the citizen read when nobody is reviewing?", "`_citizen_message` says so plainly and advises seeing a doctor, instead of the reassuring 'your centre has been told'."),
        ])
    )))

    out.append(chapter("7", "Dashboard", "c7", "One call returns everything the home page needs: latest values, trends, flags, alerts, next visit and centre.", (
        files([
            (FE + "pages/citizen/Dashboard.tsx", "export function CitizenDashboard", "The page: score ring, vital chart, time-of-day and week comparison, latest alerts."),
            (FE + "services/health.ts", "export const getSummary", "`GET /health/summary`."),
            (BE + "api/routes/vitals.py", "async def summary", "Builds the summary from `health_records`, `processed_data`, `alerts`, `scheduled_visits`."),
            (BE + "services/readings.py", "def baseline_of", "The 'usual' range shown next to each latest value."),
            (FE + "components/app/TrendChart.tsx", "", "Recharts line chart: the shaded band is the published normal range and flagged readings are drawn larger."),
        ])
        + functions([
            ("summary", BE + "api/routes/vitals.py", "async def summary", "One request: newest value of each vital with its personal baseline, 30-day trend, counts, five unread alerts, next visit, centre and how many workers serve it."),
            ("factorsOf", FE + "pages/citizen/Dashboard.tsx", "function factorsOf", "Builds the health score: vitals with a normal band share 80 points; open flags cost up to 20."),
            ("HealthRing", FE + "pages/citizen/Dashboard.tsx", "function HealthRing", "The ring: one arc per factor; hover shows why; click jumps to that vital's chart."),
            ("TimeOfDay", FE + "pages/citizen/Dashboard.tsx", "function TimeOfDay", "Average of the chosen vital by morning, afternoon, evening and night."),
            ("WeekComparison", FE + "pages/citizen/Dashboard.tsx", "function WeekComparison", "This week against the week before."),
            ("CitizenDashboard", FE + "pages/citizen/Dashboard.tsx", "const unreviewed =", "Shows a red notice when no centre or no worker is assigned: a flag would go unreviewed."),
        ])
        + h2("How the health score is made (100 points)")
        + table(["Part", "Points", "Rule"], [
            ["Each vital with a normal range", "80 shared equally", "Inside the band keeps all its share. Outside, it loses 80% of its share for every half-band width away from the band, down to zero."],
            ["Open flags", "20", "Each flag not yet reviewed by the centre costs 7 points, to a maximum of 20."],
            ["Verdict", "", "85 and above 'Looking well'; 65 and above 'Worth watching'; below that 'Needs attention'."],
        ])
        + note("The score is a **display summary** computed in the browser from values the API already returned. It does not feed any alert, so it can be explained on the page (hover each arc) without exposing the model.", "key")
        + flow([
            ("Browser", "`useResource` fetches the summary and the vitals vocabulary together.", FE + "pages/citizen/Dashboard.tsx", "useResource((signal) => Promise.all([getSummary(signal)"),
            ("Guard", "`require_onboarding_user`: only the signed-in, verified citizen; every query below filters on that user's id.", BE + "api/routes/vitals.py", "async def summary"),
            ("Database", "Readings of the last 90 days (capped at 500) joined to their scores.", BE + "api/routes/vitals.py", "window_start = now - timedelta(days=BASELINE_WINDOW_DAYS)"),
            ("Service", "For each vital the newest value is compared with that vital's earlier values (`baseline_of` needs 7).", BE + "api/routes/vitals.py", "base = baseline_of("),
            ("Database", "Open flags, unread alerts, next scheduled visit and the centre are counted or fetched.", BE + "api/routes/vitals.py", "next_visit_row = ("),
            ("Browser", "`factorsOf` turns the latest values into score factors; `HealthRing` draws them.", FE + "pages/citizen/Dashboard.tsx", "const factors = factorsOf("),
        ])
        + qa([
            ("Where do the 'usual' ranges come from?", "From the citizen's own earlier readings in the window (median and robust spread), shown only once there are at least 7; before that no baseline is shown rather than a fake one."),
            ("What does the red notice mean?", "The citizen has no centre, or their centre has no active worker, so a flagged reading has nobody to review it. It links to Settings → Your health centre."),
        ])
    )))

    out.append(chapter("8", "History", "c8", "Every reading the citizen has, filterable, with the model's explanation and a delete for their own entries.", (
        files([
            (FE + "pages/citizen/History.tsx", "export function History", "Filters (measurement, period, flagged only), paged list, expandable explanation, delete with confirmation."),
            (FE + "lib/params.ts", "export function oneOf", "Filters live in the URL; `oneOf` and `intParam` clamp whatever is typed there before it reaches the API."),
            (BE + "api/routes/vitals.py", "async def history", "`GET /health/history`: filters, pages of 20, outer join to the score."),
            (BE + "api/routes/vitals.py", "async def delete_reading", "`DELETE /health/readings/{id}`."),
            (BE + "services/triage.py", "def describe_signal", "The one-line reason shown for a flagged reading."),
        ])
        + flow([
            ("Browser", "The URL holds the filters; they are validated against the allowed lists.", FE + "pages/citizen/History.tsx", "const window = oneOf(params.get(\"days\")"),
            ("API client", "`getHistory` sends page, page size, metric, days, flagged-only.", FE + "services/health.ts", "export const getHistory"),
            ("Router", "Unknown metric names are rejected (422). The query always starts from `HealthRecord.user_id == user.id`.", BE + "api/routes/vitals.py", "if metric is not None and metric not in VITALS"),
            ("Database", "Outer join to `processed_data`; ordered newest first; offset and limit for the page; total counted separately.", BE + "api/routes/vitals.py", ".outerjoin(ProcessedData, ProcessedData.health_record_id == HealthRecord.id)"),
            ("Service", "`_reading_out` adds severity, the signal sentence, who recorded it and the population view.", BE + "api/routes/vitals.py", "def _reading_out"),
            ("Browser", "Each row shows source (watch, examination), place and worker for examinations, and 'why it was flagged' on demand.", FE + "pages/citizen/History.tsx", "const remove = async (id: string)"),
            ("Router", "Delete is scoped to the caller, so someone else's id is simply 'not found'. A worker's examination cannot be deleted by the citizen (409).", BE + "api/routes/vitals.py", "if record.source == \"phc\":"),
            ("Database", "The score is deleted with the reading and an `AuditLog` row 'delete_reading' is written, in one commit.", BE + "api/routes/vitals.py", "action=\"delete_reading\""),
        ])
        + qa([
            ("Can a citizen delete a flagged reading to make a flag disappear from the worker's queue?", "Yes for their own watch readings, and the deletion is audited. Readings recorded by a worker (`source = phc`) can only be changed by the centre."),
            ("Why filter in the URL?", "A refreshed or shared page keeps the same view, and clamping the parameters means nothing unexpected reaches the API."),
        ])
    )))

    out.append(chapter("9", "Alerts and advisories", "c9", "Two lists on one page: notices about the citizen's own readings and visits, and community advisories for their area.", (
        files([
            (FE + "pages/citizen/Alerts.tsx", "export function CitizenAlerts", "Tabs for Your alerts and Advisories; search and filters; detail pop-ups."),
            (FE + "services/health.ts", "export const getAlerts", "`getAlerts`, `getUnreadCount`, `markRead`."),
            (BE + "api/routes/alerts.py", "async def list_alerts", "Own alerts plus the advisories addressed to this citizen."),
            (BE + "api/routes/alerts.py", "async def mark_read", "Marks alerts read; scoped to the caller."),
            (BE + "api/routes/advisories.py", "def targeting", "Which advisories a person is shown."),
            (FE + "components/app/AppShell.tsx", "async function loadBadges", "The sidebar badge: unread count, refreshed every 30 s."),
        ])
        + flow([
            ("Browser", "`getAlerts` returns `alerts`, `advisories` and the unread count.", FE + "pages/citizen/Alerts.tsx", "const res = useResource((s) => getAlerts(s)"),
            ("Router", "Own alerts: `Alert.user_id == user.id`, newest first.", BE + "api/routes/alerts.py", "own = select(Alert).where(Alert.user_id == user.id)"),
            ("Service", "`targeting(user)` matches an advisory to the citizen by centre, by a 'living nearby' radius, by locality or pincode, by district, or by state.", BE + "api/routes/advisories.py", "def targeting"),
            ("Router", "Advisories of the last 365 days are returned, running ones first, so the page can show history.", BE + "api/routes/alerts.py", "Advisory.created_at >= now_utc() - timedelta(days=365)"),
            ("Browser", "`topic()` names each alert (Visit booked, Reading flagged, Smartwatch…) from its wording.", FE + "pages/citizen/Alerts.tsx", "function topic"),
            ("Browser", "Opening an alert marks just that one as seen; 'Mark all as seen' clears the rest.", FE + "pages/citizen/Alerts.tsx", "void markRead([a.id])"),
            ("Router", "`mark_read` has `user_id` in the WHERE, so ids belonging to anyone else match nothing.", BE + "api/routes/alerts.py", "query = update(Alert).where(Alert.user_id == user.id"),
            ("Browser", "The sidebar badge drops on the next poll.", FE + "components/app/AppShell.tsx", "const BADGE_POLL_MS"),
        ])
        + h2("Where alerts come from")
        + table(["Alert", "Created by", "Code"], [
            ["Reading flagged", "Scoring pipeline", ref(BE + "services/readings.py", "alert = Alert(")],
            ["Visit booked", "Worker books a visit", ref(BE + "services/visits.py", "def notify_booked")],
            ["Visit moved or cancelled", "Worker or citizen changes a visit", ref(BE + "services/visits.py", "def notify_changed")],
            ["Visit has no outcome", "First schedule load after the visit time plus 4 hours", ref(BE + "services/visits.py", "async def notify_missed")],
            ["Reading reminder", "Hourly job: nothing logged for 3 days", ref(BE + "services/reminders.py", "async def send_due")],
        ])
        + qa([
            ("Is an alert 'acted upon'?", "On this page 'Seen' means the citizen opened it (it is marked read then). The health worker's action on the underlying flag (resolved or dismissed) is on the worker side and the citizen's History shows that it was reviewed."),
            ("How is an advisory addressed to just one locality?", "The admin's advisory stores a scope (centre, area, district, state); `targeting` compares it with the citizen's centre, locality, pincode, district and home coordinates."),
        ])
    )))

    out.append(chapter("10", "Visits", "c10", "The citizen sees the visits a health worker booked, can cancel with a reason up to 8 hours ahead, and can explain a missed one.", (
        files([
            (FE + "pages/citizen/Visits.tsx", "export function CitizenVisits", "Tabs Upcoming, Done, Missed, Cancelled; search and filters; detail pop-up."),
            (FE + "components/app/visits.tsx", "export const changeable", "Shared pieces: the 8-hour check, status pill, cancel form, modal."),
            (BE + "api/routes/schedule.py", "async def my_schedule", "`GET /schedule/mine`."),
            (BE + "api/routes/schedule.py", "async def cancel_mine", "`POST /schedule/mine/{id}/cancel`."),
            (BE + "api/routes/schedule.py", "async def explain_missed", "`POST /schedule/mine/{id}/reason`."),
            (BE + "services/visit_state.py", "def visit_state", "Derives upcoming, today, due_now, overdue from the status and the clock."),
            (BE + "services/visits.py", "async def notify_missed", "One-time 'no outcome' alerts, claimed atomically."),
            (BE + "services/complaints.py", "async def missed_visits", "Counts unexplained misses for a worker's complaint."),
        ])
        + flow([
            ("Browser", "The page loads the citizen's visits.", FE + "pages/citizen/Visits.tsx", "const res = useResource((s) => getMySchedule(s)"),
            ("Router", "`notify_missed` first writes any due 'no outcome' alerts; then visits of the last 180 days, or still scheduled, are returned with the worker's phone.", BE + "api/routes/schedule.py", "await notify_missed(db, citizen_id=user.id)"),
            ("Service", "`visit_state` is derived at read time (4-hour grace), never stored.", BE + "services/visit_state.py", "if now - scheduled_for <= GRACE"),
            ("Browser", "Cancel is offered only if the visit is more than 8 hours away (`changeable`) and a reason of 10 or more characters is typed.", FE + "components/app/visits.tsx", "export const changeable"),
            ("Router", "The server enforces the same rule; a visit under 8 hours returns 409.", BE + "api/routes/schedule.py", "def check_cutoff"),
            ("Database", "Status becomes cancelled; `cancelled_by = citizen`, the reason and time are stored.", BE + "api/routes/schedule.py", "visit.cancelled_by, visit.cancel_reason, visit.cancelled_at = \"citizen\""),
            ("Service", "`notify_changed` alerts the worker with the citizen's reason and queues the emails.", BE + "services/visits.py", "def notify_changed"),
            ("Browser", "A missed visit shows a box to say why; the reason is saved with `explainMissedVisit`.", FE + "pages/citizen/Visits.tsx", "function MissedReason"),
            ("Service", "An explained miss no longer counts toward a worker's complaint (needs 3 unexplained in 90 days).", BE + "services/complaints.py", "MISSED_THRESHOLD = 3"),
        ])
        + note("Visits are **created by the health worker** (from the worker's Alerts, Citizens or Schedule pages). The citizen's page is read, cancel and explain. Booking creates the citizen's alert and email through `notify_booked`.", "key")
        + qa([
            ("Why 8 hours?", "Late cancellations leave a worker with a wasted trip. The rule is one constant (`CHANGE_CUTOFF`) enforced on the server and mirrored in the page so the button hides when it cannot work."),
            ("What if the citizen withdraws health-worker access or changes centre?", "`change_consents` and `change_health_centre` call `cancel_open_visits`, because those workers can no longer see this person (chapter 13)."),
        ])
    )))
    return out
