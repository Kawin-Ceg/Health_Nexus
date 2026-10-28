# HealthNexus demo readiness

This guide gives every teammate the **same demo accounts and the same scenarios** on their own local PostgreSQL database. Nobody copies anyone else's database. You run the committed migrations and the committed seed script, and you get identical logins and logically identical data.

Everything the seed creates is **synthetic demo data**. The people, readings and outbreaks are invented, and they are not real patients or real epidemiological evidence. The health centre list is a placeholder registry: the districts are real, the centres stand in for the official list.

---

## 1. What you need

| Tool | Version used to verify this guide | Notes |
|---|---|---|
| PostgreSQL | 18.1 (any recent version works) | Runs locally; each teammate has their own |
| Python | 3.12 (per `backend/pyproject.toml`; also verified on 3.14) | `uv` or `pip` |
| Node.js | 20.19 | For the Vite frontend |
| Chrome / Edge | any | For the demo itself |

Optional:

- **`GEMINI_API_KEYS`**: lets Gemini word the assistant's answers. Without a key, the assistant uses its built-in rule-based router and templates (see section 9).
- **Tesseract** (`TESSERACT_CMD`): reads text from uploaded ID documents. Without it, document checks still run but skip the text-reading step.
- **SMTP**: not needed. Without it, emails are logged instead of sent.

---

## 2. One-time setup (each teammate)

All commands run from the repository root unless a `cd` is shown. Windows users can run them in Git Bash; PowerShell works too (see the notes in step 3).

```bash
# 1. Get the latest code
git pull

# 2. Backend dependencies
cd backend
uv sync                         # or: python -m venv .venv && .venv/Scripts/activate && pip install -r requirements.txt
# with uv, prefix the Python commands below with "uv run", e.g. "uv run alembic upgrade head"

# 3. Create your own local database (pick any name)
createdb -U postgres healthnexus_demo
```

If `createdb` is not on your PATH, or your PostgreSQL user can't create databases, either:

- use pgAdmin (Databases, then Create, then Database), or
- run `psql -U postgres -c "CREATE DATABASE healthnexus_demo;"`, or
- reuse an existing empty database you own.

You only need a database that the user in `DATABASE_URL` can create tables in.

```bash
# 4. Configure your local environment (never commit .env)
cp .env.example .env
```

Edit `backend/.env`:

```ini
DATABASE_URL=postgresql+asyncpg://<your-pg-user>:<your-pg-password>@localhost:5432/healthnexus_demo
JWT_SECRET_KEY=<any long random string, e.g. output of: python -c "import secrets;print(secrets.token_urlsafe(48))">
DEMO_MODE=true
DEMO_PASSWORD=HealthNexus-Demo-2026      # keep exactly this so everyone's logins match
```

```bash
# 5. Create the schema with the committed migrations
alembic upgrade head            # (run inside backend/)

# 6. Load the demo data
python -m app.seeds.seed_demo   # (run inside backend/)
```

