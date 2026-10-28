from lib import bullets, chain, chapter, files, flow, functions, h2, note, p, qa, ref, table, tables

BE, FE = "backend/app/", "frontend/src/"


def build() -> list[str]:
    out = []

    out.append(chapter("11", "Nira, the records assistant (citizen view)", "c11", "A chat that answers from the citizen's own records. It retrieves with fixed SQL, then words the answer, then checks the numbers.", (
        chain(["Question", "Safety check", "Plan: pick queries", "Retrieve (read-only SQL)", "Word the answer", "Check every number", "Store with its sources"])
        + files([
            (FE + "pages/Assistant.tsx", "export function Assistant", "Chat list, greeting cards, composer, answer bubbles with a 'Based on' source line."),
            (FE + "services/assistant.ts", "export const askAssistant", "`POST /assistant/ask` and the session calls."),
            (BE + "api/routes/assistant.py", "async def ask", "Rate limit (20 a minute), chat ownership, then `assistant.ask`."),
            (BE + "services/assistant/__init__.py", "async def _answer", "The conductor: safety, plan, retrieve, write, verify."),
            (BE + "services/assistant/router.py", "EMERGENCY = re.compile", "Emergency and medical-advice rules, and the keyword planner used when Gemini is unavailable."),
            (BE + "services/assistant/catalog.py", "def tools_for", "The vetted SQL queries; 11 of the 29 are open to citizens."),
            (BE + "services/assistant/llm.py", "async def choose_tools", "Gemini function calling: chooses up to three queries; `write_answer` words the result."),
            (BE + "services/assistant/grounding.py", "def unsupported", "Finds numbers in an answer that are not in the retrieved rows."),
            (BE + "services/assistant/compose.py", "def compose", "Template answers, used when Gemini fails or its answer is rejected."),
        ])
        + flow([
            ("Browser", "`send` posts the question with the current chat id.", FE + "pages/Assistant.tsx", "const out = await askAssistant(content, activeId)"),
            ("Router", "Rate limit, then the chat is loaded and checked to belong to this user.", BE + "api/routes/assistant.py", "limit = get_settings().ASSISTANT_QUESTIONS_PER_MINUTE"),
            ("Service", "Emergency words get 'call 108' at once; diagnosis or medicine questions are declined.", BE + "services/assistant/__init__.py", "if router.EMERGENCY.search(question):"),
            ("Service", "Gemini (or the keyword router) picks which queries answer it, with cleaned parameters.", BE + "services/assistant/__init__.py", "async def _plan"),
            ("Database", "Each query runs in a **read-only** transaction with a timeout; `:me` is bound from the signed-in user, never from the question.", BE + "services/assistant/__init__.py", "async def retrieve"),
            ("Model", "Gemini writes the answer from those rows only.", BE + "services/assistant/llm.py", "async def write_answer"),
            ("Service", "Every number in the answer must appear in the rows; otherwise the template answer is used.", BE + "services/assistant/__init__.py", "missing = grounding.unsupported("),
            ("Database", "The question, answer, the sources and whether the numbers were checked are stored.", BE + "services/assistant/__init__.py", "answer = ChatMessage("),
            ("Browser", "The bubble shows 'Based on: …' and a 'Numbers checked' badge; the rows are one click away.", FE + "pages/Assistant.tsx", "function Sources"),
        ])
        + qa([
            ("Is this RAG?", "Yes: it retrieves private data at question time, adds it to the prompt and generates from it. The retriever is parameterised SQL instead of a vector search because the data is structured and needs exact counts, averages and access control."),
            ("Can the assistant read someone else's records?", "No. The scope (`:me`) is bound on the server from the signed-in user, the SQL is a fixed catalog the model cannot edit, and the transaction is read-only."),
        ])
    )))

    out.append(chapter("12", "Profile", "c12", "Name, contact details, photo and cover picture, and a safe way to change the sign-in email.", (
        files([
            (FE + "pages/Profile.tsx", "export function Profile", "Edit form, avatar and cover pickers, change-email form."),
            (FE + "pages/ConfirmEmail.tsx", "export function ConfirmEmail", "Opened from the link in the email to the new address."),
            (FE + "services/account.ts", "export const getProfile", "`getProfile`, `updateProfile`, `uploadImage`, `removeImage`, `requestEmailChange`, `confirmEmailChange`."),
            (BE + "api/routes/profile.py", "async def update_profile", "`GET/PATCH /profile`, images, email change."),
            (BE + "models/user.py", "class User(", "The columns edited here: name, phone, bio, location, date_of_birth, avatar_url, cover_url."),
        ])
        + functions([
            ("ProfilePatch", BE + "api/routes/profile.py", "class ProfilePatch", "Allowed fields only (`extra=forbid`); phone and date of birth are validated; bio at most 280 characters."),
            ("update_profile", BE + "api/routes/profile.py", "async def update_profile", "Applies only the fields that were sent; a name cannot be set empty."),
            ("_store", BE + "api/routes/profile.py", "async def _store", "Reads at most limit+1 bytes (2 MB avatar, 5 MB cover), checks the **file's own bytes** (`_sniff`), stores under an unguessable name and removes the old file."),
            ("_sniff", BE + "api/routes/profile.py", "def _sniff", "Recognises PNG, JPEG and WebP from their first bytes, not from the name or the browser's content type."),
            ("_remove_old", BE + "api/routes/profile.py", "def _remove_old", "Deletes only inside our own media folder; refuses path tricks."),
            ("request_email_change", BE + "api/routes/profile.py", "async def request_email_change", "Needs the current password; stores `pending_email` and a hashed token; mails the **new** address."),
            ("confirm_email_change", BE + "api/routes/profile.py", "async def confirm_email_change", "Public (the link opens on any device); swaps the address; mails the **old** address a notice."),
            ("ImagePicker", FE + "pages/Profile.tsx", "function ImagePicker", "Checks the size in the browser first, then uploads."),
        ])
        + h2("Changing the email address, end to end")
        + flow([
            ("Browser", "The form sends the new address and the current password.", FE + "pages/Profile.tsx", "const requestEmail = async"),
            ("Router", "Wrong password, same address, address already taken and 'asked within a minute' are each refused.", BE + "api/routes/profile.py", "if not verify_password(data.password, user.hashed_password):"),
            ("Database", "`pending_email` and the token **hash** with a 24-hour expiry are stored; the current address keeps working.", BE + "api/routes/profile.py", "user.pending_email = data.new_email"),
            ("Email", "The confirmation link goes to the new address only.", BE + "services/mailer.py", "async def send_email_change_email"),
            ("Browser", "The link opens `/confirm-email?token=…`.", FE + "pages/ConfirmEmail.tsx", "export function ConfirmEmail"),
            ("Router", "The token is checked, the address swapped, and a unique-constraint clash (someone registered it meanwhile) returns 409.", BE + "api/routes/profile.py", "user.email = new"),
            ("Email", "The old address gets 'your email was changed' so a hijack is noticed.", BE + "services/mailer.py", "async def send_email_changed_notice"),
        ])
        + qa([
            ("Why check the image's bytes?", "A file named `a.png` can be anything; content type headers are written by the sender. Checking the signature means only real PNG, JPEG or WebP files are stored."),
            ("Why mail the old address after the change?", "If someone with a stolen session changed the email, the owner finds out."),
        ])
    )))

    out.append(chapter("13", "Settings", "c13", "Five tabs. Each tab is one component in `Settings.tsx` and one group of endpoints in `settings.py`.", (
        files([
            (FE + "pages/Settings.tsx", "export function Settings", "The tab bar; the active tab lives in `?tab=`."),
            (FE + "services/account.ts", "export const getPreferences", "One function per settings call."),
            (BE + "api/routes/settings.py", "router = APIRouter", "Preferences, consents, about, export, password, deactivate, complaints, health centre."),
            (BE + "services/preferences.py", "def current_preferences", "Defaults, validation and the helpers notifications read."),
            (BE + "services/consent.py", "async def change_consents", "Records a choice and carries out what it means."),
            (BE + "services/complaints.py", "async def prepare", "Checks a complaint is allowed and attaches the app's evidence."),
        ])
        + table(["Tab", "Component", "Endpoints"], [
            ["Account & security", ref(FE + "pages/Settings.tsx", "function AccountTab"), "POST /settings/password, POST /settings/deactivate (and the Sessions page)"],
            ["Preferences", ref(FE + "pages/Settings.tsx", "function PreferencesTab"), "GET/PATCH /settings/preferences"],
            ["Privacy", ref(FE + "pages/Settings.tsx", "function PrivacyTab"), "GET/PATCH /settings/consents, GET /settings/consents/history, GET /settings/about, GET /settings/export"],
            ["Support", ref(FE + "pages/Settings.tsx", "function SupportTab"), "POST/GET /settings/concerns"],
            ["Your health centre", ref(FE + "pages/Settings.tsx", "function CentreTab"), "GET/PATCH /settings/health-centre"],
        ])
        + h2("13.1 Account and security")
        + flow([
            ("Browser", "Current and new password are sent.", FE + "pages/Settings.tsx", "await account.changePassword(current, next)"),
            ("Router", "The current password is verified; the new one must differ.", BE + "api/routes/settings.py", "async def change_password"),
            ("Service", "The hash is replaced and **every other session** is revoked; this device stays signed in.", BE + "api/routes/settings.py", "await sessions.revoke_all_for_user(db, user.id, sessions.REASON_PASSWORD_RESET, except_id=current)"),
            ("Router", "Deactivate needs the password **and** the typed word DEACTIVATE; it clears the account's access, cancels open visits, revokes sessions and writes an audit row.", BE + "api/routes/settings.py", "async def deactivate"),
            ("Guard", "A deactivated user fails `get_current_user` on the very next request.", BE + "core/dependencies.py", "if user is None or not user.is_active:"),
        ])
        + h2("13.2 Preferences")
        + bullets([
            "Stored as one JSON column on the user (`users.preferences`): theme, language (English, Tamil, Hindi), whether alerts and visits are also emailed, the **least severe flag worth an email**, and reading reminders.",
            "`PATCH` accepts any subset, **deep-merges** it into the current values and validates the merged result as a whole (`update_preferences`), so a partial save can never leave an invalid state.",
            "Everything is always shown in the app; these settings only choose what is **also emailed** (`emails_about`, `emails_flag` in `preferences.py`).",
        ])
        + functions([
            ("update_preferences", BE + "api/routes/settings.py", "async def update_preferences", "Merge, validate, store."),
            ("current_preferences", BE + "services/preferences.py", "def current_preferences", "Stored values over defaults; anything stored that no longer validates falls back to the default."),
            ("emails_flag", BE + "services/preferences.py", "def emails_flag", "True only if flag emails are on **and** the flag is at least as severe as the person's minimum."),
            ("PreferencesTab.save", FE + "pages/Settings.tsx", "const save = async (patch", "Sends the changed field; applies theme and language immediately."),
        ])
        + h2("13.3 Privacy: what each consent does")
        + table(["Consent", "Default if never answered", "Effect when off"], [
            ["Health tracking", "set at onboarding", "Watch sync returns 403 and no new readings are stored; reminders stop. Mirrored onto `users.consent` and the profile."],
            ["Health worker access", "**Yes**", "The citizen disappears from the centre's lists (`allows_worker_access`); open visits are cancelled (`cancel_open_visits`)."],
            ["Community monitoring", "**No**", "The citizen is left out of locality figures, the map and outbreak clustering (`counts_in_community`)."],
            ["Research", "**No**", "Left out of the de-identified research export (`in_research`)."],
        ])
        + functions([
            ("change_consents", BE + "services/consent.py", "async def change_consents", "Appends the choice, mirrors health tracking, cancels visits if worker access is withdrawn. Caller commits."),
            ("allows_worker_access / counts_in_community", BE + "services/consent.py", "def allows_worker_access", "SQL helpers every worker-side and area-level query includes."),
            ("about", BE + "api/routes/settings.py", "async def about", "Builds the plain-language 'who can see your data' sentence from the real consent state."),
            ("export", BE + "api/routes/settings.py", "async def export", "Downloads everything held about the citizen as one JSON file (profile, readings with scores, alerts, visits, consent history, complaints)."),
            ("PrivacyTab.change", FE + "pages/Settings.tsx", "await account.updateConsent(type, granted)", "Sends one change; reloads the list and the history."),
        ])
        + h2("13.4 Support (complaints)")
        + bullets([
            "A citizen can raise: smartwatch not syncing, a worker did not come, a worker's behaviour, a wrong flag, data misuse, an access request, app problem, other.",
            "`complaints.prepare` **attaches evidence from the app itself**: for a device complaint the last sync time and the readings by source; for a no-show the visits whose time passed with no outcome recorded.",
            "The citizen's list shows each request with its reference, status (open, in review, resolved or rejected) and the admin's reply (`admin_note`).",
        ])
        + functions([
            ("raise_concern", BE + "api/routes/settings.py", "async def raise_concern", "Creates the complaint with `subject_id` and `evidence` from `prepare`."),
            ("prepare", BE + "services/complaints.py", "async def prepare", "Validates the category for the role and gathers evidence."),
            ("_watch", BE + "services/complaints.py", "async def _watch", "Evidence for a smartwatch complaint."),
            ("SupportTab", FE + "pages/Settings.tsx", "function SupportTab", "Form and the citizen's own list."),
        ])
        + h2("13.5 Your health centre")
        + flow([
            ("Browser", "The tab lists active centres in the citizen's own district with how many workers each has.", FE + "pages/Settings.tsx", "function CentreTab"),
            ("Router", "`_health_centre` builds the list: active centres of the district, worker counts, which one is current.", BE + "api/routes/settings.py", "async def _health_centre"),
            ("Router", "Changing to a centre outside the district is refused.", BE + "api/routes/settings.py", "facility_serves_district(db, data.phc_id"),
            ("Service", "Visits booked by the old centre's workers are cancelled, since those workers lose sight of the citizen.", BE + "api/routes/settings.py", "await cancel_open_visits(db, user, unless_phc=data.phc_id)"),
            ("Database", "`user.phc_id` changes and an `AuditLog` row 'change_health_centre' is written.", BE + "api/routes/settings.py", "action=\"change_health_centre\""),
        ])
        + qa([
            ("What happens to readings already stored if the citizen changes centre?", "They stay with the citizen. The new centre's workers see them (subject to consent) because access is by the user's current `phc_id`."),
            ("Is anything deleted when an account is deactivated?", "No data is deleted; the account is switched off, sessions revoked and open visits cancelled. The export lets the person take their data."),
            ("Why is 'never answered' treated as yes for worker access but no for community monitoring?", "Choosing a centre at onboarding is what links the citizen to it, so worker access is the default and consent is how they withdraw. Area figures and research are optional extras that must be opted into."),
        ])
    )))
    return out
