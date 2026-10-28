from lib import bullets, chain, chapter, files, flow, functions, h2, md, note, p, qa, ref, table

BE, FE = "backend/app/", "frontend/src/"

ARCH_SVG = """
<svg viewBox="0 0 740 330" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif" font-size="12">
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#344e34"/></marker></defs>
  <g fill="#f4f7ee" stroke="#344e34" stroke-width="1.5">
    <rect x="10" y="10" width="340" height="52" rx="8"/><rect x="10" y="84" width="340" height="52" rx="8"/>
    <rect x="10" y="158" width="340" height="52" rx="8"/><rect x="10" y="232" width="340" height="52" rx="8"/>
  </g>
  <g fill="#fbf1d8" stroke="#d19a1b" stroke-width="1.5">
    <rect x="420" y="10" width="310" height="62" rx="8"/><rect x="420" y="92" width="310" height="62" rx="8"/>
    <rect x="420" y="174" width="310" height="62" rx="8"/><rect x="420" y="256" width="310" height="62" rx="8"/>
  </g>
  <g fill="#1c1c1a">
    <text x="22" y="32" font-weight="700">Worker pages (src/pages/phc)</text><text x="22" y="50" font-size="10.5">Dashboard · Alerts · Citizens · Schedule · Reports · Risk map</text>
    <text x="22" y="106" font-weight="700">services/phc.ts + api.ts</text><text x="22" y="124" font-size="10.5">Bearer token · refresh on 401 · one function per call</text>
    <text x="22" y="180" font-weight="700">/phc routes + schedule, advisories, clusters</text><text x="22" y="198" font-size="10.5">every /phc route runs require_catchment_worker first</text>
    <text x="22" y="254" font-weight="700">Services: catchment, localities, consent, visits</text><text x="22" y="272" font-size="10.5">who is in my catchment · area figures with a minimum size</text>
    <text x="432" y="32" font-weight="700">Catchment = same centre + consent</text><text x="432" y="50" font-size="10.5">users.phc_id match and phc_worker_access not withdrawn</text>
    <text x="432" y="114" font-weight="700">Flags come from the scorer</text><text x="432" y="132" font-size="10.5">processed_data rows the worker resolves or dismisses</text>
    <text x="432" y="196" font-weight="700">Community consent for area views</text><text x="432" y="214" font-size="10.5">reports, risk map and outbreaks count only opted-in people</text>
    <text x="432" y="278" font-weight="700">Audit trail</text><text x="432" y="296" font-size="10.5">viewing a record and recording an exam are logged</text>
  </g>
  <g stroke="#344e34" stroke-width="1.6" fill="none" marker-end="url(#a)">
    <path d="M180 62V84"/><path d="M180 136V158"/><path d="M180 210V232"/>
  </g>
  <g stroke="#d19a1b" stroke-width="1.4" stroke-dasharray="5 4" fill="none" marker-end="url(#a)">
    <path d="M350 258C390 258 390 41 420 41"/><path d="M350 262C380 262 390 123 420 123"/><path d="M350 266C380 266 390 205 420 205"/><path d="M350 270C372 270 394 287 420 287"/>
  </g>
</svg>"""


