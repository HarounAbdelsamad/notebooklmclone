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

> ✅ **Already provisioned for this project** (`NotebookLMClone` / ref `tisgrflxwgwpqwcszzfw`,
> eu-west-1) via the Supabase MCP: baseline schema applied (all tables + `alembic_version` stamped
> `0001_baseline`), pgvector 0.8.2 + HNSW/GIN indexes created, private `documents` bucket created, and
> RLS enabled on all public tables. Steps 1–3 are the from-scratch recipe; for this project you only
> need to collect the values in **step 4** into `.env`.

1. Create a new Supabase project. Choose a region close to your Render region.
2. Enable pgvector: SQL Editor → run
   ```sql
   create extension if not exists vector;
   ```
3. Create a Storage bucket named **`documents`** (must match `SUPABASE_STORAGE_BUCKET`).
   Keep it private; the backend uses the service-role key.
4. Collect these values into `.env` (never commit them):
   - **DATABASE_URL** — dashboard → **Connect** → **Session pooler**, then change the scheme to
     `postgresql+asyncpg://<user>:<db-password>@<pooler-host>:5432/postgres`. Use the **session
     pooler** (IPv4, port 5432): the direct `db.<ref>.supabase.co` host is IPv6-only (often
     unreachable from Render), and the **transaction** pooler (port 6543) breaks asyncpg/psycopg
     prepared statements. Alembic derives the sync `+psycopg` URL automatically.
   - **SUPABASE_URL** — `https://<project-ref>.supabase.co` (this project:
     `https://tisgrflxwgwpqwcszzfw.supabase.co`).
   - **SUPABASE_SERVICE_KEY** — Settings → API → **service_role** key (secret; never ship to the frontend).

## 2. Run database migrations against Supabase

> ✅ Already applied for this project via MCP — `alembic_version` is stamped `0001_baseline`, so the
> command below (and Render's build-time `alembic upgrade head`) is a **no-op** that only confirms
> connectivity. Still worth running once locally to verify your `DATABASE_URL` reaches Supabase
> before the first deploy.

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
   | `OPENROUTER_API_KEY`   |  ✓  |   ✓    | OpenRouter (also powers embeddings + rerank) |
   | `CLERK_JWKS_URL`       |  ✓  |        | Step 6                                |
   | `CLERK_ISSUER`         |  ✓  |        | Step 6                                |
   | `CLERK_AUDIENCE`       |     |        | Step 6 (optional — usually unset)     |
   | `CORS_ORIGINS`         |  ✓  |        | Step 5 (set after Vercel URL known)   |
   | `SENTRY_DSN`           |  ✓  |        | Step 7 (backend DSN)                  |

   Non-secret vars are already baked into `render.yaml` (`ENVIRONMENT=production`,
   `SUPABASE_STORAGE_BUCKET=documents`, `MAX_UPLOAD_MB=25`, `PYTHON_VERSION`, `REDIS_URL`).

   > Embeddings + rerank run on OpenRouter's free NVIDIA Nemotron models and **reuse
   > `OPENROUTER_API_KEY`** — there is no separate DeepInfra key. The optional `EMBEDDINGS_API_KEY` /
   > `RERANK_API_KEY` overrides are not part of the blueprint; leave them unset unless you want to
   > point embeddings/rerank at a different provider.
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
   - Create a Clerk application. Note the **Frontend API / JWKS URL** and **Issuer**.
   - `CLERK_JWKS_URL` = `https://<subdomain>.clerk.accounts.dev/.well-known/jwks.json`
   - `CLERK_ISSUER`   = `https://<subdomain>.clerk.accounts.dev` (**required in prod**)
   - `CLERK_AUDIENCE` = optional. Clerk's default session tokens carry no `aud` claim, so leave it
     unset unless you configure a Clerk JWT template with an audience.
     Put the JWKS URL + issuer on the **Render API** service (Step 3).
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
