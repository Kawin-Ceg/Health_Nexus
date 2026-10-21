# 🩺 HealthNexus

> **AI-powered healthcare intelligence for individuals, communities, and underserved regions.**

HealthNexus is a healthcare intelligence platform designed to combine **personal health monitoring, AI-powered health assistance, rural healthcare accessibility, and community disease intelligence** into a unified system.

The goal is to move healthcare from reactive treatment toward **continuous monitoring, early awareness, and data-driven prevention**.

---

## 🌐 Vision

Build an intelligent healthcare ecosystem that can:

* Help individuals understand and monitor their health.
* Provide personalized, context-aware health insights.
* Improve access to healthcare services in rural and underserved regions.
* Detect meaningful disease trends at the community level.
* Use AI responsibly while keeping privacy and security at the core.

---

## ✨ Core Modules

### 🩺 1. Personal Health Intelligence

A personalized health layer that helps users track and understand their health data.

**Planned capabilities:**

* Health profile management
* Health metric tracking
* Heart rate monitoring
* Sleep monitoring
* Blood pressure
* Blood oxygen (SpO₂)
* Blood glucose
* Weight tracking
* AI-powered health insights
* Health history and trends
* Smart health reminders

---

### 🏥 2. Rural Healthcare Access

A healthcare discovery and accessibility layer focused on rural and underserved communities.

**Planned capabilities:**

* Healthcare facility discovery
* Hospital and clinic information
* Doctor and specialist discovery
* Location-aware healthcare access
* Healthcare resource mapping
* Accessibility-oriented recommendations

---

### 🦠 3. Community Disease Intelligence

A population-level intelligence layer designed to identify health patterns from aggregated and privacy-aware data.

**Planned capabilities:**

* Disease trend analysis
* Community health indicators
* Anomaly detection
* Emerging health-pattern detection
* Geographic health visualization
* Data-driven alerts and insights

---

### 🤖 4. AI Health Assistant

A chat assistant for citizens, PHC workers and administrators that answers questions from the user's own HealthNexus records (SQL-driven retrieval-augmented generation):

* Each role has a fixed catalog of read-only, parameterized SQL queries (`backend/app/services/assistant/catalog.py`); the model never writes SQL
* The caller's scope (their own records, or their health centre's catchment) is bound on the server
* Gemini, when `GEMINI_API_KEYS` is set, picks the query and words the answer from the returned rows; without a key, a rule-based router and templated answers are used
* Every answer is stored with the SQL that ran and the rows it used, and the chat shows them
* Requests for a diagnosis or medicine advice are declined; emergencies are pointed to 108

> **Note:** HealthNexus is intended to assist users with healthcare information and decision support. It is not a replacement for qualified medical professionals.

---

## 🏗️ Architecture

HealthNexus follows a modular architecture:

```text
                         ┌─────────────────────┐
                         │      Frontend       │
                         │   React + TypeScript│
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │       Backend       │
                         │       FastAPI       │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
      Personal Health       Healthcare Access     Community Intelligence
        Intelligence              │                     │
              │                   │                     │
              └───────────────────┼─────────────────────┘
                                  ▼
                         ┌─────────────────────┐
                         │    AI / ML Layer    │
                         │   LLM + RAG + ML    │
                         └─────────────────────┘
```

---

## 🛠️ Tech Stack

### Frontend

* React
* TypeScript
* Vite
* Tailwind CSS
* React Router
* Axios
* Recharts

### Backend

* Python
* FastAPI
* REST APIs

### AI / ML

* Python
* Scikit-learn
* LLMs
* RAG
* Embeddings
* Vector Search

### Data & Infrastructure

* PostgreSQL
* Docker
* Git & GitHub

> The technology stack may evolve as the project develops.

---

## 📁 Project Structure

```text
HealthNexus/
│
├── frontend/
│   ├── src/
│   ├── components/
│   ├── pages/
│   └── services/
│
├── backend/
│   ├── app/
│   ├── api/
│   ├── core/
│   ├── services/
│   ├── schemas/
│   └── models/
│
├── model/                  # anomaly model: code, training, evaluation, trained artifacts
│   ├── healthnexus_ml/     # preprocessing.py, anomaly.py, vitals.py, train.py, evaluate.py
│   ├── artifacts/          # vitals_anomaly.joblib (loaded by the API) + model card
│   ├── notebooks/          # the research write-up (01-04)
│   ├── reports/            # evaluation metrics and figures
│   └── tests/
│
├── docs/
│   ├── ARCHITECTURE.md
│   └── API.md
│
├── .gitignore
└── README.md
```

---

## 🚀 Running Authentication & Onboarding

