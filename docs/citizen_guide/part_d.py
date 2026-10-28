import endpoints
from lib import chain, chapter, h2, note, p, qa, ref, table

BE, FE = "backend/app/", "frontend/src/"

def build() -> list[str]:
    out = []

    out.append(chapter("14", "How the features talk to each other", "c14", "Features never call each other's pages. They share **tables and services**: one feature writes a row, another reads it.", (
        h2("The shared spine")
        + chain(["health_records + processed_data", "alerts", "scheduled_visits", "consent_records", "users.preferences"])
        + p("These five stores are the whole conversation between features. Each row below names the writer, the table, and who reads it.")
        + table(["When this happens", "Written by", "Stored in", "Then these react"], [
            ["Citizen fetches a smartwatch reading", ref(BE + "api/routes/vitals.py", "async def sync_watch"), "health_records, processed_data", "Dashboard score and charts · History list · worker's queue (if flagged) · Nira answers"],
            ["A reading is flagged", ref(BE + "services/readings.py", "alert = Alert("), "alerts; email outbox", "Alerts page and badge · toast and sound within 30 s · emails to citizen and centre workers per their preferences"],
            ["Worker resolves or dismisses a flag", ref(BE + "api/routes/phc.py", "async def mark_seen"), "processed_data.resolution", "Dashboard open-flag count and score rise · History shows 'reviewed'"],
            ["Worker books a visit", ref(BE + "api/routes/phc.py", "async def book_visit"), "scheduled_visits; alerts; email", "Visits page · Alerts page · dashboard 'next visit' · email to the citizen"],
            ["Citizen cancels a visit", ref(BE + "api/routes/schedule.py", "async def cancel_mine"), "scheduled_visits (cancelled_by, reason)", "Worker's schedule card shows the reason · worker alert and email"],
            ["Visit time passes with no outcome", ref(BE + "services/visits.py", "async def notify_missed"), "alerts (once); `missed_notified_at`", "Both people alerted · citizen can explain · explained misses stop counting toward a complaint"],
            ["Citizen turns off 'health worker access'", ref(BE + "services/consent.py", "async def change_consents"), "consent_records", "Hidden from every worker query · open visits cancelled · `about` text changes"],
            ["Citizen turns off 'health tracking'", ref(BE + "services/consent.py", "if ConsentType.health_tracking in choices"), "consent_records, users.consent, profile", "Watch sync returns 403 · reminders stop"],
            ["Citizen turns on 'community monitoring'", ref(BE + "services/consent.py", "def counts_in_community"), "consent_records", "Counted (without name) in locality figures, the risk map and outbreak clustering"],
            ["Citizen changes centre", ref(BE + "api/routes/settings.py", "async def change_health_centre"), "users.phc_id, audit_logs", "Old centre's visits cancelled · new centre's workers see them · dashboard notice may clear"],
            ["Citizen changes email or notification choices", ref(BE + "api/routes/settings.py", "async def update_preferences"), "users.preferences", "`emails_about` / `emails_flag` decide every later email"],
            ["Quiet for 3 days", ref(BE + "services/reminders.py", "async def send_due"), "alerts; email", "Reminder on the Alerts page and by email, once per quiet stretch, between 09:00 and 20:00"],
            ["Admin publishes an advisory", ref(BE + "api/routes/advisories.py", "def targeting"), "advisories", "Appears on the matching citizens' Alerts page (Advisories tab)"],
            ["Citizen raises a complaint", ref(BE + "api/routes/settings.py", "async def raise_concern"), "concerns (with evidence)", "Admin's Complaints page; the reply returns to the citizen's Support tab"],
        ])
        + h2("Three journeys end to end")
        + h2("A. A flagged reading reaches a person who can act")
        + chain(["Watch sync", "score_reading flags SpO₂ 89", "ProcessedData + Alert", "Emails queued", "Commit", "Worker's Alerts card", "Worker books a visit", "Citizen toast + sound", "Visits page"])
        + h2("B. The citizen withdraws health-worker access")
        + chain(["Settings → Privacy", "PATCH /settings/consents", "change_consents", "ConsentRecord appended", "cancel_open_visits", "Worker queries skip the citizen", "Dashboard says nobody is reviewing"])
        + h2("C. A visit the citizen cannot attend")
        + chain(["Visit card (8+ hours away)", "Cancel with reason", "check_cutoff passes", "status = cancelled", "Worker alert with reason", "Slot freed on the worker's Schedule"])
        + note("**If the examiner asks 'how do two features communicate?'** answer with this chapter's pattern: one feature writes a row through a service function; the other reads that table through its own route. There is no feature-to-feature call, which is why a page can be rewritten without touching another.", "key")
    )))

    out.append(chapter("15", "API index for the citizen module", "c15", "Every endpoint a citizen's screens use, generated by scanning the route files, with the front-end function that calls it.", (
        table(["Endpoint", "Handler", "Called from"], endpoints.rows())
        + p("Handlers link to the first line of the function; the third column links to the line that makes the request.")
    )))

    out.append(chapter("16", "Data model cheat-sheet", "c16", "The tables the citizen module reads and writes, with the columns worth knowing.", (
        table(["Table (model)", "Key columns", "Defined at"], [
            ["<code>users</code>", "role, is_verified, is_active, profile_completed, consent, phc_id, district, state, pincode, area, geo_lat/lng, preferences (JSON), pending_email, deactivated_at", ref(BE + "models/user.py", "class User(")],
            ["<code>user_profiles</code>", "age, gender, height, weight, blood_group, conditions, medications, has_smartwatch, smartwatch_brand, emergency contact; one per user", ref(BE + "models/user_profile.py", "class UserProfile(")],
            ["<code>health_records</code>", "vitals (JSON), symptoms, timestamp (measured) vs created_at (stored), source (watch / phc / self), recorded_by, location, watch_day, watch_slot", ref(BE + "models/health_record.py", "class HealthRecord(")],
            ["<code>processed_data</code>", "features (per-vital contribution), anomaly_score, is_anomaly, basis, details (audit), population, resolution, reviewed_by, reviewed_at; one per reading", ref(BE + "models/processed_data.py", "class ProcessedData(")],
            ["<code>alerts</code>", "user_id, alert_type (personal / community), severity (low, medium, high), message, is_read", ref(BE + "models/alert.py", "class Alert(")],
            ["<code>scheduled_visits</code>", "worker_id, citizen_id, scheduled_for, status (scheduled, completed, cancelled, missed), visit_type, duration, reason, location, notes, cancelled_by, cancel_reason, missed_reason", ref(BE + "models/scheduled_visit.py", "class ScheduledVisit(")],
            ["<code>consent_records</code>", "consent_type, granted, source, ip_address, created_at; append-only; latest per type wins", ref(BE + "models/consent_record.py", "class ConsentRecord(")],
            ["<code>refresh_tokens</code>", "token_hash (SHA-256), expires_at, revoked, revoked_reason, last_activity_at, device_label, rotated_from", ref(BE + "models/refresh_token.py", "class RefreshToken(")],
            ["<code>concerns</code>", "ticket_ref, category, description, status, admin_note, subject_id, evidence (JSON)", ref(BE + "models/concern.py", "class Concern(")],
            ["<code>advisories</code>", "scope, district, area, radius_km, severity, body, expires_at, withdrawn_at, feedback", ref(BE + "models/advisory.py", "class Advisory(")],
            ["<code>valid_phc_facilities</code>", "the registry: name, code, district, state, latitude, longitude, is_active", ref(BE + "models/valid_phc_facility.py", "class ValidPhcFacility(")],
            ["<code>chat_sessions</code>, <code>chat_messages</code>", "Nira conversations; each answer stores its retrieval sources and whether it was grounded", ref(BE + "models/chat_message.py", "class ChatMessage(")],
            ["<code>audit_logs</code>", "who did what to which row from which IP (delete reading, change centre, deactivate)", ref(BE + "models/audit_log.py", "class AuditLog(")],
        ])
        + note("`created_at` and `timestamp` differ on purpose: **timestamp is when the vital was measured, created_at is when it was stored**. All queries about 'when the reading happened' use `timestamp`.")
    )))

    out.append(chapter("17", "Numbers to know", "c17", "Every threshold the examiner might ask about, with the line that defines it.", (
        table(["Setting", "Value", "Defined at"], [
            ["Access token lifetime", "15 minutes", ref(BE + "core/config.py", "ACCESS_TOKEN_EXPIRE_MINUTES")],
            ["Refresh token lifetime", "30 days", ref(BE + "core/config.py", "REFRESH_TOKEN_EXPIRE_DAYS")],
            ["Refresh idle timeout", "48 hours", ref(BE + "core/security.py", "REFRESH_IDLE_TIMEOUT")],
            ["Refresh reuse grace (two tabs)", "10 seconds", ref(BE + "core/security.py", "REFRESH_REUSE_GRACE")],
            ["Email verification link", "24 hours", ref(BE + "core/security.py", "VERIFICATION_TOKEN_TTL")],
            ["Password reset link", "1 hour", ref(BE + "core/security.py", "PASSWORD_RESET_TOKEN_TTL")],
            ["Resend an email", "60 seconds apart", ref(BE + "core/security.py", "EMAIL_RESEND_INTERVAL")],
            ["Password length", "8 characters minimum, 72 bytes maximum", ref(BE + "schemas/auth.py", "Password = Annotated")],
            ["Readings before a personal baseline starts", "7", ref(BE + "services/scoring.py", "MIN_BASELINE_READINGS =")],
            ["Readings for a fully personal baseline", "21", ref(BE + "services/scoring.py", "FULL_BASELINE_READINGS =")],
            ["Baseline looks at the latest", "30 readings of each vital", ref(BE + "services/scoring.py", "BASELINE_WINDOW =")],
            ["A vital counts toward a flag from", "contribution 0.5", ref(BE + "services/scoring.py", "FLAG_THRESHOLD =")],
            ["Contribution that equals score 1.0", "4.0", ref(BE + "services/scoring.py", "SCORE_CEILING =")],
            ["Earlier readings the scorer sees", "120", ref(BE + "services/readings.py", "SCORING_HISTORY =")],
            ["Severity bands", "critical 0.75, high 0.5, moderate 0.25", ref(BE + "services/triage.py", "BANDS")],
            ["Dashboard windows", "baseline 90 days, trend 30 days, up to 500 readings", ref(BE + "api/routes/vitals.py", "BASELINE_WINDOW_DAYS = 90")],
            ["History page size", "20 readings", ref(FE + "pages/citizen/History.tsx", "const PAGE_SIZE")],
            ["Badge refresh", "every 30 seconds", ref(FE + "components/app/AppShell.tsx", "const BADGE_POLL_MS")],
            ["Visit grace before 'no outcome'", "4 hours", ref(BE + "services/visit_state.py", "GRACE =")],
            ["Cancel or move a visit", "not within 8 hours; reason of 10+ characters", ref(BE + "api/routes/schedule.py", "CHANGE_CUTOFF =")],
            ["Complaint about missed visits", "3 unexplained in 90 days", ref(BE + "services/complaints.py", "MISSED_THRESHOLD =")],
            ["Reading reminder", "after 3 days quiet, hourly check, sent 09:00 to 20:00", ref(BE + "services/reminders.py", "READING_REMINDER_AFTER =")],
            ["Nira rate limit", "20 questions a minute", ref(BE + "core/config.py", "ASSISTANT_QUESTIONS_PER_MINUTE")],
            ["Image upload limits", "avatar 2 MB, cover 5 MB; PNG, JPEG, WebP", ref(BE + "api/routes/profile.py", "MAX_BYTES")],
        ])
    )))

    out.append(chapter("18", "Questions across the whole module", "c18", "Short answers with the place to open if the examiner says 'show me'.", (
        qa([
            ("Walk me through what happens when a citizen presses 'Fetch from watch'.", "Chapter 5 table, then chapter 6. In one breath: page calls `syncWatch` → route checks role, consent and the slot → `simulate` → `submit_reading` stores and scores → flagged readings create an alert and queue emails → the page shows the result and the badge poll shows the alert."),
            ("Where is the business logic and where is only plumbing?", "Routes are plumbing (auth, validation, call a service). The rules are in `app/services`: `scoring.py`, `readings.py`, `consent.py`, `visits.py`, `complaints.py`, `preferences.py`."),
            ("How do you make sure one citizen cannot see another's data?", "Every citizen query filters on `user.id` taken from the verified token, never from the request. Examples: `delete_reading`, `mark_read`, `_own_session`. A foreign id answers 'not found', the same as an unknown id."),
            ("What validates input?", "Pydantic models on every route (types, lengths, patterns) plus the same rules mirrored in the forms. Vitals are range-checked by `validate_vitals` in the request schema before a worker's examination is saved, and the watch simulator clamps its values to plausible limits."),
            ("What is stored about consent and why?", "Each change is a new `consent_records` row with time, source and IP, so we can show what a person agreed to and when; the latest row is the current choice."),
            ("How are emails prevented from being sent for a failed request?", "They are queued on the session and sent in a hook that runs after a successful commit; a rollback drops them (`_send_after_commit`, `_drop_after_rollback`)."),
            ("What happens if the model or email fails?", "The population model is optional (no model file means no population check). Email failures are logged with the address masked and do not fail the request."),
            ("How would you replace the simulated watch?", "Implement a function with the signature of `simulate` that calls the vendor API and returns the same four vitals; nothing else changes."),
            ("What are the limits of the scoring?", "It flags, it does not diagnose. The personal baseline needs about a week of data; until then only published ranges apply. Settings → Privacy and the flag explanations say so, and an emergency keyword gets 'call 108' immediately in Nira."),
            ("How is the app protected against someone stealing a session?", "Short access tokens, rotating refresh tokens with reuse detection, httpOnly cookie, idle timeout, a sessions page to sign out devices, and a password change signs out every other session."),
            ("What would you test first?", "Authorisation (foreign ids), the once-per-slot rule, consent effects, the 8-hour cancellation, scoring edge cases (fewer than 7 readings, safety limits, the confirmation rule). The test files in `backend/tests` are named by feature: test_auth, test_onboarding, test_watch, test_scoring, test_consents, test_notifications, test_modules."),
        ])
    )))
    return out
