from lib import bullets, chain, chapter, files, flow, functions, h2, note, p, qa, ref, table

BE, FE = "backend/app/", "frontend/src/"


def build() -> list[str]:
    out = []

    out.append(chapter("4", "Dashboard", "c4", "The start-of-day view: how many people need review, how many readings arrived, what is due today, and eight weeks of trend.", (
        files([
            (FE + "pages/phc/PhcDashboard.tsx", "export function PhcDashboard", "Greeting, quick actions, counts, severity filter, the first six people to review, four KPI charts."),
            (FE + "services/phc.ts", "export const getDashboard", "`getDashboard`, `getOverview`, `getWorklist`."),
            (BE + "api/routes/phc.py", "async def dashboard", "`GET /phc/dashboard`: the counts."),
            (BE + "api/routes/phc.py", "async def overview", "`GET /phc/overview`: four KPIs by calendar week."),
            (BE + "services/triage.py", "BANDS", "The severity bands; the dashboard's SQL uses the **same list**, so the two cannot drift."),
            (FE + "components/app/phc.tsx", "export function CitizenWorkCard", "One person's open flags as a card, with Resolve, Dismiss, Book visit and Record."),
        ])
        + functions([
            ("dashboard", BE + "api/routes/phc.py", "async def dashboard", "Citizens in catchment; citizens flagged; open flags by severity; readings and people submitting in the last 7 days; engagement counts; visits needing an outcome; visits later today."),
            ("_severity_sql", BE + "api/routes/phc.py", "def _severity_sql", "Builds a SQL `CASE` from `BANDS` so the count by severity matches the severity shown on every card."),
            ("_directory", BE + "api/routes/phc.py", "def _directory", "Joins each citizen with reading and open-flag aggregates and derives the engagement status (shared with the Citizens page)."),
            ("overview", BE + "api/routes/phc.py", "async def overview", "Readings submitted, citizens who submitted, flags raised, flags cleared; eight Monday-start weeks in India time; the current week marked partial."),
            ("KpiCard", FE + "pages/phc/PhcDashboard.tsx", "function KpiCard", "Last full week as the headline, this week so far beneath, a bar per week (the partial one is paler)."),
        ])
        + flow([
            ("Browser", "Three requests start together: counts, KPI series and the worklist.", FE + "pages/phc/PhcDashboard.tsx", "const dash = useResource((s) => getDashboard(s)"),
            ("Guard", "`require_catchment_worker` runs for the whole `/phc` router; a worker with no centre gets 409 and the page shows the 'not linked' screen.", BE + "services/catchment.py", "async def require_catchment_worker"),
            ("Database", "Open flags are rows of `processed_data` with `is_anomaly` true and no `resolution`, restricted to `catchment_ids(worker)`.", BE + "api/routes/phc.py", "def _open_flag"),
            ("Service", "Engagement status per citizen: **attention** (open flag), **never logged**, **silent** (no reading for 14 days), otherwise **ok**.", BE + "api/routes/phc.py", "status_expr = case("),
            ("Browser", "The severity tabs filter the worklist in the browser; the URL keeps the choice.", FE + "pages/phc/PhcDashboard.tsx", "const severity = oneOf(params.get(\"severity\")"),
            ("Browser", "After a card is resolved the page reloads both the worklist and the counts.", FE + "pages/phc/PhcDashboard.tsx", "const refresh = () => {"),
        ])
        + qa([
            ("Why are weeks counted in India time and from Monday?", "A flag raised at 11 pm local would otherwise land in the next day's bucket in UTC. The SQL converts to the local zone before truncating to the week."),
            ("What is a 'silent' citizen?", "Someone whose last reading is older than 14 days (`SILENT_AFTER`); a person who joined and never logged is 'never logged', which ranks above silent."),
        ])
    )))

    out.append(chapter("5", "Alerts: the worklist", "c5", "Flags arrive per reading but are worked **per person**: one citizen is one card, however many flags they have.", (
        files([
            (FE + "pages/phc/PhcAlerts.tsx", "export function PhcAlerts", "Tabs Needs review and Recent activity; search; time, severity and locality filters; cards and pop-ups."),
            (FE + "components/app/compact.tsx", "export function FlagActions", "The green **Resolve** and red **Dismiss** buttons, with the dismissal reason."),
            (BE + "api/routes/phc.py", "async def worklist", "`GET /phc/worklist`: open flags grouped by citizen."),
            (BE + "api/routes/phc.py", "async def resolve_citizen", "`POST /phc/worklist/citizens/{id}/resolve`: clear all of one person's flags."),
            (BE + "api/routes/phc.py", "async def mark_seen", "`POST /phc/queue/{id}/seen`: clear one flag."),
            (BE + "api/routes/phc.py", "async def flag_feed", "`GET /phc/alerts`: recent flags, open and cleared, for the Recent activity tab."),
            (BE + "schemas/phc.py", "class Resolve", "The decision: reviewed, or dismissed **with** a reason."),
        ])
        + functions([
            ("worklist", BE + "api/routes/phc.py", "async def worklist", "Groups open flags by citizen (count, worst score, first and latest time), orders worst first, attaches up to 10 worst flags per person and the worker's next visit with them."),
            ("_search", BE + "api/routes/phc.py", "def _search", "A name, or an `HN-1A2B3C4D` reference matched against the start of the citizen's id."),
            ("_apply", BE + "api/routes/phc.py", "def _apply", "The one update used by both resolve routes: who, when, the resolution, the reason and note."),
            ("Resolve._reason_matches", BE + "schemas/phc.py", "def _reason_matches", "A dismissal must carry a reason; a plain review must not."),
            ("PhcAlerts", FE + "pages/phc/PhcAlerts.tsx", "export function PhcAlerts", "Filters run in the browser over the loaded list; cards show name, ID, place, how long it has been open and the severity."),
            ("WorkDetails", FE + "pages/phc/PhcAlerts.tsx", "function WorkDetails", "The pop-up: details, the flags newest first (click one to resolve just that), Resolve all, Dismiss, Book visit, Full record."),
        ])
        + flow([
            ("Browser", "The page loads the worklist once and filters locally by search, period, severity and locality.", FE + "pages/phc/PhcAlerts.tsx", "const work = useResource((s) => getWorklist({}, s)"),
            ("Router", "`GROUP BY user_id` over open flags in the catchment; ordered by worst score, then latest.", BE + "api/routes/phc.py", "grouped = ("),
            ("Service", "Each person's flags are capped at 10 (worst first) so one noisy citizen cannot crowd out the list.", BE + "api/routes/phc.py", "FLAGS_PER_CITIZEN = 10"),
            ("Browser", "A card opens a pop-up; clicking a single flag opens that flag on its own.", FE + "pages/phc/PhcAlerts.tsx", "const flag = flags.find("),
            ("Browser", "**Resolve** (green) marks reviewed; **Dismiss** (red) asks why: false alarm, already being treated, contacted with no action needed, or other.", FE + "components/app/compact.tsx", "const REASONS"),
            ("Router", "`resolve_citizen` updates every open flag of that citizen in one statement; `mark_seen` locks and updates one (409 if it was already cleared).", BE + "api/routes/phc.py", "result = await db.execute("),
            ("Database", "`processed_data` gets `resolution`, `reviewed_by`, `reviewed_at`, `dismiss_reason` and the note.", BE + "api/routes/phc.py", "reviewed_at=utcnow(),"),
            ("Browser", "Booking a visit from the pop-up opens the visit form with the citizen already chosen and the flag attached.", FE + "pages/phc/PhcAlerts.tsx", "caseId={item.flags[0]?.processed_id}"),
        ])
        + note("**Effects elsewhere:** the citizen's dashboard open-flag count falls and their health score rises; their History marks the reading 'reviewed'; the badge on the worker's Alerts menu drops on the next poll.", "key")
        + qa([
            ("Why group by person?", "Five flags for one citizen are one problem to follow up, not five. The card shows the worst and lets the worker clear all or one."),
            ("Why must a dismissal carry a reason?", "A dismissal without a reason cannot be audited. The reason is stored on the flag (`dismiss_reason`) and the note beside it."),
            ("Can a worker clear another centre's flag?", "No. Both routes filter on `catchment_ids(worker)`; a foreign flag is 404 'Case not found'."),
        ])
    )))

    out.append(chapter("6", "Citizens directory", "c6", "Everyone in the catchment, sorted by what is worth opening first, with the actions a worker needs on each row.", (
        files([
            (FE + "pages/phc/Citizens.tsx", "export function Citizens", "Search, status and locality filters; numbered table with coloured status; View, Book and Examine on each row."),
            (BE + "api/routes/phc.py", "async def citizens", "`GET /phc/citizens`."),
            (BE + "services/localities.py", "def locality_of", "Blank areas become 'Unspecified'."),
        ])
        + table(["Status", "Meaning", "Colour"], [
            ["Needs attention", "has at least one open flag", "red"], ["Never logged", "joined but no reading yet", "violet"],
            ["Gone quiet", "last reading more than 14 days ago", "amber"], ["Logging", "recent readings, nothing open", "green"],
        ])
        + functions([
            ("citizens", BE + "api/routes/phc.py", "async def citizens", "Filters by name or HN reference, locality and status; ranks attention, never logged, silent, ok; within a group the worst flag first, then the longest silent."),
            ("CitizenDetails", FE + "pages/phc/Citizens.tsx", "function CitizenDetails", "Pop-up: reference, locality, tap-to-call phone, age, gender, counts, last reading, joined; Book visit, Record examination, Full record, Report a problem."),
            ("StatusPill", FE + "pages/phc/Citizens.tsx", "function StatusPill", "The coloured status."),
        ])
        + flow([
            ("Browser", "Typing in search waits 300 ms before asking, so each keystroke is not a request.", FE + "pages/phc/Citizens.tsx", "const t = window.setTimeout("),
            ("Router", "The query joins the catchment with per-citizen reading and flag aggregates and applies the three filters.", BE + "api/routes/phc.py", "query = select("),
            ("Database", "Paged with `limit` 50 and `offset`; the total and the per-status counts are computed over the **whole** catchment, not just the page.", BE + "api/routes/phc.py", "counts = await _engagement_counts(db, worker, now)"),
            ("Browser", "Row actions: View opens the pop-up; Book opens the visit form; Examine goes to the examination page.", FE + "pages/phc/Citizens.tsx", "<CalendarPlus size={15}"),
        ])
        + qa([
            ("Why compute counts over the whole catchment?", "A page of 50 cannot say how many are silent. The status dropdown shows the true counts next to each option."),
            ("Can the worker see citizens who withdrew access?", "No. They are not in `catchment_citizens`, so they are absent here and in every other worker view."),
        ])
    )))

    out.append(chapter("7", "Citizen record", "c7", "Everything about one citizen in one request, with the model's reasoning for each flag. Every view is written to the audit log.", (
        files([
            (FE + "pages/phc/CitizenRecord.tsx", "export function CitizenRecord", "Header actions, period selector, trend chart, Submissions, Visits, Alerts sent, pop-ups."),
            (BE + "api/routes/phc.py", "async def citizen_record", "`GET /phc/citizens/{id}/record?days=`."),
            (FE + "components/app/ModelInsights.tsx", "export function ScoreBreakdown", "Per-vital explanation of a flag, worded for a worker."),
            (FE + "components/app/compact.tsx", "export function CompactRow", "The one-line rows used by Submissions and Alerts sent."),
            (FE + "components/app/ReportCitizen.tsx", "export function ReportCitizen", "'Report a problem' about this citizen (chapter 13)."),
        ])
        + functions([
            ("citizen_record", BE + "api/routes/phc.py", "async def citizen_record", "Identity and profile, latest value of each vital with the citizen's own baseline and z-score, a timeline, alerts sent, past and upcoming visits, and flags still open from before the window."),
            ("_entry", BE + "api/routes/phc.py", "def _entry", "One timeline row: values, symptoms, severity, the signal sentence, the resolution, and the stored per-vital working (`checks`)."),
            ("ScoreBreakdown", FE + "components/app/ModelInsights.tsx", "export function ScoreBreakdown", "Shows each vital's value against the range and the citizen's baseline, and what it added to the flag."),
            ("PopulationNote", FE + "components/app/ModelInsights.tsx", "export function PopulationNote", "The Isolation Forest's view (how unusual next to 71 people); informs only."),
        ])
        + flow([
            ("Browser", "The record and the vitals vocabulary load together; the period (30, 90, 180, 365 days) lives in the URL.", FE + "pages/phc/CitizenRecord.tsx", "const record = useResource("),
            ("Guard", "`get_catchment_citizen`: a citizen outside the catchment is the same 404 as an unknown id.", BE + "services/catchment.py", "async def get_catchment_citizen"),
            ("Database", "Readings of the window (up to 2000) joined to their scores; alerts (50), visits (50 past, 20 upcoming).", BE + "api/routes/phc.py", "readings_query = ("),
            ("Service", "Flags still open from **before** the window are counted separately and never mixed into the window's numbers.", BE + "api/routes/phc.py", "before_open, oldest = ("),
            ("Database", "An audit row `view_citizen_record` is written with the worker and the IP, in the same request.", BE + "api/routes/phc.py", "action=\"view_citizen_record\""),
            ("Browser", "Submissions shows topic, time and severity per reading; opening one shows every vital, the symptoms and **why it was flagged**, with Resolve and Dismiss if it is still open.", FE + "pages/phc/CitizenRecord.tsx", "<ScoreBreakdown checks={openReading.checks}"),
        ])
        + qa([
            ("Why log a worker viewing a record?", "It is sensitive personal data. The log lets a centre or an administrator answer 'who looked at this person's record and when'."),
            ("Why separate 'from before this period'?", "A window of 30 days must not hide a flag that has been open for 40; it is reported in a notice beside the window instead of inside its counts."),
        ])
    )))

    out.append(chapter("8", "Recording an examination", "c8", "When a worker measures a citizen (blood pressure, sugar and so on) the reading is stored under the citizen, marked as theirs, and scored like any other.", (
        files([
            (FE + "pages/phc/RecordExam.tsx", "export function RecordExam", "Form with a field per measurement, symptoms, place and optional earlier time; the result replaces the form."),
            (FE + "services/phc.ts", "export const recordExam", "`POST /phc/citizens/{id}/readings`."),
            (BE + "api/routes/phc.py", "async def record_examination", "Checks, stores and scores the reading; writes the audit row."),
            (BE + "schemas/health.py", "class VitalsIn", "Request rules shared with every reading: known vitals, plausible ranges, systolic above diastolic, up to 12 symptoms, time not in the future or more than 30 days back."),
            (BE + "services/readings.py", "async def submit_reading", "Store, score, alert, email, commit: the same function the watch uses."),
        ])
        + flow([
            ("Browser", "Each value is checked as it is typed: it must be a number, inside the plausible range, and diastolic must be below systolic.", FE + "pages/phc/RecordExam.tsx", "function validate"),
            ("Browser", "A place is **required**; the checkbox 'I measured this earlier' lets the worker set a past time.", FE + "pages/phc/RecordExam.tsx", "Say where the examination took place."),
            ("Router", "`POST /phc/citizens/{id}/readings`: the guard, then `get_catchment_citizen` (uniform 404 outside the catchment).", BE + "api/routes/phc.py", "async def record_examination"),
            ("Router", "If the citizen turned health tracking off, nothing is stored (409).", BE + "api/routes/phc.py", "if not citizen.consent:"),
            ("Service", "`submit_reading(source='phc', recorded_by=worker, location=…)` scores it against the citizen's own baseline and creates the alert and emails if flagged.", BE + "api/routes/phc.py", "source=\"phc\", recorded_by=worker.id"),
            ("Database", "An audit row `record_examination` links the worker to the new reading.", BE + "api/routes/phc.py", "action=\"record_examination\""),
            ("Browser", "The result card replaces the form (so a second submit cannot create a duplicate) and plays the alert or clear sound.", FE + "pages/phc/RecordExam.tsx", "play(saved.flagged"),
        ])
        + note("**What the citizen sees:** the reading appears in their History with 'recorded by <worker>, <place>', cannot be deleted by them (only the centre can change it), and if flagged they get the same alert and email as for a watch reading.", "key")
        + qa([
            ("Why does a watch not provide blood pressure?", "Home watches measure heart rate, SpO₂, breathing rate and temperature. Pressure and sugar need a cuff or meter, so they come from a worker's examination."),
            ("Can a worker back-date an examination?", "Up to 30 days, never into the future (`_recent_past`), and the true storage time is kept in `created_at`."),
        ])
    )))

    out.append(chapter("9", "Schedule and visits", "c9", "A worker books, edits, completes or cancels visits; the citizen is told each time.", (
        files([
            (FE + "pages/phc/Schedule.tsx", "export function Schedule", "Tabs Needs outcome, Upcoming, Done, Missed, Cancelled; search; kind and period filters; cards and pop-up."),
            (FE + "pages/phc/Schedule.tsx", "export function VisitForm", "The booking and editing form: citizen, date, time, length, kind, place, reason, private notes."),
            (BE + "api/routes/phc.py", "async def book_visit", "`POST /phc/visits`."),
            (BE + "api/routes/schedule.py", "async def all_visits", "`GET /schedule/all`: visits of the last 180 days onward."),
            (BE + "api/routes/schedule.py", "async def update_visit", "`PATCH /schedule/{id}`: complete, nobody there, cancel, move, edit."),
            (BE + "services/visits.py", "def notify_booked", "Alerts and emails to both people when a visit is booked, changed or has no outcome."),
            (BE + "services/visit_state.py", "def visit_state", "Upcoming, today, due now, overdue: derived from the status and the clock, never stored."),
        ])
        + table(["Action", "Allowed when", "Effect"], [
            ["Book", "citizen in catchment; time in the future and within 90 days; the citizen has no other open visit", "Creates the visit; the citizen's alert and email; if made from a flag, that flag is marked reviewed ('Follow-up visit booked')."],
            ["Mark done", "the visit is today or its time has passed (not for a later day; move it first if it happened early)", "status = completed."],
            ["Nobody there", "once the booked time has passed", "status = missed (counts toward a complaint if unexplained, chapter 13)."],
            ["Move or edit time", "more than 8 hours before it starts", "New time; the citizen is notified."],
            ["Edit other details", "any time while booked", "Kind, length, place, reason, private notes."],
            ["Cancel", "more than 8 hours ahead, with a reason of 10+ characters", "status = cancelled; the citizen sees the reason."],
        ])
        + flow([
            ("Browser", "'Book a visit' (or Book on a card) opens `VisitForm`; the citizen can be searched by name or HN reference.", FE + "pages/phc/Schedule.tsx", "const found = useResource("),
            ("Router", "`book_visit` loads the citizen with `get_catchment_citizen` and checks the time.", BE + "api/routes/phc.py", "check_booking_time(data.scheduled_for)"),
            ("Router", "One open visit per citizen: a second booking is refused with 'Move that visit instead'.", BE + "api/routes/phc.py", "existing = await db.scalar("),
            ("Service", "`notify_booked` writes the citizen's alert (with the sound on their next poll) and the worker's, and queues both emails if their preferences allow.", BE + "services/visits.py", "def notify_booked"),
            ("Browser", "A success message confirms the booking for the worker.", FE + "pages/phc/Schedule.tsx", "title: \"Visit booked\""),
            ("Router", "`update_visit` locks the row, refuses a visit that already has an outcome, and applies the action's rule.", BE + "api/routes/schedule.py", "elif data.action == \"miss\":"),
            ("Router", "Cancel and time changes call `check_cutoff` (8 hours) on the server; the page also hides the buttons.", BE + "api/routes/schedule.py", "def check_cutoff"),
            ("Service", "`notify_changed` tells the citizen what happened, including the reason.", BE + "services/visits.py", "def notify_changed"),
        ])
        + qa([
            ("Why is 'overdue' not stored?", "It depends on the clock. Storing it would need a job to keep it right; deriving it with `visit_state` is always correct and cannot drift."),
            ("What stops two workers double-booking the same citizen?", "The check for an existing open visit, plus the citizen being in only one catchment."),
            ("Who sees the private notes?", "Only the worker. `VisitOut.notes` is set in `visit_for_worker` and never in the citizen's view."),
        ])
    )))
    return out
