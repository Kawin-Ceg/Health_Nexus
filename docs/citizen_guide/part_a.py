from lib import bullets, chain, chapter, files, flow, functions, h2, md, note, p, qa, ref, table, tables

BE, FE = "backend/app/", "frontend/src/"

ARCH_SVG = """
<svg viewBox="0 0 740 420" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif" font-size="12">
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#344e34"/></marker></defs>
  <g fill="#f4f7ee" stroke="#344e34" stroke-width="1.5">
    <rect x="10" y="10" width="330" height="52" rx="8"/><rect x="10" y="84" width="330" height="52" rx="8"/>
    <rect x="10" y="158" width="330" height="52" rx="8"/><rect x="10" y="232" width="330" height="52" rx="8"/>
    <rect x="10" y="306" width="330" height="52" rx="8"/><rect x="10" y="372" width="330" height="40" rx="8" fill="#344e34"/>
  </g>
  <g fill="#fbf1d8" stroke="#d19a1b" stroke-width="1.5">
    <rect x="420" y="40" width="310" height="62" rx="8"/><rect x="420" y="130" width="310" height="62" rx="8"/>
    <rect x="420" y="220" width="310" height="62" rx="8"/><rect x="420" y="310" width="310" height="62" rx="8"/>
  </g>
  <g fill="#1c1c1a">
    <text x="22" y="32" font-weight="700">Browser: React pages (src/pages)</text><text x="22" y="50" font-size="10.5">AuthContext · useResource · ProtectedRoute</text>
    <text x="22" y="106" font-weight="700">services/*.ts + api.ts (axios)</text><text x="22" y="124" font-size="10.5">adds Bearer token · on 401 refreshes once and retries</text>
    <text x="22" y="180" font-weight="700">FastAPI routers (app/api/routes)</text><text x="22" y="198" font-size="10.5">thin: validate input (Pydantic), call a service</text>
    <text x="22" y="254" font-weight="700">Guards (core/dependencies.py)</text><text x="22" y="272" font-size="10.5">who are you? which role? verified? onboarded?</text>
    <text x="22" y="328" font-weight="700">Services (app/services)</text><text x="22" y="346" font-size="10.5">all the rules: scoring, consent, visits, notify</text>
    <text x="22" y="397" font-weight="700" fill="#fff">SQLAlchemy models → PostgreSQL</text>
    <text x="432" y="62" font-weight="700">Background jobs (main.py lifespan)</text><text x="432" y="80" font-size="10.5">reading reminders hourly · outbreak clustering 6-hourly</text>
    <text x="432" y="152" font-weight="700">Scoring (the ML seam)</text><text x="432" y="170" font-size="10.5">scoring.py personal baseline + population.py (joblib)</text>
    <text x="432" y="242" font-weight="700">Email outbox</text><text x="432" y="260" font-size="10.5">notify.py queues, sends after commit via mailer.py</text>
    <text x="432" y="332" font-weight="700">Nira assistant</text><text x="432" y="350" font-size="10.5">services/assistant: SQL catalog + Gemini + checks</text>
  </g>
  <g stroke="#344e34" stroke-width="1.6" fill="none" marker-end="url(#a)">
    <path d="M175 62V84"/><path d="M175 136V158"/><path d="M175 210V232"/><path d="M175 284V306"/><path d="M175 358V372"/>
  </g>
  <g stroke="#d19a1b" stroke-width="1.4" stroke-dasharray="5 4" fill="none" marker-end="url(#a)">
    <path d="M340 326C380 326 380 71 420 71"/><path d="M340 332C372 332 380 161 420 161"/><path d="M340 336C366 336 390 251 420 251"/><path d="M420 341H340"/>
  </g>
</svg>"""

JOURNEY = chain(["Sign up", "Verify email", "Onboarding (profile + consent)", "Dashboard", "Smartwatch sync", "Score & flag", "Alert + email", "Worker books visit", "Visits / Alerts pages"])


