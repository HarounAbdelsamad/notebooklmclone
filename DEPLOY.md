# Deployment Runbook

Manual, ordered checklist to provision the NotebookLM clone in production. Everything here uses
**your own** accounts and secrets — none of it is automated in the repo. Config lives in
`render.yaml` (API + Celery worker + Redis), `frontend/vercel.json`, and
`.github/workflows/ci.yml`.

Architecture recap: React/Vite frontend on **Vercel** → FastAPI + Celery on **Render** →
**Supabase** Postgres (pgvector) + Storage. Auth via **Clerk**, monitoring via **Sentry**.

> The API must run on a warm instance. `render.yaml` pins `plan: starter` because free-tier cold
> starts break SSE streaming. The Celery **worker is a separate Render service** from the API.

---

## 1. Supabase (database + storage)

1. Create a new Supabase project. Choose a region close to your Render region.
2. Enable pgvector: SQL Editor → run
   ```sql
   create extension if not exists vector;
   ```
3. Create a Storage bucket named **`documents`** (must match `SUPABASE_STORAGE_BUCKET`).
   Keep it private; the backend uses the service-role key.
4. Collect these values (Project Settings):
   - **DATABASE_URL** — build the async form for SQLAlchemy:
     `postgresql+asyncpg://postgres:<db-password>@<host>:5432/postgres`
     (Use the direct connection host/port from Database settings. Alembic derives the sync
     `+psycopg` URL automatically.)
   - **SUPABASE_URL** — `https://<project-ref>.supabase.co`
   - **SUPABASE_SERVICE_KEY** — the service-role key (secret; never ship to the frontend).

## 2. Run database migrations against Supabase

From a machine with the backend deps installed, pointing at the Supabase DB:

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://postgres:<db-password>@<host>:5432/postgres" \
  .venv/Scripts/python.exe -m alembic upgrade head
```

(Render also runs `alembic upgrade head` in the API build command, but running it once here
confirms connectivity and that pgvector is enabled before the first deploy.)

## 3. Render (API + worker + Redis)

1. New → **Blueprint** → point at this repo. Render reads `render.yaml` and proposes the three
   services: `notebooklm-api` (web), `notebooklm-worker`, `notebooklm-redis`.
2. Set each `sync: false` secret on **both** the API and worker services as applicable:

   | Env var                | API | Worker | Value source                          |
   | ---------------------- | :-: | :----: | ------------------------------------- |
   | `DATABASE_URL`         |  ✓  |   ✓    | Step 1 (async asyncpg form)           |
   | `SUPABASE_URL`         |  ✓  |   ✓    | Step 1                                |
   | `SUPABASE_SERVICE_KEY` |  ✓  |   ✓    | Step 1                                |
   | `OPENROUTER_API_KEY`   |  ✓  |   ✓    | OpenRouter                            |
   | `EMBEDDINGS_API_KEY`   |  ✓  |   ✓    | DeepInfra                             |
   | `RERANK_API_KEY`       |  ✓  |   ✓    | DeepInfra                             |
   | `CLERK_JWKS_URL`       |  ✓  |        | Step 6                                |
   | `CLERK_ISSUER`         |  ✓  |        | Step 6                                |
   | `CLERK_AUDIENCE`       |  ✓  |        | Step 6 (**required in prod**)         |
   | `CORS_ORIGINS`         |  ✓  |        | Step 5 (set after Vercel URL known)   |
   | `SENTRY_DSN`           |  ✓  |        | Step 7 (backend DSN)                  |

   Non-secret vars are already baked into `render.yaml` (`ENVIRONMENT=production`,
   `SUPABASE_STORAGE_BUCKET=documents`, `MAX_UPLOAD_MB=25`, `PYTHON_VERSION`, `REDIS_URL`).
3. Deploy. Wait for the API health check at `/api/health` to go green.
4. Note the **API URL**: `https://<notebooklm-api>.onrender.com`.

## 4. Keep-warm (defense-in-depth)

The starter plan already prevents cold starts; add an external pinger as a safety net (chosen over
a Render cron service to keep the blueprint simple / avoid another paid worker):

- Create a monitor on a free uptime service (UptimeRobot, cron-job.org, BetterStack, …).
- Target: `https://<notebooklm-api>.onrender.com/api/health`
- Interval: every **10 minutes**, method GET, expect HTTP 200.

## 5. CORS

Once the Vercel origin is known (Step 6), set `CORS_ORIGINS` on the Render **API** service to the
exact origin (no trailing slash), e.g. `https://<app>.vercel.app`. Comma-separate multiple origins
(e.g. a custom domain). Redeploy the API for the change to take effect.

## 6. Vercel (frontend) + Clerk

1. New Vercel project from this repo. Set **Root Directory** to `frontend/`.
   `frontend/vercel.json` handles the Vite build + SPA rewrites.
2. Configure Clerk first (needed for the keys below):
   - Create a Clerk application. Note the **Frontend API / JWKS URL**, **Issuer**, and set an
     **audience** (aud) claim for your API.
   - `CLERK_JWKS_URL` = `https://<subdomain>.clerk.accounts.dev/.well-known/jwks.json`
   - `CLERK_ISSUER`   = `https://<subdomain>.clerk.accounts.dev`
   - `CLERK_AUDIENCE` = the audience you configured (**issuer AND audience are required in prod**).
     Put these three on the **Render API** service (Step 3).
3. Set Vercel env vars (Production):
   - `VITE_CLERK_PUBLISHABLE_KEY` = Clerk `pk_live_...`
   - `VITE_API_BASE_URL` = `https://<notebooklm-api>.onrender.com/api` (include `/api`)
   - `VITE_SENTRY_DSN` = frontend Sentry DSN (optional; Step 7)
4. Deploy. Copy the resulting origin and complete **Step 5** (CORS) on Render.

## 7. Sentry

- Backend: create a project, put its DSN in `SENTRY_DSN` on the Render **API** service.
- Frontend: create a project, put its DSN in `VITE_SENTRY_DSN` on Vercel.

## 8. GitHub Actions deploy hooks

CI (`.github/workflows/ci.yml`) auto-deploys on push to `main` **after** backend + frontend jobs
pass. Add these repo secrets (Settings → Secrets and variables → Actions):

- `RENDER_DEPLOY_HOOK_URL` — Render API service → Settings → Deploy Hook URL. (Blueprint services
  can each have their own hook; the worker also redeploys from its own hook if you add one.)
- `VERCEL_DEPLOY_HOOK_URL` — **optional.** If Vercel's Git integration already auto-deploys on push
  to `main`, leave this unset and the CI step no-ops. Set it only if you disabled auto-deploy.

Both steps skip gracefully when their secret is absent — never hardcode hook URLs.

## 9. End-to-end smoke test

1. Open the Vercel URL, sign in via Clerk.
2. Create a notebook, **upload** a PDF/DOCX.
3. Watch the document reach **processed** status (Celery ingestion: extract → chunk → embed →
   store). If it stalls, check the Render **worker** logs and Redis connectivity.
4. **Ask** a question grounded in the document.
5. Confirm a streamed answer (SSE) arrives **with citations** `[n]` mapping to source chunks/pages.

If any step fails, check: Render API logs, Render worker logs, Supabase logs, and Sentry. A
code/config bug in the app (not infra) should be routed to the `backend` / `frontend` agents.