def build() -> list[str]:
    out = []

    out.append(chapter("0", "How to use this guide", "c0", "Every function named here has a clickable link that opens VS Code at the exact line.", (
        h2("Opening any line the examiner asks for")
        + bullets([
            "**Click the blue `path:line` link.** It uses the `vscode://file/…` address, so VS Code opens that file at that line.",
            "**Or type it.** In VS Code press `Ctrl+P`, paste `backend/app/api/routes/phc.py:374` and press Enter. Every link is written in this form.",
            "**If a link does nothing,** your PDF viewer is blocking the `vscode://` address; use the Ctrl+P method.",
            "**Line numbers are real.** They were looked up in the code when this PDF was generated. Regenerate with `python docs/phc_guide/build.py` (needs Chrome or Edge and PyMuPDF); a stale reference stops the build.",
        ])
        + note("**Shared with the citizen guide.** Sign-in tokens, `useResource`, error handling, the scoring pipeline and Nira work the same for every role. This guide points to the citizen guide for those and spends its pages on what is **specific to a health worker**: the catchment, the worklist, examinations, visits, area reports and approval.", "key")
        + h2("The idea in one picture")
        + chain(["Apply + proof of employment", "Admin approves and links a centre", "Citizens of that centre become the catchment", "Flags arrive in the worklist", "Resolve or dismiss", "Book a visit or record an examination", "Reports, map and outbreak signals"])
    )))

    out.append(chapter("1", "Architecture and the worker module map", "c1", "A worker sees only the citizens linked to their own health centre, and only those who have not withdrawn access.", (
        f'<div class="fig">{ARCH_SVG}</div>'
        + h2("The worker module at a glance")
        + table(["Feature", "Page", "Frontend service", "Backend route", "Rules in", "Main tables"], [
            ["Join (apply, documents, approval)", "PHCSignup, PendingApproval", "auth.ts, documents.ts", "routes/auth.py, applications.py, admin.py", "accounts.py, documents.py", "users, phc_applications, phc_verification_documents"],
            ["Dashboard", "phc/PhcDashboard.tsx", "phc.ts", "routes/phc.py (/dashboard, /overview)", "triage.py, catchment.py", "processed_data, health_records"],
            ["Alerts (worklist)", "phc/PhcAlerts.tsx", "phc.ts", "routes/phc.py (/worklist, /alerts)", "catchment.py", "processed_data"],
            ["Citizens", "phc/Citizens.tsx", "phc.ts", "routes/phc.py (/citizens)", "catchment.py, localities.py", "users, user_profiles"],
            ["Citizen record", "phc/CitizenRecord.tsx", "phc.ts", "routes/phc.py (/citizens/{id}/record)", "scoring.py, readings.py", "health_records, alerts, scheduled_visits"],
            ["Examination", "phc/RecordExam.tsx", "phc.ts", "routes/phc.py (POST readings)", "readings.py", "health_records (source = phc)"],
            ["Schedule", "phc/Schedule.tsx", "phc.ts", "routes/schedule.py, phc.py (POST /visits)", "visits.py, visit_state.py", "scheduled_visits"],
            ["Reports and risk map", "phc/Reports.tsx, RiskMap.tsx", "phc.ts", "routes/phc.py (/reports, /map)", "localities.py, consent.py", "health_records, users"],
            ["Outbreak signals", "Outbreaks.tsx", "outbreaks.ts", "routes/clusters.py", "outbreaks.py", "community_data"],
            ["Advisories", "Advisories.tsx", "advisories.ts", "routes/advisories.py", "(in the route)", "advisories"],
            ["Complaints about a citizen", "components/app/ReportCitizen.tsx", "account.ts, phc.ts", "routes/settings.py, phc.py", "complaints.py", "concerns"],
            ["Nira, profile, settings", "Assistant, Profile, Settings", "assistant.ts, account.ts", "assistant.py, profile.py, settings.py", "services/assistant", "chat_*, users"],
        ])
        + h2("Technology")
        + p("Identical to the citizen module: React 18 + TypeScript + Vite + Tailwind v4 in the browser, FastAPI + SQLAlchemy 2 (async) + PostgreSQL behind it, Alembic for schema versions, Recharts and Leaflet for the charts and maps. See the citizen guide, chapter 1, for the diagram and the table.")
    )))

    out.append(chapter("2", "Foundations for the worker: roles, catchment, badges", "c2", "Three ideas run through every worker screen: a worker must be approved, linked to a centre, and only sees consenting citizens of that centre.", (
        h2("2.1 The role ladder")
        + chain(["Signs up as pending_phc", "Admin approves → role phc_worker + phc_id set", "require_phc_worker", "require_catchment_worker (needs phc_id)"])
        + functions([
            ("require_phc_worker", BE + "core/dependencies.py", "async def require_phc_worker", "403 unless the account is an approved worker."),
            ("require_catchment_worker", BE + "services/catchment.py", "async def require_catchment_worker", "Approved **and** linked to a facility; otherwise 409. Without it a worker would read '0 flagged' as a quiet day when really no readings can reach them."),
            ("phc router", BE + "api/routes/phc.py", "router = APIRouter(prefix=\"/phc\"", "The guard is attached to the **whole router**, so a new `/phc` route cannot forget it."),
            ("ProtectedRoute (worker)", FE + "main.tsx", "allowedRoles={[\"phc_worker\"]} />}>", "Worker pages are wrapped for role `phc_worker`."),
            ("workerState / NoFacility", FE + "components/app/phc.tsx", "export function workerState", "Turns a 409 into a clear 'you are not linked to a facility' screen."),
        ])
        + h2("2.2 The catchment")
        + bullets([
            "A citizen is in a worker's catchment when **(1)** `users.phc_id` equals the worker's centre, **(2)** the account is a citizen, and **(3)** the citizen has **not withdrawn** 'health worker access'. Never having answered counts as yes.",
            "Every worker query starts from `catchment_ids(worker)` or `catchment_citizens(worker)`, so no route can accidentally list another centre's people.",
            "A citizen outside the catchment answers **the same 404** as one who does not exist (`get_catchment_citizen`), so ids cannot be probed.",
        ])
        + functions([
            ("catchment_citizens / catchment_ids", BE + "services/catchment.py", "def catchment_ids", "The one definition of 'my citizens' as a SQL query."),
            ("allows_worker_access", BE + "services/consent.py", "def allows_worker_access", "The consent check inside that query (default yes)."),
            ("in_catchment", BE + "services/catchment.py", "async def in_catchment", "Same rule for one citizen."),
            ("get_catchment_citizen", BE + "services/catchment.py", "async def get_catchment_citizen", "Loads a citizen or answers the uniform 404."),
            ("workers_serving", BE + "services/catchment.py", "async def workers_serving", "How many active workers a centre has; tells a citizen whether anyone reviews their flags."),
        ])
        + h2("2.3 The shell: navigation and badges")
        + functions([
            ("worker navigation", FE + "components/app/AppShell.tsx", "paths.phcAlerts, label: \"Alerts\"", "Dashboard, Alerts, Citizens, Schedule, Reports, Risk map, Outbreaks, Advisories, Notifications."),
            ("loadBadges", FE + "components/app/AppShell.tsx", "async function loadBadges", "For a worker calls `getPhcBadge`: unread notifications and citizens flagged."),
            ("phc_unread_count", BE + "api/routes/alerts.py", "async def phc_unread_count", "Counts distinct citizens with an open flag (the work waiting) and unread notifications."),
            ("newsBetween", FE + "components/app/AppShell.tsx", "function newsBetween", "When the flagged count **grows** between two polls a toast 'A citizen needs review' appears with the alert sound."),
        ])
        + qa([
            ("Why attach the guard to the router instead of each route?", "A forgotten dependency on one new route would expose a whole centre's citizens. On the router it is impossible to forget."),
            ("What happens to a worker whose approval is revoked?", "Their role goes back to `pending_phc`, `phc_id` is cleared, their booked visits are cancelled and the citizens told (`revoke` in admin.py). The next request fails the guard."),
            ("Why is 'worker access' default-yes?", "Choosing a centre at onboarding is what links the citizen to it. The consent is the way to withdraw, so only an explicit 'no' removes them from the catchment."),
        ])
    )))

    out.append(chapter("3", "Joining: apply, prove employment, get approved", "c3", "A worker applies with their employee details and proof; an administrator decides. Until then the account sees no health information.", (
        files([
            (FE + "pages/PHCSignup.tsx", "export function PHCSignup", "The application page; uses the same form as citizens with `variant=\"phc\"`."),
            (FE + "components/auth/SignupForm.tsx", "await registerPhcWorker(", "Employee ID, designation, centre name, district, state, years of service."),
            (FE + "pages/PendingApproval.tsx", "export function PendingApproval", "Progress steps, the proof-of-employment upload, 'Check status'."),
            (FE + "components/app/VerificationDocuments.tsx", "export function ApplicantDocuments", "Upload list with a status chip per file; the admin's review half is in the same file."),
            (BE + "services/accounts.py", "async def register_phc_worker", "Creates the user (role `pending_phc`) and the `PhcApplication` in one transaction."),
            (BE + "api/routes/applications.py", "async def upload", "`POST /phc-application/documents`: validate, store privately, run the checks."),
            (BE + "services/documents.py", "def judge", "Decides auto-passed, flagged or left for manual review."),
            (BE + "api/routes/admin.py", "async def approve", "Admin approval: sets the role, links the centre, sends the 'approved' alert."),
        ])
        + flow([
            ("Browser", "The form checks the employee ID pattern (for example TNPHC-CHN-2847) with the same rule the API uses.", FE + "components/auth/SignupForm.tsx", "await registerPhcWorker("),
            ("Router", "`POST /auth/register/phc-worker`; a verification email is queued like for a citizen.", BE + "api/routes/auth.py", "async def register_phc_worker"),
            ("Service", "One transaction creates the user as **pending_phc** and an application with status `pending`.", BE + "services/accounts.py", "return await _create(session, data, UserRole.pending_phc)"),
            ("Browser", "After verifying the email, `destinationFor` sends a pending account to the approval page.", FE + "lib/routes.ts", "case \"pending_phc\":"),
            ("Browser", "The worker uploads up to six proofs (ID card, appointment order, registration certificate).", FE + "components/app/VerificationDocuments.tsx", "await uploadDocument(type, file)"),
            ("Router", "Only a `pending_phc` applicant may upload; size at most 5 MB; the file's own first bytes must say JPEG, PNG or PDF.", BE + "api/routes/applications.py", "kind = documents.sniff(data[:8])"),
            ("Service", "The file is stored in a **private** folder (never served as a public URL) and its SHA-256 is saved.", BE + "services/documents.py", "def store"),
            ("Service", "`check` runs: the same file used by another person's application; image-editor traces in the metadata; low resolution; OCR text searched for the employee ID, the name and the centre.", BE + "services/documents.py", "async def check"),
            ("Service", "ID and name both found and nothing suspicious → `auto_passed`; neither found, or a high tamper score → `flagged`; otherwise left `pending` for a person.", BE + "services/documents.py", "findings.status = PhcDocumentStatus.auto_passed"),
            ("Router", "The admin reviews the application and its files, then approves with a centre.", BE + "api/routes/admin.py", "async def approve"),
            ("Database", "Approval sets `role = phc_worker`, `phc_id`, district and state and writes an audit entry; the worker gets an alert 'Your PHC worker account is approved'.", BE + "api/routes/admin.py", "user.role = UserRole.phc_worker"),
            ("Browser", "'Check status' refreshes the user; a worker now lands on the worker dashboard.", FE + "pages/PendingApproval.tsx", "const fresh = await refreshUser();"),
        ])
        + note("The automatic checks **assist the administrator, they do not decide**. 'Auto-passed' is a hint on the admin's screen; only an administrator can approve. Documents are opened by the admin through a logged endpoint, so every view is traceable.", "key")
        + qa([
            ("Why not let anyone who types an employee ID in?", "A worker can read health records. Approval by a person with evidence is the control, and the account has no access to anyone's data until then."),
            ("How do you stop a forged or reused document?", "Duplicate detection by SHA-256 across applicants, image-editor metadata, resolution, and OCR that must find the employee ID and name. Anything doubtful is flagged for the admin."),
            ("Can a worker upload documents after approval?", "No. `upload` and `remove` return 409 once the application is decided."),
            ("Where are the files kept?", "In `private_uploads`, outside the public media folder, under generated names."),
        ])
    )))
    return out