def build() -> list[str]:
    out = []

    out.append(chapter("0", "How to use this guide", "c0", "Every function named here has a clickable link that opens VS Code at the exact line.", (
        h2("Opening any line the examiner asks for")
        + bullets([
            "**Click the blue `path:line` link.** It uses the `vscode://file/…` address, so VS Code opens that file at that line. If your PDF viewer asks permission, allow it once.",
            "**Or type it.** In VS Code press `Ctrl+P`, paste `backend/app/services/readings.py:79` and press Enter. Every link is written in this form.",
            "**Line numbers are real.** They were looked up in the code when this PDF was generated. If the code changes later, regenerate with `python docs/citizen_guide/build.py` (needs Chrome or Edge and PyMuPDF); a stale reference stops the build instead of printing a wrong number.",
            "**If a link does nothing,** your PDF viewer is blocking the `vscode://` address. Use the Ctrl+P method above; the text of every link is exactly what to type.",
        ])
        + note("Tip for the viva: say **which layer** first (page, API client, route, guard, service, table), then open the line. Every feature in this guide is walked in that order.", "key")
        + h2("The layers, in one line each")
        + table(["Layer", "Lives in", "Rule of thumb"], [
            ["Page / component", "<code>frontend/src/pages</code>, <code>components</code>", "Shows data, collects input, calls one service function."],
            ["Service (frontend)", "<code>frontend/src/services/*.ts</code>", "One function per API call; no UI."],
            ["Route", "<code>backend/app/api/routes</code>", "Checks who is asking and validates input, then calls a service."],
            ["Guard", "<code>backend/app/core/dependencies.py</code>", "Refuses the wrong role or an unverified account before the route runs."],
            ["Service (backend)", "<code>backend/app/services</code>", "The rules: scoring, consent, visits, notifications."],
            ["Model", "<code>backend/app/models</code>", "Table definitions; the only code that knows column names."],
        ])
    )))

    out.append(chapter("1", "Architecture and the citizen module map", "c1", "A browser app talks to one API; the API applies rules and stores everything in PostgreSQL.", (
        f'<div class="fig">{ARCH_SVG}</div>'
        + h2("Technology")
        + table(["Part", "What is used", "Where"], [
            ["UI", "React 18, TypeScript, Vite, Tailwind CSS v4, react-router 7, Recharts (charts), Leaflet (maps)", "<code>frontend/</code>"],
            ["API client", "axios instance with request and response interceptors", ref(FE + "services/api.ts", "export const api = axios.create")],
            ["API", "FastAPI (async), Pydantic v2 validation", ref(BE + "main.py", "app = FastAPI(")],
            ["Storage", "PostgreSQL through SQLAlchemy 2 (async, asyncpg); schema versions in Alembic (migrations 0001 to 0020)", "<code>backend/app/models</code>, <code>backend/alembic/versions</code>"],
            ["Passwords and tokens", "bcrypt hashes; JWT (HS256) access tokens; random refresh tokens stored only as SHA-256 hashes", ref(BE + "core/security.py", "def hash_password")],
            ["Anomaly scoring", "Personal-baseline rules plus a trained Isolation Forest (scikit-learn) that only informs", ref(BE + "services/scoring.py", "def score_reading")],
            ["Email", "Outbox sent after the database commit; prints to the console unless SMTP is configured", ref(BE + "services/notify.py", "def queue_email")],
            ["Assistant", "Gemini picks one of 29 vetted SQL queries and words the answer; a template answers if Gemini fails", "<code>backend/app/services/assistant</code>"],
        ])
        + h2("The citizen module at a glance")
        + JOURNEY
        + table(["Feature", "Page", "Frontend service", "Backend route", "Rules in", "Main tables"], [
            ["Account", "SignupPage, LoginPage, VerifyEmail, SessionsPage", "auth.ts", "routes/auth.py", "accounts.py, sessions.py", "users, refresh_tokens"],
            ["Onboarding", "Onboarding.tsx", "onboarding.ts", "routes/onboarding.py", "onboarding.py, consent.py", "user_profiles, consent_records"],
            ["Smartwatch", "citizen/Watch.tsx", "health.ts", "routes/vitals.py (/health/watch)", "watch.py, readings.py", "health_records, processed_data"],
            ["Dashboard", "citizen/Dashboard.tsx", "health.ts", "routes/vitals.py (/health/summary)", "scoring.py, readings.py", "health_records, alerts, scheduled_visits"],
            ["History", "citizen/History.tsx", "health.ts", "routes/vitals.py (/health/history)", "triage.py", "health_records, processed_data"],
            ["Alerts", "citizen/Alerts.tsx", "health.ts", "routes/alerts.py", "visits.py, notify.py", "alerts, advisories"],
            ["Visits", "citizen/Visits.tsx", "health.ts", "routes/schedule.py", "visits.py, visit_state.py", "scheduled_visits"],
            ["Nira", "Assistant.tsx", "assistant.ts", "routes/assistant.py", "services/assistant/*", "chat_sessions, chat_messages"],
            ["Profile", "Profile.tsx", "account.ts", "routes/profile.py", "(in the route)", "users"],
            ["Settings", "Settings.tsx", "account.ts", "routes/settings.py", "preferences.py, consent.py, complaints.py", "users, consent_records, concerns"],
        ])
    )))

    out.append(chapter("2", "Foundations every feature uses", "c2", "Sign-in state, guards, error handling and polling are written once and reused by every page.", (
        h2("2.1 The two tokens")
        + chain(["Login", "Access token (JWT, 15 min) kept in memory", "Refresh token (random, 30 days) in an httpOnly cookie", "401 → silent refresh → retry"])
        + bullets([
            "The **access token** is a signed JWT held only in a JavaScript variable (`accessToken` in `api.ts`). A page reload loses it on purpose; `AuthProvider` gets a new one from the refresh cookie at start-up.",
            "The **refresh token** is random, stored in the database only as a SHA-256 hash, sent as an `httpOnly` cookie limited to `/api/v1/auth`. JavaScript cannot read it, so a script injected into the page cannot steal it.",
            "Every refresh **rotates** the token. Presenting an old one again is treated as theft: the whole chain is revoked (`_revoke_chain`). A 10-second grace covers two tabs refreshing together.",
            "Each refresh token is valid for 30 days from when it was issued, and every refresh issues a new one, so an active person stays signed in. A session with **no refresh for 48 hours** is ended as idle (`REFRESH_IDLE_TIMEOUT`).",
        ])
        + functions([
            ("create_access_token / decode_access_token", BE + "core/security.py", "def create_access_token", "Signs and checks the 15-minute JWT (claims: user id, role, session id)."),
            ("hash_password / verify_password", BE + "core/security.py", "def hash_password", "bcrypt; passwords over 72 bytes are refused rather than silently cut."),
            ("get_current_user", BE + "core/dependencies.py", "async def get_current_user", "Decodes the token, then **reloads the user from the database**, so a deactivation or approval applies at once instead of after 15 minutes."),
            ("rotate_session", BE + "services/sessions.py", "async def rotate_session", "Validates a refresh token, revokes it, issues the next one; handles reuse, expiry and idle timeout."),
            ("_revoke_chain", BE + "services/sessions.py", "async def _revoke_chain", "Revokes every live descendant of a reused token (the thief's copy)."),
            ("request interceptor", FE + "services/api.ts", "api.interceptors.request.use", "Adds `Authorization: Bearer …` to every request."),
            ("refreshSession", FE + "services/api.ts", "export function refreshSession", "Single-flight refresh: concurrent callers share one request."),
            ("response interceptor", FE + "services/api.ts", "api.interceptors.response.use", "On a 401 it refreshes once and replays the request; login and refresh are never retried."),
            ("AuthProvider", FE + "context/AuthContext.tsx", "export function AuthProvider", "Holds `user` and `status`; restores the session on load; exposes login, logout, refreshUser."),
        ])
        + h2("2.2 Who may open what")
        + functions([
            ("require_user", BE + "core/dependencies.py", "async def require_user", "Citizen accounts only."),
            ("require_onboarding_user", BE + "core/dependencies.py", "async def require_onboarding_user", "A citizen **with a verified email**. Used by the health, schedule and watch routes."),
            ("require_any_verified", BE + "core/dependencies.py", "async def require_any_verified", "Any approved role with a verified email (settings, profile, alerts, assistant)."),
            ("ProtectedRoute", FE + "components/ProtectedRoute.tsx", "export function ProtectedRoute", "Signed out → login; wrong role → unauthorized; unverified → verify page; no profile yet → onboarding."),
            ("destinationFor", FE + "lib/routes.ts", "export function destinationFor", "The one place that decides where a user belongs after login."),
            ("route table", FE + "main.tsx", "allowedRoles={[\"user\"]} />}>", "Citizen pages are wrapped in `ProtectedRoute` for role `user`."),
        ])
        + note("The page guard is for **good behaviour**; the API guard is for **security**. A user who edits the front end still gets a 403 from the guard on the server.", "key")
        + h2("2.3 Fetching, errors, polling")
        + functions([
            ("useResource", FE + "lib/useResource.ts", "export function useResource", "Loads data when its key changes; aborts the old request so a slow earlier response can never overwrite a newer one; returns `data, error, loading, reload`."),
            ("normaliseDetail / ApiError", FE + "services/api.ts", "export function normaliseDetail", "FastAPI errors can be a string or a list; this turns both into one message plus per-field errors."),
            ("useBadges / loadBadges", FE + "components/app/AppShell.tsx", "function useBadges", "Polls unread counts every 30 s; when the count grows it shows a toast and plays the alert sound."),
            ("ToastProvider / play", FE + "components/app/Toaster.tsx", "export function ToastProvider", "One place for pop-up messages; each tone has a sound in `lib/sound.ts`."),
            ("fmtStamp", FE + "lib/format.ts", "export const fmtStamp", "The single date-and-time format used on every page (India time)."),
            ("useT / useLabel", FE + "i18n/index.ts", "export function useT", "English, Tamil and Hindi text."),
            ("lifespan", BE + "main.py", "async def lifespan", "Checks the JWT secret, starts the reminder and outbreak jobs, drains the email outbox on shutdown."),
            ("get_session", BE + "db/session.py", "async def get_session", "One database session per request."),
        ])
        + qa([
            ("Why keep the access token in memory and not in localStorage?", "Anything in localStorage can be read by any script on the page. A memory variable disappears on reload, and the refresh cookie (httpOnly, path-limited) brings it back."),
            ("What if two tabs refresh at the same moment?", "The browser side shares one request (`refreshSession`). On the server a token used within 10 seconds of rotation is answered with 'already used' without revoking anything, and the client retries after 400 ms."),
            ("Why reload the user on every request instead of trusting the role in the token?", "So that approving, deactivating or changing a role takes effect immediately (see the comment in `get_current_user`)."),
        ])
    )))

    out.append(chapter("3", "Account: sign-up, email verification, sign-in, sessions", "c3", "How a person becomes a verified, signed-in citizen, and how a session is protected.", (
        files([
            (FE + "pages/SignupPage.tsx", "", "Page shell; the form is `components/auth/SignupForm.tsx`."),
            (FE + "components/auth/SignupForm.tsx", "const form = useForm(", "Field rules, citizen vs worker sign-up, then logs in after registering."),
            (FE + "components/auth/LoginForm.tsx", "const user = await login(", "Email and password; goes to `destinationFor(user)`."),
            (FE + "pages/VerifyEmail.tsx", "export function VerifyEmail", "Redeems the emailed token once and lets the user resend (60 s apart)."),
            (FE + "pages/ForgotPassword.tsx", "export function ForgotPassword", "Asks for a reset link; the answer is the same whether or not the email exists."),
            (FE + "pages/ResetPassword.tsx", "export function ResetPassword", "Sets a new password from the emailed token."),
            (FE + "pages/account/SessionsPage.tsx", "export function SessionsPage", "Lists devices signed in; sign one or all others out."),
            (FE + "services/auth.ts", "export const registerCitizen", "One function per auth endpoint."),
            (BE + "api/routes/auth.py", "router = APIRouter", "Register, login, refresh, logout, verify, reset, sessions."),
            (BE + "services/accounts.py", "async def authenticate", "Create users, check passwords, issue and redeem one-time tokens."),
            (BE + "services/sessions.py", "async def start_session", "Refresh-token rows: start, rotate, revoke, list."),
            (BE + "services/mailer.py", "async def send_verification_email", "Builds and sends the verification and reset emails."),
        ])
        + h2("Sign-up to first sign-in, end to end")
        + flow([
            ("Browser", "The form checks the rules locally (the same rules the API enforces) and calls `registerCitizen`.", FE + "components/auth/SignupForm.tsx", "await registerCitizen(base)"),
            ("API client", "`POST /auth/register/citizen` with name, email, password.", FE + "services/auth.ts", "export const registerCitizen"),
            ("Router", "Validates the body: password 8 to 72 bytes, email normalised to lower case.", BE + "api/routes/auth.py", "async def register_citizen"),
            ("Service", "Creates the user (bcrypt hash, role `user`), makes a verification token and stores **only its hash** with a 24-hour expiry.", BE + "services/accounts.py", "async def register_citizen"),
            ("Email", "A background task emails a link to `/verify-email?token=…`.", BE + "services/mailer.py", "async def send_verification_email"),
            ("Browser", "The form then signs the new user in so they land on the verify page.", FE + "components/auth/SignupForm.tsx", "const user = await login(base.email"),
            ("Router", "`POST /auth/login`: `authenticate`, then `start_session`, then the refresh cookie is set and the access token returned.", BE + "api/routes/auth.py", "async def login"),
            ("Service", "`authenticate` gives the same error for an unknown email, a wrong password and a disabled account, and burns a hash check so timing does not reveal which.", BE + "services/accounts.py", "async def authenticate"),
            ("Browser", "`ProtectedRoute` sends an unverified user to the verify page.", FE + "components/ProtectedRoute.tsx", "if (!allowUnverified && !user.is_verified)"),
            ("Browser", "The emailed link opens the page, which removes the token from the address bar and redeems it once.", FE + "pages/VerifyEmail.tsx", "verifyEmail(token)"),
            ("Service", "`redeem_verification` marks the account verified and clears the token.", BE + "services/accounts.py", "async def redeem_verification"),
            ("Browser", "Verified but `profile_completed` is false, so the user is sent to onboarding (chapter 4).", FE + "lib/routes.ts", "return user.profile_completed ? paths.citizenHome"),
        ])
        + h2("Other flows in this feature")
        + functions([
            ("prepare_password_reset / redeem_password_reset", BE + "services/accounts.py", "async def prepare_password_reset", "Reset link valid for 1 hour and asked for at most once a minute; redeeming it signs out **every** session."),
            ("list_sessions / revoke_session", BE + "api/routes/auth.py", "async def list_sessions", "Backs the Sessions page; the current device is marked."),
            ("device_label / client_ip", BE + "services/sessions.py", "def device_label", "Turns the browser's user agent into 'Chrome on Windows' for the sessions list."),
            ("update_consent", BE + "api/routes/auth.py", "async def update_consent", "`PATCH /auth/consent`: a citizen changes consent; runs the same `change_consents` as Settings."),
        ])
        + qa([
            ("How do you stop someone discovering which emails have accounts?", "Login returns one message for every failure, forgot-password answers the same way whether or not the address exists, and a dummy hash check keeps response time similar."),
            ("Where is the verification token stored?", "Only its SHA-256 hash is in the database (`hash_token`); the raw value exists only in the email link, so a database leak does not give working links."),
            ("What happens if the user refreshes the verify page mid-way?", "The token is read once into state and removed from the URL; a `useRef` guard stops React StrictMode from spending the single-use token twice."),
        ])
    )))

    out.append(chapter("4", "Onboarding: profile, health centre and consent", "c4", "A new citizen answers five short steps; the answers decide which health centre sees their readings.", (
        files([
            (FE + "pages/Onboarding.tsx", "function OnboardingFlow", "The five-step wizard; the current step lives in the URL (`?step=`)."),
            (FE + "components/onboarding/steps.tsx", "export function PersonalStep", "One component per step: About you, Location, Medical, Device and contact, Consent."),
            (FE + "lib/onboardingDraft.ts", "export function loadDraft", "Keeps answers in `sessionStorage` per user, so a reload does not lose them."),
            (FE + "services/onboarding.ts", "export const createProfile", "`getStates`, `getDistricts`, `getFacilities`, `createProfile`."),
            (BE + "api/routes/onboarding.py", "async def create_profile", "Creates the profile and records consent in one transaction."),
            (BE + "services/onboarding.py", "async def resolve_facility", "Checks the chosen centre serves the chosen district; copies fields onto the rows."),
            (BE + "services/consent.py", "async def record_consents", "Appends a row for each choice that differs from the current state (a first answer, even a refusal, is always recorded). Rows are never edited."),
        ])
        + h2("What each step collects")
        + table(["Step", "Fields", "Why it is asked"], [
            ["1 About you", "age, gender, height, weight, blood group", "Shown on the health worker's record of the citizen."],
            ["2 Location", "state, district, health centre, pincode, area", "Links the citizen to the centre whose workers review their readings; the centre must serve that district."],
            ["3 Medical history", "conditions, medicines (tags)", "Gives a flag context for the worker."],
            ["4 Device and contact", "smartwatch yes/no and brand, emergency contact", "Decides whether the Smartwatch page starts connected."],
            ["5 Consent", "health tracking, health-worker access, community surveillance", "Each is recorded with time, source and IP; all can be changed later in Settings."],
        ])
        + flow([
            ("Browser", "Each step is validated with the same rules as the API; the user cannot jump past an invalid step (`firstInvalidStep`).", FE + "pages/Onboarding.tsx", "const firstInvalidStep"),
            ("Browser", "The location step loads states, districts and centres in turn from the registry.", FE + "components/onboarding/steps.tsx", "export function LocationStep"),
            ("Router", "The three list endpoints read the registry (`valid_phc_facilities`).", BE + "api/routes/onboarding.py", "async def facilities"),
            ("Browser", "On the last step `createProfile` sends everything in one request.", FE + "pages/Onboarding.tsx", "await createProfile(toPayload(v))"),
            ("Service", "`resolve_facility` rejects a centre that does not serve the district.", BE + "services/onboarding.py", "async def resolve_facility"),
            ("Router", "One transaction creates the profile, links the centre, sets `profile_completed`, mirrors health-tracking consent onto the account and writes consent rows. A double submit hits a unique constraint and returns 409.", BE + "api/routes/onboarding.py", "user.profile_completed = True"),
            ("Browser", "The draft is cleared, `refreshUser` reloads the account, and the citizen lands on the dashboard.", FE + "pages/Onboarding.tsx", "navigate(paths.citizenHome"),
        ])
        + qa([
            ("Why one transaction?", "Profile, centre link, completed flag and consent rows must exist together or not at all; a half-finished onboarding would leave an account that can neither log readings nor retry."),
            ("What if the second tab submits too?", "The unique `user_id` on the profile raises `IntegrityError`; the route turns it into a 409 and the page treats that as 'already saved'."),
            ("Where is the 'consent' stored and can it be changed?", "Append-only `consent_records` with time, source and IP; the latest row per type wins (`current_consents`). Settings → Privacy adds new rows, so the history of choices is kept."),
        ])
    )))
    return out