```bash
# 7. Start the backend (terminal 1, inside backend/)
uvicorn app.main:app --reload --port 8000

# 8. Start the frontend (terminal 2)
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

Open http://localhost:5173/login and sign in with an account from section 4.

**PowerShell:** use `copy .env.example .env` instead of `cp`. To point one command at a different database without editing `.env`, run `$env:DATABASE_URL = "..."` first.

---

## 3. The seed command

```bash
cd backend
python -m app.seeds.seed_demo
```

What it does, in order. Every step is idempotent: accounts are matched by fixed email or facility code, and existing records are skipped.

| Step | Script | Creates |
|---|---|---|
| 1 | `seed_phc_facilities` | 190 placeholder health centres across the 38 Tamil Nadu districts (updated in place on re-runs) |
| 2 | `seed_directory` | One approved PHC worker per centre, and one admin per district |
| 3 | `seed_admin` | The demo admin `admin.demo@example.com` |
| 4 | `seed_phc_worker` | Main PHC worker `phc.worker@example.com` at Mylapore PHC |
| 5 | `seed_citizen` | `citizen.demo@example.com`: 90 days of readings, reviewed and open flags, a done visit, a booked visit, an assistant chat |
| 6 | `seed_demo_catchment` | 27 more citizens at Mylapore (`citizen01` to `citizen27@example.com`), 14 days of readings each, 7 with health episodes |
| 7 | `seed_demo` (second catchment) | 5 scenario citizens at Adyar PHC, looked after by `tn-chn-phc-002@phc.example.com` |
| 8 | `seed_admin_workflow` | 3 pending worker applications (with an ID document), citizen concerns, and an admin advisory |
| 9 | `seed_complaints` | A worker's complaint about a citizen who missed 3 visits, and a smartwatch complaint |
| 10 | `seed_outbreak` | Fever readings in Mandaveli, then a real run of the outbreak detector |
| 11 | `seed_demo` | Sets `DEMO_PASSWORD` on every demo-owned account (see the safety notes in section 6) |

Every reading goes through the same scoring path as `POST /health/vitals`: personal baseline, the trained population model (`model/artifacts/vitals_anomaly.joblib`, committed), and the published normal ranges. Flags come from the real model, not from hand-set values.

**Dates are relative to the day you run it.** Readings cover the days before the run, so seed on or just before demo day to get "last 7 days" charts that look fresh.

### Safety checks built in

- It refuses to run unless `DEMO_MODE=true`, so demo accounts never appear by accident. Keep `DEMO_MODE=false` anywhere real.
- It refuses to run unless `DEMO_PASSWORD` is set (10+ characters).
- It refuses to run if the database isn't at the latest migration, and tells you to run `alembic upgrade head`.
- Each step runs in its own transaction and rolls back on failure.
- It never drops, truncates or deletes anything, and never touches accounts outside the demo set.

---

## 4. Demo logins

**Password for every account below:** `HealthNexus-Demo-2026` (the value of `DEMO_PASSWORD`; demo-only, never reuse it).

| Role | Login | Who / scenario |
|---|---|---|
| Admin | `admin.demo@example.com` | Demo Admin. App-wide admin: applications, accounts, centres, complaints, advisories, outbreaks, audit trail |
| PHC worker | `phc.worker@example.com` | Kavitha Raman, Mylapore PHC (Chennai). 28 citizens, flagged people to review, visits, a complaint, a fever cluster in Mandaveli |
| PHC worker | `tn-chn-phc-002@phc.example.com` | Suresh Raman, Adyar PHC (Chennai). 5 scenario citizens, one visit needing an outcome, one booked |
| Citizen | `citizen.demo@example.com` | Anjali Venkatesan (Mylapore). 90 days of history, known hypertension, blood pressure high for the last 4 days, booked visit, assistant chat, concerns |
| Citizen | `adyar.stable@example.com` | Selvi Murugan (Adyar). 28 days of stable readings, no flags, a completed check-up, a read reminder |
| Citizen | `adyar.bp@example.com` | Murali Krishnan (Adyar). Normal for 25 days, then blood pressure above 160/98 for 3 days with headache; home visit booked |
| Citizen | `adyar.glucose@example.com` | Balaji Natarajan (Adyar). Blood glucose slowly rising for a month, then above 200 mg/dL; older flags reviewed; a centre visit now overdue for an outcome |
| Citizen | `adyar.heartrate@example.com` | Kavya Srinivasan (Adyar). Resting heart rate climbing over the last week (a change against her own baseline), palpitations |
| Citizen | `adyar.new@example.com` | Farhan Ali (Adyar). Only 3 readings, so there's too little data for a personal baseline; an unread "time for a reading" reminder |

These also exist, with the same password:

- `citizen01` to `citizen27@example.com` (Mylapore catchment).
- One PHC worker per centre (`tn-<district>-phc-<nnn>@phc.example.com`) and one admin per district (`admin.<district>@admin.example.com`). The full list is written to `backend/SEED_ACCOUNTS.md`, which is git-ignored.
- 3 pending applicants: `lakshmi.applicant@`, `arun.applicant@` and `deepa.applicant@example.com`. They can't use the app until an admin approves them; that's part of the demo.

---

## 5. Record counts

These are the counts from running the seed on a **fresh, empty database**, verified on 28 Oct 2026. Every teammate's fresh database gets the same numbers.

| Entity | Count |
|---|---|
| Health centres | 190 |
| Admins | 39 (1 demo admin, plus 38 district admins) |
| PHC workers | 191 (190 directory workers, plus `phc.worker@example.com`) |
| Pending worker applicants | 3 |
| Citizens | 33 (28 Mylapore, plus 5 Adyar) |
| Readings | 625 |
| Flagged readings | 75 |
| Visits | 9 |
| Alerts and notifications | 77 |
| Concerns and complaints | 5 |
| Advisories | 2 |
| Assistant chats | 1 |
| Worker applications | 194 |

A second run printed `added 0` for every row. Your numbers will be higher if your database already had other records; the seed prints a before/after table every time.

---

## 6. Re-running safely, and existing databases

- Run `python -m app.seeds.seed_demo` as often as you like. Existing demo accounts and their data are skipped, and nothing is duplicated.
- If you seeded weeks ago and want fresh "last 7 days" data, create a new empty database, point `DATABASE_URL` at it, and run steps 5 and 6 again. The seed never deletes old demo data itself.
- On a database that already has your own accounts: those accounts are not changed. The seed only touches:
  - the fixed demo emails listed above, and
  - addresses ending in `@phc.example.com` or `@admin.example.com`.

  If one of those already exists (for example from an older seed run), its password is reset to `DEMO_PASSWORD` so the logins above work. Nothing else about it changes.
- `alembic upgrade head` on an existing database only applies the migrations it's missing. It doesn't touch your data.

---

## 7. Recommended demo walkthrough

Use two browser profiles (or one normal and one private window) so you can stay signed in as two roles at once.

1. **Admin**, signed in as `admin.demo@example.com`.
   - The dashboard shows waiting applications, open concerns, flags across all centres, accounts by role, and PHC worker activity (pick *Mylapore PHC*).
   - On **Applications**, open Lakshmi Narayanan to see the uploaded ID card and the automatic checks, then approve or reject.
   - **Health centres** lists all 190 centres, with search and filters.
   - **Complaints** has the worker's complaint about missed visits, with evidence.
   - **Outbreaks** shows the fever cluster detected in Mandaveli.
   - **Advisories** shows the monsoon fever advisory.
2. **PHC worker**, signed in as `phc.worker@example.com`.
   - The dashboard shows the people needing review (click a row for details, mark seen, or book a visit), the severity and engagement breakdowns, and the last 8 weeks.
   - **Citizens** lets you open Anjali Venkatesan's record and history.
   - **Schedule** shows visits; **Reports** shows readings per day and the locality breakdown; **Risk map**; **Notifications** shows visit updates, marked read one at a time.
3. **Stable citizen**, signed in as `adyar.stable@example.com`: health score near 100, steady trend charts, nothing flagged.
4. **Unusual readings**, two accounts:
   - `adyar.bp@example.com`: blood pressure jumped against their own baseline, flagged readings, and a booked home visit.
   - `adyar.heartrate@example.com`: a gradual heart rate change that is flagged as unusual for this person, even though it stays near the population normal.
5. **Too little data**, signed in as `adyar.new@example.com`: 3 readings, the baseline still learning, values checked against published normal ranges only, and a pending reminder under Alerts.
6. **Reminders, assistant and community**, signed in as `citizen.demo@example.com`:
   - Alerts and advisories, and visits (one done, one booked).
   - **Nira** (the assistant): ask "How has my blood pressure been this week?"
   - **Smartwatch**: simulate a sync.
7. **Persistence and roles.**
   - Refresh the browser: you stay signed in and the data is unchanged.
   - Sign in as `tn-chn-phc-002@phc.example.com` to see only the 5 Adyar citizens. The Mylapore citizens aren't visible, because workers see only their own centre.

---

## 8. Checking your setup

With the backend running, from `backend/`:

```bash
python tests/demo_smoke.py http://localhost:8000
```

It is read-only: it signs in as each demo account and checks the main pages and the access boundaries. Result on the verification database: **80 passed, 0 failed**. Among other things it checks that:

- the Adyar worker sees exactly 5 citizens and the Mylapore worker 28;
- each worker gets 403/404 on the other centre's citizen records;
- citizens get 403 on the PHC and admin APIs, and workers get 403 on the admin API;
- the new citizen's baseline is still learning, while the others' baselines are established.

---

## 9. Live features vs. fallbacks

| Feature | What runs in the demo |
|---|---|
| Anomaly flags (personal baseline, population model, normal ranges) | **Live.** Every seeded reading is scored by the real pipeline |
| Outbreak detection | **Live.** The seed runs the real clustering on the seeded fever readings |
| Assistant (Nira) | **Live retrieval** over the citizen's own data. Answers are worded by Gemini if `GEMINI_API_KEYS` is set; otherwise by the built-in templates and rule-based router (an intended fallback, not fake output). The one seeded chat is a stored example conversation |
| ID document checks for applications | **Live** checks; text reading needs Tesseract |
| Smartwatch | **Simulated** sync in the app (there is no real device integration) |
| Email | Logged, not sent, unless SMTP is configured |

---

## 10. Troubleshooting

| Message | Fix |
|---|---|
| `DEMO_MODE is not true` | Set `DEMO_MODE=true` in `backend/.env` (local demo database only) |
| `set DEMO_PASSWORD` | Add `DEMO_PASSWORD=HealthNexus-Demo-2026` to `backend/.env` |
| `cannot reach the database` | Start PostgreSQL; check the host, port, user, password and database name in `DATABASE_URL`; create the database (section 2) |
| `the database has no schema yet` / `is at migration …` | Run `alembic upgrade head` in `backend/` |
| Login says wrong password | Run the seed again: it resets the demo accounts to `DEMO_PASSWORD`. Check there are no stray spaces in `.env` |
| Frontend shows network errors | Make sure the backend is on port 8000 (Vite proxies `/api` there), and `CORS_ORIGINS` / `FRONTEND_URL` match `http://localhost:5173` |
| One 401 in the browser console on the login page | Expected: the app checks for an existing session before you sign in |
| "Last 7 days" looks empty | The data is dated relative to when you seeded; reseed into a fresh database (section 6) |

---

## 11. Known limitations

- **Not covered:** sleep and step/activity data. The app has no sleep or activity measurements; it records 8 vitals (blood pressure, heart rate, temperature, SpO₂, breathing rate, glucose, weight) plus symptoms.
- **Dates move:** seeded dates are relative to the run time, so two teammates who seed on different days get the same scenarios shifted in time.
- **Partial updates on re-run:** idempotency is per account. If a demo account already exists, its data is not re-created or updated, which keeps re-runs safe. The exceptions are the password reset and the facility registry refresh.
- **Not run:** the backend's pytest suite, as part of this setup work. The checks that were run are listed in section 8, plus a migration-drift check (`alembic check`: no differences), a fresh-database run, a second idempotent run, and a run on a database with an unrelated pre-existing user (left unchanged).

### Files

- `backend/app/seeds/seed_demo.py` is the single entry point. The other `backend/app/seeds/*` scripts are the steps it runs.
- `backend/tests/demo_smoke.py` is the read-only post-seed check.
- `backend/.env.example` holds `DEMO_MODE` and `DEMO_PASSWORD`.
- `backend/alembic/versions/` holds the migrations (0001 to 0020), unchanged by this work.
