# Jobify

Job & learning aggregator: search a role, see matching jobs, skill frequency, CV gaps, salary distribution, books, courses, GitHub projects, certifications, and a study roadmap.

## Stack

| Layer | Tech |
|--------|------|
| Frontend | Next.js (React + TypeScript) → Vercel |
| Backend | FastAPI (Python) → Railway / Render |
| Database | SQLite locally by default; PostgreSQL (Docker / Neon) for production |

## Quick start

### 1. Backend

> Note: if `python3` on macOS points at a broken Framework install (0-byte binary), use Homebrew Python explicitly.

```bash
cd apps/api
/usr/local/opt/python@3.13/bin/python3.13 -m venv .venv   # or: python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../../.env.example .env
uvicorn app.main:app --reload --port 8001
```

API docs: http://localhost:8001/docs

> If port 8000 is free, you can use that instead — just match `NEXT_PUBLIC_API_URL` in `apps/web/.env.local`.

Optional Postgres instead of SQLite:

```bash
docker compose up -d
# in apps/api/.env
# DATABASE_URL=postgresql+psycopg://jobify:jobify@localhost:5432/jobify
```

### 2. Frontend

```bash
cd apps/web
npm install
npm run dev
```

App: http://localhost:3000

## Deploy

- **Frontend (Vercel):** set Root Directory to `apps/web`, set `NEXT_PUBLIC_API_URL` to your public API URL.
- **Backend:** deploy `apps/api` to Railway/Render with `Procfile`; set `DATABASE_URL` (Neon) and `API_CORS_ORIGINS` to your Vercel domain.
- **DB:** Neon Postgres connection string → `DATABASE_URL=postgresql+psycopg://...`

Optional: set `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` for live Adzuna jobs. Remotive is enabled by default.

## MVP features

- Role search (sample jobs + Remotive; Adzuna when keys are set)
- Skill frequency across matched jobs
- CV upload (PDF/TXT) → missing skills
- Salary distribution
- Books, courses, GitHub repos, certifications, interview prompts
- Learning roadmap + estimated study time
# jobify
