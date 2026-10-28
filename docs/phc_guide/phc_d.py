import endpoints
from lib import chain, chapter, h2, note, p, qa, ref, table

BE, FE = "backend/app/", "frontend/src/"

WORKER_ROUTERS = [
    ("auth.py", None, {"register_citizen", "update_consent"}, ("router",)),
    ("applications.py", {"my_documents", "upload", "remove"}, set(), ("router",)),
    ("phc.py", None, set(), ("router",)),
    ("schedule.py", {"worker_schedule", "update_visit", "all_visits"}, set(), ("router",)),
    ("alerts.py", {"list_alerts", "unread_count", "mark_read", "phc_unread_count"}, set(), ("router", "phc_router")),
    ("advisories.py", None, set(), ("router",)),
    ("clusters.py", {"current_clusters", "acknowledge", "review"}, set(), ("router",)),
    ("settings.py", None, set(), ("router",)),
    ("profile.py", None, set(), ("router",)),
    ("assistant.py", None, set(), ("router",)),
]


def build() -> list[str]:
    out = []

    out.append(chapter("16", "How the features talk to each other", "c16", "Features never call each other's pages. They share **tables and services**: one feature writes a row, another reads it.", (
        h2("The shared spine")
        + chain(["processed_data (flags)", "health_records", "scheduled_visits", "alerts", "consent_records", "phc_applications"])
        + table(["When this happens", "Written by", "Stored in", "Then these react"], [
            ["A citizen's reading is flagged", ref(BE + "services/readings.py", "async def record_reading"), "processed_data; alerts; email outbox", "The citizen appears in the worklist · the Alerts badge grows within 30 s with a toast and sound · emails to workers who asked (`reading_flagged`)"],
            ["Worker resolves or dismisses", ref(BE + "api/routes/phc.py", "def _apply"), "processed_data.resolution", "The citizen's dashboard shows fewer open flags · History marks it reviewed · the badge drops"],
            ["Worker books a visit", ref(BE + "api/routes/phc.py", "async def book_visit"), "scheduled_visits; alerts; email", "The citizen's Visits and Alerts pages and next-visit line · the linked flag is marked reviewed"],
            ["Citizen cancels a visit", ref(BE + "api/routes/schedule.py", "async def cancel_mine"), "scheduled_visits", "The worker's card shows 'cancelled by the citizen' with the reason · worker alert and email"],
            ["Visit time passes with no outcome", ref(BE + "services/visits.py", "async def notify_missed"), "alerts (once)", "Both alerted; the worker's 'Needs outcome' tab lists it; Mark done or Nobody there"],
            ["Citizen explains a missed visit", ref(BE + "api/routes/schedule.py", "async def explain_missed"), "scheduled_visits.missed_reason", "The worker sees the reason · the visit stops counting toward a complaint"],
            ["Worker records an examination", ref(BE + "api/routes/phc.py", "async def record_examination"), "health_records (source phc)", "Scored like any reading · shows in the citizen's History as the worker's · may raise a flag, alert and email"],
            ["Citizen withdraws worker access", ref(BE + "services/consent.py", "async def change_consents"), "consent_records", "They vanish from every worker page · their open visits are cancelled"],
            ["Citizen changes health centre", ref(BE + "api/routes/settings.py", "async def change_health_centre"), "users.phc_id", "Moves from one catchment to another · the old centre's visits are cancelled"],
            ["Admin approves a worker", ref(BE + "api/routes/admin.py", "async def approve"), "users.role, users.phc_id", "The next request passes `require_phc_worker`; the catchment appears"],
            ["Outbreak run finds a cluster", ref(BE + "services/outbreaks.py", "async def run"), "community_data", "It lists on the Outbreaks page of every worker whose centre is involved"],
            ["Worker publishes an advisory", ref(BE + "api/routes/advisories.py", "async def create_advisory"), "advisories", "Matching citizens see it on their Alerts page"],
            ["Worker reports a citizen", ref(BE + "api/routes/settings.py", "async def raise_concern"), "concerns (with evidence)", "The district administrator's Complaints page; the reply comes back to the worker"],
        ])
        + h2("Two journeys end to end")
        + h2("A. From a flagged reading to a visit")
        + chain(["Citizen's watch sync", "score_reading flags", "Alert + worker email", "Worklist card", "Worker opens details", "Book visit", "Citizen toast + sound", "Visit on the citizen's page"])
        + h2("B. From a new application to a working catchment")
        + chain(["Apply + proof", "OCR and tamper checks", "Admin reviews", "approve: role + phc_id", "ProtectedRoute lets them in", "Citizens of the centre appear"])
        + note("**If the examiner asks 'how do two features communicate?'** one feature writes a row through a service function; the other reads that table through its own route. There is no feature-to-feature call, which is why a page can be changed without touching another.", "key")
    )))

    out.append(chapter("17", "API index for the worker module", "c17", "Every endpoint the worker's screens use, generated by scanning the route files, with the front-end function that calls it.", (
        table(["Endpoint", "Handler", "Called from"], endpoints.rows(WORKER_ROUTERS))
        + p("Handlers link to the first line of the function; the third column links to the line that makes the request. Every `/phc/...` route is protected by the router-level guard `require_catchment_worker`.")
    )))

    out.append(chapter("18", "Data model and numbers to know", "c18", "The tables the worker module reads and writes, then every threshold with the line that defines it.", (
        table(["Table (model)", "What the worker module uses it for", "Defined at"], [
            ["<code>users</code>", "role (pending_phc → phc_worker), phc_id (the catchment link), area, geo_lat/lng, preferences", ref(BE + "models/user.py", "class User(")],
            ["<code>phc_applications</code>", "employee_id, designation, centre name, status (pending, approved, rejected), reviewer", ref(BE + "models/phc_application.py", "class PhcApplication(")],
            ["<code>phc_verification_documents</code>", "uploaded proofs, SHA-256, OCR text, tamper score, check status", ref(BE + "models/phc_verification_document.py", "class PhcVerificationDocument(")],
            ["<code>valid_phc_facilities</code>", "the registry of centres, with coordinates", ref(BE + "models/valid_phc_facility.py", "class ValidPhcFacility(")],
            ["<code>health_records</code>", "readings; `source` watch / phc / self; `recorded_by` and `location` for examinations", ref(BE + "models/health_record.py", "class HealthRecord(")],
            ["<code>processed_data</code>", "the flag: score, working, and the worker's resolution, reason, note, reviewer", ref(BE + "models/processed_data.py", "class ProcessedData(")],
            ["<code>scheduled_visits</code>", "visits, kind, length, private notes, who cancelled and why", ref(BE + "models/scheduled_visit.py", "class ScheduledVisit(")],
            ["<code>alerts</code>", "the worker's notifications", ref(BE + "models/alert.py", "class Alert(")],
            ["<code>community_data</code>", "outbreak clusters, with acknowledgement and feedback", ref(BE + "models/community_data.py", "class CommunityData(")],
            ["<code>advisories</code>", "what the worker publishes", ref(BE + "models/advisory.py", "class Advisory(")],
            ["<code>concerns</code>", "complaints, with subject and evidence", ref(BE + "models/concern.py", "class Concern(")],
            ["<code>audit_logs</code>", "view_citizen_record, record_examination, document views", ref(BE + "models/audit_log.py", "class AuditLog(")],
        ])
        + table(["Setting", "Value", "Defined at"], [
            ["'Gone quiet' after", "14 days without a reading", ref(BE + "api/routes/phc.py", "SILENT_AFTER = ")],
            ["Flags shown per citizen on a card", "10 worst", ref(BE + "api/routes/phc.py", "FLAGS_PER_CITIZEN = ")],
            ["Record timeline", "200 entries (2000 readings read)", ref(BE + "api/routes/phc.py", "TIMELINE_LIMIT = ")],
            ["KPI history", "8 weeks, Monday start, India time", ref(BE + "api/routes/phc.py", "OVERVIEW_WEEKS = ")],
            ["Smallest area figure shown", "3 citizens", ref(BE + "services/localities.py", "MIN_CELL = ")],
            ["Locality risk levels", "30% high, 15% elevated", ref(BE + "services/localities.py", "def risk_level")],
            ["Examination time", "not in the future, at most 30 days back", ref(BE + "schemas/health.py", "BACKDATE_LIMIT = ")],
            ["Symptoms on one reading", "12", ref(BE + "schemas/health.py", "MAX_SYMPTOMS = ")],
            ["Book a visit", "at most 90 days ahead; one open visit per citizen", ref(BE + "api/routes/schedule.py", "BOOKING_HORIZON = ")],
            ["Cancel or move a visit", "not within 8 hours; cancel needs a 10+ character reason", ref(BE + "api/routes/schedule.py", "CHANGE_CUTOFF = ")],
            ["Visit 'no outcome' grace", "4 hours", ref(BE + "services/visit_state.py", "GRACE = ")],
            ["Complaint about missed visits", "3 unexplained in 90 days", ref(BE + "services/complaints.py", "MISSED_THRESHOLD = ")],
            ["Proof documents", "up to 6, 5 MB each, JPEG, PNG or PDF", ref(BE + "api/routes/applications.py", "MAX_DOCUMENTS = ")],
            ["Outbreak clustering", "14-day window, 56-day baseline, p below 0.01, every 6 hours", ref(BE + "services/outbreaks.py", "SIGNIFICANCE = ")],
            ["Red advisory", "10+ cases in a flagged outbreak, or 15+ high-alert citizens and 5% of the area", ref(BE + "api/routes/advisories.py", "RED_MIN_CASES = ")],
            ["Badge refresh", "every 30 seconds", ref(FE + "components/app/AppShell.tsx", "const BADGE_POLL_MS")],
        ])
    )))

    out.append(chapter("19", "Questions across the whole worker module", "c19", "Short answers with the place to open if the examiner says 'show me'.", (
        qa([
            ("What exactly can a health worker see?", "Only citizens whose centre is theirs and who have not withdrawn worker access (`catchment_citizens`). Within that: profile, readings, flags, visits and alerts. Area-level pages add only people who opted into community monitoring."),
            ("How do you stop a worker reading another centre's citizens?", "Every query starts from `catchment_ids(worker)`, the guard is on the whole `/phc` router, and a citizen outside the catchment returns the same 404 as an unknown id (`get_catchment_citizen`)."),
            ("How is a worker accountable?", "Viewing a record, recording an examination and each document the admin opens write `audit_logs` rows; every resolution stores who, when, the reason and the note on the flag itself."),
            ("How does someone become a worker?", "They apply as `pending_phc` with an employee ID and proof; automatic checks help the administrator; only an administrator approves and links the centre. Until then the account has no access to health information."),
            ("What is a flag and is it a diagnosis?", "A flag says a reading is unusual for that person or outside a safe range. It is a prompt to follow up. The worker resolves or dismisses with a reason; nothing is concluded automatically."),
            ("Why group alerts by citizen?", "One person with five flags is one task. The worklist ranks people by their worst flag and lets the worker clear all or one."),
            ("What prevents a visit being booked twice or cancelled at the last minute?", "One open visit per citizen, a booking horizon of 90 days, and a server-side 8-hour cut-off with a written reason for cancellation (`check_cutoff`)."),
            ("How is privacy kept in reports and maps?", "Only opted-in citizens are counted, and any area under three people is merged into 'Other localities' (`suppress`)."),
            ("Why are weeks and days counted in India time?", "So a flag raised late in the evening lands on the correct local day; SQL converts to the local zone before bucketing."),
            ("What happens if a worker's approval is withdrawn?", "`revoke` returns them to `pending_phc`, removes `phc_id`, cancels their booked visits and informs the citizens."),
            ("What would you test first?", "The catchment boundary (foreign ids), consent withdrawal hiding a citizen, the resolve and dismiss rules, the visit cut-off, area-figure suppression and the examination's consent check. Test files in `backend/tests` are named by feature (test_modules, test_consents, test_notifications, test_watch, test_onboarding)."),
        ])
    )))
    return out
