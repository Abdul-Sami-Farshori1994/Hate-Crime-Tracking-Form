# Hate Crime Tracking Form

Full-stack survey app: React (Vite) frontend, FastAPI API, PostgreSQL (or SQLite for local dev).

## Quick start (Docker)

```powershell
# Set a strong secret before production use
$env:SECRET_KEY = "your-long-random-secret-at-least-32-characters"

docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

- **App:** http://localhost:8080  
- **API (direct, Docker):** http://localhost:8787  
- **Postgres (dev overlay):** localhost:5433  

Default logins (only seeded when the database is empty and `ALLOW_DEFAULT_USER_SEED=true`):

| Role  | Username | Password |
|-------|----------|----------|
| Admin | `admin`  | `admin`  |
| Form  | `user`   | `user`   |

Change these immediately in production via **Admin → Form access** and **Admin Credential**.

## Local development

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit DATABASE_URL if needed (Postgres on 5433 or SQLite)
alembic upgrade head
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173 — Vite proxies API routes to port **8787** (Docker API; see `frontend/vite.config.ts`).

**Important:** Stop any old local `uvicorn` on ports 8000–8001 if requests return 404 — those processes can shadow the Docker API.

## Production data seed (local → production)

Alembic only creates **empty tables**. To copy your full local database (form, responses, users, etc.):

**1. On your PC** (after data changes, re-run export):

```powershell
cd backend
$env:DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/hatecrime"
python scripts/export_seed_data.py
```

**2. Commit and deploy** `backend/data/seed/` with the app.

**3. On production** (after `alembic upgrade head` / containers are up):

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec api python seed.py --dry-run
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec api python seed.py --commit
```

This replaces users, form structure, all responses, and audit log with the exported snapshot.

**Notes:** Use the same `SECRET_KEY` on production if admin MFA was enabled locally. Re-export and re-seed whenever local data changes.

## Import Microsoft Form (one-time)

Place export at `backend/data/microsoft_form.json`, then:

```bash
cd backend
alembic upgrade head
python import_microsoft_form.py
```

This replaces all pages, questions, and existing responses.

## Import Excel responses (Microsoft Forms export)

1. In Microsoft Forms: **Responses → Open in Excel** (or export `.xlsx`).
2. Save the file as `backend/data/responses.xlsx`.
3. Ensure the form questions are already in the database (`python import_microsoft_form.py` once).
4. Preview, then import:

```powershell
cd backend
pip install openpyxl
python import_responses_excel.py --dry-run
python import_responses_excel.py --commit
```

Column headers must match question text from the form (metadata columns like **Id**, **Start time**, **Email** are ignored). Respondent name is taken from **“Please enter your name”** (Q1), then **Name** / **Email**, then `import-{Id}`.

Existing responses are kept. Multiple submissions may share the same name; use `--on-duplicate suffix` only if you want labels like `Name (2)` during import.

## Tests

```powershell
cd backend
pip install -r requirements-dev.txt
pytest
pytest tests/test_e2e_soft_delete.py -v   # end-to-end hide/unhide (HTTP + DB)
```

## Production checklist

See [DEPLOYMENT.md](DEPLOYMENT.md).

## Environment variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Postgres or SQLite connection string |
| `SECRET_KEY` | JWT signing secret (32+ chars in production) |
| `ENVIRONMENT` | `development` or `production` |
| `CORS_ORIGINS` | Comma-separated allowed frontend URLs |
| `ALLOW_DEFAULT_USER_SEED` | `false` in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime (default 30) |