The first module is **accounts, sign-in and citizen onboarding**. Every other page is a labelled placeholder ("coming in a later module"). The database schema already exists; nothing here creates or changes it.

**You need:** Python 3.12+, Node 20+, and PostgreSQL with the schema migrated (`alembic upgrade head`).

### 1. Backend

```bash
cd backend
pip install -r requirements.txt          # or: uv sync
cp .env.example .env                     # then edit .env
```

In `backend/.env` set at least:

| Variable | Notes |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@localhost:5432/healthnexus` |
| `JWT_SECRET_KEY` | 32+ characters. `python -c "import secrets; print(secrets.token_urlsafe(48))"` |

Leave `SMTP_HOST` empty in development: verification and password-reset emails are **printed in the API's terminal**, links included. Set `SMTP_*` to send real mail. `.env.example` lists every variable.

```bash
python -m app.seeds.seed_phc_facilities  # onboarding needs at least one health centre (placeholder data)
uvicorn app.main:app --reload --port 8000
```

Interactive docs: <http://localhost:8000/docs>. All routes are under `/api/v1`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                              # http://localhost:5173
```

The dev server proxies `/api` to `http://localhost:8000` (`VITE_API_PROXY_TARGET` to change it), so the app and API share an origin and the `hn_refresh` cookie needs no CORS setup.

### 3. Try it

1. Open <http://localhost:5173/signup>, create an account. You are signed in and asked to check your inbox.
2. Copy the verification link from the **backend terminal** and open it (any browser works, no session needed).
3. Back in the app press *I have verified my email*. You are sent to `/onboarding`: five steps, then the dashboard placeholder.
4. `/signup/phc-worker` creates a `pending_phc` account and an application row; it lands on `/pending-approval`.
5. `/account/sessions` lists where you are signed in.

### How sign-in works

- **Access token**: a 15-minute JWT, held in memory only (never `localStorage`), sent as `Authorization: Bearer`.
- **Refresh token**: 30 days, in an `httpOnly` cookie `hn_refresh` (`SameSite=Lax`, path `/api/v1/auth`). Only its SHA-256 digest is stored. Every `/auth/refresh` **rotates** it (old row revoked, `rotated_from` set to it).
- **Reuse**: presenting an already-rotated token is rejected. Once a few seconds have passed it is treated as theft and the whole rotation chain is revoked. Inside those seconds (two tabs racing) it is rejected without revoking anything.
- **Idle timeout**: a refresh token unused for 48 hours is rejected with an "inactivity" error, even if unexpired. Each rotation restarts the 30 days, so an active session does not expire.
- A revoked session's *access* token stays valid until its 15 minutes run out (stateless JWTs); refreshing is what ends.

### Tests

The backend tests need a **migrated PostgreSQL database whose name ends in `_test`**, because they truncate the user tables. They refuse to run otherwise.

```bash
createdb healthnexus_test
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/healthnexus_test alembic upgrade head
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/healthnexus_test python -m app.seeds.seed_phc_facilities
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/healthnexus_test python -m pytest
```

Frontend: `npm run build` type-checks and builds.

---

## 🔐 Privacy & Security

Healthcare data requires strong privacy and security considerations.

HealthNexus is designed with principles such as:

* Secure authentication
* Encryption in transit
* Encryption at rest
* Privacy-aware data handling
* Minimal data exposure
* Role-based access where required
* Aggregation and anonymization for community-level analytics

The project aims to maintain compatibility with relevant healthcare and data-protection standards as the system evolves.

---

## 🎯 Development Goals

HealthNexus is being developed incrementally:

* [x] Project foundation
* [x] Frontend architecture
* [x] Backend API architecture
* [x] User authentication
* [x] Health profile
* [x] Health metric tracking
* [ ] Healthcare facility discovery
* [x] AI health assistant
* [x] RAG pipeline
* [x] ML intelligence layer
* [ ] Community disease analytics
* [ ] Security hardening
* [x] Testing
* [ ] Deployment

---

## 🌍 Long-Term Vision

HealthNexus aims to create a unified healthcare intelligence layer where:

```text
Personal Health Data
        ↓
AI-powered Understanding
        ↓
Personalized Insights
        ↓
Preventive Action
        ↓
Community Health Intelligence
        ↓
Better Healthcare Accessibility
```

The long-term objective is to use **AI, machine learning, healthcare data, and intelligent systems** to make healthcare more accessible, proactive, and data-driven.

---

## ⚠️ Disclaimer

HealthNexus is a technology and research project intended for educational, experimental, and healthcare-assistance purposes.

It does **not** provide medical diagnosis or replace professional medical advice, diagnosis, or treatment.

---

## 👨‍💻 Project

**HealthNexus**

Built with ❤️ using AI, software engineering, and healthcare technology.
